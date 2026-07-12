from model.position import Position
from realtime.motion import Motion, Jump


class ArrivalEvent:
    """Returned by advance_time for each motion that arrived."""
    def __init__(self, motion: Motion, king_captured: bool = False):
        self.motion = motion
        self.king_captured = king_captured


class RealTimeArbiter:
    def __init__(self):
        self.active_motions: list[Motion] = []
        self.active_jumps: list[Jump] = []

    # --- queries ---

    def has_active_motion(self) -> bool:
        return len(self.active_motions) > 0

    def is_in_transit(self, pos: Position) -> bool:
        return any(m.from_pos == pos for m in self.active_motions)

    def is_airborne(self, pos: Position) -> bool:
        return any(j.pos == pos for j in self.active_jumps)

    def columns_occupied(self) -> set[int]:
        """All columns currently used by active motions (for column-conflict check)."""
        cols: set[int] = set()
        for m in self.active_motions:
            min_col = min(m.from_pos.col, m.to_pos.col)
            max_col = max(m.from_pos.col, m.to_pos.col)
            cols.update(range(min_col, max_col + 1))
        return cols

    def columns_of(self, from_pos: Position, to_pos: Position) -> set[int]:
        min_col = min(from_pos.col, to_pos.col)
        max_col = max(from_pos.col, to_pos.col)
        return set(range(min_col, max_col + 1))

    def has_column_conflict(self, from_pos: Position, to_pos: Position) -> bool:
        new_cols = self.columns_of(from_pos, to_pos)
        return bool(new_cols & self.columns_occupied())

    # --- commands ---

    def schedule_move(self, token: str, from_pos: Position, to_pos: Position, clock: int) -> bool:
        """
        Schedule a move. Returns False if the destination is intercepted by an
        enemy jump (source piece is removed immediately in that case).
        Returns True if motion was queued normally.
        """
        distance = max(abs(to_pos.col - from_pos.col), abs(to_pos.row - from_pos.row))
        arrive_time = clock + distance * 500

        # Check if an enemy jumper is waiting at the destination
        intercepted = any(
            j.pos == to_pos and j.token[0] != token[0]
            for j in self.active_jumps
        )
        if intercepted:
            # piece is destroyed mid-air — caller must clear the source cell
            return False

        self.active_motions.append(Motion(token, from_pos, to_pos, arrive_time))
        return True

    def schedule_jump(self, token: str, pos: Position, clock: int):
        """Register a piece as airborne for 1000ms."""
        self.active_jumps.append(Jump(token, pos, clock + 1000))

    def advance_time(self, ms: int, clock: int) -> list[Motion]:
        """
        Advance the clock by ms. Returns list of Motions that have arrived.
        Expired jumps are pruned automatically.
        """
        new_clock = clock  # caller has already incremented clock before calling
        arrived = [m for m in self.active_motions if m.arrive_time <= new_clock]
        self.active_motions = [m for m in self.active_motions if m.arrive_time > new_clock]
        self.active_jumps = [j for j in self.active_jumps if j.expire_time > new_clock]
        return arrived
