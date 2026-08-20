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
        return max(0, int(50 + 50 * math.sin(t / 4)))

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
        elif "0120" in clean_cmd:
            return "41 20 80 00 00 01\r\r\n>"
        elif "0104" in clean_cmd:  # Engine Load
            val = 115  # ~45%
            return f"41 04 {val:02X}\r\r\n>"
        elif "0105" in clean_cmd:  # Coolant temp (val = temp + 40)
            val = 88 + 40
            return f"41 05 {val:02X}\r\r\n>"
        elif "010B" in clean_cmd:  # Intake MAP (kPa)
            val = 145  # ~1.45 bar abs -> 0.45 bar boost
            return f"41 0B {val:02X}\r\r\n>"
        elif "010C" in clean_cmd:  # RPM
            val = self.get_rpm() * 4
            a = (val >> 8) & 0xFF
            b = val & 0xFF
            return f"41 0C {a:02X} {b:02X}\r\r\n>"
        elif "010D" in clean_cmd:  # Speed
            val = self.get_speed() & 0xFF
            return f"41 0D {val:02X}\r\r\n>"
        elif "010F" in clean_cmd:  # Intake air temp (IAT)
            val = 32 + 40
            return f"41 0F {val:02X}\r\r\n>"
        elif "0110" in clean_cmd:  # MAF (g/s * 100)
            val = int(28.5 * 100)
            a = (val >> 8) & 0xFF
            b = val & 0xFF
            return f"41 10 {a:02X} {b:02X}\r\r\n>"
        elif "0111" in clean_cmd:  # Throttle pos
            val = 80
            return f"41 11 {val:02X}\r\r\n>"
        elif "0123" in clean_cmd or "0122" in clean_cmd:  # Rail pressure
            val = int(650 / 0.1)  # 650 bar
            a = (val >> 8) & 0xFF
            b = val & 0xFF
            return f"41 23 {a:02X} {b:02X}\r\r\n>"
        elif "012F" in clean_cmd:  # Fuel level
            val = int(62 * 255 / 100)
            return f"41 2F {val:02X}\r\r\n>"
        elif "0142" in clean_cmd:  # Control module voltage (mV)
            val = int(14.2 * 1000)
            a = (val >> 8) & 0xFF
            b = val & 0xFF
            return f"41 42 {a:02X} {b:02X}\r\r\n>"
        elif "0146" in clean_cmd:  # Ambient air temp
            val = 19 + 40
            return f"41 46 {val:02X}\r\r\n>"
        elif "015C" in clean_cmd:  # Oil temp
            val = 90 + 40
            return f"41 5C {val:02X}\r\r\n>"
        elif clean_cmd.startswith("03"):  # DTC
            return "43 00\r\r\n>"

        return "NO DATA\r\r\n>"
