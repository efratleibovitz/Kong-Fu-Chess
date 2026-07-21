"""client/render_state_codec.py

Inverse of dataclasses.asdict(RenderState). The server serializes a
RenderState via dataclasses.asdict + json.dumps, which flattens Enums and
nested dataclasses into a plain dict. The existing renderers use attribute
access (piece.col, piece.state.value), which does not work on a raw dict,
so this rebuilds real dataclass/Enum instances from the parsed dict.
"""

from view.render_state import RenderState, PieceRenderInfo, PlayerRenderInfo, MoveArrow
from view.constants import PieceState


def render_state_from_dict(data: dict) -> RenderState:
    pieces = [
        PieceRenderInfo(
            token=p["token"],
            col=p["col"],
            row=p["row"],
            state=PieceState(p["state"]),
            cooldown_fill=p["cooldown_fill"],
            cooldown_is_long=p["cooldown_is_long"],
        )
        for p in data["pieces"]
    ]

    pending_destinations = [
        MoveArrow(to_col=a["to_col"], to_row=a["to_row"])
        for a in data["pending_destinations"]
    ]

    def _player(p: dict) -> PlayerRenderInfo:
        return PlayerRenderInfo(
            name=p["name"],
            score=p["score"],
            captured=p["captured"],
            move_history=[tuple(entry) for entry in p["move_history"]],
        )

    return RenderState(
        num_cols=data["num_cols"],
        num_rows=data["num_rows"],
        pieces=pieces,
        selected_col=data["selected_col"],
        selected_row=data["selected_row"],
        pending_destinations=pending_destinations,
        clock_ms=data["clock_ms"],
        white=_player(data["white"]),
        black=_player(data["black"]),
        game_over=data["game_over"],
        loser=data["loser"],
    )
