from __future__ import annotations

import os
import sys
from pathlib import Path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Switcher"


def launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    launcher = Path(__file__).resolve().parent.parent / "run_switcher.py"
    project_pythonw = launcher.parent / ".venv" / "Scripts" / "pythonw.exe"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if project_pythonw.exists():
        executable = project_pythonw
    else:
        executable = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{executable}" "{launcher}"'


def set_autostart(enabled: bool) -> None:
    if os.name != "nt":
        return
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
