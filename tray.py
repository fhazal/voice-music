"""Tray icon next to the clock: status, Start with Windows, Open log folder, Quit."""
import os
import subprocess
import sys
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

STARTUP = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Voice Music.lnk"
AMBER, DARK = (232, 176, 75, 255), (65, 36, 2, 255)


def make_icon() -> Image.Image:
    """Amber rounded square with a small microphone."""
    s = 256
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, s - 8, s - 8), radius=56, fill=AMBER)
    d.rounded_rectangle((98, 50, 158, 150), radius=30, fill=DARK)
    d.arc((72, 90, 184, 190), 0, 180, fill=DARK, width=12)
    d.rectangle((122, 188, 134, 214), fill=DARK)
    d.rectangle((96, 208, 160, 220), fill=DARK)
    return img


def _ps(script: str) -> None:
    subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script], creationflags=0x08000000, check=False)


def start_with_windows(on: bool, exe: Path) -> None:
    if not on:
        STARTUP.unlink(missing_ok=True)
        return
    _ps(
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');$s.TargetPath='%s';$s.WorkingDirectory='%s';$s.Save()"
        % (STARTUP, exe, exe.parent)
    )


def start_tray(app_dir: Path, title: str = "Voice Music") -> None:
    """Show the tray icon. Quit ends the whole program."""
    exe = Path(sys.executable) if getattr(sys, "frozen", False) else None

    def toggle(icon, item):
        if exe:  # a start-up shortcut only makes sense for the installed .exe
            start_with_windows(not STARTUP.exists(), exe)

    def open_logs(icon, item):
        os.startfile(app_dir)

    def quit_app(icon, item):
        icon.stop()
        os._exit(0)

    items = [
        pystray.MenuItem(f"{title} is running", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start with Windows", toggle, checked=lambda item: STARTUP.exists(), enabled=exe is not None),
        pystray.MenuItem("Open log folder", open_logs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_app),
    ]
    pystray.Icon("VoiceMusic", make_icon(), f"{title}: hold mouse 4 and talk", pystray.Menu(*items)).run_detached()
