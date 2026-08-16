from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Callable

from PySide6.QtCore import QAbstractNativeEventFilter


WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


def parse_hotkey(sequence: str) -> tuple[int, int]:
    parts = [part.strip() for part in sequence.split("+") if part.strip()]
    if not parts:
        raise ValueError("Hotkey is empty")
    modifiers = MOD_NOREPEAT
    modifier_names = {
        "CTRL": MOD_CONTROL,
        "CONTROL": MOD_CONTROL,
        "ALT": MOD_ALT,
        "SHIFT": MOD_SHIFT,
        "WIN": MOD_WIN,
        "META": MOD_WIN,
    }
    for part in parts[:-1]:
        try:
            modifiers |= modifier_names[part.upper()]
        except KeyError as error:
            raise ValueError(f"Unsupported modifier: {part}") from error

    key = parts[-1].upper()
    if len(key) == 1 and (key.isalpha() or key.isdigit()):
        virtual_key = ord(key)
    elif key.startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        virtual_key = 0x70 + int(key[1:]) - 1
    else:
        raise ValueError("Use A-Z, 0-9 or F1-F24 as the hotkey key")
    return modifiers, virtual_key


class HotkeyManager(QAbstractNativeEventFilter):
    def __init__(self, callbacks: dict[str, Callable[[], None]]) -> None:
        super().__init__()
        self.callbacks = callbacks
        self.registered: dict[int, str] = {}

    def configure(self, sequences: dict[str, str]) -> list[str]:
        self.unregister_all()
        failures: list[str] = []
        user32 = ctypes.windll.user32
        for hotkey_id, (name, sequence) in enumerate(sequences.items(), start=1):
            try:
                modifiers, virtual_key = parse_hotkey(sequence)
            except ValueError as error:
                failures.append(f"{sequence}: {error}")
                continue
            if not user32.RegisterHotKey(None, hotkey_id, modifiers, virtual_key):
                failures.append(f"{sequence} is already in use")
                continue
            self.registered[hotkey_id] = name
        return failures

    def unregister_all(self) -> None:
        if hasattr(ctypes, "windll"):
            for hotkey_id in tuple(self.registered):
                ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)
        self.registered.clear()

    def nativeEventFilter(self, event_type, message):
        try:
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam in self.registered:
                callback = self.callbacks.get(self.registered[msg.wParam])
                if callback:
                    callback()
                return True, 0
        except (TypeError, ValueError):
            pass
        return False, 0
