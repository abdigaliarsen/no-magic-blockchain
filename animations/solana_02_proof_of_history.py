"""
Variant C: "Event Ordering" — Events embedded into PoH chain.
Side-by-side: Before PoH (ambiguous order) vs After PoH (provable order).
Animated scan line highlights the ordering proof.
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- Config ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/solana_02_proof_of_history.gif"

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
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    font_mid = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
except:
    font_title = ImageFont.load_default()
    font_header = font_title
    font_body = font_title
    font_small = font_title
    font_mid = font_title


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def draw_rounded_rect(draw, xy, fill, outline=None, radius=6):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def draw_arrow_down(draw, x, y1, y2, color, width=1):
    draw.line([(x, y1), (x, y2)], fill=color, width=width)
    draw.polygon([(x, y2), (x - 4, y2 - 7), (x + 4, y2 - 7)], fill=color)


def make_frame(frame_idx):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = frame_idx / (FRAMES - 1)

    # --- Title ---
    title = "Proof of History: Event Ordering"
    tw, th = text_size(draw, title, font_title)
    draw.text(((W - tw) // 2, 14), title, fill=CYAN, font=font_title)

    subtitle = "Cryptographic proof of event sequence"
    sw, sh = text_size(draw, subtitle, font_body)
    draw.text(((W - sw) // 2, 46), subtitle, fill=DIM, font=font_body)

    # --- Layout: Left panel (Before PoH), Right panel (After PoH) ---
    panel_w = 340
    left_x = 30
    right_x = W - 30 - panel_w
    panel_top = 75
    panel_bot = 390

    # Events
    events = [
        ("Tx1: Alice -> Bob", CYAN),
        ("Tx2: Carol -> Dave", GREEN),
        ("Tx3: Eve -> Frank", YELLOW),
        ("Tx4: Grace -> Hank", ORANGE),
    ]

    # ========== LEFT PANEL: Before PoH ==========
    draw_rounded_rect(draw, (left_x, panel_top, left_x + panel_w, panel_bot),
                      fill=PANEL, outline=BORDER)

    lbl = "WITHOUT Proof of History"
    lw, lh = text_size(draw, lbl, font_header)
    draw.text((left_x + (panel_w - lw) // 2, panel_top + 10), lbl, fill=RED, font=font_header)

    # Question marks and shuffled events
    # Events float around with ambiguous ordering
    question = "Order unknown -- nodes disagree"
    qw, qh = text_size(draw, question, font_small)
    draw.text((left_x + (panel_w - qw) // 2, panel_top + 32), question, fill=RED, font=font_small)

    # Draw events in a scattered/shuffled arrangement
    # They wobble to show uncertainty
    event_box_w = 150
    event_box_h = 28
    center_lx = left_x + panel_w // 2

    # Shuffle indices that cycle
    shuffle_orders = [
        [2, 0, 3, 1],
        [3, 1, 0, 2],
        [1, 3, 2, 0],
    ]
    shuffle = shuffle_orders[frame_idx % len(shuffle_orders)]

    for draw_i in range(4):
        event_i = shuffle[draw_i]
        label, color = events[event_i]

        # Position with wobble
        wobble_x = 12 * math.sin(t * math.pi * 4 + event_i * 1.5)
        wobble_y = 6 * math.cos(t * math.pi * 3 + event_i * 2.0)

        ey = panel_top + 55 + draw_i * (event_box_h + 18)
        ex = center_lx - event_box_w // 2 + int(wobble_x)
        ey_actual = ey + int(wobble_y)

        draw_rounded_rect(draw,
                          (ex, ey_actual, ex + event_box_w, ey_actual + event_box_h),
                          fill=RED_BG, outline=lerp_color(BORDER, RED, 0.4))

        elw, elh = text_size(draw, label, font_small)
        draw.text((ex + (event_box_w - elw) // 2, ey_actual + 7), label,
                  fill=lerp_color(DIM, color, 0.5), font=font_small)

        # Question mark beside each
        qx = ex + event_box_w + 8
        draw.text((qx, ey_actual + 5), "?", fill=RED, font=font_header)

    # Red X
    x_text = "X  No consensus on order"
    xw, xh = text_size(draw, x_text, font_header)
    draw.text((left_x + (panel_w - xw) // 2, panel_bot - 35), x_text, fill=RED, font=font_header)

    # ========== RIGHT PANEL: After PoH ==========
    draw_rounded_rect(draw, (right_x, panel_top, right_x + panel_w, panel_bot),
                      fill=PANEL, outline=BORDER)

    lbl2 = "WITH Proof of History"
    lw2, lh2 = text_size(draw, lbl2, font_header)
    draw.text((right_x + (panel_w - lw2) // 2, panel_top + 10), lbl2, fill=GREEN, font=font_header)

    proven = "Order cryptographically proven"
    pw, ph = text_size(draw, proven, font_small)
    draw.text((right_x + (panel_w - pw) // 2, panel_top + 32), proven, fill=GREEN, font=font_small)

    # Events in fixed order with hash chain links
    center_rx = right_x + panel_w // 2
    hash_chain_x = center_rx + event_box_w // 2 + 35

    # Scan line (vertical, moves down the right panel)
    scan_y = panel_top + 55 + t * (4 * (event_box_h + 18))

    for i in range(4):
        label, color = events[i]
        ey = panel_top + 55 + i * (event_box_h + 18)
        ex = center_rx - event_box_w // 2 - 20

        # Highlight based on scan proximity
        dist = abs(scan_y - (ey + event_box_h // 2))
        highlight = max(0, 1.0 - dist / 50)

        box_outline = lerp_color(BORDER, color, 0.3 + highlight * 0.7)
        box_fill = lerp_color(DARK_BOX, GREEN_BG, highlight * 0.4)

        draw_rounded_rect(draw,
                          (ex, ey, ex + event_box_w, ey + event_box_h),
                          fill=box_fill, outline=box_outline)

        elw, elh = text_size(draw, label, font_small)
        draw.text((ex + (event_box_w - elw) // 2, ey + 7), label,
                  fill=lerp_color(DIM, color, 0.5 + highlight * 0.5), font=font_small)

        # Slot number
        slot_text = f"Slot {i + 1}"
        slw, slh = text_size(draw, slot_text, font_small)
        draw.text((ex - slw - 8, ey + 7), slot_text,
                  fill=lerp_color(DIM, PURPLE, highlight), font=font_small)

        # Hash link box (to the right)
        hx = ex + event_box_w + 10
        hw = 70
        hh = event_box_h
        hash_fill = lerp_color(DARK_BOX, CYAN_BG, highlight * 0.5)
        draw_rounded_rect(draw, (hx, ey, hx + hw, ey + hh),
                          fill=hash_fill, outline=lerp_color(BORDER, CYAN, highlight))

        hash_val = f"H{i}"
        hvw, hvh = text_size(draw, hash_val, font_small)
        draw.text((hx + (hw - hvw) // 2, ey + 7), hash_val,
                  fill=lerp_color(DIM, CYAN, 0.5 + highlight * 0.5), font=font_small)

        # Arrow down between hash boxes
        if i < 3:
            arrow_y1 = ey + hh + 2
            arrow_y2 = ey + hh + 16
            arrow_x = hx + hw // 2
            arrow_c = lerp_color(BORDER, CYAN, max(0, 1.0 - abs(scan_y - arrow_y1) / 40))
            draw_arrow_down(draw, arrow_x, arrow_y1, arrow_y2, arrow_c)

    # Scan line on right panel
    scan_alpha = 0.4 + 0.3 * math.sin(t * math.pi * 6)
    scan_color = lerp_color(BG, GREEN, scan_alpha)
    sx0 = right_x + 10
    sx1 = right_x + panel_w - 10
    draw.line([(sx0, int(scan_y)), (sx1, int(scan_y))], fill=scan_color, width=2)

    # Green check
    check_text = ">> Provable ordering"
    ckw, ckh = text_size(draw, check_text, font_header)
    draw.text((right_x + (panel_w - ckw) // 2, panel_bot - 35), check_text, fill=GREEN, font=font_header)

    # ========== Center arrow ==========
    mid_x = (left_x + panel_w + right_x) // 2
    mid_y = (panel_top + panel_bot) // 2
    arrow_pulse = 0.5 + 0.5 * math.sin(t * math.pi * 4)
    arrow_c = lerp_color(DIM, YELLOW, arrow_pulse)
    # Right-pointing arrow
    draw.text((mid_x - 8, mid_y - 20), "PoH", fill=YELLOW, font=font_small)
    draw.line([(mid_x - 6, mid_y + 2), (mid_x + 12, mid_y + 2)], fill=arrow_c, width=2)
    draw.polygon([(mid_x + 12, mid_y + 2),
                  (mid_x + 6, mid_y - 3),
                  (mid_x + 6, mid_y + 7)], fill=arrow_c)

    # ========== Bottom explanation panel ==========
    bot_y = 405
    draw_rounded_rect(draw, (30, bot_y, W - 30, H - 18), fill=PANEL, outline=BORDER)

    explanations = [
        ("Hash Chain = Total Ordering",
         "Each event is hashed into the chain: H(n) = SHA-256(H(n-1) + event)",
         CYAN),
        ("No Clock Synchronization Needed",
         "The hash sequence itself proves which event came first",
         YELLOW),
        ("Solana: 400ms Slots",
         "PoH produces ~400K hashes/sec, giving each slot a verifiable timestamp",
         PURPLE),
        ("Tamper-Proof Ordering",
         "Reordering events would require recomputing all subsequent hashes",
         GREEN),
    ]

    idx = frame_idx % len(explanations)
    et, ed, ec = explanations[idx]

    etw, eth = text_size(draw, et, font_header)
    draw.text(((W - etw) // 2, bot_y + 12), et, fill=ec, font=font_header)

    edw, edh = text_size(draw, ed, font_body)
    draw.text(((W - edw) // 2, bot_y + 36), ed, fill=DIM, font=font_body)

    # Visual: hash chain mini diagram at bottom
    mini_y = bot_y + 62
    mini_labels = ["H0", "H1", "H2", "H3", "H4", "H5"]
    mini_w = 45
    mini_h = 18
    mini_gap = 12
    total_mini = len(mini_labels) * mini_w + (len(mini_labels) - 1) * mini_gap
    mini_start = (W - total_mini) // 2

    for i, ml in enumerate(mini_labels):
        mx = mini_start + i * (mini_w + mini_gap)
        my = mini_y

        dist = abs(t * total_mini + mini_start - (mx + mini_w // 2))
        highlight = max(0, 1.0 - dist / 60)

        c = lerp_color(BORDER, CYAN, highlight)
        f = lerp_color(DARK_BOX, CYAN_BG, highlight * 0.4)
        draw_rounded_rect(draw, (mx, my, mx + mini_w, my + mini_h), fill=f, outline=c)

        mlw, mlh = text_size(draw, ml, font_small)
        draw.text((mx + (mini_w - mlw) // 2, my + 3), ml,
                  fill=lerp_color(DIM, CYAN, highlight), font=font_small)

        # Arrow
        if i < len(mini_labels) - 1:
            ax = mx + mini_w + 1
            ay = my + mini_h // 2
            draw.line([(ax, ay), (ax + mini_gap - 2, ay)], fill=BORDER, width=1)
            draw.polygon([(ax + mini_gap - 2, ay),
                          (ax + mini_gap - 6, ay - 3),
                          (ax + mini_gap - 6, ay + 3)], fill=BORDER)

    return img


# --- Generate GIF ---
frames = [make_frame(i) for i in range(FRAMES)]
frames[0].save(OUT, save_all=True, append_images=frames[1:],
               duration=DELAY, loop=0, optimize=True)
print(f"Saved {OUT} ({len(frames)} frames)")
