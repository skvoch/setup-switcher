import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from switcher import config as config_module
from switcher.config import Config, Profile


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app_dir = Path(self.temp_dir.name) / "Switcher"
        self.config_path = self.app_dir / "config.json"
        self.patches = (
            patch.object(config_module, "APP_DIR", self.app_dir),
            patch.object(config_module, "CONFIG_PATH", self.config_path),
        )
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_first_launch_uses_safe_defaults_without_creating_a_file(self) -> None:
        config = Config.load()

        self.assertEqual(config.game, Profile())
        self.assertEqual(config.racing, Profile())
        self.assertEqual(config.hotkeys.panel, "Ctrl+Alt+S")
        self.assertEqual(config.colors.game, "#1677D2")
        self.assertEqual(config.colors.racing, "#E58A3A")
        self.assertTrue(config.autostart)
        self.assertFalse(self.config_path.exists())

    def test_invalid_config_falls_back_to_defaults(self) -> None:
        self.app_dir.mkdir(parents=True)
        self.config_path.write_text("not json", encoding="utf-8")

        self.assertEqual(Config.load(), Config())

    def test_config_round_trip(self) -> None:
        expected = Config(
            game=Profile("DISPLAY1", "speakers", "desk-mic"),
            racing=Profile("DISPLAY2", "headset", "headset-mic"),
            autostart=False,
            last_profile="racing",
        )

        expected.save()

        self.assertEqual(Config.load(), expected)
        self.assertEqual(json.loads(self.config_path.read_text(encoding="utf-8"))["last_profile"], "racing")

    def test_legacy_hotkey_is_migrated(self) -> None:
        self.app_dir.mkdir(parents=True)
        self.config_path.write_text(
            json.dumps({"hotkeys": {"panel": "Ctrl+Alt+F11"}}), encoding="utf-8"
        )

        self.assertEqual(Config.load().hotkeys.panel, "Ctrl+Alt+S")


if __name__ == "__main__":
    unittest.main()
