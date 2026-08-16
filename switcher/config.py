from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


APP_DIR = Path.home() / "AppData" / "Local" / "Switcher"
CONFIG_PATH = APP_DIR / "config.json"


@dataclass
class Profile:
    monitor: str = ""
    output: str = ""
    input: str = ""


@dataclass
class Hotkeys:
    panel: str = "Ctrl+Alt+S"


@dataclass
class ModeColors:
    game: str = "#1677D2"
    racing: str = "#E58A3A"


@dataclass
class Config:
    game: Profile = field(default_factory=Profile)
    racing: Profile = field(default_factory=Profile)
    hotkeys: Hotkeys = field(default_factory=Hotkeys)
    colors: ModeColors = field(default_factory=ModeColors)
    autostart: bool = True
    last_profile: str = ""

    @classmethod
    def load(cls) -> "Config":
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            raw_hotkeys = raw.get("hotkeys", {})
            panel_hotkey = raw_hotkeys.get("panel", "Ctrl+Alt+S")
            if panel_hotkey == "Ctrl+Alt+F11":
                panel_hotkey = "Ctrl+Alt+S"
            hotkeys = Hotkeys(panel=panel_hotkey)
            return cls(
                game=Profile(**raw.get("game", {})),
                racing=Profile(**raw.get("racing", {})),
                hotkeys=hotkeys,
                colors=ModeColors(**raw.get("colors", {})),
                autostart=bool(raw.get("autostart", True)),
                last_profile=raw.get("last_profile", ""),
            )
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
        )
