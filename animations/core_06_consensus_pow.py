"""
Proof of Work - Variant B: "Difficulty Adjustment"
Generates an 800x550 GIF showing how mining difficulty changes,
comparing easy vs hard targets with visual target bars.
"""

from PIL import Image, ImageDraw, ImageFont
import hashlib

# ==========================================================================
# COLORS
# ==========================================================================
BG = (13, 17, 23)
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
RED = (248, 113, 113)
PURPLE = (167, 139, 250)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)

CYAN_BG = (18, 50, 68)
PURPLE_BG = (35, 28, 58)
YELLOW_BG = (58, 50, 14)
GREEN_BG = (14, 48, 40)
RED_BG = (50, 20, 20)

PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)

# ==========================================================================
# FONTS
# ==========================================================================
def load_fonts():
    bold_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    regular_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    mono_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]

    def try_load(paths, size):
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()

    return {
        "title": try_load(bold_paths, 26),
        "header": try_load(bold_paths, 14),
        "header_lg": try_load(bold_paths, 16),
        "body": try_load(regular_paths, 12),
        "small": try_load(regular_paths, 10),
        "mono": try_load(mono_paths, 12),
        "mono_lg": try_load(mono_paths, 14),
        "mono_sm": try_load(mono_paths, 10),
    }

# ==========================================================================
# DIFFICULTY CONFIGURATIONS
# ==========================================================================
DIFFICULTIES = [
    {
        "label": "Easy",
        "zeros": 1,
        "prefix": "0",
        "target_frac": 0.45,   # wide target bar
        "color": GREEN,
        "bg": GREEN_BG,
        "avg_attempts": "~16",
        "block_time": "Fast",
    },
    {
        "label": "Medium",
        "zeros": 2,
        "prefix": "00",
        "target_frac": 0.22,
        "color": YELLOW,
        "bg": YELLOW_BG,
        "avg_attempts": "~256",
        "block_time": "Moderate",
    },
    {
        "label": "Hard",
        "zeros": 3,
        "prefix": "000",
        "target_frac": 0.08,
        "color": RED,
        "bg": RED_BG,
        "avg_attempts": "~4,096",
        "block_time": "Slow",
    },
]

# Precompute example hashes for each difficulty
def find_hash(prefix, data="block_data"):
    for n in range(200000):
        h = hashlib.sha256(f"{data}|{n}".encode()).hexdigest()
        if h.startswith(prefix):
            return n, h
    return 0, "0" * 64

EXAMPLES = []
for i, d in enumerate(DIFFICULTIES):
    nonce, h = find_hash(d["prefix"], f"block_{i}")
    EXAMPLES.append({"nonce": nonce, "hash": h})

# ==========================================================================
# DRAWING HELPERS
# ==========================================================================
def draw_rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = xy
    r = radius
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.pieslice([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=fill)
    draw.pieslice([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2*r, x0 + 2*r, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2*r, y1 - 2*r, x1, y1], 0, 90, fill=fill)
    if outline:
        draw.line([x0 + r, y0, x1 - r, y0], fill=outline, width=width)
        draw.line([x0 + r, y1, x1 - r, y1], fill=outline, width=width)
        draw.line([x0, y0 + r, x0, y1 - r], fill=outline, width=width)
        draw.line([x1, y0 + r, x1, y1 - r], fill=outline, width=width)
        draw.arc([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=outline, width=width)
        draw.arc([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=outline, width=width)
        draw.arc([x0, y1 - 2*r, x0 + 2*r, y1], 90, 180, fill=outline, width=width)
        draw.arc([x1 - 2*r, y1 - 2*r, x1, y1], 0, 90, fill=outline, width=width)

def text_center(draw, text, x, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((x - tw // 2, y - th // 2), text, font=font, fill=fill)

def draw_arrow_down(draw, x, y0, y1, color, width=2):
    draw.line([x, y0, x, y1 - 6], fill=color, width=width)
    draw.polygon([(x, y1), (x - 5, y1 - 8), (x + 5, y1 - 8)], fill=color)

# ==========================================================================
# FRAME GENERATION
# ==========================================================================
def generate_frame(frame_idx, fonts):
    W, H = 800, 550
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Title
    text_center(draw, "Proof of Work: Difficulty Adjustment", W // 2, 28, fonts["title"], CYAN)

    # Scan line
    scan_y = 50 + (frame_idx * 15) % 490
    draw.line([0, scan_y, W, scan_y], fill=(30, 40, 55), width=1)

    # =====================================================================
    # TOP: Three block columns showing different difficulties
    # =====================================================================
    col_w = 230
    col_gap = 20
    start_x = (W - (3 * col_w + 2 * col_gap)) // 2
    top_y = 58

    for i, diff in enumerate(DIFFICULTIES):
        cx = start_x + i * (col_w + col_gap)
        ex = EXAMPLES[i]

        # Column panel
        panel_h = 235
        draw_rounded_rect(draw, (cx, top_y, cx + col_w, top_y + panel_h), 8,
                           fill=PANEL, outline=diff["color"], width=2)

        # Difficulty label badge
        badge_w = 90
        badge_x = cx + (col_w - badge_w) // 2
        draw_rounded_rect(draw, (badge_x, top_y + 8, badge_x + badge_w, top_y + 28), 6,
                           fill=diff["bg"], outline=diff["color"], width=1)
        text_center(draw, diff["label"], badge_x + badge_w // 2, top_y + 18, fonts["header"], diff["color"])

        # Leading zeros requirement
        zeros_text = f"Require: {diff['zeros']} leading zero(s)"
        text_center(draw, zeros_text, cx + col_w // 2, top_y + 42, fonts["small"], DIM)

        # Target bar visualization
        bar_x = cx + 15
        bar_y = top_y + 58
        bar_w = col_w - 30
        bar_h = 24

        # Background (full hash space)
        for bx_i in range(bar_w):
            ratio = bx_i / bar_w
            c = int(20 + ratio * 35)
            draw.line([bar_x + bx_i, bar_y, bar_x + bx_i, bar_y + bar_h],
                      fill=(c, c, c + 8))

        # Valid zone (green/yellow/red fill)
        target_px = int(diff["target_frac"] * bar_w)
        draw_rounded_rect(draw, (bar_x, bar_y, bar_x + target_px, bar_y + bar_h), 2,
                           fill=diff["bg"])

        # Target line
        tl_x = bar_x + target_px
        draw.line([tl_x, bar_y - 3, tl_x, bar_y + bar_h + 3], fill=diff["color"], width=2)

        # Animated hash dot bouncing in the bar
        # Simulate random hash positions using frame_idx
        pseudo_pos = ((frame_idx * 7 + i * 13) * 2654435761) % bar_w
        dot_x = bar_x + pseudo_pos
        dot_in_range = pseudo_pos < target_px
        dot_color = diff["color"] if dot_in_range else DIM
        draw.ellipse([dot_x - 3, bar_y + bar_h // 2 - 3, dot_x + 3, bar_y + bar_h // 2 + 3],
                     fill=dot_color)

        # Labels under bar
        draw.text((bar_x, bar_y + bar_h + 3), "Valid", font=fonts["small"], fill=diff["color"])
        r_text = "Invalid"
        r_bbox = draw.textbbox((0, 0), r_text, font=fonts["small"])
        draw.text((bar_x + bar_w - (r_bbox[2] - r_bbox[0]), bar_y + bar_h + 3),
                  r_text, font=fonts["small"], fill=DIM)

        # Example hash (show leading zeros highlighted)
        hash_y = bar_y + bar_h + 22
        draw.text((cx + 10, hash_y), "Example valid hash:", font=fonts["small"], fill=DIM)
        hash_row_y = hash_y + 14
        hx = cx + 10
        for j in range(min(26, len(ex["hash"]))):
            ch = ex["hash"][j]
            if j < diff["zeros"]:
                draw.text((hx, hash_row_y), ch, font=fonts["mono_sm"], fill=diff["color"])
            else:
                draw.text((hx, hash_row_y), ch, font=fonts["mono_sm"], fill=DIM)
            hx += 8
        draw.text((hx, hash_row_y), "...", font=fonts["mono_sm"], fill=DIM)

        # Stats
        stats_y = hash_row_y + 20
        draw.text((cx + 10, stats_y), f"Avg attempts: {diff['avg_attempts']}", font=fonts["small"], fill=WHITE)
        draw.text((cx + 10, stats_y + 14), f"Speed: {diff['block_time']}", font=fonts["small"], fill=diff["color"])
        draw.text((cx + 10, stats_y + 28), f"Nonce found: {ex['nonce']}", font=fonts["small"], fill=DIM)

    # =====================================================================
    # MIDDLE: Comparison arrows
    # =====================================================================
    compare_y = top_y + 245
    arrow_y = compare_y + 8

    # Arrow from Easy to Hard
    ax1 = start_x + col_w // 2
    ax2 = start_x + 2 * (col_w + col_gap) + col_w // 2
    draw.line([ax1, arrow_y, ax2, arrow_y], fill=BORDER, width=2)
    # Arrowhead
    draw.polygon([(ax2, arrow_y), (ax2 - 8, arrow_y - 4), (ax2 - 8, arrow_y + 4)], fill=BORDER)
    text_center(draw, "Increasing Difficulty", (ax1 + ax2) // 2, arrow_y - 12, fonts["small"], DIM)
    text_center(draw, "More zeros required = harder to find valid hash",
                (ax1 + ax2) // 2, arrow_y + 10, fonts["small"], DIM)

    # =====================================================================
    # BOTTOM: Adjustment mechanism panel
    # =====================================================================
    panel_y = 330
    panel_h = 100
    draw_rounded_rect(draw, (30, panel_y, 770, panel_y + panel_h), 8,
                       fill=PANEL, outline=BORDER, width=1)

    draw.text((50, panel_y + 8), "How Difficulty Adjusts", font=fonts["header_lg"], fill=WHITE)

    # Two scenarios side by side
    sc_y = panel_y + 32
    mid_x = 400

    # Left: blocks too fast
    draw_rounded_rect(draw, (50, sc_y, mid_x - 20, sc_y + 55), 6,
                       fill=RED_BG, outline=RED, width=1)
    draw.text((60, sc_y + 4), "Blocks mined TOO FAST", font=fonts["header"], fill=RED)
    draw.text((60, sc_y + 22), "Avg time < 10 min", font=fonts["mono_sm"], fill=DIM)
    draw.text((60, sc_y + 36), "-> Increase difficulty (more zeros)", font=fonts["small"], fill=ORANGE)

    # Animated pulse on the active scenario
    pulse = 2 if frame_idx % 6 < 3 else 0

    # Right: blocks too slow
    draw_rounded_rect(draw, (mid_x, sc_y, 750, sc_y + 55), 6,
                       fill=GREEN_BG, outline=GREEN, width=1)
    draw.text((mid_x + 10, sc_y + 4), "Blocks mined TOO SLOW", font=fonts["header"], fill=GREEN)
    draw.text((mid_x + 10, sc_y + 22), "Avg time > 10 min", font=fonts["mono_sm"], fill=DIM)
    draw.text((mid_x + 10, sc_y + 36), "-> Decrease difficulty (fewer zeros)", font=fonts["small"], fill=GREEN)

    # =====================================================================
    # BOTTOM: Bitcoin info badges
    # =====================================================================
    badge_y = 445
    badges = [
        ("Bitcoin target: 10 min/block", CYAN, CYAN_BG),
        ("Adjusts every 2016 blocks (~2 weeks)", PURPLE, PURPLE_BG),
        ("Difficulty has increased 50+ trillion times", ORANGE, YELLOW_BG),
    ]
    badge_w = 240
    badge_gap = 10
    total_badges_w = len(badges) * badge_w + (len(badges) - 1) * badge_gap
    bx_start = (W - total_badges_w) // 2

    for j, (text, color, bg) in enumerate(badges):
        bx = bx_start + j * (badge_w + badge_gap)
        draw_rounded_rect(draw, (bx, badge_y, bx + badge_w, badge_y + 36), 6,
                           fill=bg, outline=color, width=1)
        text_center(draw, text, bx + badge_w // 2, badge_y + 18, fonts["small"], color)

    # =====================================================================
    # BOTTOM: Key insight
    # =====================================================================
    insight_y = 497
    draw_rounded_rect(draw, (30, insight_y, 770, insight_y + 40), 8,
                       fill=CYAN_BG, outline=CYAN, width=1)
    text_center(draw, "Difficulty auto-adjusts so blocks arrive at a steady rate",
                W // 2, insight_y + 12, fonts["body"], CYAN)
    text_center(draw, "regardless of how much total computing power joins or leaves the network",
                W // 2, insight_y + 28, fonts["small"], DIM)

    return img


# ==========================================================================
# MAIN
# ==========================================================================
def main():
    fonts = load_fonts()
    frames = [generate_frame(i, fonts) for i in range(36)]
    frames[0].save(
        "assets/gifs/core_06_consensus_pow.gif",
        save_all=True,
        append_images=frames[1:],
        duration=90,
        loop=0,
        optimize=True,
    )
    print("Saved assets/gifs/core_06_consensus_pow.gif")

if __name__ == "__main__":
    main()
