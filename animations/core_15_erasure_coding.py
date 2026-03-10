"""
Generate an animated GIF for Erasure Coding.
Style: clean box diagrams with animated arrows and visual elements.
Requires: Pillow
Output: assets/gifs/core_15_erasure_coding.gif
"""

import math
import os
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
GREEN_BG = (14, 48, 40)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)
YELLOW_BG = (58, 50, 14)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)

WHITE = (235, 240, 245)
DIM = (100, 110, 125)

N_FRAMES = 36
FRAME_MS = 90

# Data block colors (distinct for each original block)
BLOCK_COLORS = [CYAN, GREEN, YELLOW, PURPLE]
BLOCK_BGS = [CYAN_BG, GREEN_BG, YELLOW_BG, PURPLE_BG]
PARITY_COLOR = ORANGE
PARITY_BG = (50, 35, 15)


def _font(size, bold=False):
    names = (["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold
             else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
    for n in names:
        for p in [f"/usr/share/fonts/truetype/dejavu/{n}",
                  f"/usr/share/fonts/truetype/liberation/{n}",
                  f"/usr/share/fonts/{n}"]:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except (OSError, IOError):
                    pass
    return ImageFont.load_default()


F_TITLE = _font(26, True)
F_SUB = _font(11)
F_HEAD = _font(15, True)
F_BODY = _font(13)
F_BODY_B = _font(13, True)
F_SM = _font(11)
F_SM_B = _font(11, True)
F_BIG = _font(18, True)


# ============================================================================
# DRAWING HELPERS
# ============================================================================

def rrect(d, box, fill, outline=None, r=12, w=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)


def txt_c(d, s, cx, cy, f, fill):
    bb = d.textbbox((0, 0), s, font=f)
    d.text((cx - (bb[2] - bb[0]) // 2, cy - (bb[3] - bb[1]) // 2),
           s, font=f, fill=fill)


def arrow_march(d, x0, y0, x1, y1, color, phase, dash=8, gap=5, w=2):
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
    a = math.atan2(y1 - y0, x1 - x0)
    for s in [-1, 1]:
        d.line([(x1, y1), (x1 - 8 * math.cos(a + s * 0.4),
                           y1 - 8 * math.sin(a + s * 0.4))], fill=color, width=w)


def draw_data_block(d, x, y, w, h, label, color, bg, r=10):
    """Draw a single data block with label."""
    rrect(d, (x, y, x + w, y + h), bg, color, r=r)
    txt_c(d, label, x + w // 2, y + h // 2, F_SM_B, color)


def draw_lost_block(d, x, y, w, h, label, r=10):
    """Draw a block with X overlay (lost/missing)."""
    rrect(d, (x, y, x + w, y + h), RED_BG, RED, r=r)
    # X lines
    d.line((x + 8, y + 8, x + w - 8, y + h - 8), fill=RED, width=3)
    d.line((x + w - 8, y + 8, x + 8, y + h - 8), fill=RED, width=3)
    txt_c(d, label, x + w // 2, y + h + 12, F_SM, RED)


# ============================================================================
# FRAME DRAWING
# ============================================================================

def draw_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    phase = (fi / N_FRAMES) * 13

    # ── TITLE ──
    txt_c(d, "Erasure Coding", W // 2, 24, F_TITLE, WHITE)
    txt_c(d, "recover data from partial fragments using redundancy",
          W // 2, 52, F_SUB, DIM)

    # ── LAYOUT: Three rows ──
    # Row 1: Original data (4 blocks)
    # Row 2: Encoded (6 blocks = 4 data + 2 parity), 2 X'd out
    # Row 3: Reconstructed (4 blocks restored)

    bw, bh = 90, 50  # block dimensions
    gap = 18          # gap between blocks

    # ── ROW 1: Original Data ──
    row1_y = 85
    row1_label_x = 55
    txt_c(d, "Original", row1_label_x, row1_y + 12, F_SM_B, WHITE)
    txt_c(d, "Data", row1_label_x, row1_y + 28, F_SM_B, WHITE)

    # 4 data blocks
    total_4 = 4 * bw + 3 * gap
    x0_4 = (W - total_4) // 2 + 40
    data_labels = ["D0", "D1", "D2", "D3"]
    for i in range(4):
        bx = x0_4 + i * (bw + gap)
        draw_data_block(d, bx, row1_y, bw, bh, data_labels[i],
                       BLOCK_COLORS[i], BLOCK_BGS[i])

    # ── Marching arrows down: Encode ──
    arr_y1 = row1_y + bh + 5
    arr_y2 = row1_y + bh + 45
    mid_x = W // 2 + 40
    arrow_march(d, mid_x, arr_y1, mid_x, arr_y2, ORANGE, phase, w=2)

    # Encode label
    rrect(d, (mid_x - 55, arr_y1 + 8, mid_x + 55, arr_y1 + 28),
          DARK_BOX, ORANGE, r=8)
    txt_c(d, "Encode (RS)", mid_x, arr_y1 + 18, F_SM_B, ORANGE)

    # ── ROW 2: Encoded (6 blocks, 2 lost) ──
    row2_y = arr_y2 + 10
    txt_c(d, "Encoded", row1_label_x, row2_y + 5, F_SM_B, WHITE)
    txt_c(d, "6 chunks", row1_label_x, row2_y + 21, F_SM, DIM)
    txt_c(d, "(4+2)", row1_label_x, row2_y + 35, F_SM, DIM)

    total_6 = 6 * bw + 5 * gap
    x0_6 = (W - total_6) // 2 + 40
    encoded_labels = ["D0", "D1", "D2", "D3", "P0", "P1"]

    # Lost blocks: indices 1 and 4 (D1 and P0)
    lost = {1, 4}

    for i in range(6):
        bx = x0_6 + i * (bw + gap)
        if i in lost:
            draw_lost_block(d, bx, row2_y, bw, bh, encoded_labels[i])
        elif i < 4:
            draw_data_block(d, bx, row2_y, bw, bh, encoded_labels[i],
                           BLOCK_COLORS[i], BLOCK_BGS[i])
        else:
            draw_data_block(d, bx, row2_y, bw, bh, encoded_labels[i],
                           PARITY_COLOR, PARITY_BG)

    # "lost" label
    txt_c(d, "LOST", x0_6 + 1 * (bw + gap) + bw // 2, row2_y + bh + 12, F_SM, RED)
    txt_c(d, "LOST", x0_6 + 4 * (bw + gap) + bw // 2, row2_y + bh + 12, F_SM, RED)

    # ── Marching arrows down: Reconstruct ──
    arr2_y1 = row2_y + bh + 25
    arr2_y2 = row2_y + bh + 65
    arrow_march(d, mid_x, arr2_y1, mid_x, arr2_y2, GREEN, phase, w=2)

    rrect(d, (mid_x - 65, arr2_y1 + 8, mid_x + 65, arr2_y1 + 28),
          DARK_BOX, GREEN, r=8)
    txt_c(d, "Reconstruct", mid_x, arr2_y1 + 18, F_SM_B, GREEN)

    # ── ROW 3: Reconstructed (4 blocks) ──
    row3_y = arr2_y2 + 10
    txt_c(d, "Recovered", row1_label_x, row3_y + 12, F_SM_B, WHITE)
    txt_c(d, "Data", row1_label_x, row3_y + 28, F_SM_B, WHITE)

    for i in range(4):
        bx = x0_4 + i * (bw + gap)
        # Scanning glow on recovered block
        p = 0.5 + 0.5 * math.sin(2 * math.pi * (fi + i * 9) / N_FRAMES)
        glow_w = 2 + int(2 * p)
        draw_data_block(d, bx, row3_y, bw, bh, data_labels[i],
                       BLOCK_COLORS[i], BLOCK_BGS[i])
        # Glow border
        if i == 1:  # highlight the recovered block
            d.rounded_rectangle(
                (bx - 3, row3_y - 3, bx + bw + 3, row3_y + bh + 3),
                radius=12, outline=GREEN, width=glow_w)

    # ── Polynomial curve visualization (right side) ──
    curve_panel_x = 45
    curve_panel_y = row3_y + bh + 20
    curve_w = W - 90
    curve_h = 75
    rrect(d, (curve_panel_x, curve_panel_y,
              curve_panel_x + curve_w, curve_panel_y + curve_h),
          PANEL, BORDER, r=12)

    # Title for curve
    txt_c(d, "Polynomial Interpolation", curve_panel_x + curve_w // 2,
          curve_panel_y + 12, F_SM_B, PURPLE)

    # Draw a simple polynomial curve
    cx0 = curve_panel_x + 30
    cy_mid = curve_panel_y + 48
    cw = curve_w - 60
    pts = []
    for px in range(cw):
        t = px / cw
        # Simple cubic-like curve
        val = math.sin(t * 2.5 * math.pi) * 15
        pts.append((cx0 + px, cy_mid - val))

    # Draw curve
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i + 1]], fill=PURPLE, width=2)

    # Draw data points on curve
    point_positions = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    point_colors = [CYAN, RED, YELLOW, PURPLE, RED, ORANGE]  # red = lost
    point_labels = ["D0", "D1", "D2", "D3", "P0", "P1"]
    for i, (frac, color, lbl) in enumerate(zip(point_positions, point_colors, point_labels)):
        px = cx0 + int(frac * cw)
        t = frac
        val = math.sin(t * 2.5 * math.pi) * 15
        py = int(cy_mid - val)
        r = 5
        if i in lost:
            # Lost point - hollow with X
            d.ellipse((px - r, py - r, px + r, py + r), outline=RED, width=2)
        else:
            d.ellipse((px - r, py - r, px + r, py + r), fill=color)

    # Animated scanning dot along curve
    scan_frac = (fi / N_FRAMES)
    scan_px = cx0 + int(scan_frac * cw)
    scan_val = math.sin(scan_frac * 2.5 * math.pi) * 15
    scan_py = int(cy_mid - scan_val)
    d.ellipse((scan_px - 3, scan_py - 3, scan_px + 3, scan_py + 3), fill=WHITE)

    # Info text
    txt_c(d, "any 4 of 6 chunks can recover all data  --  tolerates 2 losses",
          curve_panel_x + curve_w // 2, curve_panel_y + curve_h - 12, F_SM, GREEN)

    # ── FOOTER ──
    txt_c(d, "core/15_erasure_coding.py", W // 2, H - 12, F_SM, (50, 55, 65))

    return img


def main():
    frames = [draw_frame(i) for i in range(N_FRAMES)]
    out = "assets/gifs/core_15_erasure_coding.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=FRAME_MS, loop=0, optimize=True)
    print(f"Saved {out} ({len(frames)} frames, {W}x{H})")


if __name__ == "__main__":
    main()
