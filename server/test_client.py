"""server/test_client.py

Minimal manual test client. Run two of these in two terminals against
server/app.py and type commands to drive the game:

    click <col> <row>
    jump <col> <row>
    restart
    quit

Every message received from the server is printed as-is (except 'tick',
which is printed compactly since it fires ~10x/second).
"""

import asyncio
import json
import sys
import websockets

URI = "ws://localhost:8765"


async def receiver(ws):
    async for raw in ws:
        msg = json.loads(raw)
        if msg.get("type") == "tick":
            print(f"\r[tick] clock_ms={msg['clock_ms']}", end="", flush=True)
        else:
            print(f"\n<< {msg}")


async def sender(ws):
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()

        if cmd == "click" and len(parts) == 3:
            await ws.send(json.dumps({"type": "click", "col": int(parts[1]), "row": int(parts[2])}))
        elif cmd == "jump" and len(parts) == 3:
            await ws.send(json.dumps({"type": "jump", "col": int(parts[1]), "row": int(parts[2])}))
        elif cmd == "restart":
            await ws.send(json.dumps({"type": "restart"}))
        elif cmd == "quit":
            return
        else:
            print("commands: click <col> <row> | jump <col> <row> | restart | quit")


async def main():
    async with websockets.connect(URI) as ws:
        print(f"connected to {URI}")
        recv_task = asyncio.create_task(receiver(ws))
        await sender(ws)
        recv_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())