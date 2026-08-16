from __future__ import annotations

import ctypes
from ctypes import wintypes


QDC_ONLY_ACTIVE = 0x00000002
SDC_USE_SUPPLIED_DISPLAY_CONFIG = 0x00000020
SDC_VALIDATE = 0x00000040
SDC_APPLY = 0x00000080
SDC_SAVE_TO_DATABASE = 0x00000200
DISPLAYCONFIG_MODE_INFO_TYPE_SOURCE = 1
DISPLAYCONFIG_DEVICE_INFO_GET_SOURCE_NAME = 1
DISPLAYCONFIG_PATH_MODE_IDX_INVALID = 0xFFFFFFFF


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class POINTL(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class DISPLAYCONFIG_RATIONAL(ctypes.Structure):
    _fields_ = [("Numerator", wintypes.UINT), ("Denominator", wintypes.UINT)]


class DISPLAYCONFIG_2DREGION(ctypes.Structure):
    _fields_ = [("cx", wintypes.UINT), ("cy", wintypes.UINT)]


class DISPLAYCONFIG_VIDEO_SIGNAL_INFO(ctypes.Structure):
    _fields_ = [
        ("pixelRate", ctypes.c_uint64),
        ("hSyncFreq", DISPLAYCONFIG_RATIONAL),
        ("vSyncFreq", DISPLAYCONFIG_RATIONAL),
        ("activeSize", DISPLAYCONFIG_2DREGION),
        ("totalSize", DISPLAYCONFIG_2DREGION),
        ("videoStandard", wintypes.UINT),
        ("scanLineOrdering", wintypes.UINT),
    ]


class DISPLAYCONFIG_TARGET_MODE(ctypes.Structure):
    _fields_ = [("targetVideoSignalInfo", DISPLAYCONFIG_VIDEO_SIGNAL_INFO)]


class DISPLAYCONFIG_SOURCE_MODE(ctypes.Structure):
    _fields_ = [
        ("width", wintypes.UINT),
        ("height", wintypes.UINT),
        ("pixelFormat", wintypes.UINT),
        ("position", POINTL),
    ]


class RECTL(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class DISPLAYCONFIG_DESKTOP_IMAGE_INFO(ctypes.Structure):
    _fields_ = [
        ("PathSourceSize", POINTL),
        ("DesktopImageRegion", RECTL),
        ("DesktopImageClip", RECTL),
    ]


class MODE_UNION(ctypes.Union):
    _fields_ = [
        ("targetMode", DISPLAYCONFIG_TARGET_MODE),
        ("sourceMode", DISPLAYCONFIG_SOURCE_MODE),
        ("desktopImageInfo", DISPLAYCONFIG_DESKTOP_IMAGE_INFO),
    ]


class DISPLAYCONFIG_MODE_INFO(ctypes.Structure):
    _anonymous_ = ("mode",)
    _fields_ = [
        ("infoType", wintypes.UINT),
        ("id", wintypes.UINT),
        ("adapterId", LUID),
        ("mode", MODE_UNION),
    ]


class DISPLAYCONFIG_PATH_SOURCE_INFO(ctypes.Structure):
    _fields_ = [
        ("adapterId", LUID),
        ("id", wintypes.UINT),
        ("modeInfoIdx", wintypes.UINT),
        ("statusFlags", wintypes.UINT),
    ]


class DISPLAYCONFIG_PATH_TARGET_INFO(ctypes.Structure):
    _fields_ = [
        ("adapterId", LUID),
        ("id", wintypes.UINT),
        ("modeInfoIdx", wintypes.UINT),
        ("outputTechnology", wintypes.UINT),
        ("rotation", wintypes.UINT),
        ("scaling", wintypes.UINT),
        ("refreshRate", DISPLAYCONFIG_RATIONAL),
        ("scanLineOrdering", wintypes.UINT),
        ("targetAvailable", wintypes.BOOL),
        ("statusFlags", wintypes.UINT),
    ]


class DISPLAYCONFIG_PATH_INFO(ctypes.Structure):
    _fields_ = [
        ("sourceInfo", DISPLAYCONFIG_PATH_SOURCE_INFO),
        ("targetInfo", DISPLAYCONFIG_PATH_TARGET_INFO),
        ("flags", wintypes.UINT),
    ]


class DISPLAYCONFIG_DEVICE_INFO_HEADER(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.UINT),
        ("size", wintypes.UINT),
        ("adapterId", LUID),
        ("id", wintypes.UINT),
    ]


class DISPLAYCONFIG_SOURCE_DEVICE_NAME(ctypes.Structure):
    _fields_ = [
        ("header", DISPLAYCONFIG_DEVICE_INFO_HEADER),
        ("viewGdiDeviceName", wintypes.WCHAR * 32),
    ]


user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.GetDisplayConfigBufferSizes.argtypes = [
    wintypes.UINT,
    ctypes.POINTER(wintypes.UINT),
    ctypes.POINTER(wintypes.UINT),
]
user32.QueryDisplayConfig.argtypes = [
    wintypes.UINT,
    ctypes.POINTER(wintypes.UINT),
    ctypes.POINTER(DISPLAYCONFIG_PATH_INFO),
    ctypes.POINTER(wintypes.UINT),
    ctypes.POINTER(DISPLAYCONFIG_MODE_INFO),
    ctypes.c_void_p,
]
user32.SetDisplayConfig.argtypes = [
    wintypes.UINT,
    ctypes.POINTER(DISPLAYCONFIG_PATH_INFO),
    wintypes.UINT,
    ctypes.POINTER(DISPLAYCONFIG_MODE_INFO),
    wintypes.UINT,
]
user32.DisplayConfigGetDeviceInfo.argtypes = [ctypes.POINTER(DISPLAYCONFIG_DEVICE_INFO_HEADER)]


def _check(result: int, operation: str) -> None:
    if result:
        raise OSError(result, f"{operation}: {ctypes.FormatError(result)}")


def _query_active():
    path_count = wintypes.UINT()
    mode_count = wintypes.UINT()
    _check(
        user32.GetDisplayConfigBufferSizes(
            QDC_ONLY_ACTIVE, ctypes.byref(path_count), ctypes.byref(mode_count)
        ),
        "GetDisplayConfigBufferSizes",
    )
    paths = (DISPLAYCONFIG_PATH_INFO * path_count.value)()
    modes = (DISPLAYCONFIG_MODE_INFO * mode_count.value)()
    _check(
        user32.QueryDisplayConfig(
            QDC_ONLY_ACTIVE,
            ctypes.byref(path_count),
            paths,
            ctypes.byref(mode_count),
            modes,
            None,
        ),
        "QueryDisplayConfig",
    )
    return path_count.value, paths, mode_count.value, modes


def _source_name(source: DISPLAYCONFIG_PATH_SOURCE_INFO) -> str:
    name = DISPLAYCONFIG_SOURCE_DEVICE_NAME()
    name.header.type = DISPLAYCONFIG_DEVICE_INFO_GET_SOURCE_NAME
    name.header.size = ctypes.sizeof(name)
    name.header.adapterId = source.adapterId
    name.header.id = source.id
    _check(user32.DisplayConfigGetDeviceInfo(ctypes.byref(name.header)), "DisplayConfigGetDeviceInfo")
    return name.viewGdiDeviceName


def _wide_sources(paths, path_count: int, modes, mode_count: int) -> set[tuple[str, int, int]]:
    result: set[tuple[str, int, int]] = set()
    for index in range(path_count):
        source = paths[index].sourceInfo
        mode_index = source.modeInfoIdx
        if mode_index == DISPLAYCONFIG_PATH_MODE_IDX_INVALID or mode_index >= mode_count:
            continue
        mode = modes[mode_index]
        if mode.infoType != DISPLAYCONFIG_MODE_INFO_TYPE_SOURCE:
            continue
        if mode.sourceMode.width >= mode.sourceMode.height * 3:
            result.add((_source_name(source), mode.sourceMode.width, mode.sourceMode.height))
    return result


def set_primary_display(device_name: str) -> None:
    """Move the current CCD source to (0,0) without rebuilding display paths."""
    path_count, paths, mode_count, modes = _query_active()
    original_paths = (DISPLAYCONFIG_PATH_INFO * path_count)()
    original_modes = (DISPLAYCONFIG_MODE_INFO * mode_count)()
    ctypes.memmove(original_paths, paths, ctypes.sizeof(paths))
    ctypes.memmove(original_modes, modes, ctypes.sizeof(modes))
    original_wide = _wide_sources(paths, path_count, modes, mode_count)

    target_position: tuple[int, int] | None = None
    source_mode_indices: set[int] = set()
    for index in range(path_count):
        source = paths[index].sourceInfo
        mode_index = source.modeInfoIdx
        if mode_index == DISPLAYCONFIG_PATH_MODE_IDX_INVALID or mode_index >= mode_count:
            continue
        source_mode_indices.add(mode_index)
        if _source_name(source).casefold() == device_name.casefold():
            mode = modes[mode_index].sourceMode
            target_position = (mode.position.x, mode.position.y)

    if target_position is None:
        raise RuntimeError(f"Display is not active in Windows CCD: {device_name}")
    if target_position == (0, 0):
        return

    for mode_index in source_mode_indices:
        mode = modes[mode_index]
        if mode.infoType == DISPLAYCONFIG_MODE_INFO_TYPE_SOURCE:
            mode.sourceMode.position.x -= target_position[0]
            mode.sourceMode.position.y -= target_position[1]

    supplied = SDC_USE_SUPPLIED_DISPLAY_CONFIG
    _check(
        user32.SetDisplayConfig(path_count, paths, mode_count, modes, supplied | SDC_VALIDATE),
        "SetDisplayConfig validation",
    )
    _check(
        user32.SetDisplayConfig(
            path_count,
            paths,
            mode_count,
            modes,
            supplied | SDC_APPLY | SDC_SAVE_TO_DATABASE,
        ),
        "SetDisplayConfig apply",
    )

    new_path_count, new_paths, new_mode_count, new_modes = _query_active()
    if original_wide and not original_wide.issubset(
        _wide_sources(new_paths, new_path_count, new_modes, new_mode_count)
    ):
        user32.SetDisplayConfig(
            path_count,
            original_paths,
            mode_count,
            original_modes,
            supplied | SDC_APPLY | SDC_SAVE_TO_DATABASE,
        )
        raise RuntimeError("NVIDIA Surround changed unexpectedly; the original CCD layout was restored")
