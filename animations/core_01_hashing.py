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

W, H = 1000, 620
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
F_SUBTITLE = _try_font(15)
F_HEAD = _try_font(20, bold=True)
F_BODY = _try_font(14)
F_BODY_B = _try_font(14, bold=True)
F_SMALL = _try_font(11)
F_SMALL_B = _try_font(11, bold=True)
F_MONO = _mono(13)
F_MONO_LG = _mono(15)
F_MONO_SM = _mono(11)
F_BIG = _try_font(22, bold=True)
F_HUGE = _mono(36)


# ============================================================================
# DRAWING HELPERS
# ============================================================================

def rrect(d, box, fill, outline=None, r=10, w=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)


def txt_c(d, s, cx, cy, f=F_BODY, fill=TEXT):
    bb = d.textbbox((0, 0), s, font=f)
    d.text((cx - (bb[2] - bb[0]) // 2, cy - (bb[3] - bb[1]) // 2), s, font=f, fill=fill)


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

    lx = 30  # left margin
    mid = W // 2 - 15  # divider

    # ── Section: Any Input → Fixed Output ──
    sy = 90
    d.text((lx, sy), "Any input", font=F_HEAD, fill=GREEN)
    solid_arrow(d, lx + 145, sy + 12, lx + 175, sy + 12, GREEN)
    d.text((lx + 182, sy), "Fixed-size output", font=F_HEAD, fill=YELLOW)

    # Show 3 examples in a clean table
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
        # Arrow
        solid_arrow(d, lx + 178, ty + 15, lx + 210, ty + 15, (70, 80, 95))
        # SHA-256 box (only on first row)
        if inp == '"hi"':
            rrect(d, (lx + 215, ty - 5, lx + 315, ty + 85), PURPLE_BG, PURPLE, r=10)
            txt_c(d, "SHA-256", lx + 265, ty + 25, F_BODY_B, PURPLE)
            txt_c(d, "#", lx + 265, ty + 55, F_HUGE, PURPLE)
        # Arrow out
        solid_arrow(d, lx + 323, ty + 15, lx + 350, ty + 15, (70, 80, 95))
        # Output pill
        rrect(d, (lx + 355, ty, lx + 475, ty + 30), YELLOW_BG, YELLOW, r=8)
        txt_c(d, out + "...", lx + 415, ty + 15, F_MONO, (30, 30, 20))
        ty += 34

    # ── Key insight ──
    ty += 12
    rrect(d, (lx, ty, mid, ty + 32), (25, 40, 30), GREEN, r=8)
    txt_c(d, "Always 64 hex characters out, no matter the input size",
          (lx + mid) // 2, ty + 16, F_SMALL_B, GREEN)

    # ════════════════════════════════════════════════════════
    # RIGHT HALF: Three key properties
    # ════════════════════════════════════════════════════════

    rx = mid + 30
    rw = W - 30
    py = 90

    d.text((rx, py), "Three Key Properties", font=F_HEAD, fill=ORANGE)
    py += 32

    # Property 1: Deterministic
    rrect(d, (rx, py, rw, py + 52), DARK_BOX, (50, 60, 75), r=8)
    circle(d, rx + 18, py + 26, 12, GREEN)
    txt_c(d, "1", rx + 18, py + 26, F_BODY_B, (20, 20, 20))
    d.text((rx + 38, py + 6), "Deterministic", font=F_BODY_B, fill=GREEN)
    d.text((rx + 38, py + 26), "Same input → always same output", font=F_SMALL, fill=TEXT_DIM)
    py += 60

    # Property 2: One-way
    rrect(d, (rx, py, rw, py + 52), DARK_BOX, (50, 60, 75), r=8)
    circle(d, rx + 18, py + 26, 12, PINK)
    txt_c(d, "2", rx + 18, py + 26, F_BODY_B, (20, 20, 20))
    d.text((rx + 38, py + 6), "One-way", font=F_BODY_B, fill=PINK)
    d.text((rx + 38, py + 26), "Cannot reverse hash → find input", font=F_SMALL, fill=TEXT_DIM)
    py += 60

    # Property 3: Unique
    rrect(d, (rx, py, rw, py + 52), DARK_BOX, (50, 60, 75), r=8)
    circle(d, rx + 18, py + 26, 12, YELLOW)
    txt_c(d, "3", rx + 18, py + 26, F_BODY_B, (20, 20, 20))
    d.text((rx + 38, py + 6), "Collision-resistant", font=F_BODY_B, fill=YELLOW)
    d.text((rx + 38, py + 26), "Different inputs → different outputs", font=F_SMALL, fill=TEXT_DIM)

    # ════════════════════════════════════════════════════════
    # BOTTOM: Avalanche Effect — the hero visual
    # ════════════════════════════════════════════════════════

    ay = 310
    rrect(d, (25, ay, W - 25, H - 15), (18, 22, 30), (50, 60, 75), r=12)

    # Title
    d.text((45, ay + 12), "Avalanche Effect", font=F_HEAD, fill=RED)
    d.text((250, ay + 16), "— change 1 letter, get a completely different hash", font=F_BODY, fill=TEXT_DIM)

    # Two rows: original and modified
    row_y = ay + 52

    # Row 1: "hello"
    rrect(d, (45, row_y, 170, row_y + 40), CYAN_BG, CYAN, r=8)
    txt_c(d, '"hello"', 107, row_y + 20, F_MONO_LG, TEXT)

    ha = hashlib.sha256(b"hello").hexdigest()
    d.text((250, row_y + 4), ha, font=F_MONO, fill=CYAN)
    d.text((250, row_y + 24), "← hash of \"hello\"", font=F_SMALL, fill=TEXT_DIM)

    # Row 2: "hallo" (one char different)
    row_y2 = row_y + 55
    rrect(d, (45, row_y2, 170, row_y2 + 40), RED_BG, RED, r=8)
    txt_c(d, '"hallo"', 107, row_y2 + 20, F_MONO_LG, TEXT)

    hb = hashlib.sha256(b"hallo").hexdigest()
    # Color each hex char: red if different, dim if same
    for i, (ca, cb) in enumerate(zip(ha, hb)):
        x = 250 + i * 10.2
        color = RED if ca != cb else (45, 55, 45)
        d.text((x, row_y2 + 4), cb, font=F_MONO, fill=color)
    d.text((250, row_y2 + 24), "← hash of \"hallo\" (red = changed characters)", font=F_SMALL, fill=TEXT_DIM)

    # Changed letter callout
    d.text((180, row_y + 28), "e", font=F_BODY_B, fill=CYAN)
    solid_arrow(d, 192, row_y + 45, 192, row_y2 + 5, YELLOW)
    d.text((180, row_y2 - 8), "a", font=F_BODY_B, fill=RED)
    d.text((198, row_y + 35), "just 1", font=F_SMALL, fill=YELLOW)
    d.text((198, row_y + 47), "letter!", font=F_SMALL, fill=YELLOW)

    # ── Bit grid: visual impact ──
    bits_a = bin(int(ha, 16))[2:].zfill(256)
    bits_b = bin(int(hb, 16))[2:].zfill(256)
    flipped = sum(a != b for a, b in zip(bits_a, bits_b))

    gy = row_y2 + 58
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

    # Stats badge — the punchline
    badge_y = gy0 + 4 * (cell + gap) + 12
    pct = flipped / 256 * 100

    # Legend
    d.rectangle([gx0, badge_y + 2, gx0 + 10, badge_y + 12], fill=(25, 50, 45))
    d.text((gx0 + 14, badge_y), "= same", font=F_SMALL, fill=TEXT_DIM)
    d.rectangle([gx0 + 80, badge_y + 2, gx0 + 90, badge_y + 12], fill=RED)
    d.text((gx0 + 94, badge_y), "= different", font=F_SMALL, fill=RED)

    # Big stat
    rrect(d, (320, badge_y - 8, 680, badge_y + 28), YELLOW_BG, YELLOW, r=14)
    txt_c(d, f"{flipped} / 256 bits changed  =  {pct:.0f}%", 500, badge_y + 10, F_BODY_B, YELLOW)

    # Bottom-right: Why it matters
    wx = 700
    wy = ay + 55
    rrect(d, (wx, wy, W - 40, H - 30), (25, 30, 20), GREEN, r=10)
    d.text((wx + 12, wy + 8), "Why it matters", font=F_BODY_B, fill=GREEN)
    uses = [
        "• Tamper detection",
        "  (any change is obvious)",
        "",
        "• Password storage",
        "  (store hash, not password)",
        "",
        "• Blockchain integrity",
        "  (blocks linked by hashes)",
        "",
        "• Digital signatures",
        "  (sign hash, not full doc)",
    ]
    for i, line in enumerate(uses):
        col = GREEN if line.startswith("•") else TEXT_DIM
        d.text((wx + 12, wy + 30 + i * 17), line, font=F_SMALL, fill=col)

    # Footer
    txt_c(d, "core/01_hashing.py", W // 2, H - 8, F_SMALL, (60, 65, 75))


def draw_arrows(d, phase):
    """Animated arrows: input → SHA-256 → output for each row."""
    sy = 90 + 35
    for i in range(3):
        ty = sy + i * 34
        # Arrows are already drawn as solid in static.
        # Animate the main flow arrow from SHA-256 box to output
        pass

    # Animate the big arrow between "hello" and "hallo" sections
    ay = 310
    row_y = ay + 52
    # Pulsing dotted line connecting the two hash outputs
    arrow_march(d, [(250, row_y + 40), (250, row_y + 55)], YELLOW, phase, w=1)
    # Animated arrow from inputs to hash area
    arrow_march(d, [(170, row_y + 20), (245, row_y + 20)], CYAN, phase)
    arrow_march(d, [(170, row_y + 75), (245, row_y + 75)], RED, phase)


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
