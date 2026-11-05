"""Hold mouse button 4, say a music command, let go: the bot plays it.

Light version for friends: it records a short clip and uploads it through your webhook.
The BajuBesi server turns the speech into text and deletes the clip right away.
"""
import ctypes
import io
import json
import queue
import sys
import threading
import time
import urllib.request
import uuid
import wave
import winsound
from pathlib import Path

import numpy as np
import sounddevice as sd

from overlay import run_overlay

FROZEN = getattr(sys, "frozen", False)
HERE = Path(sys.executable).parent if FROZEN else Path(__file__).parent
if FROZEN:  # no console in the .exe: keep the log in a file next to it
    sys.stdout = sys.stderr = open(HERE / "run.log", "w", encoding="utf-8", buffering=1)

CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
RATE = 16000
MIN_SECONDS = 0.4
MAX_SECONDS = 15
VK = {"x1": 0x05, "x2": 0x06}[CFG.get("button", "x1")]

ui: "queue.Queue[tuple[str, str]]" = queue.Queue()
frames: list = []
stream = None
held = False
started = 0.0
level = 0.0


def say(state: str, title: str = "", sub: str = "") -> None:
    ui.put((state, title, sub))


def log(text: str) -> None:
    print(time.strftime("%H:%M:%S"), text, flush=True)


def beep(freq: int) -> None:
    threading.Thread(target=winsound.Beep, args=(freq, 60), daemon=True).start()


def on_audio(data, *_):
    global level
    frames.append(data.copy())
    level = float(np.sqrt(np.mean((data.astype("float32") / 32768.0) ** 2)))


def start_recording() -> None:
    global stream, held, started
    if held:
        return
    held = True
    started = time.time()
    frames.clear()
    stream = sd.InputStream(samplerate=RATE, channels=1, dtype="int16", callback=on_audio)
    stream.start()
    beep(900)
    say("listen")


def stop_recording() -> None:
    global stream, held
    if not held:
        return
    held = False
    stream.stop()
    stream.close()
    stream = None
    beep(600)
    audio = np.concatenate(frames)[:, 0] if frames else np.zeros(0, dtype="int16")
    if len(audio) < RATE * MIN_SECONDS:
        say("hide", "")
        return
    say("think", "Sending…")
    threading.Thread(target=send, args=(audio[: RATE * MAX_SECONDS],), daemon=True).start()


def send(audio) -> None:
    try:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(audio.tobytes())
        boundary = uuid.uuid4().hex
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"files[0]\"; filename=\"command.wav\"\r\n"
            f"Content-Type: audio/wav\r\n\r\n"
        ).encode() + buf.getvalue() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            CFG["webhook"],
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "VoiceMusic/2"},
        )
        with urllib.request.urlopen(req, timeout=20):
            pass
        say("ok", "Sent to the bot", "It will play in your voice channel")
    except Exception as e:  # keep the program alive whatever happens
        log(f"send failed: {e}")
        say("warn", "Couldn't send", str(e)[:70])


def watch_button() -> None:
    """Poll the button state (no hook, so games and anti-cheat have nothing to block)."""
    down = False
    get = ctypes.windll.user32.GetAsyncKeyState
    while True:
        now = bool(get(VK) & 0x8000)
        if now != down:
            down = now
            log("button 4 " + ("down" if down else "up"))
            (start_recording if down else stop_recording)()
        if held and time.time() - started > MAX_SECONDS:
            stop_recording()
        time.sleep(0.01)


def single_instance() -> None:
    ctypes.windll.kernel32.CreateMutexW(None, False, "VoiceMusicFriend")
    if ctypes.windll.kernel32.GetLastError() == 183:
        sys.exit("Already running")


def main() -> None:
    single_instance()

    def start():
        threading.Thread(target=watch_button, daemon=True).start()
        say("ready")

    run_overlay(ui, lambda: level if held else 0.0, start, HERE)


if __name__ == "__main__":
    sys.exit(main())
