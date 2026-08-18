from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.navigationbar import MDNavigationBar, MDNavigationItem, MDNavigationItemIcon, MDNavigationItemLabel
from kivy.clock import Clock

import config
from app.connection import OBDConnectionManager
from app.reader import TelemetryReader


class MetricCard(MDCard):
    """Компонент картки для виводу метрики"""

    def __init__(self, title, unit="", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.unit = unit
        self.padding = 15
        self.spacing = 5
        self.style = "elevated"

        self.layout = MDBoxLayout(orientation="vertical")
        self.title_label = MDLabel(text=self.title, font_style="Label", role="medium", halign="center")
        self.value_label = MDLabel(text=f"0 {self.unit}".strip(), font_style="Headline", role="medium", halign="center")

        self.layout.add_widget(self.title_label)
        self.layout.add_widget(self.value_label)
        self.add_widget(self.layout)

    def update_value(self, val, style="Detailed"):
        formatted_val = f"{val} {self.unit}".strip()

        if style == "Compact":
            # Компактний стиль: назва і значення в один рядок
            self.title_label.text = ""
            self.value_label.font_style = "Title"
            self.value_label.role = "medium"
            self.value_label.text = f"{self.title}: {formatted_val}"
        else:
            # Детальний стиль: велика цифра, зверху назва
            self.title_label.text = self.title
            self.value_label.font_style = "Headline"
            self.value_label.role = "medium"
            self.value_label.text = formatted_val


class DashboardScreen(MDScreen):
    """Головний екран з показниками у вигляді карток"""

    def __init__(self, reader, **kwargs):
        super().__init__(**kwargs)
        self.reader = reader

        self.main_layout = MDBoxLayout(orientation='vertical', padding=15, spacing=10)

        # Створюємо картки для показників
        self.card_rpm = MetricCard(title="Оберти (RPM)", unit="")
        self.card_speed = MetricCard(title="Швидкість", unit="km/h")
        self.card_temp = MetricCard(title="Температура", unit="°C")
        self.card_boost = MetricCard(title="Наддув (Boost)", unit="bar")
        self.card_voltage = MetricCard(title="Напруга", unit="V")

        self.main_layout.add_widget(self.card_rpm)
        self.main_layout.add_widget(self.card_speed)
        self.main_layout.add_widget(self.card_temp)
        self.main_layout.add_widget(self.card_boost)
        self.main_layout.add_widget(self.card_voltage)

        self.add_widget(self.main_layout)

    def update_metrics(self, card_style):
        data = self.reader.read_metrics()
        if data:
            self.card_rpm.update_value(data.get('rpm') or 0, card_style)
            self.card_speed.update_value(data.get('speed') or 0, card_style)
            self.card_temp.update_value(data.get('coolant') or 0, card_style)
            self.card_boost.update_value(data.get('boost') or 0.0, card_style)
            self.card_voltage.update_value(data.get('voltage') or 0.0, card_style)


class DTCScreen(MDScreen):
    """Екран діагностики"""

    def __init__(self, reader, **kwargs):
        super().__init__(**kwargs)
        self.reader = reader

        layout = MDBoxLayout(orientation='vertical', padding=20, spacing=15)

        self.dtc_label = MDLabel(text="Натисніть 'Зчитати помилки'", halign="center", font_style="Body", role="large")

        read_btn = MDButton(on_release=self.read_dtc)
        read_btn.add_widget(MDButtonText(text="Зчитати помилки"))

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


class SettingsScreen(MDScreen):
    """Екран налаштувань додатка"""

    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref

        layout = MDBoxLayout(orientation='vertical', padding=20, spacing=20)

        title = MDLabel(text="Налаштування", font_style="Headline", role="small", halign="center")
        layout.add_widget(title)

        # Перемикач режиму симулятора
        sim_layout = MDBoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height="40dp")
        sim_label = MDLabel(text="Режим симулятора (Emulator):", font_style="Body", role="large")
        self.sim_switch = MDSwitch(active=config.IS_EMULATOR)
        self.sim_switch.bind(active=self.toggle_emulator)
        sim_layout.add_widget(sim_label)
        sim_layout.add_widget(self.sim_switch)

        # Перемикач вигляду карток
        style_layout = MDBoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height="40dp")
        style_label = MDLabel(text="Вигляд карток:", font_style="Body", role="large")

        btn_toggle_style = MDButton(on_release=self.toggle_card_style)
        self.style_btn_text = MDButtonText(text=getattr(config, 'CARD_STYLE', 'Detailed'))
        btn_toggle_style.add_widget(self.style_btn_text)

        style_layout.add_widget(style_label)
        style_layout.add_widget(btn_toggle_style)

        layout.add_widget(sim_layout)
        layout.add_widget(style_layout)
        layout.add_widget(MDBoxLayout())  # Пружина/заповнювач знизу

        self.add_widget(layout)

    def toggle_emulator(self, instance, value):
        config.IS_EMULATOR = value
        # Перепідключаємо считувач
        conn = OBDConnectionManager.get_connection()
        self.app_ref.reader = TelemetryReader(conn)
        self.app_ref.dashboard_screen.reader = self.app_ref.reader
        self.app_ref.dtc_screen.reader = self.app_ref.reader

    def toggle_card_style(self, instance):
        current = getattr(config, 'CARD_STYLE', 'Detailed')
        new_style = "Compact" if current == "Detailed" else "Detailed"
        config.CARD_STYLE = new_style
        self.style_btn_text.text = new_style


class DashboardApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        connection = OBDConnectionManager.get_connection()
        self.reader = TelemetryReader(connection)

        root_layout = MDBoxLayout(orientation='vertical')

        self.sm = MDScreenManager()

        self.dashboard_screen = DashboardScreen(self.reader, name="dashboard")
        self.dtc_screen = DTCScreen(self.reader, name="dtc")
        self.settings_screen = SettingsScreen(app_ref=self, name="settings")

        self.sm.add_widget(self.dashboard_screen)
        self.sm.add_widget(self.dtc_screen)
        self.sm.add_widget(self.settings_screen)

        # Нижня панель навігації (3 вкладки)
        nav_bar = MDNavigationBar()

        item_dash = MDNavigationItem(active=True)
        item_dash.add_widget(MDNavigationItemIcon(icon="gauge"))
        item_dash.add_widget(MDNavigationItemLabel(text="Дашборд"))
        item_dash.bind(on_release=lambda x: self.switch_screen("dashboard"))

        item_dtc = MDNavigationItem()
        item_dtc.add_widget(MDNavigationItemIcon(icon="car-wrench"))
        item_dtc.add_widget(MDNavigationItemLabel(text="Помилки"))
        item_dtc.bind(on_release=lambda x: self.switch_screen("dtc"))

        item_settings = MDNavigationItem()
        item_settings.add_widget(MDNavigationItemIcon(icon="cog"))
        item_settings.add_widget(MDNavigationItemLabel(text="Налаштування"))
        item_settings.bind(on_release=lambda x: self.switch_screen("settings"))

        nav_bar.add_widget(item_dash)
        nav_bar.add_widget(item_dtc)
        nav_bar.add_widget(item_settings)

        root_layout.add_widget(self.sm)
        root_layout.add_widget(nav_bar)

        Clock.schedule_interval(self.update_loop, 0.2)

        return root_layout

    def switch_screen(self, screen_name):
        self.sm.current = screen_name

    def update_loop(self, dt):
        if self.sm.current == "dashboard":
            card_style = getattr(config, 'CARD_STYLE', 'Detailed')
            self.dashboard_screen.update_metrics(card_style)


if __name__ == "__main__":
    DashboardApp().run()