#!/usr/bin/env python3
"""
Avatar Studio — the bench's STAND-IN generator.

Honesty first: this is NOT an image model. A local bench server has no
route to a real text-to-image engine, so this module composes four
genuinely different avatar options programmatically: real character
bases (the house avatar art Kevin was offered/picked on 2026-11-15)
set into keyword-driven scenes (backdrop, palette, props drawn flat in
the art's own style).

The production Avatar Studio plugs a real image model into this exact
slot: same request ({"description": str}) -> same response shape
({"options": [{"id", "url", "label"}], "engine": str}). Only the
engine changes; the flow Kevin is testing does not.

The upload path is NOT a stand-in: an uploaded picture becomes an
option as-is.
"""
import hashlib
import os
import random

from PIL import Image, ImageDraw, ImageOps

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
BASES_DIR = os.path.join(BENCH_DIR, "assets", "bases")
GEN_DIR = os.path.join(BENCH_DIR, "avatars", "generated")
SIZE = 640
FACE = 500  # character disc diameter

BASE_FILES = ["base-0.jpg", "base-1.webp", "base-2.webp", "base-3.webp", "base-4.webp"]

COLORS = {
    "gold": (232, 185, 60),
    "yellow": (232, 185, 60),
    "teal": (127, 181, 173),
    "blue": (84, 128, 196),
    "navy": (38, 54, 110),
    "purple": (146, 102, 204),
    "violet": (146, 102, 204),
    "pink": (232, 130, 178),
    "red": (208, 84, 70),
    "green": (96, 168, 96),
    "orange": (236, 148, 66),
    "cream": (239, 230, 207),
    "white": (240, 240, 235),
    "black": (18, 18, 20),
    "silver": (178, 186, 190),
    "brown": (140, 100, 66),
}

SCENE_WORDS = {
    "space": ["space", "star", "galaxy", "moon", "cosmos", "astronaut", "orbit"],
    "sunset": ["sunset", "dusk", "golden hour", "evening"],
    "beach": ["beach", "ocean", "sea", "surf", "island", "coast"],
    "city": ["city", "urban", "skyline", "downtown", "street", "new york", "toronto"],
    "forest": ["forest", "woods", "tree", "nature", "jungle", "garden"],
    "mountain": ["mountain", "alpine", "peak", "snow", "winter", "ski"],
    "neon": ["neon", "cyber", "cyberpunk", "retro", "synthwave", "vapor"],
    "studio": ["studio", "portrait", "classic", "plain", "simple", "moon"],
}


def parse_brief(description):
    text = (description or "").lower()
    colors = [name for name in COLORS if name in text]
    scenes = []
    for scene, words in SCENE_WORDS.items():
        if any(w in text for w in words):
            scenes.append(scene)
    dark = "dark" in text or "night" in text or "midnight" in text
    return colors, scenes, dark


def _gradient(size, top, bottom):
    img = Image.new("RGB", (size, size), top)
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(size):
            px[x, y] = c
    return img


def _disc(draw, cx, cy, r, fill):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def draw_scene(scene, accent, dark, rng):
    a = accent
    if scene == "space":
        img = _gradient(SIZE, (6, 10, 34), (16, 26, 62))
        d = ImageDraw.Draw(img)
        for _ in range(130):
            x, y = rng.randrange(SIZE), rng.randrange(SIZE)
            r = rng.choice([1, 1, 1, 2])
            _disc(d, x, y, r, (240, 238, 220) if rng.random() > 0.25 else a)
        _disc(d, 520, 110, 44, (239, 230, 207))
        _disc(d, 538, 96, 40, (10, 16, 44))  # crescent bite
    elif scene == "sunset":
        img = _gradient(SIZE, (64, 32, 66), (236, 148, 66))
        d = ImageDraw.Draw(img)
        _disc(d, 320, 430, 120, (250, 208, 110))
        d.rectangle([0, 470, SIZE, SIZE], fill=(38, 24, 40))
        d.rectangle([0, 462, SIZE, 470], fill=a)
    elif scene == "beach":
        img = _gradient(SIZE, (120, 190, 205), (214, 232, 220))
        d = ImageDraw.Draw(img)
        _disc(d, 110, 100, 52, (252, 224, 130))
        d.rectangle([0, 400, SIZE, SIZE], fill=(72, 150, 168))
        d.rectangle([0, 520, SIZE, SIZE], fill=(232, 214, 165))
        d.rectangle([0, 514, SIZE, 522], fill=a)
    elif scene == "city":
        img = _gradient(SIZE, (10, 30, 44) if dark else (24, 52, 70), (8, 18, 26))
        d = ImageDraw.Draw(img)
        x = 0
        while x < SIZE:
            w = rng.randrange(46, 96)
            h = rng.randrange(120, 300)
            d.rectangle([x, SIZE - h, x + w, SIZE], fill=(6, 12, 18))
            for _ in range(14):
                wx = x + rng.randrange(6, max(8, w - 10))
                wy = SIZE - h + rng.randrange(10, max(12, h - 14))
                if rng.random() > 0.45:
                    d.rectangle([wx, wy, wx + 4, wy + 6], fill=a)
            x += w + rng.randrange(2, 10)
    elif scene == "forest":
        img = _gradient(SIZE, (18, 52, 34), (10, 30, 20))
        d = ImageDraw.Draw(img)
        _disc(d, 540, 90, 40, (220, 230, 200))
        for bx in range(-20, SIZE, 74):
            h = rng.randrange(150, 260)
            d.polygon([(bx, SIZE), (bx + 44, SIZE - h), (bx + 88, SIZE)], fill=(8, 24, 14))
            d.rectangle([bx + 38, SIZE - 34, bx + 50, SIZE], fill=(30, 20, 12))
    elif scene == "mountain":
        img = _gradient(SIZE, (52, 66, 92), (24, 30, 46))
        d = ImageDraw.Draw(img)
        _disc(d, 96, 96, 42, (240, 238, 224))
        for cx, h, w in [(120, 300, 360), (360, 380, 420), (520, 260, 300)]:
            d.polygon([(cx - w // 2, SIZE), (cx, SIZE - h), (cx + w // 2, SIZE)], fill=(30, 38, 56))
            peak = SIZE - h
            d.polygon([(cx - 34, peak + 58), (cx, peak), (cx + 34, peak + 58),
                       (cx + 12, peak + 40), (cx, peak + 54), (cx - 14, peak + 40)],
                      fill=(238, 240, 244))
        d.rectangle([0, SIZE - 6, SIZE, SIZE], fill=a)
    elif scene == "neon":
        img = _gradient(SIZE, (8, 6, 18), (20, 8, 34))
        d = ImageDraw.Draw(img)
        for r, col in [(250, a), (214, (64, 224, 255)), (282, (255, 64, 178))]:
            d.ellipse([320 - r, 300 - r, 320 + r, 300 + r], outline=col, width=5)
        for y in range(500, SIZE, 22):
            d.line([0, y, SIZE, y], fill=(40, 16, 60), width=2)
    else:  # studio — the house look: cream moon on deep teal
        img = _gradient(SIZE, (13, 42, 50), (7, 24, 30))
        d = ImageDraw.Draw(img)
        _disc(d, 320, 292, 238, (239, 230, 207))
        _disc(d, 320, 292, 246, None) if False else None
        d.ellipse([320 - 246, 292 - 246, 320 + 246, 292 + 246], outline=a, width=3)
    return img


def _sketch_base(accent):
    """Fallback character base, drawn flat, for checkouts without the
    house art assets (the GitHub snapshot carries code, not binaries).
    Deliberately a simple bench sketch — the real bases are Kevin's
    avatar art in assets/bases/ when present."""
    img = Image.new("RGB", (500, 500), (244, 240, 228))
    d = ImageDraw.Draw(img)
    _disc(d, 250, 250, 218, (228, 233, 230))
    _disc(d, 250, 196, 86, (240, 205, 160))          # head
    d.rectangle([168, 168, 332, 196], fill=(24, 24, 28))  # sunglasses band
    d.rectangle([196, 300, 304, 430], fill=(30, 32, 40))  # body / suit
    d.polygon([(238, 308), (262, 308), (250, 356)], fill=accent)  # tie
    d.rectangle([120, 330, 250, 420], fill=(38, 40, 48))  # laptop
    _disc(d, 168, 366, 14, accent)                   # laptop disc
    return img


def _character_disc(base_path):
    if base_path and os.path.isfile(base_path):
        img = Image.open(base_path).convert("RGB")
    else:
        img = _sketch_base(COLORS["gold"])
    img = ImageOps.fit(img, (FACE, FACE), method=Image.LANCZOS)
    mask = Image.new("L", (FACE, FACE), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([0, 0, FACE, FACE], fill=255)
    disc = Image.new("RGBA", (FACE, FACE), (0, 0, 0, 0))
    disc.paste(img, (0, 0), mask)
    return disc


def compose(base_path, scene, accent, dark, seed):
    rng = random.Random(seed)
    canvas = draw_scene(scene, accent, dark, rng).convert("RGBA")
    disc = _character_disc(base_path)
    x, y = (SIZE - FACE) // 2, 46
    canvas.alpha_composite(disc, (x, y))
    d = ImageDraw.Draw(canvas)
    d.ellipse([x, y, x + FACE, y + FACE], outline=(239, 230, 207), width=6)
    d.ellipse([x - 9, y - 9, x + FACE + 9, y + FACE + 9], outline=accent, width=3)
    return canvas.convert("RGB")


def generate(description):
    """description -> 4 options. Same shape a real image model would fill."""
    colors, scenes, dark = parse_brief(description)
    accents = [COLORS[c] for c in colors] or [COLORS["gold"], COLORS["teal"]]
    accent_names = colors or ["gold", "teal"]
    scene_order = list(scenes)
    for s in ["studio", "space", "city", "sunset", "forest", "neon", "beach", "mountain"]:
        if s not in scene_order:
            scene_order.append(s)
    digest = hashlib.sha256((description or "house agent").lower().encode()).hexdigest()
    seed = int(digest[:8], 16)
    folder = digest[:10]
    out_dir = os.path.join(GEN_DIR, folder)
    os.makedirs(out_dir, exist_ok=True)
    bases = [os.path.join(BASES_DIR, b) for b in BASE_FILES]
    options = []
    for i in range(4):
        scene = scene_order[i % len(scene_order)]
        accent = accents[i % len(accents)]
        accent_name = accent_names[i % len(accent_names)]
        base = bases[(seed + i) % len(bases)]
        img = compose(base, scene, accent, dark, seed + i * 977)
        name = "option-%d.png" % (i + 1)
        img.save(os.path.join(out_dir, name), "PNG")
        options.append(
            {
                "id": "%s-%d" % (folder, i + 1),
                "url": "/avatars/generated/%s/%s" % (folder, name),
                "label": "Option %d — %s · %s" % (i + 1, scene.title(), accent_name.title()),
                "scene": scene,
                "accent": accent_name,
            }
        )
    return {
        "engine": "stand-in-composer",
        "realImageModel": False,
        "note": "Bench stand-in: keyword scenes composed over the house "
        "avatar art. Production plugs an image model into this slot — "
        "same request, same four-option response.",
        "options": options,
    }
