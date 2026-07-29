"""verify_stage_d_manual.py

Interactive Stage D check against your real running server (server.app on
ws://localhost:8765 / 8766). Registers two throwaway accounts, matches
them, connects both to the game session, then lets you disconnect and
reconnect one of them by hand - the same thing as closing a game window
and reopening it - while printing every message each side receives live.

Run: venv\\Scripts\\python.exe verify_stage_d_manual.py

Try:
  dc b          -> disconnect player B (simulates closing their window)
  rc b          -> reconnect B to the SAME room within the 20s grace window
                    -> watch for a "state" resync message, no game_over
  dc b, wait 20s, then do nothing -> watch A receive game_over (loser=b)
"""

import json
import queue
import threading
import time
import uuid

import websockets.sync.client

from server.auth.service import register, login_with_session

MATCHMAKING_URL = "ws://localhost:8766"
GAME_URL = "ws://localhost:8765"


class Player:
    def __init__(self, name: str, token: str):
        self.name = name
        self.token = token
        self.ws = None
        self.room_id = None
        self.color = None
        self.messages: queue.Queue = queue.Queue()
        self._last_state_print = 0.0

    def matchmake(self):
        with websockets.sync.client.connect(f"{MATCHMAKING_URL}?token={self.token}") as ws:
            for raw in ws:
                msg = json.loads(raw)
                if msg.get("type") == "match_found":
                    self.room_id = msg["room_id"]
                    self.color = msg["color"]
                    return
                if msg.get("type") == "error":
                    raise RuntimeError(f"matchmaking error: {msg}")

    def connect_game(self):
        url = f"{GAME_URL}?room_id={self.room_id}&token={self.token}"
        self.ws = websockets.sync.client.connect(url)
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def _recv_loop(self):
        ws = self.ws
        try:
            for raw in ws:
                msg = json.loads(raw)
                if msg.get("type") == "state":
                    now = time.monotonic()
                    if now - self._last_state_print < 2.0:
                        continue
                    self._last_state_print = now
                    print(f"[{self.name}] state  clock_ms={msg['data']['clock_ms']}")
                else:
                    print(f"[{self.name}] {msg}")
        except Exception as e:
            print(f"[{self.name}] connection closed ({e})")

    def disconnect(self):
        if self.ws is not None:
            self.ws.close()
            print(f"[{self.name}] socket closed")


def main():
    print("Registering two throwaway accounts and matching them...")
    uname_a = f"manual_a_{uuid.uuid4().hex[:6]}"
    uname_b = f"manual_b_{uuid.uuid4().hex[:6]}"
    register(uname_a, "pw")
    register(uname_b, "pw")
    _, token_a = login_with_session(uname_a, "pw")
    _, token_b = login_with_session(uname_b, "pw")

    a = Player("A", token_a)
    b = Player("B", token_b)

    t1 = threading.Thread(target=a.matchmake)
    t2 = threading.Thread(target=b.matchmake)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print(f"Matched. room_id={a.room_id}  A={a.color}  B={b.color}")

    a.connect_game()
    b.connect_game()

    print(
        "\nCommands:\n"
        "  dc a | dc b   - disconnect that player (simulates closing their window)\n"
        "  rc a | rc b   - reconnect that player to the SAME room\n"
        "  quit          - exit\n"
        "Messages from both players print live as they arrive.\n"
    )

    players = {"a": a, "b": b}
    while True:
        try:
            cmd = input("> ").strip().lower().split()
        except EOFError:
            break
        if not cmd:
            continue
        if cmd[0] == "quit":
            break
        if len(cmd) == 2 and cmd[1] in players:
            if cmd[0] == "dc":
                players[cmd[1]].disconnect()
                continue
            if cmd[0] == "rc":
                players[cmd[1]].connect_game()
                print(f"[{cmd[1]}] reconnect attempted")
                continue
        print("unknown command")

    a.disconnect()
    b.disconnect()


if __name__ == "__main__":
    main()
