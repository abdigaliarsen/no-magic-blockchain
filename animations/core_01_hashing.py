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

W, H = 1000, 650
BG = (13, 17, 23)

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

# Max right edge for any content (generous margin from 1000px width)
MAX_X = 940


def _font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else \
            ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for n in names:
        for d in ["/usr/share/fonts/truetype/dejavu/",
                  "/usr/share/fonts/truetype/liberation/"]:
            try:
                return ImageFont.truetype(d + n, size)
            except (OSError, IOError):
                continue
    return ImageFont.load_default()


def _mono(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


F_TITLE = _font(24, True)
F_SUB = _font(12)
F_HEAD = _font(16, True)
F_BODY = _font(12)
F_BODY_B = _font(12, True)
F_SM = _font(10)
F_SM_B = _font(10, True)
F_MONO = _mono(11)
F_MONO_SM = _mono(9)
F_MONO_HASH = _mono(9)
F_HASH = _mono(20)


def rrect(d, box, fill, outline=None, r=10, w=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)


def txt_c(d, s, cx, cy, f=F_BODY, fill=TEXT):
    bb = d.textbbox((0, 0), s, font=f)
    d.text((cx - (bb[2] - bb[0]) // 2, cy - (bb[3] - bb[1]) // 2), s, font=f, fill=fill)


def dot(d, cx, cy, r, fill):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def num_badge(d, cx, cy, num, color):
    dot(d, cx, cy, 11, color)
    txt_c(d, str(num), cx, cy, F_BODY_B, (15, 15, 20))


def arrow_solid(d, x0, y0, x1, y1, color, w=2):
    d.line([(x0, y0), (x1, y1)], fill=color, width=w)
    a = math.atan2(y1 - y0, x1 - x0)
    for s in [-1, 1]:
        d.line([(x1, y1), (x1 - 8 * math.cos(a + s * 0.4),
                           y1 - 8 * math.sin(a + s * 0.4))], fill=color, width=w)


def arrow_march(d, pts, color, phase, dash=8, gap=5, w=2):
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]; x1, y1 = pts[i + 1]
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln == 0: continue
        dx, dy = (x1 - x0) / ln, (y1 - y0) / ln
        pos = -phase % (dash + gap)
        while pos < ln:
            ep = min(pos + dash, ln)
            d.line([(x0 + dx * pos, y0 + dy * pos),
                    (x0 + dx * ep, y0 + dy * ep)], fill=color, width=w)
            pos += dash + gap
    x0, y0 = pts[-2]; x1, y1 = pts[-1]
    a = math.atan2(y1 - y0, x1 - x0)
    for s in [-1, 1]:
        d.line([(x1, y1), (x1 - 9 * math.cos(a + s * 0.4),
                           y1 - 9 * math.sin(a + s * 0.4))], fill=color, width=w)


def trunc_hash(h, n=24):
    """Truncate hash to n chars + ellipsis."""
    return h[:n] + "..."


# ============================================================================
# INFOGRAPHIC
# ============================================================================

def draw_static(d):

    # ── TITLE ──
    txt_c(d, "SHA-256  Hashing", W // 2, 22, F_TITLE, CYAN)
    txt_c(d, "A hash function is a digital fingerprint machine", W // 2, 46, F_SUB, TEXT_DIM)

    # ════════════════════════════════════════════════════════
    # TOP-LEFT: Input → SHA-256 → Output  (x: 40..510)
    # ════════════════════════════════════════════════════════

    lx, sy = 40, 70
    d.text((lx, sy), "Any input", font=F_HEAD, fill=GREEN)
    arrow_solid(d, lx + 115, sy + 9, lx + 135, sy + 9, GREEN)
    d.text((lx + 142, sy), "Fixed-size output", font=F_HEAD, fill=YELLOW)

    examples = ['"hi"', '"hello world"', '(entire book)']
    outputs = ["8f14e45f...", "b94d27b9...", "9f86d081..."]

    ty = sy + 28
    # SHA-256 box spanning all rows
    sha_x = lx + 175
    sha_w = 90
    rrect(d, (sha_x, ty - 4, sha_x + sha_w, ty + 82), PURPLE_BG, PURPLE, r=10)
    txt_c(d, "SHA-256", sha_x + sha_w // 2, ty + 18, F_BODY_B, PURPLE)
    txt_c(d, "#", sha_x + sha_w // 2, ty + 48, F_HASH, PURPLE)

    for i, (inp, out) in enumerate(zip(examples, outputs)):
        row_y = ty + i * 30
        # Input pill
        rrect(d, (lx, row_y, lx + 145, row_y + 24), CYAN_BG, CYAN, r=7)
        txt_c(d, inp, lx + 72, row_y + 12, F_MONO, TEXT)
        # Arrow to SHA
        arrow_solid(d, lx + 150, row_y + 12, sha_x, row_y + 12, (60, 70, 85))
        # Arrow from SHA
        arrow_solid(d, sha_x + sha_w, row_y + 12, sha_x + sha_w + 20, row_y + 12, (60, 70, 85))
        # Output pill
        ox = sha_x + sha_w + 25
        rrect(d, (ox, row_y, ox + 110, row_y + 24), YELLOW_BG, YELLOW, r=7)
        txt_c(d, out, ox + 55, row_y + 12, F_MONO, YELLOW)

    # Key insight
    ky = ty + 94
    insight_right = sha_x + sha_w + 140
    rrect(d, (lx, ky, insight_right, ky + 22), GREEN_BG, GREEN, r=7)
    txt_c(d, "Always 64 hex characters, no matter the input size",
          (lx + insight_right) // 2, ky + 11, F_SM_B, GREEN)

    # ════════════════════════════════════════════════════════
    # TOP-RIGHT: Properties  (x: 550..960)
    # ════════════════════════════════════════════════════════

    rx = 550
    rw = MAX_X
    py = 70

    d.text((rx, py), "Key Properties", font=F_HEAD, fill=ORANGE)
    py += 26

    props = [
        ("1", GREEN, "Deterministic", "Same input always gives same output"),
        ("2", PINK, "One-way", "Cannot reverse hash to find input"),
        ("3", YELLOW, "Collision-resistant", "Different inputs give different outputs"),
    ]
    for num, color, title, desc in props:
        rrect(d, (rx, py, rw, py + 44), DARK_BOX, (45, 55, 70), r=8)
        num_badge(d, rx + 15, py + 22, num, color)
        d.text((rx + 32, py + 5), title, font=F_BODY_B, fill=color)
        d.text((rx + 32, py + 22), desc, font=F_SM, fill=TEXT_DIM)
        py += 50

    # ════════════════════════════════════════════════════════
    # MIDDLE: Avalanche Effect — full width
    # ════════════════════════════════════════════════════════

    ay = 280
    av_bottom = 540
    rrect(d, (30, ay, W - 30, av_bottom), (18, 22, 30), (50, 60, 75), r=12)

    d.text((50, ay + 10), "Avalanche Effect", font=F_HEAD, fill=RED)
    d.text((220, ay + 13), "-- change 1 letter, the entire hash changes",
           font=F_BODY, fill=TEXT_DIM)

    ha = hashlib.sha256(b"hello").hexdigest()
    hb = hashlib.sha256(b"hallo").hexdigest()
    ha_short = trunc_hash(ha)
    hb_short = trunc_hash(hb)

    # Row 1: "hello" → its truncated hash
    r1y = ay + 42
    # Input pill
    rrect(d, (50, r1y, 140, r1y + 30), CYAN_BG, CYAN, r=7)
    txt_c(d, '"hello"', 95, r1y + 15, F_MONO, TEXT)
    # Hash in a pill (truncated, safe width)
    hash_lx = 220
    hash_rx = 420
    rrect(d, (hash_lx, r1y, hash_rx, r1y + 30), CYAN_BG, (40, 80, 100), r=7)
    txt_c(d, ha_short, (hash_lx + hash_rx) // 2, r1y + 10, F_MONO_HASH, CYAN)
    d.text((hash_lx, r1y + 20), "hash of \"hello\"", font=F_SM, fill=TEXT_DIM)

    # Callout: "just 1 letter" — between the two rows, clear yellow badge
    cy = r1y + 38
    badge_w = 210
    badge_lx = 60
    rrect(d, (badge_lx, cy, badge_lx + badge_w, cy + 24), (60, 55, 15), YELLOW, r=6)
    txt_c(d, "only 1 letter changed:  e \u2192 a",
          badge_lx + badge_w // 2, cy + 12, F_SM_B, YELLOW)

    # Row 2: "hallo" → its truncated hash (colored per char to show diff)
    r2y = cy + 32
    rrect(d, (50, r2y, 140, r2y + 30), RED_BG, RED, r=7)
    txt_c(d, '"hallo"', 95, r2y + 15, F_MONO, TEXT)

    # Hash pill with per-character coloring
    rrect(d, (hash_lx, r2y, hash_rx, r2y + 30), RED_BG, (100, 40, 40), r=7)
    cw_mono = d.textbbox((0, 0), "0", font=F_MONO_HASH)[2]
    # Center the truncated hash text inside the pill
    total_text_w = len(hb_short) * cw_mono
    text_start_x = (hash_lx + hash_rx) // 2 - total_text_w // 2
    for i, ch in enumerate(hb_short):
        if i < len(ha):
            clr = RED if ha[i] != hb[i] else (40, 60, 50)
        else:
            clr = TEXT_DIM  # the "..." part
        d.text((text_start_x + i * cw_mono, r2y + 5), ch, font=F_MONO_HASH, fill=clr)
    d.text((hash_lx, r2y + 20), "hash of \"hallo\" \u2014 red = changed",
           font=F_SM, fill=TEXT_DIM)

    # Bit grid
    bits_a = bin(int(ha, 16))[2:].zfill(256)
    bits_b = bin(int(hb, 16))[2:].zfill(256)
    flipped = sum(a != b for a, b in zip(bits_a, bits_b))
    pct = flipped / 256 * 100

    gy = r2y + 42
    d.text((50, gy), "Bit-by-bit comparison (256 bits):", font=F_SM_B, fill=TEXT_DIM)

    cell, gap = 6, 1
    gx0, gy0 = 50, gy + 14
    for row in range(4):
        for col in range(64):
            idx = row * 64 + col
            if idx >= 256: break
            same = bits_a[idx] == bits_b[idx]
            c = (25, 48, 42) if same else RED
            x = gx0 + col * (cell + gap)
            y = gy0 + row * (cell + gap)
            d.rectangle([x, y, x + cell, y + cell], fill=c)

    # Legend + stat
    ly = gy0 + 4 * (cell + gap) + 6
    d.rectangle([gx0, ly + 2, gx0 + 8, ly + 10], fill=(25, 48, 42))
    d.text((gx0 + 12, ly), "= same", font=F_SM, fill=TEXT_DIM)
    d.rectangle([gx0 + 60, ly + 2, gx0 + 68, ly + 10], fill=RED)
    d.text((gx0 + 72, ly), "= different", font=F_SM, fill=RED)

    stat_lx = 340
    stat_rx = 600
    rrect(d, (stat_lx, ly - 4, stat_rx, ly + 18), YELLOW_BG, YELLOW, r=10)
    txt_c(d, f"{flipped} / 256 bits changed  =  {pct:.0f}%",
          (stat_lx + stat_rx) // 2, ly + 7, F_BODY_B, YELLOW)

    # ════════════════════════════════════════════════════════
    # BOTTOM: Why it matters — horizontal strip
    # ════════════════════════════════════════════════════════

    wy = 555
    rrect(d, (30, wy, W - 30, H - 15), (20, 28, 22), GREEN, r=12)
    d.text((50, wy + 8), "Why it matters", font=F_HEAD, fill=GREEN)

    uses = [
        ("Tamper detection", "any file change is obvious"),
        ("Password storage", "store hash, not the password"),
        ("Blockchain", "blocks are linked by hashes"),
        ("Digital signatures", "sign the hash, not the full doc"),
    ]
    col_w = (W - 100) // 4  # evenly space 4 columns
    ux = 50
    for title, desc in uses:
        dot(d, ux + 5, wy + 42, 4, GREEN)
        d.text((ux + 14, wy + 33), title, font=F_BODY_B, fill=GREEN)
        d.text((ux + 14, wy + 49), desc, font=F_SM, fill=TEXT_DIM)
        ux += col_w

    # Footer
    txt_c(d, "core/01_hashing.py", W // 2, H - 6, F_SM, (50, 55, 65))


def draw_arrows(d, phase):
    """Marching-ant arrows from input pills to hash pills in avalanche section."""
    ay = 280
    r1y = ay + 42
    cy = r1y + 38
    r2y = cy + 32
    arrow_march(d, [(140, r1y + 15), (218, r1y + 15)], CYAN, phase)
    arrow_march(d, [(140, r2y + 15), (218, r2y + 15)], RED, phase)


def main():
    frames = []
    for i in range(N_FRAMES):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        draw_static(d)
        draw_arrows(d, (i / N_FRAMES) * 13)
        frames.append(img)

    out = "assets/gifs/core_01_hashing.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=FRAME_MS, loop=0, optimize=True)
    print(f"Saved {out} ({len(frames)} frames, {W}x{H})")


if __name__ == "__main__":
    main()
