from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.navigationbar import MDNavigationBar, MDNavigationItem, MDNavigationItemIcon, MDNavigationItemLabel
from kivy.clock import Clock

import config
from app.connection import OBDConnectionManager
from app.reader import TelemetryReader


class DashboardScreen(MDScreen):
    """Головний екран з показниками"""

    def __init__(self, reader, **kwargs):
        super().__init__(**kwargs)
        self.reader = reader

        layout = MDBoxLayout(orientation='vertical', padding=20, spacing=10)

        self.rpm_label = MDLabel(text="RPM: 0", halign="center", font_style="Display", role="medium")
        self.speed_label = MDLabel(text="Speed: 0 km/h", halign="center", font_style="Headline", role="large")
        self.temp_label = MDLabel(text="Coolant: 0 °C", halign="center", font_style="Title", role="large")
        self.boost_label = MDLabel(text="Boost: 0.0 bar", halign="center", font_style="Title", role="medium")
        self.voltage_label = MDLabel(text="Voltage: 0.0 V", halign="center", font_style="Title", role="medium")

        layout.add_widget(self.rpm_label)
        layout.add_widget(self.speed_label)
        layout.add_widget(self.temp_label)
        layout.add_widget(self.boost_label)
        layout.add_widget(self.voltage_label)

        self.add_widget(layout)

    def update_metrics(self):
        data = self.reader.read_metrics()
        if data:
            self.rpm_label.text = f"RPM: {data.get('rpm') or 0}"
            self.speed_label.text = f"Speed: {data.get('speed') or 0} km/h"
            self.temp_label.text = f"Coolant: {data.get('coolant') or 0} °C"
            self.boost_label.text = f"Boost: {data.get('boost') or 0.0} bar"
            self.voltage_label.text = f"Voltage: {data.get('voltage') or 0.0} V"


class DTCScreen(MDScreen):
    """Екран діагностики та скидання помилок"""

    def __init__(self, reader, **kwargs):
        super().__init__(**kwargs)
        self.reader = reader

        layout = MDBoxLayout(orientation='vertical', padding=20, spacing=15)

        self.dtc_label = MDLabel(
            text="Натисніть 'Зчитати помилки'",
            halign="center",
            font_style="Body",
            role="large"
        )

        # Кнопка зчитування
        read_btn = MDButton(on_release=self.read_dtc)
        read_btn.add_widget(MDButtonText(text="Зчитати помилки"))

        # Кнопка скидання
        clear_btn = MDButton(on_release=self.clear_dtc)
        clear_btn.add_widget(MDButtonText(text="Скинути помилки (Clear DTC)"))

        layout.add_widget(self.dtc_label)
        layout.add_widget(read_btn)
        layout.add_widget(clear_btn)

        self.add_widget(layout)

    def read_dtc(self, instance):
        dtcs = self.reader.read_dtc()
        if dtcs:
            res = "Знайдені помилки:\n" + "\n".join([f"{code}: {desc}" for code, desc in dtcs])
            self.dtc_label.text = res
        else:
            self.dtc_label.text = "Помилок не знайдено!"

    def clear_dtc(self, instance):
        if self.reader.clear_dtc():
            self.dtc_label.text = "Помилки успішно скинуто!"
        else:
            self.dtc_label.text = "Помилка при скиданні."


class DashboardApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        connection = OBDConnectionManager.get_connection()
        self.reader = TelemetryReader(connection)

        # Головний макет додатка
        root_layout = MDBoxLayout(orientation='vertical')

        # Менеджер екранів
        self.sm = MDScreenManager()

        self.dashboard_screen = DashboardScreen(self.reader, name="dashboard")
        self.dtc_screen = DTCScreen(self.reader, name="dtc")

        self.sm.add_widget(self.dashboard_screen)
        self.sm.add_widget(self.dtc_screen)

        # Нижня панель навігації
        nav_bar = MDNavigationBar()

        item_dash = MDNavigationItem(active=True)
        item_dash.add_widget(MDNavigationItemIcon(icon="gauge"))
        item_dash.add_widget(MDNavigationItemLabel(text="Дашборд"))
        item_dash.bind(on_release=lambda x: self.switch_screen("dashboard"))

        item_dtc = MDNavigationItem()
        item_dtc.add_widget(MDNavigationItemIcon(icon="car-wrench"))
        item_dtc.add_widget(MDNavigationItemLabel(text="Помилки"))
        item_dtc.bind(on_release=lambda x: self.switch_screen("dtc"))

        nav_bar.add_widget(item_dash)
        nav_bar.add_widget(item_dtc)

        root_layout.add_widget(self.sm)
        root_layout.add_widget(nav_bar)

        # Опитування метрик тільки якщо відкритий екран дашборду
        Clock.schedule_interval(self.update_loop, 0.2)

        return root_layout

    def switch_screen(self, screen_name):
        self.sm.current = screen_name

    def update_loop(self, dt):
        if self.sm.current == "dashboard":
            self.dashboard_screen.update_metrics()


if __name__ == "__main__":
    DashboardApp().run()