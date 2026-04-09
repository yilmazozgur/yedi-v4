"""/api/bridge — live state of the WebSocket bridge to the browser game.

The dashboard polls this to render the "Game connected/disconnected" pill in
the sidebar, and ``POST /api/runs`` checks it before letting a run start.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..bridge_status import BridgeStatus
from .deps import get_bridge_status
from .schemas import BridgeStatusResponse

router = APIRouter(prefix="/api/bridge", tags=["bridge"])


@router.get("/status", response_model=BridgeStatusResponse)
def bridge_status(status: BridgeStatus = Depends(get_bridge_status)) -> BridgeStatusResponse:
    """Return whether the browser game / Python agent are currently bridged."""
    snap = status.snapshot()
    return BridgeStatusResponse(
        game_connected=snap.game_connected,
        agent_connected=snap.agent_connected,
        game_connected_at=snap.game_connected_at,
        agent_connected_at=snap.agent_connected_at,
        tab_hidden=snap.tab_hidden,
    )
