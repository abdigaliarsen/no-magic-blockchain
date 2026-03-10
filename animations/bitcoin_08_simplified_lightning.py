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
                except (OSError, IOError): pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(15, True)
body_font = load_font(13)
small_font = load_font(11)
mono_font = load_font(13)
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

    # Three phases side by side — wider panels, more spacing
    phase_w = 225
    gap = 25
    total_w = 3 * phase_w + 2 * gap
    start_x = (W - total_w) // 2
    phase_h = 210

    # === Phase 1: Open Channel ===
    p1x = start_x
    p1y = 55
    draw_rounded_box(draw, p1x, p1y, phase_w, phase_h, PANEL, ORANGE)
    lbl = "1. OPEN"
    lbl_w = text_w(draw, lbl, header_font)
    draw.text((p1x + (phase_w - lbl_w) // 2, p1y + 8), lbl, fill=ORANGE, font=header_font)
    sub = "On-Chain Funding Tx"
    sub_w = text_w(draw, sub, small_font)
    draw.text((p1x + (phase_w - sub_w) // 2, p1y + 30), sub, fill=DIM, font=small_font)

    # Alice and Bob with funding
    alice_x, alice_y = p1x + 25, p1y + 55
    bob_x, bob_y = p1x + 140, p1y + 55
    draw_rounded_box(draw, alice_x, alice_y, 60, 30, CYAN_BG, CYAN, 4)
    draw.text((alice_x + 8, alice_y + 7), "Alice", fill=CYAN, font=small_font)
    draw_rounded_box(draw, bob_x, bob_y, 60, 30, GREEN_BG, GREEN, 4)
    draw.text((bob_x + 12, bob_y + 7), "Bob", fill=GREEN, font=small_font)

    # Funding tx
    fund_y = p1y + 110
    draw_rounded_box(draw, p1x + 25, fund_y, 175, 38, DARK_BOX, YELLOW, 4)
    ft = "Funding Tx"
    ft_w = text_w(draw, ft, body_font)
    draw.text((p1x + 25 + (175 - ft_w) // 2, fund_y + 3), ft, fill=YELLOW, font=body_font)
    fs = "5 BTC + 5 BTC = 10 BTC"
    fs_w = text_w(draw, fs, small_font)
    draw.text((p1x + 25 + (175 - fs_w) // 2, fund_y + 20), fs, fill=DIM, font=small_font)

    # Arrows to funding
    mid_fund = p1x + 25 + 87
    marching_hline(draw, alice_x + 30, mid_fund, alice_y + 30 + 18, CYAN, f, 0)
    marching_hline(draw, bob_x + 30, mid_fund, bob_y + 30 + 18, GREEN, f, 1)

    # Blockchain
    chain_y = p1y + 165
    glow_o = tuple(int(c * (0.5 + 0.5 * pulse)) for c in ORANGE)
    draw_rounded_box(draw, p1x + 35, chain_y, 155, 28, DARK_BOX, glow_o, 4)
    bc = "Blockchain"
    bc_w = text_w(draw, bc, body_font)
    draw.text((p1x + 35 + (155 - bc_w) // 2, chain_y + 6), bc, fill=ORANGE, font=body_font)

    # === Phase 2: Transact Off-Chain ===
    p2x = start_x + phase_w + gap
    p2y = 55
    draw_rounded_box(draw, p2x, p2y, phase_w, phase_h, PANEL, PURPLE)
    lbl2 = "2. TRANSACT"
    lbl2_w = text_w(draw, lbl2, header_font)
    draw.text((p2x + (phase_w - lbl2_w) // 2, p2y + 8), lbl2, fill=PURPLE, font=header_font)
    sub2 = "Off-Chain (instant!)"
    sub2_w = text_w(draw, sub2, small_font)
    draw.text((p2x + (phase_w - sub2_w) // 2, p2y + 30), sub2, fill=DIM, font=small_font)

    # Alice and Bob
    a2x, a2y = p2x + 15, p2y + 55
    b2x, b2y = p2x + 150, p2y + 55
    draw_rounded_box(draw, a2x, a2y, 60, 30, CYAN_BG, CYAN, 4)
    draw.text((a2x + 8, a2y + 7), "Alice", fill=CYAN, font=small_font)
    draw_rounded_box(draw, b2x, b2y, 60, 30, GREEN_BG, GREEN, 4)
    draw.text((b2x + 12, b2y + 7), "Bob", fill=GREEN, font=small_font)

    # Simplified: only 2 payment steps with more spacing
    pay_y = p2y + 100
    cycle = (f * 2 // FRAMES) % 2
    payments = [
        ("Pay 2 BTC  -->", CYAN, a2x + 60, b2x),
        ("<--  Pay 0.5 BTC", GREEN, b2x, a2x + 60),
    ]
    for i, (lbl, col, fx, tx) in enumerate(payments):
        py = pay_y + i * 30  # more vertical spacing (was 22)
        alpha = 1.0 if i == cycle else 0.35
        pcol = tuple(int(c * alpha) for c in col)
        lbl_w = text_w(draw, lbl, body_font)
        draw.text((p2x + (phase_w - lbl_w) // 2, py), lbl, fill=pcol, font=body_font)

    # Balance state — placed with clear separation
    bal_y = p2y + 170
    # Cycling balances (fewer steps matching 2 payments)
    balances = [(5.0, 5.0), (3.0, 7.0), (3.5, 6.5)]
    bal_idx = (f * len(balances) // FRAMES) % len(balances)
    a_bal, b_bal = balances[bal_idx]
    bal_str = f"A: {a_bal:.1f} BTC  |  B: {b_bal:.1f} BTC"
    bal_w = text_w(draw, bal_str, mono_font)
    bx = p2x + (phase_w - bal_w) // 2
    # Draw a subtle background so text is always readable
    draw_rounded_box(draw, bx - 8, bal_y - 3, bal_w + 16, 22, DARK_BOX, PURPLE_BG, 4)
    # Draw the balance text in parts for coloring
    draw.text((bx, bal_y), f"A: {a_bal:.1f}", fill=CYAN, font=mono_font)
    sep_x = bx + text_w(draw, f"A: {a_bal:.1f} ", mono_font)
    draw.text((sep_x, bal_y), "BTC  |  ", fill=DIM, font=mono_font)
    b_x = sep_x + text_w(draw, "BTC  |  ", mono_font)
    draw.text((b_x, bal_y), f"B: {b_bal:.1f}", fill=GREEN, font=mono_font)
    btc_x = b_x + text_w(draw, f"B: {b_bal:.1f} ", mono_font)
    draw.text((btc_x, bal_y), "BTC", fill=DIM, font=mono_font)

    # === Phase 3: Close ===
    p3x = start_x + 2 * (phase_w + gap)
    p3y = 55
    draw_rounded_box(draw, p3x, p3y, phase_w, phase_h, PANEL, GREEN)
    lbl3 = "3. CLOSE"
    lbl3_w = text_w(draw, lbl3, header_font)
    draw.text((p3x + (phase_w - lbl3_w) // 2, p3y + 8), lbl3, fill=GREEN, font=header_font)
    sub3 = "On-Chain Settlement"
    sub3_w = text_w(draw, sub3, small_font)
    draw.text((p3x + (phase_w - sub3_w) // 2, p3y + 30), sub3, fill=DIM, font=small_font)

    # Final balances
    a3x, a3y = p3x + 15, p3y + 55
    b3x, b3y = p3x + 150, p3y + 55
    draw_rounded_box(draw, a3x, a3y, 60, 30, CYAN_BG, CYAN, 4)
    draw.text((a3x + 8, a3y + 7), "Alice", fill=CYAN, font=small_font)
    draw.text((a3x + 5, a3y + 35), "3.5 BTC", fill=CYAN, font=body_font)
    draw_rounded_box(draw, b3x, b3y, 60, 30, GREEN_BG, GREEN, 4)
    draw.text((b3x + 12, b3y + 7), "Bob", fill=GREEN, font=small_font)
    draw.text((b3x + 5, b3y + 35), "6.5 BTC", fill=GREEN, font=body_font)

    # Settlement tx
    set_y = p3y + 120
    draw_rounded_box(draw, p3x + 15, set_y, 195, 32, DARK_BOX, GREEN, 4)
    st = "Settlement Tx"
    st_w = text_w(draw, st, body_font)
    draw.text((p3x + 15 + (195 - st_w) // 2, set_y + 7), st, fill=GREEN, font=body_font)

    # Blockchain
    chain3_y = p3y + 168
    draw_rounded_box(draw, p3x + 30, chain3_y, 165, 28, DARK_BOX, glow_o, 4)
    bc3 = "Blockchain"
    bc3_w = text_w(draw, bc3, body_font)
    draw.text((p3x + 30 + (165 - bc3_w) // 2, chain3_y + 6), bc3, fill=ORANGE, font=body_font)

    # === Comparison Table ===
    stat_y = 280
    col_w = 355
    col_gap = 30
    col_h = 155
    left_x = (W - 2 * col_w - col_gap) // 2
    right_x = left_x + col_w + col_gap

    # Left: On-Chain
    draw_rounded_box(draw, left_x, stat_y, col_w, col_h, PANEL, RED)
    oc = "On-Chain"
    oc_w = text_w(draw, oc, header_font)
    draw.text((left_x + (col_w - oc_w) // 2, stat_y + 8), oc, fill=RED, font=header_font)

    stats_l = [
        ("Speed:", "~10 min"),
        ("Fee:", "~$2-50 per tx"),
        ("100 txs:", "~$500+"),
    ]
    row_h = 30
    for i, (k, v) in enumerate(stats_l):
        ry = stat_y + 35 + i * row_h
        draw.text((left_x + 20, ry), k, fill=RED, font=body_font)
        draw.text((left_x + 120, ry), v, fill=WHITE, font=body_font)

    # Right: Lightning
    draw_rounded_box(draw, right_x, stat_y, col_w, col_h, PANEL, GREEN)
    lc = "Lightning"
    lc_w = text_w(draw, lc, header_font)
    draw.text((right_x + (col_w - lc_w) // 2, stat_y + 8), lc, fill=GREEN, font=header_font)

    stats_r = [
        ("Speed:", "< 1 second"),
        ("Fee:", "< $0.01"),
        ("100 txs:", "< $1 total"),
    ]
    for i, (k, v) in enumerate(stats_r):
        ry = stat_y + 35 + i * row_h
        draw.text((right_x + 20, ry), k, fill=GREEN, font=body_font)
        glow_w = tuple(int(c * (0.7 + 0.3 * pulse)) for c in WHITE)
        draw.text((right_x + 130, ry), v, fill=glow_w, font=body_font)

    # Key insight at bottom
    ins = "Only 2 on-chain txs for unlimited off-chain payments"
    ins_w = text_w(draw, ins, body_font)
    draw.text(((W - ins_w) // 2, 450), ins, fill=YELLOW, font=body_font)
    ins2 = "Instant + near-free"
    ins2_w = text_w(draw, ins2, body_font)
    draw.text(((W - ins2_w) // 2, 470), ins2, fill=GREEN, font=body_font)

    return img

if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save("assets/gifs/bitcoin_08_simplified_lightning.gif", save_all=True,
                   append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_08_simplified_lightning.gif")
