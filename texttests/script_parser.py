class ScriptParser:
    def __init__(self, engine):
        self.engine = engine

    def execute_command(self, line):
        parts = line.strip().split()
        if not parts: return
        
        cmd = parts[0]
        args = parts[1:]

        if cmd == "click":
            self.engine.click(int(args[0]), int(args[1]))
        elif cmd == "wait":
            self.engine.wait(int(args[0]))
        elif cmd == "jump":
            self.engine.jump(int(args[0]), int(args[1]))