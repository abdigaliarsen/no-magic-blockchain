"""Bitcoin Stratum V2 animation — pool-miner job distribution and rewards."""
from PIL import Image, ImageDraw, ImageFont
import math, os

W, H, FRAMES, DUR = 800, 550, 36, 90
BG = (13, 17, 23)
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
RED = (248, 113, 113)
PURPLE = (167, 139, 250)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)
CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)

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

def draw_rounded_rect(draw, xy, fill, outline, r=8):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)

def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * max(0, min(1, t))) for a, b in zip(c1, c2))

def draw_marching_arrow(draw, x0, y0, x1, y1, color, frame, thickness=2):
    draw.line([(x0, y0), (x1, y1)], fill=color, width=thickness)
    dash_len = 8
    total = math.hypot(x1 - x0, y1 - y0)
    if total == 0: return
    dx, dy = (x1 - x0) / total, (y1 - y0) / total
    offset = (frame * 3) % (dash_len * 2)
    d = -offset
    while d < total:
        s = max(0, d)
        e = min(total, d + dash_len)
        if e > s:
            draw.line([(x0 + dx * s, y0 + dy * s), (x0 + dx * e, y0 + dy * e)], fill=WHITE, width=thickness)
        d += dash_len * 2
    draw.polygon([(x1, y1), (x1 - dx * 10 - dy * 5, y1 - dy * 10 + dx * 5),
                  (x1 - dx * 10 + dy * 5, y1 - dy * 10 - dx * 5)], fill=color)

# Miner positions around the pool (5 miners)
POOL_CX, POOL_CY = 400, 195
MINERS = [
    {"label": "Miner 1", "x": 100, "y": 105, "hash": 32, "color": CYAN},
    {"label": "Miner 2", "x": 100, "y": 230, "hash": 25, "color": GREEN},
    {"label": "Miner 3", "x": 700, "y": 105, "hash": 18, "color": YELLOW},
    {"label": "Miner 4", "x": 700, "y": 195, "hash": 15, "color": ORANGE},
    {"label": "Miner 5", "x": 700, "y": 285, "hash": 10, "color": PURPLE},
]

frames = []
for f in range(FRAMES):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / FRAMES
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

    # Title
    draw.text((W // 2, 20), "Stratum V2: Mining Pool", fill=CYAN, font=title_font, anchor="mt")
    draw.text((W // 2, 48), "Decentralized job negotiation + encrypted shares", fill=DIM, font=body_font, anchor="mt")

    # --- POOL (center) ---
    pw, ph = 170, 80
    pool_glow = lerp_color(CYAN_BG, CYAN, pulse * 0.2)
    draw_rounded_rect(draw, (POOL_CX - pw // 2, POOL_CY - ph // 2,
                              POOL_CX + pw // 2, POOL_CY + ph // 2), CYAN_BG, pool_glow)
    draw.text((POOL_CX, POOL_CY - 18), "MINING POOL", fill=CYAN, font=header_font, anchor="mt")
    draw.text((POOL_CX, POOL_CY + 2), "Job Negotiation", fill=DIM, font=small_font, anchor="mt")
    draw.text((POOL_CX, POOL_CY + 18), "Encrypted Channel", fill=DIM, font=small_font, anchor="mt")

    # --- MINERS ---
    for i, m in enumerate(MINERS):
        mx, my = m["x"], m["y"]
        mw, mh = 110, 48
        col = m["color"]
        bg = lerp_color(DARK_BOX, col, 0.08)
        draw_rounded_rect(draw, (mx - mw // 2, my - mh // 2, mx + mw // 2, my + mh // 2), bg, col, r=6)
        draw.text((mx, my - 10), m["label"], fill=col, font=small_font, anchor="mt")
        draw.text((mx, my + 8), f"{m['hash']} TH/s", fill=DIM, font=small_font, anchor="mt")

    # Arrows: pool -> miners (job distribution, outward)
    # Arrows alternate direction based on frame half: first half = jobs out, second half = shares in
    phase = (f % 18) < 9  # True = jobs out, False = shares in
    for m in MINERS:
        mx, my = m["x"], m["y"]
        # Connect to pool edge
        dx = mx - POOL_CX
        dy = my - POOL_CY
        dist = math.hypot(dx, dy)
        if dist == 0: continue
        # Pool edge point
        px = POOL_CX + dx / dist * 88
        py = POOL_CY + dy / dist * 42
        # Miner edge point
        ex = mx - dx / dist * 58
        ey = my - dy / dist * 26

        if phase:
            draw_marching_arrow(draw, int(px), int(py), int(ex), int(ey), YELLOW, f)
        else:
            draw_marching_arrow(draw, int(ex), int(ey), int(px), int(py), GREEN, f)

    # Phase label
    if phase:
        draw.text((POOL_CX, POOL_CY + 55), "Jobs Out", fill=YELLOW, font=small_font, anchor="mt")
    else:
        draw.text((POOL_CX, POOL_CY + 55), "Shares In", fill=GREEN, font=small_font, anchor="mt")

    # --- PPLNS REWARD BAR CHART ---
    draw_rounded_rect(draw, (40, 320, 460, 445), PANEL, BORDER)
    draw.text((250, 332), "PPLNS Reward Distribution", fill=WHITE, font=header_font, anchor="mt")

    total_hash = sum(m["hash"] for m in MINERS)
    bar_area_x = 60
    bar_area_y = 355
    bar_max_w = 280
    bar_h = 14
    bar_gap = 4

    for i, m in enumerate(MINERS):
        by = bar_area_y + i * (bar_h + bar_gap)
        share = m["hash"] / total_hash
        bw = int(bar_max_w * share)
        col = m["color"]
        draw_rounded_rect(draw, (bar_area_x, by, bar_area_x + bw, by + bar_h),
                          lerp_color(DARK_BOX, col, 0.5 + pulse * 0.2), col, r=3)
        draw.text((bar_area_x + bw + 8, by), f"{share * 100:.0f}%", fill=col, font=small_font)
        draw.text((bar_area_x + bw + 42, by), f"{share * 3.125:.3f} BTC", fill=DIM, font=small_font)

    # --- V1 vs V2 comparison ---
    draw_rounded_rect(draw, (480, 320, 760, 445), PANEL, BORDER)
    draw.text((620, 332), "V1 vs V2", fill=WHITE, font=header_font, anchor="mt")

    # V1 badge
    draw_rounded_rect(draw, (495, 354, 615, 404), RED_BG, RED, r=6)
    draw.text((555, 362), "Stratum V1", fill=RED, font=small_font, anchor="mt")
    v1_items = ["Plaintext", "Pool picks txs", "No encryption"]
    for j, item in enumerate(v1_items):
        draw.text((555, 378 + j * 12), item if j == 0 else "", fill=DIM, font=small_font, anchor="mt")
    draw.text((555, 380), "Pool controls block", fill=DIM, font=small_font, anchor="mt")
    draw.text((555, 393), "template (centralized)", fill=DIM, font=small_font, anchor="mt")

    # V2 badge
    draw_rounded_rect(draw, (630, 354, 750, 404), GREEN_BG, GREEN, r=6)
    draw.text((690, 362), "Stratum V2", fill=GREEN, font=small_font, anchor="mt")
    draw.text((690, 380), "Miners pick txs", fill=DIM, font=small_font, anchor="mt")
    draw.text((690, 393), "Encrypted + auth", fill=DIM, font=small_font, anchor="mt")

    # V2 advantages
    v2_adv = [
        ("Miner tx selection", GREEN),
        ("AEAD encryption", CYAN),
        ("Binary protocol (fast)", YELLOW),
    ]
    for j, (txt, col) in enumerate(v2_adv):
        draw.text((500, 412 + j * 12), "+", fill=col, font=small_font)
        draw.text((513, 412 + j * 12), txt, fill=col, font=small_font)

    # --- BOTTOM ---
    draw_rounded_rect(draw, (40, 458, 760, 535), DARK_BOX, BORDER)
    draw.text((400, 470), "Stratum V2 Protocol Flow", fill=PURPLE, font=header_font, anchor="mt")
    draw.text((60, 490), "1. Pool sends mining job template to miners (or miners propose their own)", fill=DIM, font=body_font)
    draw.text((60, 508), "2. Miners submit shares over encrypted channel", fill=DIM, font=body_font)
    draw.text((60, 524), "3. Rewards distributed proportionally via PPLNS (Pay Per Last N Shares)", fill=DIM, font=small_font)

    # Scan line
    scan_y = int(70 + (t * 460) % 460)
    draw.line([(0, scan_y), (W, scan_y)], fill=(*CYAN[:3], 20), width=1)

    frames.append(img)

if __name__ == "__main__":
    frames[0].save("assets/gifs/bitcoin_16_stratum_v2.gif", save_all=True, append_images=frames[1:], duration=DUR, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_16_stratum_v2.gif")
