"""client/network_client.py

Background-thread websocket transport. The GUI loop (cv2.imshow/waitKey)
runs on the main thread and must never block on network I/O, so the
socket read loop runs on its own thread and hands messages to the main
thread through a queue.Queue - the only safe bridge between them needed
here, no manual locks required.

Every sent/received message is logged to client/logs/client.log via
log_sent/log_received (except "state" broadcasts, which fire every tick
and aren't a discrete action worth a log line), which main_network.py also
reuses for the raw matchmaking/room handshake sockets it opens outside of
this class - one logger/file for the whole client instead of a second
logging setup.
"""

import json
import logging
import os
import queue
import threading
import websockets.sync.client

from server.core.protocol import MSG_TYPE_CLICK, MSG_TYPE_JUMP, MSG_TYPE_RESTART, MSG_TYPE_STATE

_LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_logger = logging.getLogger("client.network")
_logger.setLevel(logging.INFO)
_logger.propagate = False
if not _logger.handlers:
    _handler = logging.FileHandler(os.path.join(_LOG_DIR, "client.log"))
    _handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _logger.addHandler(_handler)


def log_sent(msg: dict) -> None:
    _logger.info("send %s", msg)


def log_received(msg: dict) -> None:
    if msg.get("type") == MSG_TYPE_STATE:
        # "state" broadcasts fire every ~100ms during play (every tick) -
        # not a meaningful discrete action, so skip logging them entirely.
        # Every other (small, infrequent) message type logs in full.
        return
    _logger.info("recv %s", msg)


class NetworkClient:
    def __init__(self, url: str):
        self._url = url
        self._ws = None
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        with websockets.sync.client.connect(self._url) as ws:
            self._ws = ws
            for raw in ws:
                msg = json.loads(raw)
                log_received(msg)
                self._queue.put(msg)

    def poll(self) -> list[dict]:
        messages = []
        while True:
            try:
                messages.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return messages

    def _send(self, payload: dict):
        log_sent(payload)
        self._ws.send(json.dumps(payload))

    def send_click(self, col: int, row: int):
        self._send({"type": MSG_TYPE_CLICK, "col": col, "row": row})

    def send_jump(self, col: int, row: int):
        self._send({"type": MSG_TYPE_JUMP, "col": col, "row": row})

    def send_restart(self):
        self._send({"type": MSG_TYPE_RESTART})
