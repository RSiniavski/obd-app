import os

# Режим роботи: True — робота з локальним симулятором, False — з реальним авто
IS_EMULATOR = True

# Налаштування мережі для емулятора
EMULATOR_HOST = "127.0.0.1"
EMULATOR_PORT = 35000

# Налаштування COM-порту для реального ELM327 (наприклад: "COM3" або "/dev/ttyUSB0")
REAL_OBD_PORT = os.getenv("OBD_PORT", "COM3")