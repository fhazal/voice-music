"""The small banner shown at the top of the screen: icon, title, sub-line and a live level meter."""
import queue
import time
import tkinter as tk

W, H = 330, 60
KEY = "#010101"  # drawn transparent, so the banner can have rounded corners
PANEL, EDGE, TEXT, DIM = "#0b1220", "#2a3850", "#e9eef6", "#8d9ab0"
ICON_FONT = "Segoe MDL2 Assets"

# state -> (accent colour, icon glyph, default title, default sub, seconds on screen)
STATES = {
    "ready": ("#e8b04b", "", "Voice Music", "Hold mouse 4 and talk", 4),
    "listen": ("#ed4245", "", "Listening", "Let go when you're done", 60),
    "think": ("#e8b04b", "", "Working…", "", 60),
    "ok": ("#57f287", "", "Done", "", 4),
    "warn": ("#f0a04b", "", "Couldn't do that", "", 6),
    "listen_key": ("#e8b04b", "", "Press your new key", "Esc to cancel", 22),
}


def rounded(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


def run_overlay(ui: "queue.Queue", get_level, start=None, tray_dir=None, key=None) -> None:
    """ui carries (state, title, sub) tuples; get_level() returns 0..1 while recording."""
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.96)
    root.configure(bg=KEY)
    root.attributes("-transparentcolor", KEY)
    cv = tk.Canvas(root, width=W, height=H, bg=KEY, highlightthickness=0)
    cv.pack()
    root.geometry(f"{W}x{H}+{(root.winfo_screenwidth() - W) // 2}+22")

    accent = rounded(cv, 1, 1, W - 1, H - 1, 12, fill="#ed4245", outline="")
    rounded(cv, 5, 1, W - 1, H - 1, 12, fill=PANEL, outline=EDGE)
    icon = cv.create_text(34, H // 2, text="", font=(ICON_FONT, 18), fill="#ed4245")
    title = cv.create_text(62, 22, text="", anchor="w", font=("Segoe UI Semibold", 11), fill=TEXT)
    sub = cv.create_text(62, 40, text="", anchor="w", font=("Segoe UI", 9), fill=DIM, width=W - 62 - 70)
    bars = [cv.create_rectangle(W - 70 + i * 11, H // 2 - 2, W - 64 + i * 11, H // 2 + 2, fill="#ed4245", outline="") for i in range(5)]
    state = {"name": "ready", "until": 0.0, "shown": False, "level": 0.0}
    weights = [0.55, 0.85, 1.0, 0.8, 0.5]

    def apply(name, t, s):
        col, glyph, dt, ds, secs = STATES[name]
        state.update(name=name, until=time.time() + secs if secs < 60 else time.time() + 60)
        cv.itemconfig(accent, fill=col)
        cv.itemconfig(icon, text=glyph, fill=col)
        cv.itemconfig(title, text=t or dt)
        cv.itemconfig(sub, text=s if s else ds)
        for b in bars:
            cv.itemconfig(b, fill=col, state="normal" if name == "listen" else "hidden")
        if not state["shown"]:
            root.deiconify()
            state["shown"] = True

    def tick():
        try:
            while True:
                item = ui.get_nowait()
                if item[0] == "hide":
                    root.withdraw()
                    state["shown"] = False
                    state["until"] = 0
                    continue
                apply(item[0], item[1] if len(item) > 1 else "", item[2] if len(item) > 2 else "")
        except queue.Empty:
            pass
        name = state["name"]
        if name == "listen":
            lvl = state["level"] = state["level"] * 0.55 + min(1.0, get_level() * 9) * 0.45
            for i, b in enumerate(bars):
                h = 2 + int(lvl * 20 * weights[i] * (0.75 + 0.25 * ((time.time() * 7 + i) % 2)))
                cv.coords(b, W - 70 + i * 11, H // 2 - h, W - 64 + i * 11, H // 2 + h)
            pulse = 0.5 + 0.5 * ((time.time() * 2) % 1)
            cv.itemconfig(icon, fill="#ed4245" if pulse > 0.75 else "#ff8a8c")
        elif name == "think":
            dots = "." * (1 + int(time.time() * 3) % 3)
            cv.itemconfig(icon, fill="#e8b04b" if int(time.time() * 2) % 2 else "#ffd98a")
            if cv.itemcget(title, "text").rstrip(".…") in ("Sending", "Working", "Understanding"):
                cv.itemconfig(title, text=cv.itemcget(title, "text").rstrip(".…") + dots)
        if state["shown"] and state["until"] and time.time() > state["until"]:
            root.withdraw()
            state["shown"] = False
        root.after(50, tick)

    if start:
        start()
    if tray_dir is not None:
        try:
            from tray import start_tray

            start_tray(tray_dir, key=key)
        except Exception:  # the program works without a tray icon
            pass
    root.withdraw()
    root.after(50, tick)
    root.mainloop()
