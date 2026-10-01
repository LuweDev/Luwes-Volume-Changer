"""Settings window: the app and hotkeys for each row, plus the overlay toggle."""
import tkinter as tk
from tkinter import ttk

import config
import hotkeys
import winapi

BG = '#2b2b2b'
FG = '#ffffff'
HINT_FG = '#9a9a9a'
ERROR_FG = '#ff6b6b'
ENTRY_BG = '#3c3f41'
BUTTON_BG = '#4c5052'
PROMPT = 'Press keys...'
HEADERS = ('Application', 'Volume Down', 'Volume Up', 'Mute Toggle')

VK_RETURN, VK_SHIFT, VK_CONTROL, VK_MENU, VK_ESCAPE, VK_LWIN, VK_RWIN = 0x0D, 0x10, 0x11, 0x12, 0x1B, 0x5B, 0x5C
MODIFIER_KEYS = {VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN, *range(0xA0, 0xA6)}  # incl. left/right variants


class SettingsWindow:
    def __init__(self, root, settings, on_close):
        self.on_close = on_close
        self.capture = None  # (entry, variable, previous hotkey) while recording a hotkey
        self.drag_offset = (0, 0)

        self.window = tk.Toplevel(root, bg=BG)
        self.window.title('Volume Changer Settings')
        self.window.overrideredirect(True)  # uses the custom dark title bar below
        self.window.attributes('-topmost', True)
        self.window.protocol('WM_DELETE_WINDOW', self.cancel)
        self._build_title_bar()

        style = ttk.Style(self.window)
        style.theme_use('default')
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=BG, foreground=FG)

        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        for column, header in enumerate(HEADERS):
            main_frame.columnconfigure(column, weight=1)
            ttk.Label(main_frame, text=header).grid(row=0, column=column, padx=5, pady=5)

        self.rows = {}
        for row_number, row in enumerate(config.ROWS, start=1):
            variables = {'app': tk.StringVar(value=settings[f'{row}_down']['app_name'])}
            app_entry = self._entry(main_frame, variables['app'], disabledbackground=BG, disabledforeground=FG)
            app_entry.grid(row=row_number, column=0, padx=5, pady=5, sticky='ew')
            if row == config.FOCUSED:
                app_entry.configure(state='disabled')
            for column, action in enumerate(config.ACTIONS, start=1):
                variable = tk.StringVar(value=settings[f'{row}_{action}']['hotkey'])
                entry = self._entry(main_frame, variable, state='readonly', readonlybackground=ENTRY_BG)
                entry.grid(row=row_number, column=column, padx=5, pady=5, sticky='ew')
                entry.bind('<Button-1>', lambda event, entry=entry, variable=variable: self._start_capture(entry, variable))
                entry.bind('<KeyPress>', self._on_key_press)
                entry.bind('<KeyRelease>', self._on_key_release)
                variables[action] = variable
            self.rows[row] = variables
        row_number = len(config.ROWS) + 1

        tk.Label(main_frame, text='Click a hotkey box and press the new combination. Esc clears it.',
                 bg=BG, fg=HINT_FG).grid(row=row_number, column=0, columnspan=4, padx=5, sticky='w')
        self.overlay_enabled = tk.BooleanVar(value=settings['overlay_enabled'])
        tk.Checkbutton(main_frame, text='Show Volume Overlay', variable=self.overlay_enabled, bg=BG, fg=FG,
                       selectcolor=BUTTON_BG, activebackground=BG, activeforeground=FG
                       ).grid(row=row_number + 1, column=0, columnspan=4, pady=10, sticky='w')
        self.error_label = tk.Label(main_frame, bg=BG, fg=ERROR_FG)
        self.error_label.grid(row=row_number + 2, column=0, columnspan=4)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row_number + 3, column=0, columnspan=4, pady=20)
        for text, command in (('Save', self._save), ('Reset to Defaults', self._reset), ('Cancel', self.cancel)):
            tk.Button(button_frame, text=text, command=command, bg=BUTTON_BG, fg=FG, relief=tk.FLAT, padx=10, pady=5
                      ).pack(side=tk.LEFT, padx=5)

        # Clicking anywhere else stops recording a hotkey.
        self.window.bind('<Button-1>', self._on_click, add='+')

        width, height = 600, 400
        x = (self.window.winfo_screenwidth() - width) // 2
        y = (self.window.winfo_screenheight() - height) // 2
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        self.focus()

    def focus(self):
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def cancel(self):
        self._close(None)

    def _build_title_bar(self):
        title_bar = tk.Frame(self.window, bg=BG, height=30)
        title_bar.pack(fill=tk.X)
        title = tk.Label(title_bar, text='Volume Changer Settings', bg=BG, fg=FG, font=('Segoe UI', 10))
        title.pack(side=tk.LEFT, padx=10)
        tk.Button(title_bar, text='×', bg=BG, fg=FG, font=('Segoe UI', 13), relief=tk.FLAT, command=self.cancel
                  ).pack(side=tk.RIGHT, padx=10)
        for widget in (title_bar, title):
            widget.bind('<Button-1>', self._start_drag)
            widget.bind('<B1-Motion>', self._drag)

    def _entry(self, parent, variable, **options):
        return tk.Entry(parent, textvariable=variable, bg=ENTRY_BG, fg=FG, insertbackground=FG, relief=tk.FLAT,
                        selectbackground=BUTTON_BG, selectforeground=FG, **options)

    def _start_drag(self, event):
        self.drag_offset = (event.x_root - self.window.winfo_x(), event.y_root - self.window.winfo_y())

    def _drag(self, event):
        x, y = self.drag_offset
        self.window.geometry(f'+{event.x_root - x}+{event.y_root - y}')

    def _start_capture(self, entry, variable):
        if self.capture and self.capture[0] is entry:
            return
        self._cancel_capture()
        self.capture = (entry, variable, variable.get())
        variable.set(PROMPT)
        entry.focus_set()

    def _cancel_capture(self):
        """Stop recording and put back the hotkey the box had before."""
        if self.capture:
            _, variable, previous = self.capture
            variable.set(previous)
            self.capture = None

    def _on_click(self, event):
        if self.capture and event.widget is not self.capture[0]:
            self._cancel_capture()

    @staticmethod
    def _held_modifiers():
        modifiers = 0
        if winapi.key_down(VK_CONTROL):
            modifiers |= winapi.MOD_CONTROL
        if winapi.key_down(VK_MENU):
            modifiers |= winapi.MOD_ALT
        if winapi.key_down(VK_SHIFT):
            modifiers |= winapi.MOD_SHIFT
        if winapi.key_down(VK_LWIN) or winapi.key_down(VK_RWIN):
            modifiers |= winapi.MOD_WIN
        return modifiers

    def _on_key_press(self, event):
        if not self.capture or event.widget is not self.capture[0]:
            return 'break'  # hotkey boxes are only changed by recording
        variable = self.capture[1]
        vk, modifiers = event.keycode, self._held_modifiers()
        if vk in MODIFIER_KEYS:
            self._show_held_modifiers(modifiers)
        elif vk == VK_ESCAPE and not modifiers:
            variable.set('')  # Esc clears the hotkey, disabling that action
            self.capture = None
        elif vk == VK_RETURN and not modifiers:
            self._cancel_capture()
        elif hotkeys.needs_modifier(vk) and not modifiers & (winapi.MOD_CONTROL | winapi.MOD_ALT | winapi.MOD_WIN):
            pass  # a plain typing key (even with Shift) would swallow that key in every other app
        else:
            hotkey = hotkeys.format_hotkey(modifiers, vk)
            if hotkey:
                variable.set(hotkey)
                self.capture = None
        return 'break'

    def _on_key_release(self, event):
        if self.capture and event.widget is self.capture[0] and event.keycode in MODIFIER_KEYS:
            self._show_held_modifiers(self._held_modifiers())
        return 'break'

    def _show_held_modifiers(self, modifiers):
        self.capture[1].set(f'{hotkeys.format_modifiers(modifiers)}+…' if modifiers else PROMPT)

    def _reset(self):
        self._cancel_capture()
        defaults = config.defaults()
        for row, variables in self.rows.items():
            variables['app'].set(defaults[f'{row}_down']['app_name'])
            for action in config.ACTIONS:
                variables[action].set(defaults[f'{row}_{action}']['hotkey'])
        self.overlay_enabled.set(True)

    def _save(self):
        self._cancel_capture()
        settings = {}
        for row, variables in self.rows.items():
            app = variables['app'].get()
            app = config.normalize_app(app) if app.strip() else config.ROWS[row]
            for action in config.ACTIONS:
                settings[f'{row}_{action}'] = {'hotkey': variables[action].get(), 'app_name': app}
        settings['overlay_enabled'] = self.overlay_enabled.get()
        try:
            config.save(settings)
        except OSError as error:
            self.error_label.configure(text=f'Failed to save settings: {error}')
            return
        self._close(settings)

    def _close(self, settings):
        self.capture = None
        self.window.destroy()
        self.on_close(settings)
