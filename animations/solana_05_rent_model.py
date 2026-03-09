"""
Variant B: "Pay Rent or Die"
Two paths: rent-exempt account (lives forever) vs underfunded account
(rent collected each epoch, eventually purged). Timeline visual with
animated epoch scanner.
"""

from PIL import Image, ImageDraw, ImageFont
import math

W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/solana_05_rent_model.gif"

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

try:
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except Exception:
    font_title = ImageFont.load_default()
    font_header = font_title
    font_body = font_title
    font_small = font_title

NUM_EPOCHS = 8


def text_w(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # title
    title = "Pay Rent or Die"
    tw = text_w(d, title, font_title)
    d.text(((W - tw) // 2, 16), title, fill=WHITE, font=font_title)

    sub = "Two fates of a Solana account"
    sw = text_w(d, sub, font_body)
    d.text(((W - sw) // 2, 48), sub, fill=DIM, font=font_body)

    # scanning epoch position (cycles through 0..NUM_EPOCHS-1)
    scan_progress = (fi % FRAMES) / FRAMES  # 0..1
    scan_epoch = scan_progress * NUM_EPOCHS
    pulse = 0.5 + 0.5 * math.sin(fi * 2 * math.pi / 10)

    # --- TOP ROW: Rent-Exempt Account ---
    top_y = 85
    panel_h = 185

    # panel
    d.rounded_rectangle([30, top_y, W - 30, top_y + panel_h],
                        radius=8, fill=PANEL, outline=BORDER)

    # label
    d.text((50, top_y + 10), "Rent-Exempt Account", fill=GREEN, font=font_header)
    d.text((50, top_y + 28), "Balance: 0.00797 SOL  (>= minimum)", fill=DIM, font=font_small)

    # timeline
    tl_left = 60
    tl_right = W - 60
    tl_y = top_y + 70
    tl_w = tl_right - tl_left

    # timeline line
    d.line([(tl_left, tl_y), (tl_right, tl_y)], fill=BORDER, width=2)

    # epoch markers
    epoch_spacing = tl_w / (NUM_EPOCHS - 1)
    for i in range(NUM_EPOCHS):
        ex = tl_left + int(i * epoch_spacing)

        # epoch dot
        is_scanned = int(scan_epoch) >= i
        dot_col = GREEN if is_scanned else BORDER
        d.ellipse([ex - 6, tl_y - 6, ex + 6, tl_y + 6], fill=dot_col, outline=dot_col)

        # epoch label
        elbl = f"E{i}"
        elw = text_w(d, elbl, font_small)
        d.text((ex - elw // 2, tl_y + 12), elbl, fill=DIM, font=font_small)

        # balance stays the same
        bal = "0.00797"
        bw = text_w(d, bal, font_small)
        d.text((ex - bw // 2, tl_y + 26), bal, fill=GREEN, font=font_small)

    # scan line (top)
    scan_x = tl_left + int(scan_epoch / NUM_EPOCHS * tl_w)
    scan_col_top = (int(GREEN[0] * (0.5 + 0.5 * pulse)),
                    int(GREEN[1] * (0.5 + 0.5 * pulse)),
                    int(GREEN[2] * (0.5 + 0.5 * pulse)))
    d.line([(scan_x, tl_y - 20), (scan_x, tl_y + 45)], fill=scan_col_top, width=2)

    # status
    status_top = "STATUS: ALIVE -- no rent deducted"
    stw = text_w(d, status_top, font_body)
    d.text(((W - stw) // 2, top_y + panel_h - 30), status_top, fill=GREEN, font=font_body)

    # --- BOTTOM ROW: Underfunded Account ---
    bot_y = top_y + panel_h + 25
    panel_h2 = 210

    d.rounded_rectangle([30, bot_y, W - 30, bot_y + panel_h2],
                        radius=8, fill=PANEL, outline=BORDER)

    d.text((50, bot_y + 10), "Underfunded Account", fill=RED, font=font_header)
    d.text((50, bot_y + 28), "Balance: 0.00200 SOL  (< minimum)", fill=DIM, font=font_small)

    # timeline
    tl_y2 = bot_y + 70

    d.line([(tl_left, tl_y2), (tl_right, tl_y2)], fill=BORDER, width=2)

    # balance decreases each epoch until purged
    balances = [0.00200, 0.00172, 0.00144, 0.00116, 0.00088, 0.00060, 0.00032, 0.00000]
    purge_epoch = 7  # when balance hits 0

    for i in range(NUM_EPOCHS):
        ex = tl_left + int(i * epoch_spacing)
        is_scanned = int(scan_epoch) >= i
        bal = balances[i]

        # color gradient: yellow -> orange -> red -> dead
        if i < purge_epoch:
            t = i / purge_epoch
            if t < 0.5:
                dot_col = lerp_color(YELLOW, ORANGE, t * 2) if is_scanned else BORDER
                bal_col = lerp_color(YELLOW, ORANGE, t * 2)
            else:
                dot_col = lerp_color(ORANGE, RED, (t - 0.5) * 2) if is_scanned else BORDER
                bal_col = lerp_color(ORANGE, RED, (t - 0.5) * 2)
        else:
            dot_col = RED if is_scanned else BORDER
            bal_col = RED

        d.ellipse([ex - 6, tl_y2 - 6, ex + 6, tl_y2 + 6], fill=dot_col, outline=dot_col)

        # epoch label
        elbl = f"E{i}"
        elw = text_w(d, elbl, font_small)
        d.text((ex - elw // 2, tl_y2 + 12), elbl, fill=DIM, font=font_small)

        # balance
        if i < purge_epoch:
            btext = f"{bal:.5f}"
        else:
            btext = "PURGED"
        bw = text_w(d, btext, font_small)
        d.text((ex - bw // 2, tl_y2 + 26), btext, fill=bal_col, font=font_small)

        # rent deduction arrows between epochs
        if i < purge_epoch and i < NUM_EPOCHS - 1:
            ax1 = ex + 10
            ax2 = tl_left + int((i + 1) * epoch_spacing) - 10
            mid_x = (ax1 + ax2) // 2
            if is_scanned:
                d.text((mid_x - 12, tl_y2 - 20), "-rent", fill=ORANGE, font=font_small)

    # scan line (bottom)
    scan_x2 = tl_left + int(scan_epoch / NUM_EPOCHS * tl_w)
    scan_col_bot = (int(RED[0] * (0.5 + 0.5 * pulse)),
                    int(RED[1] * (0.5 + 0.5 * pulse)),
                    int(RED[2] * (0.5 + 0.5 * pulse)))
    d.line([(scan_x2, tl_y2 - 20), (scan_x2, tl_y2 + 45)], fill=scan_col_bot, width=2)

    # purge marker
    if int(scan_epoch) >= purge_epoch:
        px = tl_left + int(purge_epoch * epoch_spacing)
        # X mark
        d.line([(px - 8, tl_y2 - 8), (px + 8, tl_y2 + 8)], fill=RED, width=3)
        d.line([(px - 8, tl_y2 + 8), (px + 8, tl_y2 - 8)], fill=RED, width=3)

    # status
    current_epoch_idx = min(int(scan_epoch), NUM_EPOCHS - 1)
    if current_epoch_idx >= purge_epoch:
        status_bot = "STATUS: PURGED -- account deleted from state"
        sbc = RED
    else:
        status_bot = f"STATUS: DRAINING -- {balances[current_epoch_idx]:.5f} SOL remaining"
        sbc = ORANGE
    sbw = text_w(d, status_bot, font_body)
    d.text(((W - sbw) // 2, bot_y + panel_h2 - 30), status_bot, fill=sbc, font=font_body)

    # --- bottom note ---
    note = "Rent-exempt = 2 years of rent prepaid.  Below threshold = gradual deduction each epoch."
    nw = text_w(d, note, font_small)
    d.text(((W - nw) // 2, H - 25), note, fill=DIM, font=font_small)

    return img


frames = [draw_frame(i) for i in range(FRAMES)]
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0)
print(f"Saved {OUT}")
