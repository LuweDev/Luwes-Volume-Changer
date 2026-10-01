"""Global hotkeys using the Win32 RegisterHotKey API.

Compared to a low-level keyboard hook (the `keyboard` package this replaces) this costs nothing per
keystroke, keeps working while an elevated window (e.g. a game running as admin) is focused, can't be
silently unhooked by Windows, and matches keys by virtual-key code, so 'ctrl+alt+shift+3' is the same
physical key on UK and US layouts.
"""
import ctypes
import re
import threading
import traceback
from ctypes import wintypes

import winapi

MODIFIERS = {
    'ctrl': winapi.MOD_CONTROL, 'control': winapi.MOD_CONTROL, 'left ctrl': winapi.MOD_CONTROL,
    'right ctrl': winapi.MOD_CONTROL, 'alt': winapi.MOD_ALT, 'left alt': winapi.MOD_ALT, 'right alt': winapi.MOD_ALT,
    'alt gr': winapi.MOD_CONTROL | winapi.MOD_ALT, 'shift': winapi.MOD_SHIFT, 'left shift': winapi.MOD_SHIFT,
    'right shift': winapi.MOD_SHIFT, 'windows': winapi.MOD_WIN, 'win': winapi.MOD_WIN,
    'left windows': winapi.MOD_WIN, 'right windows': winapi.MOD_WIN,
}
MODIFIER_ORDER = (('ctrl', winapi.MOD_CONTROL), ('alt', winapi.MOD_ALT), ('shift', winapi.MOD_SHIFT),
                  ('windows', winapi.MOD_WIN))

NAMED_KEYS = {
    'backspace': 0x08, 'tab': 0x09, 'enter': 0x0D, 'pause': 0x13, 'caps lock': 0x14, 'esc': 0x1B,
    'space': 0x20, 'page up': 0x21, 'page down': 0x22, 'end': 0x23, 'home': 0x24, 'left': 0x25,
    'up': 0x26, 'right': 0x27, 'down': 0x28, 'print screen': 0x2C, 'insert': 0x2D, 'delete': 0x2E,
    'menu': 0x5D, 'num *': 0x6A, 'num plus': 0x6B, 'num -': 0x6D, 'num .': 0x6E, 'num /': 0x6F,
    'num lock': 0x90, 'scroll lock': 0x91, 'volume mute': 0xAD, 'volume down': 0xAE, 'volume up': 0xAF,
    'next track': 0xB0, 'previous track': 0xB1, 'stop media': 0xB2, 'play/pause media': 0xB3,
    **{f'f{number}': 0x6F + number for number in range(1, 25)},
    **{f'num {number}': 0x60 + number for number in range(10)},
}
ALIASES = {'escape': 'esc', 'return': 'enter', 'del': 'delete', 'ins': 'insert', 'pgup': 'page up',
           'pgdn': 'page down', 'apps': 'menu'}
KEY_NAMES = {vk: name for name, vk in NAMED_KEYS.items()}
FUNCTION_AND_MEDIA_KEYS = set(range(0x70, 0x88)) | set(range(0xAD, 0xB4))

WM_RELOAD = winapi.WM_APP + 1


def parse(hotkey):
    """'ctrl+alt+shift+1' -> (modifier flags, virtual-key code). Raises ValueError if it can't be used."""
    modifiers, key = 0, None
    for part in re.split(r'\s*\+\s*(?=.)', hotkey.strip().lower()):
        if part in MODIFIERS:
            modifiers |= MODIFIERS[part]
        elif key is None:
            key = ALIASES.get(part, part)
        else:
            raise ValueError('has more than one non-modifier key')
    if key is None:
        raise ValueError('needs a key besides the modifiers')
    if key in NAMED_KEYS:
        return modifiers, NAMED_KEYS[key]
    if len(key) == 1:
        if key.isascii() and key.isalnum():
            return modifiers, ord(key.upper())  # letters and digits have layout-independent key codes
        vk = winapi.vk_from_char(key)
        if vk is not None:
            return modifiers, vk
        raise ValueError(f"uses '{key}', which isn't on the current keyboard layout")
    raise ValueError(f"uses an unknown key '{key}'")


def key_name(vk):
    if vk in KEY_NAMES:
        return KEY_NAMES[vk]
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk).lower()
    char = winapi.char_from_vk(vk)
    return char.lower() if char else None


def format_modifiers(modifiers):
    return '+'.join(name for name, flag in MODIFIER_ORDER if modifiers & flag)


def format_hotkey(modifiers, vk):
    """(modifier flags, virtual-key code) -> 'ctrl+alt+shift+1', or None for keys that can't be named."""
    key = key_name(vk)
    if key is None:
        return None
    prefix = format_modifiers(modifiers)
    return f'{prefix}+{key}' if prefix else key


def needs_modifier(vk):
    """Ordinary typing keys need Ctrl, Alt or Win, or the hotkey would swallow normal typing everywhere."""
    return vk not in FUNCTION_AND_MEDIA_KEYS


class HotkeyListener:
    """Owns the hotkeys on a dedicated thread and calls callback(payload) on that thread when one is pressed."""

    def __init__(self, callback, on_errors):
        self._callback = callback
        self._on_errors = on_errors
        self._pending = []
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._thread_id = None
        threading.Thread(target=self._run, name='hotkeys', daemon=True).start()
        self._ready.wait()

    def set_hotkeys(self, bindings):
        """Replace all hotkeys with (hotkey, payload, repeat) tuples; an empty list pauses them. Thread-safe."""
        with self._lock:
            self._pending = list(bindings)
        winapi.PostThreadMessageW(self._thread_id, WM_RELOAD, 0, 0)

    def _run(self):
        msg = wintypes.MSG()
        # Make sure this thread has a message queue before anyone posts to it.
        winapi.PeekMessageW(ctypes.byref(msg), None, winapi.WM_USER, winapi.WM_USER, winapi.PM_NOREMOVE)
        self._thread_id = winapi.GetCurrentThreadId()
        self._ready.set()
        payloads = {}
        while winapi.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == winapi.WM_HOTKEY and msg.wParam in payloads:
                try:
                    self._callback(payloads[msg.wParam])
                except Exception:
                    traceback.print_exc()  # one failed action must never stop the hotkeys
            elif msg.message == WM_RELOAD:
                payloads = self._register(payloads)

    def _register(self, old_payloads):
        for hotkey_id in old_payloads:
            winapi.UnregisterHotKey(None, hotkey_id)
        with self._lock:
            bindings = self._pending
        payloads, combos, errors = {}, set(), []
        for hotkey_id, (hotkey, payload, repeat) in enumerate(bindings, start=1):
            if not hotkey:
                continue
            try:
                modifiers, vk = parse(hotkey)
            except ValueError as error:
                errors.append(f'{hotkey} {error}')
                continue
            if (modifiers, vk) in combos:
                errors.append(f'{hotkey} is assigned to more than one action')
                continue
            if not winapi.RegisterHotKey(None, hotkey_id, modifiers | (0 if repeat else winapi.MOD_NOREPEAT), vk):
                code = ctypes.get_last_error()
                in_use = code == winapi.ERROR_HOTKEY_ALREADY_REGISTERED
                errors.append(f'{hotkey} is ' + ('already used by another program' if in_use else f'unavailable ({code})'))
                continue
            combos.add((modifiers, vk))
            payloads[hotkey_id] = payload
        if errors:
            self._on_errors(errors)
        return payloads
