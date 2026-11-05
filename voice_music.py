"""Hold mouse button 4, say a music command, let go: the Red bot runs it.

Speech is turned into text on this PC (faster-whisper); only the text goes to the bot.
"""
import glob
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.request
import winsound
from pathlib import Path

import numpy as np
import sysconfig
import sounddevice as sd

FROZEN = getattr(sys, "frozen", False)
HERE = Path(sys.executable).parent if FROZEN else Path(__file__).parent
if FROZEN:  # no console in the .exe: keep the log in a file next to it
    sys.stdout = sys.stderr = open(HERE / "run.log", "w", encoding="utf-8", buffering=1)

# CUDA libraries (pip nvidia-cublas-cu12, nvidia-cudnn-cu12) live outside the usual PATH.
_base = getattr(sys, "_MEIPASS", sysconfig.get_paths()["purelib"])
for _d in glob.glob(os.path.join(_base, "nvidia", "*", "bin")):
    os.add_dll_directory(_d)
    os.environ["PATH"] = _d + os.pathsep + os.environ["PATH"]

from faster_whisper import WhisperModel
from overlay import run_overlay
import ctypes

CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
RATE = 16000
MIN_SECONDS = 0.4
XBUTTON = {"x1": 1, "x2": 2}[CFG.get("button", "x1")]
VOCAB_FILE = HERE / "vocabulary.txt"


def vocabulary() -> str:
    """Artist and song names to bias the speech model (one per line in vocabulary.txt)."""
    try:
        names = [l.strip() for l in VOCAB_FILE.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    except OSError:
        names = []
    return ", ".join(names)


def prompt() -> str:
    return "Music commands: play, skip, stop, pause, resume, volume. Artists and songs: " + vocabulary()

ui: "queue.Queue[tuple[str, str]]" = queue.Queue()
frames: list = []
stream = None
held = False
model = None
level = 0.0


def say(state: str, title: str = "", sub: str = "") -> None:
    ui.put((state, title, sub))


def beep(freq: int) -> None:
    threading.Thread(target=winsound.Beep, args=(freq, 60), daemon=True).start()


def on_audio(data, *_):
    global level
    frames.append(data.copy())
    level = float(np.sqrt(np.mean(data.astype("float32") ** 2)))


def start_recording() -> None:
    global stream, held
    if held:
        return
    held = True
    frames.clear()
    stream = sd.InputStream(samplerate=RATE, channels=1, dtype="float32", callback=on_audio)
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
    audio = np.concatenate(frames)[:, 0] if frames else np.zeros(0, dtype="float32")
    if len(audio) < RATE * MIN_SECONDS:
        say("hide", "")
        return
    say("think", "Understanding…")
    threading.Thread(target=handle, args=(audio,), daemon=True).start()


def handle(audio) -> None:
    try:
        segments, _ = model.transcribe(audio, language=CFG.get("language"), initial_prompt=prompt(), vad_filter=True, beam_size=5)
        text = " ".join(s.text.strip() for s in segments).strip()
        if not text:
            say("warn", "Heard nothing", "Try again, a little louder")
            return
        # Whisper writes sentences ("Black Dog Bone, Bila Rindu."): search terms read better as plain words.
        text = re.sub(r"\s+", " ", re.sub(r"[,.;:!?…]+", " ", text)).strip()
        say("think", "Sending…", text)
        if CFG.get("webhook"):
            # Friend mode: post the words through a Discord webhook; the bot reads them in a private channel.
            req = urllib.request.Request(
                CFG["webhook"],
                data=json.dumps({"content": text}).encode(),
                headers={"Content-Type": "application/json", "User-Agent": "VoiceMusic/1"},
            )
            with urllib.request.urlopen(req, timeout=15):
                pass
            say("ok", "Sent to the bot", text)
            return
        req = urllib.request.Request(
            CFG["url"],
            data=json.dumps({"text": text}).encode(),
            headers={"Content-Type": "application/json", "X-Key": CFG["key"]},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.load(r)
        except urllib.error.HTTPError as e:
            res = json.load(e)
        say("ok" if res.get("ok") else "warn", "Sent" if res.get("ok") else "Couldn't do that", res.get("say", "?"))
    except Exception as e:  # keep the program alive whatever happens
        say("warn", "Error", str(e)[:70])


def log(text: str) -> None:
    print(time.strftime("%H:%M:%S"), text, flush=True)


def log(text: str) -> None:
    print(time.strftime("%H:%M:%S"), text, flush=True)


VK = {"x1": 0x05, "x2": 0x06}[CFG.get("button", "x1")]


def watch_button() -> None:
    """Poll the button state (no hook, so games and anti-cheat have nothing to block).
    The click still reaches the game, which is fine: 'Back' is rarely bound."""
    down = False
    get = ctypes.windll.user32.GetAsyncKeyState
    while True:
        now = bool(get(VK) & 0x8000)
        if now != down:
            down = now
            log("button 4 " + ("down" if down else "up"))
            (start_recording if down else stop_recording)()
        time.sleep(0.01)


def single_instance() -> None:
    """Quit if another copy is already running (two hooks would fight over the button)."""
    import ctypes

    ctypes.windll.kernel32.CreateMutexW(None, False, "VoiceMusicBot")
    if ctypes.windll.kernel32.GetLastError() == 183:
        sys.exit("Already running")


def load() -> None:
    global model
    name = CFG.get("model", "large-v3-turbo")
    say("think", "Loading speech model…", "The first run downloads about 1.6 GB")
    try:
        model = WhisperModel(name, device="cuda", compute_type="float16")
        model.transcribe(np.zeros(RATE, dtype="float32"))
    except Exception:
        # No usable NVIDIA card: a smaller model keeps the wait short on the CPU.
        model = WhisperModel(CFG.get("cpu_model", "small"), device="cpu", compute_type="int8")
    threading.Thread(target=watch_button, daemon=True).start()
    say("ready")


def main() -> None:
    single_instance()
    run_overlay(ui, lambda: level if held else 0.0, lambda: threading.Thread(target=load, daemon=True).start(), HERE)


if __name__ == "__main__":
    sys.exit(main())
