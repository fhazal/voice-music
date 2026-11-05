"""Which key or mouse button is the voice key: names, capture ("press the key you want") and saving."""
import ctypes
import json
import threading
import time
from pathlib import Path

# config.json value -> (virtual-key code, name shown to people)
FIXED = {
    "x1": (0x05, "Mouse 4"), "x2": (0x06, "Mouse 5"), "middle": (0x04, "Middle mouse"),
    "pageup": (0x21, "Page Up"), "pagedown": (0x22, "Page Down"), "home": (0x24, "Home"), "end": (0x23, "End"),
    "insert": (0x2D, "Insert"), "delete": (0x2E, "Delete"), "capslock": (0x14, "Caps Lock"),
    "scrolllock": (0x91, "Scroll Lock"), "pause": (0x13, "Pause"), "space": (0x20, "Space"),
    "up": (0x26, "Up arrow"), "down": (0x28, "Down arrow"), "left": (0x25, "Left arrow"), "right": (0x27, "Right arrow"),
}
for _i in range(1, 25):
    FIXED[f"f{_i}"] = (0x6F + _i, f"F{_i}")
for _i in range(10):
    FIXED[f"num{_i}"] = (0x60 + _i, f"Numpad {_i}")
    FIXED[f"{_i}"] = (0x30 + _i, f"{_i}")
for _c in "abcdefghijklmnopqrstuvwxyz":
    FIXED[_c] = (ord(_c.upper()), _c.upper())

# Keys the picker refuses: both mouse buttons, Esc (cancels), Windows keys, Enter/Backspace/Tab, modifiers.
BLOCKED = {0x01, 0x02, 0x03, 0x08, 0x09, 0x0D, 0x10, 0x11, 0x12, 0x1B, 0x5B, 0x5C, 0x5D, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}
BY_VK = {vk: name for name, (vk, _) in FIXED.items()}
LABEL_BY_VK = {vk: label for _, (vk, label) in FIXED.items()}


def resolve(name: str):
    """(vk, label) for a config value; unknown values fall back to Mouse 4."""
    name = str(name or "x1").lower().strip()
    if name in FIXED:
        return FIXED[name]
    if name.startswith("vk:"):
        try:
            vk = int(name[3:], 0)
            if 1 <= vk <= 254 and vk not in BLOCKED:
                return vk, f"Key {vk}"
        except ValueError:
            pass
    return FIXED["x1"]


class KeyState:
    """The current voice key, shared by the button watcher and the tray menu."""

    def __init__(self, cfg: dict, cfg_path: Path):
        self.cfg_path = cfg_path
        self.vk, self.label = resolve(cfg.get("button"))
        self.capturing = False

    def change(self, say) -> None:
        """Ask for a new key on the banner, then switch to it and remember it."""
        if self.capturing:
            return
        threading.Thread(target=self._capture, args=(say,), daemon=True).start()

    def _capture(self, say) -> None:
        get = ctypes.windll.user32.GetAsyncKeyState
        self.capturing = True
        try:
            say("listen_key")
            deadline = time.time() + 2  # let go of whatever opened the menu first
            while time.time() < deadline and any(get(v) & 0x8000 for v in range(1, 255)):
                time.sleep(0.02)
            end = time.time() + 20
            while time.time() < end:
                if get(0x1B) & 0x8000:  # Esc
                    say("ready", "", f"Hold {self.label} and talk")
                    return
                for vk in range(3, 255):
                    if vk in BLOCKED:
                        continue
                    if get(vk) & 0x8000:
                        self._set(vk)
                        say("ok", f"Voice key: {self.label}", "Hold it and talk")
                        return
                time.sleep(0.01)
            say("ready", "", f"Hold {self.label} and talk")
        finally:
            time.sleep(0.3)  # the new key is still down: don't count that press as a command
            self.capturing = False

    def _set(self, vk: int) -> None:
        name = BY_VK.get(vk, f"vk:{vk}")
        self.vk, self.label = resolve(name)
        try:
            cfg = json.loads(self.cfg_path.read_text(encoding="utf-8"))
            cfg["button"] = name
            self.cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass  # still works until the next start
