# Kong Fu Chess

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![pytest](https://img.shields.io/badge/Tests-pytest-green)
![Coverage](https://img.shields.io/badge/Coverage-HTML%20Report-brightgreen)

Kong Fu Chess is a Python-based real-time chess-style game with animated sprites, a live HUD, and a clean modular architecture.

## Overview

- board parsing and validation
- movement logic for king, rook, bishop, queen, knight, and pawn
- real-time timed movement, jumps, captures, and promotions
- animated piece sprites with idle, move, jump, and rest states
- cooldown bars and live clock rendered every frame
- move history with algebraic notation
- observer/event pattern — UI reacts to game events, not polling
- unit, integration, and UI test suites

## Project Structure

- `engine/` - game engine and move scheduler
- `model/` - board, pieces, game state, event bus, move records, notation
- `realtime/` - move settler and motion data
- `rules/` - movement strategies and rule engine
- `view/` - renderers, sprite loader, screen, constants, render state DTOs
- `iofiles/` - board parser and printer
- `input/` - board mapper
- `tests/` - unit, integration, and UI test suites
- `main_ui.py` - graphical entry point
- `main.py` - text entry point

## Architecture Highlights

**Observer pattern** — `GameState` holds an `EventBus`. `MoveSettler` and `GameEngine` fire events (`piece_settled`, `game_over`, `selection_changed`, `restarted`). `Screen` subscribes and sets `_needs_redraw` — no polling.

**DTO layer** — `GameState.to_render_state()` is the only bridge between model and view. All renderers work with `RenderState` — zero model imports in the view layer.

**Real-time rendering** — sprite animations, cooldown bars, and the clock update every frame. Game state is only rebuilt when an event fires.

**Factory pattern** — movement strategies are configured via JSON, new strategies can be added without changing core code.

## Requirements

- Python 3.10+
- opencv-python
- numpy
- pytest
- pytest-cov

## Installation

```bash
pip install opencv-python numpy pytest pytest-cov
```

## Run the Game

```bash
python main_ui.py
```

## Run Tests

```bash
pytest -q
```

## Generate Coverage Report

```bash
pytest --cov=core --cov-report=html
```

## How to Play

1. Run `main_ui.py`
2. Click anywhere to start
3. Click a piece to select it
4. Click a destination to move
5. Double-click a piece to jump
6. Press `R` to restart, `Q` to quit

## Status

- Test suite: passing
- UI tests: passing (47 tests)
- Coverage report: available in `htmlcov/`
