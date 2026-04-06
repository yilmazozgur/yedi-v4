"""
Yedi AI Benchmark — FastAPI server with WebSocket bridge.

This server:
1. Serves the Unity WebGL build (static files)
2. Provides REST API for scores (preserving existing endpoints)
3. Bridges Python gym environments to the browser game via WebSocket

Architecture:
    Python Agent <-> /ws/agent <-> Server <-> /ws/game <-> Browser/Unity

Usage:
    cd yedi_benchmark
    python gym_server.py --build-dir ../WebGLBuild --port 8000
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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

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

class GameConnection:
    """Represents the browser/Unity WebSocket connection."""
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.connected = True

    async def send(self, data: dict):
        if self.connected:
            await self.ws.send_json(data)

    async def receive(self) -> dict:
        return await self.ws.receive_json()


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
        if game_connection and game_connection.connected:
            await game_connection.send(command)
        else:
            future.set_exception(Exception("No game connected"))
            del self.pending_responses[seq]
            raise Exception("No game connected")

        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self.pending_responses.pop(seq, None)
            raise Exception(f"Command timed out after {timeout}s: {command.get('type')}")

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
    game_connection = GameConnection(ws)
    logger.info("Game connected via WebSocket")

    try:
        while True:
            data = await ws.receive_json()
            # Route game messages to the agent
            if agent_connection and agent_connection.connected:
                agent_connection.on_game_message(data)
            else:
                logger.debug(f"Game message (no agent): {json.dumps(data)[:200]}")
    except WebSocketDisconnect:
        logger.info("Game disconnected")
        game_connection = None


@app.websocket("/ws/agent")
async def agent_websocket(ws: WebSocket):
    """WebSocket for the Python gym environment to connect to."""
    global agent_connection
    await ws.accept()
    agent_connection = AgentConnection(ws)
    logger.info("Agent connected via WebSocket")

    try:
        while True:
            data = await ws.receive_json()
            # Agent sends commands — forward to game
            if game_connection and game_connection.connected:
                # Add sequence number if not present
                if "seq" not in data:
                    agent_connection.seq += 1
                    data["seq"] = agent_connection.seq

                future = asyncio.get_event_loop().create_future()
                agent_connection.pending_responses[data["seq"]] = future
                await game_connection.send(data)

                # Wait for response and forward back to agent
                try:
                    response = await asyncio.wait_for(future, 30.0)
                    await ws.send_json(response)
                except asyncio.TimeoutError:
                    await ws.send_json({"error": "timeout", "seq": data.get("seq")})
            else:
                await ws.send_json({"error": "No game connected", "seq": data.get("seq", 0)})
    except WebSocketDisconnect:
        logger.info("Agent disconnected")
        agent_connection = None


# ------------------------------------------------------------------
# Static file serving with proper MIME types
# ------------------------------------------------------------------

# Store build_dir for use in routes
_build_dir: str = ""


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


@app.get("/")
async def serve_index():
    """Serve the WebGL game's index.html."""
    if not _build_dir:
        return JSONResponse(
            {"error": "No build directory configured. Run: python gym_server.py --build-dir /path/to/WebGLBuild"},
            status_code=503)
    index_path = os.path.join(_build_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return JSONResponse(
        {"error": "No index.html found. Do a full WebGL build from Unity with the YediBenchmark template.",
         "build_dir": _build_dir},
        status_code=503)


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
    parser.add_argument("--build-dir", default="../WebGLBuild",
                        help="Path to WebGL build directory")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    setup_static_files(os.path.abspath(args.build_dir))

    logger.info(f"Starting server on {args.host}:{args.port}")
    logger.info(f"Game WebSocket: ws://{args.host}:{args.port}/ws/game")
    logger.info(f"Agent WebSocket: ws://{args.host}:{args.port}/ws/agent")
    logger.info(f"Agent HTTP API: http://{args.host}:{args.port}/api/agent/command")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
