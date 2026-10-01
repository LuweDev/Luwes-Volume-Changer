"""Luwe's Volume Changer: global hotkeys for per-app volume (Brave, Discord and whichever app is focused)."""
import os
import threading
import tkinter as tk

import pystray
from PIL import Image

import audio
import config
import winapi
from hotkeys import HotkeyListener
from overlay import VolumeOverlay
from settings_window import SettingsWindow

TITLE = 'Volume Changer'


class App:
    def __init__(self):
        self.settings = config.load()
        self.root = tk.Tk()
        self.root.withdraw()
        self.overlay = VolumeOverlay(self.root)
        self.settings_window = None
        self.tray_ready = threading.Event()
        self.tray = pystray.Icon(TITLE, Image.open(config.resource_path('image.ico')), TITLE, menu=pystray.Menu(
            pystray.MenuItem('Settings', self.on_settings, default=True),  # also opened by clicking the icon
            pystray.MenuItem('Quit', self.on_quit)))
        self.hotkeys = HotkeyListener(self.on_hotkey, self.on_hotkey_errors)

    def run(self):
        threading.Thread(target=self.tray.run, args=(self.on_tray_ready,), daemon=True).start()
        self.hotkeys.set_hotkeys(config.hotkey_bindings(self.settings))
        self.root.mainloop()

    def on_tray_ready(self, icon):
        icon.visible = True
        self.tray_ready.set()

    def on_hotkey(self, binding):
        """Runs on the hotkey thread, so the audio work never blocks the UI."""
        app, action = binding
        if action == 'mute':
            result = audio.toggle_mute(app)
        else:
            result = audio.change_volume(app, 1 if action == 'up' else -1)
        if result and self.settings['overlay_enabled']:
            self.root.after(0, self.overlay.show, *result)  # Tk may only be used from its own thread

    def on_hotkey_errors(self, errors):
        if self.tray_ready.wait(10):
            self.tray.notify(('\n'.join(errors))[:255], "Some hotkeys couldn't be set")

    def on_settings(self, icon, item):
        self.root.after(0, self.open_settings)

    def open_settings(self):
        if self.settings_window:
            self.settings_window.focus()
            return
        self.hotkeys.set_hotkeys([])  # pause them so their combinations can be recorded
        self.settings_window = SettingsWindow(self.root, self.settings, self.on_settings_closed)

    def on_settings_closed(self, new_settings):
        self.settings_window = None
        if new_settings:
            self.settings = new_settings
            if not new_settings['overlay_enabled']:
                self.overlay.clear()
        self.hotkeys.set_hotkeys(config.hotkey_bindings(self.settings))

    def on_quit(self, icon, item):
        icon.visible = False  # remove the tray icon now, otherwise a dead icon lingers until hovered
        os._exit(0)  # nothing needs saving, and this skips slow/fragile Tk and thread teardown


def main():
    if not winapi.acquire_single_instance('VolumeChangerUniqueMutexName'):
        return  # already running
    App().run()


if __name__ == '__main__':
    main()
