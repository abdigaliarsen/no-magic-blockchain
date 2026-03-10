"""
Generate an animated GIF for BFT (Byzantine Fault Tolerant) Consensus.
Style: clean box diagrams with animated arrows and visual elements.
Requires: Pillow
Output: assets/gifs/core_14_bft_consensus.gif
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

N_FRAMES = 72
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


# ============================================================================
# NODE POSITIONS AND DEFINITIONS
# ============================================================================

# 4 nodes in a diamond arrangement
# Node 0 = Primary (top), Node 1 = right, Node 2 = bottom, Node 3 = left (Byzantine)
NODE_R = 32  # node circle radius
NODES = [
    {"name": "Node 0", "label": "Primary", "x": 400, "y": 155, "color": CYAN, "bg": CYAN_BG, "honest": True},
    {"name": "Node 1", "label": "Honest", "x": 580, "y": 265, "color": GREEN, "bg": GREEN_BG, "honest": True},
    {"name": "Node 2", "label": "Honest", "x": 400, "y": 375, "color": GREEN, "bg": GREEN_BG, "honest": True},
    {"name": "Node 3", "label": "Byzantine", "x": 220, "y": 265, "color": RED, "bg": RED_BG, "honest": False},
]


def draw_node(d, node, fi, glow=False):
    """Draw a single node as a circle with label."""
    x, y = node["x"], node["y"]
    color = node["color"]
    bg = node["bg"]

    # Glow ring for active nodes
    if glow:
        p = 0.5 + 0.5 * math.sin(2 * math.pi * fi / N_FRAMES)
        glow_r = NODE_R + 4 + int(3 * p)
        glow_color = tuple(min(255, c // 3) for c in color)
        d.ellipse((x - glow_r, y - glow_r, x + glow_r, y + glow_r),
                  fill=glow_color)

    # Main circle
    d.ellipse((x - NODE_R, y - NODE_R, x + NODE_R, y + NODE_R),
              fill=bg, outline=color, width=2)

    # Node number
    txt_c(d, node["name"][-1], x, y - 2, F_HEAD, color)

    # Label below
    txt_c(d, node["label"], x, y + NODE_R + 12, F_SM, color)

    # X mark for Byzantine node
    if not node["honest"]:
        d.line((x - 10, y - 10, x + 10, y + 10), fill=RED, width=3)
        d.line((x + 10, y - 10, x - 10, y + 10), fill=RED, width=3)


def edge_point(x0, y0, x1, y1, r):
    """Get point on circle edge from center toward target."""
    a = math.atan2(y1 - y0, x1 - x0)
    return x0 + r * math.cos(a), y0 + r * math.sin(a)


# ============================================================================
# FRAME DRAWING
# ============================================================================

def draw_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    phase = (fi / N_FRAMES) * 13

    # ── TITLE ──
    txt_c(d, "BFT Consensus", W // 2, 24, F_TITLE, WHITE)
    txt_c(d, "reach agreement despite Byzantine (malicious) nodes",
          W // 2, 52, F_SUB, DIM)

    # ── Determine which phase to highlight ──
    # Cycle through 3 phases: pre-prepare, prepare, commit
    cycle = fi % 36
    if cycle < 12:
        active_phase = 0   # pre-prepare
    elif cycle < 24:
        active_phase = 1   # prepare
    else:
        active_phase = 2   # commit

    # ── Draw message arrows between nodes ──
    # Phase 0: Primary (0) → all others
    if active_phase == 0:
        for i in [1, 2, 3]:
            src, dst = NODES[0], NODES[i]
            sx, sy = edge_point(src["x"], src["y"], dst["x"], dst["y"], NODE_R + 4)
            ex, ey = edge_point(dst["x"], dst["y"], src["x"], src["y"], NODE_R + 4)
            arrow_march(d, sx, sy, ex, ey, CYAN, phase, w=2)

    # Phase 1: All → All (prepare messages)
    elif active_phase == 1:
        for i in range(4):
            for j in range(4):
                if i == j:
                    continue
                src, dst = NODES[i], NODES[j]
                sx, sy = edge_point(src["x"], src["y"], dst["x"], dst["y"], NODE_R + 4)
                ex, ey = edge_point(dst["x"], dst["y"], src["x"], src["y"], NODE_R + 4)
                color = RED if not src["honest"] else GREEN
                arrow_march(d, sx, sy, ex, ey, color, phase, w=1)

    # Phase 2: All → All (commit messages)
    else:
        for i in range(4):
            for j in range(4):
                if i == j:
                    continue
                src, dst = NODES[i], NODES[j]
                sx, sy = edge_point(src["x"], src["y"], dst["x"], dst["y"], NODE_R + 4)
                ex, ey = edge_point(dst["x"], dst["y"], src["x"], src["y"], NODE_R + 4)
                color = RED if not src["honest"] else PURPLE
                arrow_march(d, sx, sy, ex, ey, color, phase, w=1)

    # ── Draw nodes on top of arrows ──
    for i, node in enumerate(NODES):
        glow = (active_phase == 0 and i == 0) or \
               (active_phase >= 1 and node["honest"])
        draw_node(d, node, fi, glow=glow)

    # ── Phase label (right side) ──
    phase_labels = [
        ("1. Pre-Prepare", "primary broadcasts proposal", CYAN),
        ("2. Prepare", "all nodes exchange votes", GREEN),
        ("3. Commit", "nodes finalize agreement", PURPLE),
    ]
    plabel, pdesc, pcolor = phase_labels[active_phase]
    lx, ly = 630, 140
    rrect(d, (lx, ly, W - 30, ly + 52), DARK_BOX, pcolor, r=10)
    txt_c(d, plabel, (lx + W - 30) // 2, ly + 16, F_SM_B, pcolor)
    txt_c(d, pdesc, (lx + W - 30) // 2, ly + 36, F_SM, DIM)

    # ── BOTTOM PANEL ──
    panel_y = 420
    panel_h = 105
    rrect(d, (35, panel_y, W - 35, panel_y + panel_h), PANEL, BORDER, r=14)

    # n=4, f=1 visualization
    node_vis_y = panel_y + 18
    txt_c(d, "n = 4 nodes", 160, node_vis_y, F_SM_B, WHITE)

    # Draw small node circles
    small_r = 10
    sx_start = 100
    for i in range(4):
        sx = sx_start + i * 30
        sy = node_vis_y + 22
        c = RED if i == 3 else GREEN
        bg = RED_BG if i == 3 else GREEN_BG
        d.ellipse((sx - small_r, sy - small_r, sx + small_r, sy + small_r),
                  fill=bg, outline=c, width=2)
        if i == 3:
            d.line((sx - 5, sy - 5, sx + 5, sy + 5), fill=RED, width=2)
            d.line((sx + 5, sy - 5, sx - 5, sy + 5), fill=RED, width=2)

    # Tolerance formula
    txt_c(d, "f < n/3", 160, node_vis_y + 48, F_BODY_B, YELLOW)
    txt_c(d, "1 < 4/3 = 1.33", 160, node_vis_y + 68, F_SM, DIM)

    # Divider
    d.line([(300, panel_y + 12), (300, panel_y + panel_h - 12)],
           fill=BORDER, width=1)

    # Right side: consensus result
    rx = 560
    # Honest nodes agree
    p = 0.5 + 0.5 * math.sin(2 * math.pi * fi / N_FRAMES)
    g_val = int(140 + 80 * p)
    txt_c(d, "3 honest nodes reach consensus", rx, node_vis_y + 8, F_BODY_B,
          (40, g_val, 120))
    txt_c(d, "despite 1 Byzantine fault", rx, node_vis_y + 30, F_SM, RED)

    # Checkmark / result badges
    badge_y = node_vis_y + 50
    badges = [
        ("Safety", "no conflicting decisions", GREEN),
        ("Liveness", "progress guaranteed", CYAN),
    ]
    bx = 380
    for label, desc, color in badges:
        dim_bg = tuple(max(0, c // 8 + BG[i]) for i, c in enumerate(color))
        rrect(d, (bx, badge_y, bx + 180, badge_y + 30), dim_bg, color, r=8)
        txt_c(d, f"{label}: {desc}", bx + 90, badge_y + 15, F_SM, color)
        bx += 195

    # ── FOOTER ──
    txt_c(d, "core/14_bft_consensus.py", W // 2, H - 12, F_SM, (50, 55, 65))

    return img


def main():
    frames = [draw_frame(i) for i in range(N_FRAMES)]
    out = "assets/gifs/core_14_bft_consensus.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=FRAME_MS, loop=0, optimize=True)
    print(f"Saved {out} ({len(frames)} frames, {W}x{H})")


if __name__ == "__main__":
    main()
