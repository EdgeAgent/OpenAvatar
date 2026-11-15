# OpenAvatar — Plug-in Framework

**Status: v0 spec, written 2026-11-15.** This document defines OpenAvatar as a
*framework* — a talking-avatar call window that other apps and agent stacks plug
into — not just a demo page. It is deliberately honest about the line between
what runs today and what is specified target: anything not listed under
"Exists today" is **spec, not shipped**, and is labelled as such wherever it
appears.

Kevin's direction, verbatim intent: *"like that — I want it to be able to plug
into apps and agents"*, with *"premium framework and sticker graphics"* — the
reference being the Muse call window: a sticker-style character (black suit,
gold tie, sunglasses, laptop with a gold emblem, sitting on a cloud) inside a
tall rounded call window, a call bar at the bottom, the character animating
while it talks.

---

## The core flow — the headline loop

Everything in this framework exists to serve one loop, in Kevin's words:
*"you pick a sticker and then it kind of renders into like you — typing as
well — and working"*, and *"we either describe the sticker or give you an
image to render a new sticker."*

1. **Describe it, or give it a picture.** The user describes the character
   they want, **or** uploads an image to base a new sticker on. (Exists
   today: `POST /avatar/generate` and `POST /avatar/upload`, §2.1.)
2. **Render sticker options.** The system renders a set of sticker options
   (four in the bench's Studio flow) in the locked sticker style (§4).
3. **Pick one.** The picked sticker becomes *the* avatar — persisted,
   everywhere, immediately. (Exists today: `POST /avatar/pick`.)
4. **The sticker comes alive.** The picked sticker renders into the Call
   Window as a living character and performs the framework's one invariant
   move: **head down, working at the laptop → he stops → turns to face you
   → talks**, with expressions and gestures (nod, head-shake, head-tilt
   listening, hands). Where he is and what he's on is *not* fixed — Kevin:
   *"whatever he's sitting on — it could be standing, you could be doing
   whatever."* Pose and setting are part of what the describe/upload flow
   describes (§4, variable slot). Picking a sticker is not choosing a
   static picture; it is casting the character who then works and talks in
   the window. (The window, states, and talk loop exist today; the full
   expression set is a required asset slot set — §4 — with some slots
   still spec.)

---

## 1. The embeddable unit: the Call Window

The product surface of OpenAvatar is one component: the **Call Window**.

- **Shape.** A tall, portrait, phone-shaped window with large rounded corners.
  The avatar fills the window full-bleed — no letterboxing, no visible page
  around it. The host app supplies the backdrop; the window is the whole UI.
- **Call bar.** Pinned to the bottom of the window, three controls, exactly
  like a video call:
  - **Speaker / volume** — toggles playback of the avatar's voice.
  - **Mic / mute** — toggles the user's microphone feed to the ear.
  - **End call** (red) — ends the session and returns the avatar to idle.
- **Presence.** The avatar is a *sticker-style character* (see §4): glossy 3D
  render, die-cut presence, always the same locked identity. It is not a video
  feed and never pretends to be one.

### The transition rule (the one invariant)

**Pose and setting are flexible; the transition is not.** Kevin's
correction: *"whatever he's sitting on — it could be standing, you could be
doing whatever."* The character may be seated on the cloud (the reference),
standing, at a desk, in a garden — pose and setting are described per
sticker (§4, variable slot). What every living sticker must be able to do
is the move the reference makes:

> **working** (head down at the laptop) → **stops** → **turns to face
> you** → **talks**, with expressions and gestures.

An asset set that can't perform that transition — a character locked facing
the camera, or one that never works head-down — fails the framework, no
matter how good the still looks.

### States

The window is a state machine. These states are the framework contract; a
host app can rely on these names in events (§3). Pose/setting vary per
sticker; the state semantics don't.

| State | What the user sees | Exists today |
|---|---|---|
| `idle` | Avatar present, gentle idle motion, waiting. | ✅ Bench page (`#stage` default, "Idle. Talk to me.") |
| `working` | Head down, **typing at the laptop** — the agent is doing a task. This is the "renders into you, typing and working" beat of the core flow, and the first half of the transition. | ⚠️ Partial: the typing pose is the character's home pose in the reference art; the bench page does not yet animate a distinct typing state. |
| `listening` | **Head tilt**, attentive; halo ring shifts warm/red; the user is speaking, mic is live. | ✅ Bench page (`#stage.listening`) — signalled by the halo today; the head-tilt asset is a required slot (§4). |
| `thinking` | Subtle pulsing frame animation while the brain composes a reply. | ✅ Bench page (`#stage.thinking`) |
| `talking` | He has **stopped working and turned to face you**; mouth opens/closes driven by the live audio amplitude of the spoken reply. | ✅ Bench page (`#stage.talking`, amplitude → `--amp`) |
| `nod` | **Head nod — yes.** Agreement / acknowledgement beat, layered over idle or talking. | ❌ **Spec.** Required slot (§4); not yet an implemented state or asset. |
| `headshake` | **Head shake — no.** Kevin, explicit: *"he shakes his head and everything — he has expressions and stuff."* Disagreement / can't-do beat. | ❌ **Spec.** Required slot (§4); not yet implemented. |
| `gesturing` | **Hands gesture** (hands up off the laptop, emphasis, lean-in) layered over talking/idle. | ❌ **Spec.** The reference character gestures in the Muse call window; the bench animates face/frame only today. Gesture clips are an asset slot (§4), not yet an implemented state. |

State transitions today are driven by the bench page's own flow
(record → `/hear` → `/talk` → playback). In the target interface (§2.2) the
same transitions are driven by protocol events so a host agent can move the
avatar without a browser round-trip per turn — including firing `nod` /
`headshake` as direct answers to a yes/no moment in the conversation.

---

## 2. The API surface

### 2.1 v0 plugin API — the bench's actual HTTP endpoints (exists today)

This is the real, running API of `server.py` (loopback, port 8899 by default,
`BENCH_PORT` to change). Anything can drive the avatar today with these calls —
a script, an n8n workflow, another agent. No cloud calls anywhere in the chain:
ears, brain, and mouth are all local.

**`GET /health`** — engine report.
Returns JSON: ears (`faster-whisper/<model>`, whether the Two Ears rig path or
the identical local fallback is active), brain (`ollama/<model>`, reachable
true/false), mouth (Piper: voice, readiness, binary + model paths), studio generator note,
and the mic note (capture is browser-side; the server never captures a mic).

**`GET /state`** — current avatar selection.
Returns `{"faceUrl": "/avatar.jpg"}` or the picked `/avatars/...` URL plus
`pickedAt`. Persisted server-side in `state.json`.

**`GET /avatar.jpg`** and **`GET /avatars/<file>`** — avatar artwork.
`/avatars/` serves the studio options, uploads, and generated variants
(path-traversal guarded).

**`POST /hear`** — the ear feed.
Body: raw audio bytes (`audio/wav`, `webm`, `mp3`, `ogg`, `m4a`).
Returns `{"text": "<transcript>", "stt_ms": <int>}`.
Transcription is faster-whisper, imported from the Two Ears rig
(`~/workspace/two-ears-one-mouth/rig/hear.py`) so there is exactly one
recognizer configuration; if the rig is not importable the bench falls back to
the identical local config and `/health` says which path is active.

**`POST /talk`** — say something, get a spoken reply.
Body: `{"text": "..."}`. The mouth is Piper (`en_US-lessac-medium`).
Returns:
```json
{
  "reply": "spoken-style reply text",
  "audioBase64": "<base64 WAV of the reply>",
  "llm_ms": 0, "tts_ms": 0,
  "tts_engine": "piper", "tts_voice": "en_US-lessac-medium"
}
```
The brain is a local Ollama chat (`qwen2.5:0.5b` by default) with a spoken-style
persona and a short rolling history — replies are one to three spoken
sentences, no markdown. Error contract: `400` bad input / unknown engine,
`502` with `code` `BRAIN_FAILED` / `TTS_FAILED`, `503` with code
`TTS_UNAVAILABLE` (the composed `reply` is still included so a host can show
the text even when no voice is available).

**Avatar Studio endpoints** — the swap-the-avatar flow as an API:

- **`POST /avatar/generate`** — body `{"description": "..."}` → returns
  `{"engine", "realImageModel", "note", "gen_ms", "options": [{"id", "url", "label"}]}`.
  Honest label: today's engine is `stand-in-composer` (`realImageModel:
  false`) — a PIL keyword-scene composer over the house art. A production
  image model plugs into this exact slot and response shape.
- **`POST /avatar/upload`** — body: raw image bytes (`image/png|jpeg|webp|gif`)
  → returns one option: the user's own picture, as-is (`realImageModel: true`,
  no generator involved).
- **`POST /avatar/pick`** — body `{"url": "/avatars/..."}` → persists the pick
  to `state.json` and returns the new state. This is the moment a chosen
  option *becomes* the avatar, everywhere, immediately.

### 2.2 Target interface — realtime channel (spec, not shipped)

Turn-by-turn HTTP is fine for a bench; a real call needs a stream. The target
is a **WebSocket realtime channel aligned with the OpenAI Realtime protocol —
the same protocol Hugging Face's `speech-to-speech` project speaks**
(Apache-2.0; VAD → STT → LLM → TTS as swappable stages, exposed over an
OpenAI-Realtime-compatible WebSocket). Aligning with that protocol is the
whole point: any agent stack that can drive OpenAI Realtime or HF
speech-to-speech can drive OpenAvatar, and OpenAvatar can sit in front of
either backend without a custom protocol of its own.

Target shape (spec):

- `ws://<host>/v1/realtime` — one socket per call session.
- Client → server: streamed user audio frames; `avatar.say` (text for the
  avatar to speak verbatim); `avatar.set_state` (`listening` / `thinking` /
  `gesturing`…); `avatar.pick` (same payload as `POST /avatar/pick`);
  session config (voice engine + voice, avatar URL).
- Server → client: streamed avatar audio frames; `avatar.state` events on
  every transition; `user.transcript` (final transcript of what the user
  said); `avatar.spoke` (the exact text spoken); `avatar.speech_started` /
  `avatar.speech_finished`.
- The v0 HTTP endpoints remain as the control plane (health, studio,
  state) — the socket is the media plane. Nothing in v0 is thrown away.

**Not implemented:** the WebSocket server, audio streaming, and the event
bus do not exist in the bench today. Section 3's WebSocket sketch is a sketch.

### 2.3 The character cast — ready-made faces (exists today)

Beyond generating one-off options, the bench carries a **cast**: finished
characters a user can put on the call in one click, from the Studio's Cast
row. The cast is data, not code:

- **`GET /cast`** — lists every image file in `characters/`, merged with the
  optional `characters/cast.json` metadata (`name`, `label`, `blurb`, and
  the mouth-overlay position `mx`/`my` measured off the portrait by eye).
- **`GET /characters/<file>`** — serves a cast portrait through the same
  path-guarded static route as `/avatars/`.
- Picking a cast member uses the **same** `POST /avatar/pick` + `/state`
  mechanism as every other face — `/characters/...` URLs are accepted
  alongside `/avatar.jpg` and `/avatars/...`. Nothing about the talk path
  changes; the cast member is simply the face on the call.

**The cast today:** **Nova** (the strategist — dark curly hair, deep teal
blazer, star-emblem laptop, mid-speech on her cloud), **Bolt** (the robot —
matte clay dome and antenna, grey-cream panels, tablet in both hands,
standing), and **Professor** (the mentor — grey beard, round glasses, brown
cardigan, headphones on, typing on his book-emblem laptop). Pip remains the
default face (`/avatar.jpg`).

**Adding a character — the on-the-fly flow:** describe the character → Pip
generates the portrait in the house style (below) and eye-QCs it → the file
drops into `characters/` (plus an optional `cast.json` entry for its label,
blurb, and mouth position) → it appears in `GET /cast` and the Studio's
Cast row immediately. No restart, no code change.

**Character style standard (corrected 2026-11-15, Kevin's ruling):**
character work matches the actual Muse call avatar — the references in
`docs/style-reference/` (`call-avatar-working.png`,
`call-avatar-talking.png`). That means: a **soft matte clay render** (smooth
rounded clay surfaces, gentle matte shading — *not* flat marker, no ink
outlines, no marker grain, no gloss), a **flat solid background** (plain
light by default, or a colour that fits the character or the describer's
ask), and a **flexible pose and setting** — the cloud is optional (one
reference has it, one doesn't); sitting or standing, working or talking.
This supersedes the flat-marker direction for character portraits; the
flat-marker Pip portrait at `avatar.jpg` predates the correction and is a
separate, still-open restyle. Pip's locked identity cues stay as in the
references: sunglasses, black suit, gold tie, gold-emblem laptop,
headphones in the working pose.

---

## 3. The agent interface — how apps and agents plug in

Four integration patterns, in order of how real they are today:

1. **HTTP driver (exists today).** Any app, script, or workflow tool
   (n8n, Make, a Hermes worker, a shell script) can run a full conversation
   turn against the v0 API: POST audio to `/hear`, POST text to `/talk`,
   play the returned WAV, swap faces via the Studio endpoints. This is the
   integration Robot Orchestra's own voice path already resembles — the
   bench's Piper invocation deliberately matches RO V2's `voice_server.py`
   call shape (binary + voice model, text on stdin, `--output_file` WAV).
2. **Embed the window (spec).** The Call Window ships as a self-contained web
   component / iframe embed: the host page drops it in, points it at an
   OpenAvatar server (or a realtime backend per §2.2), and gets the full
   call-window UI — avatar, states, call bar — without rebuilding any of it.
3. **Agent-driven avatar (spec).** An agent framework (Robot Orchestra's
   Roboto, a Hermes agent, a LangGraph/CrewAI worker) holds the realtime
   socket and *performs* through the avatar: it sends `avatar.say` text,
   receives `user.transcript` events as user turns, and sets states
   (`thinking` while it works, `gesturing` for emphasis). The avatar is the
   agent's face and voice; the agent stays the brain.
4. **Face as a service (partially exists).** The Studio flow is already an
   API (§2.1): an app can offer "describe your avatar → pick from 4 → it
   becomes your avatar" inside its own UI by calling `/avatar/generate`,
   `/avatar/upload`, `/avatar/pick` and rendering the returned options.

### Events a host can consume

| Event | Meaning | Today |
|---|---|---|
| `speaking_started` | Avatar started playing a spoken reply. | Page-internal (playback start); not yet an external event. |
| `speaking_finished` | Spoken reply finished; avatar back to idle. | Page-internal (playback end). |
| `user_said` | Final transcript of the user's turn. | Available synchronously as the `/hear` response; streaming event is spec. |
| `state_changed` | Window entered a new state (§1). | Page-internal CSS state; external event is spec. |
| `avatar_changed` | A new face was picked. | Real today: the `POST /avatar/pick` response + `GET /state`. |

### Integration sketch

Working today (v0 HTTP — this exact shape runs against the bench):

```js
// One full turn: hear the user, then talk back.
const audio = await recordMicSomehow();              // browser getUserMedia
const heard = await fetch("http://127.0.0.1:8899/hear", {
  method: "POST", headers: {"Content-Type": "audio/wav"}, body: audio
}).then(r => r.json());                               // { text, stt_ms }

const turn = await fetch("http://127.0.0.1:8899/talk", {
  method: "POST", headers: {"Content-Type": "application/json"},
  body: JSON.stringify({ text: heard.text })
}).then(r => r.json());                               // { reply, audioBase64, ... }

await playWavBase64(turn.audioBase64);                // avatar speaks

// Swap the face: describe -> options -> pick.
const opts = await fetch("http://127.0.0.1:8899/avatar/generate", {
  method: "POST", headers: {"Content-Type": "application/json"},
  body: JSON.stringify({ description: "a pirate captain on a cloud" })
}).then(r => r.json());                               // { options: [{id, url, label}] }
await fetch("http://127.0.0.1:8899/avatar/pick", {
  method: "POST", headers: {"Content-Type": "application/json"},
  body: JSON.stringify({ url: opts.options[0].url })
});
```

Target (WebSocket — **sketch only, not implemented**):

```js
// SPEC SKETCH — the §2.2 realtime channel. Does not run against the bench.
const ws = new WebSocket("ws://127.0.0.1:8899/v1/realtime");
ws.onmessage = (m) => {
  const ev = JSON.parse(m.data);
  if (ev.type === "user.transcript") agent.handleUserTurn(ev.text);
  if (ev.type === "avatar.state")     window.setState(ev.state);
};
// The agent performs through the avatar:
ws.send(JSON.stringify({ type: "avatar.say", text: "On it — give me a second." }));
ws.send(JSON.stringify({ type: "avatar.set_state", state: "thinking" }));
```

---

## 4. The graphics system — the sticker standard

The character is a **sticker**: a glossy 3D-rendered figure presented die-cut,
the way the Muse call-window character reads on screen. Every OpenAvatar
asset — in the call window, in the studio grid, in the sticker pack
(`stickers/`) — follows the same standard:

- **Die-cut presentation.** Subject cut out from its scene, carried on a bold
  **white border** (the sticker's die-cut edge, ~3–4% of image width) with a
  **soft drop shadow** under the border, on transparency. On any host
  background the character reads as one pasted-on sticker, never a rectangle
  photo.
- **Render style.** Glossy, soft-lit 3D render (clay/Pixar-adjacent), smooth
  skin and fabric shading, no photorealism, no flat vector look.
- **Locked identity — non-negotiable across every asset:**
  - Black wayfarer **sunglasses** (the hero face; scene variants with clear
    glasses exist in the bench but the sunglasses face is the canonical one).
  - **Black suit**, white shirt, **gold tie**.
  - **Black laptop with the round gold emblem** on the lid, held in front.
  - Same face, same hair, same proportions in every slot. If a generated
    asset changes any of these, it fails QC and does not ship.
- **Variable — pose and setting (explicitly NOT locked):** what he's sitting
  on, whether he's sitting or standing, and where he is are described per
  sticker — that's the point of the describe-a-sticker flow. The soft white
  **cloud** is the reference/default setting (and part of the hero sticker's
  silhouette), not an invariant. What *is* invariant across poses is the
  transition (§1): head-down working → stop → face you → talk.
- **The cloud rule (hard, Kevin 2026-11-15): he sits ON the cloud, never
  inside it.** When the cloud is the seat, it sits *below* him like a chair:
  his body is clearly above the cloud's top surface, legs over the front.
  Never sunk into it, never chilling inside the cloud mass with just the
  torso poking out. Any cloud-pose asset — still or living — that buries
  him in the cloud fails QC, however good the render is.
- **Asset slots** a host app can request (naming convention
  `avatar-<slot>`). The **living-sticker set** — expressions and gestures
  included — is a *required* part of the framework, per Kevin: *"he shakes
  his head and everything — he has expressions and stuff."* Living slots are
  pose-flexible (§1, transition rule); the semantics are what's fixed:
  | Slot | Use | Today |
  |---|---|---|
  | `idle` (neutral) | Default call-window presence. | ✅ `avatar.jpg`; die-cut sticker in `stickers/` |
  | `working` | Typing at the laptop, head down — first half of the transition. | ⚠️ The home pose in the reference art; no distinct animated asset yet. |
  | `talking` | Mouth moving, turned to face the user — second half of the transition. | ⚠️ Bench animates a mouth overlay + amplitude motion over `idle`; a distinct rendered talking asset is spec. |
  | `listening` | Head tilt, attentive. | ❌ Spec (bench signals listening via the halo ring). |
  | `thinking` | Gaze up/away, composing. | ❌ Spec (bench signals thinking via frame pulse). |
  | `nod` | Head nod — yes. **Required.** | ❌ Spec — no asset yet; do not fake one. |
  | `headshake` | Head shake — no. **Required.** | ❌ Spec — no asset yet; do not fake one. |
  | `gesture` | Hands-up / emphasis, for the `gesturing` state. **Required.** | ❌ Spec. |
  | `pose` / `setting` | **Variable slot:** sitting/standing, surface, place — set by the describe/upload flow, not locked. | ✅ Exercised today by the Studio scene variants. |
  | Scene variants | Full-bleed backdrops for the studio grid. | ✅ `avatars/avatar-{cloud,space,workshop,garden}.jpg` |

  A slot marked spec is a *requirement with no asset yet*, not an optional
  extra: a build that ships the Call Window without a plan for `nod`,
  `headshake`, and `gesture` is incomplete against this framework.

---

## 5. Premium voices, talk-back, and Robot Orchestra V2

One short section, per the product ruling (Kevin, 2026-11-15):

- **OpenAvatar (this repo) is the open framework and bench.** The Call Window,
  the v0 API, the sticker system, and the standard local voice (Piper) are the
  open layer.
- **Premium voices and full talk-back are V2-gated features of Robot
  Orchestra** — they ship inside RO's paid V2 expansion, behind its licence
  gate, not in the free app and not as part of this repo's open layer. This
  repo's mouth is Piper only; no premium engine ships in the open layer.
- No pricing or sales copy lives in this document; that belongs to the V2
  launch wiring, not the framework spec.

---

## 6. Status ledger — what exists vs what is spec

**Exists and proven today (2026-11-15):**
- The bench server and every endpoint in §2.1, on loopback, no cloud calls.
- Ears imported from the Two Ears rig (single recognizer config), with an
  identical-config local fallback that `/health` reports honestly.
- One local mouth: Piper (same invocation as RO V2's voice server).
- Local Ollama brain with spoken-style persona + rolling history.
- The bench page's Call-Window-style stage with `idle` / `listening` /
  `thinking` / `talking` states and amplitude-driven mouth animation.
- The Studio flow end-to-end (describe → 4 options → pick → persisted face),
  with the generator honestly labelled a stand-in composer.
- The character cast (§2.3): Nova, Bolt, and Professor in `characters/`,
  listed by `GET /cast`, pickable through the same pick/state flow, rendered
  in the corrected call-avatar clay style (references in
  `docs/style-reference/`). Proven live 2026-11-15: per-member picks,
  byte-identical serves, and a synthetic-ear round trip with a cast member
  active.
- Sticker pack v1 in `stickers/` — see its README for per-sticker QC and the
  cutout method used.

**Spec only — not implemented, do not rely on it:**
- The WebSocket realtime channel (§2.2) and all streaming events.
- The embeddable Call Window component / iframe package.
- The `nod`, `headshake`, and `gesturing` states, and the rendered
  `listening` / `thinking` / `nod` / `headshake` / `gesture` asset slots —
  required by the framework (§4), with no assets yet. Nothing in the
  sticker pack fakes them.
- A production image model in the Studio generator slot.
- A real-microphone proof on physical hardware: this sandbox has no audio
  device, so mic capture is **CANNOT RUN here** — first proof is on Kevin's
  Windows machine. (Browser-side capture code exists; the server never
  captures a mic by design.)

**Constraints honoured while writing this:** no bench code was changed for
this document; the framework is described around the server as it actually
runs. Nothing here has been pushed to GitHub.
