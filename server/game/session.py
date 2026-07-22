
"""server/game/session.py

GameSession owns a single game's GameState + GameEngine.
"""

import asyncio
import dataclasses
import json
from enum import Enum

from model.board import Board
from model.game_state import GameState
from engine.game_engine import GameEngine
from server.core.protocol import (
    COLOR_WHITE,
    COLOR_BLACK,
    MSG_TYPE_STATE,
    MSG_TYPE_WAITING,
    MSG_TYPE_START,
    MSG_TYPE_GAME_OVER,
)

TICK_MS = 16
TICKS_PER_BROADCAST = 6
GRACE_SECONDS = 20

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


_sessions: dict[str, "GameSession"] = {}


def register_session(room_id: str, session: "GameSession") -> None:
    _sessions[room_id] = session


def get_session(room_id: str) -> "GameSession | None":
    return _sessions.get(room_id)


class GameSession:
    def __init__(
        self,
        white_user_id: int | None = None,
        white_elo: int | None = None,
        black_user_id: int | None = None,
        black_elo: int | None = None,
    ):
        state = GameState(Board([row[:] for row in DEFAULT_BOARD]))
        state.player_names = {COLOR_WHITE: 'White', COLOR_BLACK: 'Black'}
        self.state = state
        self.engine = GameEngine(state)

        self.connections: dict[str, "Connection"] = {}
        self._tick_task: asyncio.Task | None = None
        self._tick_counter = 0
        self._game_started = False
        self._forfeit_tasks: dict[str, asyncio.Task] = {}

        self.white_user_id = white_user_id
        self.white_elo = white_elo
        self.black_user_id = black_user_id
        self.black_elo = black_elo

        state.events.subscribe('piece_settled', self._on_state_event)
        state.events.subscribe('selection_changed', self._on_state_event)
        state.events.subscribe('game_over', self._on_game_over)

    def assign_color(self, connection, user_id: int) -> str | None:
        """Identity-based, not slot-order: a reconnecting player gets back
        the color that matches their user_id, and an unrelated/duplicate
        connection is rejected instead of stealing the open slot."""
        if user_id == self.white_user_id:
            color = COLOR_WHITE
        elif user_id == self.black_user_id:
            color = COLOR_BLACK
        else:
            return None
        if color in self.connections:
            return None
        self.connections[color] = connection
        return color

    def on_connect(self, connection):
        task = self._forfeit_tasks.pop(connection.color, None)
        if task is not None:
            task.cancel()

    def on_disconnect(self, connection):
        color = None
        for c, conn in list(self.connections.items()):
            if conn is connection:
                color = c
                del self.connections[c]
        if color is None or not self._game_started or self.state.game_over:
            return
        # Game keeps running for the remaining player during the grace
        # window (real-time, non-turn-based game) - see _tick_loop, which
        # is untouched by connection count and only stops on game_over.
        self._forfeit_tasks[color] = asyncio.create_task(self._forfeit_after_grace(color))

    async def _forfeit_after_grace(self, color: str):
        try:
            await asyncio.sleep(GRACE_SECONDS)
        except asyncio.CancelledError:
            return
        if self.state.game_over:
            return
        winner = COLOR_BLACK if color == COLOR_WHITE else COLOR_WHITE
        self.state.game_over = True
        self.state.loser = color
        self.state.events.emit('game_over', loser=color)
        self._apply_elo_update(winner_color=winner, loser_color=color)

    def _apply_elo_update(self, winner_color: str, loser_color: str):
        winner_id = self.white_user_id if winner_color == COLOR_WHITE else self.black_user_id
        loser_id = self.white_user_id if loser_color == COLOR_WHITE else self.black_user_id
        if winner_id is None or loser_id is None:
            return
        from server.auth.service import update_elo
        update_elo(winner_id, loser_id)

    async def on_connected(self, connection):
        if not self._game_started:
            if len(self.connections) == 1:
                await connection.send({"type": MSG_TYPE_WAITING})
            elif len(self.connections) == 2:
                self._game_started = True
                for color, conn in self.connections.items():
                    await conn.send({"type": MSG_TYPE_START, "color": color})
                self._start_tick_loop()
        else:
            # Reconnect after the game already began: to_render_state()
            # is always a full snapshot, never a delta, so resync is just
            # resending it - no separate diffing logic needed.
            await self._send_resync(connection)

    async def _send_resync(self, connection):
        render_state = self.state.to_render_state()
        payload = json.dumps({"type": MSG_TYPE_STATE, "data": dataclasses.asdict(render_state)}, cls=_EnumSafeEncoder)
        await connection.send_raw(payload)

    async def broadcast(self, message: dict):
        payload = json.dumps(message, cls=_EnumSafeEncoder)
        for conn in list(self.connections.values()):
            await conn.send_raw(payload)

    def _on_state_event(self, **_kwargs):
        asyncio.create_task(self._broadcast_state())

    def _on_game_over(self, loser=None, **_kwargs):
        asyncio.create_task(self._broadcast_state())
        asyncio.create_task(self.broadcast({"type": MSG_TYPE_GAME_OVER, "loser": loser}))

    async def _broadcast_state(self):
        render_state = self.state.to_render_state()
        await self.broadcast({"type": MSG_TYPE_STATE, "data": dataclasses.asdict(render_state)})

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
                await self._broadcast_state()
