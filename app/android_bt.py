import re


def _get_jnius():
    from jnius import autoclass
    return autoclass


class AndroidBluetoothOBD:
    """Bluetooth ELM327 connection for Android via PyJNiUS."""

    SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"

    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.socket = None
        self.input_stream = None
        self.output_stream = None
        self._connected = False

    def connect(self) -> bool:
        if not self.mac_address:
            print("[Android BT] MAC-адреса не задана (config.BLUETOOTH_MAC)")
            return False

        try:
            autoclass = _get_jnius()
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            UUID = autoclass('java.util.UUID')

            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                print("[Android BT] Bluetooth вимкнено або недоступний")
                return False

            adapter.cancelDiscovery()

            device = adapter.getRemoteDevice(self.mac_address)
            spp_uuid = UUID.fromString(self.SPP_UUID)
            self.socket = device.createRfcommSocketToServiceRecord(spp_uuid)
            self.socket.connect()

            self.input_stream = self.socket.getInputStream()
            self.output_stream = self.socket.getOutputStream()
            self._connected = self._init_elm327()
            return self._connected
        except Exception as e:
            print(f"[Android BT Error] Помилка з'єднання: {e}")
            self.disconnect()
            return False

    def _init_elm327(self) -> bool:
        for cmd in ["AT Z", "AT E0", "AT L0", "AT SP 0"]:
            if not self.send_command(cmd):
                return False
        return True

    def is_connected(self) -> bool:
        return self._connected and self.socket is not None

    def send_command(self, cmd: str) -> str:
        if not self.output_stream or not self.input_stream:
            return ""
        try:
            self.output_stream.write((cmd + "\r").encode('utf-8'))
            self.output_stream.flush()

            buffer = bytearray()
            while True:
                byte = self.input_stream.read()
                if byte == -1:
                    break
                buffer.append(byte)
                if byte == ord('>'):
                    break

            return buffer.decode('utf-8', errors='ignore').replace('>', '').strip()
        except Exception as e:
            print(f"[Android BT Error] Помилка передачі: {e}")
            self._connected = False
            return ""

    def _query_pid(self, mode: str, pid: str) -> list[int] | None:
        """Send OBD PID command and return data bytes after the mode/pid header."""
        response = self.send_command(f"{mode}{pid}")
        if not response or "NO DATA" in response.upper() or "UNABLE" in response.upper():
            return None

        hex_bytes = re.findall(r'[0-9A-Fa-f]{2}', response.replace(" ", ""))
        if len(hex_bytes) < 2:
            return None

        expected = int(f"{int(mode, 16) + 0x40:02X}{pid}", 16)
        actual = int(hex_bytes[0] + hex_bytes[1], 16)
        if actual != expected:
            return None

        return [int(b, 16) for b in hex_bytes[2:]]

    def read_metrics(self) -> dict:
        if not self.is_connected():
            return {
                "rpm": None,
                "speed": None,
                "coolant": None,
                "boost": None,
                "voltage": None,
                "iat": None,
                "rail_pressure": None,
                "maf": None,
                "engine_load": None,
                "throttle": None,
                "fuel_level": None,
                "oil_temp": None,
                "ambient_temp": None,
            }

        rpm_data = self._query_pid("01", "0C")
        speed_data = self._query_pid("01", "0D")
        coolant_data = self._query_pid("01", "05")
        pressure_data = self._query_pid("01", "0B")
        voltage_data = self._query_pid("01", "42")
        iat_data = self._query_pid("01", "0F")
        maf_data = self._query_pid("01", "10")
        load_data = self._query_pid("01", "04")
        throttle_data = self._query_pid("01", "11")
        fuel_data = self._query_pid("01", "2F")
        rail_data = self._query_pid("01", "23") or self._query_pid("01", "22")
        oil_data = self._query_pid("01", "5C")
        amb_data = self._query_pid("01", "46")

        boost_val = None
        if pressure_data and len(pressure_data) >= 1:
            boost_bar = (pressure_data[0] - 101.3) / 100.0
            boost_val = max(0.0, round(boost_bar, 2))

        rail_val = None
        if rail_data and len(rail_data) >= 2:
            raw_rail = (rail_data[0] * 256) + rail_data[1]
            rail_val = int(raw_rail * 0.1)

        return {
            "rpm": int(((rpm_data[0] * 256) + rpm_data[1]) / 4) if rpm_data and len(rpm_data) >= 2 else None,
            "speed": int(speed_data[0]) if speed_data and len(speed_data) >= 1 else None,
            "coolant": int(coolant_data[0] - 40) if coolant_data and len(coolant_data) >= 1 else None,
            "boost": boost_val,
            "voltage": round(((voltage_data[0] * 256) + voltage_data[1]) / 1000.0, 1) if voltage_data and len(voltage_data) >= 2 else None,
            "iat": int(iat_data[0] - 40) if iat_data and len(iat_data) >= 1 else None,
            "rail_pressure": rail_val,
            "maf": round(((maf_data[0] * 256) + maf_data[1]) / 100.0, 1) if maf_data and len(maf_data) >= 2 else None,
            "engine_load": int(load_data[0] * 100 / 255) if load_data and len(load_data) >= 1 else None,
            "throttle": int(throttle_data[0] * 100 / 255) if throttle_data and len(throttle_data) >= 1 else None,
            "fuel_level": int(fuel_data[0] * 100 / 255) if fuel_data and len(fuel_data) >= 1 else None,
            "oil_temp": int(oil_data[0] - 40) if oil_data and len(oil_data) >= 1 else None,
            "ambient_temp": int(amb_data[0] - 40) if amb_data and len(amb_data) >= 1 else None,
        }

    def read_dtc(self) -> list:
        if not self.is_connected():
            return []

        response = self.send_command("03")
        if not response or "NO DATA" in response.upper():
            return []

        hex_bytes = re.findall(r'[0-9A-Fa-f]{2}', response.replace(" ", ""))
        if len(hex_bytes) < 2 or hex_bytes[0] != "43":
            return []

        dtcs = []
        data = hex_bytes[2:]
        for i in range(0, len(data) - 1, 2):
            a, b = int(data[i], 16), int(data[i + 1], 16)
            if a == 0 and b == 0:
                break
            prefix = ["P", "C", "B", "U"][(a >> 6) & 0x03]
            code = f"{prefix}{(a & 0x3F):02X}{b:02X}"
            dtcs.append((code, ""))
        return dtcs

    def clear_dtc(self) -> bool:
        if not self.is_connected():
            return False
        response = self.send_command("04")
        return bool(response) and "44" in response.replace(" ", "").upper()

    def query(self, cmd):
        """Compatibility shim for code expecting python-obd OBD.query()."""
        from obd.OBDResponse import OBDResponse
        if not self.is_connected():
            return OBDResponse()

        response = self.send_command(cmd.command.decode() if isinstance(cmd.command, bytes) else str(cmd.command))
        if not response:
            return OBDResponse()

        hex_bytes = re.findall(r'[0-9A-Fa-f]{2}', response.replace(" ", ""))
        if not hex_bytes:
            return OBDResponse()

        try:
            from obd.protocols import ECU
            lines = [response.replace('\r', '').replace('\n', ' ').strip()]
            messages = ECU.UNKNOWN(lines)
            if messages:
                return cmd(messages)
        except Exception:
            pass
        return OBDResponse()

    def disconnect(self):
        try:
            if self.input_stream:
                self.input_stream.close()
            if self.output_stream:
                self.output_stream.close()
            if self.socket:
                self.socket.close()
        except Exception:
            pass
        finally:
            self.socket = None
            self.input_stream = None
            self.output_stream = None
            self._connected = False
