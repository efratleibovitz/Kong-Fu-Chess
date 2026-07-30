"""server/matchmaking/session_dispatch.py

Matchmaking cannot create a GameSession in its own memory anymore - once
Matchmaking and Game Server Shards are separate containers, session.py's
in-memory `_sessions` dict lives on the SHARD, not here. This sends a
one-shot control call to whichever shard owns the room (same consistent
hash everyone else uses) to pre-register the session with verified
white/black identities BEFORE either player connects - preserving the
identity-based color assignment in GameSession.assign_color instead of
falling back to first-connect-wins ordering.
"""

import json

import websockets

from server.core.internal_protocol import NUM_SHARDS, shard_index_for_room, shard_internal_url, KIND_CREATE_SESSION
from server.core.redis_client import set_room_shard


async def create_remote_session(
    room_id: str,
    white_user_id: int,
    white_elo: int | None,
    black_user_id: int,
    black_elo: int | None,
) -> None:
    shard_index = shard_index_for_room(room_id, NUM_SHARDS)
    await set_room_shard(room_id, shard_index)
    shard_url = shard_internal_url(room_id, NUM_SHARDS)
    async with websockets.connect(shard_url) as ws:
        await ws.send(json.dumps({
            "kind": KIND_CREATE_SESSION,
            "room_id": room_id,
            "white_user_id": white_user_id,
            "white_elo": white_elo,
            "black_user_id": black_user_id,
            "black_elo": black_elo,
        }))
