import config

try:
    from kivy.utils import platform as kivy_platform
except ImportError:
    kivy_platform = "unknown"


def _is_android() -> bool:
    return kivy_platform == 'android'


def close_connection(conn) -> None:
    """Safely close an OBD / Bluetooth connection."""
    if conn is None:
        return
    try:
        if hasattr(conn, "disconnect"):
            conn.disconnect()
        elif hasattr(conn, "close"):
            conn.close()
    except Exception as e:
        print(f"[App] Помилка закриття з'єднання: {e}")


class OBDConnectionManager:
    @staticmethod
    def get_connection():
        if getattr(config, "IS_EMULATOR", False):
            if getattr(config, "USE_TCP_EMULATOR", False):
                import obd
                port = f"socket://{config.EMULATOR_HOST}:{config.EMULATOR_PORT}"
                print(f"[App] Підключення до TCP-емулятора на {port}...")
                return obd.OBD(portstr=port, check_voltage=False)
            print("[App] Запуск у режимі внутрішньої симуляції...")
            return None

        if _is_android():
            from app.android_bt import AndroidBluetoothOBD
            mac = getattr(config, 'BLUETOOTH_MAC', '')
            print(f"[App] Підключення до Android Bluetooth (MAC: {mac})...")
            conn = AndroidBluetoothOBD(mac)
            if conn.connect():
                return conn
            print("[App] Не вдалося підключитися через Bluetooth")
            return conn

        import obd
        print(f"[App] Підключення до реального OBD2 адаптера на {config.REAL_OBD_PORT}...")
        return obd.OBD(portstr=config.REAL_OBD_PORT)

    @staticmethod
    def connection_status(conn) -> str:
        """Human-readable status for the current data source."""
        if getattr(config, "IS_EMULATOR", False):
            if getattr(config, "USE_TCP_EMULATOR", False):
                if conn and hasattr(conn, "is_connected") and conn.is_connected():
                    return "TCP-емулятор: підключено"
                return "TCP-емулятор: немає зв'язку"
            return "Емулятор (симуляція)"

        if conn is None:
            return "Реальне авто: немає з'єднання"

        if hasattr(conn, "is_connected") and conn.is_connected():
            if _is_android():
                return f"Bluetooth: підключено ({config.BLUETOOTH_MAC or '?'})"
            return f"OBD: підключено ({config.REAL_OBD_PORT})"

        if _is_android():
            return f"Bluetooth: помилка ({config.BLUETOOTH_MAC or 'MAC не задано'})"
        return f"OBD: немає зв'язку ({config.REAL_OBD_PORT})"
