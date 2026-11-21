#!/usr/bin/env python3
"""VELMARA -- a travel poster for a place that does not exist.

Writes a 1024x1024 PNG to /output/entry.png (or $MAKEFUN_OUTPUT_DIR).
Pure Python 3 standard library only: no network, no files read, no clock,
no randomness, so two runs write byte-identical output. The picture is
drawn from code, including a stroke-drawn display face for the place
name, so it renders the same in any sandbox with no system font.

The invented place: VELMARA, a lighthouse island in a calm bay at
golden hour. One landmark -- the white lighthouse on its rock island --
warm cottage windows, a low sun over the horizon, and a calm turquoise
bay. Only the place name is set in type:
no quotes, no ratings, no other copy, as the judge's brief asks.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024
OUT = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
PATH = os.path.join(OUT, "entry.png")

buf = bytearray(W * H * 3)


def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def put(x, y, rgb, alpha=1.0):
    """Blend rgb over the pixel at (x, y)."""
    if x < 0 or x >= W or y < 0 or y >= H or alpha <= 0:
        return
    i = (y * W + x) * 3
    if alpha >= 1.0:
        buf[i] = rgb[0]
        buf[i + 1] = rgb[1]
        buf[i + 2] = rgb[2]
    else:
        buf[i] = clamp(int(buf[i] + (rgb[0] - buf[i]) * alpha))
        buf[i + 1] = clamp(int(buf[i + 1] + (rgb[1] - buf[i + 1]) * alpha))
        buf[i + 2] = clamp(int(buf[i + 2] + (rgb[2] - buf[i + 2]) * alpha))


def fill_row(y, rgb):
    i = y * W * 3
    buf[i:i + W * 3] = bytes(rgb) * W


def fill_rect(x0, y0, x1, y1, rgb, alpha=1.0):
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W, x1)
    y1 = min(H, y1)
    if alpha >= 1.0:
        row = bytes(rgb) * (x1 - x0)
        for y in range(y0, y1):
            i = (y * W + x0) * 3
            buf[i:i + (x1 - x0) * 3] = row
    else:
        for y in range(y0, y1):
            for x in range(x0, x1):
                put(x, y, rgb, alpha)


def fill_polygon(points, rgb, alpha=1.0):
    """Scanline fill of a (roughly convex) polygon."""
    ys = [p[1] for p in points]
    y0, y1 = int(max(0, min(ys))), int(min(H - 1, max(ys)))
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for k in range(n):
            x1, y1p = points[k]
            x2, y2p = points[(k + 1) % n]
            if (y1p <= y < y2p) or (y2p <= y < y1p):
                xs.append(x1 + (y - y1p) * (x2 - x1) / (y2p - y1p))
        if len(xs) < 2:
            continue
        xa, xb = int(min(xs)), int(max(xs))
        if alpha >= 1.0:
            xa = max(0, xa)
            xb = min(W, xb)
            i = (y * W + xa) * 3
            buf[i:i + (xb - xa) * 3] = bytes(rgb) * (xb - xa)
        else:
            for x in range(max(0, xa), min(W, xb)):
                put(x, y, rgb, alpha)


def disc(cx, cy, r, rgb, alpha=1.0):
    """Filled disc with a 1px soft edge."""
    x0, x1 = int(cx - r - 1), int(cx + r + 1)
    y0, y1 = int(cy - r - 1), int(cy + r + 1)
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(W, x1 + 1)):
            d = math.hypot(x - cx, y - cy)
            if d <= r - 1:
                put(x, y, rgb, alpha)
            elif d <= r + 1:
                put(x, y, rgb, alpha * (r + 1 - d) / 2.0)


def ellipse(cx, cy, rx, ry, rgb, alpha=1.0):
    x0, x1 = int(cx - rx - 1), int(cx + rx + 1)
    y0, y1 = int(cy - ry - 1), int(cy + ry + 1)
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(W, x1 + 1)):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d <= 1.0:
                a = alpha * (1.0 - 0.35 * d)
                put(x, y, rgb, a)


def thick_line(x1, y1, x2, y2, width, rgb, alpha=1.0):
    """A thick line with round caps, soft 1px edge, via distance to segment."""
    hw = width / 2.0
    x0 = int(min(x1, x2) - hw - 2)
    x1b = int(max(x1, x2) + hw + 2)
    y0 = int(min(y1, y2) - hw - 2)
    y1b = int(max(y1, y2) + hw + 2)
    dx, dy = x2 - x1, y2 - y1
    seg = dx * dx + dy * dy or 1.0
    for y in range(max(0, y0), min(H, y1b + 1)):
        for x in range(max(0, x0), min(W, x1b + 1)):
            t = ((x - x1) * dx + (y - y1) * dy) / seg
            t = 0.0 if t < 0 else 1.0 if t > 1 else t
            px, py = x1 + t * dx, y1 + t * dy
            d = math.hypot(x - px, y - py)
            if d <= hw - 0.5:
                put(x, y, rgb, alpha)
            elif d <= hw + 0.5:
                put(x, y, rgb, alpha * (hw + 0.5 - d))


# ---------------------------------------------------------------- sky & sea
SKY = [(0, (26, 34, 88)), (240, (82, 62, 128)), (420, (186, 96, 112)),
       (540, (246, 158, 100)), (580, (255, 198, 132))]
SEA = [(580, (18, 96, 108)), (760, (13, 68, 90)), (1024, (7, 38, 58))]


def gradient_row(y, stops):
    for k in range(len(stops) - 1):
        y0, c0 = stops[k]
        y1, c1 = stops[k + 1]
        if y0 <= y <= y1:
            return lerp(c0, c1, (y - y0) / max(1, y1 - y0))
    return stops[-1][1]


for y in range(0, 580):
    fill_row(y, gradient_row(y, SKY))
for y in range(580, H):
    fill_row(y, gradient_row(y, SEA))

# Horizon line: a thin warm band where sky meets sea.
fill_rect(0, 578, W, 582, (255, 214, 150))

# ---------------------------------------------------------------- sun & glow
SUN = (772, 478)
for y in range(SUN[1] - 250, SUN[1] + 251):
    for x in range(SUN[0] - 250, SUN[0] + 251):
        d = math.hypot(x - SUN[0], y - SUN[1])
        if d < 250:
            a = 0.34 * (1.0 - d / 250.0) ** 2
            put(x, y, (255, 176, 96), a)
disc(SUN[0], SUN[1], 66, (255, 224, 148))
disc(SUN[0], SUN[1], 52, (255, 238, 182))

# Sun path on the sea: one soft continuous column under the sun.
for y in range(584, 920):
    width = 26 + (y - 584) * 0.10
    fade = 0.16 * (1.0 - (y - 584) / 360.0)
    fill_rect(int(SUN[0] - width), y, int(SUN[0] + width), y + 1,
              (255, 198, 122), fade)

# ---------------------------------------------------------------- clouds
CLOUDS = [
    (210, 300, 150, 13, (238, 150, 140), 0.20),
    (860, 316, 160, 14, (244, 160, 138), 0.20),
    (380, 392, 130, 10, (250, 170, 130), 0.18),
    (920, 168, 140, 12, (255, 190, 160), 0.16),
]
for cx, cy, rx, ry, c, a in CLOUDS:
    ellipse(cx, cy, rx, ry, c, a)

# ---------------------------------------------------------------- island
# Main rock: a tall basalt island rising from the bay, flat-based
# so it sits in the water instead of floating above it.
ISLAND = [(428, 452), (596, 452), (628, 560), (656, 660), (636, 760),
          (600, 800), (424, 800), (388, 730), (376, 620), (398, 542)]
fill_polygon(ISLAND, (30, 46, 62))
# Lit face on the left side of the rock.
fill_polygon([(428, 452), (512, 452), (522, 560), (506, 700), (480, 800),
              (424, 800), (388, 730), (376, 620), (398, 542)], (46, 68, 86))
# Warm rim light along the right cliff edge.
thick_line(596, 452, 628, 560, 5, (255, 178, 120), 0.85)
thick_line(628, 560, 656, 660, 5, (255, 178, 120), 0.7)
thick_line(656, 660, 636, 760, 4, (255, 170, 110), 0.5)
# Rock ledges.
thick_line(400, 560, 470, 552, 4, (18, 30, 42), 0.8)
thick_line(560, 620, 632, 612, 4, (18, 30, 42), 0.8)
thick_line(420, 690, 520, 682, 4, (18, 30, 42), 0.7)
# Waterline foam where the rock meets the bay.
ellipse(512, 801, 105, 8, (226, 242, 246), 0.30)
ellipse(512, 812, 130, 7, (18, 96, 108), 0.25)

# Warm windows: one small terrace of cottages on the rock, in a row.
WINDOWS = [(446, 578), (478, 578), (510, 578), (542, 612), (574, 612)]
for wx, wy in WINDOWS:
    fill_rect(wx, wy, wx + 9, wy + 12, (255, 205, 110))
    fill_rect(wx + 2, wy + 2, wx + 7, wy + 5, (255, 232, 160))

# ---------------------------------------------------------------- lighthouse
# Tower: white with coral bands, standing on the island's plateau.
fill_polygon([(490, 452), (534, 452), (526, 300), (498, 300)], (247, 239, 224))
fill_polygon([(492, 402), (532, 402), (530, 372), (494, 372)], (217, 95, 75))
fill_polygon([(496, 336), (528, 336), (526, 312), (498, 312)], (217, 95, 75))
# Gallery and lantern room.
fill_rect(488, 292, 536, 302, (34, 44, 58))
fill_rect(496, 262, 528, 292, (52, 62, 78))
fill_rect(502, 268, 522, 288, (255, 210, 122))
disc(512, 278, 9, (255, 226, 150))
# Dome.
fill_polygon([(494, 262), (530, 262), (512, 244)], (217, 95, 75))
disc(512, 244, 4, (255, 210, 122))
# A faint glow around the lantern; no long beams, they read as smudges.
disc(512, 278, 34, (255, 220, 140), 0.22)

# ---------------------------------------------------------------- foreground
# Dark headlands framing the bay at the bottom corners, kept low.
fill_polygon([(0, 1024), (0, 962), (150, 978), (300, 1000), (340, 1024)],
             (10, 26, 36))
fill_polygon([(1024, 1024), (1024, 952), (892, 972), (742, 998), (700, 1024)],
             (10, 26, 36))
# A small rowing boat with a lantern, left of the sun path.
fill_polygon([(280, 880), (340, 880), (328, 896), (292, 896)], (16, 32, 44))
thick_line(310, 880, 310, 852, 3, (16, 32, 44))
disc(310, 846, 6, (255, 205, 110))
disc(310, 846, 12, (255, 205, 110), 0.25)

# ---------------------------------------------------------------- birds
for bx, by, s in [(280, 300, 11), (340, 268, 9), (700, 300, 10),
                  (240, 340, 8), (740, 340, 8)]:
    thick_line(bx - s, by, bx, by - 7, 3, (40, 44, 66), 0.9)
    thick_line(bx, by - 7, bx + s, by, 3, (40, 44, 66), 0.9)

# ---------------------------------------------------------------- the name
# Stroke display face, one glyph = segments in a 100 x 140 box.
# Only the letters of VELMARA are needed; all are straight strokes.
GLYPHS = {
    "V": [((8, 0), (50, 140)), ((92, 0), (50, 140))],
    "E": [((12, 0), (12, 140)), ((12, 0), (88, 0)), ((12, 70), (72, 70)),
          ((12, 140), (88, 140))],
    "L": [((12, 0), (12, 140)), ((12, 140), (88, 140))],
    "M": [((8, 140), (8, 0)), ((8, 0), (50, 70)), ((92, 0), (50, 70)),
          ((92, 0), (92, 140))],
    "A": [((50, 0), (8, 140)), ((50, 0), (92, 140)), ((28, 95), (72, 95))],
    "R": [((12, 0), (12, 140)), ((12, 0), (70, 0)), ((70, 0), (88, 18)),
          ((88, 18), (88, 45)), ((88, 45), (70, 65)), ((70, 65), (12, 65)),
          ((58, 65), (92, 140))],
}
CREAM = (255, 246, 220)
SHADOW = (22, 26, 62)


def draw_name(text, x0, y0, scale, width, colour, alpha=1.0):
    step = 100 * scale + 18
    for gi, ch in enumerate(text):
        ox = x0 + gi * step
        for (ax, ay), (bx, by) in GLYPHS[ch]:
            thick_line(ox + int(ax * scale), y0 + int(ay * scale),
                       ox + int(bx * scale), y0 + int(by * scale),
                       width, colour, alpha)


NAME = "VELMARA"
SCALE = 0.84
# Total width: 7 glyphs of 84px + 6 gaps of 18px = 696px, centred.
draw_name(NAME, 164 + 5, 68 + 6, SCALE, 15, SHADOW, 0.45)
draw_name(NAME, 164, 68, SCALE, 15, CREAM)

# A thin rule and diamond under the name, a classic poster ornament.
thick_line(312, 216, 478, 216, 3, CREAM, 0.9)
thick_line(546, 216, 712, 216, 3, CREAM, 0.9)
fill_polygon([(512, 204), (524, 216), (512, 228), (500, 216)], CREAM)

# ---------------------------------------------------------------- frame
fill_rect(20, 20, W - 20, 28, CREAM, 0.95)
fill_rect(20, H - 28, W - 20, H - 20, CREAM, 0.95)
fill_rect(20, 20, 28, H - 20, CREAM, 0.95)
fill_rect(W - 28, 20, W - 20, H - 20, CREAM, 0.95)

# ---------------------------------------------------------------- write PNG
os.makedirs(OUT, exist_ok=True)
raw = bytearray()
for y in range(H):
    raw.append(0)  # filter: none
    raw += buf[y * W * 3:(y + 1) * W * 3]
compressed = zlib.compress(bytes(raw), 9)


def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


png = b"\x89PNG\r\n\x1a\n"
png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
png += chunk(b"IDAT", compressed)
png += chunk(b"IEND", b"")
with open(PATH, "wb") as f:
    f.write(png)
print(f"wrote {PATH}: {len(png)} bytes, {W}x{H}")
