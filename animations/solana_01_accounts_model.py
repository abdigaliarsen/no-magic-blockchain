"""
Variant A: "Account Anatomy"
Show a Solana account as a box with 4 fields: owner, lamports, data, executable.
Two examples side by side: a wallet account and a program account.
Animated scan line sweeps across the account fields.
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/solana_01_accounts_model.gif"

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

# Fonts
try:
    font_bold_26 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    font_bold_14 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    font_12 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    font_10 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except Exception:
    font_bold_26 = ImageFont.load_default()
    font_bold_14 = font_bold_26
    font_12 = font_bold_26
    font_10 = font_bold_26


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def draw_rounded_rect(draw, xy, fill, outline, radius=8):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def draw_account_box(draw, x, y, w, h, title, title_color, fields, scan_y, is_program):
    """Draw an account box with 4 labeled fields."""
    # Outer box
    draw_rounded_rect(draw, (x, y, x + w, y + h), fill=PANEL, outline=title_color, radius=10)

    # Title bar
    draw.rectangle((x + 1, y + 1, x + w - 1, y + 34), fill=title_color + (40,) if len(title_color) == 3 else title_color)
    # Darken title area
    overlay_color = tuple(c // 5 for c in title_color)
    draw.rectangle((x + 2, y + 2, x + w - 2, y + 33), fill=(*overlay_color, 80))
    tw, _ = text_size(draw, title, font_bold_14)
    draw.text((x + (w - tw) // 2, y + 8), title, fill=title_color, font=font_bold_14)

    # Fields
    field_y = y + 44
    field_h = 50
    field_margin = 8
    field_w = w - field_margin * 2

    field_colors = [CYAN, YELLOW, GREEN, PURPLE] if not is_program else [CYAN, YELLOW, ORANGE, RED]
    field_bgs = [CYAN_BG, YELLOW_BG, GREEN_BG, PURPLE_BG] if not is_program else [CYAN_BG, YELLOW_BG, (48, 30, 12), RED_BG]

    for i, (label, value) in enumerate(fields):
        fy = field_y + i * (field_h + 6)
        fc = field_colors[i]
        fbg = field_bgs[i]

        # Field background
        draw_rounded_rect(draw, (x + field_margin, fy, x + field_margin + field_w, fy + field_h),
                          fill=fbg, outline=BORDER, radius=6)

        # Label
        draw.text((x + field_margin + 10, fy + 6), label, fill=fc, font=font_bold_14)
        # Value
        draw.text((x + field_margin + 10, fy + 26), value, fill=DIM, font=font_12)

    # Scan line (horizontal glow that sweeps vertically)
    if scan_y is not None:
        sy = y + 44 + scan_y
        if y + 40 < sy < y + h - 5:
            for offset in range(-3, 4):
                alpha_factor = 1.0 - abs(offset) / 4.0
                line_y = sy + offset
                if y + 35 < line_y < y + h - 2:
                    line_color = tuple(int(c * alpha_factor * 0.4) for c in title_color)
                    draw.line((x + 4, line_y, x + w - 4, line_y), fill=line_color)


def draw_arrow_between(draw, x1, y1, x2, y2, color, phase):
    """Draw a dashed arrow between two points with animation."""
    dash_len = 6
    gap = 4
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx * dx + dy * dy)
    if dist == 0:
        return
    ux, uy = dx / dist, dy / dist

    offset = (phase * 3) % (dash_len + gap)
    pos = -offset
    while pos < dist:
        s = max(0, pos)
        e = min(dist, pos + dash_len)
        if e > s:
            draw.line(
                (x1 + ux * s, y1 + uy * s, x1 + ux * e, y1 + uy * e),
                fill=color, width=2
            )
        pos += dash_len + gap

    # Arrowhead
    ax, ay = x2 - ux * 10 - uy * 5, y2 - uy * 10 + ux * 5
    bx, by = x2 - ux * 10 + uy * 5, y2 - uy * 10 - ux * 5
    draw.polygon([(x2, y2), (ax, ay), (bx, by)], fill=color)


def generate_frames():
    frames = []
    for f in range(FRAMES):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        # Title
        title = "Solana Account Anatomy"
        tw, _ = text_size(draw, title, font_bold_26)
        draw.text(((W - tw) // 2, 18), title, fill=WHITE, font=font_bold_26)

        # Subtitle
        sub = "Every account has 4 core fields"
        sw, _ = text_size(draw, sub, font_12)
        draw.text(((W - sw) // 2, 50), sub, fill=DIM, font=font_12)

        # Scan line position (cycles through account box height)
        scan_range = 230  # approximate field area height
        scan_y = (f / FRAMES * scan_range * 2) % (scan_range * 2)
        if scan_y > scan_range:
            scan_y = scan_range * 2 - scan_y  # bounce back

        # Wallet account (left)
        wallet_x, wallet_y = 60, 90
        box_w, box_h = 310, 280
        wallet_fields = [
            ("owner", "System Program (1111...1111)"),
            ("lamports", "5,000,000,000 (5 SOL)"),
            ("data", "[empty - 0 bytes]"),
            ("executable", "false"),
        ]
        draw_account_box(draw, wallet_x, wallet_y, box_w, box_h,
                         "Wallet Account", CYAN, wallet_fields, scan_y, False)

        # Program account (right)
        prog_x = 430
        prog_fields = [
            ("owner", "BPF Loader (BPFLoad...er11)"),
            ("lamports", "1,141,440 (rent-exempt)"),
            ("data", "[ELF bytecode - 94KB]"),
            ("executable", "true"),
        ]
        draw_account_box(draw, prog_x, wallet_y, box_w, box_h,
                         "Program Account", ORANGE, prog_fields, scan_y, True)

        # Labels below boxes
        draw.text((wallet_x + 60, wallet_y + box_h + 12),
                  "Holds SOL balance", fill=CYAN, font=font_10)
        draw.text((wallet_x + 60, wallet_y + box_h + 28),
                  "No code, no data storage", fill=DIM, font=font_10)

        draw.text((prog_x + 55, wallet_y + box_h + 12),
                  "Contains program bytecode", fill=ORANGE, font=font_10)
        draw.text((prog_x + 55, wallet_y + box_h + 28),
                  "Immutable after deployment", fill=DIM, font=font_10)

        # Connecting arrow between them
        arrow_phase = f
        mid_y = wallet_y + box_h // 2
        draw_arrow_between(draw, wallet_x + box_w + 8, mid_y,
                           prog_x - 8, mid_y, DIM, arrow_phase)

        # "invokes" label on arrow
        inv_text = "invokes"
        iw, _ = text_size(draw, inv_text, font_10)
        draw.text(((wallet_x + box_w + prog_x) // 2 - iw // 2, mid_y - 16),
                  inv_text, fill=DIM, font=font_10)

        # Bottom info bar
        bar_y = 460
        draw_rounded_rect(draw, (40, bar_y, W - 40, bar_y + 70), fill=DARK_BOX, outline=BORDER, radius=8)

        # Key insight
        key_text = "Key Insight:"
        draw.text((60, bar_y + 10), key_text, fill=YELLOW, font=font_bold_14)

        insight = "All on-chain state in Solana lives inside accounts."
        draw.text((60, bar_y + 32), insight, fill=WHITE, font=font_12)

        insight2 = "Programs are accounts too -- with executable = true."
        draw.text((60, bar_y + 50), insight2, fill=DIM, font=font_10)

        frames.append(img)

    return frames


if __name__ == "__main__":
    frames = generate_frames()
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DELAY, loop=0, optimize=True)
    print(f"Saved {OUT} ({len(frames)} frames)")
