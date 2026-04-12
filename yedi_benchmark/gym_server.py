"""
Yedi AI Benchmark — FastAPI server with WebSocket bridge.

This server:
1. Serves the Unity WebGL build (static files)
2. Provides REST API for scores (preserving existing endpoints)
3. Bridges Python gym environments to the browser game via WebSocket

Architecture:
    Python Agent <-> /ws/agent <-> Server <-> /ws/game <-> Browser/Unity

Usage:
    python -m yedi_benchmark.gym_server --port 8000
    # Default --build-dir resolves to <repo>/WebGLBuild relative to this
    # file, so the command works regardless of your current directory.
"""

import argparse
import asyncio
import json
import logging
import mimetypes
import os
import time
from pathlib import Path
from typing import Optional

# Load .env file (ANTHROPIC_API_KEY, etc.) so agent configs can resolve keys.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass  # python-dotenv not installed — keys must be in the real environment

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Support both `python -m yedi_benchmark.gym_server` (relative import) and the
# legacy `python gym_server.py` invocation (absolute fallback).
try:
    from .api import mount_api_routers
    from .bridge_status import get_bridge_status
    from .web import mount_web_ui
except ImportError:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from yedi_benchmark.api import mount_api_routers
    from yedi_benchmark.bridge_status import get_bridge_status
    from yedi_benchmark.web import mount_web_ui

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("yedi_server")

# ------------------------------------------------------------------
# Score persistence (migrated from server.py)
# ------------------------------------------------------------------

SCORES_FILE = "scores.json"
active_player = {"name": "default"}


def load_scores() -> dict:
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, "r") as f:
            return json.load(f)
    return {}


def save_scores(scores: dict):
    with open(SCORES_FILE, "w") as f:
        json.dump(scores, f, indent=2)


# ------------------------------------------------------------------
# WebSocket bridge state
# ------------------------------------------------------------------

class BridgeError(Exception):
    """Raised when the WebSocket bridge between agent and game fails.

    Distinguishes bridge transport problems (game tab closed, send_json on a
    closed ASGI socket, etc.) from genuine command failures so the agent side
    can shut down cleanly instead of cascading into ASGI runtime errors.
    """


# Heartbeat: how often the server pings the game (s) and how stale the
# bridge can get before we mark it dead. With a 5s interval and 12s dead
# threshold we tolerate one missed ping plus jitter; two missed pings is a
# guaranteed kill. Tuned so the agent fails fast (~12s) instead of sitting on
# the per-command 30s wait_for.
HEARTBEAT_INTERVAL_S = 5.0
HEARTBEAT_DEAD_AFTER_S = 12.0
# Sentinel seq used by the heartbeat ping. The agent route filters replies
# carrying this seq so they don't show up as "unrouted" warnings.
HEARTBEAT_SEQ = -1


class GameConnection:
    """Represents the browser/Unity WebSocket connection."""
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.connected = True
        # Updated by game_websocket() on every incoming message; the
        # heartbeat task uses this to decide whether the bridge is alive.
        self.last_seen = time.monotonic()
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def send(self, data: dict):
        if not self.connected:
            raise BridgeError("game connection is closed")
        try:
            await self.ws.send_json(data)
        except Exception as e:
            # starlette raises RuntimeError("Unexpected ASGI message...") if the
            # transport was closed underneath us. Treat any send failure as a
            # bridge death and surface it to the agent side as BridgeError.
            self.mark_dead()
            raise BridgeError(f"game send failed: {e}") from e

    async def receive(self) -> dict:
        return await self.ws.receive_json()

    def touch(self) -> None:
        """Mark the bridge as having just heard from the game."""
        self.last_seen = time.monotonic()

    def start_heartbeat(self) -> None:
        """Spawn the periodic ping task that detects a silent dead bridge."""
        if self._heartbeat_task is not None:
            return
        loop = asyncio.get_event_loop()
        self._heartbeat_task = loop.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        """Ping the game every HEARTBEAT_INTERVAL_S; mark dead if silent.

        We don't care about correlating the pong reply to the ping — the
        receive loop in ``game_websocket`` updates ``last_seen`` on ANY
        incoming message (state responses, events, pong acks). This task
        only fires when there's been no chatter from the game for a while.
        """
        try:
            while self.connected:
                await asyncio.sleep(HEARTBEAT_INTERVAL_S)
                if not self.connected:
                    return
                age = time.monotonic() - self.last_seen
                if age > HEARTBEAT_DEAD_AFTER_S:
                    logger.warning(
                        "game bridge heartbeat dead: no message in %.1fs",
                        age,
                    )
                    self.mark_dead()
                    return
                try:
                    await self.ws.send_json({
                        "type": "ping",
                        "seq": HEARTBEAT_SEQ,
                    })
                except Exception as e:
                    logger.warning("heartbeat ping send failed: %s", e)
                    self.mark_dead()
                    return
        except asyncio.CancelledError:
            return

    def mark_dead(self):
        """Mark the bridge as dead and fail all in-flight pending requests.

        Idempotent — safe to call from both the disconnect handler and the
        send-failure path.
        """
        global game_connection
        if not self.connected:
            return
        self.connected = False
        if self._heartbeat_task is not None and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        try:
            get_bridge_status().mark_game_disconnected()
        except Exception:
            pass
        if game_connection is self:
            game_connection = None
        if agent_connection is not None:
            for seq, fut in list(agent_connection.pending_responses.items()):
                if not fut.done():
                    fut.set_exception(BridgeError("game connection lost"))
            agent_connection.pending_responses.clear()


class AgentConnection:
    """Represents the Python gym environment WebSocket connection."""
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.connected = True
        self.pending_responses: dict[int, asyncio.Future] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.seq = 0

    async def send_command(self, command: dict, timeout: float = 30.0) -> dict:
        """Send a command to the game and wait for the response."""
        self.seq += 1
        command["seq"] = self.seq
        seq = self.seq

        future = asyncio.get_event_loop().create_future()
        self.pending_responses[seq] = future

        # Forward to game connection
        if game_connection is None or not game_connection.connected:
            self.pending_responses.pop(seq, None)
            raise BridgeError("no game connected")

        try:
            await game_connection.send(command)
        except BridgeError:
            self.pending_responses.pop(seq, None)
            raise

        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self.pending_responses.pop(seq, None)
            raise BridgeError(
                f"command timed out after {timeout}s: {command.get('type')}"
            )

    def on_game_message(self, message: dict):
        """Handle a message from the game, routing to the right pending request."""
        seq = message.get("seq")
        if seq and seq in self.pending_responses:
            self.pending_responses[seq].set_result(message)
            del self.pending_responses[seq]
        elif message.get("type") == "event":
            self.event_queue.put_nowait(message)
        else:
            logger.warning(f"Unrouted game message: {json.dumps(message)[:200]}")


game_connection: Optional[GameConnection] = None
agent_connection: Optional[AgentConnection] = None

# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------

app = FastAPI(title="Yedi AI Benchmark Server")

# Phase 2 API routers (agents, prompts, configs, runs)
mount_api_routers(app)

# Phase 3 dashboard pages (Jinja templates + static assets at /static/...)
mount_web_ui(app)

# --- Score REST API (preserved from server.py) ---

@app.get("/api/player")
async def get_player():
    return {"name": active_player["name"]}


@app.post("/api/player")
async def set_player(body: dict):
    name = body.get("name", "default")
    active_player["name"] = name
    logger.info(f"Active player set to: {name}")
    return {"name": name}


@app.get("/api/scores/{username}")
async def get_scores_api(username: str):
    scores = load_scores()
    return scores.get(username, {})


@app.post("/api/scores/{username}")
async def post_score(username: str, body: dict):
    config = body.get("config", "")
    mana = body.get("mana", 0)
    if not config:
        raise HTTPException(400, "Missing config")

    scores = load_scores()
    if username not in scores:
        scores[username] = {}

    current_max = scores[username].get(config, 0)
    new_record = mana > current_max
    if new_record:
        scores[username][config] = mana
        save_scores(scores)

    return {
        "new_record": new_record,
        "max_mana": scores[username].get(config, 0),
        "config": config,
    }


@app.delete("/api/scores/{username}")
async def delete_scores(username: str):
    scores = load_scores()
    if username in scores:
        del scores[username]
        save_scores(scores)
    return {"deleted": username}


@app.get("/api/leaderboard/{config}")
async def get_leaderboard(config: str):
    scores = load_scores()
    board = []
    for user, user_scores in scores.items():
        if config in user_scores:
            board.append({"username": user, "max_mana": user_scores[config]})
    board.sort(key=lambda x: x["max_mana"], reverse=True)
    return board


# --- Agent command HTTP endpoint (alternative to WebSocket) ---

@app.post("/api/agent/command")
async def agent_command_http(body: dict):
    """Send a command to the game via the active agent session."""
    if agent_connection is None or not agent_connection.connected:
        raise HTTPException(503, "No agent session active")
    try:
        response = await agent_connection.send_command(body)
        return response
    except BridgeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/agent/events")
async def agent_events():
    """Get queued game events."""
    if agent_connection is None:
        return []
    events = []
    while not agent_connection.event_queue.empty():
        events.append(agent_connection.event_queue.get_nowait())
    return events


# --- WebSocket endpoints ---

@app.websocket("/ws/game")
async def game_websocket(ws: WebSocket):
    """WebSocket for the browser/Unity game to connect to."""
    global game_connection
    await ws.accept()
    conn = GameConnection(ws)
    game_connection = conn
    get_bridge_status().mark_game_connected()
    logger.info("Game connected via WebSocket")
    conn.start_heartbeat()

    try:
        while True:
            data = await ws.receive_json()
            # Any incoming message proves the bridge is alive — let the
            # heartbeat task off the hook for another window.
            conn.touch()

            # Drop heartbeat acks before they hit the agent route, otherwise
            # the unrouted-message warning fires every 5 seconds.
            if data.get("seq") == HEARTBEAT_SEQ:
                continue

            # Page Visibility report from the browser tab. Sent unsolicited
            # by index.html's visibilitychange handler — directly from JS,
            # not via Unity SendMessage, so it still arrives even when the
            # WebGL main loop is throttled. We update bridge status and do
            # NOT forward to the agent route (the gym env doesn't care).
            if data.get("type") == "visibility":
                hidden = bool(data.get("hidden", False))
                get_bridge_status().set_tab_hidden(hidden)
                if hidden:
                    logger.warning(
                        "browser tab reported hidden — WebGL will be throttled, "
                        "expect bridge timeouts on draw_card etc."
                    )
                else:
                    logger.info("browser tab reported visible again")
                continue

            # Route game messages to the agent
            if agent_connection and agent_connection.connected:
                agent_connection.on_game_message(data)
            else:
                logger.debug(f"Game message (no agent): {json.dumps(data)[:200]}")
    except WebSocketDisconnect:
        logger.info("Game disconnected")
    except Exception as e:
        logger.warning(f"Game websocket failed: {e}")
    finally:
        # mark_dead is idempotent and clears pending requests so the agent
        # gets a clean BridgeError instead of waiting for the 30s timeout.
        conn.mark_dead()


@app.websocket("/ws/agent")
async def agent_websocket(ws: WebSocket):
    """WebSocket for the Python gym environment to connect to."""
    global agent_connection
    await ws.accept()
    conn = AgentConnection(ws)
    agent_connection = conn
    get_bridge_status().mark_agent_connected()
    logger.info("Agent connected via WebSocket")

    try:
        while True:
            data = await ws.receive_json()
            seq = data.get("seq")
            if seq is None:
                conn.seq += 1
                seq = conn.seq
                data["seq"] = seq

            try:
                if game_connection is None or not game_connection.connected:
                    await ws.send_json({"error": "no game connected", "seq": seq})
                    continue

                future = asyncio.get_event_loop().create_future()
                conn.pending_responses[seq] = future
                try:
                    await game_connection.send(data)
                except BridgeError as be:
                    conn.pending_responses.pop(seq, None)
                    await ws.send_json({"error": str(be), "seq": seq})
                    continue

                try:
                    response = await asyncio.wait_for(future, 30.0)
                    await ws.send_json(response)
                except asyncio.TimeoutError:
                    conn.pending_responses.pop(seq, None)
                    await ws.send_json({"error": "timeout", "seq": seq})
                except BridgeError as be:
                    # Game died while we were awaiting — mark_dead already
                    # popped the future from pending_responses.
                    await ws.send_json({"error": str(be), "seq": seq})
            except WebSocketDisconnect:
                raise
            except Exception as cmd_err:
                # Per-command failure: log it but keep the agent ws alive so
                # the run can decide what to do (retry, abort, etc.).
                logger.warning(f"Agent command {data.get('type')} failed: {cmd_err}")
                try:
                    await ws.send_json({"error": str(cmd_err), "seq": seq})
                except Exception:
                    raise
    except WebSocketDisconnect:
        logger.info("Agent disconnected")
    except Exception as e:
        logger.warning(f"Agent websocket failed: {e}")
    finally:
        for fut in list(conn.pending_responses.values()):
            if not fut.done():
                fut.set_exception(BridgeError("agent connection lost"))
        conn.pending_responses.clear()
        conn.connected = False
        if agent_connection is conn:
            agent_connection = None
        try:
            get_bridge_status().mark_agent_disconnected()
        except Exception:
            pass


# ------------------------------------------------------------------
# Static file serving with proper MIME types
# ------------------------------------------------------------------

# Store build_dir for use in routes
_build_dir: str = ""


def _reconcile_orphan_runs() -> None:
    """Mark stranded RUNNING/PENDING records as FAILED on startup.

    A previous server process may have crashed or been killed mid-run; the
    on-disk record is still ``status: running`` even though the worker thread
    is gone. Without this, the UI is stuck — Cancel returns 404 (executor
    isn't tracking that run) and the row template hides Delete while the
    status is "running".
    """
    try:
        from .api.deps import get_run_registry
        reconciled = get_run_registry().reconcile_orphans()
        if reconciled:
            logger.warning(
                "Reconciled %d orphaned run(s) on startup: %s",
                len(reconciled), ", ".join(reconciled),
            )
    except Exception as e:
        logger.warning("Run reconciliation failed (non-fatal): %s", e)


def setup_static_files(build_dir: str):
    """Set up static file serving for the WebGL build."""
    global _build_dir
    _build_dir = build_dir

    # Ensure correct MIME types
    mimetypes.add_type("application/wasm", ".wasm")
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("application/octet-stream", ".data")
    mimetypes.add_type("application/gzip", ".gz")
    mimetypes.add_type("application/x-brotli", ".br")

    if not os.path.exists(build_dir):
        logger.warning(f"Build directory not found: {build_dir}")
        logger.warning("You need to do a full WebGL build from Unity first.")
        return

    index_path = os.path.join(build_dir, "index.html")
    if not os.path.exists(index_path):
        logger.warning(f"No index.html in {build_dir}. Rebuild from Unity with the YediBenchmark template.")
        logger.warning("The server will still work for WebSocket connections (agent ↔ game bridge).")
        return

    logger.info(f"Serving static files from: {build_dir}")


@app.get("/game/embed", include_in_schema=False)
async def serve_game_embed():
    """Serve the Unity WebGL game's index.html, intended to be iframed by
    the dashboard's /game page. The dashboard owns the /game URL itself."""
    if not _build_dir:
        return JSONResponse(
            {"error": "No build directory configured. Run: python gym_server.py --build-dir /path/to/WebGLBuild"},
            status_code=503)
    index_path = os.path.join(_build_dir, "index.html")
    if not os.path.exists(index_path):
        return JSONResponse(
            {"error": "No index.html found. Do a full WebGL build from Unity with the YediBenchmark template.",
             "build_dir": _build_dir},
            status_code=503)

    # Inject <base href="/"> so the WebGL loader's relative "Build/..." paths
    # resolve to /Build/... regardless of the document URL.
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        if "<base " not in html:
            html = html.replace("<head>", '<head>\n    <base href="/">', 1)
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})
    except OSError:
        return FileResponse(index_path, media_type="text/html")


@app.get("/Build/{filepath:path}")
async def serve_build_files(filepath: str):
    """Serve WebGL build files with correct Content-Encoding for .br/.gz."""
    full_path = os.path.join(_build_dir, "Build", filepath)
    if not os.path.exists(full_path):
        raise HTTPException(404, f"File not found: Build/{filepath}")

    # Determine content type and encoding
    headers = {}
    if filepath.endswith(".br"):
        headers["Content-Encoding"] = "br"
        # Strip .br to determine actual content type
        base = filepath[:-3]
        if base.endswith(".js"):
            media_type = "application/javascript"
        elif base.endswith(".wasm"):
            media_type = "application/wasm"
        elif base.endswith(".data"):
            media_type = "application/octet-stream"
        else:
            media_type = "application/octet-stream"
    elif filepath.endswith(".gz"):
        headers["Content-Encoding"] = "gzip"
        base = filepath[:-3]
        if base.endswith(".js"):
            media_type = "application/javascript"
        elif base.endswith(".wasm"):
            media_type = "application/wasm"
        elif base.endswith(".data"):
            media_type = "application/octet-stream"
        else:
            media_type = "application/octet-stream"
    else:
        media_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"

    return FileResponse(full_path, media_type=media_type, headers=headers)


@app.get("/StreamingAssets/{filepath:path}")
async def serve_streaming_assets(filepath: str):
    """Serve StreamingAssets."""
    full_path = os.path.join(_build_dir, "StreamingAssets", filepath)
    if not os.path.exists(full_path):
        raise HTTPException(404)
    return FileResponse(full_path)


@app.get("/TemplateData/{filepath:path}")
async def serve_template_data(filepath: str):
    """Serve TemplateData (icons, css, etc.)."""
    full_path = os.path.join(_build_dir, "TemplateData", filepath)
    if not os.path.exists(full_path):
        raise HTTPException(404)
    return FileResponse(full_path)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Yedi AI Benchmark Server")
    # The default is computed relative to THIS file rather than the cwd —
    # otherwise launching with `python -m yedi_benchmark.gym_server` from
    # the repo root resolves "../WebGLBuild" to the parent of the repo
    # root and the server can't find the Unity build. Anchoring on the
    # source file means the default works regardless of where you cd to.
    default_build_dir = str(Path(__file__).resolve().parent.parent / "WebGLBuild")
    parser.add_argument("--build-dir", default=default_build_dir,
                        help="Path to WebGL build directory")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    setup_static_files(os.path.abspath(args.build_dir))
    _reconcile_orphan_runs()

    logger.info(f"Starting server on {args.host}:{args.port}")
    logger.info(f"Game WebSocket: ws://{args.host}:{args.port}/ws/game")
    logger.info(f"Agent WebSocket: ws://{args.host}:{args.port}/ws/agent")
    logger.info(f"Agent HTTP API: http://{args.host}:{args.port}/api/agent/command")

    # Increase WebSocket ping timeout for cloud LLM providers (Claude,
    # GPT-4) whose API calls can take 10-30s. The default 20s ping timeout
    # closes the game bridge while the agent thread is blocked waiting for
    # an API response — even though the asyncio event loop is still alive.
    # 120s is generous enough for any provider while still catching truly
    # dead connections.
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        ws_ping_interval=30,
        ws_ping_timeout=120,
    )


if __name__ == "__main__":
    main()
