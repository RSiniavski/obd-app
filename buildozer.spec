[app]

# Назва додатка та пакета
title = OBD App
package.name = obdapp
package.domain = org.siniavski

# Вихідний код (обов'язково має містити main.py)
source.dir = .
source.include_exts = py,png,jpg,kv,json

# Версія додатка
version = 0.1.0

# Залежності для Android
requirements = python3,kivy,kivymd,pyjnius,pillow,obd,pyserial,pint,materialyoucolor,asynckivy,asyncgui

# Виключити з APK зайві каталоги
source.exclude_dirs = tests,.venv,.idea,.git,.buildozer,bin,emulator,__pycache__

# Дозволи Android для роботи з Bluetooth
android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

# Архітектури (спочатку лише arm64 — швидша збірка; для старих телефонів додайте armeabi-v7a)
android.archs = arm64-v8a

# Системні версії Android API
android.minapi = 21
android.api = 33
android.ndk = 25b
android.accept_sdk_license = True

# Орієнтація екрана
orientation = portrait
fullscreen = 0

[buildozer]

log_level = 2
warn_on_root = 1
