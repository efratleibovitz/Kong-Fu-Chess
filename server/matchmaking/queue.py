"""server/matchmaking/queue.py"""

import asyncio
import json
import time
import uuid

from server.core.protocol import COLOR_WHITE, COLOR_BLACK, MSG_TYPE_ERROR, MSG_TYPE_MATCH_FOUND

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
    entry = {
        "ws": ws,
        "user_id": user_id,
        "elo": elo,
        "entered": time.monotonic(),
        "matched": False,
        "task": None,
    }
    task = asyncio.create_task(_check_loop(entry))
    entry["task"] = task
    async with _lock:
        _queue.append(entry)
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
                    if entry in _queue:
                        _queue.remove(entry)
                    await entry["ws"].send(json.dumps({"type": MSG_TYPE_ERROR, "reason": "timeout"}))
                return

            window = _current_window(entry["entered"])
            candidate = None
            for other in _queue:
                if other is entry:
                    continue
                if other["matched"]:
                    continue
                if abs(other["elo"] - entry["elo"]) <= window:
                    cand_window = _current_window(other["entered"])
                    if abs(entry["elo"] - other["elo"]) <= cand_window:
                        candidate = other
                        break

            if candidate is None:
                continue

            entry["matched"] = True
            candidate["matched"] = True
            if entry in _queue:
                _queue.remove(entry)
            if candidate in _queue:
                _queue.remove(candidate)

        # outside lock: cancel candidate's task, create session, notify both
        if candidate["task"] is not None:
            candidate["task"].cancel()

        from server.game.session import GameSession, register_session
        room_id = str(uuid.uuid4())
        session = GameSession(
            white_user_id=entry["user_id"],
            white_elo=entry["elo"],
            black_user_id=candidate["user_id"],
            black_elo=candidate["elo"],
        )
        register_session(room_id, session)

        await entry["ws"].send(json.dumps({"type": MSG_TYPE_MATCH_FOUND, "color": COLOR_WHITE, "room_id": room_id}))
        await candidate["ws"].send(json.dumps({"type": MSG_TYPE_MATCH_FOUND, "color": COLOR_BLACK, "room_id": room_id}))
        return
