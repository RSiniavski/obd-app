import math
import time
import obd
import config

class TelemetryReader:
    def __init__(self, connection):
        self.conn = connection
        self.start_time = time.time()

    def _get_mock_data(self) -> dict:
        t = time.time() - self.start_time
        coolant_val = int(88 + 15 * math.sin(t / 10))  # Моделюємо підйом температури до 103°C для тесту сповіщень
        return {
            "rpm": int(2150 + 1350 * math.sin(t / 2)),
            "speed": int(50 + 50 * math.sin(t / 4)),
            "coolant": coolant_val,
            "boost": round(0.2 + 1.2 * math.sin(t / 3), 2),  # Чистий наддув в bar
            "voltage": round(14.2 - 1.5 * abs(math.sin(t / 8)), 1) # Моделюємо просідання напруги
        }

    def read_metrics(self) -> dict:
        if config.IS_EMULATOR:
            return self._get_mock_data()

        if not self.conn or not self.conn.is_connected():
            return {"rpm": None, "speed": None, "coolant": None, "boost": None, "voltage": None}

        rpm = self.conn.query(obd.commands.RPM)
        speed = self.conn.query(obd.commands.SPEED)
        coolant = self.conn.query(obd.commands.COOLANT_TEMP)
        pressure = self.conn.query(obd.commands.INTAKE_PRESSURE)
        voltage = self.conn.query(obd.commands.CONTROL_MODULE_VOLTAGE)

        # Розрахунок чистого наддуву: MAP - 100 kPa (Атмосферний тиск) = Boost
        boost_val = None
        if pressure and not pressure.is_null():
            boost_bar = (pressure.value.magnitude - 101.3) / 100.0
            boost_val = max(0.0, round(boost_bar, 2))

        return {
            "rpm": int(rpm.value.magnitude) if rpm and not rpm.is_null() else None,
            "speed": int(speed.value.magnitude) if speed and not speed.is_null() else None,
            "coolant": int(coolant.value.magnitude) if coolant and not coolant.is_null() else None,
            "boost": boost_val,
            "voltage": round(float(voltage.value.magnitude), 1) if voltage and not voltage.is_null() else None
        }

    def read_dtc(self) -> list:
        if config.IS_EMULATOR:
            return [("P0300", "Random/Multiple Cylinder Misfire Detected")]

        if not self.conn or not self.conn.is_connected():
            return []

        dtc_response = self.conn.query(obd.commands.GET_DTC)
        if dtc_response and not dtc_response.is_null():
            return dtc_response.value
        return []

    def clear_dtc(self) -> bool:
        """Скидання помилок діагностики"""
        if config.IS_EMULATOR:
            return True

        if not self.conn or not self.conn.is_connected():
            return False

        response = self.conn.query(obd.commands.CLEAR_DTC)
        return not response.is_null()