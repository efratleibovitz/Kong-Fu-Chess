# Kong Fu Chess

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![pytest](https://img.shields.io/badge/Tests-189%20passed-green)
![Coverage](https://img.shields.io/badge/Coverage-90%25-brightgreen)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![Redis](https://img.shields.io/badge/Redis-PubSub%20%2B%20Queue%20%2B%20Snapshots-red)

Kong Fu Chess is a Python-based real-time chess-style game with animated sprites, a live HUD, and a clean modular architecture. It can be played solo on one machine, or online against another player over a real-time-matched, ELO-based server backed by a full microservices architecture running in Docker.

## Overview

- board parsing and validation
- movement logic for king, rook, bishop, queen, knight, and pawn
- real-time timed movement, jumps, captures, and promotions
- animated piece sprites with idle, move, jump, and rest states
- cooldown bars and live clock rendered every frame
- move history with algebraic notation
- observer/event pattern — UI reacts to game events, not polling
- **online 2-player mode**: account/ELO based matchmaking, authoritative game server shards, automatic board-perspective flip, disconnect grace window with technical loss + ELO update
- **microservices architecture**: API Gateway, WS Gateway, Matchmaking service, and Game Server shards — all orchestrated with Docker Compose
- **Redis-backed infrastructure**: shared matchmaking queue (sorted set), room→shard registry, game-state snapshots for crash recovery, and Redis Pub/Sub decoupling Matchmaking from Game Server shards
- **structured observability**: JSON logging and `/health` endpoints on every service
- unit, integration, and UI test suites — 189 tests, 90% core coverage

## Project Structure

- `core/` - all game logic: engine, model, rules, realtime, input, iofiles
  - `core/engine/` - game engine and move scheduler
  - `core/model/` - board, pieces, game state, event bus, move records, notation
  - `core/realtime/` - move settler and motion data
  - `core/rules/` - movement strategies and rule engine
  - `core/input/` - board mapper
  - `core/iofiles/` - board parser and printer
- `view/` - renderers, sprite loader, screen, constants, render state DTOs
- `server/` - microservices backend
  - `server/api/` - REST API Gateway (register, login) on port 8000
  - `server/gateway/` - WebSocket Gateway — routes clients to game shards by consistent-hashed room_id, port 8765
  - `server/matchmaking/` - ELO matchmaking service, port 8766
  - `server/game/` - Game Server shards (game-server-0, game-server-1), internal port 9600
  - `server/core/` - shared database, protocol constants, internal protocol, game logger, Redis client, observability
  - `server/auth/` - authentication service (register, login, tokens, ELO updates)
- `client/` - network transport and a thin adapter that lets the existing `Screen` drive networked play unmodified
- `tests/` - unit, integration, and UI test suites
- `Dockerfile` - single image for all server-side services
- `docker-compose.yml` - orchestrates postgres, redis, api-gateway, ws-gateway, matchmaking, game-server-0, game-server-1
- `main.py` - **the one entry point** — `python main.py [--gui | --online]` (see below)
- `main_ui.py` - single-player graphical mode (also runnable directly)
- `main_network.py` - online 2-player graphical client (also runnable directly)
- `verify_stage_c.py` / `verify_stage_d_manual.py` - standalone scripts that exercise matchmaking and disconnect/reconnect against a real running server

## Architecture Highlights

**Microservices + Docker Compose** — the server is split into four independently deployable services: API Gateway (REST auth), WS Gateway (websocket routing), Matchmaking (ELO queue), and Game Server shards (one per shard index). All wired together with Docker Compose alongside Postgres and Redis.

**Consistent hashing for shard routing** — every service that needs to reach "the shard that owns this room" computes the same deterministic `md5(room_id) % NUM_SHARDS` index. No allocator service, no lookup table.

**Redis Pub/Sub for service decoupling** — when a match is found, Matchmaking publishes a `create_session` event to a per-shard Redis channel (`shard:N:events`). The target Game Server shard subscribes and pre-registers the session. Matchmaking no longer needs to know the shard's hostname or port. Falls back to a direct WebSocket call if Redis is unavailable.

**Redis-backed matchmaking queue** — the ELO queue is stored as a Redis sorted set (score = ELO) so it survives a Matchmaking restart. Falls back to an in-memory list transparently when Redis is unavailable.

**Game state persistence** — `GameSession` snapshots are written to Redis on every `piece_settled` event and restored on reconnect after a shard restart. Deleted from Redis when the game ends. Falls back gracefully (GRACE_SECONDS forfeit logic) if Redis is unavailable.

**Room→shard registry** — Redis stores `room:{room_id} → shard_index` so the WS Gateway can route reconnecting clients to the correct shard without recomputing the hash. Deleted on game end; falls back to consistent hashing if the key is missing.

**Structured observability** — every service emits JSON log lines (one object per line, ingestible by any log aggregator). Every service exposes a `/health` endpoint that probes Postgres and Redis and returns `{"status": "ok"|"degraded", ...}` — used for Docker healthchecks and ready to back Kubernetes readiness/liveness probes.

**Observer pattern** — `GameState` holds an `EventBus`. `MoveSettler` and `GameEngine` fire events (`piece_settled`, `game_over`, `selection_changed`, `restarted`). `Screen` subscribes and sets `_needs_redraw` — no polling.

**DTO layer** — `GameState.to_render_state()` is the only bridge between model and view. All renderers work with `RenderState` — zero model imports in the view layer.

**Real-time rendering** — sprite animations, cooldown bars, and the clock update every frame. Game state is only rebuilt when an event fires.

**Factory pattern** — movement strategies are configured via JSON, new strategies can be added without changing core code.

**Networked play reuses the same Screen** — `client/network_session.py`'s `NetworkSession` is passed in as both the `engine` and `state` argument `Screen` expects, so `Screen` renders and handles clicks exactly as it always did — it has no idea it's talking to a network client. Board flip for the black player, and all click-to-network translation, happens entirely inside `NetworkSession`.

**Server-authoritative state** — the server sends a full `RenderState` snapshot on every relevant event and roughly every 96ms, so the client always renders exactly what the server says with no local interpolation.

**Per-room sessions** — matchmaking creates one `GameSession` per match and pre-registers it on the correct shard before notifying either player.

## Requirements

- Python 3.10+
- Docker + Docker Compose (for online play)
- opencv-python
- numpy
- pytest
- pytest-cov
- websockets
- aiohttp
- psycopg2-binary
- redis

## Installation

```bash
pip install -r requirements.txt
```

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

**1. Start all server services with Docker Compose** (leave running):

```bash
docker compose up --build
```

This starts:
- Postgres on port 5432
- API Gateway on port 8000
- WS Gateway on port 8765
- Matchmaking on port 8766
- Game Server shards (game-server-0, game-server-1) on internal port 9600

**2. Start a client, once per player, each in its own terminal:**

```bash
python main.py --online
```

You'll be prompted to `[1] Register` or `[2] Login` with a username/password.

**3. Choose a mode from the menu:**
- **Play** — quick match via ELO matchmaking
- **Room** — create a named room or join one by room code

**4. Matchmaking:** players are matched by ELO (new accounts start at 1200). The acceptable ELO gap starts at ±100 and widens by 100 every 15 seconds (up to ±500); if no match is found within 2 minutes, a timeout error is shown.

**5. Playing:** once matched, each client opens its own board window automatically. Each window only accepts moves for its own color, and shows the board from that player's perspective — the black player sees their own pieces at the bottom.

**6. Disconnects:** if a client disconnects mid-game, the disconnected player has **20 seconds** to reconnect (same account) and get a full board resync. If they don't return in time, it's recorded as a technical loss and both players' ELO is updated.

## Run Tests

```bash
pytest -q
```

## Generate Coverage Report

```bash
pytest --cov=core --cov-report=html
```

## Verification Scripts

- `python verify_stage_c.py` — matchmaking: token auth, ELO window widening, timeout, concurrent matching, room_id assignment.
- `python verify_stage_d_manual.py` — interactive: registers two throwaway accounts, matches them, and lets you type `dc a`/`dc b` (disconnect) and `rc a`/`rc b` (reconnect) to watch the grace window, resync, forfeit, and ELO update happen live.

## Health Endpoints

After `docker compose up --build`, every service exposes a `/health` endpoint:

```bash
curl http://localhost:8000/health   # api-gateway
curl http://localhost:8767/health   # matchmaking
curl http://localhost:8768/health   # ws-gateway
curl http://localhost:9601/health   # game-server-0
curl http://localhost:9602/health   # game-server-1
```

Each returns: `{"status": "ok", "service": "...", "checks": {"postgres": "ok", "redis": "ok"}}`

## Status

- Test suite: 189 passed, 0 failures
- UI tests: passing
- Core coverage: 90% (HTML report in `htmlcov/`)
- Online play: matchmaking, per-room sessions, disconnect/reconnect, ELO updates — implemented and verified
- Microservices: API Gateway, WS Gateway, Matchmaking, Game Server shards — running in Docker Compose
- Redis: Pub/Sub messaging, matchmaking queue, game snapshots, room registry — all implemented with in-memory fallback
- Observability: structured JSON logging and `/health` endpoints on all services
- Production architecture: documented in `Server_Design.md` §8 (Kubernetes evolution path)
