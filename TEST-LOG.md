# Talking Avatar Bench — end-to-end test log

**Date:** 2026-11-15 (sandbox run, this machine)
**Server:** `server.py` on http://127.0.0.1:8899 (bench venv Python 3.12)
**Chain under test:** synthetic ear → ears → brain → mouth, all local.

## Setup checks

| Check | Result |
|---|---|
| `GET /health` | ears = faster-whisper/tiny **via two-ears-rig** (rig imported, not forked); brain = ollama/qwen2.5:0.5b **reachable**; mouth = piper/en_US-lessac-medium **ready** (bin: bench `.venv/bin/piper`, model: bench `voices/`) |
| `GET /` | 200 |
| `GET /avatar.jpg` | 200 |

## Round 1 — full synthetic-ear loop (`test/run_e2e.py`)

1. **Question audio** — Piper spoke the line *"Hey Pip, what can you help me
   with today?"* → `test/question.wav` (2.57 s, 22050 Hz mono, 113,196 bytes).
2. **Ears** — `POST /hear` with that WAV. Transcript, exactly as recognized:
   > "Hey, Pip! What can you help me with today?"
   
   STT time (server): **17,786 ms** — includes the one-time faster-whisper
   model load.
3. **Brain + mouth** — `POST /talk` with the transcript. Ollama reply:
   > "I'm here to assist you! Could you please tell me what specific task or
   > issue you're facing today?"
   
   Brain time: **93,902 ms** · Piper time: **18,872 ms** · total wall:
   112,787 ms.
4. **Reply audio** — `test/reply.wav` (5.26 s, 22050 Hz mono, 231,980 bytes) —
   valid WAV, non-silent duration matches the reply length.

## Round 2 — warm pass (same question WAV + one typed line)

- `POST /hear` again → identical transcript ("Hey, Pip! What can you help me
  with today?"), STT **52,596 ms** this time.
- `POST /talk` with *"In one short line, what do you do?"* → reply:
  > "I'm a personal assistant who can provide assistance, answer questions,
  > and offer advice."
  
  Brain **36,199 ms** · Piper **14,976 ms** · `test/reply2.wav` 5.17 s.

## Look upgrade — 3D-style portraits (2026-11-15, later the same day)

Kevin's direction after seeing the original flat art: *"make it a lot
better… I want it like 3D, sort of like you — like with the call."*

- **New art, generated and QC'd by eye** (each file opened and inspected;
  all five passed — dimensional 3D-render look, on-character, no
  distortions): `avatar.jpg` is now a polished 3D-style studio portrait
  (same character: sunglasses, black suit, gold tie, laptop with the gold
  emblem, cloud). Four scene portraits join it as the studio's house set:
  `avatars/avatar-cloud.jpg` (cloud desk at sunrise),
  `avatars/avatar-space.jpg` (space station, gold scarf),
  `avatars/avatar-workshop.jpg` (workshop, leather apron),
  `avatars/avatar-garden.jpg` (garden, cloud bench). The original flat
  illustration is kept as `avatar-legacy.jpg`.
- **Presentation:** the stage now wraps the portrait in a 2.5D tilt layer —
  pointer-parallax tilt, a soft glow behind the character, a grounded
  shadow beneath it that shifts against the tilt, and a deeper frame
  shadow. The amplitude-driven talk animation (head bob + mouth shadow)
  is unchanged, with the mouth position re-measured per portrait.
  **Honest label:** these are 3D-*style* generated stills with 2.5D
  presentation — not a real-time 3D model, and the bench does not claim
  one anywhere.
- **Routes verified live** after a server restart on the merged code:
  `/health` 200 (studio block present), `/state` 200,
  `/avatar.jpg` 200 (253,567 B — the new portrait), all four
  `/avatars/*.jpg` 200 at full size; studio flow exercised end-to-end
  (`/avatar/generate` → 4 options, `/avatar/pick` persisted, face reset
  to the default afterwards).

### E2E re-run after the look upgrade (`test/run_e2e.py`)

| Stage | Result |
|---|---|
| Question WAV | `test/question.wav` — 2.57 s, 22050 Hz, 113,196 B (unchanged) |
| Ears transcript | "Hey, Pip! What can you help me with today?" — exact, again |
| STT (server) | 19,326 ms (contention-dominated, as before) |
| Brain reply | "Hey! Just let me know what project or task you need help with today." |
| Brain / Piper | 29,573 ms / 11,886 ms |
| Reply WAV | `test/reply.wav` — 4.14 s, 22050 Hz, 182,828 B, valid |

**Verdict: PASS.** The look upgrade changed art and presentation only;
the ears → brain → mouth pipeline is untouched and re-proven.

## Avatar Studio — endpoint proofs (bench build agent)

Exercised against the running server, request by request:

| Call | Result |
|---|---|
| `POST /avatar/generate` `{"description":"a sharp agent in space, gold and teal, dark city night"}` | 200 — engine `stand-in-composer`, `realImageModel: false`, **4 options in 3,697 ms**: Space·Gold, City·Teal, Studio·Gold, Sunset·Teal. Two options opened and inspected by eye: genuinely different bases/scenes, clean composition. |
| `POST /avatar/upload` (a real `.webp` picture as the raw body) | 200 — option `Your upload` at `/avatars/uploads/up-*.webp`, served back as-is. The upload path is real, not a stand-in. |
| `POST /avatar/pick` (a generated option URL) | 200 — persisted; `GET /state` returned the picked URL. Face reset to `/avatar.jpg` after the test. |
| `GET /avatars/../server.py` | **404** — path traversal guard holds. |
| `POST /hear` re-run after the studio merge (same question WAV) | Exact transcript again — "Hey, Pip! What can you help me with today?" (STT 54,814 ms, contention). Talk path untouched by the studio work. |

## Packaging — GitHub repo (2026-11-15)

- Intended repo: **https://github.com/EdgeAgent/talking-avatar**
  (public, MIT — `LICENSE` in the folder).
- **BLOCKED at creation:** the GitHub connector's `create_repository`
  returned **403 "Resource not accessible by integration"** — the Muse
  GitHub App installation cannot create repositories. Verified the repo
  does not exist yet (search: 0 results; `get_file_contents`: 404).
- **Kevin's 1-minute unblock:** github.com → New repository → name
  `talking-avatar`, Public, create it empty. If the Muse GitHub App
  prompts for repository selection, include the new repo. Then the
  snapshot push is one command (text files only, per the connector's
  snapshot rules):
  `github push-files --owner EdgeAgent --repo talking-avatar --branch main --source-dir /home/hatch/workspace/talking-avatar-bench --paths-file /home/hatch/workspace/talking-avatar-paths.manifest`
  with the message "Talking Avatar Bench: ears + brain + mouth, Avatar
  Studio, 3D-style portrait set".
- Snapshot set (11 text files): `server.py`, `studio.py`, `index.html`,
  `README.md`, `TEST-LOG.md`, `LICENSE`, `.gitignore`,
  `requirements.txt`, `run.sh`, `run.bat`, `test/run_e2e.py`. Binaries
  (voice model, avatar art, test WAVs) stay local per the connector's
  UTF-8-only snapshot rule — restore steps are in the README.
- Local folder is already a git repo (`main`, remote `origin` →
  the URL above, first commit made), so it becomes the working copy the
  moment the remote exists — same pattern as two-ears-one-mouth.

Stand-in honesty, restated for the log: the generator composes keyword
scenes over the house avatar art with PIL (`studio.py`). It is **not**
an image model. The production studio swaps a real image model into
the same request/response shape; the flow Kevin tests (describe →
4 options → click → face switches → persists) is identical either way.

## Honest notes

- **Timings are contention-dominated, not representative.** This sandbox
  shares ~1.5 CPUs with several other builds/agents that were running
  concurrently; that's why a "warm" STT pass came out slower than the cold
  one. On Kevin's Windows machine (dedicated CPU/GPU-less but uncontended)
  expect dramatically faster turns; treat the numbers above as
  worst-case-under-load, and the *correctness* results (exact transcript,
  coherent spoken reply, valid reply WAV) as the proof.
- **Reply quality:** qwen2.5:0.5b follows the spoken-style format (short,
  plain sentences) but its persona is generic-assistant. The bench takes
  `BENCH_OLLAMA_MODEL` — a larger local model (e.g. llama3.1:8b, also
  installed on this machine) will sound much more like Pip, at more latency.
- **CANNOT RUN in this sandbox: real microphone capture.** There is no
  audio hardware here and the server never touches a mic by design — the
  browser does (getUserMedia). The page detects a blocked/missing mic and
  says so cleanly, offering type-to-talk and the synthetic-ear file feed
  instead. Mic capture gets its first real proof on Kevin's Windows
  machine, same as the Two Ears rig's ear 2.
- The talking animation is browser-side (WebAudio amplitude → CSS) and so
  is **not exercised by this log** — it runs when the page plays the reply.
  It was verified by code inspection, not by eye; first visual proof is
  Kevin opening the page.
