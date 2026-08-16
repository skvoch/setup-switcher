import unittest

from switcher.hotkeys import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    MOD_SHIFT,
    MOD_WIN,
    parse_hotkey,
)


class HotkeyTests(unittest.TestCase):
    def test_parses_letter_with_modifiers(self) -> None:
        modifiers, key = parse_hotkey("Ctrl+Alt+S")

        self.assertEqual(modifiers, MOD_NOREPEAT | MOD_CONTROL | MOD_ALT)
        self.assertEqual(key, ord("S"))

    def test_parses_function_key_and_all_modifiers(self) -> None:
        modifiers, key = parse_hotkey("Ctrl+Alt+Shift+Win+F24")

        self.assertEqual(
            modifiers, MOD_NOREPEAT | MOD_CONTROL | MOD_ALT | MOD_SHIFT | MOD_WIN
        )
        self.assertEqual(key, 0x87)

    def test_rejects_invalid_sequences(self) -> None:
        for sequence in ("", "Ctrl+Space", "Option+S", "Ctrl+F25"):
            with self.subTest(sequence=sequence), self.assertRaises(ValueError):
                parse_hotkey(sequence)


if __name__ == "__main__":
    unittest.main()
