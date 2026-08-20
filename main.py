import os
import sys

# Android APK entry (Buildozer requires main.py)
if "ANDROID_ARGUMENT" in os.environ:
    from gui.main_app import DashboardApp
    DashboardApp().run()
    raise SystemExit(0)

import time
import colorama
import config
from app.connection import OBDConnectionManager
from app.reader import TelemetryReader

colorama.just_fix_windows_console()

# Кольори
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
WHITE = "\033[97m"
RESET = "\033[0m"


# --- КОНТЕКСТНИЙ МЕНЕДЖЕР ДЛЯ ВВОДУ ---
class NonBlockingInput:
    def __enter__(self):
        if os.name != 'nt':
            import termios
            import tty
            self.fd = sys.stdin.fileno()
            self.old_settings = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, type, value, traceback):
        if os.name != 'nt':
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)


def get_key_pressed():
    if os.name == 'nt':
        import msvcrt
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            try:
                # Декодуємо байт у символ і приводимо до нижнього регістру
                return ch.decode('utf-8', errors='ignore').lower()
            except Exception:
                return ""
    else:
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.read(1)
            return ch.lower() if ch else None
    return None


# --- ДОПОМІЖНІ ФУНКЦІЇ ДЛЯ РЕЖИМІВ ---

def make_bar(value, min_val, max_val, width=20, color=GREEN):
    """Створює графічну шкалу"""
    if value is None:
        return f"[{' ' * width}] N/A"

    safe_val = max(min_val, min(value, max_val))
    percent = (safe_val - min_val) / (max_val - min_val)
    filled_width = int(percent * width)

    bar = "=" * filled_width
    if filled_width < width:
        bar += ">"
        bar += " " * (width - filled_width - 1)

    return f"{color}[{bar}]{RESET} {value}"


def format_coolant(val):
    if val is None: return f"{YELLOW}N/A{RESET}"
    text = f"{val} °C"
    if val > 98: return f"{RED}🔥 {text} [ПЕРЕГРІВ]{RESET}"
    elif val < 75: return f"{CYAN}❄️  {text} [НЕДОГРІВ]{RESET}"
    return f"{GREEN}✅ {text}{RESET}"


def format_voltage(val):
    if val is None: return f"{YELLOW}N/A{RESET}"
    text = f"{val} V"
    if val < 13.2: return f"{RED}⚠️  {text} [НИЗЬКИЙ ЗАРЯД]{RESET}"
    elif val > 14.8: return f"{YELLOW}⚠️  {text} [ПЕРЕЗАРЯД]{RESET}"
    return f"{GREEN}✅ {text}{RESET}"


def format_boost(val):
    if val is None: return f"{YELLOW}N/A{RESET}"
    text = f"{val} bar"
    if val > 1.4: return f"{YELLOW}🚀 {text} [ПІК]{RESET}"
    return f"{text}"


# --- ГОЛОВНА ФУНКЦІЯ ДАШБОРДУ ---

def print_dashboard(metrics: dict, dtcs: list, status_msg: str = "", view_mode: str = "bars"):
    os.system('cls' if os.name == 'nt' else 'clear')

    print(f"{WHITE}=========================================={RESET}")
    print(f"{CYAN}     BMW E91 (M47TU2) DIAGNOSTIC DASH     {RESET}")
    print(f"{WHITE}=========================================={RESET}")

    rpm = metrics.get('rpm')
    speed = metrics.get('speed')
    temp = metrics.get('coolant')
    boost = metrics.get('boost')
    volt = metrics.get('voltage')

    if view_mode == "bars":
        # РЕЖИМ ШКАЛ (TUI)
        rpm_color = RED if rpm and rpm > 4500 else GREEN
        print(f" RPM   : {make_bar(rpm, 0, 5000, 25, rpm_color)} RPM")
        print(f" Speed : {make_bar(speed, 0, 200, 25, CYAN)} km/h")

        temp_color = RED if temp and temp > 98 else (CYAN if temp and temp < 75 else GREEN)
        print(f" Temp  : {make_bar(temp, 50, 120, 25, temp_color)} °C")

        boost_color = YELLOW if boost and boost > 1.4 else WHITE
        print(f" Boost : {make_bar(boost, 0, 2.0, 25, boost_color)} bar")

        volt_color = RED if volt and (volt < 13.2 or volt > 14.8) else GREEN
        print(f" Volt  : {make_bar(volt, 11.0, 15.0, 25, volt_color)} V")
    else:
        # ТЕКСТОВИЙ РЕЖИМ
        print(f" Оберти двигуна (RPM)   : {rpm if rpm is not None else 'N/A'} RPM")
        print(f" Швидкість авто (Speed)  : {speed if speed is not None else 'N/A'} km/h")
        print(f" Темп. антифризу        : {format_coolant(temp)}")
        print(f" Тиск наддуву (Boost)   : {format_boost(boost)}")
        print(f" Напруга мережі         : {format_voltage(volt)}")

    print(f"{WHITE}------------------------------------------{RESET}")

    if dtcs:
        print(f" {RED}Знайдені помилки (DTC):{RESET}")
        for code, desc in dtcs:
            print(f"  - {RED}{code}{RESET}: {desc}")
    else:
        print(f" {GREEN}Помилок (DTC) не виявлено{RESET}")

    print(f"{WHITE}------------------------------------------{RESET}")
    if status_msg:
        print(f" {YELLOW}Статус: {status_msg}{RESET}")
        print(f"{WHITE}------------------------------------------{RESET}")

    mode_text = "Шкала" if view_mode == "bars" else "Текст"
    print(f" [{CYAN}M{RESET}] Режим: {mode_text} | [{CYAN}C{RESET}] Скинути | [{CYAN}R{RESET}] Оновити | [{CYAN}Ctrl+C{RESET}] Вихід")


def main():
    connection = OBDConnectionManager.get_connection()
    reader = TelemetryReader(connection)

    dtcs = reader.read_dtc()
    status_msg = ""
    view_mode = "bars"  # Початковий режим — Шкали

    with NonBlockingInput():
        try:
            while True:
                metrics = reader.read_metrics()
                print_dashboard(metrics, dtcs, status_msg, view_mode)

                start_time = time.time()
                while time.time() - start_time < 0.3:
                    key = get_key_pressed()

                    # Реагує на m, ь (укр розкладка), пробіл та Enter
                    if key in ['m', 'ь', ' ', '\r', '\n']:
                        view_mode = "text" if view_mode == "bars" else "bars"
                        status_msg = f"Режим змінено на: {view_mode}"
                        print_dashboard(metrics, dtcs, status_msg, view_mode)
                    elif key in ['c', 'с']:
                        status_msg = "Очищення..."
                        print_dashboard(metrics, dtcs, status_msg, view_mode)
                        if reader.clear_dtc():
                            dtcs = []
                            status_msg = "Скинуто!"
                        else:
                            status_msg = "Помилка скидання."
                    elif key in ['r', 'к']:
                        status_msg = "Оновлення..."
                        print_dashboard(metrics, dtcs, status_msg, view_mode)
                        dtcs = reader.read_dtc()
                        status_msg = "DTC оновлено."

                    time.sleep(0.02)

        except KeyboardInterrupt:
            print("\n[App] Зупинено.")


if __name__ == "__main__":
    main()