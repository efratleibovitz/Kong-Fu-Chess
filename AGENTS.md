# AGENTS.md

## Project purpose

Kong-Fu Chess is a real-time chess-style game with animated sprites and a live HUD.
The goal is to keep game logic correct and the architecture clean and modular.
It runs solo (`main_ui.py`) or online 2-player over a websocket server (`main_network.py` + `server/`).

## Core architecture

- Graphical entry point (solo): `main_ui.py`
- Graphical entry point (online): `main_network.py`
- Text entry point: `main.py`
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

- `server/app.py` — two websocket servers: game port (8765) and matchmaking port (8766). `game_handler` resolves both `room_id` and `token` from the connection's query string and looks up the match's `GameSession` via `get_session(room_id)` — there is no single global session; never reintroduce one.
- `server/game_session.py` — module-level `register_session`/`get_session` registry keyed by `room_id`, populated by matchmaking when a match is made. `assign_color(connection, user_id)` is **identity-based** (checked against `white_user_id`/`black_user_id`), not slot-order — this is what lets a reconnecting player get their own color back and rejects an unrelated or duplicate connection. `GRACE_SECONDS = 20`: on disconnect a forfeit timer is scheduled; reconnecting before it fires cancels it and triggers a full resync (`to_render_state()` resent as-is, no diffing); if it fires, it's a technical loss and `server/auth.py`'s `update_elo` is called. The tick loop is untouched by connection count — it only stops on `state.game_over`, so the game keeps running in real time while a player is disconnected. Do not change this without an explicit decision, since it affects UX (a disconnected player can lose material/position while away).
- `server/matchmaking.py` — ELO window starts at ±100 and widens by 100 every 15s (capped at ±500); 60s overall timeout.
- `server/connection.py` — `Connection` is constructed with a `user_id` already resolved from the token; it does not pick its own color, `GameSession.assign_color` does.
- `client/network_client.py` — pure transport only: a background thread runs the blocking `websockets.sync.client` receive loop and pushes parsed messages onto a `queue.Queue`; `poll()` drains it from the main thread once per frame. Sends go straight through `ws.send()` from the main thread (thread-safe by design). No game logic belongs in this file.
- `client/render_state_codec.py` — one pure function, `render_state_from_dict`: the inverse of the server's `dataclasses.asdict(RenderState)`. No class, no state.
- `client/network_session.py` — **the key pattern**: `NetworkSession` is passed to `Screen` as *both* the `engine` and `state` constructor argument (the two roles' attribute/method names never collide), so `Screen` is reused completely unmodified for online play — it never learns it isn't talking to a local `GameEngine`/`GameState`. Do not create a parallel `NetworkScreen`-style class again; if `Screen` needs new capabilities for online play, extend `Screen` itself (carefully, tests-first) rather than duplicating its render/input loop.
  - Board flip for the black player (`7 - col`, `7 - row`) happens *only* inside `NetworkSession` — once for rendering (pieces, selection, pending-move arrows) and once for click input, right after `BoardMapper.pixel_to_cell`. `Screen` stays entirely color-agnostic; do not add color awareness to it.
  - `NetworkSession.wait()` unconditionally emits its redraw event on every call (not only when a new server message arrived), so `Screen` always takes its full-refresh branch and never reaches the per-frame cooldown-interpolation branch. `cooldowns`/`rest_type` are therefore kept permanently empty dicts by design — this is intentional (Option A: render the server's `RenderState` as-is, no local interpolation). Do not "fix" this by reconstructing an expiry timestamp from `cooldown_fill`; that reintroduces a redundant round-trip and silently depends on the client's rest-duration constants matching the server's.
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
