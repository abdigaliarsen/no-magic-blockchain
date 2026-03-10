"""BTC07-A: The Thermostat — Difficulty adjustment feedback loop with gauge."""
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
header_font = load_font(14, True)
body_font = load_font(12)
small_font = load_font(10)
mono_font = load_font(12)
big_font = load_font(20, True)

def text_w(draw, txt, font):
    bb = draw.textbbox((0,0), txt, font=font)
    return bb[2] - bb[0]

def draw_rounded_box(draw, x, y, w, h, fill, border_col, r=8):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=border_col, width=2)

def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    pulse = 0.5 + 0.5 * math.sin(f * 2 * math.pi / FRAMES)
    # Needle oscillates around target
    needle_angle = -30 + 60 * (0.5 + 0.4 * math.sin(f * 2 * math.pi / FRAMES + 0.5))

    title = "Difficulty: The Thermostat"
    tw = text_w(draw, title, title_font)
    draw.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)

    # === GAUGE ===
    gauge_cx, gauge_cy = 400, 260
    gauge_r = 150

    # Draw arc background (semicircle)
    # Red zone (too fast), Green zone (target), Blue zone (too slow)
    for angle_deg in range(-150, -90):
        rad = math.radians(angle_deg)
        x1 = gauge_cx + (gauge_r - 20) * math.cos(rad)
        y1 = gauge_cy + (gauge_r - 20) * math.sin(rad)
        x2 = gauge_cx + gauge_r * math.cos(rad)
        y2 = gauge_cy + gauge_r * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=RED, width=3)

    for angle_deg in range(-90, -50):
        rad = math.radians(angle_deg)
        x1 = gauge_cx + (gauge_r - 20) * math.cos(rad)
        y1 = gauge_cy + (gauge_r - 20) * math.sin(rad)
        x2 = gauge_cx + gauge_r * math.cos(rad)
        y2 = gauge_cy + gauge_r * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=ORANGE, width=3)

    for angle_deg in range(-50, -10):
        rad = math.radians(angle_deg)
        x1 = gauge_cx + (gauge_r - 20) * math.cos(rad)
        y1 = gauge_cy + (gauge_r - 20) * math.sin(rad)
        x2 = gauge_cx + gauge_r * math.cos(rad)
        y2 = gauge_cy + gauge_r * math.sin(rad)
        glow_g = tuple(int(c * (0.7 + 0.3 * pulse)) for c in GREEN)
        draw.line([(x1, y1), (x2, y2)], fill=glow_g, width=3)

    for angle_deg in range(-10, 30):
        rad = math.radians(angle_deg)
        x1 = gauge_cx + (gauge_r - 20) * math.cos(rad)
        y1 = gauge_cy + (gauge_r - 20) * math.sin(rad)
        x2 = gauge_cx + gauge_r * math.cos(rad)
        y2 = gauge_cy + gauge_r * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=CYAN, width=3)

    for angle_deg in range(30, 70):
        rad = math.radians(angle_deg)
        x1 = gauge_cx + (gauge_r - 20) * math.cos(rad)
        y1 = gauge_cy + (gauge_r - 20) * math.sin(rad)
        x2 = gauge_cx + gauge_r * math.cos(rad)
        y2 = gauge_cy + gauge_r * math.sin(rad)
        # Too slow zone - not used but for symmetry
        pass

    # Labels on gauge
    draw.text((gauge_cx - gauge_r - 30, gauge_cy - 10), "FAST", fill=RED, font=small_font)
    draw.text((gauge_cx - 20, gauge_cy - gauge_r - 20), "10 min", fill=GREEN, font=header_font)
    draw.text((gauge_cx + gauge_r + 5, gauge_cy - 10), "SLOW", fill=CYAN, font=small_font)

    # Needle
    needle_rad = math.radians(-90 + needle_angle)
    needle_len = gauge_r - 30
    nx = gauge_cx + needle_len * math.cos(needle_rad)
    ny = gauge_cy + needle_len * math.sin(needle_rad)
    draw.line([(gauge_cx, gauge_cy), (nx, ny)], fill=YELLOW, width=3)
    draw.ellipse([gauge_cx-6, gauge_cy-6, gauge_cx+6, gauge_cy+6], fill=YELLOW)

    # Current time display
    current_min = 10 + needle_angle / 6  # roughly maps angle to minutes
    draw.text((gauge_cx - 30, gauge_cy + 20), f"{current_min:.1f} min", fill=WHITE, font=big_font)
    draw.text((gauge_cx - 30, gauge_cy + 45), "avg block time", fill=DIM, font=small_font)

    # === Feedback Loop (left side) ===
    loop_x = 30
    loop_y = 70

    # Box 1: Measure
    draw_rounded_box(draw, loop_x, loop_y, 160, 50, DARK_BOX, CYAN)
    draw.text((loop_x + 10, loop_y + 6), "1. Measure", fill=CYAN, font=header_font)
    draw.text((loop_x + 10, loop_y + 26), "Actual block time", fill=DIM, font=small_font)

    # Box 2: Compare
    draw_rounded_box(draw, loop_x, loop_y + 70, 160, 50, DARK_BOX, YELLOW)
    draw.text((loop_x + 10, loop_y + 76), "2. Compare", fill=YELLOW, font=header_font)
    draw.text((loop_x + 10, loop_y + 96), "vs 10 min target", fill=DIM, font=small_font)

    # Box 3: Adjust
    draw_rounded_box(draw, loop_x, loop_y + 140, 160, 50, DARK_BOX, GREEN)
    draw.text((loop_x + 10, loop_y + 146), "3. Adjust", fill=GREEN, font=header_font)
    draw.text((loop_x + 10, loop_y + 166), "New difficulty", fill=DIM, font=small_font)

    # Arrows between boxes (marching)
    dash = 6
    offset = (f * 2) % (dash * 2)
    for start_y_off, col in [(50, CYAN), (120, YELLOW)]:
        sy = loop_y + start_y_off
        ey = sy + 18
        pos = offset % (dash * 2)
        while pos < (ey - sy):
            draw.line([(loop_x + 80, sy + pos), (loop_x + 80, min(sy + pos + dash, ey))], fill=col, width=2)
            pos += dash * 2
        draw.polygon([(loop_x+80, ey+5), (loop_x+75, ey-2), (loop_x+85, ey-2)], fill=col)

    # Loop back arrow
    draw.line([(loop_x + 160, loop_y + 165), (loop_x + 180, loop_y + 165)], fill=GREEN, width=2)
    draw.line([(loop_x + 180, loop_y + 165), (loop_x + 180, loop_y + 50)], fill=GREEN, width=2)
    draw.line([(loop_x + 180, loop_y + 50), (loop_x + 162, loop_y + 50)], fill=GREEN, width=2)

    # === Rules panel (bottom) ===
    rules_y = 350
    draw_rounded_box(draw, 30, rules_y, 340, 80, PANEL, BORDER)
    draw.text((45, rules_y + 8), "Adjustment Rules:", fill=YELLOW, font=header_font)
    draw.text((45, rules_y + 30), "Too fast (< 10 min):", fill=RED, font=body_font)
    draw.text((220, rules_y + 30), "difficulty UP", fill=RED, font=body_font)
    draw.text((45, rules_y + 50), "Too slow (> 10 min):", fill=CYAN, font=body_font)
    draw.text((220, rules_y + 50), "difficulty DOWN", fill=CYAN, font=body_font)

    # Every 2016 blocks
    draw_rounded_box(draw, 30, rules_y + 100, 340, 55, PANEL, BORDER)
    draw.text((45, rules_y + 108), "Checked every 2016 blocks (~2 weeks)", fill=ORANGE, font=header_font)
    draw.text((45, rules_y + 130), "Self-correcting: always targets 10 min/block", fill=DIM, font=body_font)

    # Right bottom info
    draw_rounded_box(draw, 420, rules_y + 50, 350, 110, PANEL, BORDER)
    draw.text((435, rules_y + 58), "Why 10 Minutes?", fill=YELLOW, font=header_font)
    info_lines = [
        "Fast enough for usability",
        "Slow enough for propagation",
        "Blocks reach all nodes before",
        "next block is found -- reduces",
        "orphan blocks and forks"
    ]
    for i, line in enumerate(info_lines):
        draw.text((435, rules_y + 78 + i * 16), line, fill=WHITE, font=body_font)

    return img

if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save("assets/gifs/bitcoin_07_difficulty_adjustment.gif", save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_07_difficulty_adjustment.gif")
