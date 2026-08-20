from jnius import autoclass

# Отримуємо доступ до нативних класів Android через PyJNiUS
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
BluetoothSocket = autoclass('android.bluetooth.BluetoothSocket')
UUID = autoclass('java.util.UUID')


class AndroidBluetoothOBD:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.socket = None
        self.input_stream = None
        self.output_stream = None
        # SPP UUID для ELM327
        self.spp_uuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")

    def connect(self) -> bool:
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                print("[Android BT] Bluetooth вимкнено або недоступний")
                return False

            # Зупиняємо сканування для прискорення передачі даних
            adapter.cancelDiscovery()

            device = adapter.getRemoteDevice(self.mac_address)
            self.socket = device.createRfcommSocketToServiceRecord(self.spp_uuid)
            self.socket.connect()

            self.input_stream = self.socket.getInputStream()
            self.output_stream = self.socket.getOutputStream()

            return self._init_elm327()
        except Exception as e:
            print(f"[Android BT Error] Помилка з'єднання: {e}")
            self.disconnect()
            return False

    def _init_elm327(self) -> bool:
        init_cmds = ["AT Z", "AT E0", "AT L0", "AT SP 0"]
        for cmd in init_cmds:
            res = self.send_command(cmd)
            if not res:
                return False
        return True

    def send_command(self, cmd: str) -> str:
        if not self.output_stream or not self.input_stream:
            return ""
        try:
            # Відправка команди з переносом каретки \r
            full_cmd = (cmd + "\r").encode('utf-8')
            self.output_stream.write(full_cmd)
            self.output_stream.flush()

            # Читання відповіді до промпта '>'
            buffer = bytearray()
            while True:
                byte = self.input_stream.read()
                if byte == -1:
                    break
                buffer.append(byte)
                if byte == ord('>'):
                    break

            res_str = buffer.decode('utf-8', errors='ignore')
            return res_str.replace('>', '').strip()
        except Exception as e:
            print(f"[Android BT Error] Помилка передачі: {e}")
            return ""

    def disconnect(self):
        try:
            if self.input_stream: self.input_stream.close()
            if self.output_stream: self.output_stream.close()
            if self.socket: self.socket.close()
        except Exception:
            pass
        finally:
            self.socket = None
            self.input_stream = None
            self.output_stream = None