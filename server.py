#!/usr/bin/env python3
"""
Talking Avatar Bench — one small local server. Loopback only.

  GET  /         -> the bench page (index.html)
  GET  /avatar.jpg
  GET  /cast     -> the character cast: every portrait in characters/,
                    merged with characters/cast.json metadata
  GET  /characters/<file> -> a cast portrait (same serve path as avatars)
  GET  /health   -> engine report: ears / brain / mouth readiness
  POST /hear     -> raw audio bytes in (webm/wav/mp3/ogg/m4a), transcript out.
                    EARS: the Two Ears rig's hear path, imported — see below.
  POST /talk     -> JSON {"text": "..."} in; Ollama reply + spoken WAV
                    out as JSON {"reply", "audioBase64", timings,
                    "tts_engine", "tts_voice"}.

EARS reuse: this server imports load_model/transcribe_file from the Two
Ears rig (~/workspace/two-ears-one-mouth/rig/hear.py) — the rig's ONE
recognizer configuration (faster-whisper, cpu, int8). Nothing is forked;
if the rig is not importable, it falls back to the identical local config
and /health says which path is active.

MOUTH: Piper, invoked exactly the way Robot Orchestra's V2 voice
server (apps/desktop/voice-server/voice_server.py) invokes it — binary
+ voice model, text on stdin, --output_file WAV. Voice:
en_US-lessac-medium, the same default voice as the V2 server.

BRAIN: local Ollama chat, qwen2.5:0.5b, short spoken-style replies.

The server never captures a microphone. The browser does that and POSTs
the recording here. No cloud calls anywhere.
"""
import base64
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("BENCH_HOST", "127.0.0.1")
PORT = int(os.environ.get("BENCH_PORT", "8899"))
WHISPER_MODEL = os.environ.get("BENCH_WHISPER_MODEL", "tiny")
OLLAMA_URL = os.environ.get("BENCH_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("BENCH_OLLAMA_MODEL", "qwen2.5:0.5b")
TTS_VOICE = os.environ.get("BENCH_TTS_VOICE", "en_US-lessac-medium")
RIG_DIR = os.environ.get(
    "BENCH_RIG_DIR", os.path.expanduser("~/workspace/two-ears-one-mouth")
)

if HOST not in ("127.0.0.1", "localhost", "::1"):
    print("bench: refusing to bind a non-loopback host", flush=True)
    sys.exit(2)

# Temp files live inside the bench (the host /tmp can be tiny/full).
TMP_DIR = os.path.join(BENCH_DIR, ".tmp")
os.makedirs(TMP_DIR, exist_ok=True)
tempfile.tempdir = TMP_DIR

# ---------------------------------------------------------------- ears
_ear_path = "fallback"
_rig_load_model = None
_rig_transcribe_file = None
try:
    sys.path.insert(0, RIG_DIR)
    from rig.hear import load_model as _rig_load_model
    from rig.hear import transcribe_file as _rig_transcribe_file

    _ear_path = "two-ears-rig"
except Exception as exc:  # rig not importable — identical local config
    print("bench: rig hear import failed (%s); using local config" % exc, flush=True)

_model = None


def whisper_model():
    global _model
    if _model is None:
        if _rig_load_model is not None:
            _model = _rig_load_model(WHISPER_MODEL)
        else:
            from faster_whisper import WhisperModel

            _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def transcribe(path):
    if _rig_transcribe_file is not None:
        return _rig_transcribe_file(whisper_model(), path, "en")
    segments, _info = whisper_model().transcribe(path, language="en", beam_size=1)
    return " ".join(s.text.strip() for s in segments).strip()


# ---------------------------------------------------------------- mouth
def find_piper_bin():
    env = os.environ.get("BENCH_PIPER_BIN")
    if env and os.path.isfile(env):
        return env
    sibling = os.path.join(os.path.dirname(sys.executable), "piper")
    if os.path.isfile(sibling):
        return sibling
    on_path = shutil.which("piper")
    if on_path:
        return on_path
    dev = os.path.expanduser("~/workspace/.venvs/piper/bin/piper")
    if os.path.isfile(dev):
        return dev
    return None


def find_piper_model():
    env = os.environ.get("BENCH_PIPER_MODEL")
    if env and os.path.isfile(env):
        return env
    local = os.path.join(BENCH_DIR, "voices", TTS_VOICE + ".onnx")
    if os.path.isfile(local):
        return local
    # Same search spots as the RO V2 voice server.
    patterns = [
        os.path.expanduser(f"~/.local/share/piper/{TTS_VOICE}.onnx"),
        os.path.expanduser(f"~/piper-voices/{TTS_VOICE}.onnx"),
        os.path.expanduser(f"~/workspace/voices/{TTS_VOICE}.onnx"),
        os.path.expanduser(f"~/workspace/*/voices/{TTS_VOICE}.onnx"),
    ]
    for pat in patterns:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    return None


PIPER_BIN = find_piper_bin()
PIPER_MODEL = find_piper_model()


def piper_ready():
    return bool(PIPER_BIN and PIPER_MODEL)


def synthesize_wav_piper(text):
    """Piper for one utterance; returns WAV bytes. Same call shape as
    Robot Orchestra's V2 voice_server.py synthesize_wav()."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out_path = tmp.name
    try:
        proc = subprocess.run(
            [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", out_path],
            input=text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "piper exited %d: %s"
                % (proc.returncode, proc.stderr.decode("utf-8", "replace")[:300])
            )
        with open(out_path, "rb") as fh:
            return fh.read()
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


def tts_ready():
    return piper_ready()


def synthesize_wav(text):
    """Speak one utterance with Piper.
    Returns (wav_bytes, engine_used, voice_used)."""
    return synthesize_wav_piper(text), "piper", TTS_VOICE


# ---------------------------------------------------------------- brain
PERSONA = (
    "You are Pip, Kevin's personal assistant, speaking out loud through an "
    "avatar. Reply in one to three short, natural spoken sentences. No "
    "markdown, no lists, no emoji — just words a person would say. Be warm, "
    "direct, and a little wry. If you don't know something, say so plainly."
)
_history = []  # list of {"role","content"} — one bench conversation


def brain_reply(text):
    global _history
    messages = [{"role": "system", "content": PERSONA}]
    messages += _history[-6:]
    messages.append({"role": "user", "content": text})
    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 140},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL + "/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    reply = (data.get("message") or {}).get("content", "").strip()
    if not reply:
        raise RuntimeError("empty reply from Ollama")
    _history.append({"role": "user", "content": text})
    _history.append({"role": "assistant", "content": reply})
    del _history[:-12]
    return reply


def ollama_up():
    try:
        req = urllib.request.Request(OLLAMA_URL + "/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


# ---------------------------------------------------------------- studio
STATE_PATH = os.path.join(BENCH_DIR, "state.json")
AVATARS_DIR = os.path.join(BENCH_DIR, "avatars")
CHARACTERS_DIR = os.path.join(BENCH_DIR, "characters")
CAST_META_PATH = os.path.join(CHARACTERS_DIR, "cast.json")
UPLOAD_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
STATIC_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def load_state():
    try:
        with open(STATE_PATH) as fh:
            state = json.load(fh)
        if isinstance(state, dict) and state.get("faceUrl"):
            return state
    except Exception:
        pass
    return {"faceUrl": "/avatar.jpg"}


def save_state(state):
    with open(STATE_PATH, "w") as fh:
        json.dump(state, fh, indent=2)


def generate_options(description):
    import studio  # lazy: keeps the talk path free of the PIL import

    return studio.generate(description)


def list_cast():
    """The character cast: every image file in characters/, merged with
    the optional cast.json metadata (name/label/blurb/mouth position).
    Dropping a new portrait into characters/ is all it takes for it to
    appear here and in the Studio's Cast row — metadata is optional."""
    meta = {}
    try:
        with open(CAST_META_PATH) as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            meta = loaded
    except Exception:
        pass
    cast = []
    if os.path.isdir(CHARACTERS_DIR):
        for name in sorted(os.listdir(CHARACTERS_DIR)):
            if os.path.splitext(name)[1].lower() not in STATIC_TYPES:
                continue
            if not os.path.isfile(os.path.join(CHARACTERS_DIR, name)):
                continue
            info = meta.get(name) or {}
            stem = os.path.splitext(name)[0]
            cast.append(
                {
                    "id": stem,
                    "name": info.get("name") or stem.replace("-", " ").title(),
                    "url": "/characters/" + name,
                    "label": info.get("label") or stem.replace("-", " ").title(),
                    "blurb": info.get("blurb") or "",
                    "mx": info.get("mx"),
                    "my": info.get("my"),
                }
            )
    return cast


# ---------------------------------------------------------------- http
SUFFIX_BY_TYPE = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stdout.write("bench: %s\n" % (fmt % args))
        sys.stdout.flush()

    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, payload):
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length > 0 else b""

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(BENCH_DIR, "index.html"), "rb") as fh:
                self._send(200, fh.read(), "text/html; charset=utf-8")
        elif self.path == "/avatar.jpg":
            with open(os.path.join(BENCH_DIR, "avatar.jpg"), "rb") as fh:
                self._send(200, fh.read(), "image/jpeg")
        elif self.path == "/state":
            self._json(200, load_state())
        elif self.path == "/cast":
            self._json(200, {"cast": list_cast()})
        elif self.path.startswith("/avatars/"):
            self._serve_avatar_file(self.path[len("/avatars/"):])
        elif self.path.startswith("/characters/"):
            self._serve_character_file(self.path[len("/characters/"):])
        elif self.path == "/health":
            self._json(
                200,
                {
                    "ok": True,
                    "port": PORT,
                    "studio": {
                        "generator": "stand-in-composer",
                        "realImageModel": False,
                        "note": "production plugs an image model into "
                        "the same slot",
                    },
                    "ears": {
                        "engine": "faster-whisper/" + WHISPER_MODEL,
                        "path": _ear_path,
                        "rigDir": RIG_DIR,
                    },
                    "brain": {
                        "engine": "ollama/" + OLLAMA_MODEL,
                        "reachable": ollama_up(),
                    },
                    "mouth": {
                        "engine": "piper",
                        "voice": TTS_VOICE,
                        "ready": piper_ready(),
                        "bin": PIPER_BIN,
                        "model": PIPER_MODEL,
                    },
                    "mic": "browser-side (getUserMedia); the server never "
                    "captures a microphone",
                },
            )
        else:
            self._json(404, {"error": "not found"})

    def _serve_from(self, base_dir, rel):
        path = os.path.normpath(os.path.join(base_dir, rel))
        if not path.startswith(base_dir) or not os.path.isfile(path):
            return self._json(404, {"error": "not found"})
        ext = os.path.splitext(path)[1].lower()
        with open(path, "rb") as fh:
            self._send(200, fh.read(), STATIC_TYPES.get(ext, "application/octet-stream"))

    def _serve_avatar_file(self, rel):
        self._serve_from(AVATARS_DIR, rel)

    def _serve_character_file(self, rel):
        self._serve_from(CHARACTERS_DIR, rel)

    def do_POST(self):
        if self.path == "/hear":
            return self._hear()
        if self.path == "/talk":
            return self._talk()
        if self.path == "/avatar/generate":
            return self._avatar_generate()
        if self.path == "/avatar/upload":
            return self._avatar_upload()
        if self.path == "/avatar/pick":
            return self._avatar_pick()
        self._json(404, {"error": "not found"})

    def _avatar_generate(self):
        raw = self._body()
        try:
            description = str(json.loads(raw or b"{}").get("description") or "")
        except Exception:
            return self._json(400, {"error": "invalid JSON body"})
        try:
            t0 = time.time()
            result = generate_options(description)
            result["gen_ms"] = int((time.time() - t0) * 1000)
            self._json(200, result)
        except Exception as exc:
            self._json(
                502, {"error": "generator failed: %s" % exc, "code": "GEN_FAILED"}
            )

    def _avatar_upload(self):
        raw = self._body()
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        ext = UPLOAD_TYPES.get(ctype)
        if not raw:
            return self._json(400, {"error": "empty upload body"})
        if not ext:
            return self._json(
                400, {"error": "unsupported image type: %s" % (ctype or "?")}
            )
        up_dir = os.path.join(AVATARS_DIR, "uploads")
        os.makedirs(up_dir, exist_ok=True)
        name = "up-%d%s" % (int(time.time() * 1000), ext)
        with open(os.path.join(up_dir, name), "wb") as fh:
            fh.write(raw)
        url = "/avatars/uploads/" + name
        self._json(
            200,
            {
                "engine": "upload",
                "realImageModel": True,
                "note": "Your picture, as-is — no generator involved.",
                "options": [{"id": name, "url": url, "label": "Your upload"}],
            },
        )

    def _avatar_pick(self):
        raw = self._body()
        try:
            url = str(json.loads(raw or b"{}").get("url") or "")
        except Exception:
            return self._json(400, {"error": "invalid JSON body"})
        if not (
            url == "/avatar.jpg"
            or url.startswith("/avatars/")
            or url.startswith("/characters/")
        ):
            return self._json(400, {"error": "unknown avatar url"})
        state = {"faceUrl": url, "pickedAt": int(time.time())}
        save_state(state)
        self._json(200, state)

    def _hear(self):
        raw = self._body()
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        if not raw:
            return self._json(400, {"error": "empty audio body"})
        suffix = SUFFIX_BY_TYPE.get(ctype, ".wav")
        path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(raw)
                path = tmp.name
            t0 = time.time()
            text = transcribe(path)
            self._json(
                200, {"text": text, "stt_ms": int((time.time() - t0) * 1000)}
            )
        except Exception as exc:
            self._json(502, {"error": "STT failed: %s" % exc, "code": "STT_FAILED"})
        finally:
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def _talk(self):
        raw = self._body()
        try:
            payload = json.loads(raw or b"{}")
            text = str(payload.get("text") or "").strip()
        except Exception:
            return self._json(400, {"error": "invalid JSON body"})
        if not text:
            return self._json(400, {"error": "nothing to say"})
        try:
            t0 = time.time()
            reply = brain_reply(text)
            llm_ms = int((time.time() - t0) * 1000)
        except Exception as exc:
            return self._json(
                502, {"error": "brain failed: %s" % exc, "code": "BRAIN_FAILED"}
            )
        if not tts_ready():
            detail = "Piper TTS unavailable (bin: %s, model: %s)" % (
                PIPER_BIN or "not found",
                PIPER_MODEL or "not found",
            )
            return self._json(
                503,
                {"error": detail, "code": "TTS_UNAVAILABLE", "reply": reply},
            )
        try:
            t0 = time.time()
            wav, engine_used, voice_used = synthesize_wav(reply[:600])
            tts_ms = int((time.time() - t0) * 1000)
        except Exception as exc:
            return self._json(
                502,
                {"error": "TTS failed: %s" % exc, "code": "TTS_FAILED", "reply": reply},
            )
        self._json(
            200,
            {
                "reply": reply,
                "audioBase64": base64.b64encode(wav).decode("ascii"),
                "llm_ms": llm_ms,
                "tts_ms": tts_ms,
                "tts_engine": engine_used,
                "tts_voice": voice_used,
            },
        )


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(
        "bench: http://%s:%d  ears=faster-whisper/%s via %s  brain=ollama/%s "
        "up=%s  mouth=piper/%s ready=%s"
        % (
            HOST,
            PORT,
            WHISPER_MODEL,
            _ear_path,
            OLLAMA_MODEL,
            ollama_up(),
            TTS_VOICE,
            piper_ready(),
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
