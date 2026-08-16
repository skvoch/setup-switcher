import unittest
from unittest.mock import Mock, call, patch

from switcher import app as app_module
from switcher.config import Config, Profile


class SwitchingTests(unittest.TestCase):
    def test_apply_profile_switches_every_device_and_saves_state(self) -> None:
        controller = object.__new__(app_module.SwitcherApp)
        controller.config = Config(
            game=Profile("DISPLAY1", "speakers", "microphone"),
            last_profile="racing",
        )
        controller.flyout = Mock()

        with (
            patch.object(app_module, "set_primary_monitor") as set_monitor,
            patch.object(app_module, "set_default_audio") as set_audio,
            patch.object(app_module.QApplication, "processEvents"),
            patch.object(Config, "save") as save,
        ):
            controller.apply_profile("game")

        set_monitor.assert_called_once_with("DISPLAY1")
        self.assertEqual(set_audio.call_args_list, [call("speakers"), call("microphone")])
        self.assertEqual(controller.config.last_profile, "game")
        save.assert_called_once_with()
        controller.flyout.switcher.set_active.assert_called_once_with("game")
        controller.flyout.animate_close.assert_called_once_with()

    def test_incomplete_profile_opens_settings_without_switching_devices(self) -> None:
        controller = object.__new__(app_module.SwitcherApp)
        controller.config = Config(game=Profile(), last_profile="racing")
        controller.flyout = Mock()
        controller.show_settings = Mock()

        with (
            patch.object(app_module, "set_primary_monitor") as set_monitor,
            patch.object(app_module, "set_default_audio") as set_audio,
        ):
            controller.apply_profile("game")

        set_monitor.assert_not_called()
        set_audio.assert_not_called()
        controller.flyout.switcher.set_active.assert_called_once_with("racing")
        controller.show_settings.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
