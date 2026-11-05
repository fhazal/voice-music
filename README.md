# Voice Music

Hold a mouse button, say a song, let go: your Red-DiscordBot plays it in your voice channel.
Made for the BajuBesi Discord by BajuBesi Labs.

```
hold mouse 4 → "play Eminem Slim Shady" → let go → the bot plays it
```

Say `play …`, `skip` (or `next`), `pause`, `resume`, `stop` or `volume 40`. English and Malay work.

## For friends: install

1. Ask the server admin for your **webhook address** (they send it privately; treat it like a password).
2. Download `VoiceMusic-Setup-….exe` from the [latest release](../../releases/latest) and run it.
3. Paste your webhook address when asked. Finish, then start Voice Music.

It installs in your own folder and needs no administrator rights to install. The program asks for
administrator rights when it starts so it can see the mouse button while a game has focus.

**Windows or your antivirus may warn about it.** The installer is not code-signed, and it reads the mouse
button state and your microphone, which security software distrusts. You can read all the source here. The
download page lists a SHA-256 checksum for every release so you can check your copy.

## What it does with your voice

- It records only while you hold the button (up to 15 seconds).
- The short clip is uploaded through your webhook to the server's private channel, turned into text on the
  server, and the clip is deleted right away. Nothing is kept.
- Only people the admin has linked can send commands, and only if they hold the admin-chosen role.

## How it works

| Part | Where | What it does |
| --- | --- | --- |
| `voice_friend.py` + `overlay.py` | friend's PC | records the clip and uploads it through the webhook; shows the small banner |
| `voice_music.py` | the admin's own PC | same, but runs the speech model locally (NVIDIA GPU) and calls the bot directly |
| `server/voice-stt` | the bot's server | Docker service: faster-whisper speech to text (`/transcribe`) |
| `voicecmd` cog | the bot | reads the commands, runs Red's Audio commands as the linked member. Lives in [red-cogs](https://github.com/fhazal/red-cogs) |
| `installer.iss` | build | the Windows installer (Inno Setup) |

## Build it yourself

```
pip install -r requirements.txt
python -m PyInstaller --noconfirm --onedir --noconsole --uac-admin --name VoiceMusicLite voice_friend.py
```

Then compile `installer.iss` with Inno Setup 6.

## License

MIT, see `LICENSE`. © 2026 BajuBesi Labs.
