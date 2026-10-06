# OBD App

Діагностичний дашборд OBD-II для BMW E90/E91 (M47TU2): телеметрія в реальному часі, читання/скидання DTC і збірка під Android (ELM327 Bluetooth).

Версія: **0.1.0** · пакет: `org.siniavski.obdapp`

## Можливості

- **Kivy GUI** — дашборд, DTC, налаштування
- **Консольний TUI** — шкали / текст, гарячі клавіші
- Показники: RPM, швидкість, температура ОР, boost, напруга, IAT, тиск у рампі, MAF, навантаження, дросель, паливо, температура оливи, зовнішня температура
- Віджети: `text`, `bar`, `gauge`, `chart` (увімкнення/стиль зберігаються в `settings.json`)
- Режим емулятора (внутрішній mock або TCP ELM327)
- Desktop: COM-порт / serial ELM327
- Android: Bluetooth через PyJnius
- Збірка APK через Buildozer

## Структура

```
obd-app/
├── main.py              # TUI (desktop); на Android — GUI
├── main_android.py      # Точка входу GUI
├── run_emulator.py      # TCP-емулятор ELM327
├── config.py            # Режими підключення та каталог метрик
├── settings.json        # Збережені налаштування UI / connection
├── buildozer.spec       # Збірка Android APK
├── requirements.txt
├── app/                 # Підключення, телеметрія, Android BT
│   ├── connection.py
│   ├── reader.py
│   └── android_bt.py
├── gui/                 # Kivy UI
│   ├── main_app.py
│   └── ui_layout.kv
├── emulator/            # Mock ELM327 (TCP)
└── tests/
```

## Вимоги

- Python 3.10+
- Windows / Linux / macOS (desktop)
- Для Android: Buildozer + WSL/Linux, ELM327 Bluetooth

Основні залежності: `Kivy==2.3.1`, `obd`, `pyserial`, `Pillow`, `Pint`, `asynckivy`, `colorama` (на Android також `pyjnius`).

## Встановлення

```bash
git clone https://github.com/RSiniavski/obd-app.git
cd obd-app
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Запуск

### Kivy GUI (рекомендовано)

```bash
python gui/main_app.py
# або
python main_android.py
```

Екрани: **Дашборд** · **DTC** · **Налаштування**.

### Консольний дашборд

```bash
python main.py
```

| Клавіша | Дія |
|---------|-----|
| `M` / Space / Enter | Шкала ↔ текст |
| `C` | Скинути DTC |
| `R` | Оновити DTC |
| `Ctrl+C` | Вихід |

### Емулятор

**Внутрішній mock** (за замовчуванням): у `config.py` або `settings.json`:

```python
IS_EMULATOR = True
USE_TCP_EMULATOR = False
```

**TCP ELM327** (окремий термінал):

```bash
python run_emulator.py
```

Потім:

```python
IS_EMULATOR = True
USE_TCP_EMULATOR = True
# EMULATOR_HOST = "127.0.0.1"
# EMULATOR_PORT = 35000
```

### Реальне авто (desktop)

```python
IS_EMULATOR = False
REAL_OBD_PORT = "COM5"       # Windows
# REAL_OBD_PORT = "/dev/ttyUSB0"  # Linux
```

Або змінна середовища `OBD_PORT=COM5`, або поле COM-порту в налаштуваннях GUI.

### Android

1. Вкажи MAC адаптера: `BLUETOOTH_MAC` / env / налаштування.
2. Збери APK:

```bash
buildozer -v android debug
```

APK: `bin/`. Потрібні дозволи Bluetooth / Location (див. `buildozer.spec`).

## Налаштування

| Параметр | Де | Опис |
|----------|-----|------|
| `IS_EMULATOR` | `config.py` / `settings.json` | Симуляція vs авто |
| `USE_TCP_EMULATOR` | те саме | Внутрішній mock vs TCP |
| `REAL_OBD_PORT` | те саме / `OBD_PORT` | Serial ELM327 |
| `BLUETOOTH_MAC` | те саме / env | Android BT |
| `METRICS_INFO` | `config.py` | Каталог показників |
| `enabled_metrics` / `metric_styles` | `settings.json` | UI-картки |

GUI зберігає зміни в `settings.json` автоматично.

## Тести

```bash
python -m pytest tests/
```

## Стек

Python · Kivy · python-OBD · pyserial · PyJnius (Android) · Buildozer
