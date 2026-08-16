import sys
import types
import unittest
from unittest.mock import patch

from switcher.devices import Device, list_monitors, validate_selection


class DeviceTests(unittest.TestCase):
    def test_selection_requires_known_non_empty_device_ids(self) -> None:
        devices = [Device("one", "One"), Device("two", "Two")]

        self.assertTrue(validate_selection(["one", "two"], devices))
        self.assertFalse(validate_selection(["one", ""], devices))
        self.assertFalse(validate_selection(["missing"], devices))

    def test_nvidia_surround_layout_is_identified(self) -> None:
        display = types.SimpleNamespace(
            StateFlags=1, DeviceName=r"\\.\DISPLAY1", DeviceString="NVIDIA display"
        )
        mode = types.SimpleNamespace(PelsWidth=7680, PelsHeight=1440, DisplayFrequency=120)
        win32api = types.SimpleNamespace(
            EnumDisplayDevices=lambda parent, index: display
            if index == 0 and parent is None
            else (_ for _ in ()).throw(RuntimeError()),
            EnumDisplaySettings=lambda *_: mode,
        )
        win32con = types.SimpleNamespace(
            DISPLAY_DEVICE_ATTACHED_TO_DESKTOP=1, ENUM_CURRENT_SETTINGS=-1
        )

        with patch.dict(sys.modules, {"win32api": win32api, "win32con": win32con}):
            monitors = list_monitors()

        self.assertEqual(len(monitors), 1)
        self.assertIn("NVIDIA Surround", monitors[0].name)
        self.assertIn("7680 × 1440 @ 120 Hz", monitors[0].name)


if __name__ == "__main__":
    unittest.main()
