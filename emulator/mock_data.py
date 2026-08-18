import math
import time

class OBDMockEngine:
    def __init__(self):
        self.start_time = time.time()

    def get_rpm(self) -> int:
        t = time.time() - self.start_time
        return int(2150 + 1350 * math.sin(t / 2))

    def get_speed(self) -> int:
        t = time.time() - self.start_time
        return int(50 + 50 * math.sin(t / 4))

    def process_command(self, cmd: str) -> str:
        clean_cmd = cmd.strip().upper().replace(" ", "")

        # Реагуємо на AT-команди з точним переносом рядків
        if clean_cmd == "ATZ":
            return "ELM327 v1.5\r\r\n>"
        elif clean_cmd.startswith("AT"):
            return "OK\r\r\n>"

        # PIDs
        if "0100" in clean_cmd:
            return "41 00 BE 1F A8 13\r\r\n>"
        elif "010C" in clean_cmd:
            val = self.get_rpm() * 4
            a = (val >> 8) & 0xFF
            b = val & 0xFF
            return f"41 0C {a:02X} {b:02X}\r\r\n>"
        elif "010D" in clean_cmd:
            val = self.get_speed() & 0xFF
            return f"41 0D {val:02X}\r\r\n>"
        elif clean_cmd.startswith("03"):
            return "43 00\r\r\n>"

        return "NO DATA\r\r\n>"