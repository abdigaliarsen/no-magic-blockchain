"""
Gulf Stream Variant B: "Leader Schedule"
Pipeline visualization: transactions forwarded to NEXT leader before current slot ends.
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
BG = (13, 17, 23)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
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
YELLOW_BG = (58, 50, 14)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)

OUT = "assets/gifs/solana_08_gulf_stream.gif"

def load_fonts():
    fonts = {}
    for name, size in [("title", 26), ("header", 14), ("body", 12), ("small", 10)]:
        bold = name in ("title", "header")
        fname = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        try:
            fonts[name] = ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{fname}", size)
        except:
            fonts[name] = ImageFont.load_default()
    return fonts

FONTS = load_fonts()

def text_center(draw, x, y, text, font, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((x - tw // 2, y - th // 2), text, font=font, fill=fill)

def draw_box(draw, x, y, w, h, fill, border_color, radius=6):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill, outline=border_color, width=1)

def draw_arrow(draw, x1, y1, x2, y2, color, width=2):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    dx, dy = x2 - x1, y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    sz = 7
    draw.polygon([
        (x2, y2),
        (x2 - ux * sz + px * sz * 0.5, y2 - uy * sz + py * sz * 0.5),
        (x2 - ux * sz - px * sz * 0.5, y2 - uy * sz - py * sz * 0.5),
    ], fill=color)

def draw_dashed_line(draw, x1, y1, x2, y2, color, dash=8, gap=5, width=1):
    dx, dy = x2 - x1, y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    pos = 0
    while pos < length:
        sx = x1 + ux * pos
        sy = y1 + uy * pos
        end = min(pos + dash, length)
        ex = x1 + ux * end
        ey = y1 + uy * end
        draw.line([(sx, sy), (ex, ey)], fill=color, width=width)
        pos += dash + gap

def draw_frame(frame_idx):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = frame_idx / (FRAMES - 1)

    # Title
    text_center(draw, W // 2, 24, "Gulf Stream: Leader Schedule Pipeline", FONTS["title"], WHITE)

    # --- Timeline at top ---
    tl_y = 65
    tl_x1, tl_x2 = 60, 740
    draw.line([(tl_x1, tl_y), (tl_x2, tl_y)], fill=BORDER, width=2)

    # Slot divisions
    slot_w = (tl_x2 - tl_x1) // 4
    slot_colors = [CYAN, PURPLE, ORANGE, GREEN]
    slot_bg = [CYAN_BG, PURPLE_BG, YELLOW_BG, GREEN_BG]
    slot_names = ["Slot 1", "Slot 2", "Slot 3", "Slot 4"]
    validator_names = ["Val A", "Val B", "Val C", "Val D"]

    for i in range(4):
        sx = tl_x1 + i * slot_w
        draw_box(draw, sx + 2, tl_y - 20, slot_w - 4, 40, slot_bg[i], slot_colors[i])
        text_center(draw, sx + slot_w // 2, tl_y - 8, slot_names[i], FONTS["small"], slot_colors[i])
        text_center(draw, sx + slot_w // 2, tl_y + 8, validator_names[i], FONTS["small"], WHITE)

    # Animated current-slot marker
    marker_x = tl_x1 + int(t * (tl_x2 - tl_x1))
    draw.polygon([
        (marker_x, tl_y + 25),
        (marker_x - 6, tl_y + 35),
        (marker_x + 6, tl_y + 35),
    ], fill=YELLOW)
    text_center(draw, marker_x, tl_y + 44, "now", FONTS["small"], YELLOW)

    # --- Validators row ---
    val_y = 140
    val_w, val_h = 130, 70
    val_gap = 40
    total_val_w = 4 * val_w + 3 * val_gap
    val_start_x = (W - total_val_w) // 2

    for i in range(4):
        vx = val_start_x + i * (val_w + val_gap)
        col = slot_colors[i]
        bg = slot_bg[i]

        # Highlight active validator
        current_slot = int(t * 4) % 4
        if i == current_slot:
            draw_box(draw, vx - 3, val_y - 3, val_w + 6, val_h + 6, DARK_BOX, YELLOW, radius=8)

        draw_box(draw, vx, val_y, val_w, val_h, bg, col)
        text_center(draw, vx + val_w // 2, val_y + 18, validator_names[i], FONTS["header"], col)
        text_center(draw, vx + val_w // 2, val_y + 42, "Leader" if i == current_slot else "Waiting", FONTS["small"],
                    YELLOW if i == current_slot else DIM)

    # --- Transaction forwarding section ---
    fwd_y = 260
    draw.rounded_rectangle([40, fwd_y, W - 40, fwd_y + 230], radius=8, fill=PANEL, outline=BORDER)
    text_center(draw, W // 2, fwd_y + 18, "Transaction Forwarding Pipeline", FONTS["header"], WHITE)

    # Three tx rows showing forwarding
    tx_data = [
        ("Tx #1", CYAN, 0),
        ("Tx #2", PURPLE, 1),
        ("Tx #3", ORANGE, 2),
    ]

    current_slot = int(t * 4) % 4
    next_slot = (current_slot + 1) % 4
    next2_slot = (current_slot + 2) % 4

    for row, (tx_name, tx_col, offset) in enumerate(tx_data):
        ty = fwd_y + 50 + row * 60

        # Source: "Tx" box
        draw_box(draw, 70, ty, 80, 36, DARK_BOX, tx_col)
        text_center(draw, 110, ty + 18, tx_name, FONTS["body"], tx_col)

        # Arrow from tx to current+1 leader
        target_idx = (current_slot + 1 + offset) % 4
        target_col = slot_colors[target_idx]
        target_name = validator_names[target_idx]

        # Intermediate: RPC node
        draw_box(draw, 200, ty, 80, 36, DARK_BOX, DIM)
        text_center(draw, 240, ty + 18, "RPC", FONTS["body"], DIM)

        # Arrow tx -> RPC
        draw_arrow(draw, 150, ty + 18, 200, ty + 18, tx_col)

        # Forward box
        draw_box(draw, 330, ty, 100, 36, GREEN_BG, GREEN)
        text_center(draw, 380, ty + 18, "Forward", FONTS["body"], GREEN)

        # Arrow RPC -> Forward
        draw_arrow(draw, 280, ty + 18, 330, ty + 18, GREEN)

        # Target leader
        draw_box(draw, 490, ty, 110, 36, slot_bg[target_idx], target_col)
        text_center(draw, 545, ty + 18, target_name, FONTS["body"], target_col)

        # Arrow Forward -> Target
        # Animated: pulsing arrow
        phase = (t * 3 + offset * 0.3) % 1.0
        pulse_alpha = 0.5 + 0.5 * math.sin(phase * math.pi * 2)
        arrow_col = tuple(int(c * pulse_alpha + BG[j] * (1 - pulse_alpha)) for j, c in enumerate(GREEN))
        draw_arrow(draw, 430, ty + 18, 490, ty + 18, arrow_col, width=2)

        # Checkmark at end
        draw_box(draw, 650, ty, 80, 36, DARK_BOX, GREEN)
        text_center(draw, 690, ty + 18, "Ready", FONTS["small"], GREEN)
        draw_arrow(draw, 600, ty + 18, 650, ty + 18, GREEN)

    # --- Bottom: Key insight ---
    text_center(draw, W // 2, H - 30, "Transactions forwarded to upcoming leaders before slot transition", FONTS["small"], DIM)
    text_center(draw, W // 2, H - 14, "No waiting in mempool -- immediate pipeline processing", FONTS["small"], GREEN)

    return img

frames = [draw_frame(i) for i in range(FRAMES)]
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0)
print(f"Saved {OUT}")
