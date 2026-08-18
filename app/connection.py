import config

class OBDConnectionManager:
    @staticmethod
    def get_connection():
        if config.IS_EMULATOR:
            print("[Connection] Запуск у режимі внутрішньої симуляції...")
            return None

        import obd

        print(f"[Connection] Підключення до реального OBD2 адаптера на {config.REAL_OBD_PORT}...")

        # Підключення з додатковими параметрами для стабільності ELM327
        connection = obd.OBD(
            portstr=config.REAL_OBD_PORT,
            baudrate=config.OBD_BAUDRATE,
            fast=False,   # Вимикаємо fast-mode для стабільності з дешевими ELM327
            timeout=30    # Таймаут на опитування ECU
        )

        if connection.is_connected():
            print(f"[Connection] ✅ Успішно підключено! Протокол: {connection.protocol_name()}")
        else:
            print("[Connection] ⚠️ Не вдалося з'єднатися з ECU. Перевірте, чи увімкнене запалювання!")

        return connection