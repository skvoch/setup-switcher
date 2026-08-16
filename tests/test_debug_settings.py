import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from switcher import app as app_module
from switcher.config import Config


class DebugSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])
        cls.qt_app.setStyleSheet(app_module.STYLE)

    def create_dialog(self, *, frozen: bool):
        with (
            patch.object(app_module.sys, "frozen", frozen, create=True),
            patch.object(app_module, "list_monitors", return_value=[]),
            patch.object(app_module, "list_outputs", return_value=[]),
            patch.object(app_module, "list_inputs", return_value=[]),
        ):
            return app_module.SettingsDialog(Config(), check_updates=False)

    def test_screenshot_mode_can_explicitly_hide_debug_tab(self) -> None:
        dialog = app_module.SettingsDialog(
            Config(), check_updates=False, show_debug=False
        )

        tabs = [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())]
        self.assertNotIn("Debug", tabs)
        dialog.close()

    def test_source_run_has_debug_tab_and_can_simulate_update(self) -> None:
        dialog = self.create_dialog(frozen=False)

        self.assertEqual(dialog.tabs.tabText(dialog.tabs.count() - 1), "Debug")
        self.assertTrue(dialog.release_banner.isHidden())
        dialog.debug_update_available.setChecked(True)
        self.assertFalse(dialog.release_banner.isHidden())
        self.assertIn("99.0.0-debug is available", dialog.release_banner.text())
        self.assertIn("Download the update from GitHub", dialog.release_banner.text())
        dialog.debug_update_available.setChecked(False)
        self.assertTrue(dialog.release_banner.isHidden())
        dialog.close()

    def test_packaged_run_has_no_debug_tab(self) -> None:
        dialog = self.create_dialog(frozen=True)

        tabs = [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())]
        self.assertNotIn("Debug", tabs)
        self.assertFalse(hasattr(dialog, "debug_update_available"))
        dialog.close()


if __name__ == "__main__":
    unittest.main()
