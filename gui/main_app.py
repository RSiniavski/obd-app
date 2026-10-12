import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty, NumericProperty, ColorProperty, ListProperty
from kivy.graphics import Color, Line
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
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
    if "bluetooth_name" in conn:
        config.BLUETOOTH_NAME = str(conn.get("bluetooth_name") or "")

    saved_styles = data.get("metric_styles", {})
    if isinstance(saved_styles, dict):
        config.METRIC_STYLES.update(saved_styles)

    saved_enabled = data.get("enabled_metrics", {})
    if isinstance(saved_enabled, dict):
        config.ENABLED_METRICS.update(saved_enabled)

    cards = data.get("cards", {})
    # Старі збереження з columns=3 ламають UI на телефоні — нормалізуємо.
    if isinstance(cards, dict):
        for _key, cfg in cards.items():
            if isinstance(cfg, dict) and int(cfg.get("columns", 1) or 1) >= 3:
                cfg["columns"] = 1
    return cards


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
            "bluetooth_name": getattr(config, "BLUETOOTH_NAME", ""),
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
    card_height = NumericProperty(dp(120))
    card_width = NumericProperty(dp(160))
    card_columns = NumericProperty(1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._long_press_ev = None
        self.bind(card_columns=self._schedule_width_update)
        Clock.schedule_once(self._init_card, 0)

    def _init_card(self, dt):
        if not hasattr(config, "CARD_CONFIGS"):
            config.CARD_CONFIGS = load_settings()

        cfg = config.CARD_CONFIGS.get(self.key, {})
        if "height" in cfg:
            self.card_height = cfg["height"]
        if "columns" in cfg:
            # 3 колонки на телефоні ламають текст — обмежуємо до 2 за замовчуванням сітки
            cols = int(cfg["columns"])
            self.card_columns = 2 if cols >= 3 else max(1, cols)

        if self.parent:
            self.parent.bind(size=self._schedule_width_update)
        self.apply_style_layout()
        self._update_card_width()

    def _schedule_width_update(self, *args):
        Clock.schedule_once(lambda dt: self._update_card_width(), 0)

    def _update_card_width(self):
        parent = self.parent
        if not parent or parent.width <= 0:
            return

        n = max(1, int(self.card_columns))
        spacing = float(getattr(parent, "spacing", [0, 0])[0] or 0)
        padding = getattr(parent, "padding", [0, 0, 0, 0])
        pad_x = float(padding[0]) + float(padding[2]) if len(padding) >= 4 else float(padding[0]) * 2
        avail = max(0.0, float(parent.width) - pad_x - spacing * (n - 1))
        self.card_width = avail / n
        self._apply_fonts()

    def cycle_width_span(self):
        spans = [1, 2]
        try:
            curr_idx = spans.index(self.card_columns if self.card_columns in spans else 1)
            next_span = spans[(curr_idx + 1) % len(spans)]
        except ValueError:
            next_span = 1

        self.card_columns = next_span

        if self.key not in config.CARD_CONFIGS:
            config.CARD_CONFIGS[self.key] = {}
        config.CARD_CONFIGS[self.key]["columns"] = next_span
        save_settings()
        self._update_card_width()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.ud["metric_card"] = self
            self._long_press_ev = Clock.schedule_once(lambda dt: self._on_long_press(touch), 0.45)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._long_press_ev:
            self._long_press_ev.cancel()
            self._long_press_ev = None
        return super().on_touch_up(touch)

    def on_touch_move(self, touch):
        if touch.ud.get("metric_card") is self and self._long_press_ev:
            if abs(touch.dx) + abs(touch.dy) > dp(8):
                self._long_press_ev.cancel()
                self._long_press_ev = None
        return super().on_touch_move(touch)

    def _on_long_press(self, touch):
        self._long_press_ev = None
        if self.collide_point(*touch.pos):
            self.cycle_width_span()

    def _apply_fonts(self):
        if "title_lbl" not in self.ids or "value_lbl" not in self.ids:
            return

        mode = config.METRIC_STYLES.get(self.key, "text")
        w = max(1.0, float(self.card_width))
        title_size = 11 if w < dp(140) else 13
        if mode == "text":
            value_size = 26 if w < dp(140) else 32
        elif mode == "bar":
            value_size = 22 if w < dp(140) else 26
        else:
            value_size = 20 if w < dp(140) else 24

        self.ids.title_lbl.font_size = f"{title_size}sp"
        self.ids.value_lbl.font_size = f"{value_size}sp"

    def _set_layout(self, mode: str):
        if "title_lbl" not in self.ids or "value_lbl" not in self.ids or "visual_container" not in self.ids:
            return

        title = self.ids.title_lbl
        value = self.ids.value_lbl
        visual = self.ids.visual_container

        title.size_hint_y = None
        title.height = dp(22)
        title.opacity = 1

        if mode == "text":
            self.card_height = dp(100)
            self.ids.content_box.spacing = dp(6)
            value.size_hint_y = 1
            value.height = 0
            value.opacity = 1
            visual.size_hint_y = None
            visual.height = 0
        elif mode == "gauge":
            self.card_height = dp(140)
            self.ids.content_box.spacing = dp(2)
            value.size_hint_y = None
            value.height = 0
            value.opacity = 0
            visual.size_hint_y = 1
            visual.height = 0
        elif mode == "bar":
            self.card_height = dp(110)
            self.ids.content_box.spacing = dp(4)
            value.size_hint_y = 1
            value.height = 0
            value.opacity = 1
            visual.size_hint_y = None
            visual.height = dp(14)
        else:  # chart
            self.card_height = dp(140)
            self.ids.content_box.spacing = dp(4)
            value.size_hint_y = None
            value.height = dp(32)
            value.opacity = 1
            visual.size_hint_y = 1
            visual.height = 0

        self._apply_fonts()

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
            visual.height = 0
            visual.opacity = 0
            progress.height = chart.height = gauge.height = 0
            progress.opacity = chart.opacity = gauge.opacity = 0
        elif mode == "bar":
            visual.height = dp(14)
            visual.opacity = 1
            progress.height = dp(10)
            progress.opacity = 1
            chart.height = gauge.height = 0
            chart.opacity = gauge.opacity = 0
        elif mode == "chart":
            visual.opacity = 1
            chart.size_hint_y = 1
            chart.height = 0
            chart.opacity = 1
            progress.height = gauge.height = 0
            progress.opacity = gauge.opacity = 0
        elif mode == "gauge":
            visual.opacity = 1
            gauge.size_hint_y = 1
            gauge.height = 0
            gauge.opacity = 1
            progress.height = chart.height = 0
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
        value_color = self._value_color(val) if mode in {"bar", "chart", "gauge"} else [1, 1, 1, 1]

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
    status_color = ListProperty([0.2, 0.8, 0.2, 1])

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
                card._update_card_width()

        box.bind(size=self._relayout_cards)

    def _relayout_cards(self, *args):
        for card in self.cards_map.values():
            card._update_card_width()

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
        lower = (text or "").lower()
        if "помилка" in lower or "немає" in lower or "оберіть" in lower:
            self.status_color = [1.0, 0.45, 0.2, 1]
        elif "підключено" in lower:
            self.status_color = [0.2, 0.8, 0.2, 1]
        else:
            self.status_color = [0.75, 0.75, 0.75, 1]
        if "status_lbl" in self.ids:
            self.ids.status_lbl.text = text
            self.ids.status_lbl.color = self.status_color


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
        self._device_popup = None

    def on_enter(self, *args):
        self.is_emulator = config.IS_EMULATOR
        self._refresh_port_value()
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

    def _refresh_port_value(self):
        if self._is_android():
            name = getattr(config, "BLUETOOTH_NAME", "")
            mac = getattr(config, "BLUETOOTH_MAC", "")
            if name and mac:
                self.port_value = f"{name} ({mac})"
            else:
                self.port_value = mac or name or ""
        else:
            self.port_value = config.REAL_OBD_PORT or ""

    def _sync_mode_button(self):
        if "sim_btn" in self.ids:
            self.ids.sim_btn.text = "Режим: Емулятор" if self.is_emulator else "Режим: Реальне авто"
        if "port_hint_lbl" in self.ids:
            self.ids.port_hint_lbl.text = (
                "Адаптер:" if self._is_android() else "COM-порт:"
            )
        if "port_btn" in self.ids:
            self.ids.port_btn.text = "Обрати" if self._is_android() else "Порт"
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
        switching_to_real = config.IS_EMULATOR

        if switching_to_real and self._is_android() and not getattr(config, "BLUETOOTH_MAC", ""):
            # Спочатку вибір адаптера, підключення після вибору.
            config.IS_EMULATOR = False
            config.USE_TCP_EMULATOR = False
            self.is_emulator = False
            save_settings()
            self._sync_mode_button()
            self._refresh_status()
            self.select_device()
            return

        app.switch_data_source(use_emulator=not switching_to_real)
        self.is_emulator = config.IS_EMULATOR
        self._sync_mode_button()
        self._refresh_status()

    def select_device(self):
        """Android: список paired BT. Desktop: введення COM-порту."""
        if self._is_android():
            self._open_bt_picker()
        else:
            self._open_com_editor()

    def _open_com_editor(self):
        content = BoxLayout(orientation="vertical", spacing="8dp", padding="12dp")
        hint = Label(
            text="Вкажіть COM-порт ELM327 (наприклад COM5):",
            size_hint_y=None,
            height="28dp",
        )
        inp = TextInput(
            text=config.REAL_OBD_PORT or "",
            multiline=False,
            size_hint_y=None,
            height="40dp",
        )
        buttons = BoxLayout(orientation="horizontal", spacing="8dp", size_hint_y=None, height="40dp")

        popup = Popup(title="COM-порт", content=content, size_hint=(0.9, 0.35))

        def _save(_btn):
            port = (inp.text or "").strip()
            if port:
                config.REAL_OBD_PORT = port
                save_settings()
                self._refresh_port_value()
                self._sync_mode_button()
            popup.dismiss()
            if not config.IS_EMULATOR:
                self.reconnect()

        buttons.add_widget(Button(text="Скасувати", on_release=lambda *_: popup.dismiss()))
        buttons.add_widget(Button(text="Зберегти", on_release=_save))
        content.add_widget(hint)
        content.add_widget(inp)
        content.add_widget(buttons)
        popup.open()

    def _open_bt_picker(self):
        from app.android_bt import request_bt_permissions, list_bonded_devices

        self.connection_status = "Запит дозволів Bluetooth..."
        if "conn_status_lbl" in self.ids:
            self.ids.conn_status_lbl.text = self.connection_status

        def _after_permissions(ok, _perms):
            # Callback може прийти з Java-потоку — UI тільки через Clock.
            Clock.schedule_once(lambda dt: self._show_bt_device_list(ok), 0)

        request_bt_permissions(_after_permissions)

    def _show_bt_device_list(self, permissions_ok: bool):
        from app.android_bt import list_bonded_devices

        if self._device_popup:
            self._device_popup.dismiss()
            self._device_popup = None

        root = BoxLayout(orientation="vertical", spacing="8dp", padding="10dp")
        info = Label(
            text=(
                "Оберіть paired ELM327.\n"
                "Якщо списку немає — спочатку зв'яжіть адаптер у налаштуваннях Bluetooth телефону (PIN 1234/0000)."
                if permissions_ok
                else "Немає дозволів Bluetooth. Дозвольте їх у налаштуваннях додатка і спробуйте знову."
            ),
            size_hint_y=None,
            height="72dp",
            halign="left",
            valign="middle",
        )
        info.bind(size=info.setter("text_size"))
        root.add_widget(info)

        scroll = ScrollView(do_scroll_x=False)
        device_box = BoxLayout(orientation="vertical", spacing="6dp", size_hint_y=None)
        device_box.bind(minimum_height=device_box.setter("height"))
        scroll.add_widget(device_box)
        root.add_widget(scroll)

        popup = Popup(title="Bluetooth-адаптери", content=root, size_hint=(0.95, 0.8))
        self._device_popup = popup

        def _refresh_list(_btn=None):
            device_box.clear_widgets()
            devices = list_bonded_devices() if permissions_ok else []
            if not devices:
                device_box.add_widget(
                    Label(
                        text="Немає paired-пристроїв",
                        size_hint_y=None,
                        height="40dp",
                    )
                )
            for dev in devices:
                label = f"{dev['name']}\n{dev['mac']}"
                btn = Button(
                    text=label,
                    size_hint_y=None,
                    height="56dp",
                    halign="center",
                    on_release=lambda _b, d=dev: self._on_bt_device_chosen(d, popup),
                )
                device_box.add_widget(btn)

        actions = BoxLayout(orientation="horizontal", spacing="8dp", size_hint_y=None, height="40dp")
        actions.add_widget(Button(text="Оновити", on_release=_refresh_list))
        actions.add_widget(Button(text="Закрити", on_release=lambda *_: popup.dismiss()))
        root.add_widget(actions)

        _refresh_list()
        popup.open()
        self._refresh_status()

    def _on_bt_device_chosen(self, device: dict, popup: Popup):
        config.BLUETOOTH_MAC = device.get("mac", "")
        config.BLUETOOTH_NAME = device.get("name", "")
        config.IS_EMULATOR = False
        config.USE_TCP_EMULATOR = False
        save_settings()

        self.is_emulator = False
        self._refresh_port_value()
        self._sync_mode_button()
        popup.dismiss()
        self._device_popup = None

        self.connection_status = f"Підключення до {config.BLUETOOTH_NAME or config.BLUETOOTH_MAC}..."
        if "conn_status_lbl" in self.ids:
            self.ids.conn_status_lbl.text = self.connection_status

        self.reconnect()

    def reconnect(self):
        app = App.get_running_app()
        if self._is_android() and not config.IS_EMULATOR and not getattr(config, "BLUETOOTH_MAC", ""):
            self.select_device()
            return
        app.switch_data_source(use_emulator=config.IS_EMULATOR)
        self._refresh_port_value()
        self._sync_mode_button()
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