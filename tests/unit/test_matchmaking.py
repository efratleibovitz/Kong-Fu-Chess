"""tests/unit/test_matchmaking.py"""

import asyncio
import json
import time
import pytest
import server.core.game_logger as game_logger
import server.matchmaking.queue as matchmaking
from server.matchmaking.queue import _check_loop


class MockWS:
    def __init__(self):
        self.sent = []

    async def send(self, data):
        self.sent.append(json.loads(data))

    async def close(self):
        pass


def _make_entry(ws, user_id, elo, elapsed=0):
    return {
        "ws": ws,
        "user_id": user_id,
        "elo": elo,
        "entered": time.monotonic() - elapsed,
        "matched": False,
        "task": None,
    }


@pytest.fixture(autouse=True)
def clean_queue():
    matchmaking._queue.clear()
    yield
    matchmaking._queue.clear()


@pytest.fixture(autouse=True)
def mock_redis_queue(monkeypatch):
    """Stub out all Redis queue calls so tests run without a live Redis."""
    import server.core.redis_client as rc
    async def _noop_enqueue(user_id, elo, entered, token): return False
    async def _noop_remove(user_id): pass
    async def _noop_clear(): pass
    monkeypatch.setattr(rc, "enqueue", _noop_enqueue)
    monkeypatch.setattr(rc, "remove_from_queue", _noop_remove)
    monkeypatch.setattr(rc, "clear_queue", _noop_clear)


@pytest.fixture(autouse=True)
def fast_interval(monkeypatch):
    monkeypatch.setattr(matchmaking, "CHECK_INTERVAL_SECONDS", 0.01)


@pytest.fixture(autouse=True)
def mock_create_remote_session(monkeypatch):
    """Matchmaking no longer creates GameSession in-process (it can't -
    once Game Server is split into separate shard containers, that
    in-memory dict lives on the shard, not here). It calls
    create_remote_session() instead, which opens a real network
    connection to whichever shard owns the room - stub that out here so
    matchmaking's matching logic can be tested without a live shard."""
    async def _fake(room_id, white_user_id, white_elo, black_user_id, black_elo):
        return None
    monkeypatch.setattr("server.matchmaking.session_dispatch.create_remote_session", _fake)


@pytest.fixture(autouse=True)
def redirect_log_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(game_logger, "LOG_DIR", str(tmp_path))


class TestMatchmaking:
    def test_immediate_match_within_100(self):
        async def run():
            ws_a, ws_b = MockWS(), MockWS()
            a = _make_entry(ws_a, 1, 1200)
            b = _make_entry(ws_b, 2, 1250)

            matchmaking._queue.extend([a, b])

            task_a = asyncio.create_task(_check_loop(a))
            a["task"] = task_a
            task_b = asyncio.create_task(_check_loop(b))
            b["task"] = task_b

            await asyncio.sleep(0.05)

            assert a["matched"] and b["matched"]
            assert any(m["type"] == "match_found" and m["color"] == "w" for m in ws_a.sent)
            assert any(m["type"] == "match_found" and m["color"] == "b" for m in ws_b.sent)
            # exactly one of the two tasks was cancelled
            assert task_a.cancelled() or task_b.cancelled()
            assert not (task_a.cancelled() and task_b.cancelled())

        asyncio.run(run())

    def test_no_match_before_window_widens(self):
        async def run():
            ws_a, ws_b = MockWS(), MockWS()
            # 250 apart — needs ±300 window (30s elapsed), only 10s in → ±200
            a = _make_entry(ws_a, 1, 1200, elapsed=10)
            b = _make_entry(ws_b, 2, 1450, elapsed=10)

            matchmaking._queue.extend([a, b])

            task_a = asyncio.create_task(_check_loop(a))
            a["task"] = task_a
            task_b = asyncio.create_task(_check_loop(b))
            b["task"] = task_b

            await asyncio.sleep(0.05)

            assert not a["matched"] and not b["matched"]
            assert ws_a.sent == [] and ws_b.sent == []

            task_a.cancel()
            task_b.cancel()
            await asyncio.gather(task_a, task_b, return_exceptions=True)

        asyncio.run(run())

    def test_match_after_window_widens(self):
        async def run():
            ws_a, ws_b = MockWS(), MockWS()
            # 250 apart — needs ±300 window, both 31s in → ±300
            a = _make_entry(ws_a, 1, 1200, elapsed=31)
            b = _make_entry(ws_b, 2, 1450, elapsed=31)

            matchmaking._queue.extend([a, b])

            task_a = asyncio.create_task(_check_loop(a))
            a["task"] = task_a
            task_b = asyncio.create_task(_check_loop(b))
            b["task"] = task_b

            await asyncio.sleep(0.05)

            assert a["matched"] and b["matched"]
            assert any(m["type"] == "match_found" for m in ws_a.sent + ws_b.sent)

        asyncio.run(run())

    def test_timeout_sends_error_and_removes(self):
        async def run():
            ws_a = MockWS()
            a = _make_entry(ws_a, 1, 1200, elapsed=61)

            matchmaking._queue.append(a)

            task_a = asyncio.create_task(_check_loop(a))
            a["task"] = task_a

            await asyncio.sleep(0.05)

            assert a["matched"]
            assert a not in matchmaking._queue
            assert ws_a.sent == [{"type": "error", "reason": "timeout"}]
            assert task_a.done() and not task_a.cancelled()

        asyncio.run(run())

    def test_candidate_task_cancelled_after_match(self):
        """Verify the losing side's _check_loop task is actually cancelled."""
        async def run():
            ws_a, ws_b = MockWS(), MockWS()
            a = _make_entry(ws_a, 1, 1200)
            b = _make_entry(ws_b, 2, 1200)

            matchmaking._queue.extend([a, b])

            task_a = asyncio.create_task(_check_loop(a))
            a["task"] = task_a
            task_b = asyncio.create_task(_check_loop(b))
            b["task"] = task_b

            await asyncio.sleep(0.05)

            # whichever task was the candidate gets cancelled
            assert task_a.cancelled() or task_b.cancelled()
            # the winner returned normally (done but not cancelled)
            winner_task = task_b if task_a.cancelled() else task_a
            assert winner_task.done() and not winner_task.cancelled()

        asyncio.run(run())

    def test_no_double_match_three_concurrent_clients(self):
        """3 clients race via asyncio.gather — exactly one match_found pair, no duplicates."""
        async def run():
            ws_a, ws_b, ws_c = MockWS(), MockWS(), MockWS()
            a = _make_entry(ws_a, 1, 1200)
            b = _make_entry(ws_b, 2, 1210)
            c = _make_entry(ws_c, 3, 1220)

            matchmaking._queue.extend([a, b, c])

            task_a = asyncio.create_task(_check_loop(a))
            a["task"] = task_a
            task_b = asyncio.create_task(_check_loop(b))
            b["task"] = task_b
            task_c = asyncio.create_task(_check_loop(c))
            c["task"] = task_c

            await asyncio.gather(
                asyncio.sleep(0.05),
                return_exceptions=True
            )

            all_sent = ws_a.sent + ws_b.sent + ws_c.sent
            match_found_msgs = [m for m in all_sent if m["type"] == "match_found"]
            timeout_msgs = [m for m in all_sent if m["type"] == "error"]

            # exactly two match_found (one per matched player)
            assert len(match_found_msgs) == 2
            colors = {m["color"] for m in match_found_msgs}
            assert colors == {"w", "b"}
            # both share the same room_id
            assert match_found_msgs[0]["room_id"] == match_found_msgs[1]["room_id"]
            # no spurious timeouts
            assert timeout_msgs == []
            # unmatched client's task still running (not cancelled, not done)
            unmatched_ws = next(
                ws for ws, entry in [(ws_a, a), (ws_b, b), (ws_c, c)]
                if not entry["matched"]
            )
            assert unmatched_ws.sent == []

            # cleanup
            for t in [task_a, task_b, task_c]:
                if not t.done():
                    t.cancel()
            await asyncio.gather(task_a, task_b, task_c, return_exceptions=True)

        asyncio.run(run())
