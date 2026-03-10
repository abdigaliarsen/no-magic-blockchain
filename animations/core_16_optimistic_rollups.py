"""
Generate an animated GIF for Optimistic Rollups.
Style: clean box diagrams with animated arrows and visual elements.
Requires: Pillow
Output: assets/gifs/core_16_optimistic_rollups.gif
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


def draw_tx_box(d, x, y, w, h, label, color, bg, r=6):
    """Draw a small transaction box."""
    rrect(d, (x, y, x + w, y + h), bg, color, r=r)
    txt_c(d, label, x + w // 2, y + h // 2, F_SM, color)


# ============================================================================
# FRAME DRAWING
# ============================================================================

def draw_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    phase = (fi / N_FRAMES) * 13

    # ── TITLE ──
    txt_c(d, "Optimistic Rollups", W // 2, 24, F_TITLE, WHITE)
    txt_c(d, "execute on L2, post data to L1, challenge if invalid",
          W // 2, 52, F_SUB, DIM)

    # ════════════════════════════════════════════════════════
    # LAYOUT: L2 layer (top) and L1 layer (bottom)
    # ════════════════════════════════════════════════════════

    # ── L2 LAYER ──
    l2_y = 75
    l2_h = 150
    l2_x = 35
    l2_w = W - 70
    rrect(d, (l2_x, l2_y, l2_x + l2_w, l2_y + l2_h), PANEL, CYAN, r=14)

    # L2 label
    rrect(d, (l2_x + 8, l2_y + 6, l2_x + 55, l2_y + 26), CYAN_BG, CYAN, r=8)
    txt_c(d, "L2", l2_x + 31, l2_y + 16, F_SM_B, CYAN)

    # Sequencer box
    seq_x = l2_x + 25
    seq_y = l2_y + 38
    seq_w = 130
    seq_h = 55
    rrect(d, (seq_x, seq_y, seq_x + seq_w, seq_y + seq_h),
          PURPLE_BG, PURPLE, r=10)
    txt_c(d, "Sequencer", seq_x + seq_w // 2, seq_y + 16, F_SM_B, PURPLE)
    txt_c(d, "orders txs", seq_x + seq_w // 2, seq_y + 36, F_SM, DIM)

    # Transaction pool (small tx boxes flowing into sequencer)
    tx_labels = ["tx1", "tx2", "tx3", "tx4", "tx5"]
    tx_w, tx_h = 42, 22
    tx_x_start = seq_x + seq_w + 20
    tx_y = seq_y + 5
    for i, label in enumerate(tx_labels):
        tx_x = tx_x_start + i * (tx_w + 8)
        # Alternate colors
        colors = [CYAN, GREEN, YELLOW, ORANGE, PURPLE]
        bgs = [CYAN_BG, GREEN_BG, YELLOW_BG, (50, 35, 15), PURPLE_BG]
        draw_tx_box(d, tx_x, tx_y, tx_w, tx_h, label,
                    colors[i], bgs[i], r=6)

    # Arrow from txs to sequencer (marching right-to-left)
    arrow_march(d, tx_x_start - 5, seq_y + seq_h // 2,
                seq_x + seq_w + 5, seq_y + seq_h // 2, CYAN, phase, w=2)

    # Batch box (output of sequencer)
    batch_x = seq_x + 10
    batch_y = seq_y + seq_h + 12
    batch_w = 700
    batch_h = 30
    rrect(d, (batch_x, batch_y, batch_x + batch_w, batch_y + batch_h),
          DARK_BOX, ORANGE, r=8)
    txt_c(d, "Batch: [tx1, tx2, tx3, tx4, tx5]  +  state_root: 0xa3f7...",
          batch_x + batch_w // 2, batch_y + batch_h // 2, F_SM, ORANGE)

    # ── Arrow L2 → L1 ──
    mid_x = W // 2
    arr_y1 = l2_y + l2_h + 5
    arr_y2 = l2_y + l2_h + 45
    arrow_march(d, mid_x, arr_y1, mid_x, arr_y2, YELLOW, phase, w=3)
    rrect(d, (mid_x - 55, arr_y1 + 8, mid_x + 55, arr_y1 + 28),
          DARK_BOX, YELLOW, r=8)
    txt_c(d, "post batch", mid_x, arr_y1 + 18, F_SM_B, YELLOW)

    # ── L1 LAYER ──
    l1_y = arr_y2 + 10
    l1_h = 120
    rrect(d, (l2_x, l1_y, l2_x + l2_w, l1_y + l1_h), PANEL, GREEN, r=14)

    # L1 label
    rrect(d, (l2_x + 8, l1_y + 6, l2_x + 55, l1_y + 26), GREEN_BG, GREEN, r=8)
    txt_c(d, "L1", l2_x + 31, l1_y + 16, F_SM_B, GREEN)

    # State roots on L1
    root_y = l1_y + 35
    root_labels = ["S0", "S1", "S2", "S3"]
    root_w, root_h = 80, 40
    root_gap = 20
    total_roots = len(root_labels) * root_w + (len(root_labels) - 1) * root_gap
    rx0 = (W - total_roots) // 2

    for i, rl in enumerate(root_labels):
        rx = rx0 + i * (root_w + root_gap)
        if i == 2:
            # Bad state root (highlighted red)
            p = 0.5 + 0.5 * math.sin(2 * math.pi * fi / N_FRAMES)
            glow_w = 2 + int(2 * p)
            rrect(d, (rx, root_y, rx + root_w, root_y + root_h),
                  RED_BG, RED, r=8, w=glow_w)
            txt_c(d, rl, rx + root_w // 2, root_y + 12, F_SM_B, RED)
            txt_c(d, "invalid!", rx + root_w // 2, root_y + 28, F_SM, RED)
        else:
            rrect(d, (rx, root_y, rx + root_w, root_y + root_h),
                  GREEN_BG, GREEN, r=8)
            txt_c(d, rl, rx + root_w // 2, root_y + 12, F_SM_B, GREEN)
            txt_c(d, "valid", rx + root_w // 2, root_y + 28, F_SM, DIM)

        # Chain links between roots
        if i < len(root_labels) - 1:
            d.line([(rx + root_w + 2, root_y + root_h // 2),
                    (rx + root_w + root_gap - 2, root_y + root_h // 2)],
                   fill=BORDER, width=2)

    # Challenge window bar
    cw_y = root_y + root_h + 10
    cw_x = rx0
    cw_w = total_roots
    rrect(d, (cw_x, cw_y, cw_x + cw_w, cw_y + 18), DARK_BOX, BORDER, r=6)
    # Animated progress
    progress = (fi / N_FRAMES)
    fill_w = int(cw_w * progress)
    if fill_w > 4:
        d.rounded_rectangle((cw_x, cw_y, cw_x + fill_w, cw_y + 18),
                            radius=6, fill=YELLOW_BG, outline=YELLOW, width=1)
    txt_c(d, "Challenge Window (7 days)", cw_x + cw_w // 2, cw_y + 9,
          F_SM, YELLOW)

    # ── FRAUD PROOF PANEL (bottom) ──
    fp_y = l1_y + l1_h + 15
    fp_h = 95
    rrect(d, (35, fp_y, W - 35, fp_y + fp_h), PANEL, BORDER, r=14)

    txt_c(d, "Fraud Proof", W // 2, fp_y + 14, F_HEAD, RED)

    # Three-step flow
    steps = [
        ("Challenger", "detects\nbad root", RED, RED_BG),
        ("Re-execute", "replay txs\non L1", YELLOW, YELLOW_BG),
        ("Slash", "sequencer\npenalized", GREEN, GREEN_BG),
    ]

    step_w = 150
    step_h = 48
    step_gap = 55
    total_steps = len(steps) * step_w + (len(steps) - 1) * step_gap
    sx0 = (W - total_steps) // 2

    for i, (label, desc, color, bg) in enumerate(steps):
        sx = sx0 + i * (step_w + step_gap)
        sy = fp_y + 30
        rrect(d, (sx, sy, sx + step_w, sy + step_h), bg, color, r=10)
        txt_c(d, label, sx + step_w // 2, sy + 14, F_SM_B, color)
        # Multiline desc
        lines = desc.split("\n")
        for li, line in enumerate(lines):
            txt_c(d, line, sx + step_w // 2, sy + 30 + li * 12, F_SM, DIM)

        # Arrow between steps
        if i < len(steps) - 1:
            ax0 = sx + step_w + 5
            ax1 = sx + step_w + step_gap - 5
            ay = sy + step_h // 2
            arrow_march(d, ax0, ay, ax1, ay, color, phase, w=2)

    # ── Insight ──
    p = 0.5 + 0.5 * math.sin(2 * math.pi * fi / N_FRAMES * 0.8)
    g_val = int(130 + 80 * p)
    txt_c(d, "assume valid, prove fraud only when needed",
          W // 2, fp_y + fp_h - 12, F_BODY_B, (40, g_val, 120))

    # ── FOOTER ──
    txt_c(d, "core/16_optimistic_rollups.py", W // 2, H - 12, F_SM, (50, 55, 65))

    return img


def main():
    frames = [draw_frame(i) for i in range(N_FRAMES)]
    out = "assets/gifs/core_16_optimistic_rollups.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=FRAME_MS, loop=0, optimize=True)
    print(f"Saved {out} ({len(frames)} frames, {W}x{H})")


if __name__ == "__main__":
    main()
