"""
Generate an animated GIF for Zero-Knowledge Proofs (Schnorr Protocol).
Style: clean box diagrams with animated arrows and visual elements.
Requires: Pillow
Output: assets/gifs/core_13_zero_knowledge_proofs.gif
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


# ============================================================================
# DRAWING HELPERS
# ============================================================================

def rrect(d, box, fill, outline=None, r=12, w=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)


def text_w(d, s, f):
    bb = d.textbbox((0, 0), s, font=f)
    return bb[2] - bb[0]


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
        d.line([(x1, y1), (x1 - 10 * math.cos(a + s * 0.4),
                           y1 - 10 * math.sin(a + s * 0.4))], fill=color, width=w)


def pulse_alpha(frame, speed=1.0):
    """Return a 0..1 pulse value for glow effects."""
    return 0.5 + 0.5 * math.sin(2 * math.pi * frame * speed / N_FRAMES)


# ============================================================================
# FRAME DRAWING
# ============================================================================

def draw_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    phase = (fi / N_FRAMES) * 13  # marching ant phase

    # ── TITLE ──
    txt_c(d, "Zero-Knowledge Proofs", W // 2, 24, F_TITLE, WHITE)
    txt_c(d, "prove you know a secret without revealing it", W // 2, 52, F_SUB, DIM)

    # ── LAYOUT: Prover (left) | Protocol arrows (center) | Verifier (right) ──
    prover_x = 55
    verifier_x = 555
    box_w = 190
    box_h = 260
    box_y = 85

    # ── PROVER BOX ──
    rrect(d, (prover_x, box_y, prover_x + box_w, box_y + box_h),
          PURPLE_BG, PURPLE, r=14)
    txt_c(d, "Prover", prover_x + box_w // 2, box_y + 20, F_HEAD, PURPLE)

    # Secret key visual
    key_y = box_y + 48
    rrect(d, (prover_x + 15, key_y, prover_x + box_w - 15, key_y + 32),
          DARK_BOX, BORDER, r=8)
    txt_c(d, "secret x", prover_x + box_w // 2, key_y + 10, F_SM, YELLOW)
    # Lock icon (simple padlock shape)
    lx = prover_x + box_w // 2
    ly = key_y + 25
    d.rounded_rectangle((lx - 6, ly - 4, lx + 6, ly + 6), radius=2,
                         fill=YELLOW_BG, outline=YELLOW, width=1)
    d.arc((lx - 4, ly - 10, lx + 4, ly - 2), 0, 180, fill=YELLOW, width=1)

    # Public key
    pk_y = key_y + 42
    rrect(d, (prover_x + 15, pk_y, prover_x + box_w - 15, pk_y + 28),
          CYAN_BG, CYAN, r=8)
    txt_c(d, "PK = x * G", prover_x + box_w // 2, pk_y + 14, F_SM_B, CYAN)

    # Commitment R
    r_y = pk_y + 40
    rrect(d, (prover_x + 15, r_y, prover_x + box_w - 15, r_y + 28),
          GREEN_BG, GREEN, r=8)
    txt_c(d, "R = r * G", prover_x + box_w // 2, r_y + 14, F_SM_B, GREEN)

    # Response s
    s_y = r_y + 40
    rrect(d, (prover_x + 15, s_y, prover_x + box_w - 15, s_y + 28),
          YELLOW_BG, YELLOW, r=8)
    txt_c(d, "s = r + c * x", prover_x + box_w // 2, s_y + 14, F_SM_B, YELLOW)

    # ── VERIFIER BOX ──
    rrect(d, (verifier_x, box_y, verifier_x + box_w, box_y + box_h),
          CYAN_BG, CYAN, r=14)
    txt_c(d, "Verifier", verifier_x + box_w // 2, box_y + 20, F_HEAD, CYAN)

    # Knows PK
    vpk_y = box_y + 48
    rrect(d, (verifier_x + 15, vpk_y, verifier_x + box_w - 15, vpk_y + 32),
          DARK_BOX, BORDER, r=8)
    txt_c(d, "knows PK", verifier_x + box_w // 2, vpk_y + 16, F_SM, CYAN)

    # Challenge c
    vc_y = vpk_y + 48
    rrect(d, (verifier_x + 15, vc_y, verifier_x + box_w - 15, vc_y + 28),
          PURPLE_BG, PURPLE, r=8)
    txt_c(d, "random c", verifier_x + box_w // 2, vc_y + 14, F_SM_B, PURPLE)

    # Verify check
    vv_y = vc_y + 44
    rrect(d, (verifier_x + 15, vv_y, verifier_x + box_w - 15, vv_y + 38),
          GREEN_BG, GREEN, r=8)
    txt_c(d, "check:", verifier_x + box_w // 2, vv_y + 10, F_SM, DIM)
    txt_c(d, "s*G = R + c*PK", verifier_x + box_w // 2, vv_y + 27, F_SM_B, GREEN)

    # Question mark / no x known
    no_y = vv_y + 48
    txt_c(d, "x = ???", verifier_x + box_w // 2, no_y, F_SM, RED)

    # ── PROTOCOL ARROWS (center column) ──
    ax_l = prover_x + box_w + 8    # arrow start (right of prover)
    ax_r = verifier_x - 8          # arrow end (left of verifier)
    mid_x = (ax_l + ax_r) // 2

    # Step 1: Prover → Verifier: R (commitment)
    a1_y = box_y + 78
    arrow_march(d, ax_l, a1_y, ax_r, a1_y, GREEN, phase, w=2)
    # Label above arrow
    rrect(d, (mid_x - 45, a1_y - 22, mid_x + 45, a1_y - 4), DARK_BOX, GREEN, r=8)
    txt_c(d, "1. send R", mid_x, a1_y - 13, F_SM_B, GREEN)

    # Step 2: Verifier → Prover: c (challenge)
    a2_y = box_y + 140
    arrow_march(d, ax_r, a2_y, ax_l, a2_y, PURPLE, phase, w=2)
    rrect(d, (mid_x - 55, a2_y - 22, mid_x + 55, a2_y - 4), DARK_BOX, PURPLE, r=8)
    txt_c(d, "2. challenge c", mid_x, a2_y - 13, F_SM_B, PURPLE)

    # Step 3: Prover → Verifier: s (response)
    a3_y = box_y + 202
    arrow_march(d, ax_l, a3_y, ax_r, a3_y, YELLOW, phase, w=2)
    rrect(d, (mid_x - 50, a3_y - 22, mid_x + 50, a3_y - 4), DARK_BOX, YELLOW, r=8)
    txt_c(d, "3. respond s", mid_x, a3_y - 13, F_SM_B, YELLOW)

    # ── BOTTOM PANEL: Zero Knowledge property ──
    panel_y = box_y + box_h + 25
    panel_h = 105
    rrect(d, (35, panel_y, W - 35, panel_y + panel_h), PANEL, BORDER, r=14)

    # Three property badges
    props = [
        ("Completeness", "honest prover always passes", GREEN),
        ("Soundness", "cheater cannot forge proof", RED),
        ("Zero-Knowledge", "verifier learns nothing about x", YELLOW),
    ]
    badge_w = 225
    gap = 15
    total = len(props) * badge_w + (len(props) - 1) * gap
    bx = (W - total) // 2
    for label, desc, color in props:
        by = panel_y + 14
        bg = (*color[:3],)
        dim_bg = tuple(max(0, c // 8 + BG[i]) for i, c in enumerate(color))
        rrect(d, (bx, by, bx + badge_w, by + 42), dim_bg, color, r=10)
        txt_c(d, label, bx + badge_w // 2, by + 14, F_SM_B, color)
        txt_c(d, desc, bx + badge_w // 2, by + 32, F_SM, DIM)
        bx += badge_w + gap

    # Bottom insight with pulse
    p = pulse_alpha(fi, 0.8)
    g_val = int(130 + 80 * p)
    insight_color = (40, g_val, 120)
    txt_c(d, "Verifier is convinced Prover knows x -- but learns NOTHING about x",
          W // 2, panel_y + panel_h - 22, F_BODY_B, insight_color)

    # ── Scanning highlight on active arrow ──
    cycle = fi % 12
    if cycle < 4:
        scan_y = a1_y
        frac = cycle / 4.0
        sx = ax_l + frac * (ax_r - ax_l)
    elif cycle < 8:
        scan_y = a2_y
        frac = (cycle - 4) / 4.0
        sx = ax_r - frac * (ax_r - ax_l)
    else:
        scan_y = a3_y
        frac = (cycle - 8) / 4.0
        sx = ax_l + frac * (ax_r - ax_l)
    d.ellipse((sx - 4, scan_y - 4, sx + 4, scan_y + 4), fill=WHITE)

    # ── FOOTER ──
    txt_c(d, "core/13_zero_knowledge_proofs.py", W // 2, H - 12, F_SM, (50, 55, 65))

    return img


def main():
    frames = [draw_frame(i) for i in range(N_FRAMES)]
    out = "assets/gifs/core_13_zero_knowledge_proofs.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=FRAME_MS, loop=0, optimize=True)
    print(f"Saved {out} ({len(frames)} frames, {W}x{H})")


if __name__ == "__main__":
    main()
