from kivy.utils import platform
import config

class OBDConnectionManager:
    @staticmethod
    def get_connection():
        if getattr(config, "IS_EMULATOR", False):
            print("[App] Запуск у режимі внутрішньої симуляції...")
            return None
        elif platform == 'android':
            from app.android_bt import AndroidBluetoothOBD
            mac = getattr(config, 'BLUETOOTH_MAC', '')
            print(f"[App] Підключення до Android Bluetooth (MAC: {mac})...")
            return AndroidBluetoothOBD(mac)
        else:
            import obd
            print(f"[App] Підключення до реального OBD2 адаптера на {config.REAL_OBD_PORT}...")
            return obd.OBD(portstr=config.REAL_OBD_PORT)