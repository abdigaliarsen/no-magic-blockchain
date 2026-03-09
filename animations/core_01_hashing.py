"""
Generate a ByteByteGo-style infographic GIF for SHA-256 hashing.
Single layout, everything visible at once, with animated marching-ant arrows.
Requires: Pillow
Output: assets/gifs/core_01_hashing.gif
"""

import hashlib
import math
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# CONFIGURATION
# ============================================================================

W, H = 1100, 680
BG = (13, 17, 23)

# Color palette (ByteByteGo-inspired)
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
PINK = (244, 114, 182)
RED = (248, 113, 113)
PURPLE = (167, 139, 250)
BLUE = (96, 165, 250)

# Box fills (semi-transparent feel via darker versions)
CYAN_BG = (20, 60, 80)
GREEN_BG = (15, 55, 45)
YELLOW_BG = (65, 55, 15)
PURPLE_BG = (40, 30, 65)
ORANGE_BG = (65, 40, 18)
RED_BG = (70, 25, 25)

TEXT = (230, 235, 240)
TEXT_DIM = (120, 130, 145)
TEXT_DARK = (180, 185, 195)
GRID_SAME = (30, 55, 50)
GRID_FLIP = (220, 60, 40)

N_ANIM_FRAMES = 24  # frames for one full arrow cycle
FRAME_MS = 100


def font(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def font_regular(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def font_bold(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


F_TITLE = font_bold(28)
F_SECTION = font_bold(16)
F_BODY = font_regular(14)
F_MONO = font(14)
F_MONO_SM = font(11)
F_MONO_LG = font(16)
F_SMALL = font_regular(11)
F_LABEL = font_bold(12)


# ============================================================================
# DRAWING PRIMITIVES
# ============================================================================

def rrect(draw, box, fill, outline=None, r=10):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=2)


def txt(draw, text, x, y, f=F_BODY, fill=TEXT, anchor="lt"):
    draw.text((x, y), text, font=f, fill=fill, anchor=anchor)


def txt_c(draw, text, cx, cy, f=F_BODY, fill=TEXT):
    bb = draw.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((cx - tw // 2, cy - th // 2), text, font=f, fill=fill)


def marching_arrow(draw, pts, color, phase, dash=8, gap=6, width=2, head=True):
    """Draw a dashed arrow along a polyline with animated phase offset."""
    # Flatten to segments
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        length = math.hypot(x1 - x0, y1 - y0)
        if length == 0:
            continue
        dx, dy = (x1 - x0) / length, (y1 - y0) / length
        pos = -phase % (dash + gap)
        while pos < length:
            sx = x0 + dx * pos
            sy = y0 + dy * pos
            end_pos = min(pos + dash, length)
            ex = x0 + dx * end_pos
            ey = y0 + dy * end_pos
            if pos + dash > 0:
                draw.line([(sx, sy), (ex, ey)], fill=color, width=width)
            pos += dash + gap

    # Arrowhead at last point
    if head and len(pts) >= 2:
        x0, y0 = pts[-2]
        x1, y1 = pts[-1]
        angle = math.atan2(y1 - y0, x1 - x0)
        hl = 10
        for s in [-1, 1]:
            hx = x1 - hl * math.cos(angle + s * 0.45)
            hy = y1 - hl * math.sin(angle + s * 0.45)
            draw.line([(x1, y1), (hx, hy)], fill=color, width=width)


def pill(draw, cx, cy, text_str, bg, outline, f=F_LABEL, text_color=TEXT):
    """Draw a pill/badge."""
    bb = draw.textbbox((0, 0), text_str, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pw, ph = tw + 16, th + 10
    rrect(draw, (cx - pw // 2, cy - ph // 2, cx + pw // 2, cy + ph // 2),
           bg, outline=outline, r=ph // 2)
    txt_c(draw, text_str, cx, cy, f=f, fill=text_color)


def numbered_circle(draw, x, y, num, color):
    r = 12
    draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
    txt_c(draw, str(num), x, y, f=F_LABEL, fill=(20, 20, 30))


# ============================================================================
# BUILD STATIC CONTENT
# ============================================================================

def draw_static(draw):
    """Draw all static content (everything except animated arrows)."""

    # ---- Title bar ----
    rrect(draw, (0, 0, W, 50), (20, 25, 35))
    txt(draw, "SHA-256  Hashing", 20, 10, F_TITLE, CYAN)
    txt(draw, "core/01_hashing.py", W - 220, 18, F_MONO, TEXT_DIM)

    # ==== TOP SECTION: Hash flow ====

    # Step 1: Input
    bx, by = 30, 75
    numbered_circle(draw, bx + 15, by + 15, 1, CYAN)
    txt(draw, "Input", bx + 35, by + 6, F_SECTION, CYAN)
    rrect(draw, (bx, by + 32, bx + 155, by + 75), CYAN_BG, CYAN)
    txt_c(draw, '"hello"', bx + 77, by + 53, F_MONO_LG, TEXT)

    # Step 2: Padding
    bx2 = 230
    numbered_circle(draw, bx2 + 15, by + 15, 2, GREEN)
    txt(draw, "Pad to 512 bits", bx2 + 35, by + 6, F_SECTION, GREEN)
    rrect(draw, (bx2, by + 32, bx2 + 225, by + 95), GREEN_BG, GREEN)
    txt(draw, '"hello" + 1-bit + zeros', bx2 + 12, by + 38, F_MONO_SM, TEXT_DARK)
    txt(draw, '+ 64-bit length', bx2 + 12, by + 55, F_MONO_SM, TEXT_DARK)
    # Show the bit layout
    bar_y = by + 74
    segments = [(bx2 + 8, 80, GREEN, "msg"), (bx2 + 88, 8, YELLOW, "1"),
                (bx2 + 96, 72, TEXT_DIM, "zeros"), (bx2 + 168, 50, ORANGE, "len")]
    for sx, sw, sc, label in segments:
        draw.rectangle([sx, bar_y, sx + sw, bar_y + 12], fill=sc, outline=BG)
        if sw > 15:
            txt_c(draw, label, sx + sw // 2, bar_y + 6, F_SMALL, (20, 20, 30))

    # Step 3: Message Schedule
    bx3 = 500
    numbered_circle(draw, bx3 + 15, by + 15, 3, YELLOW)
    txt(draw, "Message Schedule", bx3 + 35, by + 6, F_SECTION, YELLOW)
    rrect(draw, (bx3, by + 32, bx3 + 200, by + 95), YELLOW_BG, YELLOW)
    txt(draw, "16 words → 64 words", bx3 + 12, by + 40, F_MONO_SM, TEXT)
    txt(draw, "σ₀, σ₁ expansion", bx3 + 12, by + 58, F_MONO_SM, TEXT_DARK)
    # Mini word grid
    for i in range(16):
        x = bx3 + 12 + i * 11
        c = YELLOW if i < 4 else (80, 70, 30)
        draw.rectangle([x, by + 78, x + 9, by + 88], fill=c, outline=BG)

    # Step 4: 64 Compression Rounds
    bx4 = 745
    numbered_circle(draw, bx4 + 15, by + 15, 4, ORANGE)
    txt(draw, "64 Rounds", bx4 + 35, by + 6, F_SECTION, ORANGE)
    rrect(draw, (bx4, by + 32, bx4 + 320, by + 95), ORANGE_BG, ORANGE)
    # Show operations
    ops = ["Ch", "Maj", "Σ₀", "Σ₁", "+", "+"]
    for i, op in enumerate(ops):
        ox = bx4 + 18 + i * 50
        pill(draw, ox + 15, by + 52, op, (100, 65, 25), ORANGE, F_LABEL)
    txt(draw, "a b c d e f g h  (8 state vars)", bx4 + 12, by + 74, F_MONO_SM, TEXT_DARK)

    # ==== MIDDLE SECTION: Output hash ====
    oy = 195
    numbered_circle(draw, 45, oy + 10, 5, PURPLE)
    txt(draw, "Output (256 bits = 64 hex chars)", 65, oy + 2, F_SECTION, PURPLE)
    h = hashlib.sha256(b"hello").hexdigest()
    rrect(draw, (30, oy + 25, W - 30, oy + 60), PURPLE_BG, PURPLE)
    txt_c(draw, h, W // 2, oy + 42, F_MONO_LG, YELLOW)

    # Properties on the right
    props_x = 620
    props = [
        ("Deterministic", "same input → same hash", CYAN),
        ("One-way", "cannot reverse to find input", GREEN),
        ("Fixed size", "always 256 bits output", YELLOW),
        ("Collision-resistant", "unique output per input", ORANGE),
    ]
    for i, (label, desc, color) in enumerate(props):
        py = oy + 72 + i * 22
        draw.rectangle([props_x, py + 3, props_x + 8, py + 11], fill=color)
        txt(draw, f"{label}: {desc}", props_x + 14, py, F_SMALL, TEXT_DARK)

    # ==== BOTTOM LEFT: Avalanche Effect ====
    ay = oy + 75
    rrect(draw, (25, ay, 590, ay + 275), (18, 22, 30), (50, 60, 75), r=12)
    txt(draw, "Avalanche Effect", 42, ay + 10, F_SECTION, PINK)
    txt(draw, "Change 1 character → ~50% of output bits flip", 42, ay + 30, F_SMALL, TEXT_DIM)

    # Two inputs
    inp_a, inp_b = "hello", "hallo"
    ha = hashlib.sha256(inp_a.encode()).hexdigest()
    hb = hashlib.sha256(inp_b.encode()).hexdigest()

    iy = ay + 55
    pill(draw, 90, iy, f'"{inp_a}"', CYAN_BG, CYAN, F_MONO)
    pill(draw, 90, iy + 35, f'"{inp_b}"', RED_BG, RED, F_MONO)
    # highlight the diff
    txt(draw, "e→a", 145, iy + 28, F_SMALL, YELLOW)

    # Hashes with colored diffs
    hx = 185
    for i, (ca, cb) in enumerate(zip(ha, hb)):
        x = hx + i * 8.8
        draw.text((x, iy - 8), ca, font=F_MONO_SM, fill=CYAN)
        c = RED if ca != cb else (50, 60, 50)
        draw.text((x, iy + 28), cb, font=F_MONO_SM, fill=c)

    # Bit comparison grid (256 bits, 32x8)
    bits_a = bin(int(ha, 16))[2:].zfill(256)
    bits_b = bin(int(hb, 16))[2:].zfill(256)
    flipped = sum(a != b for a, b in zip(bits_a, bits_b))

    gy = iy + 62
    txt(draw, "256-bit comparison:", 42, gy, F_SMALL, TEXT_DIM)
    cell = 7
    gap = 1
    gx0 = 42
    for row in range(8):
        for col in range(64):
            idx = row * 64 + col
            if idx >= 256:
                break
            same = bits_a[idx] == bits_b[idx]
            c = GRID_SAME if same else GRID_FLIP
            x = gx0 + col * (cell + gap)
            y = gy + 18 + row * (cell + gap)
            draw.rectangle([x, y, x + cell, y + cell], fill=c)

    # Legend and stats
    ly = gy + 18 + 8 * (cell + gap) + 8
    draw.rectangle([gx0, ly, gx0 + 10, ly + 10], fill=GRID_SAME)
    txt(draw, "same", gx0 + 14, ly - 1, F_SMALL, TEXT_DIM)
    draw.rectangle([gx0 + 60, ly, gx0 + 70, ly + 10], fill=GRID_FLIP)
    txt(draw, "flipped", gx0 + 74, ly - 1, F_SMALL, RED)

    pct = flipped / 256 * 100
    pill(draw, 350, ly + 5, f" {flipped}/256 bits flipped = {pct:.1f}% ", YELLOW_BG, YELLOW, F_MONO)

    # ==== BOTTOM RIGHT: SHA-256 Internals ====
    rx, ry = 605, ay
    rrect(draw, (rx, ry, W - 25, ry + 275), (18, 22, 30), (50, 60, 75), r=12)
    txt(draw, "Inside SHA-256", rx + 17, ry + 10, F_SECTION, CYAN)

    # Compression round diagram
    dy = ry + 38
    state_vars = list("abcdefgh")
    for i, v in enumerate(state_vars):
        vx = rx + 30 + i * 55
        rrect(draw, (vx, dy, vx + 40, dy + 28), CYAN_BG, CYAN, r=6)
        txt_c(draw, v, vx + 20, dy + 14, F_MONO_LG, TEXT)

    # Round operations box
    rop_y = dy + 45
    rrect(draw, (rx + 15, rop_y, W - 40, rop_y + 55), ORANGE_BG, ORANGE, r=8)
    txt(draw, "Each round:", rx + 25, rop_y + 5, F_SMALL, TEXT_DIM)
    txt(draw, "T₁ = Σ₁(e) + Ch(e,f,g) + h + K[i] + W[i]", rx + 25, rop_y + 20, F_MONO_SM, TEXT)
    txt(draw, "T₂ = Σ₀(a) + Maj(a,b,c)", rx + 25, rop_y + 36, F_MONO_SM, TEXT)

    # Constants
    kc_y = rop_y + 68
    txt(draw, "Constants", rx + 17, kc_y, F_LABEL, GREEN)
    txt(draw, "K[0..63] = fractional parts of", rx + 17, kc_y + 18, F_SMALL, TEXT_DIM)
    txt(draw, "cube roots of first 64 primes", rx + 17, kc_y + 33, F_SMALL, TEXT_DIM)

    txt(draw, "Initial Hash", rx + 260, kc_y, F_LABEL, YELLOW)
    txt(draw, "H[0..7] = fractional parts of", rx + 260, kc_y + 18, F_SMALL, TEXT_DIM)
    txt(draw, "square roots of first 8 primes", rx + 260, kc_y + 33, F_SMALL, TEXT_DIM)

    # Final note
    fn_y = kc_y + 62
    rrect(draw, (rx + 15, fn_y, W - 40, fn_y + 48), (25, 35, 25), GREEN, r=8)
    txt(draw, "After all 64 rounds, add compressed", rx + 25, fn_y + 5, F_SMALL, GREEN)
    txt(draw, "state to initial hash → 256-bit digest", rx + 25, fn_y + 22, F_SMALL, GREEN)
    txt(draw, "× repeat for each 512-bit block", rx + 25, fn_y + 38, F_SMALL, TEXT_DIM)


# ============================================================================
# ANIMATED ARROWS
# ============================================================================

def draw_arrows(draw, phase):
    """Draw all animated arrows for the given phase."""
    by = 75

    # Arrow 1→2: Input to Padding
    marching_arrow(draw, [(185, by + 53), (228, by + 53)], CYAN, phase)

    # Arrow 2→3: Padding to Message Schedule
    marching_arrow(draw, [(455, by + 63), (498, by + 63)], GREEN, phase)

    # Arrow 3→4: Message Schedule to Compression
    marching_arrow(draw, [(700, by + 63), (743, by + 63)], YELLOW, phase)

    # Arrow 4→5: Compression to Output
    oy = 195
    marching_arrow(draw, [(905, by + 95), (905, oy + 42), (W - 30, oy + 42)],
                   ORANGE, phase, head=False)
    marching_arrow(draw, [(745, by + 95), (745, oy + 42), (W - 30, oy + 42)],
                   ORANGE, phase, head=False)
    # Main down arrow to output
    mid_x = W // 2
    marching_arrow(draw, [(mid_x, by + 95), (mid_x, oy + 25)], PURPLE, phase)


# ============================================================================
# MAIN
# ============================================================================

def main():
    frames = []
    for i in range(N_ANIM_FRAMES):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        draw_static(draw)
        phase = (i / N_ANIM_FRAMES) * 14  # one full dash+gap cycle
        draw_arrows(draw, phase)
        frames.append(img)

    out = "assets/gifs/core_01_hashing.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=True,
    )
    print(f"Saved {out} ({len(frames)} frames, {W}x{H})")


if __name__ == "__main__":
    main()
