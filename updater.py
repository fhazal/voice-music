"""Update check for the installed friends' version: runs once at start-up.

Asks GitHub for the latest release of fhazal/voice-music. If it is newer, downloads the installer,
checks its SHA-256 against the digest GitHub publishes for that file, installs it quietly (the installer
keeps the saved webhook and starts the program again) and exits so its files can be replaced.
Any problem is logged and ignored: the program just keeps working.
"""
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

VERSION = "1.4"  # keep in step with AppVer in installer.iss
API = "https://api.github.com/repos/fhazal/voice-music/releases/latest"
UA = {"User-Agent": "VoiceMusic-Updater"}


def as_tuple(v: str) -> tuple:
    return tuple(int(x) for x in v.lstrip("vV").split(".") if x.isdigit())


def find_update(current: str = VERSION):
    """(version, download url, sha256) of a newer release, or None."""
    with urllib.request.urlopen(urllib.request.Request(API, headers=UA), timeout=10) as r:
        rel = json.load(r)
    latest = str(rel.get("tag_name", ""))
    if as_tuple(latest) <= as_tuple(current):
        return None
    for a in rel.get("assets", []):
        name, digest = str(a.get("name", "")), str(a.get("digest", ""))
        if name.startswith("VoiceMusic-Setup-") and name.endswith(".exe") and digest.startswith("sha256:"):
            return latest.lstrip("vV"), a["browser_download_url"], digest[7:].lower()
    return None  # no installer with a published checksum: never run an unchecked file


def download(url: str, sha256: str) -> Path:
    """Fetch the installer into a fresh temp folder and verify it; raises if the checksum is wrong."""
    path = Path(tempfile.mkdtemp(prefix="voicemusic-update-")) / "VoiceMusic-Setup.exe"
    h = hashlib.sha256()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r, open(path, "wb") as f:
        while chunk := r.read(1 << 20):
            h.update(chunk)
            f.write(chunk)
    if h.hexdigest().lower() != sha256:
        path.unlink(missing_ok=True)
        raise ValueError("update checksum does not match")
    return path


def run_installer(path: Path) -> None:
    subprocess.Popen(
        [str(path), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
        creationflags=0x00000008 | 0x00000200,  # detached, new process group: it outlives us
        close_fds=True,
    )


def check_and_update(say, log, enabled: bool = True) -> None:
    """Call from a background thread after start-up. Exits the process when an update is installing."""
    if not enabled:
        return
    try:
        found = find_update()
        if not found:
            log(f"up to date ({VERSION})")
            return
        version, url, sha = found
        log(f"update {VERSION} -> {version}")
        say("think", "Updating Voice Music…", f"to version {version}")
        path = download(url, sha)
        run_installer(path)
        log("installer started, exiting")
        os._exit(0)
    except Exception as e:  # offline, rate-limited, bad download: carry on with the current version
        log(f"update check failed: {e}")
        say("ready")
