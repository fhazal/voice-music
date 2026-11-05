"""Speech to text for the voice music cog: POST raw audio to /transcribe, get {"text": ...}."""
import io
import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from faster_whisper import WhisperModel

log = logging.getLogger("voice-stt")
MODEL = os.environ.get("STT_MODEL", "large-v3-turbo")
VOCAB = Path("/data/vocabulary.txt")
MAX_BYTES = 5_000_000

app = FastAPI()
try:
    model = WhisperModel(MODEL, device="cuda", compute_type="int8", download_root="/data/models")
    DEVICE = "cuda"
except Exception as e:  # no usable GPU: still works, slower
    log.warning("GPU unavailable (%s), using CPU", e)
    model = WhisperModel(MODEL, device="cpu", compute_type="int8", download_root="/data/models")
    DEVICE = "cpu"


def vocabulary() -> str:
    try:
        return ", ".join(l.strip() for l in VOCAB.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#"))
    except OSError:
        return ""


@app.get("/health")
def health():
    return {"ok": True, "device": DEVICE, "model": MODEL}


@app.post("/transcribe")
async def transcribe(request: Request):
    data = await request.body()
    if not data or len(data) > MAX_BYTES:
        return {"text": "", "error": "bad size"}
    t = time.time()
    prompt = "Music commands: play, skip, stop, pause, resume, volume. Artists and songs: " + vocabulary()
    segments, info = model.transcribe(io.BytesIO(data), initial_prompt=prompt, vad_filter=True, beam_size=5)
    text = " ".join(s.text.strip() for s in segments).strip()
    log.warning("heard %r in %.2fs (%s)", text, time.time() - t, info.language)
    return {"text": text, "language": info.language}
