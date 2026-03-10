"""Sealevel: Parallel transaction execution across multiple lanes."""
from PIL import Image, ImageDraw, ImageFont
import math, os

W, H, FRAMES, DUR = 800, 550, 72, 90
BG = (13, 17, 23)
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)
CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
PURPLE = (167, 139, 250)
PURPLE_BG = (35, 28, 58)
RED = (248, 113, 113)
RED_BG = (50, 20, 20)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
YELLOW_BG = (58, 50, 14)

OUT = "assets/gifs/solana_10_sealevel_parallel.gif"

def load_font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for n in names:
        for p in [f"/usr/share/fonts/truetype/dejavu/{n}", f"/usr/share/fonts/truetype/liberation/{n}", f"/usr/share/fonts/{n}"]:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except (OSError, IOError): pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(15, True)
body_font = load_font(13)
small_font = load_font(11)

def draw_rounded_rect(d, xy, fill, outline, r=8):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

# Transactions with account dependencies
TXNS = [
    ("Tx1", ["A", "B"], CYAN),
    ("Tx2", ["C", "D"], GREEN),
    ("Tx3", ["E", "F"], YELLOW),
    ("Tx4", ["A", "C"], ORANGE),   # conflicts with Tx1 & Tx2
    ("Tx5", ["G", "H"], PURPLE),
    ("Tx6", ["B", "E"], RED),      # conflicts with Tx1 & Tx3
]

# Parallel groups: non-conflicting txns run together
# Group 1: Tx1, Tx2, Tx3, Tx5 (no shared accounts)
# Group 2: Tx4, Tx6 (after their deps)
# But for visual: 4 lanes
PARALLEL_LANES = [
    [0, 3],  # Lane 0: Tx1 then Tx4
    [1],     # Lane 1: Tx2
    [2, 5],  # Lane 2: Tx3 then Tx6
    [4],     # Lane 3: Tx5
]


def make_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    t = fi / (FRAMES - 1)

    # Title
    title = "Sealevel: Parallel Execution"
    tw, _ = text_size(d, title, title_font)
    d.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)
    sub = "Non-conflicting transactions run simultaneously"
    sw, _ = text_size(d, sub, body_font)
    d.text(((W - sw) // 2, 44), sub, fill=DIM, font=body_font)

    # === TOP: Transaction list with account tags ===
    tx_panel_y = 68
    tx_panel_h = 55
    draw_rounded_rect(d, (30, tx_panel_y, W - 30, tx_panel_y + tx_panel_h), PANEL, BORDER)
    d.text((42, tx_panel_y + 6), "Transactions:", fill=DIM, font=small_font)

    tag_x = 42
    tag_y = tx_panel_y + 24
    for i, (name, accts, color) in enumerate(TXNS):
        # Tx box
        label = f"{name}({','.join(accts)})"
        lw, _ = text_size(d, label, small_font)
        bw = lw + 16
        pulse = 0.5 + 0.5 * math.sin(t * math.pi * 4 + i)
        draw_rounded_rect(d, (tag_x, tag_y, tag_x + bw, tag_y + 20),
                          DARK_BOX, lerp_color(BORDER, color, 0.3 + 0.2 * pulse), r=4)
        d.text((tag_x + 8, tag_y + 4), label, fill=color, font=small_font)
        tag_x += bw + 10

    # === LEFT: Sequential (1 lane) ===
    left_x, left_w = 30, 200
    seq_top, seq_bot = 140, 390
    draw_rounded_rect(d, (left_x, seq_top, left_x + left_w, seq_bot), PANEL, BORDER)
    hdr = "Sequential"
    hw, _ = text_size(d, hdr, header_font)
    d.text((left_x + (left_w - hw) // 2, seq_top + 6), hdr, fill=RED, font=header_font)
    d.text((left_x + 10, seq_top + 26), "1 thread", fill=DIM, font=small_font)

    # All 6 txns stacked vertically in one lane
    lane_x = left_x + 30
    lane_w = left_w - 60
    slot_h = 26
    gap = 6
    start_y = seq_top + 44

    # Progress bar (scanning through sequential)
    seq_progress_y = start_y + t * (len(TXNS) * (slot_h + gap))

    for i, (name, accts, color) in enumerate(TXNS):
        sy = start_y + i * (slot_h + gap)
        dist = abs(seq_progress_y - (sy + slot_h // 2))
        hl = max(0, 1.0 - dist / 25)
        fill = lerp_color(DARK_BOX, RED_BG, hl * 0.4)
        outline = lerp_color(BORDER, color, 0.2 + hl * 0.5)
        draw_rounded_rect(d, (lane_x, sy, lane_x + lane_w, sy + slot_h), fill, outline, r=4)
        d.text((lane_x + 8, sy + 6), name, fill=lerp_color(DIM, color, 0.5 + hl * 0.5), font=small_font)

    # Time arrow
    time_x = left_x + 12
    d.line([(time_x, start_y), (time_x, start_y + len(TXNS) * (slot_h + gap) - gap)], fill=DIM, width=1)
    d.polygon([(time_x, start_y + len(TXNS) * (slot_h + gap)),
               (time_x - 3, start_y + len(TXNS) * (slot_h + gap) - 6),
               (time_x + 3, start_y + len(TXNS) * (slot_h + gap) - 6)], fill=DIM)
    d.text((left_x + 5, seq_bot - 26), "6 time slots", fill=RED, font=small_font)

    # === RIGHT: Parallel (4 lanes) ===
    right_x, right_w = 260, 510
    draw_rounded_rect(d, (right_x, seq_top, right_x + right_w, seq_bot), PANEL, BORDER)
    hdr2 = "Parallel (Sealevel)"
    hw2, _ = text_size(d, hdr2, header_font)
    d.text((right_x + (right_w - hw2) // 2, seq_top + 6), hdr2, fill=GREEN, font=header_font)
    d.text((right_x + 10, seq_top + 26), "4 threads", fill=DIM, font=small_font)

    # 4 lanes side by side
    lane_start_x = right_x + 25
    par_lane_w = 100
    par_gap = 16
    par_start_y = seq_top + 44

    # Progress bar
    par_progress_y = par_start_y + t * (2 * (slot_h + gap))

    lane_labels = ["Thread 1", "Thread 2", "Thread 3", "Thread 4"]
    for lane_i, txn_indices in enumerate(PARALLEL_LANES):
        lx = lane_start_x + lane_i * (par_lane_w + par_gap)
        # Lane header
        llw, _ = text_size(d, lane_labels[lane_i], small_font)
        d.text((lx + (par_lane_w - llw) // 2, par_start_y - 14), lane_labels[lane_i], fill=DIM, font=small_font)

        # Lane background stripe
        stripe_top = par_start_y
        stripe_bot = par_start_y + 2 * (slot_h + gap) - gap + slot_h
        d.rectangle((lx - 2, stripe_top, lx + par_lane_w + 2, stripe_bot), fill=lerp_color(BG, PANEL, 0.5))

        for slot_i, txn_i in enumerate(txn_indices):
            name, accts, color = TXNS[txn_i]
            sy = par_start_y + slot_i * (slot_h + gap)
            dist = abs(par_progress_y - (sy + slot_h // 2))
            hl = max(0, 1.0 - dist / 25)
            fill = lerp_color(DARK_BOX, GREEN_BG, hl * 0.4)
            outline = lerp_color(BORDER, color, 0.3 + hl * 0.5)
            draw_rounded_rect(d, (lx, sy, lx + par_lane_w, sy + slot_h), fill, outline, r=4)
            lbl = f"{name}({','.join(accts)})"
            lw, _ = text_size(d, lbl, small_font)
            # Truncate if too wide
            if lw > par_lane_w - 8:
                lbl = name
                lw, _ = text_size(d, lbl, small_font)
            d.text((lx + (par_lane_w - lw) // 2, sy + 6), lbl, fill=lerp_color(DIM, color, 0.5 + hl * 0.5), font=small_font)

    d.text((right_x + 10, seq_bot - 26), "2 time slots", fill=GREEN, font=small_font)

    # Speedup stat
    speedup = "3x speedup"
    spw, _ = text_size(d, speedup, header_font)
    pulse = 0.6 + 0.4 * math.sin(t * math.pi * 3)
    d.text((right_x + right_w - spw - 20, seq_bot - 28), speedup,
           fill=lerp_color(DIM, GREEN, pulse), font=header_font)

    # === Bottom Panel ===
    bot_y = 402
    draw_rounded_rect(d, (30, bot_y, W - 30, H - 14), PANEL, BORDER)

    explanations = [
        ("Account-Level Locking", "Txns touching different accounts run in parallel -- no conflicts", CYAN),
        ("Conflict Detection", "Txns sharing accounts (e.g. Tx1+Tx4 share A) must serialize", ORANGE),
        ("4000+ TPS Potential", "Multiple CPU cores process independent transactions simultaneously", GREEN),
        ("Declared Account Lists", "Each tx declares accounts upfront, enabling scheduler to plan", PURPLE),
    ]
    idx = (fi // 18) % len(explanations)
    et, ed, ec = explanations[idx]
    etw, _ = text_size(d, et, header_font)
    d.text(((W - etw) // 2, bot_y + 10), et, fill=ec, font=header_font)
    edw, _ = text_size(d, ed, body_font)
    d.text(((W - edw) // 2, bot_y + 32), ed, fill=DIM, font=body_font)

    # Mini comparison bar chart
    bar_y = bot_y + 56
    bar_h = 16
    # Sequential bar
    d.text((120, bar_y), "Sequential:", fill=DIM, font=small_font)
    seq_bw = 280
    draw_rounded_rect(d, (210, bar_y, 210 + seq_bw, bar_y + bar_h), RED_BG, lerp_color(BORDER, RED, 0.3), r=3)
    d.text((210 + seq_bw // 2 - 15, bar_y + 2), "6 slots", fill=RED, font=small_font)

    # Parallel bar
    d.text((120, bar_y + 22), "Parallel:", fill=DIM, font=small_font)
    par_bw = 280 * 2 // 6  # 2/6 of sequential
    draw_rounded_rect(d, (210, bar_y + 22, 210 + par_bw, bar_y + 22 + bar_h), GREEN_BG, lerp_color(BORDER, GREEN, 0.3), r=3)
    d.text((210 + par_bw // 2 - 15, bar_y + 24), "2 slots", fill=GREEN, font=small_font)

    return img


if __name__ == "__main__":
    frames = [make_frame(i) for i in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DUR, loop=0, optimize=True)
    print(f"Saved {OUT} ({len(frames)} frames)")
