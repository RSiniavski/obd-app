import config

class OBDConnectionManager:
    @staticmethod
    def get_connection():
        if config.IS_EMULATOR:
            print("[App] Запуск у режимі внутрішньої симуляції...")
            return None
        else:
            import obd
            print(f"[App] Підключення до реального OBD2 адаптера на {config.REAL_OBD_PORT}...")
            return obd.OBD(portstr=config.REAL_OBD_PORT)