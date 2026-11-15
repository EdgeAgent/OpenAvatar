# OpenAvatar — Sticker Pack v1

Die-cut stickers of the OpenAvatar character, built from the bench's own
character art (`../avatar.jpg`, `../avatars/*.jpg`) to the graphics standard
in `../FRAMEWORK.md` §4: subject cut out, bold white die-cut border, soft
drop shadow, on transparency (RGBA PNG). Drop one into any app, page, chat,
or slide and it reads as a pasted sticker, not a photo rectangle.

## The pack

| File | Source art | Slot / use |
|---|---|---|
| `sticker-hero.png` | `avatar.jpg` | `idle` — the canonical face. Bust portrait: sunglasses, black suit, gold tie, laptop with gold emblem. |
| `sticker-garden.png` | `avatars/avatar-garden.jpg` | `working` — full pose, typing at the laptop, **sitting ON TOP of the cloud seat** (the cloud-rule exemplar). |
| `sticker-space.png` | `avatars/avatar-space.jpg` | Scene variant — canonical face + a gold scarf (wardrobe variant), laptop resting on cloud puffs. |
| `sticker-workshop.png` | `avatars/avatar-workshop.jpg` | Scene variant — canonical face in a leather apron at a workbench (costume variant), typing pose; the cutout keeps a slice of bench and the tiny potted plant. |
| `sticker-cloud.png` | `avatars/avatar-cloud.jpg` | Scene variant — see the identity flag below before using as the face of anything. |

## How apps use it

- **Call Window:** the `idle` sticker is the window's resting presence;
  state changes (listening halo, talking amplitude) animate around it.
- **Anywhere else:** plain `<img>` / image component — the transparency,
  border, and shadow are baked in, so no CSS treatment is needed or wanted.
- **Naming:** stickers map to framework slots (`sticker-<slot-or-scene>.png`)
  so a host can request assets by the §4 slot names as more are produced.

## Required slots not yet in the pack (do not fake them)

Per FRAMEWORK.md §4, the living-sticker set also requires `listening`
(head tilt), `thinking`, `nod` (yes), `headshake` (no), and `gesture`
(hands) variants. **None of those exist yet** — the source art is a set of
neutral stills, and this pack does not manufacture expressions by warping
them. They arrive when the art pipeline renders them properly.

## QC — every sticker checked by eye against the reference (2026-11-15)

Method: u2net segmentation (via onnxruntime, rembg's model) → alpha trim →
white border from the dilated silhouette → soft shadow. Checked on a
neutral slate background against the locked identity (sunglasses, black
suit, gold tie, laptop emblem, same face) and the **cloud rule: sits ON
the cloud, never inside it.**

- **sticker-hero.png — PASS.** Clean die-cut, border follows the silhouette
  including the wavy cloud-line at the bottom edge; identity exact. It is a
  bust crop, so the cloud-seat rule applies only loosely — the cloud is
  mostly below the frame line in this composition.
- **sticker-garden.png — PASS, with a noted softness.** The pose is the
  cloud rule done right: body clearly above the cloud's top surface, legs
  over the front, typing. The far-right cloud puffs are slightly soft /
  translucent at the fringe — u2net is genuinely unsure where the white
  cloud ends against the bright garden hedge, and firmer alpha curves made
  it worse (they ate the cloud and imported background). Shipped as the
  best honest version, not a perfect one.
- **sticker-space.png — PASS.** Clean cutout, canonical face; the gold
  scarf is a wardrobe addition in the source art, flagged here so nobody
  mistakes it for the standard outfit. Cloud puffs sit under the laptop,
  rule-compliant.
- **sticker-workshop.png — PASS, as a costume variant.** Clean cutout;
  apron + black shirt replace the suit jacket in the source art, and a
  slice of workbench + the potted plant ride along in the silhouette.
  No cloud in this scene, so the cloud rule doesn't apply.
- **sticker-cloud.png — TECHNICALLY CLEAN, IDENTITY FLAG.** The cutout and
  border are fine, but the *source art itself* is a different face: clear
  glasses instead of the locked sunglasses, different hair and features,
  and the character rises out of the cloud mass (the exact "inside the
  cloud" composition the cloud rule bans). This is drift in the bench's
  earlier generated art, not a cutout defect. **Do not use it as the
  canonical face** until the source is re-rendered to the locked identity
  and the on-the-cloud pose.

## Rebuilding

The builder used here: u2net ONNX run directly under onnxruntime
(rembg 2.0.87 is also installed in the bench `.venv`; its import chain was
extremely slow on this shared rig, so the shipped pack was produced with
the direct-onnxruntime path — same model, same result class). Garden's
alpha needed a firming curve (0.18→0.55 ramp); the other four used the raw
mask. Border ≈ 2.8% of subject width; shadow = blurred dilated silhouette
at 38% opacity, offset ~2% of height.
