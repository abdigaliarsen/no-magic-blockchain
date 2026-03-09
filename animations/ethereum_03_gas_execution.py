"""
Variant B: "EIP-1559 Fee Market" -- Base fee + priority fee, block fullness
affects base fee. Generates assets/gifs/ethereum_03_gas_execution.gif (800x550, 36 frames, 90ms delay)
"""

from PIL import Image, ImageDraw, ImageFont
import math

# ---------------------------------------------------------------------------
# COLORS
# ---------------------------------------------------------------------------
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

W, H = 800, 550
FRAMES = 36
DELAY = 90

# ---------------------------------------------------------------------------
# FONTS
# ---------------------------------------------------------------------------
def load_fonts():
    try:
        bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
        hdr = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        big_num = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except Exception:
        bold = hdr = body = small = big_num = ImageFont.load_default()
    return bold, hdr, body, small, big_num

FONT_TITLE, FONT_HDR, FONT_BODY, FONT_SMALL, FONT_BIG = load_fonts()

# ---------------------------------------------------------------------------
# SIMULATION DATA -- 8 blocks with varying fullness
# ---------------------------------------------------------------------------
# (block_num, fullness 0..1, tx_count)
BLOCKS = [
    (101, 0.45, 120),
    (102, 0.80, 210),
    (103, 0.95, 280),
    (104, 0.92, 265),
    (105, 0.60, 160),
    (106, 0.30, 85),
    (107, 0.25, 70),
    (108, 0.55, 150),
]

TARGET_FULLNESS = 0.5  # 50% = target gas usage

def compute_base_fees(blocks):
    """Simulate EIP-1559 base fee adjustment."""
    base = 20.0  # starting base fee in gwei
    fees = [base]
    for _, fullness, _ in blocks:
        delta = (fullness - TARGET_FULLNESS) / TARGET_FULLNESS
        change = base * delta * 0.125  # max 12.5% change per block
        base = max(1.0, base + change)
        fees.append(base)
    return fees

BASE_FEES = compute_base_fees(BLOCKS)

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def draw_rounded_rect(draw, xy, fill, outline, r=6):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)

def lerp(a, b, t):
    return a + (b - a) * t

def fullness_color(f):
    if f < 0.4:
        return GREEN
    elif f < 0.7:
        return YELLOW
    elif f < 0.9:
        return ORANGE
    return RED

# ---------------------------------------------------------------------------
# BUILD FRAMES
# ---------------------------------------------------------------------------
frames = []

for fi in range(FRAMES):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = fi / (FRAMES - 1)

    # --- Title ---
    draw.text((30, 16), "EIP-1559 Fee Market", fill=WHITE, font=FONT_TITLE)
    draw.text((340, 22), "-- Base fee adjusts with block fullness", fill=DIM, font=FONT_BODY)
    draw.line([(30, 52), (W - 30, 52)], fill=BORDER, width=1)

    # === TOP ROW: Block sequence ===
    # Show 8 blocks horizontally, each as a box with fullness bar
    block_panel_y = 62
    draw_rounded_rect(draw, (30, block_panel_y, W - 30, 250), PANEL, BORDER)
    draw.text((42, block_panel_y + 8), "BLOCK SEQUENCE", fill=CYAN, font=FONT_HDR)
    draw.text((200, block_panel_y + 10), "50% target gas", fill=DIM, font=FONT_SMALL)

    # Scan line: which block is highlighted
    scan_idx = t * len(BLOCKS)
    active_block = min(int(scan_idx), len(BLOCKS) - 1)

    block_w = 78
    block_gap = 10
    total_bw = len(BLOCKS) * block_w + (len(BLOCKS) - 1) * block_gap
    bx_start = (W - total_bw) // 2
    block_top = block_panel_y + 32

    for i, (bnum, fullness, txc) in enumerate(BLOCKS):
        bx = bx_start + i * (block_w + block_gap)
        by = block_top

        is_active = (i == active_block)
        box_fill = CYAN_BG if is_active else DARK_BOX
        box_border = CYAN if is_active else BORDER
        draw_rounded_rect(draw, (bx, by, bx + block_w, by + 130), box_fill, box_border)

        # Block number
        lbl = f"#{bnum}"
        lw, _ = text_size(draw, lbl, FONT_SMALL)
        draw.text((bx + (block_w - lw) // 2, by + 4), lbl, fill=WHITE if is_active else DIM, font=FONT_SMALL)

        # Fullness bar inside block
        bar_x = bx + 8
        bar_w_inner = block_w - 16
        bar_h = 60
        bar_y = by + 22
        draw_rounded_rect(draw, (bar_x, bar_y, bar_x + bar_w_inner, bar_y + bar_h), DARK_BOX, BORDER, r=3)

        # Filled portion (from bottom)
        fill_h = int(bar_h * fullness)
        if fill_h > 1:
            fc = fullness_color(fullness)
            fy = bar_y + bar_h - fill_h
            draw_rounded_rect(draw, (bar_x + 1, fy, bar_x + bar_w_inner - 1, bar_y + bar_h - 1),
                              (*fc, ), fc, r=2)

        # 50% target line
        target_y = bar_y + bar_h - int(bar_h * 0.5)
        draw.line([(bar_x, target_y), (bar_x + bar_w_inner, target_y)], fill=DIM, width=1)

        # Percentage label
        pct_str = f"{fullness*100:.0f}%"
        pw, _ = text_size(draw, pct_str, FONT_SMALL)
        draw.text((bx + (block_w - pw) // 2, bar_y + bar_h + 4), pct_str,
                  fill=fullness_color(fullness), font=FONT_SMALL)

        # Tx count
        tx_str = f"{txc} tx"
        tw, _ = text_size(draw, tx_str, FONT_SMALL)
        draw.text((bx + (block_w - tw) // 2, bar_y + bar_h + 16), tx_str, fill=DIM, font=FONT_SMALL)

        # Arrow between blocks (animated scan)
        if i < len(BLOCKS) - 1:
            ax = bx + block_w + 2
            pulse = 1.0 if i == active_block else 0.3
            ac = (*CYAN[:3],) if i == active_block else BORDER
            draw.text((ax, by + 55), "->", fill=ac, font=FONT_SMALL)

    # === BOTTOM LEFT: Fee breakdown ===
    fee_panel_y = 268
    draw_rounded_rect(draw, (30, fee_panel_y, 390, H - 30), PANEL, BORDER)
    draw.text((42, fee_panel_y + 10), "FEE STRUCTURE", fill=PURPLE, font=FONT_HDR)

    base_fee = BASE_FEES[active_block]
    priority_fee = 2.0  # constant tip
    total_fee = base_fee + priority_fee

    # Base fee box (burned)
    bf_y = fee_panel_y + 36
    draw_rounded_rect(draw, (44, bf_y, 370, bf_y + 60), RED_BG, RED)
    draw.text((56, bf_y + 6), "BASE FEE (burned)", fill=RED, font=FONT_HDR)
    draw.text((56, bf_y + 28), f"{base_fee:.1f} gwei", fill=WHITE, font=FONT_BIG)
    # Burn icon
    draw.text((280, bf_y + 28), "BURNED", fill=RED, font=FONT_SMALL)

    # Priority fee box (to validator)
    pf_y = bf_y + 72
    draw_rounded_rect(draw, (44, pf_y, 370, pf_y + 60), GREEN_BG, GREEN)
    draw.text((56, pf_y + 6), "PRIORITY FEE (to validator)", fill=GREEN, font=FONT_HDR)
    draw.text((56, pf_y + 28), f"{priority_fee:.1f} gwei", fill=WHITE, font=FONT_BIG)
    draw.text((280, pf_y + 28), "TIP", fill=GREEN, font=FONT_SMALL)

    # Total
    tot_y = pf_y + 72
    draw_rounded_rect(draw, (44, tot_y, 370, tot_y + 40), PURPLE_BG, PURPLE)
    draw.text((56, tot_y + 8), "TOTAL:", fill=PURPLE, font=FONT_HDR)
    draw.text((140, tot_y + 6), f"{total_fee:.1f} gwei / gas unit", fill=WHITE, font=FONT_HDR)

    # === BOTTOM RIGHT: Base fee chart ===
    chart_x, chart_y = 410, fee_panel_y
    draw_rounded_rect(draw, (chart_x, chart_y, W - 30, H - 30), PANEL, BORDER)
    draw.text((chart_x + 12, chart_y + 10), "BASE FEE TREND", fill=ORANGE, font=FONT_HDR)

    # Draw line chart of base fees
    chart_l = chart_x + 40
    chart_r = W - 50
    chart_t = chart_y + 40
    chart_b = H - 55

    # Y axis
    draw.line([(chart_l, chart_t), (chart_l, chart_b)], fill=DIM, width=1)
    draw.line([(chart_l, chart_b), (chart_r, chart_b)], fill=DIM, width=1)

    max_fee = max(BASE_FEES) * 1.15
    min_fee = 0

    # Grid lines
    for gv in [10, 20, 30]:
        gy = chart_b - int((gv - min_fee) / (max_fee - min_fee) * (chart_b - chart_t))
        draw.line([(chart_l, gy), (chart_r, gy)], fill=BORDER, width=1)
        draw.text((chart_l - 22, gy - 5), str(gv), fill=DIM, font=FONT_SMALL)

    # Plot points and lines
    pts = []
    for i in range(len(BASE_FEES)):
        px = chart_l + int(i / (len(BASE_FEES) - 1) * (chart_r - chart_l))
        py = chart_b - int((BASE_FEES[i] - min_fee) / (max_fee - min_fee) * (chart_b - chart_t))
        pts.append((px, py))

    for i in range(len(pts) - 1):
        c = ORANGE if i <= active_block else BORDER
        draw.line([pts[i], pts[i + 1]], fill=c, width=2)

    # Dots
    for i, (px, py) in enumerate(pts):
        dot_c = WHITE if i == active_block else (ORANGE if i <= active_block else BORDER)
        r = 5 if i == active_block else 3
        draw.ellipse((px - r, py - r, px + r, py + r), fill=dot_c)

    # Active point label
    if active_block < len(pts):
        apx, apy = pts[active_block]
        lbl = f"{BASE_FEES[active_block]:.1f}"
        draw.text((apx + 8, apy - 14), lbl, fill=WHITE, font=FONT_SMALL)

    # Arrow indicator
    if active_block > 0:
        delta = BASE_FEES[active_block] - BASE_FEES[active_block - 1]
        direction = "UP" if delta > 0 else "DOWN"
        dc = RED if delta > 0 else GREEN
        draw.text((chart_r - 60, chart_t), direction, fill=dc, font=FONT_HDR)

    # X axis labels
    draw.text((chart_l - 5, chart_b + 5), "blocks ->", fill=DIM, font=FONT_SMALL)

    frames.append(img)

# ---------------------------------------------------------------------------
# SAVE
# ---------------------------------------------------------------------------
frames[0].save(
    "assets/gifs/ethereum_03_gas_execution.gif",
    save_all=True,
    append_images=frames[1:],
    duration=DELAY,
    loop=0,
    optimize=True,
)
print("Saved assets/gifs/ethereum_03_gas_execution.gif")
