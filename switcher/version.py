from pathlib import Path
import re


VERSION_FILE = Path(__file__).resolve().parent / "VERSION"


def current_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        return "dev"


def _version_key(version: str) -> tuple[tuple[int, ...], tuple[tuple[int, object], ...]]:
    value = version.strip().removeprefix("v")
    core, separator, prerelease = value.partition("-")
    numbers = tuple(int(part) for part in core.split(".") if part.isdigit())
    if not numbers:
        return ((), ((0, "dev"),))
    # A stable version sorts after every prerelease with the same core.
    if not separator:
        return (numbers, ((2, ""),))
    parts: list[tuple[int, object]] = []
    for part in re.split(r"[.-]", prerelease.casefold()):
        parts.append((1, int(part)) if part.isdigit() else (0, part))
    return (numbers, tuple(parts))


def is_newer_version(candidate: str, installed: str) -> bool:
    return _version_key(candidate) > _version_key(installed)
