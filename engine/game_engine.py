# engine/game_engine.py
from model.game_state import GameState
from rules.rule_engine import RuleEngine
from realtime.real_time_arbiter import RealTimeArbiter

class GameEngine:
    def __init__(self, game_state: GameState):
        self.state = game_state
        self.rule_engine = RuleEngine()
        self.arbiter = RealTimeArbiter()

    def request_move(self, source, destination):
        # 1. תנאי הגנה (Guard Clauses)
        if self.state.game_over:
            return {"is_accepted": False, "reason": "game_over"}
        
        # בדיקת תנועה פעילה - דרישת המסלול המשותף
        if self.arbiter.has_active_motion():
            return {"is_accepted": False, "reason": "motion_in_progress"}
        
        # 2. אימות חוקיות
        validation = self.rule_engine.validate_move(self.state.board, source, destination)
        if not validation["is_valid"]:
            return {"is_accepted": False, "reason": validation["reason"]}
            
        # 3. התחלת תנועה (בהנחה שקבענו מהירות קבועה של 1000ms לכל משבצת)
        # חישוב מרחק וזמן (לוגיקה שניתן להוציא ל-utils או להשאיר כאן)
        distance = max(abs(destination.x - source.x), abs(destination.y - source.y))
        duration = distance * 1000
        
        token = self.state.board.get_token(source)
        self.arbiter.start_motion(token, source, destination, duration)
        
        return {"is_accepted": True, "reason": "ok"}

    # engine/game_engine.py

    def wait(self, ms: int):
        # התקדמות זמן ב-Arbiter וקבלת אירועי הגעה
        events = self.arbiter.advance_time(ms)
        
        # עיבוד כל תנועה שהגיעה ליעדה
        for motion in events:
            # 1. הסרת הכלי מהמקור
            self.state.board.set_token(motion.from_pos, '.')
            
            # 2. בדיקה אם יש כלי ביעד (אכילה)
            captured = self.state.board.get_token(motion.to_pos)
            if captured != '.' and 'K' in captured:
                self.state.game_over = True
            
            # 3. הצבת הכלי ביעד
            self.state.board.set_token(motion.to_pos, motion.piece_id)
            
    def _finalize_move(self, motion):
        # עדכון הלוח:
        # א. הסרת הכלי מהמקור
        self.state.board.set_token(motion.from_pos, '.')
        
        # ב. בדיקה אם יש כלי ביעד (אכילה)
        captured = self.state.board.get_token(motion.to_pos)
        
        # ג. בדיקה אם נפל מלך (סיום משחק)
        # נניח ש-token מיוצג כ-wK, bK וכו'
        if captured != '.' and 'K' in captured:
            self.state.game_over = True
            
        # ד. הצבת הכלי ביעד
        self.state.board.set_token(motion.to_pos, motion.piece_id)