# AGENTS.md

## Project purpose
This repository is a text-driven chess-style game called Kong-Fu Chess.
The main goal is to preserve the game logic from the basic reference version while keeping the refactored architecture clean and modular.

## Core architecture
- Entry point: main.py
- Game engine: engine/game_engine.py
- Board model: model/board.py
- Position model: model/position.py
- Runtime state: model/game_state.py
- Move validation and rules: rules/
- Input parsing: iofiles/board_parser.py
- Board rendering: iofiles/board_printer.py
- Text tests: texttests/
- Automated tests: tests/

## Important domain rules
- The engine is event-driven: click, jump, wait, and print board are the main interaction points.
- Board coordinates use a Position object with col/row fields.
- The Position class also exposes x/y properties for backward compatibility.
- Movement timing is important: moves are scheduled and settled after a delay based on distance.
- Jump mechanics are separate from normal movement and may intercept incoming moves.
- Promotion changes a pawn into a queen on the last row.
- Capturing a king ends the game.

## What to preserve
When changing code, preserve these behaviors unless a test proves they are wrong:
- click/select behavior
- movement legality for king, rook, bishop, queen, knight, and pawn
- blocked-path rules
- capture rules
- jump and interception rules
- promotion behavior
- game-over behavior

## Preferred development approach
- Prefer small, focused changes.
- If changing gameplay, add or update a regression test first.
- Keep architecture improvements separate from gameplay fixes.
- Avoid rewriting game rules just to make the code look different.

## Testing
Run tests from the repository root:
- pytest -q

Useful targeted tests:
- pytest tests/integration/test_game.py -q
- pytest tests/integration/test_game_jump.py -q
- pytest tests/integration/test_main.py -q
- pytest tests/integration/test_boss_cases.py -q

## Notes for future AI assistants
- Do not assume the refactored architecture is wrong just because it looks different from the basic version.
- Check the behavior against tests before changing logic.
- The most important files to inspect first are:
  - engine/game_engine.py
  - model/game_state.py
  - rules/rule_engine.py
  - rules/moves/*
  - iofiles/board_parser.py
