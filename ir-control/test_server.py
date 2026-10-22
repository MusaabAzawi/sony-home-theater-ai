"""
Test suite for Sony Home Theater IR Control Server.

Validates all REST endpoints against the Mock backend, testing:
- Health check
- Status reporting
- Volume up / down / set
- Mute toggle
- Power toggle
- Source switching
- Preset selection
- Raw IR sending
- Error validation
"""

import os
import unittest
from fastapi.testclient import TestClient

# Force Mock backend for automated testing
os.environ["IR_BACKEND"] = "mock"

from ir_server import app, receiver_state


class TestIRServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        # Reset baseline receiver state
        receiver_state["volume"] = 25
        receiver_state["muted"] = False
        receiver_state["power"] = True
        receiver_state["source"] = "hdmi1"

    def test_health_check(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_ir_status(self):
        resp = self.client.get("/ir/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["device"], "mock")
        self.assertTrue(data["connected"])
        self.assertEqual(data["estimated_volume"], 25)

    def test_volume_up(self):
        resp = self.client.post("/ir/volume/up")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["action"], "volume_up")
        self.assertEqual(data["estimated_volume"], 26)

    def test_volume_down(self):
        resp = self.client.post("/ir/volume/down")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["action"], "volume_down")
        self.assertEqual(data["estimated_volume"], 24)

    def test_volume_set(self):
        # Set volume from 25 to 28 (3 pulses)
        resp = self.client.post("/ir/volume/set", json={"level": 28})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["target_level"], 28)
        self.assertEqual(data["pulses_sent"], 3)
        self.assertEqual(data["estimated_volume"], 28)

        # Set volume downwards from 28 to 22 (6 pulses)
        resp = self.client.post("/ir/volume/set", json={"level": 22})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["pulses_sent"], 6)
        self.assertEqual(data["estimated_volume"], 22)

    def test_volume_bounds_validation(self):
        # Out of bounds (>100 or <0)
        resp = self.client.post("/ir/volume/set", json={"level": 150})
        self.assertEqual(resp.status_code, 422)

        resp = self.client.post("/ir/volume/set", json={"level": -5})
        self.assertEqual(resp.status_code, 422)

    def test_toggle_mute(self):
        resp = self.client.post("/ir/mute")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["action"], "mute")
        self.assertTrue(data["is_muted"])

        # Toggle again
        resp2 = self.client.post("/ir/mute")
        self.assertFalse(resp2.json()["is_muted"])

    def test_toggle_power(self):
        resp = self.client.post("/ir/power")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["action"], "power")
        self.assertFalse(data["power_state"])

    def test_switch_source(self):
        sources = ["hdmi1", "hdmi2", "bluetooth", "optical"]
        for s in sources:
            resp = self.client.post("/ir/source", json={"source": s})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["action"], "source")
            self.assertEqual(data["source"], s)

        # Invalid source
        resp_invalid = self.client.post("/ir/source", json={"source": "aux99"})
        self.assertEqual(resp_invalid.status_code, 422)

    def test_select_preset(self):
        presets = ["movie", "music", "gaming", "sports"]
        for p in presets:
            resp = self.client.post("/ir/preset", json={"preset": p})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["action"], "preset")
            self.assertEqual(data["preset"], p)

        # Invalid preset
        resp_invalid = self.client.post("/ir/preset", json={"preset": "jazz"})
        self.assertEqual(resp_invalid.status_code, 422)

    def test_send_raw(self):
        raw_code = "JgBGAAABK5YTERQRFBEUERQRFBEUERQRFBEAABFFERQRFBEUERQRFBEAABFFERQRFBEUERQRFBEAABFAAAAAAAAAAAAAAAAAA=="
        resp = self.client.post("/ir/send", json={"code": raw_code})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["action"], "raw_send")


if __name__ == "__main__":
    unittest.main()
