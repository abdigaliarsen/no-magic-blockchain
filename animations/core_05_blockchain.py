"""
Generate animated GIF: "The Chain" — blocks linked by hashes.
Output: assets/gifs/core_05_blockchain.gif
"""

from PIL import Image, ImageDraw, ImageFont
import math
import hashlib

# === Canvas ===
W, H = 800, 550
FRAMES = 36
DELAY = 90  # ms

# === Colors ===
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

# Hash-matching colors — each block's hash gets a unique color
HASH_COLORS = [CYAN, GREEN, ORANGE, PURPLE]

# === Font Loading ===
def load_font(size, bold=False):
    paths = []
    if bold:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        ]
    else:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()

def load_mono(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()

font_title = load_font(26, bold=True)
font_header = load_font(14, bold=True)
font_body = load_font(12)
font_small = load_font(10)
font_mono = load_mono(12)
font_mono_sm = load_mono(10)

# === Block Data ===
def short_hash(s, length=8):
    return hashlib.sha256(s.encode()).hexdigest()[:length]

blocks = []
prev = "0" * 8
block_info = [
    ("#0 Genesis", "Genesis Block", "0" * 8),
    ("#1", "Alice -> Bob 5", None),
    ("#2", "Bob -> Carol 3", None),
    ("#3", "Carol -> Dave 1", None),
]

for i, (label, data, forced_prev) in enumerate(block_info):
    p = forced_prev if forced_prev is not None else prev
    raw = f"{p}{data}{i}"
    h = short_hash(raw)
    blocks.append({"label": label, "data": data, "prev_hash": p, "hash": h})
    prev = h

# === Drawing Helpers ===
def rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = xy
    r = radius
    # Four corner circles
    draw.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill, outline=outline, width=width)
    draw.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill, outline=outline, width=width)
    draw.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill, outline=outline, width=width)
    draw.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill, outline=outline, width=width)
    # Fill rectangles
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    # Outline edges (top, bottom, left, right)
    if outline:
        draw.line([x0 + r, y0, x1 - r, y0], fill=outline, width=width)
        draw.line([x0 + r, y1, x1 - r, y1], fill=outline, width=width)
        draw.line([x0, y0 + r, x0, y1 - r], fill=outline, width=width)
        draw.line([x1, y0 + r, x1, y1 - r], fill=outline, width=width)

def draw_marching_arrow(draw, x0, y0, x1, y1, color, frame, dash_len=6, gap_len=4):
    """Draw a horizontal marching-ant arrow from (x0,y0) to (x1,y1)."""
    total = dash_len + gap_len
    offset = (frame * 2) % total  # march speed
    length = abs(x1 - x0)
    direction = 1 if x1 > x0 else -1

    # Draw dashed line
    pos = 0
    while pos < length:
        seg_start = pos - offset
        if seg_start < 0:
            seg_start = 0
        seg_end = pos - offset + dash_len
        if seg_end < 0:
            pos += total
            continue
        seg_end = min(seg_end, length)
        seg_start = max(seg_start, 0)
        if seg_start < seg_end:
            sx = x0 + direction * seg_start
            ex = x0 + direction * seg_end
            draw.line([(sx, y0), (ex, y1)], fill=color, width=2)
        pos += total

    # Arrowhead at destination
    ah = 6  # arrowhead size
    if direction == -1:
        # Arrow pointing left
        draw.polygon([(x1, y1), (x1 + ah, y1 - ah), (x1 + ah, y1 + ah)], fill=color)
    else:
        draw.polygon([(x1, y1), (x1 - ah, y1 - ah), (x1 - ah, y1 + ah)], fill=color)

def text_centered(draw, x, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw // 2, y), text, font=font, fill=fill)

def text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]

# === Frame Generation ===
frames = []

# Block layout constants
NUM_BLOCKS = 4
BLOCK_W = 160
BLOCK_H = 165
BLOCK_GAP = 22
chain_total_w = NUM_BLOCKS * BLOCK_W + (NUM_BLOCKS - 1) * BLOCK_GAP
chain_x0 = (W - chain_total_w) // 2
CHAIN_Y = 65

for frame_idx in range(FRAMES):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # --- Title ---
    text_centered(draw, W // 2, 14, "The Blockchain: Linked by Hashes", font_title, WHITE)
    # Subtitle
    text_centered(draw, W // 2, 46, "Each block contains the previous block's hash, forming a tamper-evident chain",
                  font_small, DIM)

    # --- Draw Blocks ---
    block_positions = []  # store (x, y) for arrow drawing
    for i, blk in enumerate(blocks):
        bx = chain_x0 + i * (BLOCK_W + BLOCK_GAP)
        by = CHAIN_Y
        block_positions.append((bx, by))

        # Block background
        rounded_rect(draw, (bx, by, bx + BLOCK_W, by + BLOCK_H), 8,
                      fill=DARK_BOX, outline=BORDER, width=1)

        # Block label header bar
        draw.rectangle([bx + 1, by + 1, bx + BLOCK_W - 1, by + 26], fill=PANEL)
        hdr_color = CYAN if i == 0 else WHITE
        text_centered(draw, bx + BLOCK_W // 2, by + 5, blk["label"], font_header, hdr_color)

        # Separator
        draw.line([(bx + 8, by + 27), (bx + BLOCK_W - 8, by + 27)], fill=BORDER, width=1)

        # prev_hash
        prev_label = "prev:"
        prev_val = blk["prev_hash"]
        # Color-match prev_hash to the previous block's hash color
        prev_color = DIM if i == 0 else HASH_COLORS[(i - 1) % len(HASH_COLORS)]
        draw.text((bx + 8, by + 33), prev_label, font=font_mono_sm, fill=DIM)
        draw.text((bx + 8 + 42, by + 33), prev_val, font=font_mono_sm, fill=prev_color)

        # Separator
        draw.line([(bx + 8, by + 50), (bx + BLOCK_W - 8, by + 50)], fill=BORDER, width=1)

        # Data
        draw.text((bx + 8, by + 56), "data:", font=font_mono_sm, fill=DIM)
        # Truncate data if needed
        dtext = blk["data"]
        if len(dtext) > 16:
            dtext = dtext[:15] + ".."
        draw.text((bx + 8, by + 70), dtext, font=font_mono_sm, fill=WHITE)

        # Separator
        draw.line([(bx + 8, by + 88), (bx + BLOCK_W - 8, by + 88)], fill=BORDER, width=1)

        # Hash — highlighted with unique color
        hash_color = HASH_COLORS[i % len(HASH_COLORS)]
        draw.text((bx + 8, by + 94), "hash:", font=font_mono_sm, fill=DIM)

        # Hash value background highlight
        hv_x = bx + 8
        hv_y = by + 108
        hv_text = blk["hash"]
        hvw = text_width(draw, hv_text, font_mono_sm)
        # Subtle background behind hash
        bg_colors = [CYAN_BG, GREEN_BG, YELLOW_BG, PURPLE_BG]
        draw.rectangle([hv_x - 2, hv_y - 1, hv_x + hvw + 3, hv_y + 14], fill=bg_colors[i % len(bg_colors)])
        draw.text((hv_x, hv_y), hv_text, font=font_mono_sm, fill=hash_color)

        # Small chain link icon at bottom
        if i < NUM_BLOCKS - 1:
            # Draw chain link symbol between blocks
            link_x = bx + BLOCK_W + BLOCK_GAP // 2
            link_y = by + BLOCK_H // 2
            # Small dot
            draw.ellipse([link_x - 3, link_y - 3, link_x + 3, link_y + 3], fill=BORDER)

    # --- Marching-ant arrows (prev_hash <- hash links) ---
    for i in range(1, NUM_BLOCKS):
        # Arrow from prev_hash field of block i back to hash field of block i-1
        src_x = block_positions[i][0] + 8  # left edge of prev_hash in block i
        src_y = block_positions[i][1] + 40  # vertical center of prev_hash row

        dst_x = block_positions[i-1][0] + BLOCK_W - 8  # right edge of hash in block i-1
        dst_y = block_positions[i-1][1] + 115  # vertical center of hash row

        arrow_color = HASH_COLORS[(i - 1) % len(HASH_COLORS)]

        # Draw a bent arrow: horizontal from src left, then a short connector
        # Path: from src left edge, go left into the gap, then bend to dst right edge
        mid_x = block_positions[i][0] - BLOCK_GAP // 2
        mid_y_top = src_y
        mid_y_bot = dst_y

        # Vertical segment in the gap
        v_top = min(mid_y_top, mid_y_bot)
        v_bot = max(mid_y_top, mid_y_bot)

        # Marching horizontal segment: src to mid
        draw_marching_arrow(draw, src_x, src_y, mid_x + 3, src_y, arrow_color, frame_idx)

        # Vertical dashed segment
        total = 10
        offset = (frame_idx * 2) % total
        pos = 0
        seg_len = v_bot - v_top
        while pos < seg_len:
            s = pos - offset
            e = s + 6
            s = max(s, 0)
            e = min(e, seg_len)
            if s < e:
                draw.line([(mid_x, v_top + s), (mid_x, v_top + e)], fill=arrow_color, width=2)
            pos += total

        # Horizontal segment: mid to dst
        draw_marching_arrow(draw, mid_x - 3, dst_y, dst_x, dst_y, arrow_color, frame_idx)

    # --- Tamper Detection Panel ---
    panel_y = CHAIN_Y + BLOCK_H + 30
    panel_h = 90
    panel_x = 30
    panel_w = W - 60
    rounded_rect(draw, (panel_x, panel_y, panel_x + panel_w, panel_y + panel_h), 8,
                  fill=RED_BG, outline=(80, 40, 40), width=1)

    # Panel title
    draw.text((panel_x + 16, panel_y + 8), "TAMPER DETECTION", font=font_header, fill=RED)

    # Show what happens when Block #1 is changed
    desc_y = panel_y + 28
    draw.text((panel_x + 16, desc_y),
              "If Block #1 data is changed, its hash changes", font=font_body, fill=WHITE)
    draw.text((panel_x + 16, desc_y + 18),
              "-> Block #2 prev_hash no longer matches -> chain is BROKEN", font=font_body, fill=ORANGE)

    # Visual: mini chain with X marks — animated flicker
    mini_y = desc_y + 42
    mini_bw = 80
    mini_bh = 18
    labels = ["#0", "#1 (changed)", "#2", "#3"]
    colors_border = [GREEN, RED, RED, RED]
    x_start = panel_x + 60

    for i, (lbl, col) in enumerate(zip(labels, colors_border)):
        mx = x_start + i * (mini_bw + 30)
        # Flicker: blocks after tampering flash
        if i >= 1:
            # Pulsing alpha effect via color mixing
            pulse = 0.5 + 0.5 * math.sin(frame_idx * 0.35 + i)
            rc = tuple(int(c * pulse + BG[j] * (1 - pulse)) for j, c in enumerate(col))
        else:
            rc = col
        draw.rectangle([mx, mini_y, mx + mini_bw, mini_y + mini_bh], outline=rc, width=1)
        text_centered(draw, mx + mini_bw // 2, mini_y + 2, lbl, font_small, rc)

        # X marks between broken links
        if i >= 2:
            xx = mx - 15
            xy = mini_y + mini_bh // 2
            draw.line([(xx - 5, xy - 5), (xx + 5, xy + 5)], fill=RED, width=2)
            draw.line([(xx - 5, xy + 5), (xx + 5, xy - 5)], fill=RED, width=2)
        elif i == 1:
            # Checkmark for link 0->1 originally OK, but now the block itself is red
            xx = mx - 15
            xy = mini_y + mini_bh // 2
            # Show an X here too since block 1 changed means its hash changed
            # so link from block 2's prev_hash is broken
            draw.text((xx - 4, xy - 7), "!", font=font_header, fill=YELLOW)

    # --- Bottom Badges ---
    badge_y = H - 48
    badges = [
        ("APPEND-ONLY", CYAN, CYAN_BG),
        ("TAMPER-EVIDENT", GREEN, GREEN_BG),
        ("DISTRIBUTED LEDGER", PURPLE, PURPLE_BG),
    ]
    badge_w = 180
    badge_h = 28
    badge_gap = 30
    total_badges_w = len(badges) * badge_w + (len(badges) - 1) * badge_gap
    badge_x0 = (W - total_badges_w) // 2

    for j, (label, fg, bg_c) in enumerate(badges):
        bx = badge_x0 + j * (badge_w + badge_gap)
        rounded_rect(draw, (bx, badge_y, bx + badge_w, badge_y + badge_h), 6,
                      fill=bg_c, outline=fg, width=1)
        text_centered(draw, bx + badge_w // 2, badge_y + 6, label, font_small, fg)

    frames.append(img)

# === Save GIF ===
frames[0].save(
    "assets/gifs/core_05_blockchain.gif",
    save_all=True,
    append_images=frames[1:],
    duration=DELAY,
    loop=0,
    optimize=True,
)
print("GIF saved to assets/gifs/core_05_blockchain.gif")
print(f"  {FRAMES} frames, {DELAY}ms delay, {W}x{H}px")
