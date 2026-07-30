"""server/core/redis_client.py

Optional Redis helper for:
  - Stage 1: room->shard routing (set/get_room_shard)
  - Stage 2: matchmaking queue (enqueue, dequeue_match, remove_from_queue,
             get_queue_entries)

If Redis is unavailable (no REDIS_URL, or connection fails), every call
silently returns None/empty and callers fall back to in-memory behavior -
no service is disrupted.
"""

import json
import logging
import os
import time

_logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL")
ROOM_KEY_TTL_SECONDS = 3600

# Sorted set key for the matchmaking queue.
# Score = ELO, member = JSON-serialised entry (user_id, elo, entered, token).
MATCHMAKING_QUEUE_KEY = "matchmaking:queue"

_redis = None


async def get_redis():
    global _redis
    if _redis is not None:
        return _redis
    if not REDIS_URL:
        return None
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        return _redis
    except Exception as e:
        _logger.warning("Redis unavailable: %s", e)
        return None


# ---------------------------------------------------------------------------
# Stage 1 — room->shard routing
# ---------------------------------------------------------------------------

async def set_room_shard(room_id: str, shard_index: int) -> None:
    r = await get_redis()
    if r is None:
        return
    try:
        await r.set(f"room:{room_id}", shard_index, ex=ROOM_KEY_TTL_SECONDS)
    except Exception as e:
        _logger.warning("set_room_shard failed: %s", e)


async def get_room_shard(room_id: str) -> int | None:
    r = await get_redis()
    if r is None:
        return None
    try:
        val = await r.get(f"room:{room_id}")
        return int(val) if val is not None else None
    except Exception as e:
        _logger.warning("get_room_shard failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Stage 2 — matchmaking queue
# ---------------------------------------------------------------------------

async def enqueue(user_id: int, elo: int, entered: float, token: str) -> bool:
    """Add a player to the Redis sorted set (score=elo). Returns True on
    success, False if Redis is unavailable (caller uses in-memory fallback)."""
    r = await get_redis()
    if r is None:
        return False
    try:
        member = json.dumps({"user_id": user_id, "elo": elo,
                             "entered": entered, "token": token})
        await r.zadd(MATCHMAKING_QUEUE_KEY, {member: elo})
        return True
    except Exception as e:
        _logger.warning("enqueue failed: %s", e)
        return False


async def remove_from_queue(user_id: int) -> None:
    """Remove all entries for user_id from the sorted set."""
    r = await get_redis()
    if r is None:
        return
    try:
        members = await r.zrange(MATCHMAKING_QUEUE_KEY, 0, -1)
        to_remove = [m for m in members
                     if json.loads(m).get("user_id") == user_id]
        if to_remove:
            await r.zrem(MATCHMAKING_QUEUE_KEY, *to_remove)
    except Exception as e:
        _logger.warning("remove_from_queue failed: %s", e)


async def get_queue_entries() -> list[dict]:
    """Return all entries in the queue as dicts, ordered by ELO ascending.
    Returns empty list if Redis is unavailable."""
    r = await get_redis()
    if r is None:
        return []
    try:
        members = await r.zrange(MATCHMAKING_QUEUE_KEY, 0, -1)
        return [json.loads(m) for m in members]
    except Exception as e:
        _logger.warning("get_queue_entries failed: %s", e)
        return []


async def clear_queue() -> None:
    """Delete the entire matchmaking queue key. Used in tests and on
    service startup to avoid stale entries from a previous run."""
    r = await get_redis()
    if r is None:
        return
    try:
        await r.delete(MATCHMAKING_QUEUE_KEY)
    except Exception as e:
        _logger.warning("clear_queue failed: %s", e)


# ---------------------------------------------------------------------------
# Stage 3 — game state persistence
# ---------------------------------------------------------------------------

GAME_KEY_TTL_SECONDS = 7200  # 2 hours — well beyond any realistic game length


async def save_game_state(room_id: str, snapshot: dict) -> None:
    """Persist a full game snapshot. Called on every state event."""
    r = await get_redis()
    if r is None:
        return
    try:
        await r.set(f"game:{room_id}", json.dumps(snapshot), ex=GAME_KEY_TTL_SECONDS)
    except Exception as e:
        _logger.warning("save_game_state failed: %s", e)


async def load_game_state(room_id: str) -> dict | None:
    """Return the snapshot dict, or None if not found / Redis unavailable."""
    r = await get_redis()
    if r is None:
        return None
    try:
        val = await r.get(f"game:{room_id}")
        return json.loads(val) if val is not None else None
    except Exception as e:
        _logger.warning("load_game_state failed: %s", e)
        return None


async def delete_game_state(room_id: str) -> None:
    """Remove the snapshot when a game ends — keeps Redis clean."""
    r = await get_redis()
    if r is None:
        return
    try:
        await r.delete(f"game:{room_id}")
    except Exception as e:
        _logger.warning("delete_game_state failed: %s", e)
