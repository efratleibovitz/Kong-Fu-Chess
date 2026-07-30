"""server/matchmaking/session_dispatch.py

Notifies the correct Game Server shard that a new session should be
pre-registered, using Redis Pub/Sub instead of a direct WebSocket call.

Before (Stage 1-4):
    Matchmaking ──websockets.connect()──► Game Server shard

After (Stage 5):
    Matchmaking ──PUBLISH──► Redis ──SUBSCRIBE──► Game Server shard

Benefits:
  - Matchmaking no longer needs to know the shard's hostname/port.
  - If the shard is briefly restarting, the message is still delivered
    once it reconnects and re-subscribes (Redis buffers in-flight).
  - Services are decoupled: adding a new shard only requires it to
    subscribe to its own channel — no Matchmaking config change needed.

Fallback: if Redis is unavailable, falls back to the original direct
WebSocket call so the system keeps working without Redis.
"""

import json

import websockets

from server.core.internal_protocol import (
    NUM_SHARDS,
    shard_index_for_room,
    shard_internal_url,
    shard_channel,
    KIND_CREATE_SESSION,
)
from server.core.redis_client import set_room_shard, publish


async def create_remote_session(
    room_id: str,
    white_user_id: int,
    white_elo: int | None,
    black_user_id: int,
    black_elo: int | None,
) -> None:
    shard_index = shard_index_for_room(room_id, NUM_SHARDS)
    await set_room_shard(room_id, shard_index)

    payload = {
        "kind": KIND_CREATE_SESSION,
        "room_id": room_id,
        "white_user_id": white_user_id,
        "white_elo": white_elo,
        "black_user_id": black_user_id,
        "black_elo": black_elo,
    }

    # Try Redis Pub/Sub first; fall back to direct WebSocket if unavailable.
    published = await publish(shard_channel(shard_index), payload)
    if not published:
        shard_url = shard_internal_url(room_id, NUM_SHARDS)
        async with websockets.connect(shard_url) as ws:
            await ws.send(json.dumps(payload))
