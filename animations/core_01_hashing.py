"""
Generate a ByteByteGo-style infographic GIF for SHA-256 hashing.
Focus: intuitive understanding, not internals. Anyone should get it.
Requires: Pillow
Output: assets/gifs/core_01_hashing.gif
"""

import hashlib
import math
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# CONFIG
# ============================================================================

W, H = 1000, 660
BG = (13, 17, 23)

# Colors
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
PINK = (244, 114, 182)
RED = (248, 113, 113)
PURPLE = (167, 139, 250)

CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
YELLOW_BG = (58, 50, 14)
RED_BG = (65, 22, 22)
PURPLE_BG = (35, 28, 58)
DARK_BOX = (22, 27, 35)

TEXT = (230, 235, 240)
TEXT_DIM = (110, 120, 135)

N_FRAMES = 20
FRAME_MS = 120


def _try_font(size, bold=False):
    if bold:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
    else:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _mono(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


F_TITLE = _try_font(30, bold=True)
F_SUBTITLE = _try_font(14)
F_HEAD = _try_font(20, bold=True)
F_BODY = _try_font(14)
F_BODY_B = _try_font(14, bold=True)
F_SMALL = _try_font(11)
F_SMALL_B = _try_font(11, bold=True)
F_MONO = _mono(13)
F_MONO_LG = _mono(15)
F_MONO_SM = _mono(11)
F_MONO_XS = _mono(10)
F_BIG = _try_font(22, bold=True)
F_HASH_SYM = _mono(28)


# ============================================================================
# DRAWING HELPERS
# ============================================================================

def rrect(d, box, fill, outline=None, r=10, w=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)


def txt_c(d, s, cx, cy, f=F_BODY, fill=TEXT):
    bb = d.textbbox((0, 0), s, font=f)
    d.text((cx - (bb[2] - bb[0]) // 2, cy - (bb[3] - bb[1]) // 2), s, font=f, fill=fill)


def char_width(d, f):
    """Get the width of a single character in a monospace font."""
    bb = d.textbbox((0, 0), "0", font=f)
    return bb[2] - bb[0]


def circle(d, cx, cy, r, fill, outline=None):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline)


def arrow_march(d, pts, color, phase, dash=8, gap=5, w=2):
    """Animated dashed polyline with arrowhead."""
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln == 0:
            continue
        dx, dy = (x1 - x0) / ln, (y1 - y0) / ln
        pos = -phase % (dash + gap)
        while pos < ln:
            sx = x0 + dx * pos
            sy = y0 + dy * pos
            ep = min(pos + dash, ln)
            d.line([(sx, sy), (x0 + dx * ep, y0 + dy * ep)], fill=color, width=w)
            pos += dash + gap
    # Arrowhead
    x0, y0 = pts[-2]
    x1, y1 = pts[-1]
    ang = math.atan2(y1 - y0, x1 - x0)
    for s in [-1, 1]:
        d.line([(x1, y1), (x1 - 12 * math.cos(ang + s * 0.4),
                           y1 - 12 * math.sin(ang + s * 0.4))], fill=color, width=w)


def solid_arrow(d, x0, y0, x1, y1, color, w=2):
    d.line([(x0, y0), (x1, y1)], fill=color, width=w)
    ang = math.atan2(y1 - y0, x1 - x0)
    for s in [-1, 1]:
        d.line([(x1, y1), (x1 - 10 * math.cos(ang + s * 0.4),
                           y1 - 10 * math.sin(ang + s * 0.4))], fill=color, width=w)


# ============================================================================
# THE INFOGRAPHIC
# ============================================================================

def draw_static(d):
    # ── Title ──
    txt_c(d, "SHA-256  Hashing", W // 2, 28, F_TITLE, CYAN)
    txt_c(d, "A hash function is a digital fingerprint machine", W // 2, 58, F_SUBTITLE, TEXT_DIM)

    # ════════════════════════════════════════════════════════
    # LEFT HALF: "What is hashing?" — the big picture
    # ════════════════════════════════════════════════════════

    lx = 30
    mid = W // 2 - 15

    # ── Section: Any Input → Fixed Output ──
    sy = 88
    d.text((lx, sy), "Any input", font=F_HEAD, fill=GREEN)
    solid_arrow(d, lx + 145, sy + 12, lx + 175, sy + 12, GREEN)
    d.text((lx + 182, sy), "Fixed-size output", font=F_HEAD, fill=YELLOW)

    # Show 3 examples
    examples = [
        ('"hi"', "8f14e45f"),
        ('"hello world"', "b94d27b9"),
        ('(entire book)', "9f86d081"),
    ]
    ty = sy + 35
    for inp, out in examples:
        # Input pill
        rrect(d, (lx, ty, lx + 170, ty + 30), CYAN_BG, CYAN, r=8)
        txt_c(d, inp, lx + 85, ty + 15, F_MONO, TEXT)
        # Arrow in
        solid_arrow(d, lx + 178, ty + 15, lx + 210, ty + 15, (70, 80, 95))
        # SHA-256 box (spans all 3 rows, drawn once)
        if inp == '"hi"':
            rrect(d, (lx + 215, ty - 5, lx + 315, ty + 85), PURPLE_BG, PURPLE, r=10)
            txt_c(d, "SHA-256", lx + 265, ty + 20, F_BODY_B, PURPLE)
            txt_c(d, "#", lx + 265, ty + 52, F_HASH_SYM, PURPLE)
        # Arrow out
        solid_arrow(d, lx + 323, ty + 15, lx + 350, ty + 15, (70, 80, 95))
        # Output pill — light text on dark yellow bg
        rrect(d, (lx + 355, ty, lx + 475, ty + 30), YELLOW_BG, YELLOW, r=8)
        txt_c(d, out + "...", lx + 415, ty + 15, F_MONO, YELLOW)
        ty += 34

    # Key insight
    ty += 12
    rrect(d, (lx, ty, mid, ty + 30), (25, 40, 30), GREEN, r=8)
    txt_c(d, "Always 64 hex characters out, no matter the input size",
          (lx + mid) // 2, ty + 15, F_SMALL_B, GREEN)

    # ════════════════════════════════════════════════════════
    # RIGHT HALF: Three key properties
    # ════════════════════════════════════════════════════════

    rx = mid + 30
    rw = W - 30
    py = 88

    d.text((rx, py), "Three Key Properties", font=F_HEAD, fill=ORANGE)
    py += 32

    props = [
        ("1", GREEN, "Deterministic", "Same input always gives same output"),
        ("2", PINK, "One-way", "Cannot reverse the hash to find input"),
        ("3", YELLOW, "Collision-resistant", "Different inputs give different outputs"),
    ]
    for num, color, title, desc in props:
        rrect(d, (rx, py, rw, py + 52), DARK_BOX, (50, 60, 75), r=8)
        circle(d, rx + 18, py + 26, 12, color)
        txt_c(d, num, rx + 18, py + 26, F_BODY_B, (20, 20, 20))
        d.text((rx + 38, py + 8), title, font=F_BODY_B, fill=color)
        d.text((rx + 38, py + 28), desc, font=F_SMALL, fill=TEXT_DIM)
        py += 60

    # ════════════════════════════════════════════════════════
    # BOTTOM: Avalanche Effect — the hero visual
    # ════════════════════════════════════════════════════════

    ay = 320
    rrect(d, (25, ay, W - 25, H - 15), (18, 22, 30), (50, 60, 75), r=12)

    # Title
    d.text((45, ay + 12), "Avalanche Effect", font=F_HEAD, fill=RED)
    d.text((250, ay + 16), "-- change 1 letter, the hash changes completely",
           font=F_BODY, fill=TEXT_DIM)

    # ── Two rows: original and modified ──
    row_y = ay + 52

    # Measure char width for proper spacing
    cw = char_width(d, F_MONO_XS)

    # Truncate hashes to fit (show first 32 chars + "...")
    ha_full = hashlib.sha256(b"hello").hexdigest()
    hb_full = hashlib.sha256(b"hallo").hexdigest()
    show_chars = 40
    ha = ha_full[:show_chars]
    hb = hb_full[:show_chars]

    hash_x = 210  # where hash text starts

    # Row 1: "hello"
    rrect(d, (45, row_y, 155, row_y + 36), CYAN_BG, CYAN, r=8)
    txt_c(d, '"hello"', 100, row_y + 18, F_MONO_LG, TEXT)
    d.text((hash_x, row_y + 5), ha + "...", font=F_MONO_XS, fill=CYAN)
    d.text((hash_x, row_y + 20), "hash of \"hello\"", font=F_SMALL, fill=TEXT_DIM)

    # Row 2: "hallo"
    row_y2 = row_y + 52
    rrect(d, (45, row_y2, 155, row_y2 + 36), RED_BG, RED, r=8)
    txt_c(d, '"hallo"', 100, row_y2 + 18, F_MONO_LG, TEXT)

    # Color each hex char: red if different, dim green if same
    for i in range(show_chars):
        ca, cb = ha_full[i], hb_full[i]
        x = hash_x + i * cw
        color = RED if ca != cb else (50, 70, 55)
        d.text((x, row_y2 + 5), cb, font=F_MONO_XS, fill=color)
    d.text((hash_x + show_chars * cw + 2, row_y2 + 5), "...", font=F_MONO_XS, fill=RED)
    d.text((hash_x, row_y2 + 20), "hash of \"hallo\" — red = changed", font=F_SMALL, fill=TEXT_DIM)

    # "just 1 letter" callout — between the two input pills
    callout_x = 162
    callout_y = row_y + 36
    d.text((callout_x, callout_y), "e -> a", font=F_SMALL_B, fill=YELLOW)
    d.text((callout_x, callout_y + 14), "just 1", font=F_SMALL_B, fill=YELLOW)
    d.text((callout_x, callout_y + 26), "letter!", font=F_SMALL_B, fill=YELLOW)

    # ── Bit grid: visual impact ──
    bits_a = bin(int(ha_full, 16))[2:].zfill(256)
    bits_b = bin(int(hb_full, 16))[2:].zfill(256)
    flipped = sum(a != b for a, b in zip(bits_a, bits_b))

    gy = row_y2 + 50
    d.text((45, gy), "Bit-by-bit comparison (256 bits):", font=F_SMALL_B, fill=TEXT_DIM)

    cell, gap = 8, 1
    gx0 = 45
    gy0 = gy + 18
    for row in range(4):
        for col in range(64):
            idx = row * 64 + col
            if idx >= 256:
                break
            same = bits_a[idx] == bits_b[idx]
            c = (25, 50, 45) if same else RED
            x = gx0 + col * (cell + gap)
            y = gy0 + row * (cell + gap)
            d.rectangle([x, y, x + cell, y + cell], fill=c)

    # Legend
    badge_y = gy0 + 4 * (cell + gap) + 10
    pct = flipped / 256 * 100

    d.rectangle([gx0, badge_y + 2, gx0 + 10, badge_y + 12], fill=(25, 50, 45))
    d.text((gx0 + 14, badge_y), "= same", font=F_SMALL, fill=TEXT_DIM)
    d.rectangle([gx0 + 75, badge_y + 2, gx0 + 85, badge_y + 12], fill=RED)
    d.text((gx0 + 89, badge_y), "= different", font=F_SMALL, fill=RED)

    # Big stat badge
    rrect(d, (280, badge_y - 6, 620, badge_y + 26), YELLOW_BG, YELLOW, r=14)
    txt_c(d, f"{flipped} / 256 bits changed  =  {pct:.0f}%", 450, badge_y + 10, F_BODY_B, YELLOW)

    # ── Bottom-right: Why it matters ──
    wx = 640
    wy = row_y - 5
    rrect(d, (wx, wy, W - 40, H - 30), (22, 28, 22), GREEN, r=10)
    d.text((wx + 14, wy + 10), "Why it matters", font=F_BODY_B, fill=GREEN)

    uses = [
        ("Tamper detection", "(any change is obvious)"),
        ("Password storage", "(store hash, not password)"),
        ("Blockchain", "(blocks linked by hashes)"),
        ("Digital signatures", "(sign hash, not full doc)"),
    ]
    uy = wy + 35
    for title, desc in uses:
        circle(d, wx + 22, uy + 7, 4, GREEN)
        d.text((wx + 32, uy - 2), title, font=F_SMALL_B, fill=GREEN)
        d.text((wx + 32, uy + 13), desc, font=F_SMALL, fill=TEXT_DIM)
        uy += 35

    # Footer
    txt_c(d, "core/01_hashing.py", W // 2, H - 8, F_SMALL, (60, 65, 75))


def draw_arrows(d, phase):
    """Animated marching arrows."""
    ay = 320
    row_y = ay + 52
    row_y2 = row_y + 52

    # Animated arrows from input pills to hash text
    arrow_march(d, [(155, row_y + 18), (205, row_y + 18)], CYAN, phase)
    arrow_march(d, [(155, row_y2 + 18), (205, row_y2 + 18)], RED, phase)


# ============================================================================
# MAIN
# ============================================================================

def main():
    frames = []
    for i in range(N_FRAMES):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        draw_static(d)
        phase = (i / N_FRAMES) * 13
        draw_arrows(d, phase)
        frames.append(img)

    out = "assets/gifs/core_01_hashing.gif"
    frames[0].save(
        out, save_all=True, append_images=frames[1:],
        duration=FRAME_MS, loop=0, optimize=True,
    )
    print(f"Saved {out} ({len(frames)} frames, {W}x{H})")


if __name__ == "__main__":
    main()
