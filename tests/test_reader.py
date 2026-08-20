import math
import time
import unittest

import config
from app.reader import TelemetryReader
from emulator.mock_data import OBDMockEngine


class TestTelemetryReader(unittest.TestCase):
    def setUp(self):
        self._orig_emulator = config.IS_EMULATOR
        self._orig_tcp = config.USE_TCP_EMULATOR
        config.IS_EMULATOR = True
        config.USE_TCP_EMULATOR = False

    def tearDown(self):
        config.IS_EMULATOR = self._orig_emulator
        config.USE_TCP_EMULATOR = self._orig_tcp

    def test_mock_metrics_returns_expected_keys(self):
        reader = TelemetryReader(None)
        metrics = reader.read_metrics()
        self.assertEqual(set(metrics.keys()), set(config.METRICS_INFO.keys()))

    def test_mock_metrics_values_are_numeric(self):
        reader = TelemetryReader(None)
        metrics = reader.read_metrics()
        for key, value in metrics.items():
            self.assertIsInstance(value, (int, float), msg=key)

    def test_mock_dtc_returns_sample_code(self):
        reader = TelemetryReader(None)
        dtcs = reader.read_dtc()
        self.assertEqual(len(dtcs), 1)
        self.assertEqual(dtcs[0][0], "P0300")

    def test_clear_dtc_in_emulator_mode(self):
        reader = TelemetryReader(None)
        self.assertTrue(reader.clear_dtc())


class TestOBDMockEngine(unittest.TestCase):
    def test_at_commands(self):
        engine = OBDMockEngine()
        self.assertIn("ELM327", engine.process_command("ATZ"))
        self.assertIn("OK", engine.process_command("ATE0"))

    def test_rpm_pid(self):
        engine = OBDMockEngine()
        response = engine.process_command("010C")
        self.assertIn("41 0C", response)

    def test_dtc_mode(self):
        engine = OBDMockEngine()
        response = engine.process_command("03")
        self.assertIn("43", response)


if __name__ == "__main__":
    unittest.main()
