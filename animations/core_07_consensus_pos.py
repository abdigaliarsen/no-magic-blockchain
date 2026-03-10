"""
Variant C: Slashing — validator lifecycle: deposit, validate, earn rewards OR misbehave and get slashed.
Generates assets/gifs/core_07_consensus_pos.gif (800x550, 36 frames, 90ms, dark background).
"""

from PIL import Image, ImageDraw, ImageFont
import math

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
BG        = (13, 17, 23)
CYAN      = (56, 189, 248)
GREEN     = (52, 211, 153)
YELLOW    = (250, 204, 21)
ORANGE    = (251, 146, 60)
RED       = (248, 113, 113)
PURPLE    = (167, 139, 250)
WHITE     = (235, 240, 245)
DIM       = (100, 110, 125)
CYAN_BG   = (18, 50, 68)
PURPLE_BG = (35, 28, 58)
YELLOW_BG = (58, 50, 14)
GREEN_BG  = (14, 48, 40)
RED_BG    = (50, 20, 20)
PANEL     = (17, 21, 28)
DARK_BOX  = (22, 27, 35)
BORDER    = (40, 50, 65)

W, H = 800, 550
FRAMES = 36
DELAY_MS = 90

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
def load_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()

def load_mono(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()

font_title  = load_font(26, bold=True)
font_header = load_font(14, bold=True)
font_body   = load_font(12)
font_small  = load_font(10)
font_mono   = load_mono(12)
font_big    = load_font(18, bold=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def text_center(draw, text, x, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw // 2, y), text, font=font, fill=fill)

def draw_arrow_right(draw, x1, y, x2, color, width=2):
    """Draw a horizontal arrow from (x1,y) to (x2,y)."""
    draw.line([(x1, y), (x2, y)], fill=color, width=width)
    draw.polygon([(x2 - 8, y - 5), (x2 - 8, y + 5), (x2, y)], fill=color)

def draw_arrow_down(draw, x, y1, y2, color, width=2):
    """Draw a vertical arrow from (x,y1) to (x,y2)."""
    draw.line([(x, y1), (x, y2)], fill=color, width=width)
    draw.polygon([(x - 5, y2 - 8), (x + 5, y2 - 8), (x, y2)], fill=color)

def draw_stake_bar(draw, x, y, w, h, fill_frac, color, bg):
    """Horizontal bar showing stake amount."""
    rounded_rect(draw, (x, y, x + w, y + h), 3, fill=bg, outline=BORDER)
    bar_w = int(w * fill_frac)
    if bar_w > 2:
        rounded_rect(draw, (x, y, x + bar_w, y + h), 3, fill=color)

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------
# Shared start box
START_X, START_Y = 60, 110
BOX_W, BOX_H = 130, 60

# Happy path (top row)
HAPPY_Y = 100
# Boxes: Deposit -> Validate -> Earn Rewards -> Stake Grows
happy_boxes = [
    {"label": "Deposit",      "sub": "32 ETH",       "color": CYAN,   "bg": CYAN_BG,   "x": 55},
    {"label": "Validate",     "sub": "Propose blocks","color": GREEN,  "bg": GREEN_BG,  "x": 235},
    {"label": "Earn Rewards", "sub": "+0.05 ETH/day", "color": GREEN,  "bg": GREEN_BG,  "x": 415},
    {"label": "Stake Grows",  "sub": "32 -> 34.8 ETH","color": CYAN,   "bg": CYAN_BG,   "x": 595},
]

# Bad path (bottom row)
BAD_Y = 310
bad_boxes = [
    {"label": "Deposit",       "sub": "32 ETH",           "color": CYAN,   "bg": CYAN_BG,   "x": 55},
    {"label": "Double Sign",   "sub": "Sign 2 blocks",    "color": ORANGE, "bg": YELLOW_BG, "x": 235},
    {"label": "SLASHED!",      "sub": "Penalty applied",  "color": RED,    "bg": RED_BG,    "x": 415},
    {"label": "Stake Burned",  "sub": "32 -> 0 ETH",      "color": RED,    "bg": RED_BG,    "x": 595},
]

# ---------------------------------------------------------------------------
# Frame generation
# ---------------------------------------------------------------------------
def make_frame(frame_idx):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = frame_idx / (FRAMES - 1)

    # Title
    text_center(draw, "Proof of Stake: Slashing", W // 2, 14, font_title, WHITE)
    text_center(draw, "Honest validators earn rewards -- dishonest ones lose everything",
                W // 2, 50, font_body, DIM)

    # --- Happy path label ---
    happy_label_y = HAPPY_Y - 16
    draw.text((20, happy_label_y), "Happy Path", font=font_header, fill=GREEN)

    # Happy path boxes
    for i, box in enumerate(happy_boxes):
        bx = box["x"]
        by = HAPPY_Y
        bw, bh = BOX_W, BOX_H

        rounded_rect(draw, (bx, by, bx + bw, by + bh), 8,
                      fill=box["bg"], outline=box["color"], width=2)
        text_center(draw, box["label"], bx + bw // 2, by + 10, font_header, box["color"])
        text_center(draw, box["sub"], bx + bw // 2, by + 32, font_small, DIM)

        # Arrow to next box
        if i < len(happy_boxes) - 1:
            next_bx = happy_boxes[i + 1]["x"]
            arrow_y = by + bh // 2
            # Animated pulse on arrow
            pulse = 0.4 + 0.6 * abs(math.sin(frame_idx * 0.3 + i * 1.2))
            ac = (int(GREEN[0] * pulse), int(GREEN[1] * pulse), int(GREEN[2] * pulse))
            draw_arrow_right(draw, bx + bw + 4, arrow_y, next_bx - 4, ac)

    # Stake growth bar under happy path
    bar_y = HAPPY_Y + BOX_H + 18
    bar_x = happy_boxes[0]["x"]
    bar_total_w = happy_boxes[-1]["x"] + BOX_W - bar_x
    text_center(draw, "Stake over time", bar_x + bar_total_w // 2, bar_y, font_small, DIM)
    bar_y += 16
    # Animated growing bar
    grow = 0.7 + 0.3 * abs(math.sin(frame_idx * 0.15))
    draw_stake_bar(draw, bar_x, bar_y, bar_total_w, 14, 0.5 + 0.15 * grow, GREEN, GREEN_BG)
    # Labels on bar
    draw.text((bar_x + 4, bar_y - 1), "32 ETH", font=font_small, fill=GREEN)
    text_right_pos = bar_x + int(bar_total_w * (0.5 + 0.15 * grow))
    if text_right_pos > bar_x + 80:
        draw.text((text_right_pos + 6, bar_y - 1), f"{32 + 2.8 * grow:.1f}", font=font_small, fill=CYAN)

    # --- Divider ---
    div_y = HAPPY_Y + BOX_H + 58
    draw.line([(40, div_y), (W - 40, div_y)], fill=BORDER, width=1)

    # --- Bad path label ---
    bad_label_y = BAD_Y - 16
    draw.text((20, bad_label_y), "Slashing Path", font=font_header, fill=RED)

    # Bad path boxes
    for i, box in enumerate(bad_boxes):
        bx = box["x"]
        by = BAD_Y
        bw, bh = BOX_W, BOX_H

        # For SLASHED box, pulsing red border
        outline_w = 2
        outline_c = box["color"]
        if box["label"] == "SLASHED!":
            pulse = 0.5 + 0.5 * math.sin(frame_idx * 0.5)
            outline_w = 2 + int(2 * pulse)
            outline_c = (int(RED[0] * (0.6 + 0.4 * pulse)),
                         int(RED[1] * (0.6 + 0.4 * pulse)),
                         int(RED[2] * (0.6 + 0.4 * pulse)))

        rounded_rect(draw, (bx, by, bx + bw, by + bh), 8,
                      fill=box["bg"], outline=outline_c, width=outline_w)
        text_center(draw, box["label"], bx + bw // 2, by + 10, font_header, box["color"])
        text_center(draw, box["sub"], bx + bw // 2, by + 32, font_small, DIM)

        # Arrow to next box
        if i < len(bad_boxes) - 1:
            next_bx = bad_boxes[i + 1]["x"]
            arrow_y = by + bh // 2
            arrow_color = ORANGE if i < 1 else RED
            pulse = 0.4 + 0.6 * abs(math.sin(frame_idx * 0.3 + i * 1.2))
            ac = (int(arrow_color[0] * pulse), int(arrow_color[1] * pulse),
                  int(arrow_color[2] * pulse))
            draw_arrow_right(draw, bx + bw + 4, arrow_y, next_bx - 4, ac)

    # Stake shrink bar under bad path
    bar_y2 = BAD_Y + BOX_H + 18
    bar_x2 = bad_boxes[0]["x"]
    bar_total_w2 = bad_boxes[-1]["x"] + BOX_W - bar_x2
    text_center(draw, "Stake over time", bar_x2 + bar_total_w2 // 2, bar_y2, font_small, DIM)
    bar_y2 += 16
    # Animated shrinking bar
    shrink = 0.3 * abs(math.sin(frame_idx * 0.15))
    draw_stake_bar(draw, bar_x2, bar_y2, bar_total_w2, 14, max(0.05, 0.5 - shrink), RED, RED_BG)
    draw.text((bar_x2 + 4, bar_y2 - 1), "32 ETH", font=font_small, fill=RED)
    # "X" slash marks on the depleted portion
    slash_end = bar_x2 + int(bar_total_w2 * max(0.05, 0.5 - shrink))
    for sx in range(slash_end + 10, bar_x2 + int(bar_total_w2 * 0.5), 20):
        pulse2 = 0.4 + 0.6 * abs(math.sin(frame_idx * 0.4 + sx * 0.01))
        xc = (int(RED[0] * pulse2), int(RED[1] * pulse2), int(RED[2] * pulse2))
        draw.line([(sx - 4, bar_y2), (sx + 4, bar_y2 + 14)], fill=xc, width=1)
        draw.line([(sx + 4, bar_y2), (sx - 4, bar_y2 + 14)], fill=xc, width=1)

    # --- Scan lines on both paths ---
    # A vertical scan line sweeps across both rows
    scan_x = 55 + int((595 + BOX_W - 55) * ((frame_idx % FRAMES) / FRAMES))
    pulse_s = 0.2 + 0.3 * abs(math.sin(frame_idx * 0.4))
    sc = (int(255 * pulse_s), int(255 * pulse_s), int(255 * pulse_s))
    draw.line([(scan_x, HAPPY_Y - 5), (scan_x, HAPPY_Y + BOX_H + 5)], fill=sc, width=1)
    draw.line([(scan_x, BAD_Y - 5), (scan_x, BAD_Y + BOX_H + 5)], fill=sc, width=1)

    # --- Contrast arrow between paths (center) ---
    contrast_x = W // 2
    # Down arrow from happy to bad with "OR" label
    or_y = div_y - 10
    draw.ellipse((contrast_x - 14, or_y - 2, contrast_x + 14, or_y + 18),
                 fill=DARK_BOX, outline=BORDER, width=1)
    text_center(draw, "OR", contrast_x, or_y, font_small, WHITE)

    # --- Bottom note ---
    text_center(draw, "Misbehavior costs real money -- economic security enforces honest behavior",
                W // 2, H - 28, font_small, DIM)

    return img


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    frames = [make_frame(i) for i in range(FRAMES)]
    frames[0].save(
        "assets/gifs/core_07_consensus_pos.gif",
        save_all=True,
        append_images=frames[1:],
        duration=DELAY_MS,
        loop=0,
        optimize=True,
    )
    print("Saved assets/gifs/core_07_consensus_pos.gif")
