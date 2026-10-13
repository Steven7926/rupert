from __future__ import annotations

from typing import Callable, Union

Hit = Union[None, str, tuple[int, tuple[int, int, int, int]]]
OwnIds = Callable[[], set[int]]

MIN_W, MIN_H = 140, 60


class WinTracker:

    SKIP = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}

    def __init__(self, own_ids: OwnIds):
        import ctypes
        from ctypes import wintypes
        self.ct, self.wt = ctypes, wintypes
        self.user32 = ctypes.windll.user32
        self.dwm = ctypes.windll.dwmapi
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.own_ids = own_ids

    def active(self) -> Hit:
        hwnd = self.user32.GetForegroundWindow()
        if hwnd and int(hwnd) in self.own_ids():
            return "keep"
        if not hwnd or self.user32.IsIconic(hwnd):
            return None
        buf = self.ct.create_unicode_buffer(64)
        self.user32.GetClassNameW(hwnd, buf, 64)
        if buf.value in self.SKIP:
            return None
        r = self.wt.RECT()
        if self.dwm.DwmGetWindowAttribute(hwnd, 9, self.ct.byref(r), self.ct.sizeof(r)) != 0:
            self.user32.GetWindowRect(hwnd, self.ct.byref(r))
        if r.right - r.left < MIN_W or r.bottom - r.top < MIN_H:
            return "keep"
        return int(hwnd), (r.left, r.top, r.right, r.bottom)


class X11Tracker:

    def __init__(self, own_ids: OwnIds):
        from Xlib import X, display
        self.X = X
        self.display = display.Display()
        self.root = self.display.screen().root
        self.ACTIVE = self.display.intern_atom("_NET_ACTIVE_WINDOW")
        self.FRAME = self.display.intern_atom("_NET_FRAME_EXTENTS")
        self.GTK = self.display.intern_atom("_GTK_FRAME_EXTENTS")
        self.own_ids = own_ids

    def _extents(self, window, atom) -> list[int] | None:
        p = window.get_full_property(atom, self.X.AnyPropertyType)
        return list(p.value) if p is not None and len(p.value) == 4 else None

    def active(self) -> Hit:
        try:
            p = self.root.get_full_property(self.ACTIVE, self.X.AnyPropertyType)
            if p is None or not len(p.value) or not p.value[0]:
                return None
            wid = int(p.value[0])
            if wid in self.own_ids():
                return "keep"
            w = self.display.create_resource_object("window", wid)
            g = w.get_geometry()
            t = self.root.translate_coords(w, 0, 0)
            x, y, width, height = t.x, t.y, g.width, g.height
            ext = self._extents(w, self.FRAME)
            if ext:
                left, right, top, bottom = ext
                x, y, width, height = x - left, y - top, width + left + right, height + top + bottom
            gtk = self._extents(w, self.GTK)
            if gtk:
                left, right, top, bottom = gtk
                x, y, width, height = x + left, y + top, width - left - right, height - top - bottom
            if width < MIN_W or height < MIN_H:
                return "keep"
            return wid, (x, y, x + width, y + height)
        except Exception:
            return "keep"
