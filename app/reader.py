import math
import time
import config

try:
    import obd
except ImportError:
    obd = None

try:
    from app.android_bt import AndroidBluetoothOBD
except ImportError:
    AndroidBluetoothOBD = None


class TelemetryReader:
    def __init__(self, connection):
        self.conn = connection
        self.start_time = time.time()

    def _is_android_bt(self) -> bool:
        return AndroidBluetoothOBD is not None and isinstance(self.conn, AndroidBluetoothOBD)

    def _connection_ready(self) -> bool:
        if not self.conn:
            return False
        if self._is_android_bt():
            return self.conn.is_connected()
        return self.conn.is_connected()

    def _get_mock_data(self) -> dict:
        t = time.time() - self.start_time
        rpm = int(2150 + 1350 * math.sin(t / 2))
        speed = max(0, int(50 + 50 * math.sin(t / 4)))
        coolant = int(88 + 5 * math.sin(t / 12))
        boost = max(0.0, round(0.3 + 1.1 * (math.sin(t / 3) ** 2), 2))
        voltage = round(14.2 - 0.4 * abs(math.sin(t / 8)), 1)
        iat = int(32 + 8 * math.sin(t / 15))
        rail_pressure = int(350 + 900 * max(0.0, (rpm - 800) / 3700.0) + 100 * math.sin(t / 2))
        rail_pressure = max(280, min(1650, rail_pressure))
        maf = round(max(8.0, min(180.0, 12.0 + (rpm / 35.0) + 20.0 * boost)), 1)
        engine_load = int(max(10, min(100, 20 + 60 * (boost / 1.4))))
        throttle = int(max(0, min(100, 20 + 45 * math.sin(t / 3))))
        fuel_level = 62
        oil_temp = int(90 + 4 * math.sin(t / 20))
        ambient_temp = 19

        return {
            "rpm": rpm,
            "speed": speed,
            "coolant": coolant,
            "boost": boost,
            "voltage": voltage,
            "iat": iat,
            "rail_pressure": rail_pressure,
            "maf": maf,
            "engine_load": engine_load,
            "throttle": throttle,
            "fuel_level": fuel_level,
            "oil_temp": oil_temp,
            "ambient_temp": ambient_temp,
        }

    def read_metrics(self) -> dict:
        if config.IS_EMULATOR and not getattr(config, "USE_TCP_EMULATOR", False):
            return self._get_mock_data()

        if self._is_android_bt():
            return self.conn.read_metrics()

        if not self._connection_ready() or obd is None:
            return {k: None for k in config.METRICS_INFO.keys()}

        def _safe_query(cmd_attr):
            try:
                cmd = getattr(obd.commands, cmd_attr, None)
                if cmd is None:
                    return None
                resp = self.conn.query(cmd)
                if resp and not resp.is_null() and hasattr(resp.value, "magnitude"):
                    return resp.value.magnitude
                return None
            except Exception:
                return None

        rpm = _safe_query("RPM")
        speed = _safe_query("SPEED")
        coolant = _safe_query("COOLANT_TEMP")
        pressure = _safe_query("INTAKE_PRESSURE")
        voltage = _safe_query("CONTROL_MODULE_VOLTAGE")
        iat = _safe_query("INTAKE_TEMP")
        maf = _safe_query("MAF")
        load = _safe_query("ENGINE_LOAD")
        throttle = _safe_query("THROTTLE_POS")
        fuel = _safe_query("FUEL_LEVEL")
        oil_temp = _safe_query("OIL_TEMP")
        amb_temp = _safe_query("AMBIANT_AIR_TEMP")
        baro = _safe_query("BAROMETRIC_PRESSURE")

        rail_kpa = _safe_query("FUEL_RAIL_PRESSURE_DIRECT")
        if rail_kpa is None:
            rail_kpa = _safe_query("FUEL_RAIL_PRESSURE_VACUUM")

        rail_bar = None
        if rail_kpa is not None:
            rail_bar = int(rail_kpa / 100.0) if rail_kpa > 1000 else int(rail_kpa * 0.1)

        boost_val = None
        if pressure is not None:
            baro_kpa = baro if baro is not None else 101.3
            boost_bar = (pressure - baro_kpa) / 100.0
            boost_val = max(0.0, round(boost_bar, 2))

        return {
            "rpm": int(rpm) if rpm is not None else None,
            "speed": int(speed) if speed is not None else None,
            "coolant": int(coolant) if coolant is not None else None,
            "boost": boost_val,
            "voltage": round(float(voltage), 1) if voltage is not None else None,
            "iat": int(iat) if iat is not None else None,
            "rail_pressure": rail_bar,
            "maf": round(float(maf), 1) if maf is not None else None,
            "engine_load": int(load) if load is not None else None,
            "throttle": int(throttle) if throttle is not None else None,
            "fuel_level": int(fuel) if fuel is not None else None,
            "oil_temp": int(oil_temp) if oil_temp is not None else None,
            "ambient_temp": int(amb_temp) if amb_temp is not None else None,
        }

    def read_dtc(self) -> list:
        if config.IS_EMULATOR and not getattr(config, "USE_TCP_EMULATOR", False):
            return [("P0300", "Random/Multiple Cylinder Misfire Detected")]

        if self._is_android_bt():
            return self.conn.read_dtc()

        if not self._connection_ready() or obd is None:
            return []

        dtc_response = self.conn.query(obd.commands.GET_DTC)
        if dtc_response and not dtc_response.is_null():
            return dtc_response.value
        return []

    def clear_dtc(self) -> bool:
        if config.IS_EMULATOR and not getattr(config, "USE_TCP_EMULATOR", False):
            return True

        if self._is_android_bt():
            return self.conn.clear_dtc()

        if not self._connection_ready() or obd is None:
            return False

        response = self.conn.query(obd.commands.CLEAR_DTC)
        return not response.is_null()
