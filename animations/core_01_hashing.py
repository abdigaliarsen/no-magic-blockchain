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

W, H = 800, 510
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

    # ════════════════════════════════════════════════════════
    # AVALANCHE SECTION — the visual core
    # ════════════════════════════════════════════════════════

    ay = 220
    panel_bottom = H - 30
    rrect(d, (25, ay, W - 25, panel_bottom), PANEL, BORDER, r=14)

    txt_c(d, "Avalanche Effect", W // 2, ay + 18, F_HEAD, RED)
    txt_c(d, "change 1 letter, the entire hash changes", W // 2, ay + 38, F_SM, DIM)

    # --- Row 1: "hello" with hash bar ---
    inp_x, inp_w = 70, 100
    bar_x = 220
    bar_w = W - 50 - bar_x
    bar_h = 30
    r1y = ay + 58
    row_gap = 55

    rrect(d, (inp_x, r1y, inp_x + inp_w, r1y + bar_h), CYAN_BG, CYAN, r=8)
    txt_c(d, '"hello"', inp_x + inp_w // 2, r1y + bar_h // 2, F_MONO, WHITE)

    # Arrow
    arrow_march(d, inp_x + inp_w + 4, r1y + bar_h // 2,
                bar_x - 4, r1y + bar_h // 2, CYAN, phase)

    # Hash visualized as color bar
    draw_hash_bar(d, bar_x, r1y, bar_w, bar_h, BITS_A,
                  color_1=CYAN, color_0=(20, 45, 58))

    # --- Row 2: "hallo" with diff bar ---
    r2y = r1y + row_gap

    rrect(d, (inp_x, r2y, inp_x + inp_w, r2y + bar_h), RED_BG, RED, r=8)
    txt_c(d, '"hallo"', inp_x + inp_w // 2, r2y + bar_h // 2, F_MONO, WHITE)

    arrow_march(d, inp_x + inp_w + 4, r2y + bar_h // 2,
                bar_x - 4, r2y + bar_h // 2, RED, phase)

    # Show differences: red = changed bit, dark = same
    draw_diff_bar(d, bar_x, r2y, bar_w, bar_h,
                  BITS_A, BITS_B,
                  same_color=(25, 48, 42),
                  diff_color=RED,
                  dim_color=(25, 32, 38))

    # --- Scanning highlight line (animated) ---
    scan_x = bar_x + (frame_idx / N_FRAMES) * bar_w
    sw = 3
    for bar_y in [r1y, r2y]:
        d.rectangle([scan_x, bar_y, scan_x + sw, bar_y + bar_h],
                    fill=(255, 255, 255, 180))

    # --- Vertical connector + "e → a" label on the left ---
    # Small vertical arrow from hello box bottom to hallo box top
    conn_x = inp_x + inp_w // 2
    d.line([(conn_x, r1y + bar_h + 2), (conn_x, r2y - 2)], fill=YELLOW, width=2)
    # Arrowhead pointing down
    for s in [-1, 1]:
        d.line([(conn_x, r2y - 2),
                (conn_x + s * 5, r2y - 9)], fill=YELLOW, width=2)
    # Label to the right of the arrow
    label_x = conn_x + 12
    label_y = (r1y + bar_h + r2y) // 2
    d.text((label_x, label_y - 6), "e \u2192 a", font=F_SM_B, fill=YELLOW)

    # --- Stats row ---
    sy = r2y + bar_h + 16

    # Left: legend
    d.rectangle([bar_x, sy + 2, bar_x + 10, sy + 12], fill=(25, 48, 42))
    d.text((bar_x + 14, sy), "same", font=F_SM, fill=DIM)
    d.rectangle([bar_x + 55, sy + 2, bar_x + 65, sy + 12], fill=RED)
    d.text((bar_x + 69, sy), "different", font=F_SM, fill=RED)

    # Center: stat badge
    stat_w = 260
    stat_x = W // 2 + 30
    rrect(d, (stat_x, sy - 4, stat_x + stat_w, sy + 20), YELLOW_BG, YELLOW, r=12)
    txt_c(d, f"{FLIPPED}/256 bits flipped  =  {PCT:.0f}%",
          stat_x + stat_w // 2, sy + 8, F_BODY_B, YELLOW)

    # --- Bottom insight ---
    iy = panel_bottom - 30
    txt_c(d, "1 bit of input change  \u2192  ~50% of output bits flip",
          W // 2, iy + 8, F_BODY_B, GREEN)

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
