# Server Design — Kong Fu Chess at Scale (100M users / 10M concurrent)

**Assumption (per assignment):** each server = one process = one Docker container. DB counts as one "server" in the list. Component split follows the reviewed architecture (API Gateway / WS Gateway / Matchmaker / Game Server Shards / Observability / Postgres+Redis), with two deliberate deviations documented in §1: no separate Game Allocator (consistent hashing instead), WS Gateway kept as a thin routing layer rather than holding any game logic.

---

## 1. Servers needed & their roles

| # | Service | Role |
|---|---------|------|
| 1 | **API Gateway** | Non-real-time REST: register/login (wraps Auth), rooms, match/game history |
| 2 | **WS Gateway** | Terminates the client's live WebSocket connection; forwards messages to the correct Game Server shard |
| 3 | **Matchmaking Service** | Queue of waiting players, ELO-based match creation, hands off to Game Server |
| 4 | **Game Server (Shards)** | Runs the tick loop + real-time game logic for its rooms; authoritative `GameEngine` — rules live only here, never in the Gateway or the client |
| 5 | **Observability** | Health checks for every service above, structured logs, basic metrics |
| 6 | **Database (Postgres)** | Only persistent store — users, elo, sessions, move history |

Supporting infra (not a "server" role of its own, but load-bearing): **Redis** — shared matchmaking queue, room→shard registry, game-state snapshots — used by Matchmaking, WS Gateway, and Game Server replicas.

**Why split this way:** Auth/rooms/history are short-request, stateless, bursty — good fit for a REST gateway that scales on request count. The WS Gateway holds millions of *idle* long-lived sockets and does async I/O with no thread per client, so it scales on connection count, not CPU. Matchmaking is a periodic queue scan. Game Server is latency-critical (16ms tick) and CPU-bound per active room. Mixing any of these means the slowest one drags the others' scaling with it — each needs an independent replica count and autoscaling metric.

**Design choice — WS Gateway vs. direct-to-shard:** an alternative (and simpler) design skips the WS Gateway entirely and has the client connect straight to its Game Server shard, with routing done by consistent-hashing the `room_id` at the Ingress. We chose the WS Gateway instead because (a) it matches the reviewed architecture, and (b) it decouples the client's connection lifetime from a Game Server pod's — a shard can be redeployed/rescaled without the client's TCP/TLS session dying, since the Gateway is what the client is actually attached to. The cost is one extra network hop per message. **Room placement itself still uses consistent hashing** (§2) — we did not add a separate Game Allocator service, since hashing `room_id` gives the same "which shard owns this room" answer without an extra stateful component to keep alive.

---

## 2. How they communicate

```
Client --(REST: register/login)--> API Gateway --> Auth logic --> Postgres
Client --(REST: rooms/history)--> API Gateway --> Postgres
Client --(WS: token, join queue)--> Matchmaking Service --> Redis (shared queue)
Matchmaking --(match found)--> Client: {"room_id", "color"}
Client --(WS: room_id + token)--> WS Gateway --(consistent hash of room_id)--> Game Server shard
Game Server --(on first join)--> Redis: read/create room registry entry
Game Server --(tick loop, in-memory)--> WS Gateway --> broadcasts state to both clients every ~96ms
Game Server --(only at game-over / on login)--> Postgres: ELO update
```

- Only **API Gateway** and **WS Gateway** are internet-facing. Everything behind them (Auth logic, Matchmaking, Game Server, Postgres, Redis) is internal-only (`ClusterIP` / Kubernetes DNS in K8s; Docker's internal network in Compose).
- **Room routing is the key trick:** a room lives in exactly one process for its whole life (in-memory `GameSession`, can't be split across pods). The **WS Gateway** routes every message for a given `room_id` to the same Game Server shard via **consistent hashing** — so "which shard is room X on" is a pure function of `room_id`, no lookup table needed, and adding/removing shards only reshuffles a small fraction of rooms. In Docker Compose (MVP, §6) this hash is computed in the Gateway's own application code; at Kubernetes scale the same logic can move into the Ingress controller's routing rules instead, so the Gateway itself never becomes a bottleneck — same mechanism, just implemented in app code now vs. infra config later.

---

## 3. If a server goes down

| Server | What happens |
|---|---|
| **API Gateway** | Stateless — readiness probe fails, pod removed from rotation in seconds, traffic goes to remaining replicas. Zero user impact if ≥1 replica alive. |
| **WS Gateway** | Holds live client sockets but no game state (state lives in Redis/Game Server) — a crashed replica drops its connected clients' sockets, but they reconnect to a healthy replica and rejoin their room via `room_id` + token, same as a client-side network blip. Not a state loss, just a reconnect. |
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

- **"Which shard is player X's room on?"** → consistent hashing of `room_id`, done at the WS Gateway (§2). Any client with a `room_id` reaches the correct shard deterministically, no central lookup table, no cross-shard state sharing needed for gameplay itself.
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
- The WS Gateway adds one extra network hop to every client message vs. the direct-to-shard alternative — a latency cost accepted in exchange for decoupling client connections from Game Server pod lifecycle (§1).

---

## 6. Observability (MVP scope)

Not built as a separate always-on stack for the Compose MVP — kept intentionally small:

- Every service (API Gateway, WS Gateway, Matchmaking, Game Server) exposes a `/health` endpoint used for container healthchecks in Compose and would back K8s readiness/liveness probes later.
- Structured logging (existing per-room log files under `server/logs/` are the current version of this) to stdout in containers, so `docker compose logs` is the MVP's monitoring.
- Metrics/tracing/alerting (Prometheus/Grafana-style) are noted as the production upgrade path, not implemented here — out of scope for a small working version.

---

## 7. Docker Compose MVP — what actually runs

| Container | Image / built from | Notes |
|---|---|---|
| `api-gateway` | built (shared Dockerfile, different start command) | REST: register/login/rooms/history |
| `ws-gateway` | built (shared Dockerfile) | Client WS entrypoint, hashes `room_id` → shard |
| `matchmaking` | built (shared Dockerfile) | ELO queue via Redis |
| `game-server` (x2 for MVP) | built (shared Dockerfile) | Two replicas, enough to prove shard routing works, not real scale |
| `postgres` | official `postgres` image | users, elo, sessions, move history |
| `redis` | official `redis` image | queue, room→shard registry, snapshots |

All services share one Dockerfile (single Python package, `server.*` imports) and one Docker network; only `api-gateway` and `ws-gateway` publish ports to the host.

---

## 8. Production Architecture — Kubernetes evolution

This section documents how the Docker Compose MVP maps to a production Kubernetes deployment capable of handling the 10M concurrent / 83K matches-per-second scale described in §4. No code changes are required — the application layer is already designed for this. The changes are entirely in how containers are deployed and wired together.

### 8.1 Docker Compose → Kubernetes mapping

| Docker Compose | Kubernetes resource | Replicas / scaling |
|---|---|---|
| `api-gateway` container | `Deployment` + `ClusterIP` Service | 3–10 replicas, HPA on CPU |
| `ws-gateway` container | `Deployment` + `LoadBalancer` Service (or Ingress) | 5–20 replicas, HPA on active connection count |
| `matchmaking` container | `Deployment` + `ClusterIP` Service | 3–10 replicas, HPA on queue depth (custom metric) |
| `game-server-0/1` containers | `StatefulSet` (one pod per shard index) | Fixed shard count, vertical scaling per pod |
| `postgres` container | Managed DB (RDS / Cloud SQL) or `StatefulSet` with PVC | Primary + 1–2 read replicas |
| `redis` container | Managed Redis (ElastiCache) or Redis Sentinel `StatefulSet` | 1 primary + 2 replicas |
| Docker network (internal) | Kubernetes `ClusterIP` Services + DNS | All inter-service traffic stays inside the cluster |
| `ports:` in Compose | `Ingress` controller (NGINX / Traefik) | Single external entry point, TLS termination |

### 8.2 Ingress — replacing manual port exposure

In Docker Compose, `api-gateway` and `ws-gateway` publish ports directly to the host. In Kubernetes, a single **Ingress controller** (NGINX or Traefik) is the only internet-facing component:

```
Internet
    │
    ▼
Ingress controller  (TLS termination, rate limiting, DDoS protection)
    ├── /api/*          ──► api-gateway ClusterIP Service
    └── /ws  (Upgrade)  ──► ws-gateway ClusterIP Service
```

- REST traffic (`/register`, `/login`, `/rooms`) routes to `api-gateway`.
- WebSocket upgrade requests route to `ws-gateway`. The Ingress must be configured with `nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"` (or equivalent) so long-lived WS connections are not killed by the default 60s proxy timeout.
- Everything else (`matchmaking`, `game-server-*`, `postgres`, `redis`) has `ClusterIP` only — unreachable from outside the cluster.

### 8.3 Autoscaling — the right metric per service

Each service has a different bottleneck, so each needs a different HPA metric:

| Service | Scale metric | Why |
|---|---|---|
| `api-gateway` | CPU utilisation | Short stateless requests — CPU is the right proxy for load |
| `ws-gateway` | Active connection count (custom metric via Prometheus) | CPU stays low even under millions of idle sockets — connection count is the real resource |
| `matchmaking` | Redis queue depth (external metric) | Queue growing means match-creation is falling behind — add replicas to drain it faster |
| `game-server` | Active room count per pod (custom metric) | CPU per pod rises linearly with rooms; scale out when rooms-per-pod exceeds a threshold |

`game-server` pods are a `StatefulSet` with a fixed shard count, not a standard HPA target — adding a new shard requires a rolling config update (new `SHARD_INDEX`, new pub/sub subscription). The consistent-hashing function (`md5(room_id) % NUM_SHARDS`) must be updated atomically across all services when `NUM_SHARDS` changes, otherwise the Gateway routes new rooms to the wrong shard. In practice: double the shard count during a maintenance window, drain old shards gracefully.

**PodDisruptionBudgets** — set `minAvailable: 1` on every Deployment so a node drain never takes a service to zero replicas:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ws-gateway-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: ws-gateway
```

### 8.4 Redis — high availability

In Docker Compose, Redis is a single container — one crash loses the matchmaking queue and all game snapshots. In production:

**Redis Sentinel** (minimum viable HA):
```
Redis Primary  ◄──replication──  Redis Replica-1
      │                          Redis Replica-2
      │
Sentinel-1  Sentinel-2  Sentinel-3   (quorum = 2)
```
- Sentinel monitors the primary and promotes a replica automatically on failure (typically within 10–30 seconds).
- Application code connects to Sentinel, not directly to the primary — `redis.asyncio.from_url("redis+sentinel://...")` handles failover transparently.
- The existing `get_redis()` in `server/core/redis_client.py` only needs its URL changed — no other code changes required.

**Redis Cluster** (for true horizontal scale beyond a single primary's memory/throughput) — not needed until the sorted-set matchmaking queue or snapshot storage exceeds a single node's capacity, which at 10M concurrent is a real concern for snapshots (`game:{room_id}` keys at ~5M concurrent rooms). Cluster shards the keyspace automatically; the application code change is minimal (`redis.asyncio.RedisCluster` instead of `from_url`).

### 8.5 Postgres — high availability

In Docker Compose, Postgres is a single container. In production:

- **Primary + streaming replication replica** — replica handles read traffic (ELO lookups, history queries); primary handles writes (register, ELO update on game-over).
- **Managed service preferred** (AWS RDS, Google Cloud SQL, Azure Database for PostgreSQL) — automated failover, point-in-time recovery, and connection pooling (PgBouncer) are handled by the provider rather than requiring custom ops work.
- The existing `server/core/database.py` `_connect()` function only needs `DATABASE_URL` pointed at the managed endpoint — no schema or query changes required.
- At 100M users, the `users` table stays fast: `username` is already `UNIQUE`-indexed (existing schema), so login is always an index seek, not a scan.

### 8.6 What stays exactly the same

The application layer requires zero changes to run in Kubernetes:

- **Consistent hashing** (`md5(room_id) % NUM_SHARDS`) — same function, same result, whether running in Compose or K8s. The Gateway, Matchmaking, and Game Server all compute it independently with no coordination.
- **Redis Pub/Sub channels** (`shard:0:events`, `shard:1:events`) — channel names are derived from `SHARD_INDEX`, which is already an environment variable. Each pod subscribes to its own channel on startup.
- **Health endpoints** (`/health` on every service) — already implemented (Stage 4). In K8s these back `readinessProbe` and `livenessProbe` directly:
  ```yaml
  readinessProbe:
    httpGet:
      path: /health
      port: 8000
    initialDelaySeconds: 5
    periodSeconds: 10
  livenessProbe:
    httpGet:
      path: /health
      port: 8000
    initialDelaySeconds: 15
    periodSeconds: 30
  ```
- **Structured JSON logs** (Stage 4) — already stdout JSON. In K8s, a log collector (Fluentd / Fluent Bit) picks them up from pod stdout and ships to any aggregator (CloudWatch, Datadog, Loki) with no application changes.
- **Graceful disconnect handling** (`GRACE_SECONDS = 20`) — already implemented. A pod receiving `SIGTERM` (K8s rolling update) stops accepting new connections; existing games finish within their grace window before the pod exits.
- **Redis fallback** — every Redis call in `redis_client.py` returns `None`/`False` silently if Redis is unreachable. During a Redis failover (Sentinel promoting a replica, ~10–30s), the system degrades gracefully: matchmaking falls back to in-memory queue, Gateway falls back to hash routing, game snapshots are skipped. No crash, no data corruption.

### 8.7 Migration path — Compose to Kubernetes

The steps are additive, not a rewrite:

1. **Containerise** — already done. One shared `Dockerfile`, all services.
2. **Push image to a registry** (ECR / GCR / Docker Hub).
3. **Write K8s manifests** — one `Deployment` + `Service` per service, one `StatefulSet` for game-server shards, one `Ingress`. Environment variables (`REDIS_URL`, `DATABASE_URL`, `SHARD_INDEX`, `NUM_SHARDS`) move from `docker-compose.yml` to K8s `ConfigMap` / `Secret`.
4. **Point DNS** at the Ingress controller's external IP.
5. **Add HPAs** once baseline metrics are collected (first week of production traffic).
6. **Swap Redis/Postgres** to managed services — change one environment variable each, redeploy.

No application code changes at any step.

