[app]

# Назва додатка та пакета
title = OBD App
package.name = obdapp
package.domain = org.siniavski

# Вихідний код
source.dir = .
source.include_exts = py,png,jpg,kv,json

# Версія додатка
version = 0.1.0

# Необхідні залежності Python (Kivy, KivyMD для UI та pyjnius для Bluetooth)
requirements = python3,kivy,kivymd,pyjnius

# Дозволи Android для роботи з Bluetooth
android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, BLUETOOTH_SCAN, ACCESS_FINE_LOCATION

# Налаштування системних версій Android API
android.minapi = 21
android.api = 33
android.ndk = 25b

# Орієнтація екрана (portrait, landscape або all)
orientation = portrait

# Формат збірки (0 — вимкнути full-screen, 1 — увімкнути)
fullscreen = 0

[buildozer]

# Рівень логування (2 = детальний вивід помилок збірки)
log_level = 2

# Попередження про запуск під root (0 = вимкнути)
warn_on_root = 1