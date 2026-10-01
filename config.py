"""Settings: where they live, the defaults, and loading (including upgrading older files) and saving."""
import json
import os
import sys

FROZEN = getattr(sys, 'frozen', False)
# Keep settings next to the exe/script rather than in the working directory, which is often
# somewhere else (e.g. System32) when the app is started from a shortcut, the Startup folder or a task.
APP_DIR = os.path.dirname(os.path.abspath(sys.executable if FROZEN else __file__))
SETTINGS_FILE = os.path.join(APP_DIR, 'settings.json')

FOCUSED = 'focused'
ROWS = {'brave': 'brave.exe', 'discord': 'discord.exe', 'focused': FOCUSED}  # settings row -> default app
ACTIONS = ('down', 'up', 'mute')
DEFAULT_KEYS = {'brave': '123', 'discord': '456', 'focused': '789'}  # Ctrl+Alt+Shift + number row

# Older versions saved the shifted UK number-row characters (e.g. 'ctrl+alt+shift+£'), which only exist on
# a UK layout and crashed the app on a US one. The digit is the same physical key on any layout.
UK_SHIFTED_DIGITS = {'!': '1', '"': '2', '£': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9',
                     ')': '0'}


def resource_path(name):
    """Path to a file bundled with the app (inside the PyInstaller bundle when frozen)."""
    return os.path.join(getattr(sys, '_MEIPASS', APP_DIR), name)


def defaults():
    settings = {f'{row}_{action}': {'hotkey': f'ctrl+alt+shift+{key}', 'app_name': app}
                for row, app in ROWS.items() for action, key in zip(ACTIONS, DEFAULT_KEYS[row])}
    settings['overlay_enabled'] = True
    return settings


def normalize_app(name):
    name = name.strip()
    if name.lower() == FOCUSED:
        return FOCUSED
    return name if name.lower().endswith('.exe') else f'{name}.exe'


def _upgrade_hotkey(hotkey):
    parts = [part.strip() for part in hotkey.lower().split('+')]
    parts[-1] = UK_SHIFTED_DIGITS.get(parts[-1], parts[-1])
    return '+'.join(parts)


def load():
    settings = defaults()
    try:
        with open(SETTINGS_FILE, encoding='utf-8') as file:
            saved = json.load(file)
    except FileNotFoundError:
        return settings
    except (OSError, ValueError) as error:
        print(f'Could not read {SETTINGS_FILE}, using defaults: {error}')
        return settings
    if not isinstance(saved, dict):
        return settings

    for key, entry in settings.items():
        value = saved.get(key)
        if key == 'overlay_enabled':
            if isinstance(value, bool):
                settings[key] = value
        elif isinstance(value, str):  # oldest format: {"brave_down": "ctrl+alt+shift+!"}
            entry['hotkey'] = _upgrade_hotkey(value)
        elif isinstance(value, dict):
            if isinstance(value.get('hotkey'), str):
                entry['hotkey'] = _upgrade_hotkey(value['hotkey'])
            app = value.get('app_name')
            if isinstance(app, str) and app.strip() and entry['app_name'] != FOCUSED:
                entry['app_name'] = normalize_app(app)
    return settings


def save(settings):
    temp_file = SETTINGS_FILE + '.tmp'
    with open(temp_file, 'w', encoding='utf-8') as file:
        json.dump(settings, file, indent=4)
    os.replace(temp_file, SETTINGS_FILE)  # never leaves a half-written settings file behind


def hotkey_bindings(settings):
    """(hotkey, (app, action), repeat) for every action; holding a volume key repeats, holding mute doesn't."""
    return [(settings[f'{row}_{action}']['hotkey'], (settings[f'{row}_{action}']['app_name'], action), action != 'mute')
            for row in ROWS for action in ACTIONS]
