[app]
#p4a.hook =
p4a.pip_build_args = --use-pep517

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
requirements = python3,kivy==2.3.1,pillow,pyjnius,obd,pyserial,pint,asynckivy,asyncgui

# Виключити з APK зайві каталоги
source.exclude_dirs = tests,.venv,.idea,.git,.buildozer,bin,emulator,__pycache__

# Ресурси та оформлення (Виправляють помилку Invalid ID 0x00000000)
# Якщо є свої файли в папці проєкту — розкоментуй та вкажи шляхи:
# icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #49535C

# Дозволи Android для роботи з Bluetoothms
android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

# Підтримка AndroidX (Обов'язково для KivyMD та MaterialYouColor)
android.enable_androidx = True

# Архітектури (спочатку лише arm64 — швидша збірка; для старих телефонів додайте armeabi-v7a)
android.archs = arm64-v8a

# Системні версії Android API
android.minapi = 21
android.api = 33
android.ndk = 25b
android.accept_sdk_license = True

# Увімкнути відображення помилок Traceback прямо на екрані при вильоті
android.logcat_filters = *:S python:D StandardOutput:I

# Орієнтація екрана
orientation = portrait
fullscreen = 0

[buildozer]

log_level = 2
warn_on_root = 1