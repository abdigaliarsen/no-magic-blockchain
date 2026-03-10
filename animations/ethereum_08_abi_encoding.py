"""
Variant A: "Function Selector"
Shows transfer(address,uint256) -> keccak256 -> first 4 bytes = 0xa9059cbb
Then shows how arguments are padded to 32 bytes each. Color-coded selector vs args.
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/ethereum_08_abi_encoding.gif"

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

# --- Fonts ---
try:
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except Exception:
    font_title = ImageFont.load_default()
    font_header = ImageFont.load_default()
    font_body = ImageFont.load_default()
    font_small = ImageFont.load_default()


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def draw_rounded_rect(draw, xy, fill, outline=None, radius=8):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / (FRAMES - 1)  # 0..1

    # --- Title ---
    draw.text((30, 18), "ABI Encoding: Function Selector", font=font_title, fill=WHITE)
    draw.line((30, 52, 770, 52), fill=BORDER, width=1)

    # --- Top section: Signature -> keccak256 -> selector ---
    # Signature box
    sig_text = "transfer(address,uint256)"
    sig_box = (40, 72, 320, 118)
    draw_rounded_rect(draw, sig_box, fill=CYAN_BG, outline=CYAN)
    draw.text((50, 78), "Function Signature", font=font_small, fill=DIM)
    draw.text((50, 93), sig_text, font=font_body, fill=CYAN)

    # Arrow from sig to keccak box
    arrow_x1, arrow_x2 = 325, 385
    arrow_y = 95
    # Animate scan dot along arrow
    scan_pos = arrow_x1 + (arrow_x2 - arrow_x1) * ((t * 3) % 1.0)
    draw.line((arrow_x1, arrow_y, arrow_x2, arrow_y), fill=DIM, width=2)
    draw.polygon([(arrow_x2, arrow_y), (arrow_x2 - 6, arrow_y - 4), (arrow_x2 - 6, arrow_y + 4)], fill=YELLOW)
    draw.ellipse((scan_pos - 3, arrow_y - 3, scan_pos + 3, arrow_y + 3), fill=YELLOW)

    # Keccak256 box
    keccak_box = (390, 72, 570, 118)
    draw_rounded_rect(draw, keccak_box, fill=YELLOW_BG, outline=YELLOW)
    draw.text((400, 78), "keccak256()", font=font_small, fill=DIM)
    draw.text((400, 93), "Hash Function", font=font_body, fill=YELLOW)

    # Arrow from keccak to selector
    arrow2_x1, arrow2_x2 = 575, 635
    scan_pos2 = arrow2_x1 + (arrow2_x2 - arrow2_x1) * ((t * 3 + 0.33) % 1.0)
    draw.line((arrow2_x1, arrow_y, arrow2_x2, arrow_y), fill=DIM, width=2)
    draw.polygon([(arrow2_x2, arrow_y), (arrow2_x2 - 6, arrow_y - 4), (arrow2_x2 - 6, arrow_y + 4)], fill=ORANGE)
    draw.ellipse((scan_pos2 - 3, arrow_y - 3, scan_pos2 + 3, arrow_y + 3), fill=ORANGE)

    # Selector result box
    sel_box = (640, 72, 770, 118)
    draw_rounded_rect(draw, sel_box, fill=PURPLE_BG, outline=ORANGE)
    draw.text((650, 78), "First 4 Bytes", font=font_small, fill=DIM)
    draw.text((650, 93), "0xa9059cbb", font=font_body, fill=ORANGE)

    # --- Middle section: Full keccak hash ---
    draw.line((40, 135, 770, 135), fill=BORDER, width=1)
    draw.text((40, 145), "Full keccak256 Hash:", font=font_header, fill=DIM)
    full_hash = "a9059cbb2ab09eb219583f4a59a5d0623ade346d962bcd4e46b11da047c9049b"
    # Color the first 8 chars (4 bytes) in orange, rest in DIM
    x_hash = 40
    y_hash = 168
    for i, ch in enumerate(full_hash):
        color = ORANGE if i < 8 else DIM
        draw.text((x_hash, y_hash), ch, font=font_body, fill=color)
        cw, _ = text_size(draw, ch, font_body)
        x_hash += cw + 1

    # Underline selector portion with animated pulse
    pulse = 0.5 + 0.5 * math.sin(t * math.pi * 4)
    ul_color = lerp_color(ORANGE, YELLOW, pulse)
    sel_end_x = 40
    for i in range(8):
        cw, _ = text_size(draw, full_hash[i], font_body)
        sel_end_x += cw + 1
    draw.line((40, y_hash + 18, sel_end_x, y_hash + 18), fill=ul_color, width=2)

    # --- Bottom section: Padded arguments ---
    draw.line((40, 200, 770, 200), fill=BORDER, width=1)
    draw.text((40, 210), "Calldata Construction (ABI Encoded)", font=font_header, fill=WHITE)

    # Selector row
    row_y = 240
    draw_rounded_rect(draw, (40, row_y, 200, row_y + 55), fill=PURPLE_BG, outline=ORANGE)
    draw.text((50, row_y + 5), "Selector (4 bytes)", font=font_small, fill=DIM)
    draw.text((50, row_y + 22), "a9059cbb", font=font_body, fill=ORANGE)
    draw.text((50, row_y + 38), "Bytes 0-3", font=font_small, fill=DIM)

    # Arg1: address (left-padded to 32 bytes)
    arg1_y = row_y + 70
    draw_rounded_rect(draw, (40, arg1_y, 770, arg1_y + 55), fill=GREEN_BG, outline=GREEN)
    draw.text((50, arg1_y + 5), "Arg 1: address (32 bytes, left-padded with zeros)", font=font_small, fill=DIM)
    addr_hex = "0000000000000000000000005B38Da6a701c568545dCfcB03FcB875f56beddC4"
    # Show zeros dim, address bright
    x_addr = 50
    for i, ch in enumerate(addr_hex):
        color = DIM if i < 24 else GREEN
        draw.text((x_addr, arg1_y + 22), ch, font=font_body, fill=color)
        cw, _ = text_size(draw, ch, font_body)
        x_addr += cw + 1
    draw.text((50, arg1_y + 38), "Bytes 4-35", font=font_small, fill=DIM)

    # Scanning line over arg1
    scan_x = 50 + int((770 - 80) * ((t * 2) % 1.0))
    draw.line((scan_x, arg1_y + 2, scan_x, arg1_y + 53), fill=GREEN, width=1)

    # Arg2: uint256 (left-padded to 32 bytes)
    arg2_y = arg1_y + 70
    draw_rounded_rect(draw, (40, arg2_y, 770, arg2_y + 55), fill=CYAN_BG, outline=CYAN)
    draw.text((50, arg2_y + 5), "Arg 2: uint256 (32 bytes, left-padded with zeros)", font=font_small, fill=DIM)
    val_hex = "0000000000000000000000000000000000000000000000000DE0B6B3A7640000"
    x_val = 50
    for i, ch in enumerate(val_hex):
        color = DIM if i < 48 else CYAN
        draw.text((x_val, arg2_y + 22), ch, font=font_body, fill=color)
        cw, _ = text_size(draw, ch, font_body)
        x_val += cw + 1
    draw.text((50, arg2_y + 38), "Bytes 36-67 (= 1 ETH in wei)", font=font_small, fill=DIM)

    # Scanning line over arg2
    scan_x2 = 50 + int((770 - 80) * ((t * 2 + 0.5) % 1.0))
    draw.line((scan_x2, arg2_y + 2, scan_x2, arg2_y + 53), fill=CYAN, width=1)

    # --- Footer: Total size ---
    footer_y = arg2_y + 70
    draw.line((40, footer_y, 770, footer_y), fill=BORDER, width=1)
    draw.text((40, footer_y + 8), "Total calldata: 4 + 32 + 32 = 68 bytes", font=font_header, fill=WHITE)

    # Size breakdown boxes
    sizes = [("4B", ORANGE), ("32B", GREEN), ("32B", CYAN)]
    sx = 420
    for label, color in sizes:
        bw = 60
        draw_rounded_rect(draw, (sx, footer_y + 4, sx + bw, footer_y + 26), fill=BG, outline=color)
        tw, _ = text_size(draw, label, font_body)
        draw.text((sx + (bw - tw) // 2, footer_y + 7), label, font=font_body, fill=color)
        sx += bw + 10

    return img


# --- Generate GIF ---
if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print(f"Saved {OUT}")
