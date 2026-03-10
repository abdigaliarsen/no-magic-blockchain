"""Tower BFT: Vote tower with exponential lockouts and fork choice."""
from PIL import Image, ImageDraw, ImageFont
import math, os

W, H, FRAMES, DUR = 800, 550, 72, 90
BG = (13, 17, 23)
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)
CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
PURPLE = (167, 139, 250)
PURPLE_BG = (35, 28, 58)
RED = (248, 113, 113)
RED_BG = (50, 20, 20)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
YELLOW_BG = (58, 50, 14)

OUT = "assets/gifs/solana_09_tower_bft.gif"

def load_font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for n in names:
        for p in [f"/usr/share/fonts/truetype/dejavu/{n}", f"/usr/share/fonts/truetype/liberation/{n}", f"/usr/share/fonts/{n}"]:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except (OSError, IOError): pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(15, True)
body_font = load_font(13)
small_font = load_font(11)

def draw_rounded_rect(d, xy, fill, outline, r=8):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def make_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    t = fi / (FRAMES - 1)

    # Title
    title = "Tower BFT: Vote Lockouts"
    tw, _ = text_size(d, title, title_font)
    d.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)
    sub = "Exponential lockouts secure fork choice"
    sw, _ = text_size(d, sub, body_font)
    d.text(((W - sw) // 2, 44), sub, fill=DIM, font=body_font)

    # === LEFT: Vote Tower ===
    lt_x, lt_w = 30, 220
    panel_top, panel_bot = 72, 400
    draw_rounded_rect(d, (lt_x, panel_top, lt_x + lt_w, panel_bot), PANEL, BORDER)
    hdr = "Vote Tower"
    hw, _ = text_size(d, hdr, header_font)
    d.text((lt_x + (lt_w - hw) // 2, panel_top + 8), hdr, fill=PURPLE, font=header_font)

    # Stack of votes with lockout periods
    votes = [
        ("Slot 80", 2, CYAN),
        ("Slot 79", 4, CYAN),
        ("Slot 78", 8, GREEN),
        ("Slot 77", 16, GREEN),
        ("Slot 76", 32, YELLOW),
        ("Slot 75", 64, ORANGE),
        ("Slot 74", 128, RED),
    ]

    box_w, box_h = 170, 28
    start_y = panel_top + 32
    # Pulsing highlight on one vote
    highlight_idx = (fi // 10) % len(votes)

    for i, (slot, lockout, color) in enumerate(votes):
        bx = lt_x + (lt_w - box_w) // 2
        by = start_y + i * (box_h + 6)
        is_hl = (i == highlight_idx)
        fill = lerp_color(DARK_BOX, CYAN_BG, 0.5) if is_hl else DARK_BOX
        outline = lerp_color(BORDER, color, 0.7 if is_hl else 0.3)
        draw_rounded_rect(d, (bx, by, bx + box_w, by + box_h), fill, outline, r=5)

        # Slot label
        d.text((bx + 8, by + 7), slot, fill=color if is_hl else lerp_color(DIM, color, 0.5), font=small_font)
        # Lockout badge
        lo_text = f"lockout: {lockout}"
        lo_w, _ = text_size(d, lo_text, small_font)
        d.text((bx + box_w - lo_w - 8, by + 7), lo_text, fill=YELLOW if is_hl else DIM, font=small_font)

    # Lockout label
    lo_label = "Lockout doubles per depth"
    ll_w, _ = text_size(d, lo_label, small_font)
    d.text((lt_x + (lt_w - ll_w) // 2, panel_bot - 22), lo_label, fill=YELLOW, font=small_font)

    # === RIGHT: Fork Choice ===
    rt_x, rt_w = 280, 490
    draw_rounded_rect(d, (rt_x, panel_top, rt_x + rt_w, panel_bot), PANEL, BORDER)
    hdr2 = "Fork Choice (Stake-Weighted)"
    hw2, _ = text_size(d, hdr2, header_font)
    d.text((rt_x + (rt_w - hw2) // 2, panel_top + 8), hdr2, fill=GREEN, font=header_font)

    # Draw two competing forks from a common ancestor
    # Common chain
    chain_y = panel_top + 55
    bw, bh = 55, 30
    common_x = rt_x + 25

    common_blocks = ["74", "75", "76"]
    for i, blk in enumerate(common_blocks):
        bx = common_x + i * (bw + 18)
        draw_rounded_rect(d, (bx, chain_y, bx + bw, chain_y + bh), DARK_BOX, lerp_color(BORDER, CYAN, 0.3), r=5)
        lbl = f"#{blk}"
        lw, _ = text_size(d, lbl, small_font)
        d.text((bx + (bw - lw) // 2, chain_y + 8), lbl, fill=CYAN, font=small_font)
        if i < len(common_blocks) - 1:
            d.line([(bx + bw + 2, chain_y + bh // 2), (bx + bw + 16, chain_y + bh // 2)], fill=BORDER, width=1)

    fork_x = common_x + len(common_blocks) * (bw + 18) - 18
    # Fork point
    fork_cx = fork_x + bw // 2

    # Fork A (top) - winning
    fork_a_y = chain_y - 50
    fork_a_blocks = ["77a", "78a", "79a"]
    # Fork B (bottom) - losing
    fork_b_y = chain_y + 55
    fork_b_blocks = ["77b", "78b"]

    # Lines from fork point to fork starts
    d.line([(fork_x - 2, chain_y + bh // 2), (fork_x + 15, fork_a_y + bh // 2)], fill=lerp_color(BORDER, GREEN, 0.5), width=2)
    d.line([(fork_x - 2, chain_y + bh // 2), (fork_x + 15, fork_b_y + bh // 2)], fill=lerp_color(BORDER, RED, 0.3), width=1)

    # Draw Fork A blocks
    for i, blk in enumerate(fork_a_blocks):
        bx = fork_x + 18 + i * (bw + 14)
        pulse = 0.5 + 0.5 * math.sin(t * math.pi * 4 + i)
        draw_rounded_rect(d, (bx, fork_a_y, bx + bw, fork_a_y + bh),
                          lerp_color(DARK_BOX, GREEN_BG, 0.3), lerp_color(BORDER, GREEN, 0.4 + 0.3 * pulse), r=5)
        lbl = f"#{blk}"
        lw, _ = text_size(d, lbl, small_font)
        d.text((bx + (bw - lw) // 2, fork_a_y + 8), lbl, fill=GREEN, font=small_font)
        if i < len(fork_a_blocks) - 1:
            d.line([(bx + bw + 1, fork_a_y + bh // 2), (bx + bw + 13, fork_a_y + bh // 2)], fill=lerp_color(BORDER, GREEN, 0.4), width=1)

    # Stake label for Fork A
    stake_a = "72% stake"
    saw, _ = text_size(d, stake_a, small_font)
    last_ax = fork_x + 18 + (len(fork_a_blocks) - 1) * (bw + 14) + bw + 8
    d.text((last_ax, fork_a_y + 8), stake_a, fill=GREEN, font=small_font)

    # Draw Fork B blocks
    for i, blk in enumerate(fork_b_blocks):
        bx = fork_x + 18 + i * (bw + 14)
        draw_rounded_rect(d, (bx, fork_b_y, bx + bw, fork_b_y + bh),
                          DARK_BOX, lerp_color(BORDER, RED, 0.3), r=5)
        lbl = f"#{blk}"
        lw, _ = text_size(d, lbl, small_font)
        d.text((bx + (bw - lw) // 2, fork_b_y + 8), lbl, fill=lerp_color(DIM, RED, 0.5), font=small_font)
        if i < len(fork_b_blocks) - 1:
            d.line([(bx + bw + 1, fork_b_y + bh // 2), (bx + bw + 13, fork_b_y + bh // 2)], fill=lerp_color(BORDER, RED, 0.2), width=1)

    # Stake label for Fork B
    stake_b = "28% stake"
    sbw, _ = text_size(d, stake_b, small_font)
    last_bx = fork_x + 18 + (len(fork_b_blocks) - 1) * (bw + 14) + bw + 8
    d.text((last_bx, fork_b_y + 8), stake_b, fill=RED, font=small_font)

    # Winner / Loser labels
    d.text((fork_x + 18, fork_a_y - 16), ">> Winner (heaviest fork)", fill=GREEN, font=small_font)
    d.text((fork_x + 18, fork_b_y + bh + 4), "Abandoned fork", fill=DIM, font=small_font)

    # PoH timeline at bottom of right panel
    poh_y = panel_bot - 60
    d.text((rt_x + 15, poh_y), "PoH Timeline:", fill=DIM, font=small_font)
    poh_start = rt_x + 100
    poh_end = rt_x + rt_w - 20
    d.line([(poh_start, poh_y + 8), (poh_end, poh_y + 8)], fill=BORDER, width=2)
    # Ticks
    n_ticks = 8
    for i in range(n_ticks):
        tx = poh_start + i * (poh_end - poh_start) // (n_ticks - 1)
        d.line([(tx, poh_y + 4), (tx, poh_y + 12)], fill=CYAN, width=1)
    # Moving marker
    marker_x = poh_start + int(t * (poh_end - poh_start))
    d.ellipse((marker_x - 4, poh_y + 4, marker_x + 4, poh_y + 12), fill=CYAN)

    # Votes on PoH
    d.text((rt_x + 15, poh_y + 20), "Votes anchor to PoH slots -- no ambiguity", fill=DIM, font=small_font)

    # === Bottom Panel: Explanation ===
    bot_y = 412
    draw_rounded_rect(d, (30, bot_y, W - 30, H - 14), PANEL, BORDER)

    explanations = [
        ("Exponential Lockouts", "Each deeper vote doubles lockout: 2, 4, 8, 16, 32... slots", CYAN),
        ("Cost of Switching Forks", "Switching to a competing fork means losing all deeper lockouts", ORANGE),
        ("Stake-Weighted Fork Choice", "The fork with the most staked SOL voting on it wins", GREEN),
        ("Optimistic Confirmation", "66%+ stake on a slot = optimistically confirmed in ~400ms", PURPLE),
    ]
    idx = (fi // 18) % len(explanations)
    et, ed, ec = explanations[idx]
    etw, _ = text_size(d, et, header_font)
    d.text(((W - etw) // 2, bot_y + 10), et, fill=ec, font=header_font)
    edw, _ = text_size(d, ed, body_font)
    d.text(((W - edw) // 2, bot_y + 32), ed, fill=DIM, font=body_font)

    # Mini lockout sequence
    mini_y = bot_y + 56
    lockouts = [2, 4, 8, 16, 32, 64, 128, 256]
    total_w = len(lockouts) * 50 + (len(lockouts) - 1) * 8
    sx = (W - total_w) // 2
    for i, lo in enumerate(lockouts):
        mx = sx + i * 58
        dist = abs(t * total_w + sx - (mx + 25))
        hl = max(0, 1.0 - dist / 60)
        c = lerp_color(BORDER, YELLOW, hl)
        f = lerp_color(DARK_BOX, YELLOW_BG, hl * 0.3)
        draw_rounded_rect(d, (mx, mini_y, mx + 50, mini_y + 18), f, c, r=4)
        lt = str(lo)
        lw, _ = text_size(d, lt, small_font)
        d.text((mx + (50 - lw) // 2, mini_y + 3), lt, fill=lerp_color(DIM, YELLOW, hl), font=small_font)
        if i < len(lockouts) - 1:
            d.line([(mx + 51, mini_y + 9), (mx + 57, mini_y + 9)], fill=BORDER, width=1)

    # "x2" labels above arrows
    d.text((sx - 30, mini_y + 2), "x2 >>", fill=YELLOW, font=small_font)

    return img


if __name__ == "__main__":
    frames = [make_frame(i) for i in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DUR, loop=0, optimize=True)
    print(f"Saved {OUT} ({len(frames)} frames)")
