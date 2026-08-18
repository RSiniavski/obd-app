import os

# Перемикач режиму: True — емулятор, False — реальне авто
IS_EMULATOR = False

# Порт для реального Bluetooth OBD2 адаптера
# Для WalnutPi (Linux) це /dev/rfcomm0, для Windows (для тестів вдома) — COM3/COM4
REAL_OBD_PORT = '/dev/rfcomm0' if os.name != 'nt' else 'COM3'

# Швидкість підключення для ELM327
OBD_BAUDRATE = 38400