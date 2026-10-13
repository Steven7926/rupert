from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import QAbstractNativeEventFilter

HOTKEY_LABEL = "Ctrl+Alt+R"


class HotkeyTaken(RuntimeError):
    def __init__(self):
        super().__init__(f"{HOTKEY_LABEL} is already used by another app")


class X11Hotkey(threading.Thread):

    def __init__(self, callback: Callable[[], None]):
        super().__init__(daemon=True)
        from Xlib import XK, X, display, error
        self.X, self.callback = X, callback
        self.display = display.Display()
        root = self.display.screen().root
        self.code = self.display.keysym_to_keycode(XK.string_to_keysym("r"))
        catch = error.CatchError(error.BadAccess)
        for extra in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
            root.grab_key(self.code, X.ControlMask | X.Mod1Mask | extra, True,
                          X.GrabModeAsync, X.GrabModeAsync, onerror=catch)
        self.display.sync()
        if catch.get_error():
            raise HotkeyTaken()

    def run(self) -> None:
        while True:
            ev = self.display.next_event()
            if ev.type == self.X.KeyPress and ev.detail == self.code:
                self.callback()


class WinHotkey(QAbstractNativeEventFilter):

    ID = 0xB0B
    WM_HOTKEY = 0x0312

    def __init__(self, callback: Callable[[], None]):
        super().__init__()
        import ctypes
        from ctypes import wintypes
        self.callback, self.wt = callback, wintypes
        mod_alt, mod_control, mod_norepeat, vk_r = 0x1, 0x2, 0x4000, 0x52
        if not ctypes.windll.user32.RegisterHotKey(None, self.ID, mod_control | mod_alt | mod_norepeat, vk_r):
            raise HotkeyTaken()

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) in (b"windows_dispatcher_MSG", b"windows_generic_MSG"):
            msg = self.wt.MSG.from_address(int(message))
            if msg.message == self.WM_HOTKEY and msg.wParam == self.ID:
                self.callback()
                return True, 0
        return False, 0
