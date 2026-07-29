"""server/core/internal_protocol.py

Wire format + routing for INTERNAL traffic only (WS Gateway <-> Game Server
shard, Matchmaking <-> Game Server shard). Never seen by a real client.

Room -> shard placement is a pure function of room_id (consistent hashing,
per Server_Design.md Sec.1/2) - no allocator service, no lookup table. Every
service that needs to reach "the shard that owns this room" computes the
same index the same way.
"""

import hashlib
import os

NUM_SHARDS = int(os.environ.get("NUM_SHARDS", "2"))

# Each shard i is reachable at this hostname on the internal Docker network
# (docker-compose.yml defines one service per index: game-server-0, game-server-1, ...).
SHARD_HOST_PATTERN = os.environ.get("SHARD_HOST_PATTERN", "game-server-{i}")
SHARD_INTERNAL_PORT = int(os.environ.get("SHARD_INTERNAL_PORT", "9600"))


def shard_index_for_room(room_id: str, num_shards: int = NUM_SHARDS) -> int:
    """Deterministic room -> shard index. md5 (not Python's salted hash())
    so the result is identical across processes/restarts."""
    digest = hashlib.md5(room_id.encode()).hexdigest()
    return int(digest, 16) % num_shards


def shard_internal_url(room_id: str, num_shards: int = NUM_SHARDS) -> str:
    i = shard_index_for_room(room_id, num_shards)
    host = SHARD_HOST_PATTERN.format(i=i)
    return f"ws://{host}:{SHARD_INTERNAL_PORT}"


# --- Envelope "kind" values -------------------------------------------------
# Gateway -> shard (multiplexed: many real clients share one internal socket)
KIND_CLIENT_OPEN = "client_open"        # {kind, conn_id, path}
KIND_CLIENT_MESSAGE = "client_message"  # {kind, conn_id, data}
KIND_CLIENT_CLOSE = "client_close"      # {kind, conn_id}

# Shard -> gateway
KIND_SERVER_MESSAGE = "server_message"  # {kind, conn_id, data}
KIND_SERVER_CLOSE = "server_close"      # {kind, conn_id}

# Matchmaking -> shard (one-shot control call, connection closes right after)
KIND_CREATE_SESSION = "create_session"  # {kind, room_id, white_user_id, white_elo, black_user_id, black_elo}
