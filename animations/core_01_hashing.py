"""
Generate an animated GIF for SHA-256 hashing.
Style: clean box diagrams with animated arrows and visual hash bars.
Inspired by no-magic repo GIF style — abstract, minimal text, visual.
Requires: Pillow
Output: assets/gifs/core_01_hashing.gif
"""

import hashlib
import math
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# CONFIG
# ============================================================================

W, H = 800, 550
BG = (13, 17, 23)

CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
RED = (248, 113, 113)
PURPLE = (167, 139, 250)

CYAN_BG = (18, 50, 68)
PURPLE_BG = (35, 28, 58)
YELLOW_BG = (58, 50, 14)
RED_BG = (50, 20, 20)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)

WHITE = (235, 240, 245)
DIM = (100, 110, 125)

N_FRAMES = 36
FRAME_MS = 90


def _font(size, bold=False):
    names = (["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold
             else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
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


F_TITLE = _font(26, True)
F_SUB = _font(11)
F_HEAD = _font(14, True)
F_BODY = _font(12)
F_BODY_B = _font(12, True)
F_SM = _font(10)
F_SM_B = _font(10, True)
F_MONO = _mono(12)
F_BIG = _font(20, True)


# ============================================================================
# DRAWING HELPERS
# ============================================================================

def rrect(d, box, fill, outline=None, r=12, w=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)


def txt_c(d, s, cx, cy, f, fill):
    bb = d.textbbox((0, 0), s, font=f)
    d.text((cx - (bb[2] - bb[0]) // 2, cy - (bb[3] - bb[1]) // 2), s, font=f, fill=fill)


def arrow_march(d, x0, y0, x1, y1, color, phase, dash=8, gap=5, w=2):
    """Draw a marching-ant arrow between two points."""
    ln = math.hypot(x1 - x0, y1 - y0)
    if ln == 0:
        return
    dx, dy = (x1 - x0) / ln, (y1 - y0) / ln
    pos = -phase % (dash + gap)
    while pos < ln:
        ep = min(pos + dash, ln)
        d.line([(x0 + dx * pos, y0 + dy * pos),
                (x0 + dx * ep, y0 + dy * ep)], fill=color, width=w)
        pos += dash + gap
    # Arrowhead
    a = math.atan2(y1 - y0, x1 - x0)
    for s in [-1, 1]:
        d.line([(x1, y1), (x1 - 10 * math.cos(a + s * 0.4),
                           y1 - 10 * math.sin(a + s * 0.4))], fill=color, width=w)


def draw_hash_bar(d, x, y, w, h, bits, color_1, color_0):
    """Draw a visual bar where each bit of a hash is a colored cell."""
    cell_w = w / len(bits)
    for i, b in enumerate(bits):
        cx = x + i * cell_w
        c = color_1 if b == '1' else color_0
        d.rectangle([cx, y, cx + cell_w + 0.5, y + h], fill=c)


def draw_diff_bar(d, x, y, w, h, bits_a, bits_b, same_color, diff_color, dim_color):
    """Draw a bar highlighting bit differences between two hashes."""
    cell_w = w / len(bits_a)
    for i in range(len(bits_a)):
        cx = x + i * cell_w
        if bits_a[i] != bits_b[i]:
            c = diff_color
        else:
            c = dim_color
        d.rectangle([cx, y, cx + cell_w + 0.5, y + h], fill=c)


# ============================================================================
# PRECOMPUTE HASHES
# ============================================================================

HASH_A = hashlib.sha256(b"hello").hexdigest()
HASH_B = hashlib.sha256(b"hallo").hexdigest()
BITS_A = bin(int(HASH_A, 16))[2:].zfill(256)
BITS_B = bin(int(HASH_B, 16))[2:].zfill(256)
FLIPPED = sum(a != b for a, b in zip(BITS_A, BITS_B))
PCT = FLIPPED / 256 * 100


# ============================================================================
# MAIN DRAWING
# ============================================================================

def _draw_char_cells(d, word, cx, cy, cell_w, cell_h, hi_idx, font,
                     normal_fill, hi_fill, hi_bg, box_bg, box_outline, r=6):
    """Render a word as individual character cells in a typewriter grid.

    Each letter gets its own rounded-rect cell.  The letter at hi_idx is
    drawn with a bright yellow glow background so the single-character
    difference between "hello" and "hallo" is immediately obvious without
    any separate callout or label.
    """
    gap = 4                                       # px between cells
    n = len(word)
    total_w = n * cell_w + (n - 1) * gap
    x0 = cx - total_w // 2
    for i, ch in enumerate(word):
        lx = x0 + i * (cell_w + gap)
        if i == hi_idx:
            # Outer glow -- slightly larger rect behind the cell
            pad = 3
            d.rounded_rectangle(
                (lx - pad, cy - pad, lx + cell_w + pad, cy + cell_h + pad),
                radius=r + 2, fill=hi_bg)
            # The highlighted cell itself
            d.rounded_rectangle(
                (lx, cy, lx + cell_w, cy + cell_h),
                radius=r, fill=hi_bg, outline=hi_fill, width=2)
            txt_c(d, ch, lx + cell_w // 2, cy + cell_h // 2, font, hi_fill)
        else:
            d.rounded_rectangle(
                (lx, cy, lx + cell_w, cy + cell_h),
                radius=r, fill=box_bg, outline=box_outline, width=1)
            txt_c(d, ch, lx + cell_w // 2, cy + cell_h // 2, font, normal_fill)


def draw_avalanche(d, phase, frame_idx):
    """Draw the avalanche-effect panel from y=230 to y=520.

    Design: two horizontal rows.  Each row shows the input word as
    individual character cells (typewriter grid) with the differing letter
    highlighted in bright yellow, then a marching-ant arrow leading to a
    256-bit hash/diff bar.  No separate "e -> a" callout -- the inline
    highlighting makes the one-letter difference self-evident.
    """
    ay = 230                                      # panel top
    ab = 520                                      # panel bottom

    # -- Panel background --
    rrect(d, (25, ay, W - 25, ab), PANEL, BORDER, r=14)

    # -- Title --
    txt_c(d, "Avalanche Effect", W // 2, ay + 18, F_HEAD, RED)
    txt_c(d, "change 1 letter, the entire hash changes",
          W // 2, ay + 38, F_SM, DIM)

    # -- Geometry --
    cell_w, cell_h = 28, 30                       # per-character cell size
    chars_cx = 128                                # horizontal center of cells
    bar_x = 240                                   # left edge of hash bars
    bar_w = W - 55 - bar_x                        # hash bar width (~505 px)
    bar_h = 30                                    # hash bar height
    r1y = ay + 60                                 # row 1 cell top
    row_gap = 58                                  # vertical spacing between rows
    r2y = r1y + row_gap                           # row 2 cell top

    # -- Row 1: "hello" char cells + hash bar --
    _draw_char_cells(
        d, "hello", chars_cx, r1y, cell_w, cell_h,
        hi_idx=1,                                 # highlight 'e' at index 1
        font=F_MONO,
        normal_fill=WHITE, hi_fill=YELLOW, hi_bg=YELLOW_BG,
        box_bg=DARK_BOX, box_outline=BORDER)

    # Marching-ant arrow from char cells to hash bar
    arrow_start = chars_cx + 82                   # just past last cell
    arrow_march(d, arrow_start, r1y + cell_h // 2,
                bar_x - 6, r1y + cell_h // 2, CYAN, phase)

    # Hash bar -- each of the 256 bits of SHA-256("hello") as a colored cell
    draw_hash_bar(d, bar_x, r1y, bar_w, bar_h, BITS_A,
                  color_1=CYAN, color_0=(20, 45, 58))

    # -- Row 2: "hallo" char cells + diff bar --
    _draw_char_cells(
        d, "hallo", chars_cx, r2y, cell_w, cell_h,
        hi_idx=1,                                 # highlight 'a' at index 1
        font=F_MONO,
        normal_fill=WHITE, hi_fill=YELLOW, hi_bg=YELLOW_BG,
        box_bg=DARK_BOX, box_outline=BORDER)

    arrow_march(d, arrow_start, r2y + cell_h // 2,
                bar_x - 6, r2y + cell_h // 2, RED, phase)

    # Diff bar -- red cells where bits differ, dark where they match
    draw_diff_bar(d, bar_x, r2y, bar_w, bar_h,
                  BITS_A, BITS_B,
                  same_color=(25, 48, 42),
                  diff_color=RED,
                  dim_color=(25, 32, 38))

    # -- Scanning highlight line (animates across both bars) --
    scan_x = bar_x + (frame_idx / N_FRAMES) * bar_w
    sw = 3
    for bar_y in [r1y, r2y]:
        d.rectangle([scan_x, bar_y, scan_x + sw, bar_y + bar_h],
                    fill=(255, 255, 255, 180))

    # -- Stats row --
    sy = r2y + bar_h + 18

    # Legend swatches
    d.rectangle([bar_x, sy + 2, bar_x + 10, sy + 12], fill=(25, 48, 42))
    d.text((bar_x + 14, sy), "same", font=F_SM, fill=DIM)
    d.rectangle([bar_x + 55, sy + 2, bar_x + 65, sy + 12], fill=RED)
    d.text((bar_x + 69, sy), "different", font=F_SM, fill=RED)

    # Flipped-bits badge
    stat_w = 260
    stat_x = W // 2 + 30
    rrect(d, (stat_x, sy - 4, stat_x + stat_w, sy + 20),
          YELLOW_BG, YELLOW, r=12)
    txt_c(d, f"{FLIPPED}/256 bits flipped  =  {PCT:.0f}%",
          stat_x + stat_w // 2, sy + 8, F_BODY_B, YELLOW)

    # -- Bottom insight --
    txt_c(d, "1 bit of input change  \u2192  ~50% of output bits flip",
          W // 2, ab - 18, F_BODY_B, GREEN)


def draw_frame(frame_idx):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    phase = (frame_idx / N_FRAMES) * (8 + 5)  # marching ant phase

    # ── TITLE ──
    txt_c(d, "SHA-256 Hashing", W // 2, 24, F_TITLE, WHITE)
    txt_c(d, "any data in, fixed fingerprint out", W // 2, 50, F_SUB, DIM)

    # ════════════════════════════════════════════════════════
    # FLOW DIAGRAM: Input → SHA-256 → Hash
    # ════════════════════════════════════════════════════════

    box_w, box_h = 155, 90
    arrow_gap = 60
    total = 3 * box_w + 2 * arrow_gap
    x0 = (W - total) // 2
    by = 75

    # --- Input box ---
    ix = x0
    rrect(d, (ix, by, ix + box_w, by + box_h), CYAN_BG, CYAN, r=14)
    txt_c(d, "Input", ix + box_w // 2, by + 22, F_HEAD, CYAN)
    txt_c(d, "any data", ix + box_w // 2, by + 48, F_BODY, DIM)
    txt_c(d, '"hello"', ix + box_w // 2, by + 68, F_MONO, WHITE)

    # --- Arrow 1 (animated) ---
    a1_x0 = ix + box_w + 6
    a1_x1 = ix + box_w + arrow_gap - 6
    a1_y = by + box_h // 2
    arrow_march(d, a1_x0, a1_y, a1_x1, a1_y, CYAN, phase, w=3)

    # --- SHA-256 box ---
    sx = ix + box_w + arrow_gap
    rrect(d, (sx, by, sx + box_w, by + box_h), PURPLE_BG, PURPLE, r=14)
    txt_c(d, "SHA-256", sx + box_w // 2, by + 28, F_HEAD, PURPLE)
    txt_c(d, "hash fn", sx + box_w // 2, by + 52, F_BODY, DIM)

    # --- Arrow 2 (animated) ---
    a2_x0 = sx + box_w + 6
    a2_x1 = sx + box_w + arrow_gap - 6
    arrow_march(d, a2_x0, a1_y, a2_x1, a1_y, YELLOW, phase, w=3)

    # --- Output box ---
    ox = sx + box_w + arrow_gap
    rrect(d, (ox, by, ox + box_w, by + box_h), YELLOW_BG, YELLOW, r=14)
    txt_c(d, "Hash", ox + box_w // 2, by + 22, F_HEAD, YELLOW)
    txt_c(d, "256 bits", ox + box_w // 2, by + 48, F_BODY, DIM)
    txt_c(d, "2cf24d...", ox + box_w // 2, by + 68, F_MONO, YELLOW)

    # --- Property badges below flow ---
    py = by + box_h + 16
    badges = [
        ("deterministic", GREEN),
        ("one-way", ORANGE),
        ("collision-resistant", RED),
    ]
    badge_gap = 18
    # Measure total width
    badge_widths = []
    for label, _ in badges:
        bb = d.textbbox((0, 0), label, font=F_SM_B)
        badge_widths.append(bb[2] - bb[0] + 20)
    total_bw = sum(badge_widths) + badge_gap * (len(badges) - 1)
    bx = (W - total_bw) // 2
    for (label, color), bw in zip(badges, badge_widths):
        rrect(d, (bx, py, bx + bw, py + 22), DARK_BOX, color, r=11)
        txt_c(d, label, bx + bw // 2, py + 11, F_SM_B, color)
        bx += bw + badge_gap

    draw_avalanche(d, phase, frame_idx)

    # ── FOOTER ──
    txt_c(d, "core/01_hashing.py", W // 2, H - 12, F_SM, (50, 55, 65))

    return img


def main():
    frames = [draw_frame(i) for i in range(N_FRAMES)]

    out = "assets/gifs/core_01_hashing.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=FRAME_MS, loop=0, optimize=True)
    print(f"Saved {out} ({len(frames)} frames, {W}x{H})")


if __name__ == "__main__":
    main()
