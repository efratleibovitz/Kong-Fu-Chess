"""server/matchmaking/queue.py

Matchmaking queue backed by a Redis sorted set (score = ELO) so the queue
survives a matchmaking service restart. Falls back to the in-memory list
transparently when Redis is unavailable - behaviour is identical either way.

Redis layout:
  key   : matchmaking:queue  (sorted set)
  member: JSON {user_id, elo, entered, token}
  score : elo

The asyncio lock + matched/task fields on each entry are still in-memory
(they guard the per-process check loop, not cross-process state). That is
correct: this service runs as a single replica. The Redis store gives us
durability on restart, not distributed coordination.
"""

import asyncio
import json
import time
import uuid

from server.core.protocol import COLOR_WHITE, COLOR_BLACK, MsgType, Message, FIELD_REASON, Reason
from server.core import redis_client as _rc

# In-memory fallback list - used when Redis is unavailable.
_queue: list[dict] = []
_lock = asyncio.Lock()

CHECK_INTERVAL_SECONDS = 5
QUEUE_TIMEOUT_SECONDS = 60

INITIAL_ELO_WINDOW = 100
ELO_EXPANSION_INTERVAL_SECONDS = 15
ELO_EXPANSION_STEP = 100
MAX_ELO_WINDOW = 500


def _current_window(entered: float) -> int:
    elapsed = time.monotonic() - entered
    expansions = int(elapsed // ELO_EXPANSION_INTERVAL_SECONDS)
    return min(INITIAL_ELO_WINDOW + expansions * ELO_EXPANSION_STEP, MAX_ELO_WINDOW)


async def add_to_queue(ws, user_id: int, elo: int) -> None:
    entered = time.monotonic()
    entry = {
        "ws": ws,
        "user_id": user_id,
        "elo": elo,
        "entered": entered,
        "matched": False,
        "task": None,
    }

    # Write to Redis; fall back to in-memory list if Redis is down.
    redis_ok = await _rc.enqueue(user_id, elo, entered, token="")
    if not redis_ok:
        async with _lock:
            _queue.append(entry)

    task = asyncio.create_task(_check_loop(entry))
    entry["task"] = task
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _check_loop(entry: dict) -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

        if entry["matched"]:
            return

        async with _lock:
            elapsed = time.monotonic() - entry["entered"]

            if elapsed >= QUEUE_TIMEOUT_SECONDS:
                if not entry["matched"]:
                    entry["matched"] = True
                    _queue_remove(entry)
                    await _rc.remove_from_queue(entry["user_id"])
                    await entry["ws"].send(json.dumps(
                        Message(MsgType.ERROR, {FIELD_REASON: Reason.TIMEOUT.value}).to_dict()
                    ))
                return

            candidate = await _find_candidate(entry)
            if candidate is None:
                continue

            entry["matched"] = True
            candidate["matched"] = True
            _queue_remove(entry)
            _queue_remove(candidate)
            await _rc.remove_from_queue(entry["user_id"])
            await _rc.remove_from_queue(candidate["user_id"])

        # outside lock: cancel candidate task, create session, notify both
        if candidate["task"] is not None:
            candidate["task"].cancel()

        from server.matchmaking.session_dispatch import create_remote_session
        room_id = str(uuid.uuid4())
        await create_remote_session(
            room_id,
            white_user_id=entry["user_id"],
            white_elo=entry["elo"],
            black_user_id=candidate["user_id"],
            black_elo=candidate["elo"],
        )

        await entry["ws"].send(json.dumps(
            Message(MsgType.MATCH_FOUND, {"color": COLOR_WHITE, "room_id": room_id}).to_dict()
        ))
        await candidate["ws"].send(json.dumps(
            Message(MsgType.MATCH_FOUND, {"color": COLOR_BLACK, "room_id": room_id}).to_dict()
        ))
        return


async def _find_candidate(entry: dict) -> dict | None:
    """Find a compatible opponent. Checks the in-memory list first (always
    populated when Redis is down, and also populated for the current process
    when Redis is up). Redis entries from a previous run that survived a
    restart are not in _queue - those players' websockets are gone, so they
    cannot be matched anyway. The Redis store gives durability for the queue
    length/visibility, not for cross-restart matching."""
    window = _current_window(entry["entered"])
    for other in _queue:
        if other is entry:
            continue
        if other["matched"]:
            continue
        if abs(other["elo"] - entry["elo"]) <= window:
            cand_window = _current_window(other["entered"])
            if abs(entry["elo"] - other["elo"]) <= cand_window:
                return other
    return None


def _queue_remove(entry: dict) -> None:
    """Remove from in-memory list if present."""
    if entry in _queue:
        _queue.remove(entry)
