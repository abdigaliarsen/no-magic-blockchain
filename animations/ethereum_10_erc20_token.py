"""
ERC-20 Token: Token contract box in center, transfer flow showing
Alice balance decrease / Bob balance increase, approve+transferFrom flow,
and event log panel.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/ethereum_10_erc20_token.gif"

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


def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / (FRAMES - 1)

    # --- Title ---
    draw.text((30, 18), "ERC-20 Token Standard", font=font_title, fill=WHITE)
    draw.line((30, 52, 770, 52), fill=BORDER, width=1)

    # --- Central contract box ---
    contract_box = (290, 68, 510, 160)
    draw_rounded_rect(draw, contract_box, fill=PURPLE_BG, outline=PURPLE)
    draw.text((310, 75), "ERC-20 Contract", font=font_header, fill=PURPLE)
    draw.text((310, 98), 'name: "MyToken"', font=font_small, fill=DIM)
    draw.text((310, 114), "symbol: MTK", font=font_small, fill=DIM)
    draw.text((310, 130), "totalSupply: 1000", font=font_small, fill=DIM)

    # --- Transfer flow: Alice -> Contract -> Bob ---
    # Alice box (left)
    alice_box = (40, 80, 210, 148)
    draw_rounded_rect(draw, alice_box, fill=CYAN_BG, outline=CYAN)
    draw.text((55, 86), "Alice", font=font_header, fill=CYAN)
    # Animated balance
    alice_bal = 1000 - int(100 * ((math.sin(t * math.pi * 2) + 1) / 2))
    draw.text((55, 108), f"balance: {alice_bal}", font=font_body, fill=WHITE)
    draw.text((55, 126), "0x1a2b...", font=font_small, fill=DIM)

    # Bob box (right)
    bob_box = (590, 80, 760, 148)
    draw_rounded_rect(draw, bob_box, fill=GREEN_BG, outline=GREEN)
    draw.text((605, 86), "Bob", font=font_header, fill=GREEN)
    bob_bal = 0 + int(100 * ((math.sin(t * math.pi * 2) + 1) / 2))
    draw.text((605, 108), f"balance: {bob_bal}", font=font_body, fill=WHITE)
    draw.text((605, 126), "0x3c4d...", font=font_small, fill=DIM)

    # Arrow Alice -> Contract
    ax1, ax2 = 215, 285
    ay = 114
    draw.line((ax1, ay, ax2, ay), fill=DIM, width=2)
    draw.polygon([(ax2, ay), (ax2 - 6, ay - 4), (ax2 - 6, ay + 4)], fill=CYAN)
    dot_x = ax1 + (ax2 - ax1) * ((t * 3) % 1.0)
    draw.ellipse((dot_x - 3, ay - 3, dot_x + 3, ay + 3), fill=CYAN)

    # Arrow Contract -> Bob
    bx1, bx2 = 515, 585
    by = 114
    draw.line((bx1, by, bx2, by), fill=DIM, width=2)
    draw.polygon([(bx2, by), (bx2 - 6, by - 4), (bx2 - 6, by + 4)], fill=GREEN)
    dot_x2 = bx1 + (bx2 - bx1) * ((t * 3 + 0.5) % 1.0)
    draw.ellipse((dot_x2 - 3, by - 3, dot_x2 + 3, by + 3), fill=GREEN)

    # Transfer label
    draw.text((330, 162), "transfer(to, amount)", font=font_small, fill=YELLOW)

    # --- Separator ---
    draw.line((30, 185, 770, 185), fill=BORDER, width=1)

    # --- Approve + TransferFrom flow ---
    draw.text((40, 195), "Approve + TransferFrom Pattern", font=font_header, fill=ORANGE)

    # Alice box (approve)
    a2_box = (40, 222, 180, 302)
    draw_rounded_rect(draw, a2_box, fill=CYAN_BG, outline=CYAN)
    draw.text((55, 228), "Alice", font=font_body, fill=CYAN)
    draw.text((55, 246), "Owner", font=font_small, fill=DIM)
    draw.text((55, 264), "approve()", font=font_small, fill=YELLOW)
    draw.text((55, 280), "allowance: 50", font=font_small, fill=WHITE)

    # Arrow to DEX
    draw.line((185, 262, 250, 262), fill=DIM, width=2)
    draw.polygon([(250, 262), (244, 258), (244, 266)], fill=ORANGE)
    d1 = 185 + 65 * ((t * 2.5) % 1.0)
    draw.ellipse((d1 - 3, 259, d1 + 3, 265), fill=ORANGE)

    # DEX / Spender box
    dex_box = (255, 222, 420, 302)
    draw_rounded_rect(draw, dex_box, fill=YELLOW_BG, outline=ORANGE)
    draw.text((270, 228), "DEX (Spender)", font=font_body, fill=ORANGE)
    draw.text((270, 248), "transferFrom(", font=font_small, fill=DIM)
    draw.text((270, 262), "  alice, bob,", font=font_small, fill=DIM)
    draw.text((270, 276), "  50)", font=font_small, fill=DIM)

    # Arrow to Bob
    draw.line((425, 262, 490, 262), fill=DIM, width=2)
    draw.polygon([(490, 262), (484, 258), (484, 266)], fill=GREEN)
    d2 = 425 + 65 * ((t * 2.5 + 0.5) % 1.0)
    draw.ellipse((d2 - 3, 259, d2 + 3, 265), fill=GREEN)

    # Bob receives
    b2_box = (495, 222, 635, 302)
    draw_rounded_rect(draw, b2_box, fill=GREEN_BG, outline=GREEN)
    draw.text((510, 228), "Bob", font=font_body, fill=GREEN)
    draw.text((510, 246), "Recipient", font=font_small, fill=DIM)
    draw.text((510, 264), "receives 50 MTK", font=font_small, fill=WHITE)

    # --- Separator ---
    draw.line((30, 318, 770, 318), fill=BORDER, width=1)

    # --- Event Log panel ---
    draw.text((40, 328), "Event Log", font=font_header, fill=RED)

    events = [
        ("Transfer(alice, bob, 100)", CYAN),
        ("Approval(alice, dex, 50)", YELLOW),
        ("Transfer(alice, bob, 50)", GREEN),
    ]
    ey = 352
    for i, (evt, color) in enumerate(events):
        # Pulse each event in sequence
        pulse = 0.5 + 0.5 * math.sin(t * math.pi * 2 - i * 1.2)
        ec = lerp_color(DIM, color, pulse)
        draw.text((55, ey), f"emit {evt}", font=font_body, fill=ec)
        ey += 24

    # --- Right: Interface methods ---
    draw.text((480, 328), "Interface", font=font_header, fill=WHITE)
    methods = [
        ("balanceOf(addr)", CYAN),
        ("transfer(to, amt)", GREEN),
        ("approve(spdr, amt)", YELLOW),
        ("transferFrom()", ORANGE),
        ("allowance(own, spdr)", PURPLE),
        ("totalSupply()", DIM),
    ]
    my = 352
    for meth, color in methods:
        draw.text((495, my), meth, font=font_small, fill=color)
        my += 20

    # --- Bottom note ---
    draw.text((40, 520), "EIP-20: Standard interface for fungible tokens on Ethereum", font=font_small, fill=DIM)

    return img


if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print(f"Saved {OUT}")
