"""Per-app volume control through Windows audio sessions (pycaw/comtypes).

Sessions are collected from every active output device rather than just the default one, so apps that
play through another device (Discord set to a headset, a game still using the device that was the
default when it started, virtual devices such as NVIDIA Broadcast, ...) are still found.
"""
import threading

import comtypes
import psutil
from pycaw.constants import DEVICE_STATE, AudioSessionState, EDataFlow
from pycaw.pycaw import AudioUtilities, IAudioSessionControl2, IAudioSessionManager2, ISimpleAudioVolume

import winapi
from config import FOCUSED

STEPS = 20  # volume moves in 5% steps
SHELL = 'explorer.exe'

_thread_state = threading.local()
_level_before_mute = {}  # app -> volume it had when muted, so unmuting can restore it


def _sessions():
    """(pid, ISimpleAudioVolume, is_active) for every app audio session on every active output device."""
    if not getattr(_thread_state, 'com_ready', False):
        comtypes.CoInitialize()
        _thread_state.com_ready = True
    found = []
    devices = AudioUtilities.GetDeviceEnumerator().EnumAudioEndpoints(EDataFlow.eRender.value,
                                                                       DEVICE_STATE.ACTIVE.value)
    for device_index in range(devices.GetCount()):
        try:
            manager = devices.Item(device_index).Activate(IAudioSessionManager2._iid_, comtypes.CLSCTX_ALL, None)
            sessions = manager.QueryInterface(IAudioSessionManager2).GetSessionEnumerator()
            count = sessions.GetCount()
        except comtypes.COMError:
            continue  # device went away while enumerating
        for session_index in range(count):
            try:
                control = sessions.GetSession(session_index).QueryInterface(IAudioSessionControl2)
                pid, state = control.GetProcessId(), control.GetState()
                if pid and state != AudioSessionState.Expired:  # pid 0 is "System Sounds"
                    found.append((pid, control.QueryInterface(ISimpleAudioVolume), state == AudioSessionState.Active))
            except comtypes.COMError:
                continue  # session closed while enumerating
    return found


def _process_name(pid, cache):
    if pid not in cache:
        try:
            cache[pid] = psutil.Process(pid).name().lower()
        except psutil.Error:
            cache[pid] = ''
    return cache[pid]


def _exe(pid):
    try:
        return psutil.Process(pid).exe()
    except psutil.Error:
        return None


def _find(target):
    """Return (display name, exe for the overlay icon, matching sessions), or None if nothing is focused."""
    sessions = _sessions()
    names = {}
    if target != FOCUSED:
        matches = [session for session in sessions if _process_name(session[0], names) == target.lower()]
        return target, _exe(matches[0][0]) if matches else None, matches

    pid = winapi.foreground_pid()
    try:
        process = psutil.Process(pid) if pid else None
        name = process.name() if process else None
    except psutil.Error:
        name = None
    if not name:
        return None
    # Apps often play audio from a different process with the same exe name (browsers, Discord, ...).
    matches = [session for session in sessions if session[0] == pid or _process_name(session[0], names) == name.lower()]
    if not matches and name.lower() != SHELL:
        # Launchers and apps built on Chromium/CEF/WebView2 (Steam, Battle.net, Riot, Teams, ...) play audio
        # from helper child processes with other names. Use those, but skip children with windows of their
        # own: those are separate apps, like a game started from its launcher.
        try:
            children = {child.pid for child in process.children(recursive=True)}
        except psutil.Error:
            children = set()
        if children:
            helpers = children - winapi.visible_window_pids()
            matches = [session for session in sessions if session[0] in helpers]
    return name, _exe(pid), matches


def _reference_volume(matches):
    """The session whose level the change is based on: the first one actually playing, if any."""
    return next((volume for _, volume, active in matches if active), matches[0][1])


def _apply(matches, level):
    for _, volume, _ in matches:
        try:
            volume.SetMasterVolume(level, None)
            if volume.GetMute():
                volume.SetMute(False, None)  # a mute set elsewhere (e.g. the volume mixer) would hide the change
        except comtypes.COMError:
            pass  # session closed in the meantime


def change_volume(target, steps):
    """Step an app's volume up/down. Returns (name, exe, new level or None if it has no audio) or None."""
    found = _find(target)
    if found is None:
        return None
    name, exe, matches = found
    if not matches:
        return name, exe, None
    current = _reference_volume(matches).GetMasterVolume()
    level = min(max(round(current * STEPS) + steps, 0), STEPS) / STEPS
    _apply(matches, level)
    return name, exe, level


def toggle_mute(target):
    """Mute an app (volume 0) or restore the volume it had before. Same return value as change_volume."""
    found = _find(target)
    if found is None:
        return None
    name, exe, matches = found
    if not matches:
        return name, exe, None
    reference = _reference_volume(matches)
    current = reference.GetMasterVolume()
    if round(current * 100) == 0 or reference.GetMute():
        level = current if round(current * 100) else _level_before_mute.pop(name.lower(), 1.0)
    else:
        _level_before_mute[name.lower()] = current
        level = 0.0
    _apply(matches, level)
    return name, exe, level
