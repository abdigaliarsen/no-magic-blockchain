"""
Variant C: "Broadcast vs Turbine"
Side by side comparison:
- Naive broadcast: leader sends to ALL N validators, bandwidth = N
- Turbine: tree broadcast, bandwidth = log(N)
Shows the scaling advantage visually.
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/solana_07_turbine_propagation.gif"

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

try:
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except Exception:
    font_title = ImageFont.load_default()
    font_header = font_title
    font_body = font_title
    font_small = font_title


def text_center(draw, x, y, text, font, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((x - tw // 2, y - th // 2), text, font=font, fill=fill)


def rounded_rect(draw, x0, y0, x1, y1, r, fill, outline):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=outline, width=1)


def draw_arrow(draw, x1, y1, x2, y2, color, width=1):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    alen = 5
    for side in [-1, 1]:
        ax = x2 - alen * math.cos(angle + side * 0.45)
        ay = y2 - alen * math.sin(angle + side * 0.45)
        draw.line([(x2, y2), (int(ax), int(ay))], fill=color, width=width)


def draw_pulse(draw, x1, y1, x2, y2, t, color, size=3):
    if t < 0 or t > 1:
        return
    px = x1 + (x2 - x1) * t
    py = y1 + (y2 - y1) * t
    draw.ellipse([px - size, py - size, px + size, py + size], fill=color)


def draw_node(draw, cx, cy, r, fill, outline, label, font, text_col):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline, width=1)
    text_center(draw, cx, cy, label, font, text_col)


def render_frame(frame_idx):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = frame_idx / (FRAMES - 1)

    # --- Title ---
    text_center(draw, W // 2, 22, "Naive Broadcast vs Turbine", font_title, CYAN)

    # --- Divider ---
    mid_x = W // 2
    draw.line([(mid_x, 48), (mid_x, H - 70)], fill=BORDER, width=1)

    # === LEFT SIDE: Naive Broadcast ===
    left_cx = mid_x // 2
    text_center(draw, left_cx, 52, "Naive Broadcast", font_header, RED)

    # Leader at top center-left
    leader_lx, leader_ly = left_cx, 90
    draw_node(draw, leader_lx, leader_ly, 16, RED_BG, RED, "L", font_header, RED)

    # 9 validator nodes in a grid below
    naive_nodes = []
    rows, cols = 3, 3
    grid_start_x = left_cx - 100
    grid_start_y = 160
    gap_x, gap_y = 100, 70

    for r in range(rows):
        for c in range(cols):
            nx = grid_start_x + c * gap_x
            ny = grid_start_y + r * gap_y
            naive_nodes.append((nx, ny))

    # Draw ALL arrows from leader to every node (the problem!)
    for idx, (nx, ny) in enumerate(naive_nodes):
        # Color arrows to show congestion — more red as count increases
        arr_col = (180, 50, 50)
        draw_arrow(draw, leader_lx, leader_ly + 16, nx, ny - 12, arr_col, 1)

        # Pulse: stagger pulses to show sequential sending
        pulse_phase = (frame_idx - idx * 2) / 12.0
        draw_pulse(draw, leader_lx, leader_ly + 16, nx, ny - 12, pulse_phase % 1.0 if pulse_phase > 0 else -1, RED, 3)

    # Draw nodes on top of arrows
    for idx, (nx, ny) in enumerate(naive_nodes):
        draw_node(draw, nx, ny, 12, DARK_BOX, DIM, f"V{idx+1}", font_small, DIM)

    # Bandwidth indicator
    bw_y = 395
    rounded_rect(draw, 20, bw_y, mid_x - 15, bw_y + 55, 6, RED_BG, RED)
    text_center(draw, left_cx, bw_y + 12, "Leader bandwidth: O(N)", font_header, RED)
    text_center(draw, left_cx, bw_y + 32, "9 sends from 1 node", font_body, WHITE)
    # Bandwidth bar (full/overloaded)
    bar_x, bar_y = 35, bw_y + 42
    bar_w = mid_x - 65
    rounded_rect(draw, bar_x, bar_y, bar_x + bar_w, bar_y + 8, 2, DARK_BOX, BORDER)
    # Pulsing red fill to show overload
    pulse = 0.7 + 0.3 * math.sin(frame_idx * 0.4)
    fill_w = int(bar_w * pulse)
    rounded_rect(draw, bar_x, bar_y, bar_x + fill_w, bar_y + 8, 2, RED, RED)

    # === RIGHT SIDE: Turbine Tree ===
    right_cx = mid_x + mid_x // 2
    text_center(draw, right_cx, 52, "Turbine (Tree)", font_header, GREEN)

    # Leader
    leader_rx, leader_ry = right_cx, 90
    draw_node(draw, leader_rx, leader_ry, 16, GREEN_BG, GREEN, "L", font_header, GREEN)

    # Layer 1: 3 nodes
    layer1_y = 170
    layer1_spread = 110
    layer1_nodes = []
    for i in range(3):
        nx = right_cx + (i - 1) * layer1_spread
        layer1_nodes.append((nx, layer1_y))

    # Arrows leader -> layer 1
    for idx, (nx, ny) in enumerate(layer1_nodes):
        draw_arrow(draw, leader_rx, leader_ry + 16, nx, ny - 12, GREEN, 1)
        pulse_t = (frame_idx - idx * 2) / 10.0
        draw_pulse(draw, leader_rx, leader_ry + 16, nx, ny - 12,
                   pulse_t % 1.0 if pulse_t > 0 else -1, GREEN, 3)

    # Draw layer 1 nodes
    layer1_colors = [CYAN, YELLOW, ORANGE]
    layer1_bgs = [CYAN_BG, YELLOW_BG, YELLOW_BG]
    for idx, (nx, ny) in enumerate(layer1_nodes):
        draw_node(draw, nx, ny, 12, layer1_bgs[idx], layer1_colors[idx],
                  f"V{idx+1}", font_small, layer1_colors[idx])

    # Layer 2: 3 children per layer1 node = 9 nodes (but we show 6 to fit)
    layer2_y = 260
    layer2_nodes = []
    for pi, (px, py) in enumerate(layer1_nodes):
        for ci in range(2):
            nx = px + (ci * 2 - 1) * 40
            layer2_nodes.append((nx, layer2_y, pi))

    # Arrows layer1 -> layer2
    for idx, (nx, ny, pi) in enumerate(layer2_nodes):
        px, py = layer1_nodes[pi]
        pcol = layer1_colors[pi]
        dim_col = tuple(max(20, c // 2) for c in pcol)
        draw_arrow(draw, px, py + 12, nx, ny - 10, dim_col, 1)
        pulse_t = (frame_idx - 10 - idx * 2) / 10.0
        draw_pulse(draw, px, py + 12, nx, ny - 10,
                   pulse_t % 1.0 if pulse_t > 0 else -1, pcol, 3)

    # Draw layer 2 nodes
    for idx, (nx, ny, pi) in enumerate(layer2_nodes):
        draw_node(draw, nx, ny, 10, DARK_BOX, DIM, f"N{idx+1}", font_small, DIM)

    # Layer 3: even more children (just show dots to indicate scale)
    layer3_y = 340
    for idx, (nx, ny, pi) in enumerate(layer2_nodes):
        for di in range(2):
            dx = nx + (di * 2 - 1) * 18
            draw.ellipse([dx - 4, layer3_y - 4, dx + 4, layer3_y + 4],
                         fill=DARK_BOX, outline=BORDER)
        # Connecting lines
        for di in range(2):
            dx = nx + (di * 2 - 1) * 18
            draw.line([(nx, ny + 10), (dx, layer3_y - 4)], fill=BORDER, width=1)

    text_center(draw, right_cx, layer3_y + 16, "... more layers ...", font_small, DIM)

    # Bandwidth indicator
    rounded_rect(draw, mid_x + 15, bw_y, W - 20, bw_y + 55, 6, GREEN_BG, GREEN)
    text_center(draw, right_cx, bw_y + 12, "Per-node bandwidth: O(fan-out)", font_header, GREEN)
    text_center(draw, right_cx, bw_y + 32, "3 sends per node, log(N) depth", font_body, WHITE)
    # Bandwidth bar (low and stable)
    bar_x2 = mid_x + 30
    bar_w2 = mid_x - 65
    rounded_rect(draw, bar_x2, bw_y + 42, bar_x2 + bar_w2, bw_y + 50, 2, DARK_BOX, BORDER)
    fill_w2 = int(bar_w2 * 0.33)
    rounded_rect(draw, bar_x2, bw_y + 42, bar_x2 + fill_w2, bw_y + 50, 2, GREEN, GREEN)

    # --- Bottom comparison panel ---
    panel_y = 460
    rounded_rect(draw, 30, panel_y, W - 30, H - 12, 8, PANEL, BORDER)

    # Scaling comparison
    comparisons = [
        ("N=100 validators", "100 sends", "3 layers", RED, GREEN),
        ("N=1000 validators", "1000 sends", "4 layers", RED, GREEN),
        ("N=10000 validators", "10000 sends", "5 layers", RED, GREEN),
    ]
    cycle = (frame_idx // 12) % 3
    n_label, naive_val, turbine_val, naive_col, turbine_col = comparisons[cycle]

    text_center(draw, W // 2, panel_y + 14, n_label, font_header, WHITE)
    # Left stat
    text_center(draw, W // 4, panel_y + 38, f"Naive: {naive_val}", font_body, naive_col)
    # Right stat
    text_center(draw, 3 * W // 4, panel_y + 38, f"Turbine: {turbine_val}", font_body, turbine_col)

    # Animated arrows
    arr_phase = (frame_idx % 12) / 12.0
    vs_x = W // 2
    # "VS" label
    text_center(draw, vs_x, panel_y + 38, "vs", font_small, DIM)

    # Scan line
    scan_x = int(t * (W - 60)) + 30
    draw.line([(scan_x, H - 8), (scan_x, H - 4)], fill=CYAN, width=2)

    return img


def main():
    frames = [render_frame(i) for i in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DELAY, loop=0, optimize=True)
    print(f"Saved {OUT} ({FRAMES} frames, {DELAY}ms delay)")


if __name__ == "__main__":
    main()
