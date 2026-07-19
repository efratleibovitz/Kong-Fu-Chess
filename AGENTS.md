# AGENTS.md

## Project purpose
Kong-Fu Chess is a real-time chess-style game with animated sprites and a live HUD.
The goal is to keep game logic correct and the architecture clean and modular.

## Core architecture
- Graphical entry point: `main_ui.py`
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

## Notes for future AI assistants
- Do not remove or bypass the EventBus — it is the communication layer between engine and UI
- Do not import model classes inside `view/` renderers — use `RenderState` DTOs only
- Cooldown fills and clock are updated every frame in `screen.py` — do not move this to `to_render_state()`
- Asset path: `view/assets/pieces_mine/{token}/states/{state}/sprites/{n}.png`
- Token format: `'wP'`, `'bK'` — color + kind, not unique across board
- Cooldown keys are `(col, row)` tuples, not token strings
