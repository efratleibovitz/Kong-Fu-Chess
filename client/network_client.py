"""client/network_client.py

Background-thread websocket transport. The GUI loop (cv2.imshow/waitKey)
runs on the main thread and must never block on network I/O, so the
socket read loop runs on its own thread and hands messages to the main
thread through a queue.Queue - the only safe bridge between them needed
here, no manual locks required.
"""

import json
import queue
import threading
import websockets.sync.client


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
                self._queue.put(json.loads(raw))

    def poll(self) -> list[dict]:
        messages = []
        while True:
            try:
                messages.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return messages

    def send_click(self, col: int, row: int):
        self._ws.send(json.dumps({"type": "click", "col": col, "row": row}))

    def send_jump(self, col: int, row: int):
        self._ws.send(json.dumps({"type": "jump", "col": col, "row": row}))

    def send_restart(self):
        self._ws.send(json.dumps({"type": "restart"}))
