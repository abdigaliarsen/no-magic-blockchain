"""
MEV & Flashbots: Mempool with pending txs, sandwich attack diagram,
block builder auction with 3 builders bidding, PBS flow.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 72
DELAY = 90
OUT = "assets/gifs/ethereum_13_mev_flashbots.gif"

CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
RED = (248, 113, 113)
PURPLE = (167, 139, 250)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)
BG = (13, 17, 23)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)

CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
YELLOW_BG = (58, 50, 14)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)
ORANGE_BG = (55, 35, 15)


def load_font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for n in names:
        for p in [f"/usr/share/fonts/truetype/dejavu/{n}", f"/usr/share/fonts/truetype/liberation/{n}", f"/usr/share/fonts/{n}"]:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
    return ImageFont.load_default()


font_title = load_font(26, bold=True)
font_header = load_font(15, bold=True)
font_body = load_font(13)
font_small = load_font(11)


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def draw_rounded_rect(draw, xy, fill, outline=None, radius=8):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def draw_arrow_h(draw, x1, x2, y, color, t_anim):
    """Horizontal arrow with animated dot."""
    draw.line((x1, y, x2, y), fill=DIM, width=2)
    direction = 1 if x2 > x1 else -1
    draw.polygon([(x2, y), (x2 - direction * 6, y - 4), (x2 - direction * 6, y + 4)], fill=color)
    dx = x1 + (x2 - x1) * (t_anim % 1.0)
    draw.ellipse((dx - 3, y - 3, dx + 3, y + 3), fill=color)


def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / (FRAMES - 1)

    # --- Title ---
    draw.text((30, 18), "MEV & Flashbots (PBS)", font=font_title, fill=WHITE)
    draw.line((30, 52, 770, 52), fill=BORDER, width=1)

    # === Left: Sandwich Attack ===
    draw.text((40, 62), "Sandwich Attack", font=font_header, fill=RED)

    # Mempool box
    mp_box = (40, 84, 370, 168)
    draw_rounded_rect(draw, mp_box, fill=DARK_BOX, outline=BORDER)
    draw.text((55, 88), "Public Mempool", font=font_body, fill=DIM)

    # Victim tx
    draw_rounded_rect(draw, (55, 108, 200, 130), fill=YELLOW_BG, outline=YELLOW)
    draw.text((62, 111), "Victim: swap 10 ETH", font=font_small, fill=YELLOW)

    # Sandwich txs
    pulse = 0.5 + 0.5 * math.sin(t * math.pi * 4)
    fr_color = lerp_color(DIM, RED, pulse)
    draw_rounded_rect(draw, (55, 136, 355, 162), fill=RED_BG, outline=RED)
    draw.text((62, 139), "Frontrun", font=font_small, fill=fr_color)
    draw.text((130, 139), "->", font=font_small, fill=DIM)
    draw.text((150, 139), "Victim", font=font_small, fill=YELLOW)
    draw.text((205, 139), "->", font=font_small, fill=DIM)
    draw.text((225, 139), "Backrun", font=font_small, fill=fr_color)
    draw.text((290, 139), "= profit", font=font_small, fill=RED)

    # === Right: Builder Auction ===
    draw.text((420, 62), "Block Builder Auction", font=font_header, fill=CYAN)

    builders = [
        ("Builder A", "2.1 ETH", CYAN),
        ("Builder B", "2.5 ETH", GREEN),
        ("Builder C", "1.8 ETH", PURPLE),
    ]

    # Rotating highlight: which builder is winning
    winner_idx = int(t * 3) % 3
    by = 84
    for i, (name, bid, color) in enumerate(builders):
        bg = CYAN_BG if i == winner_idx else DARK_BOX
        outline = color if i == winner_idx else BORDER
        box = (420, by, 760, by + 24)
        draw_rounded_rect(draw, box, fill=bg, outline=outline)
        draw.text((430, by + 4), name, font=font_small, fill=color)
        draw.text((530, by + 4), "bid: " + bid, font=font_small, fill=DIM)
        if i == winner_idx:
            draw.text((620, by + 4), "WINNING", font=font_small, fill=color)
        by += 30

    # === PBS Flow (middle section) ===
    draw.line((30, 180, 770, 180), fill=BORDER, width=1)
    draw.text((40, 188), "Proposer-Builder Separation (PBS)", font=font_header, fill=GREEN)

    flow_y = 215
    box_h = 55

    # Searcher
    s_box = (40, flow_y, 160, flow_y + box_h)
    draw_rounded_rect(draw, s_box, fill=RED_BG, outline=RED)
    draw.text((52, flow_y + 6), "Searcher", font=font_body, fill=RED)
    draw.text((52, flow_y + 24), "finds MEV", font=font_small, fill=DIM)
    draw.text((52, flow_y + 38), "bundles txs", font=font_small, fill=DIM)

    # Builder
    b_box = (210, flow_y, 350, flow_y + box_h)
    draw_rounded_rect(draw, b_box, fill=CYAN_BG, outline=CYAN)
    draw.text((222, flow_y + 6), "Builder", font=font_body, fill=CYAN)
    draw.text((222, flow_y + 24), "builds block", font=font_small, fill=DIM)
    draw.text((222, flow_y + 38), "bids for slot", font=font_small, fill=DIM)

    # Relay
    r_box = (400, flow_y, 530, flow_y + box_h)
    draw_rounded_rect(draw, r_box, fill=PURPLE_BG, outline=PURPLE)
    draw.text((415, flow_y + 6), "Relay", font=font_body, fill=PURPLE)
    draw.text((415, flow_y + 24), "escrows block", font=font_small, fill=DIM)
    draw.text((415, flow_y + 38), "trustless", font=font_small, fill=DIM)

    # Proposer
    p_box = (580, flow_y, 760, flow_y + box_h)
    draw_rounded_rect(draw, p_box, fill=GREEN_BG, outline=GREEN)
    draw.text((595, flow_y + 6), "Proposer", font=font_body, fill=GREEN)
    draw.text((595, flow_y + 24), "selects best bid", font=font_small, fill=DIM)
    draw.text((595, flow_y + 38), "signs header", font=font_small, fill=DIM)

    # Arrows: Searcher -> Builder -> Relay -> Proposer
    ary = flow_y + box_h // 2
    draw_arrow_h(draw, 165, 205, ary, RED, t * 3)
    draw_arrow_h(draw, 355, 395, ary, CYAN, t * 3 + 0.33)
    draw_arrow_h(draw, 535, 575, ary, PURPLE, t * 3 + 0.66)

    # Labels on arrows
    draw.text((168, ary - 14), "bundles", font=font_small, fill=DIM)
    draw.text((358, ary - 14), "block+bid", font=font_small, fill=DIM)
    draw.text((538, ary - 14), "header", font=font_small, fill=DIM)

    # === Bottom: MEV Supply Chain stats ===
    draw.line((30, flow_y + box_h + 20, 770, flow_y + box_h + 20), fill=BORDER, width=1)
    stat_y = flow_y + box_h + 30
    draw.text((40, stat_y), "MEV Supply Chain", font=font_header, fill=ORANGE)

    # Stat boxes
    stats = [
        ("MEV Types", "Arbitrage, Liquidation\nSandwich, Backrun", ORANGE, ORANGE_BG),
        ("Protection", "Private mempools\nMEV-Share refunds", GREEN, GREEN_BG),
        ("Revenue", "Searcher -> Builder\n-> Proposer (fees)", CYAN, CYAN_BG),
    ]

    sx = 40
    for label, desc, color, bg in stats:
        sbox = (sx, stat_y + 24, sx + 230, stat_y + 80)
        draw_rounded_rect(draw, sbox, fill=bg, outline=color)
        draw.text((sx + 10, stat_y + 28), label, font=font_body, fill=color)
        lines = desc.split("\n")
        for j, line in enumerate(lines):
            draw.text((sx + 10, stat_y + 46 + j * 14), line, font=font_small, fill=DIM)
        sx += 242

    # Animated MEV value
    mev_val = 0.5 + 2.0 * abs(math.sin(t * math.pi * 2))
    mev_pulse = lerp_color(DIM, ORANGE, 0.5 + 0.5 * math.sin(t * math.pi * 4))
    draw.text((40, stat_y + 92), f"Block MEV: {mev_val:.2f} ETH", font=font_small, fill=mev_pulse)

    # Bottom note
    draw.text((40, 530), "Flashbots: democratizing MEV extraction, reducing negative externalities", font=font_small, fill=DIM)

    return img


if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print(f"Saved {OUT}")
