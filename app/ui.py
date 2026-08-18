import time
import os
from app.reader import TelemetryReader

def run_cli_ui(reader: TelemetryReader):
    """Консольний інтерфейс оновлення даних в реальному часі"""
    try:
        while True:
            metrics = reader.read_metrics()
            os.system('cls' if os.name == 'nt' else 'clear')
            print("==========================================")
            print("       OBD-II DIAGNOSTIC DASHBOARD        ")
            print("==========================================")
            print(f" Оберти двигуна (RPM) : {metrics.get('rpm')}")
            print(f" Швидкість авто (Speed): {metrics.get('speed')}")
            print("------------------------------------------")
            print(" Натисніть Ctrl+C для виходу")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nЗавершення роботи...")