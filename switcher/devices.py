from __future__ import annotations

import ctypes
import winreg
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Device:
    id: str
    name: str


def _require_windows() -> None:
    import sys

    if sys.platform != "win32":
        raise RuntimeError("Switcher only works on Windows")


def list_monitors() -> list[Device]:
    _require_windows()
    import win32api
    import win32con

    result: list[Device] = []
    index = 0
    while True:
        try:
            display = win32api.EnumDisplayDevices(None, index)
        except Exception:
            break
        index += 1
        if not display.StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            continue
        mode = win32api.EnumDisplaySettings(
            display.DeviceName, win32con.ENUM_CURRENT_SETTINGS
        )
        model = ""
        try:
            monitor = win32api.EnumDisplayDevices(display.DeviceName, 0)
            hardware_id = monitor.DeviceID.split("\\")[1]
            model = _monitor_name_from_edid(hardware_id)
        except (Exception, IndexError):
            pass
        if mode.PelsWidth >= mode.PelsHeight * 3:
            model = "NVIDIA Surround"
        elif not model or model.lower() == "generic pnp monitor":
            model = display.DeviceString or "Display"
        label = f"{model} — {mode.PelsWidth} × {mode.PelsHeight} @ {mode.DisplayFrequency} Hz"
        result.append(Device(display.DeviceName, label))
    return result


def _monitor_name_from_edid(hardware_id: str) -> str:
    """Read the human-friendly model stored in the monitor's EDID."""
    path = rf"SYSTEM\CurrentControlSet\Enum\DISPLAY\{hardware_id}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as root:
            instance_count = winreg.QueryInfoKey(root)[0]
            for index in range(instance_count):
                instance = winreg.EnumKey(root, index)
                try:
                    with winreg.OpenKey(root, instance + r"\Device Parameters") as params:
                        edid, _ = winreg.QueryValueEx(params, "EDID")
                except OSError:
                    continue
                for offset in (54, 72, 90, 108):
                    block = edid[offset : offset + 18]
                    if len(block) == 18 and block[:5] == b"\x00\x00\x00\xfc\x00":
                        name = block[5:18].decode("ascii", errors="ignore").strip(" \x00\n\r")
                        if name:
                            return name
    except OSError:
        pass
    return ""


def set_primary_monitor(device_name: str) -> None:
    _require_windows()
    from .display_config import set_primary_display

    set_primary_display(device_name)


def _audio_devices(flow: int) -> list[Device]:
    _require_windows()
    from pycaw.pycaw import AudioUtilities

    # Ask Windows only for active endpoints of the requested data flow.
    result: list[Device] = []
    for endpoint in AudioUtilities.GetAllDevices(data_flow=flow, device_state=1):
        try:
            result.append(Device(endpoint.id, endpoint.FriendlyName or endpoint.id))
        except (AttributeError, OSError):
            continue
    return sorted(result, key=lambda item: item.name.casefold())


def list_outputs() -> list[Device]:
    return _audio_devices(0)


def list_inputs() -> list[Device]:
    return _audio_devices(1)


def set_default_audio(device_id: str) -> None:
    """Set one endpoint for Console, Multimedia and Communications roles."""
    _require_windows()
    from comtypes import CLSCTX_ALL, COMMETHOD, GUID, HRESULT, IUnknown
    from comtypes.client import CreateObject
    from ctypes import POINTER, c_int
    from ctypes.wintypes import LPCWSTR

    class IPolicyConfig(IUnknown):
        _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
        _methods_ = [
            COMMETHOD([], HRESULT, "GetMixFormat"),
            COMMETHOD([], HRESULT, "GetDeviceFormat"),
            COMMETHOD([], HRESULT, "ResetDeviceFormat"),
            COMMETHOD([], HRESULT, "SetDeviceFormat"),
            COMMETHOD([], HRESULT, "GetProcessingPeriod"),
            COMMETHOD([], HRESULT, "SetProcessingPeriod"),
            COMMETHOD([], HRESULT, "GetShareMode"),
            COMMETHOD([], HRESULT, "SetShareMode"),
            COMMETHOD([], HRESULT, "GetPropertyValue"),
            COMMETHOD([], HRESULT, "SetPropertyValue"),
            COMMETHOD([], HRESULT, "SetDefaultEndpoint", (['in'], LPCWSTR, 'device_id'), (['in'], c_int, 'role')),
            COMMETHOD([], HRESULT, "SetEndpointVisibility"),
        ]

    policy = CreateObject(
        GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}"),
        interface=IPolicyConfig,
        clsctx=CLSCTX_ALL,
    )
    for role in (0, 1, 2):
        policy.SetDefaultEndpoint(device_id, role)


def validate_selection(selected: Iterable[str], available: Iterable[Device]) -> bool:
    ids = {item.id for item in available}
    return all(bool(value) and value in ids for value in selected)
