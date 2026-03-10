"""
Account Abstraction (ERC-4337): EOA vs Smart Account comparison,
UserOp flow through Bundler -> EntryPoint -> Smart Account,
Paymaster sponsoring gas, social recovery with guardian icons.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/ethereum_12_account_abstraction.gif"

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


def draw_arrow_h(draw, x1, x2, y, color, t_anim, dot_color=None):
    """Horizontal arrow with animated dot."""
    draw.line((x1, y, x2, y), fill=DIM, width=2)
    direction = 1 if x2 > x1 else -1
    draw.polygon([(x2, y), (x2 - direction * 6, y - 4), (x2 - direction * 6, y + 4)], fill=color)
    dx = x1 + (x2 - x1) * (t_anim % 1.0)
    dc = dot_color or color
    draw.ellipse((dx - 3, y - 3, dx + 3, y + 3), fill=dc)


def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / (FRAMES - 1)

    # --- Title ---
    draw.text((30, 18), "Account Abstraction (ERC-4337)", font=font_title, fill=WHITE)
    draw.line((30, 52, 770, 52), fill=BORDER, width=1)

    # --- Top: EOA vs Smart Account comparison ---
    draw.text((40, 62), "EOA (Traditional)", font=font_header, fill=RED)
    draw.text((420, 62), "Smart Account (AA)", font=font_header, fill=GREEN)

    # EOA box
    eoa_box = (40, 84, 370, 168)
    draw_rounded_rect(draw, eoa_box, fill=RED_BG, outline=RED)
    eoa_items = [
        "Single private key",
        "Must hold ETH for gas",
        "No recovery if key lost",
        "ECDSA only",
    ]
    ey = 90
    for item in eoa_items:
        draw.text((55, ey), "x  " + item, font=font_small, fill=RED)
        ey += 18

    # Smart Account box
    sa_box = (420, 84, 760, 168)
    draw_rounded_rect(draw, sa_box, fill=GREEN_BG, outline=GREEN)
    sa_items = [
        "Custom validation logic",
        "Paymaster sponsors gas",
        "Social recovery",
        "Any signature scheme",
    ]
    sy = 90
    for item in sa_items:
        draw.text((435, sy), "+  " + item, font=font_small, fill=GREEN)
        sy += 18

    # --- Middle: UserOp flow ---
    draw.line((30, 180, 770, 180), fill=BORDER, width=1)
    draw.text((40, 188), "UserOperation Flow", font=font_header, fill=CYAN)

    # Flow boxes: User -> Bundler -> EntryPoint -> SmartAccount
    flow_y = 215
    box_h = 62
    boxes = [
        ("User", "sends UserOp", CYAN, CYAN_BG, 40, 155),
        ("Bundler", "batches UserOps", YELLOW, YELLOW_BG, 195, 155),
        ("EntryPoint", "validates + exec", ORANGE, DARK_BOX, 390, 155),
        ("Smart Acct", "custom logic", GREEN, GREEN_BG, 585, 155),
    ]

    for label, desc, color, bg, bx, bw in boxes:
        box = (bx, flow_y, bx + bw, flow_y + box_h)
        draw_rounded_rect(draw, box, fill=bg, outline=color)
        draw.text((bx + 10, flow_y + 8), label, font=font_body, fill=color)
        draw.text((bx + 10, flow_y + 28), desc, font=font_small, fill=DIM)
        # UserOp fields for first box
        if label == "User":
            draw.text((bx + 10, flow_y + 44), "nonce, callData", font=font_small, fill=DIM)

    # Arrows between boxes (User->Bundler->EntryPoint->SmartAcct)
    arrow_y = flow_y + box_h // 2
    draw_arrow_h(draw, 160, 190, arrow_y, CYAN, (t * 3))
    draw_arrow_h(draw, 355, 385, arrow_y, YELLOW, (t * 3 + 0.33))
    draw_arrow_h(draw, 550, 580, arrow_y, ORANGE, (t * 3 + 0.66))

    # --- Paymaster (below flow, connected to EntryPoint) ---
    pm_y = flow_y + box_h + 20
    pm_box = (390, pm_y, 545, pm_y + 48)
    draw_rounded_rect(draw, pm_box, fill=PURPLE_BG, outline=PURPLE)
    draw.text((405, pm_y + 6), "Paymaster", font=font_body, fill=PURPLE)
    draw.text((405, pm_y + 26), "sponsors gas fees", font=font_small, fill=DIM)

    # Arrow from Paymaster up to EntryPoint
    ep_cx = 467
    draw.line((ep_cx, pm_y, ep_cx, flow_y + box_h), fill=PURPLE, width=2)
    draw.polygon([(ep_cx, flow_y + box_h), (ep_cx - 4, flow_y + box_h + 6), (ep_cx + 4, flow_y + box_h + 6)], fill=PURPLE)
    # Animated dot
    dot_y = pm_y - (pm_y - flow_y - box_h) * ((t * 2) % 1.0)
    draw.ellipse((ep_cx - 3, dot_y - 3, ep_cx + 3, dot_y + 3), fill=PURPLE)

    # Gas label with pulse
    pulse = 0.5 + 0.5 * math.sin(t * math.pi * 4)
    gas_color = lerp_color(DIM, PURPLE, pulse)
    draw.text((550, pm_y + 14), "pays ETH", font=font_small, fill=gas_color)

    # --- Bottom: Social Recovery ---
    draw.line((30, pm_y + 62, 770, pm_y + 62), fill=BORDER, width=1)
    recov_y = pm_y + 72
    draw.text((40, recov_y), "Social Recovery", font=font_header, fill=YELLOW)

    # Smart wallet in center
    sw_box = (290, recov_y + 25, 500, recov_y + 75)
    draw_rounded_rect(draw, sw_box, fill=DARK_BOX, outline=YELLOW)
    draw.text((310, recov_y + 32), "Smart Wallet", font=font_body, fill=YELLOW)
    draw.text((310, recov_y + 50), "2-of-3 guardians", font=font_small, fill=DIM)

    # Guardian circles around the wallet
    guardians = [
        ("G1", CYAN, 160, recov_y + 50),
        ("G2", GREEN, 610, recov_y + 35),
        ("G3", PURPLE, 610, recov_y + 65),
    ]
    for label, color, gx, gy in guardians:
        # Pulse guardian circles
        gp = 0.5 + 0.5 * math.sin(t * math.pi * 2 + gx * 0.01)
        gc = lerp_color(DIM, color, gp)
        draw.ellipse((gx - 18, gy - 18, gx + 18, gy + 18), fill=DARK_BOX, outline=gc, width=2)
        tw, th = text_size(draw, label, font_body)
        draw.text((gx - tw // 2, gy - th // 2), label, font=font_body, fill=gc)

        # Lines from guardians to wallet
        # Connect to nearest edge of wallet
        if gx < 290:
            wx = 290
        else:
            wx = 500
        wy = recov_y + 50
        draw.line((gx + 18 if gx < 290 else gx - 18, gy, wx, wy), fill=DIM, width=1)

    # Threshold label
    draw.text((40, recov_y + 90), "Key lost? 2 guardians approve new key", font=font_small, fill=DIM)

    # Bottom note
    draw.text((40, 530), "ERC-4337: programmable accounts without protocol changes", font=font_small, fill=DIM)

    return img


if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print(f"Saved {OUT}")
