# Kong Fu Chess

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![pytest](https://img.shields.io/badge/Tests-pytest-green)
![Coverage](https://img.shields.io/badge/Coverage-HTML%20Report-brightgreen)

Kong Fu Chess is a Python-based real-time chess-style game with animated sprites, a live HUD, and a clean modular architecture. It can be played solo on one machine, or online against another player over a real-time-matched, ELO-based server.

## Overview

- board parsing and validation
- movement logic for king, rook, bishop, queen, knight, and pawn
- real-time timed movement, jumps, captures, and promotions
- animated piece sprites with idle, move, jump, and rest states
- cooldown bars and live clock rendered every frame
- move history with algebraic notation
- observer/event pattern — UI reacts to game events, not polling
- **online 2-player mode**: account/ELO based matchmaking, one authoritative game server, automatic board-perspective flip, disconnect grace window with technical loss + ELO update
- unit, integration, and UI test suites

## Project Structure

- `engine/` - game engine and move scheduler
- `model/` - board, pieces, game state, event bus, move records, notation
- `realtime/` - move settler and motion data
- `rules/` - movement strategies and rule engine
- `view/` - renderers, sprite loader, screen, constants, render state DTOs
- `iofiles/` - board parser and printer
- `input/` - board mapper
- `server/` - websocket game server: auth, ELO matchmaking, per-room `GameSession`, disconnect/reconnect handling
- `client/` - network transport and a thin adapter that lets the existing `Screen` drive networked play unmodified
- `tests/` - unit, integration, and UI test suites
- `main.py` - **the one entry point** — `python main.py [--gui | --online | --server]` (see below)
- `main_ui.py` - single-player graphical mode (also runnable directly)
- `main_network.py` - online 2-player graphical client (also runnable directly)
- `verify_stage_c.py` / `verify_stage_d_manual.py` - standalone scripts that exercise matchmaking and disconnect/reconnect against a real running server

## Architecture Highlights

**Observer pattern** — `GameState` holds an `EventBus`. `MoveSettler` and `GameEngine` fire events (`piece_settled`, `game_over`, `selection_changed`, `restarted`). `Screen` subscribes and sets `_needs_redraw` — no polling.

**DTO layer** — `GameState.to_render_state()` is the only bridge between model and view. All renderers work with `RenderState` — zero model imports in the view layer.

**Real-time rendering** — sprite animations, cooldown bars, and the clock update every frame. Game state is only rebuilt when an event fires.

**Factory pattern** — movement strategies are configured via JSON, new strategies can be added without changing core code.

**Networked play reuses the same Screen** — `view/screen.py`'s `Screen` class is the single rendering/input loop for both single-player and online play. For online play, `client/network_session.py`'s `NetworkSession` is passed in as *both* the `engine` and `state` argument Screen expects (their method/attribute names never overlap), so `Screen` renders and handles clicks exactly as it always did — it has no idea it's talking to a network client instead of a local `GameEngine`/`GameState`. Board flip for the black player, and all click-to-network translation, happens entirely inside `NetworkSession` — `Screen` stays color-agnostic.

**Server-authoritative state** — the server sends a full `RenderState` snapshot (not a delta) on every relevant event and roughly every 96ms besides, so the client always renders exactly what the server says, with no local physics/cooldown interpolation.

**Per-room sessions** — matchmaking creates one `GameSession` per match and registers it by `room_id`; the game-port connection handler looks a session up by `room_id` from the connecting client, so many matches can run concurrently on one server.

## Requirements

- Python 3.10+
- opencv-python
- numpy
- pytest
- pytest-cov
- websockets

## Installation

```bash
pip install -r requirements.txt
```

## One Entry Point

Everything runs through `main.py`:

```bash
python main.py            # solo, text mode
python main.py --gui      # solo, graphical
python main.py --online   # online 2-player client
python main.py --server   # start the game server
```

(`main_ui.py`, `main_network.py`, and `server/app.py` still work if run directly by name — `main.py` is just a thin router on top, no logic duplicated.)

## Play Solo

```bash
python main.py --gui
```

1. Click anywhere to start
2. Click a piece to select it
3. Click a destination to move
4. Double-click a piece to jump
5. Press `R` to restart, `Q` to quit

## Play Online (2 players)

**1. Start the server** (leave running in its own terminal):

```bash
python main.py --server
```

This starts the game server on `ws://localhost:8765` and the matchmaking server on `ws://localhost:8766`.

**2. Start a client, once per player, each in its own terminal:**

```bash
python main.py --online
```

You'll be prompted to `[1] Register` or `[2] Login` with a username/password. Once authenticated, the client joins the matchmaking queue automatically.

**3. Matchmaking:** players are matched by ELO (new accounts start at 1200). The acceptable ELO gap starts at ±100 and widens by 100 every 15 seconds (up to ±500); if no match is found within 60 seconds, the client is disconnected with a timeout error.

**4. Playing:** once matched, each client opens its own board window automatically, connected to that match's own game session. Each window only accepts moves for its own color, and shows the board from that player's perspective — the black player sees their own pieces at the bottom, same as sitting across a real board.

**5. Disconnects:** if a client disconnects mid-game, the game keeps running for the remaining player. The disconnected player has **20 seconds** to reconnect (same account) and get a full board resync with no lost state. If they don't return in time, it's recorded as a technical loss and both players' ELO is updated.

## Run Tests

```bash
pytest -q
```

## Generate Coverage Report

```bash
pytest --cov=core --cov-report=html
```

## Verification Scripts

Two standalone scripts exercise the online-play server logic end-to-end against a real running server, outside of pytest:

- `python verify_stage_c.py` — matchmaking: token auth, ELO window widening, timeout, concurrent matching, room_id assignment.
- `python verify_stage_d_manual.py` — interactive: registers two throwaway accounts, matches them, and lets you type `dc a`/`dc b` (disconnect) and `rc a`/`rc b` (reconnect) to watch the grace window, resync, forfeit, and ELO update happen live.

## Status

- Test suite: passing
- UI tests: passing
- Online play: matchmaking, per-room sessions, disconnect/reconnect, ELO updates — implemented and verified
- Coverage report: available in `htmlcov/`
