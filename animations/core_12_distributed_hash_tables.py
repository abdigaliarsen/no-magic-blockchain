"""CORE12-A: Distributed Hash Tables (Kademlia) — decentralized key-value lookup."""
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
PURPLE_BG = (35, 28, 58)
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
                except: pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(15, True)
body_font = load_font(13)
small_font = load_font(11)
big_font = load_font(18, True)

def text_w(draw, txt, font):
    bb = draw.textbbox((0, 0), txt, font=font)
    return bb[2] - bb[0]

def draw_rounded_box(draw, x, y, w, h, fill, border_col, r=8):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill, outline=border_col, width=2)

def marching_hline(draw, x1, x2, y, color, frame, idx=0):
    dash_len = 6
    offset = (frame * 2 + idx * 5) % (dash_len * 2)
    direction = 1 if x2 > x1 else -1
    length = abs(x2 - x1)
    pos = offset % (dash_len * 2)
    while pos < length:
        sx = x1 + direction * pos
        ex = x1 + direction * min(pos + dash_len, length)
        draw.line([(sx, y), (ex, y)], fill=color, width=2)
        pos += dash_len * 2
    if direction > 0:
        draw.polygon([(x2, y), (x2 - 8, y - 5), (x2 - 8, y + 5)], fill=color)
    else:
        draw.polygon([(x2, y), (x2 + 8, y - 5), (x2 + 8, y + 5)], fill=color)

def draw_node(draw, cx, cy, r, label, color, active=False, pulse_val=0.5):
    """Draw a network node as a circle with label."""
    if active:
        # Glow ring
        glow_r = r + 4
        gcol = tuple(int(c * 0.3) for c in color)
        draw.ellipse([cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r], fill=gcol)
    # Node body
    bg = tuple(int(c * 0.15) for c in color)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg, outline=color, width=2)
    lw = text_w(draw, label, small_font)
    draw.text((cx - lw // 2, cy - 6), label, fill=color, font=small_font)

def draw_connection(draw, x1, y1, x2, y2, color, alpha=0.4):
    """Draw a dim connection line between two nodes."""
    col = tuple(int(c * alpha) for c in color)
    draw.line([(x1, y1), (x2, y2)], fill=col, width=1)

def marching_line_xy(draw, x1, y1, x2, y2, color, frame, idx=0):
    """Draw a marching-ant line between two arbitrary points."""
    dash_len = 6
    offset = (frame * 2 + idx * 5) % (dash_len * 2)
    dx, dy = x2 - x1, y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    pos = offset % (dash_len * 2)
    while pos < length - 10:  # stop before arrowhead
        sx = x1 + ux * pos
        sy = y1 + uy * pos
        end = min(pos + dash_len, length - 10)
        ex = x1 + ux * end
        ey = y1 + uy * end
        draw.line([(sx, sy), (ex, ey)], fill=color, width=2)
        pos += dash_len * 2
    # Arrowhead
    draw.polygon([
        (int(x2), int(y2)),
        (int(x2 - 8 * ux - 5 * uy), int(y2 - 8 * uy + 5 * ux)),
        (int(x2 - 8 * ux + 5 * uy), int(y2 - 8 * uy - 5 * ux)),
    ], fill=color)

def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    pulse = 0.5 + 0.5 * math.sin(f * 2 * math.pi / FRAMES)

    # Title
    title = "Distributed Hash Tables"
    tw = text_w(draw, title, title_font)
    draw.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)
    subtitle = "Kademlia: decentralized key-value lookup via XOR distance"
    sw = text_w(draw, subtitle, small_font)
    draw.text(((W - sw) // 2, 44), subtitle, fill=DIM, font=small_font)

    # === Left panel: Network topology ===
    net_x, net_y = 30, 68
    net_w, net_h = 370, 250
    draw_rounded_box(draw, net_x, net_y, net_w, net_h, PANEL, BORDER)

    net_lbl = "NETWORK (8 nodes)"
    net_lbl_w = text_w(draw, net_lbl, header_font)
    draw.text((net_x + (net_w - net_lbl_w) // 2, net_y + 8), net_lbl, fill=ORANGE, font=header_font)

    # Node positions in a ring layout
    ring_cx = net_x + net_w // 2
    ring_cy = net_y + net_h // 2 + 15
    ring_r = 90
    n_nodes = 8
    node_ids = ["0010", "0100", "0110", "0111", "1001", "1011", "1100", "1110"]
    node_colors = [CYAN, GREEN, ORANGE, YELLOW, PURPLE, RED, CYAN, GREEN]
    node_positions = []
    for i in range(n_nodes):
        angle = -math.pi / 2 + i * 2 * math.pi / n_nodes
        nx = ring_cx + int(ring_r * math.cos(angle))
        ny = ring_cy + int(ring_r * math.sin(angle))
        node_positions.append((nx, ny))

    # Draw connections (each node knows some others)
    connections = [(0, 1), (0, 4), (1, 2), (1, 5), (2, 3), (3, 6),
                   (4, 5), (4, 7), (5, 6), (6, 7), (0, 7), (2, 5)]
    for a, b in connections:
        ax, ay = node_positions[a]
        bx, by = node_positions[b]
        draw_connection(draw, ax, ay, bx, by, DIM, 0.3)

    # Lookup path: node 0 looking for key closest to node 5 (1011)
    # Path: 0 -> 4 -> 5 (getting closer by XOR distance)
    lookup_path = [0, 4, 5]
    path_phase = (f * 3 // FRAMES) % 3  # which hop is active

    for step in range(len(lookup_path) - 1):
        ai = lookup_path[step]
        bi = lookup_path[step + 1]
        ax, ay = node_positions[ai]
        bx, by = node_positions[bi]
        col = YELLOW if step <= path_phase else DIM
        if step <= path_phase:
            marching_line_xy(draw, ax, ay, bx, by, col, f, step)

    # Draw nodes (on top of connections)
    for i in range(n_nodes):
        nx, ny = node_positions[i]
        is_active = i in lookup_path[:path_phase + 2]
        col = node_colors[i]
        if i == lookup_path[-1]:  # target
            col = YELLOW
        draw_node(draw, nx, ny, 18, node_ids[i], col, active=is_active, pulse_val=pulse)

    # Lookup label
    look_lbl = "LOOKUP: key=1010"
    look_lbl_w = text_w(draw, look_lbl, body_font)
    draw.text((net_x + (net_w - look_lbl_w) // 2, net_y + net_h - 28), look_lbl, fill=YELLOW, font=body_font)

    # === Right panel: XOR distance ===
    xor_x, xor_y = 420, 68
    xor_w, xor_h = 350, 120
    draw_rounded_box(draw, xor_x, xor_y, xor_w, xor_h, PANEL, CYAN)

    xor_lbl = "XOR DISTANCE"
    xor_lbl_w = text_w(draw, xor_lbl, header_font)
    draw.text((xor_x + (xor_w - xor_lbl_w) // 2, xor_y + 8), xor_lbl, fill=CYAN, font=header_font)

    # Show XOR distance calculations
    distances = [
        ("0010 XOR 1010", "1000", "= 8", CYAN),
        ("1001 XOR 1010", "0011", "= 3", PURPLE),
        ("1011 XOR 1010", "0001", "= 1", YELLOW),
    ]

    for i, (expr, result, decimal, col) in enumerate(distances):
        dy = xor_y + 32 + i * 26
        draw.text((xor_x + 15, dy), expr, fill=WHITE, font=body_font)
        draw.text((xor_x + 170, dy), "=", fill=DIM, font=body_font)
        draw.text((xor_x + 185, dy), result, fill=col, font=body_font)
        draw.text((xor_x + 240, dy), decimal, fill=col, font=body_font)

        # Highlight the closest
        if i == 2:
            glow = tuple(int(c * (0.5 + 0.5 * pulse)) for c in YELLOW)
            draw.text((xor_x + 285, dy), "<-- closest!", fill=glow, font=small_font)

    # === Right panel: Key-Value store ===
    kv_x, kv_y = 420, 198
    kv_w, kv_h = 350, 120
    draw_rounded_box(draw, kv_x, kv_y, kv_w, kv_h, PANEL, GREEN)

    kv_lbl = "KEY-VALUE STORE"
    kv_lbl_w = text_w(draw, kv_lbl, header_font)
    draw.text((kv_x + (kv_w - kv_lbl_w) // 2, kv_y + 8), kv_lbl, fill=GREEN, font=header_font)

    kv_pairs = [
        ("key: 1010", "val: tx_data_abc", GREEN),
        ("key: 0101", "val: block_hash_7f", CYAN),
        ("key: 1100", "val: peer_addr_42", ORANGE),
    ]

    for i, (k, v, col) in enumerate(kv_pairs):
        ky = kv_y + 32 + i * 28
        draw_rounded_box(draw, kv_x + 10, ky, 140, 22, DARK_BOX, col, 3)
        kw = text_w(draw, k, small_font)
        draw.text((kv_x + 10 + (140 - kw) // 2, ky + 4), k, fill=col, font=small_font)

        marching_hline(draw, kv_x + 155, kv_x + 180, ky + 11, col, f, i)

        draw_rounded_box(draw, kv_x + 185, ky, 150, 22, DARK_BOX, BORDER, 3)
        vw = text_w(draw, v, small_font)
        draw.text((kv_x + 185 + (150 - vw) // 2, ky + 4), v, fill=WHITE, font=small_font)

    # === Bottom: Properties ===
    bot_y = 335
    bot_h = 200
    draw_rounded_box(draw, 30, bot_y, 740, bot_h, PANEL, BORDER)

    prop_lbl = "DHT PROPERTIES"
    prop_lbl_w = text_w(draw, prop_lbl, header_font)
    draw.text(((W - prop_lbl_w) // 2, bot_y + 10), prop_lbl, fill=CYAN, font=header_font)

    # Four property boxes
    prop_w = 165
    prop_gap = 15
    total_prop = 4 * prop_w + 3 * prop_gap
    prop_start = (W - total_prop) // 2

    props = [
        ("O(log n) Hops", "Lookup in log(n)", "steps, not n", CYAN),
        ("Decentralized", "No central server", "all peers equal", GREEN),
        ("XOR Metric", "Distance = XOR", "of node IDs", ORANGE),
        ("Self-Healing", "Nodes join/leave", "routing adapts", PURPLE),
    ]

    for i, (hdr, l1, l2, col) in enumerate(props):
        px = prop_start + i * (prop_w + prop_gap)
        py = bot_y + 35

        hdr_w = text_w(draw, hdr, header_font)
        draw.text((px + (prop_w - hdr_w) // 2, py), hdr, fill=col, font=header_font)

        draw_rounded_box(draw, px + 3, py + 22, prop_w - 6, 50, DARK_BOX, BORDER, 4)
        l1w = text_w(draw, l1, body_font)
        l2w = text_w(draw, l2, body_font)
        draw.text((px + 3 + (prop_w - 6 - l1w) // 2, py + 30), l1, fill=WHITE, font=body_font)
        draw.text((px + 3 + (prop_w - 6 - l2w) // 2, py + 48), l2, fill=col, font=body_font)

    # Routing table visualization
    rt_y = bot_y + 115
    rt_lbl = "ROUTING TABLE (k-buckets by XOR distance)"
    rt_lbl_w = text_w(draw, rt_lbl, body_font)
    draw.text(((W - rt_lbl_w) // 2, rt_y), rt_lbl, fill=ORANGE, font=body_font)

    # Show k-buckets as progressively larger ranges
    bucket_y = rt_y + 22
    bucket_labels = ["d=1", "d=2", "d=4", "d=8"]
    bucket_widths = [60, 100, 160, 280]
    total_bw = sum(bucket_widths) + 3 * 8
    bx = (W - total_bw) // 2

    for i, (bl, bw) in enumerate(zip(bucket_labels, bucket_widths)):
        # Pulsing bucket
        active_bucket = (f * 4 // FRAMES) % 4
        col = [CYAN, GREEN, ORANGE, PURPLE][i]
        if i == active_bucket:
            bcol = tuple(int(c * (0.7 + 0.3 * pulse)) for c in col)
        else:
            bcol = BORDER
        draw_rounded_box(draw, bx, bucket_y, bw, 26, DARK_BOX, bcol, 3)
        blw = text_w(draw, bl, small_font)
        tcol = col if i == active_bucket else DIM
        draw.text((bx + (bw - blw) // 2, bucket_y + 6), bl, fill=tcol, font=small_font)
        bx += bw + 8

    use = "Used in: BitTorrent, IPFS, Ethereum node discovery"
    use_w = text_w(draw, use, small_font)
    draw.text(((W - use_w) // 2, bot_y + bot_h - 25), use, fill=DIM, font=small_font)

    return img

if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save("assets/gifs/core_12_distributed_hash_tables.gif", save_all=True,
                   append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print("Saved assets/gifs/core_12_distributed_hash_tables.gif")
