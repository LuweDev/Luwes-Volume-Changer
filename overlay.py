"""On-screen volume overlay and the strip of muted-app icons. Everything here runs on the Tk thread."""
import tkinter as tk

from PIL import Image, ImageEnhance, ImageTk

import winapi
from config import resource_path

BG = '#2b2b2b'
TRANSPARENT = '#000000'  # color key of the muted-apps strip
ICON_SIZE = 48
VOLUME_FONT = ('Segoe UI', 20, 'bold')
MESSAGE_FONT = ('Segoe UI', 16, 'bold')
SHOW_MS = 1000
FADE_MS = 300
FADE_STEPS = 30
MAX_CACHED_ICONS = 32


class VolumeOverlay:
    def __init__(self, root):
        self.window, self.hwnd = self._create_window(root, BG, '+10+80')
        frame = tk.Frame(self.window, bg=BG, padx=10, pady=0)
        frame.pack(fill=tk.BOTH, expand=True)
        self.icon_label = tk.Label(frame, bg=BG)
        self.icon_label.pack(side=tk.LEFT, padx=(0, 10))
        right = tk.Frame(frame, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Frame(right, height=2, bg=BG).pack(fill=tk.X)
        content = tk.Frame(right, bg=BG)
        content.pack(fill=tk.BOTH, expand=True, pady=(5, 2))
        self.volume_label = tk.Label(content, font=VOLUME_FONT, fg='#ffffff', bg=BG, width=13, anchor='w')
        self.volume_label.pack(fill=tk.X)
        self.bar = tk.Canvas(content, height=4, bg=BG, highlightthickness=0)
        self.bar.pack(fill=tk.X)
        self.bar_track = self.bar.create_rectangle(0, 0, 0, 4, fill='#0f0f0f', outline='')
        self.bar_fill = self.bar.create_rectangle(0, 0, 0, 4, fill='#ffffff', outline='')
        self.bar.bind('<Configure>', lambda event: self._draw_bar())
        self.level = None
        self.timer = None

        self.muted_window, _ = self._create_window(root, TRANSPARENT, '+5+20', color_key=(0, 0, 0))
        self.muted_frame = tk.Frame(self.muted_window, bg=TRANSPARENT, padx=10, pady=5)
        self.muted_frame.pack(fill=tk.BOTH, expand=True)
        self.muted_icons = {}  # app -> label

        self.icons = {}  # exe path -> (normal, muted) PhotoImages
        try:
            badge = Image.open(resource_path('disabled.ico')).convert('RGBA')
            self.badge = badge.resize((ICON_SIZE // 2, ICON_SIZE // 2), Image.Resampling.LANCZOS)
        except OSError as error:
            print(f'Could not load disabled.ico: {error}')
            self.badge = None

    @staticmethod
    def _create_window(root, bg, position, color_key=None):
        window = tk.Toplevel(root, bg=bg)
        window.overrideredirect(True)
        window.attributes('-topmost', True)
        window.wm_attributes('-toolwindow', True)
        # Map it once off-screen so the native window exists, then make it click-through and unable to
        # take focus, so it can never pull you out of a fullscreen game.
        window.geometry('+-32000+-32000')
        window.deiconify()
        window.update_idletasks()
        hwnd = int(window.wm_frame(), 16)
        winapi.make_overlay_window(hwnd)
        if color_key:
            winapi.set_window_color_key(hwnd, color_key)
        else:
            winapi.set_window_alpha(hwnd, 1.0)
        window.withdraw()
        window.geometry(position)
        return window, hwnd

    def show(self, name, exe, level):
        """Show an app's new volume (0..1), or that it has no audio session when level is None."""
        if level is None:
            self._show_message(f'No audio source detected for {name}')
        else:
            self._set_muted(name, exe, level == 0)
            self._show_level(exe, level)
        winapi.set_window_alpha(self.hwnd, 1.0)
        self.window.deiconify()
        self._schedule(SHOW_MS, self._fade_out)

    def clear(self):
        """Hide everything, e.g. when the overlay gets turned off."""
        for label in self.muted_icons.values():
            label.destroy()
        self.muted_icons.clear()
        self.muted_window.withdraw()
        if self.timer:
            self.window.after_cancel(self.timer)
            self.timer = None
        self.window.withdraw()

    def _show_level(self, exe, level):
        self.window.geometry('165x65')
        photo = self._icons(exe)[0]
        self.icon_label.configure(image=photo)
        self.icon_label.image = photo
        self.volume_label.configure(text=f'{round(level * 100)}%', font=VOLUME_FONT, width=13, pady=0)
        self.level = level
        self._draw_bar()

    def _show_message(self, text):
        self.icon_label.configure(image='')
        self.volume_label.configure(text=text, font=MESSAGE_FONT, width=0, pady=15)
        self.level = None
        self._draw_bar()
        self.window.geometry(f'{max(300, self.volume_label.winfo_reqwidth() + 40)}x65')

    def _draw_bar(self):
        width = self.bar.winfo_width() if self.level is not None else 0
        self.bar.coords(self.bar_track, 0, 0, width, 4)
        self.bar.coords(self.bar_fill, 0, 0, int(width * (self.level or 0)), 4)

    def _set_muted(self, name, exe, muted):
        key = name.lower()
        if muted and key not in self.muted_icons:
            photo = self._icons(exe)[1]
            label = tk.Label(self.muted_frame, image=photo, bg=TRANSPARENT)
            label.image = photo
            label.pack(side=tk.LEFT, padx=5)
            self.muted_icons[key] = label
            self.muted_window.deiconify()
        elif not muted and key in self.muted_icons:
            self.muted_icons.pop(key).destroy()
            if not self.muted_icons:
                self.muted_window.withdraw()

    def _icons(self, exe):
        """(normal, muted) icon images for an executable, cached."""
        key = (exe or '').lower()
        if key not in self.icons:
            image = winapi.extract_icon(exe, ICON_SIZE) or Image.new('RGBA', (ICON_SIZE, ICON_SIZE))
            muted = ImageEnhance.Brightness(image).enhance(0.66)
            if self.badge:
                muted.alpha_composite(self.badge, (ICON_SIZE // 2, ICON_SIZE // 2))
            if len(self.icons) >= MAX_CACHED_ICONS:
                del self.icons[next(iter(self.icons))]
            self.icons[key] = (ImageTk.PhotoImage(image), ImageTk.PhotoImage(muted))
        return self.icons[key]

    def _schedule(self, delay, callback):
        if self.timer:
            self.window.after_cancel(self.timer)
        self.timer = self.window.after(delay, callback)

    def _fade_out(self, step=1):
        if step < FADE_STEPS:
            winapi.set_window_alpha(self.hwnd, 1 - step / FADE_STEPS)
            self._schedule(FADE_MS // FADE_STEPS, lambda: self._fade_out(step + 1))
        else:
            self.timer = None
            self.window.withdraw()
