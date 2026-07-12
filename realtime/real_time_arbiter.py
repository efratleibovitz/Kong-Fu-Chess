# realtime/real_time_arbiter.py
from dataclasses import dataclass
from model.position import Position

@dataclass
class Motion:
    piece_id: str
    from_pos: Position
    to_pos: Position
    remaining_time: int

class RealTimeArbiter:
    def __init__(self):
        self.active_motions: list[Motion] = []

    def has_active_motion(self) -> bool:
        return len(self.active_motions) > 0

    def start_motion(self, piece_id, from_pos, to_pos, duration):
        # חישוב הזמן הכולל לפי מרחק (כפי שהגדרנו)
        motion = Motion(piece_id, from_pos, to_pos, duration)
        self.active_motions.append(motion)

    def advance_time(self, ms: int):
        # הפחתת זמן מכל התנועות וטיפול באלו שהסתיימו
        finished_motions = []
        for motion in self.active_motions:
            motion.remaining_time -= ms
            if motion.remaining_time <= 0:
                finished_motions.append(motion)
        
        # כאן יתבצע העדכון של הלוח (האכילה/הצבה) ע"י ה-GameEngine
        self.active_motions = [m for m in self.active_motions if m.remaining_time > 0]
        return finished_motions