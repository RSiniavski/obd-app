import os

# Режим роботи: True — симуляція, False — реальне авто
IS_EMULATOR = True

# True — підключення до TCP-емулятора (run_emulator.py), False — внутрішній mock
USE_TCP_EMULATOR = False

# Налаштування мережі для емулятора
EMULATOR_HOST = "127.0.0.1"
EMULATOR_PORT = 35000

# Налаштування COM-порту для реального ELM327 (наприклад: "COM3" або "/dev/ttyUSB0")
REAL_OBD_PORT = os.getenv("OBD_PORT", "COM3")

# MAC / ім'я ELM327 Bluetooth-адаптера (Android; обирається в UI)
BLUETOOTH_MAC = os.getenv("BLUETOOTH_MAC", "")
BLUETOOTH_NAME = os.getenv("BLUETOOTH_NAME", "")

# Вигляд карток за замовчуванням ("Detailed" або "Compact")
CARD_STYLE = "Detailed"

# Каталог усіх доступних показників для BMW E90/E91 (M47TU2 / OBD-II)
METRICS_INFO = {
    "rpm": {
        "name": "Оберти",
        "unit": "RPM",
        "default_style": "bar",
        "limit": (0, 7000),
        "critical": (500, 6500),
        "default_enabled": True,
    },
    "speed": {
        "name": "Швидкість",
        "unit": "km/h",
        "default_style": "text",
        "limit": (0, 260),
        "critical": (None, 200),
        "default_enabled": True,
    },
    "coolant": {
        "name": "Температура ОР",
        "unit": "°C",
        "default_style": "gauge",
        "limit": (0, 120),
        "critical": (70, 105),
        "default_enabled": True,
    },
    "boost": {
        "name": "Наддув (Boost)",
        "unit": "bar",
        "default_style": "bar",
        "limit": (0.0, 2.5),
        "critical": (None, 2.0),
        "default_enabled": True,
    },
    "voltage": {
        "name": "Напруга",
        "unit": "V",
        "default_style": "chart",
        "limit": (10.0, 16.0),
        "critical": (11.8, 14.8),
        "default_enabled": True,
    },
    "iat": {
        "name": "Темп. впуску (IAT)",
        "unit": "°C",
        "default_style": "text",
        "limit": (-20, 100),
        "critical": (None, 65),
        "default_enabled": True,
    },
    "rail_pressure": {
        "name": "Тиск у рампі",
        "unit": "bar",
        "default_style": "gauge",
        "limit": (0, 1800),
        "critical": (None, 1650),
        "default_enabled": True,
    },
    "maf": {
        "name": "Витрата повітря (MAF)",
        "unit": "g/s",
        "default_style": "text",
        "limit": (0, 250),
        "critical": (None, 200),
        "default_enabled": True,
    },
    "engine_load": {
        "name": "Навантаження ДВЗ",
        "unit": "%",
        "default_style": "bar",
        "limit": (0, 100),
        "critical": (None, 95),
        "default_enabled": True,
    },
    "throttle": {
        "name": "Педаль / Дросель",
        "unit": "%",
        "default_style": "bar",
        "limit": (0, 100),
        "critical": (None, None),
        "default_enabled": True,
    },
    "fuel_level": {
        "name": "Рівень палива",
        "unit": "%",
        "default_style": "bar",
        "limit": (0, 100),
        "critical": (15, None),
        "default_enabled": False,
    },
    "oil_temp": {
        "name": "Температура оливи",
        "unit": "°C",
        "default_style": "gauge",
        "limit": (0, 150),
        "critical": (70, 125),
        "default_enabled": False,
    },
    "ambient_temp": {
        "name": "Зовнішня темп.",
        "unit": "°C",
        "default_style": "text",
        "limit": (-40, 50),
        "critical": (None, None),
        "default_enabled": False,
    },
}

# Доступні типи стилів: "text", "bar", "gauge", "chart"
METRIC_STYLES = {k: v["default_style"] for k, v in METRICS_INFO.items()}

# Словник увімкнених/вимкнених віджетів
ENABLED_METRICS = {k: v["default_enabled"] for k, v in METRICS_INFO.items()}

# Межі значень для шкал та графіків
METRIC_LIMITS = {k: v["limit"] for k, v in METRICS_INFO.items()}

# Нижні/верхні критичні пороги
METRIC_CRITICAL_LIMITS = {k: v["critical"] for k, v in METRICS_INFO.items()}
