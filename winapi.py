"""Small ctypes bindings for the Win32 calls the app needs (replaces pywin32 + win32ui/MFC)."""
import ctypes
from ctypes import wintypes

from PIL import Image

# Private DLL instances so these argtypes never clash with other packages (pystray, comtypes).
user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
shell32 = ctypes.WinDLL('shell32', use_last_error=True)

WM_HOTKEY = 0x0312
WM_USER = 0x0400
WM_APP = 0x8000
PM_NOREMOVE = 0x0000
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x0001, 0x0002, 0x0004, 0x0008, 0x4000
MAPVK_VK_TO_CHAR = 2
ERROR_ALREADY_EXISTS = 183
ERROR_HOTKEY_ALREADY_REGISTERED = 1409
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT, WS_EX_LAYERED, WS_EX_NOACTIVATE = 0x00000020, 0x00080000, 0x08000000
LWA_COLORKEY, LWA_ALPHA = 0x1, 0x2
DI_MASK, DI_NORMAL = 0x1, 0x3
IMAGE_ICON, LR_SHARED = 1, 0x8000
IDI_APPLICATION = 32512

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG), ('biHeight', wintypes.LONG),
                ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG),
                ('biYPelsPerMeter', wintypes.LONG), ('biClrUsed', wintypes.DWORD),
                ('biClrImportant', wintypes.DWORD)]


def _declare(dll, name, restype, *argtypes):
    function = getattr(dll, name)
    function.restype = restype
    function.argtypes = argtypes
    return function


GetMessageW = _declare(user32, 'GetMessageW', wintypes.BOOL, ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                       wintypes.UINT, wintypes.UINT)
PeekMessageW = _declare(user32, 'PeekMessageW', wintypes.BOOL, ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                        wintypes.UINT, wintypes.UINT, wintypes.UINT)
PostThreadMessageW = _declare(user32, 'PostThreadMessageW', wintypes.BOOL, wintypes.DWORD, wintypes.UINT,
                              wintypes.WPARAM, wintypes.LPARAM)
RegisterHotKey = _declare(user32, 'RegisterHotKey', wintypes.BOOL, wintypes.HWND, ctypes.c_int, wintypes.UINT,
                          wintypes.UINT)
UnregisterHotKey = _declare(user32, 'UnregisterHotKey', wintypes.BOOL, wintypes.HWND, ctypes.c_int)
VkKeyScanW = _declare(user32, 'VkKeyScanW', ctypes.c_short, wintypes.WCHAR)
MapVirtualKeyW = _declare(user32, 'MapVirtualKeyW', wintypes.UINT, wintypes.UINT, wintypes.UINT)
GetKeyState = _declare(user32, 'GetKeyState', ctypes.c_short, ctypes.c_int)
GetForegroundWindow = _declare(user32, 'GetForegroundWindow', wintypes.HWND)
GetWindowThreadProcessId = _declare(user32, 'GetWindowThreadProcessId', wintypes.DWORD, wintypes.HWND,
                                    ctypes.POINTER(wintypes.DWORD))
GetClassNameW = _declare(user32, 'GetClassNameW', ctypes.c_int, wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
EnumWindows = _declare(user32, 'EnumWindows', wintypes.BOOL, WNDENUMPROC, wintypes.LPARAM)
EnumChildWindows = _declare(user32, 'EnumChildWindows', wintypes.BOOL, wintypes.HWND, WNDENUMPROC, wintypes.LPARAM)
IsWindowVisible = _declare(user32, 'IsWindowVisible', wintypes.BOOL, wintypes.HWND)
GetWindowLongPtrW = _declare(user32, 'GetWindowLongPtrW', ctypes.c_ssize_t, wintypes.HWND, ctypes.c_int)
SetWindowLongPtrW = _declare(user32, 'SetWindowLongPtrW', ctypes.c_ssize_t, wintypes.HWND, ctypes.c_int,
                             ctypes.c_ssize_t)
SetLayeredWindowAttributes = _declare(user32, 'SetLayeredWindowAttributes', wintypes.BOOL, wintypes.HWND,
                                      wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD)
LoadImageW = _declare(user32, 'LoadImageW', wintypes.HANDLE, wintypes.HINSTANCE, ctypes.c_void_p, wintypes.UINT,
                      ctypes.c_int, ctypes.c_int, wintypes.UINT)
DrawIconEx = _declare(user32, 'DrawIconEx', wintypes.BOOL, wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.HICON,
                      ctypes.c_int, ctypes.c_int, wintypes.UINT, wintypes.HBRUSH, wintypes.UINT)
DestroyIcon = _declare(user32, 'DestroyIcon', wintypes.BOOL, wintypes.HICON)
GetCurrentThreadId = _declare(kernel32, 'GetCurrentThreadId', wintypes.DWORD)
CreateMutexW = _declare(kernel32, 'CreateMutexW', wintypes.HANDLE, ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
CreateCompatibleDC = _declare(gdi32, 'CreateCompatibleDC', wintypes.HDC, wintypes.HDC)
CreateDIBSection = _declare(gdi32, 'CreateDIBSection', wintypes.HBITMAP, wintypes.HDC, ctypes.c_void_p,
                            wintypes.UINT, ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD)
SelectObject = _declare(gdi32, 'SelectObject', wintypes.HGDIOBJ, wintypes.HDC, wintypes.HGDIOBJ)
DeleteObject = _declare(gdi32, 'DeleteObject', wintypes.BOOL, wintypes.HGDIOBJ)
DeleteDC = _declare(gdi32, 'DeleteDC', wintypes.BOOL, wintypes.HDC)
SHDefExtractIconW = _declare(shell32, 'SHDefExtractIconW', ctypes.c_long, wintypes.LPCWSTR, ctypes.c_int,
                             wintypes.UINT, ctypes.POINTER(wintypes.HICON), ctypes.POINTER(wintypes.HICON),
                             wintypes.UINT)

_instance_mutex = None


def acquire_single_instance(name):
    """Return False if another instance already holds the named mutex."""
    global _instance_mutex
    _instance_mutex = CreateMutexW(None, False, name)
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS


def window_pid(hwnd):
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _class_name(hwnd):
    buffer = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, buffer, len(buffer))
    return buffer.value


def foreground_pid():
    """PID of the app that owns the foreground window (0 if there isn't one)."""
    hwnd = GetForegroundWindow()
    if not hwnd:
        return 0
    pid = window_pid(hwnd)
    if _class_name(hwnd) == 'ApplicationFrameWindow':
        # Store/UWP apps are framed by ApplicationFrameHost.exe; the app's own process owns a child window.
        hosted = []

        def find_hosted(child, _):
            child_pid = window_pid(child)
            if child_pid != pid:
                hosted.append(child_pid)
                return False
            return True

        EnumChildWindows(hwnd, WNDENUMPROC(find_hosted), 0)
        if hosted:
            return hosted[0]
    return pid


def visible_window_pids():
    """PIDs of all processes that own a visible top-level window."""
    pids = set()

    def collect(hwnd, _):
        if IsWindowVisible(hwnd):
            pids.add(window_pid(hwnd))
        return True

    EnumWindows(WNDENUMPROC(collect), 0)
    return pids


def key_down(vk):
    return GetKeyState(vk) & 0x8000 != 0


def vk_from_char(char):
    """Virtual-key code that types `char` on the current keyboard layout, or None."""
    result = VkKeyScanW(char)
    return None if result == -1 else result & 0xFF


def char_from_vk(vk):
    """Unshifted character a virtual-key code types on the current keyboard layout, or None."""
    char = MapVirtualKeyW(vk, MAPVK_VK_TO_CHAR) & 0x7FFF  # the top bit flags dead keys
    return chr(char) if char > 32 else None


def make_overlay_window(hwnd):
    """Make a window click-through and never take focus (so clicking it can't pull you out of a game)."""
    style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)


def set_window_alpha(hwnd, alpha):
    SetLayeredWindowAttributes(hwnd, 0, max(0, min(255, int(alpha * 255))), LWA_ALPHA)


def set_window_color_key(hwnd, rgb):
    red, green, blue = rgb
    SetLayeredWindowAttributes(hwnd, red | green << 8 | blue << 16, 0, LWA_COLORKEY)


def _render_icon(hicon, size, flags):
    header = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), size, -size, 1, 32)  # 32-bit top-down DIB
    bits = ctypes.c_void_p()
    hdc = CreateCompatibleDC(None)
    bitmap = CreateDIBSection(hdc, ctypes.byref(header), 0, ctypes.byref(bits), None, 0)
    try:
        previous = SelectObject(hdc, bitmap)
        DrawIconEx(hdc, 0, 0, hicon, size, size, 0, None, flags)
        SelectObject(hdc, previous)
        return ctypes.string_at(bits, size * size * 4)
    finally:
        DeleteObject(bitmap)
        DeleteDC(hdc)


def extract_icon(path, size):
    """The executable's icon as a size x size RGBA image (the generic app icon if it has none)."""
    hicon = wintypes.HICON()
    owned = bool(path) and SHDefExtractIconW(path, 0, 0, ctypes.byref(hicon), None, size) == 0 and bool(hicon)
    if not owned:
        hicon = LoadImageW(None, IDI_APPLICATION, IMAGE_ICON, size, size, LR_SHARED)
        if not hicon:
            return None
    try:
        color = _render_icon(hicon, size, DI_NORMAL)
        image = Image.frombuffer('RGBA', (size, size), color, 'raw', 'BGRa', 0, 1)
        if image.getchannel('A').getbbox() is None:
            # Old-style icon without an alpha channel: build the alpha from its transparency mask.
            mask = Image.frombuffer('RGBA', (size, size), _render_icon(hicon, size, DI_MASK), 'raw', 'BGRA', 0, 1)
            image = Image.frombuffer('RGBA', (size, size), color, 'raw', 'BGRA', 0, 1)
            image.putalpha(mask.getchannel('R').point(lambda value: 255 - value))
        return image
    finally:
        if owned:
            DestroyIcon(hicon)
