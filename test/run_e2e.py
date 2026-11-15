#!/usr/bin/env python3
"""End-to-end synthetic-ear proof for the Talking Avatar Bench.

Chain: test/question.wav (Piper-spoken) -> POST /hear (rig ears) ->
transcript -> POST /talk (Ollama brain + Piper mouth) -> test/reply.wav.
Prints a JSON summary; TEST-LOG.md is written from its output.
"""
import base64
import json
import time
import urllib.request
import wave

BASE = "http://127.0.0.1:8899"


def post(path, data, ctype):
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": ctype})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body, int((time.time() - t0) * 1000)


def wav_seconds(path):
    with wave.open(path) as w:
        return round(w.getnframes() / w.getframerate(), 2), w.getframerate()


def main():
    out = {}
    q = open("test/question.wav", "rb").read()
    q_secs, q_rate = wav_seconds("test/question.wav")
    out["question_wav"] = {"seconds": q_secs, "rate": q_rate, "bytes": len(q)}

    heard, hear_wall = post("/hear", q, "audio/wav")
    out["transcript"] = heard["text"]
    out["stt_ms_server"] = heard["stt_ms"]
    out["hear_wall_ms"] = hear_wall

    talked, talk_wall = post(
        "/talk",
        json.dumps({"text": heard["text"]}).encode("utf-8"),
        "application/json",
    )
    out["reply"] = talked["reply"]
    out["llm_ms_server"] = talked["llm_ms"]
    out["tts_ms_server"] = talked["tts_ms"]
    out["talk_wall_ms"] = talk_wall
    wav = base64.b64decode(talked["audioBase64"])
    with open("test/reply.wav", "wb") as fh:
        fh.write(wav)
    r_secs, r_rate = wav_seconds("test/reply.wav")
    out["reply_wav"] = {"seconds": r_secs, "rate": r_rate, "bytes": len(wav)}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
