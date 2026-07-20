"""全局热键 —— Ctrl+Alt+I (输入) + Ctrl+Alt+O (输出)"""
import ctypes, threading
from ctypes import wintypes
from src.utils.logging_config import logger

MOD_CTRL, MOD_ALT = 0x0002, 0x0001
VK_LBRACKET, VK_RBRACKET = 0xDB, 0xDD  # [ and ] keys
WM_HOTKEY = 0x0312
HOTKEY_INPUT, HOTKEY_OUTPUT = 1, 2


class HotkeyListener:
    def __init__(self, on_input, on_output):
        self._on_input = on_input
        self._on_output = on_output
        self._running = False

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        return True

    def _loop(self):
        u32 = ctypes.windll.user32
        for hid, vk in [(HOTKEY_INPUT, VK_LBRACKET), (HOTKEY_OUTPUT, VK_RBRACKET)]:
            if not u32.RegisterHotKey(None, hid, MOD_CTRL | MOD_ALT, vk):
                err = ctypes.windll.kernel32.GetLastError()
                if err not in (0, 1409):
                    logger.warning(f"Hotkey {hid} error {err}")

        msg = wintypes.MSG()
        while self._running:
            if u32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == WM_HOTKEY:
                    try:
                        if msg.wParam == HOTKEY_INPUT:
                            self._on_input()
                        elif msg.wParam == HOTKEY_OUTPUT:
                            self._on_output()
                    except Exception as e:
                        logger.error(f"Hotkey callback: {e}")
                u32.TranslateMessage(ctypes.byref(msg))
                u32.DispatchMessageW(ctypes.byref(msg))

    def stop(self):
        self._running = False
