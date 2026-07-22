# AGENTS.md

## Project purpose

Kong-Fu Chess is a real-time chess-style game with animated sprites and a live HUD.
The goal is to keep game logic correct and the architecture clean and modular.
It runs solo (text or graphical) or online 2-player over a websocket server, all through one entry point.

## Core architecture

- Entry point: `main.py` — `python main.py [--gui | --online | --server]`; no flags = text mode (default, matches historical behavior), `--gui` = solo graphical, `--online` = online 2-player client, `--server` = start the game server. Each flag just imports and calls the existing `main()` from the module below — no logic is duplicated in `main.py` itself.
- Graphical entry point (solo), also runnable directly: `main_ui.py`
- Graphical entry point (online), also runnable directly: `main_network.py`
- Game engine: `engine/game_engine.py`
- Move scheduler: `engine/move_scheduler.py`
- Board model: `model/board.py`
- Game state: `model/game_state.py`
- Event bus: `model/event_bus.py`
- Move records and notation: `model/move_record.py`, `model/notation.py`
- Move validation: `rules/rule_engine.py`, `rules/moves/`
- Real-time settling: `realtime/move_settler.py`
- Input parsing: `iofiles/board_parser.py`
- View layer: `view/`
- Server (online play): `server/`
- Client (online play): `client/`

## View layer

- `view/screen.py` — main render loop, subscribes to game events
- `view/render_state.py` — DTOs: `RenderState`, `PieceRenderInfo`, `MoveArrow`, `PlayerRenderInfo`
- `view/constants.py` — `CELL`, `HUD_W`, `FPS`, `PieceState` enum, colors
- `view/img.py` — image wrapper with alpha/black-mask blending
- `view/loaders/sprite_loader.py` — loads and caches piece sprites by token and `PieceState`
- `view/renderers/board_renderer.py` — draws board, pieces, cooldown bars, highlights
- `view/renderers/hud_renderer.py` — draws player info, scores, captured pieces, move history
- `view/renderers/overlay_renderer.py` — draws start screen and game over screen
- `view/renderers/history_renderer.py` — draws move history with algebraic notation

## Observer / event pattern

- `GameState.events` is an `EventBus`
- `MoveSettler` emits: `piece_settled`, `game_over`
- `GameEngine` emits: `selection_changed`, `restarted`
- `Screen` subscribes to all events and sets `_needs_redraw = True`
- `to_render_state()` is only called when `_needs_redraw` is True
- Sprite animations, cooldown bars, and clock always update every frame

## DTO bridge rule

- `GameState.to_render_state()` is the ONLY place model data is converted to view data
- No model imports anywhere in `view/` except `screen.py` which holds `GameState` and `GameEngine` references

## Online play (server/client)

The server is layered into four packages under `server/` — `core/` (infrastructure), `auth/`, `matchmaking/`, `game/` — plus a thin `server/app.py` that only wires them together. No package's `__init__.py` re-exports anything; every import names the exact submodule (`server.auth.service`, not `server.auth`) — this matters because tests monkeypatch these modules by dotted string path (e.g. `patch("server.auth.service.login", ...)`), which silently breaks if an import instead resolves to a package's `__init__.py`.

- `server/core/database.py` — sqlite setup and queries (was `server/db.py`). `DB_PATH` is relative to `core/`'s own directory plus `..`, so it still resolves to the same `server/chess.db` regardless of this file's location.
- `server/core/protocol.py` — shared wire-protocol constants (message-type strings, color strings) plus `HOST`/`PORT`/`MATCHMAKING_PORT`. Both `server/` and `client/` import from here instead of repeating raw literals.
- `server/auth/service.py` — register/login/password hashing/tokens/`update_elo` (was `server/auth.py`).
- `server/auth/cli.py` — command-line register/login tool (was `server/cli.py`).
- `server/matchmaking/queue.py` — the matchmaking queue and ELO window math (was `server/matchmaking.py`). ELO window starts at ±100 and widens by 100 every 15s (capped at ±500); 60s overall timeout.
- `server/matchmaking/handler.py` — `matchmaking_handler`, the websocket entry point for the matchmaking port (extracted out of `server/app.py`).
- `server/game/session.py` — `GameSession` (was `server/game_session.py`): module-level `register_session`/`get_session` registry keyed by `room_id`, populated by matchmaking when a match is made (or by `server/game/rooms.py` when a room is created). `register_session` also stamps `session.room_id` and wires up the per-room event logger (see `server/core/game_logger.py`) — the one shared place both entry points go through, so logging isn't set up twice. `assign_color(connection, user_id)` is **identity-based** (checked against `white_user_id`/`black_user_id`), not slot-order — this is what lets a reconnecting player get their own color back and rejects an unrelated or duplicate connection. It returns a `Role` (see below), not a raw string. `GRACE_SECONDS = 20`: on disconnect a forfeit timer is scheduled; reconnecting before it fires cancels it and triggers a full resync (`to_render_state()` resent as-is, no diffing); if it fires, it's a technical loss and `update_elo` is called. The tick loop is untouched by connection count — it only stops on `state.game_over`, so the game keeps running in real time while a player is disconnected. Do not change this without an explicit decision, since it affects UX (a disconnected player can lose material/position while away).
- **Stage E — rooms and viewers**: `GameSession(allow_viewers=True)` (only set by `server/game/rooms.py`, never by matchmaking) makes `assign_color` treat the first two *distinct* joining `user_id`s as the open white/black slots instead of requiring them pre-assigned, and treats anyone after that as a read-only viewer (`Role.VIEWER`, appended to `self.viewers`, never `self.connections`) instead of rejecting them. `on_connect`/`on_disconnect` and `broadcast()` are viewer-aware (viewers get every broadcast state/game_over, never get a forfeit timer). `server/game/rooms.py` has no `join_room` function — joining a room is already exactly what `game_handler` + `assign_color` do via `get_session(room_id)`, so a second function would just duplicate that path.
- `server/core/protocol.py`'s `Role` enum (`Role.WHITE`/`Role.BLACK`/`Role.VIEWER`, `.value` is the wire string) is what `assign_color` returns and what the new `MSG_TYPE_ROLE` message carries — it exists so "what role did this connection get" is reasoned about as a type internally, while `Connection.color`/`self.connections` keys stay the plain `"w"`/`"b"` strings every other message shape already uses. Every connection (matchmaking or room, player or viewer) gets a `{"type": "role", "role": ...}` message right after `assign_color` succeeds, before `waiting`/`start`/resync.
- `server/core/game_logger.py` — `attach_event_logger(events, room_id)` subscribes to all four event names emitted anywhere in the codebase (`piece_settled`, `selection_changed`, `restarted`, `game_over`) and writes one line per event to `server/logs/<room_id>.log`. Called only from `register_session`.
- `server/game/connection.py` — `Connection` (was `server/connection.py`), constructed with a `user_id` already resolved from the token; it does not pick its own color, `GameSession.assign_color` does. Also holds `game_handler`, the websocket entry point for the game port (extracted out of `server/app.py`, colocated with the `Connection` it constructs). If `room_id` is missing from the query string, `game_handler` calls `server.game.rooms.create_room()` to make one — this is how a client "creates a room" over the wire, there's no separate port/message for it. `Connection.is_viewer` short-circuits `_handle_message` to a no-op, blocking `click`/`jump`/`restart` for viewers in one place.
- `server/app.py` — thin entry point only: `init_db()`, then `websockets.serve(...)` for both ports using the handlers above. Do not put protocol/game/matchmaking logic back into this file.
- `client/network_client.py` — pure transport only: a background thread runs the blocking `websockets.sync.client` receive loop and pushes parsed messages onto a `queue.Queue`; `poll()` drains it from the main thread once per frame. Sends go straight through `ws.send()` from the main thread (thread-safe by design). No game logic belongs in this file. Every sent/received message is logged to `client/logs/client.log` via this module's `log_sent`/`log_received`, which `main_network.py` reuses for its own raw handshake sockets (matchmaking/create-room/join-room) so there's one client logger, not several.
- `client/render_state_codec.py` — one pure function, `render_state_from_dict`: the inverse of the server's `dataclasses.asdict(RenderState)`. No class, no state.
- `client/network_session.py` — **the key pattern**: `NetworkSession` is passed to `Screen` as *both* the `engine` and `state` constructor argument (the two roles' attribute/method names never collide), so `Screen` is reused completely unmodified for online play — it never learns it isn't talking to a local `GameEngine`/`GameState`. Do not create a parallel `NetworkScreen`-style class again; if `Screen` needs new capabilities for online play, extend `Screen` itself (carefully, tests-first) rather than duplicating its render/input loop.
  - Board flip for the black player (`7 - col`, `7 - row`) happens *only* inside `NetworkSession` — once for rendering (pieces, selection, pending-move arrows) and once for click input, right after `BoardMapper.pixel_to_cell`. `Screen` stays entirely color-agnostic; do not add color awareness to it.
  - `NetworkSession.wait()` unconditionally emits its redraw event on every call (not only when a new server message arrived), so `Screen` always takes its full-refresh branch and never reaches the per-frame cooldown-interpolation branch. `cooldowns`/`rest_type` are therefore kept permanently empty dicts by design — this is intentional (Option A: render the server's `RenderState` as-is, no local interpolation). Do not "fix" this by reconstructing an expiry timestamp from `cooldown_fill`; that reintroduces a redundant round-trip and silently depends on the client's rest-duration constants matching the server's.
  - `_send` (click/jump) and `restart` are no-ops unless `self._color` is `COLOR_WHITE`/`COLOR_BLACK` — a viewer's role string is `"viewer"`, so this quietly disables all input without `Screen` ever needing to know about roles.
- `main_network.py` offers a 3-way menu after login: quick match (unchanged `_connect_matchmaking`), create room, or join room by ID. Create/join both go through `_peek_role`, a throwaway blocking connection to the game port that reads the `role` message (and, for a fresh room, the `room_id` from `waiting`) then closes; the real `NetworkClient` reconnects on the same room_id/token right after. That close-then-reconnect is deliberately just a normal Stage D reconnect (identity-based, grace-window) — not special-cased.
- `view/screen.py`'s `_on_mouse` has **no manual `cv2.getWindowImageRect` rescale**. The installed `websockets`/OpenCV Win32 HighGUI backend already remaps mouse coordinates back into the original image space when the window is resized; a manual rescale on top of that double-scales and corrupts click positions as soon as the window is resized away from its initial size. Do not re-add it.

## Important domain rules

- Board coordinates use `Position(col, row)`
- Movement timing: moves are scheduled and settled after a delay based on distance
- Jump mechanics are separate from normal movement and may intercept incoming moves
- Friendly pieces targeting the same square: loser bounces back to `from_pos`
- Promotion: pawn becomes queen on the last row
- Capturing a king ends the game

## What to preserve

- click/select behavior
- movement legality for all piece types
- blocked-path rules
- capture and jump/interception rules
- promotion behavior
- game-over behavior
- event bus subscribers must survive `restart()` — bus is preserved across state reset

## Testing

```bash
pytest -q                          # all tests
pytest tests/ui_tests/ -v          # UI tests only
pytest tests/integration/ -q       # integration tests only
pytest --cov=core --cov-report=html  # coverage report
```

Two standalone scripts also exercise online-play server logic end-to-end against a real running server, outside of pytest:

- `python verify_stage_c.py` — matchmaking: token auth, ELO window widening, timeout, concurrent matching, room_id assignment.
- `python verify_stage_d_manual.py` — interactive: registers two throwaway accounts, matches them, and lets you type `dc a`/`dc b` (disconnect) and `rc a`/`rc b` (reconnect) to watch the grace window, resync, forfeit, and ELO update happen live.

## Notes for future AI assistants

- Do not remove or bypass the EventBus — it is the communication layer between engine and UI
- Do not import model classes inside `view/` renderers — use `RenderState` DTOs only
- Cooldown fills and clock are updated every frame in `screen.py` — do not move this to `to_render_state()`
- Asset path: `view/assets/pieces_mine/{token}/states/{state}/sprites/{n}.png`
- Token format: `'wP'`, `'bK'` — color + kind, not unique across board
- Cooldown keys are `(col, row)` tuples, not token strings
- `server/` and `client/` are not model/view internals — do not import `server.*` from `model/`, `engine/`, `rules/`, or `view/`; the dependency direction is one-way, server/client depend on the core game, never the reverse
