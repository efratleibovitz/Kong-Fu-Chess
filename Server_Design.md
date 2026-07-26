# Server Design — Kong Fu Chess at Scale (100M users / 10M concurrent)

**Assumption (per assignment):** each server = one process = one Docker container. DB counts as one "server" in the list.

---

## 1. Servers needed & their roles

| # | Service | Role |
|---|---------|------|
| 1 | **Auth Service** | Register/login, issue + validate session tokens |
| 2 | **Matchmaking Service** | Queue of waiting players, ELO-based match creation, hands off to Game Server |
| 3 | **Game Server** | Runs the tick loop + real-time game logic for its rooms, broadcasts state to clients |
| 4 | **Database (Postgres)** | Only persistent store — users, elo, sessions |

Supporting infra (not a "server" role of its own, but load-bearing): **Redis** — shared matchmaking queue + room registry + game-state snapshots, used by both Matchmaking and Game Server replicas.

**Why split this way:** Auth is short-request, stateless, bursty. Matchmaking is a periodic queue scan. Game Server is latency-critical (16ms tick) and holds long-lived WebSocket connections. Mixing any of these means the slowest one drags the others' scaling with it — each needs an independent replica count and autoscaling metric.

---

## 2. How they communicate

```
Client --(register/login)--> Auth Service --> Postgres
Client --(token, join queue)--> Matchmaking Service --> Redis (shared queue)
Matchmaking --(match found)--> Client: {"room_id", "color"}
Client --(room_id + token)--> Ingress --(consistent hash of room_id)--> Game Server pod
Game Server --(on first join)--> Redis: read/create room registry entry
Game Server --(tick loop, in-memory)--> broadcasts state to both clients every ~96ms
Game Server --(only at game-over / on login)--> Postgres: ELO update
```

- All inter-service traffic is internal (`ClusterIP`, Kubernetes DNS) — only Auth/Matchmaking/Game Server are internet-facing via Ingress.
- **Room routing is the key trick:** a room lives in exactly one process for its whole life (in-memory `GameSession`, can't be split across pods). The Ingress routes every request for a given `room_id` to the same pod via **consistent hashing** — so "which pod is room X on" is a pure function of `room_id`, no lookup table needed, and adding/removing pods only reshuffles a small fraction of rooms.

---

## 3. If a server goes down

| Server | What happens |
|---|---|
| **Auth** | Stateless — readiness probe fails, pod removed from rotation in seconds, traffic goes to remaining replicas. Zero user impact if ≥1 replica alive. |
| **Matchmaking** | Queue lives in Redis, not pod memory — a crashed replica loses zero queued players. A player whose *own* socket was on the dead pod reconnects (existing `QUEUE_TIMEOUT_SECONDS` logic already covers this). |
| **Game Server — planned restart (deploy/scale-down)** | Pod stops accepting *new* rooms (readiness flips false), finishes the games it's already hosting, only then exits. **Zero games lost.** |
| **Game Server — unplanned crash** | (a) K8s restarts the pod in seconds. (b) Every broadcast already computes `to_render_state()` — also written to Redis at negligible extra cost, so a reconnecting client rehydrates full game state, losing at most one broadcast interval (~100ms) of movement, not the whole game. (c) Existing `GRACE_SECONDS` forfeit-on-disconnect logic is the final safety net if recovery is too slow — opponent wins by forfeit instead of the game hanging forever. |
| **Database** | Single biggest real risk. Mitigation: Postgres with streaming replication / managed failover. Every DB call from Game Server/Matchmaking is wrapped in retry+backoff — a short outage delays ELO/login updates, it does **not** crash the tick loop (which never touches the DB per-tick). |
| **Redis** | Not a source of truth (Postgres is) — losing it costs you the current matchmaking queue (players re-queue) and crash-rehydration (falls back to the `GRACE_SECONDS` forfeit safety net). Redis Sentinel/replica recommended if budget allows. |

---

## 4. Does this meet the scale requirements?

### Q1 — 100M registered users. SQLite OK?

**No — Postgres, single instance + replica.** SQLite is a single-file, single-writer database: multiple server processes/pods hitting it concurrently will corrupt/serialize writes and cap you at one process, period — the opposite of what a multi-pod deployment needs. Postgres handles concurrent connections from many pods natively.

100M rows is *not* a size problem for Postgres by itself — `users.username` already has a `UNIQUE` constraint (existing schema), which Postgres auto-indexes, so login/register stays an O(log n) index lookup, not a table scan, at any row count. The real reason for Postgres isn't row count, it's **concurrent multi-process access**, which SQLite structurally cannot do.

### Q2 — 10M concurrent. One server enough? How does routing/matchmaking work across many pods?

**No, one server is nowhere near enough** — Game Server is horizontally scaled (`N` replicas, N depending on load, autoscaled on active-room-count/CPU). Two problems this raises, both solved:

- **"Which pod is player X's room on?"** → consistent hashing of `room_id` at the Ingress (§2). Any client with a `room_id` reaches the correct pod deterministically, no central lookup table, no cross-pod state sharing needed for gameplay itself.
- **"How does everyone find a match with everyone, across many Matchmaking pods?"** → the naive fix (each pod's own in-memory queue) is wrong — two players on two different pods would never see each other. Fix: the queue moves to **Redis**, shared by every Matchmaking replica, so match-finding always searches the *same* global pool regardless of which pod a player's socket landed on.

**Where this needs more than "move it to Redis," and the actual fix:** at 10M concurrent / 30-90s games (see Q4), the required match-creation rate is far higher than the current algorithm can sustain. The current design scans the *entire* queue under one global lock every 5 seconds per waiting player — that's O(n) per check, serialized. Moving that same algorithm's data into Redis fixes *sharing*, not *throughput*. The actual fix: store the queue as a **Redis sorted set keyed by ELO** (`ZADD`), and match via `ZRANGEBYSCORE` (O(log n + matches found)) instead of a full linear scan, with the "claim both players atomically" step done as a small Lua script (atomic in Redis, no external lock needed at all). This lets match-throughput scale by adding Matchmaking replicas, each independently querying Redis — no shared Python-side lock serializing the whole system.

### Q3 — Traffic from "one step every 2 seconds"

This is inbound (client→server) traffic — a separate, much smaller number than the state broadcasts:

- A click message (`{"type":"click","col":3,"row":4}`) is ~40 bytes.
- At 1 click per 2 sec: **~20 bytes/sec/player inbound.**
- Compare to outbound: measured a real `to_render_state()` JSON payload (actual server code, actual dataclasses) at **~3.8 KB**, broadcast every ~96ms (`TICK_MS=16 × TICKS_PER_BROADCAST=6`) to both players in a room → **~77 KB/sec per room outbound (~38.5 KB/sec/player)**.
- Inbound is **~1,900x smaller** than outbound. Answer: negligible — the real bandwidth budget is entirely dominated by the broadcast side, not player input.

At 10M concurrent (5M rooms): **~385 MB/sec outbound system-wide**, spread horizontally across every Game Server pod — a large but entirely standard figure for a horizontally-scaled real-time service (comparable to any video-call/game-streaming platform at this user count), not a red flag on its own.

### Q4 — 30-90s games. What does this mean for the Docker roles?

Short games at 10M-concurrent scale mean **extreme churn**, and this is the requirement that actually stresses the design the most:

- 10M concurrent ÷ 2 players/room = **5,000,000 concurrent rooms**.
- At ~60s average game length: **5,000,000 ÷ 60 ≈ 83,000 games finishing *every second*** — which must be replaced by ~83,000 new matches/sec to hold steady state.
- **Game Server:** rooms are created and torn down constantly, not long-lived — autoscaling on "active room count" needs a *fast* reaction window (seconds, not minutes), and Redis snapshot keys need a short TTL so short-lived rooms don't accumulate stale state forever.
- **Matchmaking:** this is the pod role most impacted — it must sustain ~83K matches/sec, which is exactly why the ELO-sorted-set + Lua-atomic-claim redesign in Q2 isn't optional polish, it's load-bearing at this scale.
- **Auth:** least affected — 10M concurrent players logged in *once* each is a much smaller request rate than 83K/sec, since sessions are reused (token-based), not re-authenticated per game.

---

## 5. Known limitations (honest, not hidden)

- Crash rehydration is best-effort (~100ms snapshot granularity), not zero-data-loss — acceptable here, not "real production" (which would need full event-sourcing).
- Redis is a single SPOF for matchmaking + snapshots at minimum viable setup; Sentinel/cluster recommended, not implemented in this proposal.
- ELO-window widening (±100→±500 over 45s) across a sharded/sorted-set queue needs care so a widened window still reaches candidates it would have matched with — solved by ELO being the sort key of one shared sorted set rather than pre-partitioned fixed ranges.
