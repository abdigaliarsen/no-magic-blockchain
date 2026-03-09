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

W, H = 1000, 750
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


F_TITLE = _font(28, True)
F_SUB = _font(13)
F_HEAD = _font(18, True)
F_BODY = _font(13)
F_BODY_B = _font(13, True)
F_SM = _font(11)
F_SM_B = _font(11, True)
F_MONO = _mono(12)
F_MONO_SM = _mono(9)
F_MONO_LG = _mono(14)
F_HASH = _mono(24)


def rrect(d, box, fill, outline=None, r=10, w=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)


def txt_c(d, s, cx, cy, f=F_BODY, fill=TEXT):
    bb = d.textbbox((0, 0), s, font=f)
    d.text((cx - (bb[2] - bb[0]) // 2, cy - (bb[3] - bb[1]) // 2), s, font=f, fill=fill)


def dot(d, cx, cy, r, fill):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def num_badge(d, cx, cy, num, color):
    dot(d, cx, cy, 12, color)
    txt_c(d, str(num), cx, cy, F_BODY_B, (15, 15, 20))


def arrow_solid(d, x0, y0, x1, y1, color, w=2):
    d.line([(x0, y0), (x1, y1)], fill=color, width=w)
    a = math.atan2(y1 - y0, x1 - x0)
    for s in [-1, 1]:
        d.line([(x1, y1), (x1 - 9 * math.cos(a + s * 0.4),
                           y1 - 9 * math.sin(a + s * 0.4))], fill=color, width=w)


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
        d.line([(x1, y1), (x1 - 10 * math.cos(a + s * 0.4),
                           y1 - 10 * math.sin(a + s * 0.4))], fill=color, width=w)


# ============================================================================
# INFOGRAPHIC
# ============================================================================

def draw_static(d):

    # ── TITLE ──
    txt_c(d, "SHA-256  Hashing", W // 2, 26, F_TITLE, CYAN)
    txt_c(d, "A hash function is a digital fingerprint machine", W // 2, 52, F_SUB, TEXT_DIM)

    # ════════════════════════════════════════════════════════
    # TOP-LEFT: Input → SHA-256 → Output
    # ════════════════════════════════════════════════════════

    lx, sy = 30, 80
    d.text((lx, sy), "Any input", font=F_HEAD, fill=GREEN)
    arrow_solid(d, lx + 125, sy + 10, lx + 150, sy + 10, GREEN)
    d.text((lx + 157, sy), "Fixed-size output", font=F_HEAD, fill=YELLOW)

    examples = ['"hi"', '"hello world"', '(entire book)']
    outputs = ["8f14e45f...", "b94d27b9...", "9f86d081..."]

    ty = sy + 30
    # SHA-256 box spanning all rows
    sha_x = lx + 195
    sha_w = 100
    rrect(d, (sha_x, ty - 5, sha_x + sha_w, ty + 88), PURPLE_BG, PURPLE, r=10)
    txt_c(d, "SHA-256", sha_x + sha_w // 2, ty + 22, F_BODY_B, PURPLE)
    txt_c(d, "#", sha_x + sha_w // 2, ty + 55, F_HASH, PURPLE)

    for i, (inp, out) in enumerate(zip(examples, outputs)):
        row_y = ty + i * 32
        # Input pill
        rrect(d, (lx, row_y, lx + 160, row_y + 26), CYAN_BG, CYAN, r=7)
        txt_c(d, inp, lx + 80, row_y + 13, F_MONO, TEXT)
        # Arrow to SHA
        arrow_solid(d, lx + 165, row_y + 13, sha_x, row_y + 13, (60, 70, 85))
        # Arrow from SHA
        arrow_solid(d, sha_x + sha_w, row_y + 13, sha_x + sha_w + 25, row_y + 13, (60, 70, 85))
        # Output pill
        ox = sha_x + sha_w + 30
        rrect(d, (ox, row_y, ox + 120, row_y + 26), YELLOW_BG, YELLOW, r=7)
        txt_c(d, out, ox + 60, row_y + 13, F_MONO, YELLOW)

    # Key insight
    ky = ty + 100
    rrect(d, (lx, ky, sha_x + sha_w + 155, ky + 26), GREEN_BG, GREEN, r=7)
    txt_c(d, "Always 64 hex characters, no matter the input size",
          (lx + sha_x + sha_w + 155) // 2, ky + 13, F_SM_B, GREEN)

    # ════════════════════════════════════════════════════════
    # TOP-RIGHT: Properties
    # ════════════════════════════════════════════════════════

    rx = 560
    rw = W - 30
    py = 80

    d.text((rx, py), "Key Properties", font=F_HEAD, fill=ORANGE)
    py += 28

    props = [
        ("1", GREEN, "Deterministic", "Same input always gives same output"),
        ("2", PINK, "One-way", "Cannot reverse hash to find input"),
        ("3", YELLOW, "Collision-resistant", "Different inputs give different outputs"),
    ]
    for num, color, title, desc in props:
        rrect(d, (rx, py, rw, py + 48), DARK_BOX, (45, 55, 70), r=8)
        num_badge(d, rx + 16, py + 24, num, color)
        d.text((rx + 35, py + 6), title, font=F_BODY_B, fill=color)
        d.text((rx + 35, py + 24), desc, font=F_SM, fill=TEXT_DIM)
        py += 56

    # ════════════════════════════════════════════════════════
    # MIDDLE: Avalanche Effect — full width
    # ════════════════════════════════════════════════════════

    ay = 300
    rrect(d, (25, ay, W - 25, 570), (18, 22, 30), (50, 60, 75), r=12)

    d.text((45, ay + 12), "Avalanche Effect", font=F_HEAD, fill=RED)
    d.text((230, ay + 15), "-- change 1 letter, the entire hash changes",
           font=F_BODY, fill=TEXT_DIM)

    # Row 1: "hello" → its hash (FULL WIDTH available now)
    r1y = ay + 48
    rrect(d, (45, r1y, 145, r1y + 32), CYAN_BG, CYAN, r=7)
    txt_c(d, '"hello"', 95, r1y + 16, F_MONO_LG, TEXT)

    ha = hashlib.sha256(b"hello").hexdigest()
    d.text((220, r1y + 3), ha, font=F_MONO_SM, fill=CYAN)
    d.text((220, r1y + 18), "hash of \"hello\"", font=F_SM, fill=TEXT_DIM)

    # Callout: "just 1 letter" — clearly between the two rows
    cy = r1y + 38
    rrect(d, (55, cy, 200, cy + 28), (60, 55, 15), YELLOW, r=6)
    txt_c(d, "only 1 letter changed:  e -> a", 127, cy + 14, F_SM_B, YELLOW)

    # Row 2: "hallo" → its hash (colored per char)
    r2y = cy + 36
    rrect(d, (45, r2y, 145, r2y + 32), RED_BG, RED, r=7)
    txt_c(d, '"hallo"', 95, r2y + 16, F_MONO_LG, TEXT)

    hb = hashlib.sha256(b"hallo").hexdigest()
    cw_mono = d.textbbox((0, 0), "0", font=F_MONO_SM)[2]
    for i, (ca, cb) in enumerate(zip(ha, hb)):
        clr = RED if ca != cb else (40, 60, 50)
        d.text((220 + i * cw_mono, r2y + 3), cb, font=F_MONO_SM, fill=clr)
    d.text((220, r2y + 18), "hash of \"hallo\" — red = changed hex digits",
           font=F_SM, fill=TEXT_DIM)

    # Bit grid
    bits_a = bin(int(ha, 16))[2:].zfill(256)
    bits_b = bin(int(hb, 16))[2:].zfill(256)
    flipped = sum(a != b for a, b in zip(bits_a, bits_b))
    pct = flipped / 256 * 100

    gy = r2y + 46
    d.text((45, gy), "Bit-by-bit comparison (256 bits):", font=F_SM_B, fill=TEXT_DIM)

    cell, gap = 7, 1
    gx0, gy0 = 45, gy + 16
    for row in range(4):
        for col in range(64):
            idx = row * 64 + col
            if idx >= 256: break
            same = bits_a[idx] == bits_b[idx]
            c = (25, 48, 42) if same else RED
            x = gx0 + col * (cell + gap)
            y = gy0 + row * (cell + gap)
            d.rectangle([x, y, x + cell, y + cell], fill=c)

    # Legend + big stat on same line
    ly = gy0 + 4 * (cell + gap) + 8
    d.rectangle([gx0, ly + 2, gx0 + 10, ly + 12], fill=(25, 48, 42))
    d.text((gx0 + 14, ly), "= same", font=F_SM, fill=TEXT_DIM)
    d.rectangle([gx0 + 70, ly + 2, gx0 + 80, ly + 12], fill=RED)
    d.text((gx0 + 84, ly), "= different", font=F_SM, fill=RED)

    rrect(d, (350, ly - 6, 640, ly + 22), YELLOW_BG, YELLOW, r=12)
    txt_c(d, f"{flipped} / 256 bits changed  =  {pct:.0f}%",
          495, ly + 8, F_BODY_B, YELLOW)

    # ════════════════════════════════════════════════════════
    # BOTTOM: Why it matters — horizontal strip
    # ════════════════════════════════════════════════════════

    wy = 585
    rrect(d, (25, wy, W - 25, H - 15), (20, 28, 22), GREEN, r=12)
    d.text((45, wy + 10), "Why it matters", font=F_HEAD, fill=GREEN)

    uses = [
        ("Tamper detection", "any file change is obvious"),
        ("Password storage", "store hash, not the password"),
        ("Blockchain", "blocks are linked by hashes"),
        ("Digital signatures", "sign the hash, not the full doc"),
    ]
    ux = 45
    for title, desc in uses:
        dot(d, ux + 6, wy + 48, 5, GREEN)
        d.text((ux + 16, wy + 38), title, font=F_BODY_B, fill=GREEN)
        d.text((ux + 16, wy + 56), desc, font=F_SM, fill=TEXT_DIM)
        ux += 235

    # Footer
    txt_c(d, "core/01_hashing.py", W // 2, H - 6, F_SM, (50, 55, 65))


def draw_arrows(d, phase):
    ay = 300
    r1y = ay + 48
    cy = r1y + 38
    r2y = cy + 36
    arrow_march(d, [(145, r1y + 16), (215, r1y + 16)], CYAN, phase)
    arrow_march(d, [(145, r2y + 16), (215, r2y + 16)], RED, phase)


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
