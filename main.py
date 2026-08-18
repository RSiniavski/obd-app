import time
import os
import sys
import select
import colorama
import config
from app.connection import OBDConnectionManager
from app.reader import TelemetryReader

# Ініціалізація підтримки кольорів у Windows/Linux
colorama.just_fix_windows_console()

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


def format_coolant(val):
    if val is None: return f"{YELLOW}N/A{RESET}"
    text = f"{val} °C"
    if val > 98:
        return f"{RED}🔥 {text} [ПЕРЕГРІВ]{RESET}"
    elif val < 75:
        return f"{CYAN}❄️  {text} [НЕДОГРІВ]{RESET}"
    return f"{GREEN}✅ {text}{RESET}"


def format_voltage(val):
    if val is None: return f"{YELLOW}N/A{RESET}"
    text = f"{val} V"
    if val < 13.2:
        return f"{RED}⚠️  {text} [НИЗЬКИЙ ЗАРЯД]{RESET}"
    elif val > 14.8:
        return f"{YELLOW}⚠️  {text} [ПЕРЕЗАРЯД]{RESET}"
    return f"{GREEN}✅ {text}{RESET}"


def format_boost(val):
    if val is None: return f"{YELLOW}N/A{RESET}"
    text = f"{val} bar"
    if val > 1.4:
        return f"{YELLOW}🚀 {text} [ПІК]{RESET}"
    return f"{text}"


def print_dashboard(metrics: dict, dtcs: list, status_msg: str = ""):
    os.system('cls' if os.name == 'nt' else 'clear')

    print("==========================================")
    print("     BMW E91 (M47TU2) DIAGNOSTIC DASH     ")
    print("==========================================")
    print(f" Оберти двигуна (RPM)   : {metrics.get('rpm', 'N/A')} RPM")
    print(f" Швидкість авто (Speed)  : {metrics.get('speed', 'N/A')} km/h")
    print(f" Темп. антифризу        : {format_coolant(metrics.get('coolant'))}")
    print(f" Тиск наддуву (Boost)   : {format_boost(metrics.get('boost'))}")
    print(f" Напруга мережі         : {format_voltage(metrics.get('voltage'))}")
    print("------------------------------------------")

    if dtcs:
        print(f" {RED}Знайдені помилки (DTC):{RESET}")
        for code, desc in dtcs:
            print(f"  - {RED}{code}{RESET}: {desc}")
    else:
        print(f" {GREEN}Помилок (DTC) не виявлено{RESET}")

    print("------------------------------------------")
    if status_msg:
        print(f" {YELLOW}Статус: {status_msg}{RESET}")
        print("------------------------------------------")
    print(f" [{CYAN}C{RESET}] - Скинути помилки | [{CYAN}R{RESET}] - Оновити DTC | [{CYAN}Ctrl+C{RESET}] - Вихід")


def main():
    connection = OBDConnectionManager.get_connection()
    reader = TelemetryReader(connection)

    dtcs = reader.read_dtc()
    status_msg = ""

    # Налаштування неблокуючого вводу з клавіатури для Windows
    import msvcrt

    try:
        while True:
            metrics = reader.read_metrics()
            print_dashboard(metrics, dtcs, status_msg)

            # Перевіряємо натискання клавіш без затримки
            start_time = time.time()
            while time.time() - start_time < 0.5:
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8').lower()
                    if key == 'c':
                        status_msg = "Очищення помилок..."
                        print_dashboard(metrics, dtcs, status_msg)
                        if reader.clear_dtc():
                            dtcs = []
                            status_msg = "Помилки успішно скинуті!"
                        else:
                            status_msg = "Помилка при скиданні DTC."
                    elif key == 'r':
                        status_msg = "Зчитування помилок..."
                        dtcs = reader.read_dtc()
                        status_msg = "DTC оновлено."
                time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[App] Роботу завершено користувачем.")


if __name__ == "__main__":
    main()