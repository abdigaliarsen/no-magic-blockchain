"""
Variant B: "Token Operations"
Three operations side by side: Mint (create new tokens), Transfer (move between
accounts), Burn (destroy tokens). Shows supply changing with each operation.
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- Config ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/solana_06_token_program.gif"

# Colors
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
    font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
except Exception:
    font_title = ImageFont.load_default()
    font_header = font_title
    font_body = font_title
    font_small = font_title
    font_big = font_title


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def draw_rounded_rect(draw, box, fill, outline, radius=8):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline)


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def draw_frame(frame_idx):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    t = frame_idx / FRAMES
    pulse = 0.5 + 0.5 * math.sin(frame_idx * 2 * math.pi / 18)  # pulse cycle
    scan = (frame_idx % 24) / 24.0

    # --- Title ---
    title = "SPL Token Operations"
    tw, _ = text_size(draw, title, font_title)
    draw.text(((W - tw) // 2, 12), title, fill=CYAN, font=font_title)

    # --- Three columns ---
    col_w = 220
    col_gap = 30
    total = col_w * 3 + col_gap * 2
    start_x = (W - total) // 2

    operations = [
        {
            "title": "MINT",
            "color": GREEN,
            "bg": GREEN_BG,
            "desc": "Create new tokens",
            "icon_label": "+",
            "supply_before": "0",
            "supply_after": "1,000",
            "from_label": "Mint Authority",
            "to_label": "Alice Acct",
            "amount": "+1,000",
        },
        {
            "title": "TRANSFER",
            "color": CYAN,
            "bg": CYAN_BG,
            "desc": "Move between accounts",
            "icon_label": ">>",
            "supply_before": "1,000",
            "supply_after": "1,000",
            "from_label": "Alice Acct",
            "to_label": "Bob Acct",
            "amount": "300",
        },
        {
            "title": "BURN",
            "color": RED,
            "bg": RED_BG,
            "desc": "Destroy tokens",
            "icon_label": "X",
            "supply_before": "1,000",
            "supply_after": "900",
            "from_label": "Bob Acct",
            "to_label": "(destroyed)",
            "amount": "-100",
        },
    ]

    for i, op in enumerate(operations):
        cx = start_x + i * (col_w + col_gap)
        cy = 55

        color = op["color"]
        bg = op["bg"]

        # Column panel
        draw_rounded_rect(draw, (cx, cy, cx + col_w, cy + 440), fill=PANEL, outline=BORDER, radius=10)

        # Header
        draw_rounded_rect(draw, (cx + 8, cy + 8, cx + col_w - 8, cy + 50), fill=bg, outline=color, radius=6)
        tw2, _ = text_size(draw, op["title"], font_big)
        draw.text((cx + (col_w - tw2) // 2, cy + 16), op["title"], fill=color, font=font_big)

        # Description
        dw, _ = text_size(draw, op["desc"], font_small)
        draw.text((cx + (col_w - dw) // 2, cy + 58), op["desc"], fill=DIM, font=font_small)

        # From box
        from_y = cy + 82
        draw_rounded_rect(draw, (cx + 15, from_y, cx + col_w - 15, from_y + 55),
                           fill=DARK_BOX, outline=BORDER, radius=6)
        draw.text((cx + 25, from_y + 6), "FROM", fill=DIM, font=font_small)
        draw.text((cx + 25, from_y + 22), op["from_label"], fill=WHITE, font=font_body)
        if i == 0:
            draw.text((cx + 25, from_y + 38), "Authority", fill=PURPLE, font=font_small)
        elif i == 1:
            draw.text((cx + 25, from_y + 38), "Bal: 1,000", fill=GREEN, font=font_small)
        else:
            draw.text((cx + 25, from_y + 38), "Bal: 300", fill=ORANGE, font=font_small)

        # Arrow area with animated scan dot
        arrow_y_start = from_y + 60
        arrow_y_end = from_y + 130
        mid_x = cx + col_w // 2

        draw.line([(mid_x, arrow_y_start), (mid_x, arrow_y_end)], fill=color, width=2)
        # Arrowhead
        draw.polygon([(mid_x, arrow_y_end),
                       (mid_x - 6, arrow_y_end - 10),
                       (mid_x + 6, arrow_y_end - 10)], fill=color)

        # Amount label
        amnt = op["amount"]
        aw, _ = text_size(draw, amnt, font_header)
        amount_color = GREEN if amnt.startswith("+") else RED if amnt.startswith("-") else CYAN
        draw.text((mid_x + 12, (arrow_y_start + arrow_y_end) // 2 - 7), amnt,
                  fill=amount_color, font=font_header)

        # Scanning dot on arrow
        dot_t = (scan + i * 0.33) % 1.0
        dot_y = arrow_y_start + (arrow_y_end - arrow_y_start) * dot_t
        glow_color = lerp_color(BG, color, pulse)
        draw.ellipse([mid_x - 5, dot_y - 5, mid_x + 5, dot_y + 5], fill=color)
        draw.ellipse([mid_x - 8, dot_y - 8, mid_x + 8, dot_y + 8], outline=glow_color)

        # To box
        to_y = from_y + 135
        draw_rounded_rect(draw, (cx + 15, to_y, cx + col_w - 15, to_y + 55),
                           fill=DARK_BOX, outline=BORDER, radius=6)
        draw.text((cx + 25, to_y + 6), "TO", fill=DIM, font=font_small)
        draw.text((cx + 25, to_y + 22), op["to_label"], fill=WHITE, font=font_body)
        if i == 0:
            draw.text((cx + 25, to_y + 38), "Bal: 0 -> 1,000", fill=GREEN, font=font_small)
        elif i == 1:
            draw.text((cx + 25, to_y + 38), "Bal: 0 -> 300", fill=CYAN, font=font_small)
        else:
            draw.text((cx + 25, to_y + 38), "Tokens gone", fill=RED, font=font_small)

        # Supply indicator
        supply_y = to_y + 75
        draw.line([(cx + 20, supply_y), (cx + col_w - 20, supply_y)], fill=BORDER)
        draw.text((cx + 25, supply_y + 8), "Total Supply:", fill=DIM, font=font_small)

        before_text = op["supply_before"]
        after_text = op["supply_after"]
        supply_str = before_text + " -> " + after_text
        scolor = GREEN if int(after_text.replace(",", "")) > int(before_text.replace(",", "")) else \
                 RED if int(after_text.replace(",", "")) < int(before_text.replace(",", "")) else DIM
        draw.text((cx + 25, supply_y + 24), supply_str, fill=scolor, font=font_body)

    # --- Bottom scan line ---
    scan_x = int(30 + (W - 60) * scan)
    draw.line([(scan_x, H - 20), (scan_x + 50, H - 20)], fill=CYAN, width=2)

    return img


frames = [draw_frame(i) for i in range(FRAMES)]
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0)
print(f"Saved {OUT} ({len(frames)} frames)")
