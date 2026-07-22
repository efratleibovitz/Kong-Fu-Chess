"""
verify_stage_c.py
-----------------
Standalone verification script for Stage C (Matchmaking).
Does NOT touch any existing code. Calls the real production functions.
Uses a temporary SQLite DB so server/chess.db is never polluted.

Run:
    python verify_stage_c.py

Each check prints PASS or FAIL with a short reason.
Final line: ALL CHECKS PASSED  or  X CHECK(S) FAILED
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import asyncio
import json
import os
import tempfile
import time

# -- redirect db to a temp file before any server imports --------------------
import server.core.database as _db
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
_db.DB_PATH = _tmp.name

import server.matchmaking.queue as matchmaking
from server.auth.service import register, login_with_session, get_user_id_by_token
from server.core.database import init_db, get_user_by_id, update_user_elo, get_user_by_username

# ---------------------------------------------------------------------------
# result tracking
# ---------------------------------------------------------------------------
_results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, reason: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    _results.append((name, passed, reason))
    suffix = f"  <- {reason}" if (reason and not passed) else ""
    print(f"  [{status}] {name}{suffix}")


# ---------------------------------------------------------------------------
# shared fakes
# ---------------------------------------------------------------------------
class MockWS:
    def __init__(self, name: str = ""):
        self.name = name
        self.sent: list[dict] = []
        self.closed = False

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))

    async def close(self) -> None:
        self.closed = True

    def of_type(self, t: str) -> list[dict]:
        return [m for m in self.sent if m.get("type") == t]


class MockGameSession:
    def __init__(self, **kwargs):
        pass


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def setup_user(username: str, password: str, elo: int) -> tuple[int, str]:
    init_db()
    try:
        user_id = register(username, password)
    except ValueError:
        user_id = get_user_by_username(username)["id"]
    update_user_elo(user_id, elo)
    result = login_with_session(username, password)
    assert result is not None
    _, token = result
    return user_id, token


def patch_session(monkeypatch_dict: dict) -> None:
    import server.game.session as gs
    monkeypatch_dict["_orig"] = gs.GameSession
    gs.GameSession = MockGameSession


def unpatch_session(monkeypatch_dict: dict) -> None:
    import server.game.session as gs
    gs.GameSession = monkeypatch_dict["_orig"]


async def run_with_fast_interval(coro, interval=0.05):
    old = matchmaking.CHECK_INTERVAL_SECONDS
    matchmaking.CHECK_INTERVAL_SECONDS = interval
    try:
        return await coro
    finally:
        matchmaking.CHECK_INTERVAL_SECONDS = old


# ===========================================================================
# CHECK 1 -- invalid token is rejected immediately
# ===========================================================================
async def check_invalid_token() -> None:
    print("\n-- Check 1: invalid token -> unauthorized --")
    from server.matchmaking.handler import matchmaking_handler

    class FakeRequest:
        path = "/matchmaking?token=totally_forged_token"

    class FakeWS:
        request = FakeRequest()
        sent: list = []
        closed = False
        async def send(self, data): self.sent.append(json.loads(data))
        async def close(self): self.closed = True

    ws = FakeWS()
    await matchmaking_handler(ws)

    rejected = any(m.get("reason") == "unauthorized" for m in ws.sent)
    check("forged token -> unauthorized error sent", rejected,
          f"sent={ws.sent}")
    check("socket closed after rejection", ws.closed)


# ===========================================================================
# CHECK 2 -- valid token resolves to correct user_id and real ELO from DB
# ===========================================================================
async def check_token_resolves() -> None:
    print("\n-- Check 2: valid token -> correct user_id + ELO from DB --")
    user_id, token = setup_user("verify_alice", "pw1", elo=1350)

    resolved_id = get_user_id_by_token(token)
    check("token resolves to correct user_id", resolved_id == user_id,
          f"got {resolved_id}, expected {user_id}")

    user = get_user_by_id(resolved_id)
    check("ELO fetched from DB (not client-supplied)", user["elo"] == 1350,
          f"got {user['elo']}")


# ===========================================================================
# CHECK 3 -- two clients within +-100 ELO match immediately
# ===========================================================================
async def check_immediate_match() -> None:
    print("\n-- Check 3: two clients within +-100 ELO -> immediate match --")
    mp: dict = {}
    patch_session(mp)
    matchmaking._queue.clear()

    user_id_a, _ = setup_user("verify_bob",   "pw2", elo=1200)
    user_id_b, _ = setup_user("verify_carol", "pw3", elo=1250)
    ws_a, ws_b = MockWS("bob"), MockWS("carol")

    async def run():
        await asyncio.gather(
            matchmaking.add_to_queue(ws_a, user_id_a, 1200),
            matchmaking.add_to_queue(ws_b, user_id_b, 1250),
        )

    try:
        await asyncio.wait_for(run_with_fast_interval(run()), timeout=2.0)
    except asyncio.TimeoutError:
        pass
    finally:
        matchmaking._queue.clear()
        unpatch_session(mp)

    ma, mb = ws_a.of_type("match_found"), ws_b.of_type("match_found")
    check("player A received match_found", len(ma) == 1, f"sent={ws_a.sent}")
    check("player B received match_found", len(mb) == 1, f"sent={ws_b.sent}")
    if ma and mb:
        check("colors are w and b", {ma[0]["color"], mb[0]["color"]} == {"w", "b"})
        check("both share the same room_id", ma[0]["room_id"] == mb[0]["room_id"])
        check("no duplicate match_found for A", len(ma) == 1)
        check("no duplicate match_found for B", len(mb) == 1)


# ===========================================================================
# CHECK 4 -- 250 ELO apart -> no match at t=0 (window = +-100)
# ===========================================================================
async def check_no_early_match() -> None:
    print("\n-- Check 4: 250 ELO apart -> no match at t=0 --")
    mp: dict = {}
    patch_session(mp)
    matchmaking._queue.clear()
    old = matchmaking.CHECK_INTERVAL_SECONDS
    matchmaking.CHECK_INTERVAL_SECONDS = 0.05

    ws_a, ws_b = MockWS("dave"), MockWS("eve")
    user_id_a, _ = setup_user("verify_dave", "pw4", elo=1200)
    user_id_b, _ = setup_user("verify_eve",  "pw5", elo=1450)

    entry_a = {"ws": ws_a, "user_id": user_id_a, "elo": 1200,
               "entered": time.monotonic(), "matched": False, "task": None}
    entry_b = {"ws": ws_b, "user_id": user_id_b, "elo": 1450,
               "entered": time.monotonic(), "matched": False, "task": None}
    matchmaking._queue.extend([entry_a, entry_b])

    task_a = asyncio.create_task(matchmaking._check_loop(entry_a))
    entry_a["task"] = task_a
    task_b = asyncio.create_task(matchmaking._check_loop(entry_b))
    entry_b["task"] = task_b

    await asyncio.sleep(0.12)   # one interval -- should NOT match

    check("no match at t=0 with 250 ELO gap",
          not entry_a["matched"] and not entry_b["matched"])
    check("no match_found sent to A", ws_a.of_type("match_found") == [])
    check("no match_found sent to B", ws_b.of_type("match_found") == [])

    for t in [task_a, task_b]:
        if not t.done():
            t.cancel()
    await asyncio.gather(task_a, task_b, return_exceptions=True)
    matchmaking._queue.clear()
    matchmaking.CHECK_INTERVAL_SECONDS = old
    unpatch_session(mp)


# ===========================================================================
# CHECK 5 -- widening window: 250 apart matches after 30s elapsed
# ===========================================================================
async def check_widening_window() -> None:
    print("\n-- Check 5: 250 ELO apart -> match after window widens to +-300 --")
    mp: dict = {}
    patch_session(mp)
    matchmaking._queue.clear()
    old = matchmaking.CHECK_INTERVAL_SECONDS
    matchmaking.CHECK_INTERVAL_SECONDS = 0.05

    ws_a, ws_b = MockWS("frank"), MockWS("grace")
    user_id_a, _ = setup_user("verify_frank", "pw6", elo=1200)
    user_id_b, _ = setup_user("verify_grace", "pw7", elo=1450)

    entry_a = {"ws": ws_a, "user_id": user_id_a, "elo": 1200,
               "entered": time.monotonic() - 31, "matched": False, "task": None}
    entry_b = {"ws": ws_b, "user_id": user_id_b, "elo": 1450,
               "entered": time.monotonic() - 31, "matched": False, "task": None}
    matchmaking._queue.extend([entry_a, entry_b])

    task_a = asyncio.create_task(matchmaking._check_loop(entry_a))
    entry_a["task"] = task_a
    task_b = asyncio.create_task(matchmaking._check_loop(entry_b))
    entry_b["task"] = task_b

    await asyncio.sleep(0.15)

    check("match found after window widens to +-300",
          entry_a["matched"] and entry_b["matched"],
          f"a={entry_a['matched']} b={entry_b['matched']}")
    check("match_found sent to A", len(ws_a.of_type("match_found")) == 1)
    check("match_found sent to B", len(ws_b.of_type("match_found")) == 1)
    check("candidate task was cancelled",
          task_a.cancelled() or task_b.cancelled())

    for t in [task_a, task_b]:
        if not t.done():
            t.cancel()
    await asyncio.gather(task_a, task_b, return_exceptions=True)
    matchmaking._queue.clear()
    matchmaking.CHECK_INTERVAL_SECONDS = old
    unpatch_session(mp)


# ===========================================================================
# CHECK 6 -- timeout: client with no match after 60s gets error
# ===========================================================================
async def check_timeout() -> None:
    print("\n-- Check 6: no opponent within +-500 -> timeout after 60s --")
    mp: dict = {}
    patch_session(mp)
    matchmaking._queue.clear()
    old = matchmaking.CHECK_INTERVAL_SECONDS
    matchmaking.CHECK_INTERVAL_SECONDS = 0.05

    ws_a = MockWS("henry")
    user_id_a, _ = setup_user("verify_henry", "pw8", elo=1200)

    entry_a = {"ws": ws_a, "user_id": user_id_a, "elo": 1200,
               "entered": time.monotonic() - 61, "matched": False, "task": None}
    matchmaking._queue.append(entry_a)

    task_a = asyncio.create_task(matchmaking._check_loop(entry_a))
    entry_a["task"] = task_a

    await asyncio.sleep(0.15)

    check("timeout error sent",
          ws_a.sent == [{"type": "error", "reason": "timeout"}],
          f"sent={ws_a.sent}")
    check("entry removed from queue", entry_a not in matchmaking._queue)
    check("entry marked matched=True", entry_a["matched"])
    check("task finished (not cancelled)", task_a.done() and not task_a.cancelled())

    matchmaking._queue.clear()
    matchmaking.CHECK_INTERVAL_SECONDS = old
    unpatch_session(mp)


# ===========================================================================
# CHECK 7 -- no double-match: 3 clients race, exactly one pair matched
# ===========================================================================
async def check_no_double_match() -> None:
    print("\n-- Check 7: 3 concurrent clients -> exactly one match pair, no duplicates --")
    mp: dict = {}
    patch_session(mp)
    matchmaking._queue.clear()
    old = matchmaking.CHECK_INTERVAL_SECONDS
    matchmaking.CHECK_INTERVAL_SECONDS = 0.05

    ws_a, ws_b, ws_c = MockWS("i"), MockWS("j"), MockWS("k")
    user_id_a, _ = setup_user("verify_i", "pw9",  elo=1200)
    user_id_b, _ = setup_user("verify_j", "pw10", elo=1210)
    user_id_c, _ = setup_user("verify_k", "pw11", elo=1220)

    entries, tasks = [], []
    for ws, uid, elo in [(ws_a, user_id_a, 1200),
                         (ws_b, user_id_b, 1210),
                         (ws_c, user_id_c, 1220)]:
        e = {"ws": ws, "user_id": uid, "elo": elo,
             "entered": time.monotonic(), "matched": False, "task": None}
        entries.append(e)
        matchmaking._queue.append(e)

    for e in entries:
        t = asyncio.create_task(matchmaking._check_loop(e))
        e["task"] = t
        tasks.append(t)

    await asyncio.sleep(0.2)

    all_sent = ws_a.sent + ws_b.sent + ws_c.sent
    match_msgs   = [m for m in all_sent if m.get("type") == "match_found"]
    timeout_msgs = [m for m in all_sent if m.get("type") == "error"]

    check("exactly 2 match_found messages total", len(match_msgs) == 2,
          f"got {len(match_msgs)}")
    if len(match_msgs) == 2:
        check("colors are w and b",
              {m["color"] for m in match_msgs} == {"w", "b"})
        check("both match_found share same room_id",
              match_msgs[0]["room_id"] == match_msgs[1]["room_id"])
    check("no spurious timeout messages", timeout_msgs == [],
          f"got {timeout_msgs}")
    check("exactly 2 entries marked matched",
          sum(1 for e in entries if e["matched"]) == 2,
          f"matched={[e['matched'] for e in entries]}")

    for t in tasks:
        if not t.done():
            t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    matchmaking._queue.clear()
    matchmaking.CHECK_INTERVAL_SECONDS = old
    unpatch_session(mp)


# ===========================================================================
# MAIN
# ===========================================================================
async def main() -> int:
    print("=" * 60)
    print("  Stage C - Matchmaking Verification")
    print("=" * 60)

    await check_invalid_token()
    await check_token_resolves()
    await check_immediate_match()
    await check_no_early_match()
    await check_widening_window()
    await check_timeout()
    await check_no_double_match()

    print("\n" + "=" * 60)
    failed = [name for name, passed, _ in _results if not passed]
    if failed:
        print(f"  {len(failed)} CHECK(S) FAILED: {', '.join(failed)}")
    else:
        print(f"  ALL {len(_results)} CHECKS PASSED")
    print("=" * 60)

    try:
        os.unlink(_tmp.name)
    except OSError:
        pass

    return len(failed)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
