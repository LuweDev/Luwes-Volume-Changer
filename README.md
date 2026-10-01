# Luwe's Volume Changer

## Overview
Luwe's Volume Changer is a Windows utility that allows you to control the volume and mute state of specific applications (such as Brave and Discord) or the currently focused application using customizable global hotkeys. It features a modern, dark-themed settings window and an optional on-screen overlay to display volume changes.

## Features
- **Per-application volume control:** Adjust volume or mute/unmute for Brave, Discord, or any focused app. Unmuting restores the volume the app had before.
- **Customizable hotkeys:** Set your own global hotkeys for volume up, down, and mute actions per app. Hotkeys work on any keyboard layout and keep working while a game running as administrator is focused.
- **Finds apps on any output device:** Not just the default one (e.g. Discord on a headset, NVIDIA Broadcast, or a game still using a previous default device).
- **Smart focused-app detection:** Handles Microsoft Store apps and launchers that play audio from helper processes (Steam, Battle.net, Riot Client, Teams, ...).
- **On-screen overlay:** Visual feedback for volume changes, including app icons and mute status. It's click-through and never takes focus, so it can't pull you out of a game.
- **System tray integration:** Click the tray icon to open settings, or right-click it for settings/quit.
- **Single-instance enforcement:** Prevents multiple instances from running simultaneously.

## Default Hotkeys
| Action                | Brave                | Discord              | Focused App           |
|-----------------------|----------------------|----------------------|-----------------------|
| Volume Down           | Ctrl+Alt+Shift+1     | Ctrl+Alt+Shift+4     | Ctrl+Alt+Shift+7      |
| Volume Up             | Ctrl+Alt+Shift+2     | Ctrl+Alt+Shift+5     | Ctrl+Alt+Shift+8      |
| Mute/Unmute           | Ctrl+Alt+Shift+3     | Ctrl+Alt+Shift+6     | Ctrl+Alt+Shift+9      |

Hold a volume hotkey to keep changing the volume. Settings from older versions (e.g. `ctrl+alt+shift+£`) are converted automatically.

## Settings Window
- Open it by clicking the system tray icon (or right-click > Settings).
- Click a hotkey box and press the new key combination. Esc clears it, clicking elsewhere keeps the old one.
- Hotkeys are paused while the window is open, so existing combinations can be recorded.
- Change which app the Brave/Discord rows control by editing the Application name.
- Enable or disable the on-screen overlay, or restore the default settings.
- Settings are stored in `settings.json` next to the exe (or next to `main.py` when running from source).

## Overlay
- Shows the app icon, volume percentage, and a progress bar when you change volume or mute/unmute.
- Can be toggled on/off in settings.
- Muted apps are shown as small icons in the top-left corner.

## Installation
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the app:**
   ```bash
   python main.py
   ```

## Building the EXE
To build a standalone executable (Windows):
1. Make sure you have [PyInstaller](https://pyinstaller.org/) installed:
   ```bash
   pip install pyinstaller
   ```
2. Run the following command in CMD:
   ```bash
   pyinstaller --onefile --windowed --name "Luwe Volume Changer" --icon=image.ico --add-data "image.ico;." --add-data "disabled.ico;." --exclude-module numpy main.py
   ```
   The EXE will be created in the `dist/` folder. `--exclude-module numpy` stops PyInstaller from bundling numpy (~13 MB) through comtypes' optional numpy support.

## Project Layout
- `main.py`: entry point; wires the tray icon, hotkeys, overlay and settings together.
- `audio.py`: finds apps' audio sessions and changes their volume/mute.
- `hotkeys.py`: global hotkeys (Win32 `RegisterHotKey`) and hotkey parsing.
- `overlay.py`: the on-screen volume overlay and muted-app icons.
- `settings_window.py`: the settings window.
- `config.py`: settings file loading/saving and defaults.
- `winapi.py`: small ctypes bindings for the Windows APIs used.

## Dependencies
- pycaw (and comtypes, which it installs)
- psutil
- Pillow
- pystray
- tkinter (standard with Python)
