from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.clock import Clock

import config
from app.connection import OBDConnectionManager
from app.reader import TelemetryReader


class DashboardApp(MDApp):
    def build(self):
        # Темна тема KivyMD 2.0
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        # 1. Отримуємо об'єкт підключення
        connection = OBDConnectionManager.get_connection()

        # 2. Передаємо connection в TelemetryReader
        self.reader = TelemetryReader(connection)

        # Головний макет
        layout = MDBoxLayout(
            orientation='vertical',
            padding=30,
            spacing=15
        )

        # Метрики з оновленими стилями Material 3
        self.rpm_label = MDLabel(
            text="RPM: 0",
            halign="center",
            font_style="Display",
            role="medium"
        )
        self.speed_label = MDLabel(
            text="Speed: 0 km/h",
            halign="center",
            font_style="Headline",
            role="large"
        )
        self.temp_label = MDLabel(
            text="Coolant: 0 °C",
            halign="center",
            font_style="Title",
            role="large"
        )
        self.boost_label = MDLabel(
            text="Boost: 0 bar",
            halign="center",
            font_style="Title",
            role="large"
        )
        self.voltage_lavel = MDLabel(
            text="Voltage: 0 V",
            halign="center",
            font_style="Title",
            role="large"
        )

        layout.add_widget(self.rpm_label)
        layout.add_widget(self.speed_label)
        layout.add_widget(self.temp_label)
        layout.add_widget(self.boost_label)
        layout.add_widget(self.voltage_lavel)

        # Опитування даних кожні 0.2 секунди
        Clock.schedule_interval(self.update_metrics, 0.2)

        return layout

    def update_metrics(self, dt):
        # Викликаємо правильний метод з reader.py
        data = self.reader.read_metrics()

        if data:
            # Звертаємося до ключів маленькими літерами ("rpm", "speed", "coolant")
            rpm = data.get('rpm') or 0
            speed = data.get('speed') or 0
            coolant = data.get('coolant') or 0
            boost = data.get('boost') or 0
            voltage = data.get('voltage') or 0

            self.rpm_label.text = f"RPM: {rpm}"
            self.speed_label.text = f"Speed: {speed} km/h"
            self.temp_label.text = f"Coolant: {coolant} °C"
            self.boost_label.text = f"Boost: {boost} bar"
            self.voltage_lavel.text = f"Voltage: {voltage} V"


if __name__ == "__main__":
    DashboardApp().run()