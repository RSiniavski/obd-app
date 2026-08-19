import os

# Режим роботи: True — робота з локальним симулятором, False — з реальним авто
IS_EMULATOR = True

# Налаштування мережі для емулятора
EMULATOR_HOST = "127.0.0.1"
EMULATOR_PORT = 35000

# Налаштування COM-порту для реального ELM327 (наприклад: "COM3" або "/dev/ttyUSB0")
REAL_OBD_PORT = os.getenv("OBD_PORT", "COM3")

# Вигляд карток за замовчуванням ("Detailed" або "Compact")
CARD_STYLE = "Detailed"

# Доступні типи: "text", "bar", "gauge", "chart"
METRIC_STYLES = {
    "rpm": "bar",        # Шкала для обертів
    "speed": "text",      # Числовий текст для швидкості
    "coolant": "text",    # Числовий текст для температури
    "boost": "bar",       # Шкала для наддуву
    "voltage": "text"     # Числовий текст для напруги
}

# Межі значень для шкал та графіків
METRIC_LIMITS = {
    "rpm": (0, 7000),
    "speed": (0, 260),
    "coolant": (0, 120),
    "boost": (0.0, 2.0),
    "voltage": (10.0, 16.0)
}