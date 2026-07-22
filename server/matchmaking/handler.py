"""server/matchmaking/handler.py"""

import json
from urllib.parse import urlparse, parse_qs

from server.core.protocol import MSG_TYPE_ERROR, QUERY_TOKEN, FIELD_REASON, Reason
from server.core.database import get_user_by_id
from server.auth.service import get_user_id_by_token
from server.matchmaking.queue import add_to_queue


async def matchmaking_handler(websocket):
    params = parse_qs(urlparse(websocket.request.path).query)
    token = params.get(QUERY_TOKEN, [None])[0]

    user_id = get_user_id_by_token(token) if token else None
    if user_id is None:
        await websocket.send(json.dumps({"type": MSG_TYPE_ERROR, FIELD_REASON: Reason.UNAUTHORIZED.value}))
        await websocket.close()
        return

    user = get_user_by_id(user_id)
    elo = user["elo"]

    await add_to_queue(websocket, user_id, elo)
