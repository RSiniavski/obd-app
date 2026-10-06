import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty, NumericProperty, ColorProperty
from kivy.graphics import Color, Line
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen

import config
from app.connection import OBDConnectionManager, close_connection
from app.reader import TelemetryReader

SETTINGS_FILE = os.path.join(_ROOT, "settings.json")
KV_FILE = os.path.join(os.path.dirname(__file__), "ui_layout.kv")


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    conn = data.get("connection", {})
    if "is_emulator" in conn:
        config.IS_EMULATOR = bool(conn["is_emulator"])
    if "use_tcp_emulator" in conn:
        config.USE_TCP_EMULATOR = bool(conn["use_tcp_emulator"])
    if conn.get("obd_port"):
        config.REAL_OBD_PORT = str(conn["obd_port"])
    if "bluetooth_mac" in conn:
        config.BLUETOOTH_MAC = str(conn.get("bluetooth_mac") or "")

    saved_styles = data.get("metric_styles", {})
    if isinstance(saved_styles, dict):
        config.METRIC_STYLES.update(saved_styles)

    saved_enabled = data.get("enabled_metrics", {})
    if isinstance(saved_enabled, dict):
        config.ENABLED_METRICS.update(saved_enabled)

    return data.get("cards", {})


def save_settings():
    data = {
        "cards": getattr(config, "CARD_CONFIGS", {}),
        "metric_styles": config.METRIC_STYLES,
        "enabled_metrics": config.ENABLED_METRICS,
        "connection": {
            "is_emulator": bool(config.IS_EMULATOR),
            "use_tcp_emulator": bool(getattr(config, "USE_TCP_EMULATOR", False)),
            "obd_port": config.REAL_OBD_PORT,
            "bluetooth_mac": getattr(config, "BLUETOOTH_MAC", ""),
        },
    }
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[App] Не вдалося зберегти налаштування: {e}")


class MiniChartWidget(BoxLayout):
    def __init__(self, max_points=150, **kwargs):
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
            Color(0.996, 0.251, 0.0, 1)
            line_points = []
            width_step = self.width / (self.max_points - 1) if self.max_points > 1 else self.width

            for i, norm_val in enumerate(self.points_history):
                x = self.x + i * width_step
                y = self.y + norm_val * self.height
                line_points.extend([x, y])

            Line(points=line_points, width=1)


class MiniGaugeWidget(Widget):
    value_text = StringProperty("0")
    value_color = ColorProperty([1, 1, 1, 1])
    gauge_diameter = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.norm_value = 0.0
        self.bind(size=self.redraw, pos=self.redraw)

    def set_norm_value(self, norm_val):
        self.norm_value = max(0.0, min(1.0, norm_val))
        self.redraw()

    def redraw(self, *args):
        self.canvas.after.clear()
        d = min(self.width, self.height) - 16
        if d <= 0:
            self.gauge_diameter = 0
            return

        self.gauge_diameter = d
        x = self.x + (self.width - d) / 2
        y = self.y + (self.height - d) / 2

        with self.canvas.after:
            Color(0.3, 0.3, 0.3, 1)
            Line(ellipse=(x, y, d, d, -120, 120), width=3)

            angle = -120 + (self.norm_value * 240)
            Color(0.996, 0.251, 0.0, 1)
            Line(ellipse=(x, y, d, d, -120, angle), width=4)


if os.path.exists(KV_FILE):
    Builder.load_file(KV_FILE)


class MetricCard(BoxLayout):
    key = StringProperty("")
    title = StringProperty("")
    unit = StringProperty("")
    card_height = NumericProperty(130)
    card_columns = NumericProperty(2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self._init_card, 0)

    def _init_card(self, dt):
        if not hasattr(config, "CARD_CONFIGS"):
            config.CARD_CONFIGS = load_settings()

        cfg = config.CARD_CONFIGS.get(self.key, {})
        if "height" in cfg:
            self.card_height = cfg["height"]
        if "columns" in cfg:
            self.card_columns = int(cfg["columns"])

        self.apply_style_layout()

    def cycle_width_span(self):
        spans = [1, 2, 3]
        try:
            curr_idx = spans.index(self.card_columns)
            next_span = spans[(curr_idx + 1) % len(spans)]
        except ValueError:
            next_span = 2

        self.card_columns = next_span

        if self.key not in config.CARD_CONFIGS:
            config.CARD_CONFIGS[self.key] = {}
        config.CARD_CONFIGS[self.key]["columns"] = next_span
        save_settings()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.cycle_width_span()
            return True
        return super().on_touch_down(touch)

    def _set_layout(self, mode: str):
        """Відновлена логіка регулювання розмірів внутрішніх елементів для кожного режиму."""
        if "title_lbl" not in self.ids or "value_lbl" not in self.ids or "visual_container" not in self.ids:
            return

        title = self.ids.title_lbl
        value = self.ids.value_lbl
        visual = self.ids.visual_container

        title.size_hint_y = None
        title.height = "24dp"

        if mode == "text":
            self.ids.content_box.spacing = "14dp"
            value.size_hint_y = 1
            value.font_size = "34sp"
            visual.size_hint_y = None
        elif mode == "gauge":
            self.ids.content_box.spacing = "4dp"
            value.size_hint_y = None
            value.height = "0dp"
            value.opacity = 0
            visual.size_hint_y = 1
        elif mode == "bar":
            self.ids.content_box.spacing = "6dp"
            value.size_hint_y = 1
            value.font_size = "28sp"
            visual.size_hint_y = None
        else:  # chart
            self.ids.content_box.spacing = "6dp"
            value.size_hint_y = None
            value.height = "38dp"
            value.font_size = "28sp"
            visual.size_hint_y = 1

        if mode != "gauge":
            value.opacity = 1

    def apply_style_layout(self):
        mode = config.METRIC_STYLES.get(self.key, "text")
        self._set_layout(mode)

        if "visual_container" not in self.ids:
            return

        visual = self.ids.visual_container
        progress = self.ids.progress_bar
        chart = self.ids.chart_widget
        gauge = self.ids.gauge_widget

        progress.size_hint_y = None
        chart.size_hint_y = None
        gauge.size_hint_y = None

        if mode == "text":
            visual.height = "0dp"
            visual.opacity = 0
            progress.height = chart.height = gauge.height = "0dp"
            progress.opacity = chart.opacity = gauge.opacity = 0
        elif mode == "bar":
            visual.height = "12dp"
            visual.opacity = 1
            progress.height = "10dp"
            progress.opacity = 1
            chart.height = gauge.height = "0dp"
            chart.opacity = gauge.opacity = 0
        elif mode == "chart":
            visual.height = 0
            visual.opacity = 1
            chart.size_hint_y = 1
            chart.height = 0
            chart.opacity = 1
            progress.height = gauge.height = "0dp"
            progress.opacity = gauge.opacity = 0
        elif mode == "gauge":
            visual.height = 0
            visual.opacity = 1
            gauge.size_hint_y = 1
            gauge.height = 0
            gauge.opacity = 1
            progress.height = chart.height = "0dp"
            progress.opacity = chart.opacity = 0

    def _value_color(self, val):
        low, high = config.METRIC_CRITICAL_LIMITS.get(self.key, (None, None))
        if low is not None and val < low:
            return [0.26, 0.64, 0.96, 1]
        if high is not None and val > high:
            return [0.93, 0.32, 0.31, 1]
        return [1, 1, 1, 1]

    def update_value(self, val):
        if "value_lbl" not in self.ids:
            return

        if val is None:
            self.ids.value_lbl.text = "—"
            if "gauge_widget" in self.ids:
                self.ids.gauge_widget.value_text = "—"
            return

        mode = config.METRIC_STYLES.get(self.key, "text")
        value_text = str(val)
        value_color = self._value_color(val) if mode in {"bar", "chart"} else [1, 1, 1, 1]

        self.ids.value_lbl.text = value_text
        self.ids.value_lbl.color = value_color
        if "gauge_widget" in self.ids:
            self.ids.gauge_widget.value_text = value_text
            self.ids.gauge_widget.value_color = value_color

        min_val, max_val = config.METRIC_LIMITS.get(self.key, (0, 100))
        norm = (val - min_val) / (max_val - min_val if max_val != min_val else 1)

        if mode == "bar" and "progress_bar" in self.ids:
            self.ids.progress_bar.value = max(0, min(100, int(norm * 100)))
        elif mode == "chart" and "chart_widget" in self.ids:
            self.ids.chart_widget.add_value(val, min_val, max_val)
        elif mode == "gauge" and "gauge_widget" in self.ids:
            self.ids.gauge_widget.set_norm_value(norm)


class DashboardScreen(Screen):
    connection_status = StringProperty("...")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cards_map = {}
        Clock.schedule_once(lambda dt: self.rebuild_cards(), 0)

    def rebuild_cards(self):
        if "dashboard_box" not in self.ids:
            return

        box = self.ids.dashboard_box
        box.clear_widgets()
        self.cards_map = {}

        for key, info in config.METRICS_INFO.items():
            if config.ENABLED_METRICS.get(key, info.get("default_enabled", True)):
                card = MetricCard(
                    key=key,
                    title=info["name"],
                    unit=info["unit"],
                )
                self.cards_map[key] = card
                box.add_widget(card)

    def update_metrics(self, reader):
        data = reader.read_metrics()
        if not data:
            return

        if not self.cards_map and "dashboard_box" in self.ids:
            self.rebuild_cards()

        for key, card in self.cards_map.items():
            if key in data:
                card.update_value(data.get(key))

    def set_status(self, text: str):
        self.connection_status = text
        if "status_lbl" in self.ids:
            self.ids.status_lbl.text = text


class DTCScreen(Screen):
    def read_dtc(self):
        app = App.get_running_app()
        dtcs = app.reader.read_dtc()
        if dtcs:
            res = "Знайдені помилки:\n" + "\n".join([f"{code}: {desc}" for code, desc in dtcs])
            self.ids.dtc_label.text = res
        else:
            self.ids.dtc_label.text = "Помилок не знайдено!"

    def clear_dtc(self):
        app = App.get_running_app()
        if app.reader.clear_dtc():
            self.ids.dtc_label.text = "Помилки успішно скинуто!"
        else:
            self.ids.dtc_label.text = "Помилка при скиданні."


class SettingsScreen(Screen):
    is_emulator = BooleanProperty(True)
    connection_status = StringProperty("")
    port_value = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ui_built = False
        self.style_buttons = {}
        self.toggle_buttons = {}

    def on_enter(self, *args):
        self.is_emulator = config.IS_EMULATOR
        self.port_value = (
            getattr(config, "BLUETOOTH_MAC", "")
            if self._is_android()
            else config.REAL_OBD_PORT
        )
        self._refresh_status()
        if not self._ui_built:
            self.build_settings_ui()
            self._ui_built = True
        self._sync_mode_button()

    @staticmethod
    def _is_android() -> bool:
        try:
            from kivy.utils import platform
            return platform == "android"
        except ImportError:
            return False

    def _sync_mode_button(self):
        if "sim_btn" in self.ids:
            self.ids.sim_btn.text = "Режим: Емулятор" if self.is_emulator else "Режим: Реальне авто"
        if "port_hint_lbl" in self.ids:
            self.ids.port_hint_lbl.text = (
                "Bluetooth MAC:" if self._is_android() else "COM-порт:"
            )
        if "port_value_lbl" in self.ids:
            self.ids.port_value_lbl.text = self.port_value or "(не задано)"

    def _refresh_status(self):
        app = App.get_running_app()
        if app and hasattr(app, "connection"):
            self.connection_status = OBDConnectionManager.connection_status(app.connection)
        else:
            self.connection_status = OBDConnectionManager.connection_status(None)
        if "conn_status_lbl" in self.ids:
            self.ids.conn_status_lbl.text = self.connection_status

    def build_settings_ui(self):
        if "metrics_settings_box" not in self.ids:
            return

        self.style_buttons = {}
        self.toggle_buttons = {}
        box = self.ids.metrics_settings_box
        box.clear_widgets()

        for key, info in config.METRICS_INFO.items():
            is_enabled = config.ENABLED_METRICS.get(key, info.get("default_enabled", True))
            curr_style = config.METRIC_STYLES.get(key, info.get("default_style", "text"))

            row = BoxLayout(
                orientation="horizontal",
                spacing="8dp",
                size_hint_y=None,
                height="44dp",
            )

            toggle_btn = Button(
                text="ВКЛ" if is_enabled else "ВИКЛ",
                size_hint_x=None,
                width="72dp",
                size_hint_y=None,
                height="36dp",
                on_release=lambda x, k=key: self.toggle_metric_enabled(k),
            )
            self.toggle_buttons[key] = toggle_btn

            lbl = Label(
                text=f"{info['name']} ({info['unit']}):" if info['unit'] else f"{info['name']}:",
                size_hint_y=None,
                height="40dp",
                halign="left",
                valign="middle",
            )
            lbl.bind(size=lbl.setter("text_size"))

            style_btn = Button(
                text=curr_style.upper(),
                size_hint_x=None,
                width="84dp",
                size_hint_y=None,
                height="36dp",
                on_release=lambda x, k=key: self.cycle_metric_style(k),
            )
            self.style_buttons[key] = style_btn

            row.add_widget(toggle_btn)
            row.add_widget(lbl)
            row.add_widget(style_btn)
            box.add_widget(row)

    def toggle_metric_enabled(self, key):
        new_state = not config.ENABLED_METRICS.get(key, True)
        config.ENABLED_METRICS[key] = new_state

        if key in self.toggle_buttons:
            self.toggle_buttons[key].text = "ВКЛ" if new_state else "ВИКЛ"

        app = App.get_running_app()
        if hasattr(app, "dashboard_screen"):
            app.dashboard_screen.rebuild_cards()

        save_settings()

    def cycle_metric_style(self, key):
        modes = ["text", "bar", "gauge", "chart"]
        curr = config.METRIC_STYLES.get(key, "text")
        next_mode = modes[(modes.index(curr) + 1) % len(modes)]

        config.METRIC_STYLES[key] = next_mode
        if key in self.style_buttons:
            self.style_buttons[key].text = next_mode.upper()

        app = App.get_running_app()
        if hasattr(app, "dashboard_screen") and key in app.dashboard_screen.cards_map:
            app.dashboard_screen.cards_map[key].apply_style_layout()

        save_settings()

    def toggle_emulator(self):
        app = App.get_running_app()
        use_emulator = not config.IS_EMULATOR
        app.switch_data_source(use_emulator=use_emulator)
        self.is_emulator = config.IS_EMULATOR
        self._sync_mode_button()
        self._refresh_status()

    def reconnect(self):
        app = App.get_running_app()
        app.switch_data_source(use_emulator=config.IS_EMULATOR)
        self._refresh_status()


class DashboardApp(App):
    def build(self):
        if not hasattr(config, "CARD_CONFIGS"):
            config.CARD_CONFIGS = load_settings()

        self.connection = OBDConnectionManager.get_connection()
        self.reader = TelemetryReader(self.connection)

        root_layout = BoxLayout(orientation="vertical")

        self.sm = ScreenManager()

        self.dashboard_screen = DashboardScreen(name="dashboard")
        self.dtc_screen = DTCScreen(name="dtc")
        self.settings_screen = SettingsScreen(name="settings")

        self.sm.add_widget(self.dashboard_screen)
        self.sm.add_widget(self.dtc_screen)
        self.sm.add_widget(self.settings_screen)

        nav_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height="50dp", spacing="4dp")

        btn_dash = Button(text="Дашборд", on_release=lambda x: self.switch_screen("dashboard"))
        btn_dtc = Button(text="Помилки", on_release=lambda x: self.switch_screen("dtc"))
        btn_settings = Button(text="Налаштування", on_release=lambda x: self.switch_screen("settings"))

        nav_bar.add_widget(btn_dash)
        nav_bar.add_widget(btn_dtc)
        nav_bar.add_widget(btn_settings)

        root_layout.add_widget(self.sm)
        root_layout.add_widget(nav_bar)

        Clock.schedule_once(lambda dt: self._refresh_status_ui(), 0)
        Clock.schedule_once(lambda dt: self.dashboard_screen.rebuild_cards(), 0)
        Clock.schedule_interval(self.update_loop, 0.2)

        return root_layout

    def switch_data_source(self, use_emulator: bool):
        close_connection(getattr(self, "connection", None))

        config.IS_EMULATOR = use_emulator
        if use_emulator:
            config.USE_TCP_EMULATOR = False

        self.connection = OBDConnectionManager.get_connection()
        self.reader = TelemetryReader(self.connection)
        save_settings()
        self._refresh_status_ui()

    def _refresh_status_ui(self):
        status = OBDConnectionManager.connection_status(self.connection)
        self.dashboard_screen.set_status(status)
        if hasattr(self, "settings_screen"):
            self.settings_screen.connection_status = status
            if "conn_status_lbl" in self.settings_screen.ids:
                self.settings_screen.ids.conn_status_lbl.text = status

    def switch_screen(self, screen_name):
        self.sm.current = screen_name

    def update_loop(self, dt):
        if self.sm.current == "dashboard":
            self.dashboard_screen.update_metrics(self.reader)

    def on_stop(self):
        close_connection(getattr(self, "connection", None))


if __name__ == "__main__":
    DashboardApp().run()