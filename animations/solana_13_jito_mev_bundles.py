"""Jito MEV Bundles: Searchers submit bundles with tips to block engine auction."""
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
RED = (248, 113, 113)
PURPLE = (167, 139, 250)
CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
YELLOW_BG = (58, 50, 14)

OUT = "assets/gifs/solana_13_jito_mev_bundles.gif"

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
tiny_font = load_font(10)

def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def draw_rounded_rect(d, xy, fill, outline, r=8):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)


def make_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    t = fi / (FRAMES - 1)
    pulse = 0.5 + 0.5 * math.sin(fi * 2 * math.pi / 10)

    # Title
    title = "Jito MEV Bundles"
    tw, _ = text_size(d, title, title_font)
    d.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)
    sub = "Searcher bundles compete via tip auction"
    sw, _ = text_size(d, sub, body_font)
    d.text(((W - sw) // 2, 44), sub, fill=DIM, font=body_font)

    # === LEFT: Searcher boxes ===
    searchers = [
        ("Searcher A", "Arb: DEX A->B", "0.05 SOL", CYAN, 0.05),
        ("Searcher B", "Liquidation", "0.12 SOL", GREEN, 0.12),
        ("Searcher C", "Arb: DEX C->D", "0.03 SOL", ORANGE, 0.03),
    ]

    sx = 30
    sy_start = 75
    box_w, box_h = 150, 70
    gap = 18

    for i, (name, tx_type, tip, color, tip_val) in enumerate(searchers):
        sy = sy_start + i * (box_h + gap)
        bord = lerp_color(BORDER, color, 0.4 + 0.2 * pulse)
        draw_rounded_rect(d, (sx, sy, sx + box_w, sy + box_h), DARK_BOX, bord, r=6)
        d.text((sx + 10, sy + 6), name, fill=color, font=small_font)
        d.text((sx + 10, sy + 22), tx_type, fill=DIM, font=tiny_font)
        d.text((sx + 10, sy + 38), f"Bundle + Tip: {tip}", fill=YELLOW, font=small_font)
        # Checkmark for winner
        if i == 1:  # Searcher B wins (highest tip)
            d.text((sx + box_w - 20, sy + 6), "*", fill=GREEN, font=header_font)

    # === MIDDLE: Block Engine / Auction ===
    eng_x, eng_y = 230, 85
    eng_w, eng_h = 180, 200
    draw_rounded_rect(d, (eng_x, eng_y, eng_x + eng_w, eng_y + eng_h), PANEL, BORDER)
    d.text((eng_x + 15, eng_y + 8), "Jito Block Engine", fill=PURPLE, font=header_font)
    d.text((eng_x + 15, eng_y + 28), "Bundle Auction", fill=DIM, font=small_font)

    # Auction ranking inside engine
    ranked = [
        ("B: 0.12 SOL", GREEN, True),
        ("A: 0.05 SOL", CYAN, False),
        ("C: 0.03 SOL", ORANGE, False),
    ]
    for i, (label, color, winner) in enumerate(ranked):
        ry = eng_y + 55 + i * 28
        rank_bg = GREEN_BG if winner else DARK_BOX
        rank_bord = GREEN if winner else BORDER
        draw_rounded_rect(d, (eng_x + 15, ry, eng_x + eng_w - 15, ry + 22), rank_bg, rank_bord, r=4)
        prefix = "#1 " if i == 0 else f"#{i+1} "
        d.text((eng_x + 22, ry + 3), prefix + label, fill=color, font=small_font)
        if winner:
            d.text((eng_x + eng_w - 40, ry + 3), "WIN", fill=GREEN, font=small_font)

    # Arrows from searchers to engine
    for i in range(3):
        ay = sy_start + i * (box_h + gap) + box_h // 2
        # Animated dash offset
        dash_offset = int(fi * 2) % 8
        for dx in range(0, eng_x - sx - box_w - 10, 8):
            if (dx + dash_offset) % 16 < 8:
                px = sx + box_w + 5 + dx
                d.line([(px, ay), (min(px + 6, eng_x - 5), ay)], fill=DIM, width=1)
        # Arrowhead
        d.polygon([(eng_x - 2, ay), (eng_x - 8, ay - 4), (eng_x - 8, ay + 4)], fill=DIM)

    # === RIGHT: Validator Block ===
    val_x, val_y = 460, 75
    val_w, val_h = 310, 210
    draw_rounded_rect(d, (val_x, val_y, val_x + val_w, val_y + val_h), PANEL, BORDER)
    d.text((val_x + 15, val_y + 8), "Validator Block", fill=YELLOW, font=header_font)

    # Block contents
    block_items = [
        ("Regular Tx 1", DIM),
        ("Regular Tx 2", DIM),
        ("Bundle: Arb DEX A->B", GREEN),
        ("Bundle: Tip 0.12 SOL", YELLOW),
        ("Regular Tx 3", DIM),
        ("Regular Tx 4", DIM),
    ]
    for i, (label, color) in enumerate(block_items):
        ty = val_y + 35 + i * 24
        is_bundle = "Bundle" in label
        bg = GREEN_BG if is_bundle else DARK_BOX
        bord_c = GREEN if is_bundle else BORDER
        draw_rounded_rect(d, (val_x + 15, ty, val_x + val_w - 15, ty + 19), bg, bord_c, r=3)
        d.text((val_x + 22, ty + 2), label, fill=color, font=small_font)

    # Arrow from engine to validator
    arr_y = eng_y + eng_h // 2
    d.line([(eng_x + eng_w + 3, arr_y), (val_x - 8, arr_y)], fill=GREEN, width=2)
    d.polygon([(val_x - 2, arr_y), (val_x - 8, arr_y - 5), (val_x - 8, arr_y + 5)], fill=GREEN)
    d.text((eng_x + eng_w + 6, arr_y - 16), "Winning", fill=GREEN, font=tiny_font)
    d.text((eng_x + eng_w + 6, arr_y - 5), "bundle", fill=GREEN, font=tiny_font)

    # === BOTTOM: Revenue comparison ===
    bot_y = 305
    bot_h = 120
    draw_rounded_rect(d, (30, bot_y, W - 30, bot_y + bot_h), PANEL, BORDER)
    d.text((50, bot_y + 8), "Validator Revenue Comparison", fill=YELLOW, font=header_font)

    # Two bars: without Jito vs with Jito
    bar_x = 220
    bar_max = 380
    bar_h = 22

    # Without Jito
    by1 = bot_y + 38
    d.text((50, by1 + 3), "Without Jito:", fill=DIM, font=small_font)
    w1 = int(bar_max * 0.55)
    draw_rounded_rect(d, (bar_x, by1, bar_x + w1, by1 + bar_h), CYAN_BG, lerp_color(BORDER, CYAN, 0.3), r=4)
    d.text((bar_x + 8, by1 + 4), "Block rewards only", fill=CYAN, font=small_font)
    d.text((bar_x + w1 + 8, by1 + 4), "1.2 SOL", fill=CYAN, font=small_font)

    # With Jito
    by2 = bot_y + 68
    d.text((50, by2 + 3), "With Jito:", fill=DIM, font=small_font)
    w2_base = int(bar_max * 0.55)
    w2_tip = int(bar_max * 0.20)
    # Base rewards
    draw_rounded_rect(d, (bar_x, by2, bar_x + w2_base, by2 + bar_h), CYAN_BG, lerp_color(BORDER, CYAN, 0.3), r=4)
    d.text((bar_x + 8, by2 + 4), "Block rewards", fill=CYAN, font=small_font)
    # Tips portion with pulse
    tip_col = lerp_color(YELLOW_BG, YELLOW, 0.2 + 0.15 * pulse)
    draw_rounded_rect(d, (bar_x + w2_base + 2, by2, bar_x + w2_base + w2_tip, by2 + bar_h),
                      tip_col, lerp_color(BORDER, YELLOW, 0.5), r=4)
    d.text((bar_x + w2_base + 8, by2 + 4), "+ Tips", fill=YELLOW, font=small_font)
    d.text((bar_x + w2_base + w2_tip + 8, by2 + 4), "1.65 SOL (+37%)", fill=GREEN, font=small_font)

    # === BOTTOM: Explanation rotation ===
    exp_y = 440
    draw_rounded_rect(d, (30, exp_y, W - 30, H - 14), PANEL, BORDER)
    explanations = [
        ("MEV = Maximal Extractable Value", "Profit from tx ordering: arbitrage, liquidations, sandwich attacks", CYAN),
        ("Bundle = Atomic Tx Group", "All-or-nothing execution -- if one tx fails, entire bundle reverts", GREEN),
        ("Tip Auction", "Searchers compete by tipping validators -- highest tip wins inclusion", YELLOW),
        ("Jito Block Engine", "Off-chain auction system that validators opt into for extra revenue", PURPLE),
    ]
    idx = (fi // 18) % len(explanations)
    et, ed, ec = explanations[idx]
    etw, _ = text_size(d, et, header_font)
    d.text(((W - etw) // 2, exp_y + 10), et, fill=ec, font=header_font)
    edw, _ = text_size(d, ed, body_font)
    d.text(((W - edw) // 2, exp_y + 32), ed, fill=DIM, font=body_font)

    # Animated tip flow dots (searcher B -> engine -> validator)
    dot_phase = (fi % 18) / 18.0
    # Path: searcher B center -> engine left -> engine right -> validator left
    path_points = [
        (sx + box_w, sy_start + 1 * (box_h + gap) + box_h // 2),
        (eng_x, eng_y + eng_h // 2),
        (eng_x + eng_w, eng_y + eng_h // 2),
        (val_x, eng_y + eng_h // 2),
    ]
    # Draw 3 dots along path
    for dot_i in range(3):
        dp = (dot_phase + dot_i * 0.33) % 1.0
        # Determine which segment
        seg = int(dp * 3)
        seg_t = (dp * 3) - seg
        if seg < len(path_points) - 1:
            x1, y1 = path_points[seg]
            x2, y2 = path_points[seg + 1]
            dx = int(x1 + (x2 - x1) * seg_t)
            dy = int(y1 + (y2 - y1) * seg_t)
            d.ellipse((dx - 3, dy - 3, dx + 3, dy + 3), fill=GREEN)

    return img


if __name__ == "__main__":
    frames = [make_frame(i) for i in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DUR, loop=0, optimize=True)
    print(f"Saved {OUT} ({len(frames)} frames)")
