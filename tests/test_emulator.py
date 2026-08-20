import socket
import threading
import time
import unittest

import config
from emulator.server import start_emulator_server


class TestEmulatorServer(unittest.TestCase):
    def test_server_accepts_elm327_command(self):
        host = config.EMULATOR_HOST
        port = config.EMULATOR_PORT + 1

        thread = threading.Thread(
            target=start_emulator_server,
            args=(host, port),
            daemon=True,
        )
        thread.start()

        deadline = time.time() + 3
        while time.time() < deadline:
            try:
                with socket.create_connection((host, port), timeout=0.5) as conn:
                    conn.sendall(b"010C\r")
                    data = conn.recv(1024).decode("utf-8", errors="ignore")
                    self.assertIn("41 0C", data)
                    return
            except OSError:
                time.sleep(0.05)

        self.fail("Emulator server did not respond in time")


if __name__ == "__main__":
    unittest.main()
