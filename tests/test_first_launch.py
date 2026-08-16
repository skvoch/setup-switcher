import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from switcher import app as app_module
from switcher.config import Config
from switcher.hotkeys import HotkeyManager


@unittest.skipUnless(sys.platform == "win32", "Switcher supports Windows only")
class FirstLaunchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])
        cls.qt_app.setStyleSheet(app_module.STYLE)

    def test_missing_profiles_open_settings_on_first_launch(self) -> None:
        first_run_config = Config()
        with (
            patch.object(app_module.Config, "load", return_value=first_run_config),
            patch.object(app_module, "set_autostart"),
            patch.object(HotkeyManager, "configure", return_value=[]),
            patch.object(QSystemTrayIcon, "show"),
            patch.object(app_module.SwitcherApp, "show_settings") as show_settings,
        ):
            controller = app_module.SwitcherApp(self.qt_app)

        show_settings.assert_called_once_with()
        controller.flyout.close()
        controller.tray.hide()

    def test_complete_profiles_do_not_open_settings(self) -> None:
        configured = Config()
        configured.game.monitor = configured.game.output = configured.game.input = "game"
        configured.racing.monitor = configured.racing.output = configured.racing.input = "racing"
        with (
            patch.object(app_module.Config, "load", return_value=configured),
            patch.object(app_module, "set_autostart"),
            patch.object(HotkeyManager, "configure", return_value=[]),
            patch.object(QSystemTrayIcon, "show"),
            patch.object(app_module.SwitcherApp, "show_settings") as show_settings,
        ):
            controller = app_module.SwitcherApp(self.qt_app)

        show_settings.assert_not_called()
        controller.flyout.close()
        controller.tray.hide()


if __name__ == "__main__":
    unittest.main()
