"""BTC08-A: Payment Channel — Open, transact off-chain, close."""
from PIL import Image, ImageDraw, ImageFont
import math, os

W, H, FRAMES, DELAY = 800, 550, 36, 90
BG = (13, 17, 23)
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
PURPLE = (167, 139, 250)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)
RED = (248, 113, 113)
CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
PANEL = (17, 21, 28)
YELLOW_BG = (58, 50, 14)

def load_font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for n in names:
        for p in [f"/usr/share/fonts/truetype/dejavu/{n}", f"/usr/share/fonts/truetype/liberation/{n}", f"/usr/share/fonts/{n}"]:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except: pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(14, True)
body_font = load_font(12)
small_font = load_font(10)
mono_font = load_font(12)
big_font = load_font(18, True)

def text_w(draw, txt, font):
    bb = draw.textbbox((0,0), txt, font=font)
    return bb[2] - bb[0]

def draw_rounded_box(draw, x, y, w, h, fill, border_col, r=8):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=border_col, width=2)

def marching_hline(draw, x1, x2, y, color, frame, idx=0):
    dash_len = 6
    offset = (frame * 2 + idx * 5) % (dash_len * 2)
    direction = 1 if x2 > x1 else -1
    length = abs(x2 - x1)
    pos = offset % (dash_len * 2)
    while pos < length:
        sx = x1 + direction * pos
        ex = x1 + direction * min(pos + dash_len, length)
        draw.line([(sx, y), (ex, y)], fill=color, width=2)
        pos += dash_len * 2
    # arrowhead
    if direction > 0:
        draw.polygon([(x2, y), (x2-8, y-5), (x2-8, y+5)], fill=color)
    else:
        draw.polygon([(x2, y), (x2+8, y-5), (x2+8, y+5)], fill=color)

def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    pulse = 0.5 + 0.5 * math.sin(f * 2 * math.pi / FRAMES)

    title = "Lightning: Payment Channel"
    tw = text_w(draw, title, title_font)
    draw.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)

    # Three phases side by side
    phase_w = 230
    gap = 20
    start_x = 30

    # === Phase 1: Open Channel ===
    p1x = start_x
    p1y = 55
    draw_rounded_box(draw, p1x, p1y, phase_w, 200, PANEL, ORANGE)
    draw.text((p1x + 50, p1y + 8), "1. OPEN", fill=ORANGE, font=header_font)
    draw.text((p1x + 10, p1y + 30), "On-Chain Funding Tx", fill=DIM, font=small_font)

    # Alice and Bob with funding
    alice_x, alice_y = p1x + 30, p1y + 55
    bob_x, bob_y = p1x + 140, p1y + 55
    draw_rounded_box(draw, alice_x, alice_y, 60, 30, CYAN_BG, CYAN, 4)
    draw.text((alice_x + 8, alice_y + 7), "Alice", fill=CYAN, font=small_font)
    draw_rounded_box(draw, bob_x, bob_y, 60, 30, GREEN_BG, GREEN, 4)
    draw.text((bob_x + 12, bob_y + 7), "Bob", fill=GREEN, font=small_font)

    # Funding tx
    fund_y = p1y + 105
    draw_rounded_box(draw, p1x + 30, fund_y, 170, 35, DARK_BOX, YELLOW, 4)
    draw.text((p1x + 40, fund_y + 3), "Funding Tx", fill=YELLOW, font=body_font)
    draw.text((p1x + 40, fund_y + 18), "5 BTC + 5 BTC = 10 BTC", fill=DIM, font=small_font)

    # Arrows to funding
    marching_hline(draw, alice_x + 30, p1x + 115, alice_y + 30 + 18, CYAN, f, 0)
    marching_hline(draw, bob_x + 30, p1x + 115, bob_y + 30 + 18, GREEN, f, 1)

    # Blockchain
    chain_y = p1y + 155
    glow_o = tuple(int(c * (0.5 + 0.5 * pulse)) for c in ORANGE)
    draw_rounded_box(draw, p1x + 40, chain_y, 150, 28, DARK_BOX, glow_o, 4)
    draw.text((p1x + 55, chain_y + 6), "Blockchain", fill=ORANGE, font=body_font)

    # === Phase 2: Transact Off-Chain ===
    p2x = start_x + phase_w + gap
    p2y = 55
    draw_rounded_box(draw, p2x, p2y, phase_w, 200, PANEL, PURPLE)
    draw.text((p2x + 30, p2y + 8), "2. TRANSACT", fill=PURPLE, font=header_font)
    draw.text((p2x + 10, p2y + 30), "Off-Chain (instant!)", fill=DIM, font=small_font)

    # Alice and Bob
    a2x, a2y = p2x + 20, p2y + 55
    b2x, b2y = p2x + 150, p2y + 55
    draw_rounded_box(draw, a2x, a2y, 60, 30, CYAN_BG, CYAN, 4)
    draw.text((a2x + 8, a2y + 7), "Alice", fill=CYAN, font=small_font)
    draw_rounded_box(draw, b2x, b2y, 60, 30, GREEN_BG, GREEN, 4)
    draw.text((b2x + 12, b2y + 7), "Bob", fill=GREEN, font=small_font)

    # Animated payments back and forth
    pay_y = p2y + 100
    # Payment direction alternates
    cycle = (f * 4 // FRAMES) % 4
    payments = [
        ("Pay 1 BTC -->", CYAN, a2x + 60, b2x),
        ("<-- Pay 0.5 BTC", GREEN, b2x, a2x + 60),
        ("Pay 2 BTC -->", CYAN, a2x + 60, b2x),
        ("<-- Pay 0.3 BTC", GREEN, b2x, a2x + 60),
    ]
    for i, (lbl, col, fx, tx) in enumerate(payments):
        py = pay_y + i * 22
        alpha = 1.0 if i == cycle else 0.4
        pcol = tuple(int(c * alpha) for c in col)
        draw.text((p2x + 15, py), lbl, fill=pcol, font=small_font)

    # Balance state
    bal_y = p2y + 158
    # Cycling balances
    balances = [(5,5), (4,6), (4.5,5.5), (2.5,7.5), (2.8,7.2)]
    bal_idx = (f * len(balances) // FRAMES) % len(balances)
    a_bal, b_bal = balances[bal_idx]
    draw.text((p2x + 10, bal_y), f"A:{a_bal:.1f}", fill=CYAN, font=mono_font)
    draw.text((p2x + 80, bal_y), "|", fill=DIM, font=mono_font)
    draw.text((p2x + 100, bal_y), f"B:{b_bal:.1f}", fill=GREEN, font=mono_font)
    draw.text((p2x + 160, bal_y), "BTC", fill=DIM, font=small_font)
    draw.text((p2x + 10, bal_y + 18), "No blockchain needed!", fill=YELLOW, font=small_font)

    # === Phase 3: Close ===
    p3x = start_x + 2 * (phase_w + gap)
    p3y = 55
    draw_rounded_box(draw, p3x, p3y, phase_w, 200, PANEL, GREEN)
    draw.text((p3x + 55, p3y + 8), "3. CLOSE", fill=GREEN, font=header_font)
    draw.text((p3x + 10, p3y + 30), "On-Chain Settlement", fill=DIM, font=small_font)

    # Final balances
    a3x, a3y = p3x + 20, p3y + 55
    b3x, b3y = p3x + 150, p3y + 55
    draw_rounded_box(draw, a3x, a3y, 60, 30, CYAN_BG, CYAN, 4)
    draw.text((a3x + 8, a3y + 7), "Alice", fill=CYAN, font=small_font)
    draw.text((a3x + 8, a3y + 32), "2.8 BTC", fill=CYAN, font=small_font)
    draw_rounded_box(draw, b3x, b3y, 60, 30, GREEN_BG, GREEN, 4)
    draw.text((b3x + 12, b3y + 7), "Bob", fill=GREEN, font=small_font)
    draw.text((b3x + 8, b3y + 32), "7.2 BTC", fill=GREEN, font=small_font)

    # Settlement tx
    set_y = p3y + 115
    draw_rounded_box(draw, p3x + 20, set_y, 190, 30, DARK_BOX, GREEN, 4)
    draw.text((p3x + 30, set_y + 7), "Settlement Tx", fill=GREEN, font=body_font)

    # Blockchain
    chain3_y = p3y + 158
    draw_rounded_box(draw, p3x + 40, chain3_y, 150, 28, DARK_BOX, glow_o, 4)
    draw.text((p3x + 55, chain3_y + 6), "Blockchain", fill=ORANGE, font=body_font)

    # === Key Insight Box ===
    insight_y = 275
    draw_rounded_box(draw, 30, insight_y, 740, 65, YELLOW_BG, YELLOW)
    draw.text((50, insight_y + 8), "KEY INSIGHT:", fill=YELLOW, font=big_font)
    draw.text((250, insight_y + 10), "Only 2 on-chain transactions for", fill=WHITE, font=header_font)
    draw.text((250, insight_y + 30), "UNLIMITED off-chain payments!", fill=GREEN, font=header_font)
    draw.text((50, insight_y + 48), "Each off-chain payment: instant, nearly free, private", fill=DIM, font=body_font)

    # === Stats comparison ===
    stat_y = 360
    draw_rounded_box(draw, 30, stat_y, 350, 170, PANEL, RED)
    draw.text((50, stat_y + 8), "On-Chain (every payment):", fill=RED, font=header_font)
    stats_l = [
        ("Speed:", "~10 min confirmation"),
        ("Fee:", "~$2-50 per tx"),
        ("Capacity:", "~7 tx/sec"),
        ("Privacy:", "All txs public"),
        ("Cost for 100 txs:", "~$500+"),
    ]
    for i, (k, v) in enumerate(stats_l):
        draw.text((50, stat_y + 30 + i * 22), k, fill=RED, font=body_font)
        draw.text((140, stat_y + 30 + i * 22), v, fill=WHITE, font=body_font)

    draw_rounded_box(draw, 420, stat_y, 350, 170, PANEL, GREEN)
    draw.text((440, stat_y + 8), "Lightning Channel:", fill=GREEN, font=header_font)
    stats_r = [
        ("Speed:", "< 1 second"),
        ("Fee:", "< $0.01"),
        ("Capacity:", "Millions tx/sec"),
        ("Privacy:", "Only endpoints know"),
        ("Cost for 100 txs:", "< $1 total"),
    ]
    for i, (k, v) in enumerate(stats_r):
        draw.text((440, stat_y + 30 + i * 22), k, fill=GREEN, font=body_font)
        glow_w = tuple(int(c * (0.7 + 0.3 * pulse)) for c in WHITE)
        draw.text((530, stat_y + 30 + i * 22), v, fill=glow_w, font=body_font)

    return img

frames = [make_frame(f) for f in range(FRAMES)]
frames[0].save("assets/gifs/bitcoin_08_simplified_lightning.gif", save_all=True, append_images=frames[1:], duration=DELAY, loop=0)
print("Saved assets/gifs/bitcoin_08_simplified_lightning.gif")
