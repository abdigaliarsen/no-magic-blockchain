"""Banking Stage: TPU pipeline with parallel transaction processing threads."""
from PIL import Image, ImageDraw, ImageFont
import math, os

W, H, FRAMES, DUR = 800, 550, 36, 90
BG = (13, 17, 23)
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)
RED = (248, 113, 113)
PURPLE = (167, 139, 250)
CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
YELLOW_BG = (58, 50, 14)

OUT = "assets/gifs/solana_16_banking_stage.gif"

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
tiny_font = load_font(10)

def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def draw_rounded_rect(d, xy, fill, outline, r=8):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)


def make_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    t = fi / (FRAMES - 1)
    pulse = 0.5 + 0.5 * math.sin(fi * 2 * math.pi / 10)

    # Title
    title = "Solana Banking Stage"
    tw, _ = text_size(d, title, title_font)
    d.text(((W - tw) // 2, 10), title, fill=CYAN, font=title_font)
    sub = "TPU pipeline: pipelined and parallel transaction processing"
    sw, _ = text_size(d, sub, body_font)
    d.text(((W - sw) // 2, 40), sub, fill=DIM, font=body_font)

    # === TOP: Pipeline stages ===
    pipe_y = 68
    pipe_h = 70
    draw_rounded_rect(d, (25, pipe_y, W - 25, pipe_y + pipe_h), PANEL, BORDER)
    d.text((40, pipe_y + 6), "TPU Pipeline Stages", fill=YELLOW, font=header_font)

    stages = [
        ("Fetch", CYAN, "UDP packets"),
        ("SigVerify", PURPLE, "Ed25519 check"),
        ("Banking", GREEN, "Execute txs"),
        ("Broadcast", ORANGE, "Shred + send"),
    ]
    stage_w = 150
    stage_h = 30
    stage_gap = 20
    total_sw = len(stages) * stage_w + (len(stages) - 1) * stage_gap
    stage_start_x = (W - total_sw) // 2
    stage_mid_y = pipe_y + 35

    # Animated highlight showing which stage is "active"
    active_stage = int(fi / 3) % 4

    for i, (name, color, desc) in enumerate(stages):
        sx = stage_start_x + i * (stage_w + stage_gap)
        is_active = i == active_stage
        bg = lerp_color(DARK_BOX, color, 0.2 if is_active else 0.05)
        bord = color if is_active else lerp_color(BORDER, color, 0.3)
        draw_rounded_rect(d, (sx, stage_mid_y, sx + stage_w, stage_mid_y + stage_h), bg, bord, r=5)
        nw, _ = text_size(d, name, small_font)
        d.text((sx + (stage_w - nw) // 2, stage_mid_y + 2), name, fill=color, font=small_font)
        dw, _ = text_size(d, desc, tiny_font)
        d.text((sx + (stage_w - dw) // 2, stage_mid_y + 16), desc, fill=DIM, font=tiny_font)

        # Arrow between stages
        if i < len(stages) - 1:
            ax = sx + stage_w + 3
            ay = stage_mid_y + stage_h // 2
            d.line([(ax, ay), (ax + stage_gap - 6, ay)], fill=DIM, width=1)
            d.polygon([(ax + stage_gap - 3, ay),
                       (ax + stage_gap - 8, ay - 3),
                       (ax + stage_gap - 8, ay + 3)], fill=DIM)

    # === MIDDLE: Banking Stage Detail (4 parallel threads) ===
    bank_y = 150
    bank_h = 195
    draw_rounded_rect(d, (25, bank_y, W - 25, bank_y + bank_h), PANEL, BORDER)
    d.text((40, bank_y + 6), "Banking Stage: 4 Parallel Threads", fill=GREEN, font=header_font)

    # Priority queue on left
    pq_x, pq_y = 40, bank_y + 30
    pq_w, pq_h = 150, 155
    draw_rounded_rect(d, (pq_x, pq_y, pq_x + pq_w, pq_y + pq_h), DARK_BOX, BORDER, r=6)
    d.text((pq_x + 10, pq_y + 5), "Priority Queue", fill=YELLOW, font=small_font)

    # Queue items sorted by priority fee
    queue_items = [
        ("Tx #7", "50k", YELLOW),
        ("Tx #2", "30k", ORANGE),
        ("Tx #5", "20k", CYAN),
        ("Tx #1", "10k", GREEN),
        ("Tx #9", "5k", DIM),
        ("Tx #3", "1k", DIM),
    ]
    for i, (tx_name, fee, color) in enumerate(queue_items):
        qy = pq_y + 24 + i * 20
        # Items shift based on animation (dequeue effect)
        shift = 0
        if i == 0:
            shift_cycle = fi % 12
            if shift_cycle < 4:
                shift = int(shift_cycle * 3)
        draw_rounded_rect(d, (pq_x + 8 + shift, qy, pq_x + pq_w - 8, qy + 16),
                          BG, lerp_color(BORDER, color, 0.3), r=3)
        d.text((pq_x + 14 + shift, qy + 1), f"{tx_name}  fee:{fee}", fill=color, font=tiny_font)

    # 4 parallel banking threads
    thread_x = 220
    thread_w = 120
    thread_h = 32
    thread_gap = 6
    thread_colors = [CYAN, GREEN, PURPLE, ORANGE]

    for i in range(4):
        ty = bank_y + 30 + i * (thread_h + thread_gap)
        color = thread_colors[i]

        # Thread box
        thread_active = ((fi + i * 3) % 12) < 8  # Staggered activity
        bg = lerp_color(DARK_BOX, color, 0.15 if thread_active else 0.05)
        bord = lerp_color(BORDER, color, 0.5 if thread_active else 0.2)
        draw_rounded_rect(d, (thread_x, ty, thread_x + thread_w, ty + thread_h), bg, bord, r=4)

        d.text((thread_x + 6, ty + 3), f"Thread {i}", fill=color, font=small_font)
        status = "exec..." if thread_active else "idle"
        d.text((thread_x + 6, ty + 17), status, fill=DIM, font=tiny_font)

        # Activity indicator
        if thread_active:
            indicator_pulse = 0.5 + 0.5 * math.sin((fi + i * 4) * 2 * math.pi / 8)
            ic = lerp_color(DIM, color, indicator_pulse)
            d.ellipse((thread_x + thread_w - 14, ty + 10, thread_x + thread_w - 6, ty + 18), fill=ic)

        # Arrow from queue to thread
        d.line([(pq_x + pq_w + 3, ty + thread_h // 2),
                (thread_x - 5, ty + thread_h // 2)], fill=DIM, width=1)

    # Right side: block packing
    bp_x, bp_y = 370, bank_y + 28
    bp_w, bp_h = 390, 160
    draw_rounded_rect(d, (bp_x, bp_y, bp_x + bp_w, bp_y + bp_h), DARK_BOX, BORDER, r=6)
    d.text((bp_x + 12, bp_y + 5), "Block Packing", fill=YELLOW, font=small_font)

    # Block grid (4 rows x 8 cols representing tx slots)
    grid_x, grid_y = bp_x + 15, bp_y + 28
    cell_w, cell_h = 40, 22
    n_cols, n_rows = 8, 4
    filled_count = int(t * n_cols * n_rows)

    for row in range(n_rows):
        for col in range(n_cols):
            cx = grid_x + col * (cell_w + 4)
            cy = grid_y + row * (cell_h + 4)
            cell_idx = row * n_cols + col
            is_filled = cell_idx < filled_count

            if is_filled:
                # Color based on which thread processed it
                thread_idx = cell_idx % 4
                cell_color = thread_colors[thread_idx]
                cell_bg = lerp_color(DARK_BOX, cell_color, 0.25)
                cell_bord = lerp_color(BORDER, cell_color, 0.5)
                label = f"T{cell_idx + 1}"
            else:
                cell_bg = BG
                cell_bord = lerp_color(BG, BORDER, 0.5)
                label = ""

            draw_rounded_rect(d, (cx, cy, cx + cell_w, cy + cell_h), cell_bg, cell_bord, r=3)
            if label:
                lw, _ = text_size(d, label, tiny_font)
                d.text((cx + (cell_w - lw) // 2, cy + 4), label, fill=cell_color, font=tiny_font)

    # Block progress bar
    prog_y = bp_y + bp_h - 30
    prog_w = bp_w - 30
    draw_rounded_rect(d, (bp_x + 15, prog_y, bp_x + 15 + prog_w, prog_y + 14),
                      BG, BORDER, r=4)
    fill_w = int(prog_w * t)
    if fill_w > 4:
        draw_rounded_rect(d, (bp_x + 15, prog_y, bp_x + 15 + fill_w, prog_y + 14),
                          GREEN_BG, lerp_color(BORDER, GREEN, 0.5), r=4)
    pct = f"{int(t * 100)}% full"
    pw, _ = text_size(d, pct, tiny_font)
    d.text((bp_x + 15 + (prog_w - pw) // 2, prog_y + 1), pct, fill=GREEN, font=tiny_font)

    # === BOTTOM: Stats and explanations ===
    stats_y = 358
    stats_h = 65
    draw_rounded_rect(d, (30, stats_y, W - 30, stats_y + stats_h), PANEL, BORDER)
    d.text((50, stats_y + 8), "Performance Metrics", fill=CYAN, font=header_font)

    metrics = [
        ("TPS:", f"{int(3000 + 1500 * pulse)}", CYAN),
        ("Block time:", "400ms", GREEN),
        ("Threads:", "4 parallel", PURPLE),
        ("Queue depth:", f"{max(0, 150 - int(t * 100))}", ORANGE),
        ("Priority floor:", "5000 lamports", YELLOW),
    ]
    mx = 50
    for label, value, color in metrics:
        d.text((mx, stats_y + 32), label, fill=DIM, font=tiny_font)
        vw, _ = text_size(d, label, tiny_font)
        d.text((mx + vw + 4, stats_y + 32), value, fill=color, font=tiny_font)
        mx += vw + text_size(d, value, tiny_font)[0] + 20

    # Explanation panel
    exp_y = 435
    draw_rounded_rect(d, (30, exp_y, W - 30, H - 14), PANEL, BORDER)
    explanations = [
        ("Banking Stage = Execution Engine", "Processes transactions in parallel using 4+ threads with lock-free queues", GREEN),
        ("Priority Fees = Queue Ordering", "Higher fee transactions get processed first during congestion", YELLOW),
        ("Pipelined Architecture", "Fetch, verify, execute, broadcast happen simultaneously on different data", CYAN),
        ("Account Locking", "Threads process non-conflicting txs in parallel -- conflicts serialized", PURPLE),
    ]
    idx = fi % len(explanations)
    et, ed, ec = explanations[idx]
    etw, _ = text_size(d, et, header_font)
    d.text(((W - etw) // 2, exp_y + 10), et, fill=ec, font=header_font)
    edw, _ = text_size(d, ed, body_font)
    d.text(((W - edw) // 2, exp_y + 32), ed, fill=DIM, font=body_font)

    # Animated tx flow dots through pipeline
    dot_phase = (fi % 12) / 12.0
    for dot_i in range(4):
        dp = (dot_phase + dot_i * 0.25) % 1.0
        # Move across pipeline stages
        stage_idx = int(dp * len(stages))
        if stage_idx < len(stages):
            sx = stage_start_x + stage_idx * (stage_w + stage_gap) + int((dp * len(stages) - stage_idx) * (stage_w + stage_gap))
            sx = min(sx, stage_start_x + (len(stages) - 1) * (stage_w + stage_gap) + stage_w)
            dot_y = stage_mid_y - 5
            dc = thread_colors[dot_i]
            d.ellipse((sx - 3, dot_y - 3, sx + 3, dot_y + 3), fill=dc)

    return img


if __name__ == "__main__":
    frames = [make_frame(i) for i in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DUR, loop=0, optimize=True)
    print(f"Saved {OUT} ({len(frames)} frames)")
