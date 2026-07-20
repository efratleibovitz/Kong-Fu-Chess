# import asyncio
# import dataclasses
# import json
# from model.board import Board
# from model.game_state import GameState
# from engine.game_engine import GameEngine

# DEFAULT_BOARD = [
#     ['bR', 'bN', 'bB', 'bK', 'bQ', 'bB', 'bN', 'bR'],
#     ['bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP'],
#     ['.', '.', '.', '.', '.', '.', '.', '.'],
#     ['.', '.', '.', '.', '.', '.', '.', '.'],
#     ['.', '.', '.', '.', '.', '.', '.', '.'],
#     ['.', '.', '.', '.', '.', '.', '.', '.'],
#     ['wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP'],
#     ['wR', 'wN', 'wB', 'wK', 'wQ', 'wB', 'wN', 'wR'],
# ]

# TICK_MS = 16
# TICK_BROADCAST_EVERY = 6   # ~100ms


# class GameSession:
#     def __init__(self):
#         self._connections = []          # max 2, in join order
#         self._colors = ['w', 'b']
#         self.state = GameState(Board([row[:] for row in DEFAULT_BOARD]))
#         self.state.player_names = {'w': 'White', 'b': 'Black'}
#         self.engine = GameEngine(self.state)
#         self._tick_task = None
#         self._subscribe_events()

#     # ------------------------------------------------------------------ #
#     # connection management                                                #
#     # ------------------------------------------------------------------ #

#     def is_full(self) -> bool:
#         return len(self._connections) >= 2

#     async def add_connection(self, conn):
#         self._connections.append(conn)
#         if len(self._connections) == 1:
#             await conn.send_json({"type": "waiting"})
#         else:
#             for c, color in zip(self._connections, self._colors):
#                 await c.send_json({"type": "start", "color": color})
#             await self._broadcast_state()
#             self._tick_task = asyncio.create_task(self._tick_loop())

#     async def remove_connection(self, conn):
#         if conn in self._connections:
#             self._connections.remove(conn)
#         if self._tick_task and len(self._connections) < 2:
#             self._tick_task.cancel()
#             self._tick_task = None

#     def color_of(self, conn) -> str:
#         idx = self._connections.index(conn)
#         return self._colors[idx]

#     # ------------------------------------------------------------------ #
#     # tick loop                                                            #
#     # ------------------------------------------------------------------ #

#     async def _tick_loop(self):
#         counter = 0
#         while True:
#             await asyncio.sleep(TICK_MS / 1000)
#             self.engine.wait(TICK_MS)
#             counter += 1
#             if counter >= TICK_BROADCAST_EVERY:
#                 counter = 0
#                 await self._broadcast_tick()

#     # ------------------------------------------------------------------ #
#     # event bus → broadcast                                               #
#     # ------------------------------------------------------------------ #

#     def _subscribe_events(self):
#         for event in ('piece_settled', 'selection_changed', 'game_over'):
#             self.state.events.subscribe(event, self._on_game_event)

#     def _on_game_event(self, **kwargs):
#         asyncio.get_event_loop().call_soon_threadsafe(
#             lambda: asyncio.ensure_future(self._broadcast_state())
#         )

#     async def _broadcast_state(self):
#         rs = self.state.to_render_state()
#         msg = {"type": "state", "data": dataclasses.asdict(rs)}
#         if self.state.game_over:
#             await self._broadcast({"type": "game_over", "loser": self.state.loser})
#         await self._broadcast(msg)

#     async def _broadcast_tick(self):
#         await self._broadcast({"type": "tick", "clock_ms": self.state.clock})

#     async def _broadcast(self, msg: dict):
#         text = json.dumps(msg)
#         for conn in list(self._connections):
#             await conn.send_raw(text)


"""server/game_session.py

GameSession owns a single game's GameState + GameEngine (Stage A: exactly
one session, no rooms yet).
"""

import asyncio
import dataclasses
import json
from enum import Enum

from model.board import Board
from model.game_state import GameState
from engine.game_engine import GameEngine

TICK_MS = 16
TICKS_PER_BROADCAST = 6

DEFAULT_BOARD = [
    ['bR', 'bN', 'bB', 'bK', 'bQ', 'bB', 'bN', 'bR'],
    ['bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP'],
    ['wR', 'wN', 'wB', 'wK', 'wQ', 'wB', 'wN', 'wR'],
]


class _EnumSafeEncoder(json.JSONEncoder):
    """RenderState carries a PieceState Enum field. dataclasses.asdict()
    does NOT convert nested Enum values, so plain json.dumps() crashes.
    This encoder fixes that without touching view/render_state.py."""
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class GameSession:
    def __init__(
        self,
        white_user_id: int | None = None,
        white_elo: int | None = None,
        black_user_id: int | None = None,
        black_elo: int | None = None,
    ):
        state = GameState(Board([row[:] for row in DEFAULT_BOARD]))
        state.player_names = {'w': 'White', 'b': 'Black'}
        self.state = state
        self.engine = GameEngine(state)

        self.connections: dict[str, "Connection"] = {}
        self._tick_task: asyncio.Task | None = None
        self._tick_counter = 0

        self.white_user_id = white_user_id
        self.white_elo = white_elo
        self.black_user_id = black_user_id
        self.black_elo = black_elo

        state.events.subscribe('piece_settled', self._on_state_event)
        state.events.subscribe('selection_changed', self._on_state_event)
        state.events.subscribe('game_over', self._on_game_over)

    def is_full(self) -> bool:
        return len(self.connections) >= 2

    def assign_color(self, connection) -> str:
        color = 'w' if 'w' not in self.connections else 'b'
        self.connections[color] = connection
        return color

    def remove(self, connection):
        for color, conn in list(self.connections.items()):
            if conn is connection:
                del self.connections[color]

    async def on_connected(self, connection):
        if len(self.connections) == 1:
            await connection.send({"type": "waiting"})
        elif len(self.connections) == 2:
            for color, conn in self.connections.items():
                await conn.send({"type": "start", "color": color})
            self._start_tick_loop()

    async def broadcast(self, message: dict):
        payload = json.dumps(message, cls=_EnumSafeEncoder)
        for conn in list(self.connections.values()):
            await conn.send_raw(payload)

    def _on_state_event(self, **_kwargs):
        asyncio.create_task(self._broadcast_state())

    def _on_game_over(self, loser=None, **_kwargs):
        asyncio.create_task(self._broadcast_state())
        asyncio.create_task(self.broadcast({"type": "game_over", "loser": loser}))

    async def _broadcast_state(self):
        render_state = self.state.to_render_state()
        await self.broadcast({"type": "state", "data": dataclasses.asdict(render_state)})

    def _start_tick_loop(self):
        if self._tick_task is None:
            self._tick_task = asyncio.create_task(self._tick_loop())

    async def _tick_loop(self):
        await self._broadcast_state()
        while not self.state.game_over:
            await asyncio.sleep(TICK_MS / 1000)
            self.engine.wait(TICK_MS)
            self._tick_counter += 1
            if self._tick_counter >= TICKS_PER_BROADCAST:
                self._tick_counter = 0
                await self.broadcast({"type": "tick", "clock_ms": self.state.clock})