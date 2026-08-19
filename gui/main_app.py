import os
import json
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty, NumericProperty
from kivy.graphics import Color, Line

from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.navigationbar import MDNavigationBar, MDNavigationItem, MDNavigationItemIcon, MDNavigationItemLabel
from kivymd.uix.boxlayout import MDBoxLayout

import config
from app.connection import OBDConnectionManager
from app.reader import TelemetryReader

SETTINGS_FILE = "settings.json"


def load_saved_card_configs():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("cards", {})
        except Exception:
            pass
    return {}


def save_card_configs():
    data = {"cards": getattr(config, "CARD_CONFIGS", {})}
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass


class MiniChartWidget(MDBoxLayout):
    def __init__(self, max_points=30, **kwargs):
        super().__init__(**kwargs)
        self.max_points = max_points
        self.points_history = []
        self.bind(size=self.redraw, pos=self.redraw)

    def add_value(self, val, min_val, max_val):
        norm_val = max(0.0, min(1.0, (val - min_val) / (max_val - min_val if max_val != min_val else 1)))
        self.points_history.append(norm_val)
        if len(self.points_history) > self.max_points:
            self.points_history.pop(0)
        self.redraw()

    def redraw(self, *args):
        self.canvas.after.clear()
        if len(self.points_history) < 2 or self.height <= 0:
            return

        with self.canvas.after:
            Color(0.2, 0.6, 1.0, 1)
            line_points = []
            width_step = self.width / (self.max_points - 1) if self.max_points > 1 else self.width

            for i, norm_val in enumerate(self.points_history):
                x = self.x + i * width_step
                y = self.y + (norm_val * (self.height - 10)) + 5
                line_points.extend([x, y])

            Line(points=line_points, width=2)


class MiniGaugeWidget(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.norm_value = 0.0
        self.bind(size=self.redraw, pos=self.redraw)

    def set_norm_value(self, norm_val):
        self.norm_value = max(0.0, min(1.0, norm_val))
        self.redraw()

    def redraw(self, *args):
        self.canvas.after.clear()
        d = min(self.width, self.height) - 4
        if d <= 0:
            return

        x = self.x + (self.width - d) / 2
        y = self.y + (self.height - d) / 2

        with self.canvas.after:
            Color(0.3, 0.3, 0.3, 1)
            Line(ellipse=(x, y, d, d, -120, 120), width=3)

            angle = -120 + (self.norm_value * 240)
            Color(0.2, 0.7, 1.0, 1)
            Line(ellipse=(x, y, d, d, -120, angle), width=4)


KV_FILE = os.path.join(os.path.dirname(__file__), "ui_layout.kv")
Builder.load_file(KV_FILE)


class MetricCard(MDCard):
    key = StringProperty("")
    title = StringProperty("")
    unit = StringProperty("")
    card_height = NumericProperty(130)
    card_size_hint_x = NumericProperty(0.475)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._resizing = False
        self._initial_mouse_y = 0
        self._initial_card_height = 130
        Clock.schedule_once(self._init_card, 0)

    def _init_card(self, dt):
        if not hasattr(config, "CARD_CONFIGS"):
            config.CARD_CONFIGS = load_saved_card_configs()

        cfg = config.CARD_CONFIGS.get(self.key, {})
        if "height" in cfg:
            self.card_height = cfg["height"]
        if "size_hint_x" in cfg:
            self.card_size_hint_x = cfg["size_hint_x"]

        self.apply_style_layout()

    def cycle_width_span(self):
        # Точні розраховані значення для симетричного перемикання
        spans = [1.0, 0.475, 0.31]
        try:
            curr_idx = spans.index(round(self.card_size_hint_x, 3))
            next_span = spans[(curr_idx + 1) % len(spans)]
        except ValueError:
            next_span = 0.475

        self.card_size_hint_x = next_span

        if self.key not in config.CARD_CONFIGS:
            config.CARD_CONFIGS[self.key] = {}
        config.CARD_CONFIGS[self.key]["size_hint_x"] = next_span
        save_card_configs()

    def on_touch_down(self, touch):
        if self.ids.resize_handle.collide_point(*touch.pos):
            self._resizing = True
            self._initial_mouse_y = touch.y
            self._initial_card_height = self.card_height
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self and self._resizing:
            delta_y = self._initial_mouse_y - touch.y
            new_height = max(100, min(500, self._initial_card_height + delta_y))

            self.card_height = new_height
            if self.key not in config.CARD_CONFIGS:
                config.CARD_CONFIGS[self.key] = {}
            config.CARD_CONFIGS[self.key]["height"] = new_height
            self.apply_style_layout()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._resizing = False
            save_card_configs()
            return True
        return super().on_touch_up(touch)

    def apply_style_layout(self):
        mode = config.METRIC_STYLES.get(self.key, "text")

        if mode == "text":
            self.ids.visual_container.height = "0dp"
            self.ids.visual_container.opacity = 0
            self.ids.progress_bar.height = "0dp"
            self.ids.progress_bar.opacity = 0
            self.ids.chart_widget.height = "0dp"
            self.ids.chart_widget.opacity = 0
            self.ids.gauge_widget.height = "0dp"
            self.ids.gauge_widget.opacity = 0

        elif mode == "bar":
            self.ids.visual_container.height = "12dp"
            self.ids.visual_container.opacity = 1
            self.ids.progress_bar.height = "10dp"
            self.ids.progress_bar.opacity = 1
            self.ids.chart_widget.height = "0dp"
            self.ids.chart_widget.opacity = 0
            self.ids.gauge_widget.height = "0dp"
            self.ids.gauge_widget.opacity = 0

        elif mode == "chart":
            chart_h = max(20, self.card_height - 85)
            self.ids.visual_container.height = f"{chart_h}dp"
            self.ids.visual_container.opacity = 1
            self.ids.progress_bar.height = "0dp"
            self.ids.progress_bar.opacity = 0
            self.ids.chart_widget.height = f"{chart_h}dp"
            self.ids.chart_widget.opacity = 1
            self.ids.gauge_widget.height = "0dp"
            self.ids.gauge_widget.opacity = 0

        elif mode == "gauge":
            gauge_h = max(20, self.card_height - 85)
            self.ids.visual_container.height = f"{gauge_h}dp"
            self.ids.visual_container.opacity = 1
            self.ids.progress_bar.height = "0dp"
            self.ids.progress_bar.opacity = 0
            self.ids.chart_widget.height = "0dp"
            self.ids.chart_widget.opacity = 0
            self.ids.gauge_widget.height = f"{gauge_h}dp"
            self.ids.gauge_widget.opacity = 1

    def update_value(self, val):
        unit_str = f" {self.unit}".strip()
        self.ids.value_lbl.text = f"{val}{unit_str}"

        mode = config.METRIC_STYLES.get(self.key, "text")
        min_val, max_val = config.METRIC_LIMITS.get(self.key, (0, 100))
        norm = (val - min_val) / (max_val - min_val if max_val != min_val else 1)

        if mode == "bar":
            self.ids.progress_bar.value = max(0, min(100, int(norm * 100)))
        elif mode == "chart":
            self.ids.chart_widget.add_value(val, min_val, max_val)
        elif mode == "gauge":
            self.ids.gauge_widget.set_norm_value(norm)


class DashboardScreen(MDScreen):
    def update_metrics(self, reader):
        data = reader.read_metrics()
        if data:
            if 'card_rpm' in self.ids:
                self.ids.card_rpm.update_value(data.get('rpm') or 0)
            if 'card_speed' in self.ids:
                self.ids.card_speed.update_value(data.get('speed') or 0)
            if 'card_coolant' in self.ids:
                self.ids.card_coolant.update_value(data.get('coolant') or 0)
            if 'card_boost' in self.ids:
                self.ids.card_boost.update_value(data.get('boost') or 0.0)
            if 'card_voltage' in self.ids:
                self.ids.card_voltage.update_value(data.get('voltage') or 0.0)


class DTCScreen(MDScreen):
    def read_dtc(self):
        app = MDApp.get_running_app()
        dtcs = app.reader.read_dtc()
        if dtcs:
            res = "Знайдені помилки:\n" + "\n".join([f"{code}: {desc}" for code, desc in dtcs])
            self.ids.dtc_label.text = res
        else:
            self.ids.dtc_label.text = "Помилок не знайдено!"

    def clear_dtc(self):
        app = MDApp.get_running_app()
        if app.reader.clear_dtc():
            self.ids.dtc_label.text = "Помилки успішно скинуто!"
        else:
            self.ids.dtc_label.text = "Помилка при скиданні."


class SettingsScreen(MDScreen):
    is_emulator = BooleanProperty(config.IS_EMULATOR)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ui_built = False

    def on_enter(self, *args):
        if not self._ui_built:
            self.build_settings_ui()
            self._ui_built = True

    def build_settings_ui(self):
        if 'metrics_settings_box' not in self.ids:
            return

        self.style_buttons = {}
        box = self.ids.metrics_settings_box
        box.clear_widgets()

        metrics = [
            ("rpm", "Оберти"),
            ("speed", "Швидкість"),
            ("coolant", "Температура"),
            ("boost", "Наддув"),
            ("voltage", "Напруга")
        ]

        for key, name in metrics:
            row = MDBoxLayout(
                orientation='horizontal',
                spacing="10dp",
                size_hint_y=None,
                height="40dp"
            )

            lbl = MDLabel(
                text=f"{name}:",
                font_style="Body",
                role="medium",
                size_hint_y=None,
                height="40dp"
            )

            curr_style = config.METRIC_STYLES.get(key, "text")
            btn = MDButton(
                on_release=lambda x, k=key: self.cycle_metric_style(k),
                size_hint_y=None,
                height="36dp"
            )
            btn_text = MDButtonText(text=curr_style.upper())
            btn.add_widget(btn_text)
            self.style_buttons[key] = btn_text

            row.add_widget(lbl)
            row.add_widget(btn)
            box.add_widget(row)

    def toggle_emulator(self):
        config.IS_EMULATOR = not config.IS_EMULATOR
        self.is_emulator = config.IS_EMULATOR

        app = MDApp.get_running_app()
        conn = OBDConnectionManager.get_connection()
        app.reader = TelemetryReader(conn)

    def cycle_metric_style(self, key):
        modes = ["text", "bar", "gauge", "chart"]
        curr = config.METRIC_STYLES.get(key, "text")
        next_mode = modes[(modes.index(curr) + 1) % len(modes)]

        config.METRIC_STYLES[key] = next_mode
        if key in self.style_buttons:
            self.style_buttons[key].text = next_mode.upper()

        app = MDApp.get_running_app()
        card_id = f"card_{key}"
        if card_id in app.dashboard_screen.ids:
            app.dashboard_screen.ids[card_id].apply_style_layout()


class DashboardApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        connection = OBDConnectionManager.get_connection()
        self.reader = TelemetryReader(connection)

        root_layout = MDBoxLayout(orientation='vertical')

        self.sm = MDScreenManager()

        self.dashboard_screen = DashboardScreen(name="dashboard")
        self.dtc_screen = DTCScreen(name="dtc")
        self.settings_screen = SettingsScreen(name="settings")

        self.sm.add_widget(self.dashboard_screen)
        self.sm.add_widget(self.dtc_screen)
        self.sm.add_widget(self.settings_screen)

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
            self.dashboard_screen.update_metrics(self.reader)


if __name__ == "__main__":
    DashboardApp().run()