"""
Merkle Patricia Trie - Variant B: Trie Structure
Visual trie with key-value pairs showing root -> extension -> branch -> leaf paths.
Each node type color-coded. Animated scan line traces path through trie.
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- Configuration ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/ethereum_05_merkle_patricia_trie.gif"

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


def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def draw_rounded_rect(draw, xy, fill, outline, radius=6):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def draw_arrow(draw, x0, y0, x1, y1, color, width=2):
    draw.line([(x0, y0), (x1, y1)], fill=color, width=width)
    angle = math.atan2(y1 - y0, x1 - x0)
    size = 6
    lx = x1 - size * math.cos(angle - 0.4)
    ly = y1 - size * math.sin(angle - 0.4)
    rx = x1 - size * math.cos(angle + 0.4)
    ry = y1 - size * math.sin(angle + 0.4)
    draw.polygon([(x1, y1), (int(lx), int(ly)), (int(rx), int(ry))], fill=color)


# Trie node definitions with positions
# Structure: root(ext "a7") -> branch -> leaf1("7d3" = 42ETH), leaf2("b91" = 10ETH), ext2("c") -> leaf3("5f" = 7ETH)
# Layout as a tree

NODES = {
    "root": {"type": "EXT", "label": "EXT", "detail": 'prefix: "a7"', "x": 400, "y": 100, "color": CYAN, "bg": CYAN_BG},
    "branch": {"type": "BRANCH", "label": "BRANCH", "detail": "slots 0-f", "x": 400, "y": 200, "color": YELLOW, "bg": YELLOW_BG},
    "leaf1": {"type": "LEAF", "label": "LEAF", "detail": '"7d3"->42', "x": 180, "y": 330, "color": GREEN, "bg": GREEN_BG},
    "leaf2": {"type": "LEAF", "label": "LEAF", "detail": '"b91"->10', "x": 400, "y": 330, "color": GREEN, "bg": GREEN_BG},
    "ext2": {"type": "EXT", "label": "EXT", "detail": 'prefix: "c"', "x": 620, "y": 310, "color": CYAN, "bg": CYAN_BG},
    "leaf3": {"type": "LEAF", "label": "LEAF", "detail": '"5f"->7', "x": 620, "y": 420, "color": GREEN, "bg": GREEN_BG},
}

EDGES = [
    ("root", "branch", ""),
    ("branch", "leaf1", "[7]"),
    ("branch", "leaf2", "[b]"),
    ("branch", "ext2", "[c]"),
    ("ext2", "leaf3", ""),
]

# Three lookup paths we animate through
PATHS = [
    {"keys": ["root", "branch", "leaf1"], "label": 'key: "a77d3" -> 42 ETH', "edge_labels": ["a7", "[7]", "d3"]},
    {"keys": ["root", "branch", "leaf2"], "label": 'key: "a7b91" -> 10 ETH', "edge_labels": ["a7", "[b]", "91"]},
    {"keys": ["root", "branch", "ext2", "leaf3"], "label": 'key: "a7c5f" -> 7 ETH', "edge_labels": ["a7", "[c]", "c", "5f"]},
]

NODE_W = 120
NODE_H = 50


def draw_frame(frame_idx):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Phase: cycle through 3 paths (12 frames each)
    path_idx = frame_idx // 12
    local_t = (frame_idx % 12) / 11.0

    current_path = PATHS[path_idx]
    path_keys = current_path["keys"]
    # How far along the path the scan is (0.0 to 1.0 maps to nodes)
    scan_progress = local_t
    # Which edge is being traversed
    num_edges = len(path_keys) - 1
    edge_float = scan_progress * num_edges
    active_edge = min(int(edge_float), num_edges - 1)
    edge_t = edge_float - active_edge
    if edge_float >= num_edges:
        active_edge = num_edges - 1
        edge_t = 1.0

    # Title
    title = "Merkle Patricia Trie: Structure"
    tw, _ = text_size(draw, title, font_title)
    draw.text(((W - tw) // 2, 12), title, fill=WHITE, font=font_title)

    # Current lookup label
    lbl = current_path["label"]
    lw, _ = text_size(draw, lbl, font_body)
    draw.text(((W - lw) // 2, 46), lbl, fill=ORANGE, font=font_body)

    # Legend at bottom
    legend_y = 490
    legend_items = [("EXT", CYAN), ("BRANCH", YELLOW), ("LEAF", GREEN)]
    lx = 60
    for ltxt, lcol in legend_items:
        draw_rounded_rect(draw, (lx, legend_y, lx + 14, legend_y + 14), fill=lcol, outline=lcol, radius=3)
        draw.text((lx + 20, legend_y), ltxt, fill=DIM, font=font_small)
        tw2, _ = text_size(draw, ltxt, font_small)
        lx += tw2 + 40

    # Key-value table on right
    kv_x = 620
    kv_y = 475
    draw.text((kv_x, kv_y), "Stored pairs:", fill=WHITE, font=font_body)
    pairs = [("a77d3", "42"), ("a7b91", "10"), ("a7c5f", "7")]
    for pi, (k, v) in enumerate(pairs):
        py = kv_y + 14 + pi * 14
        pcol = ORANGE if pi == path_idx else DIM
        draw.text((kv_x, py), f"{k} -> {v}", fill=pcol, font=font_small)

    # Draw all edges first (behind nodes)
    for src_name, dst_name, elbl in EDGES:
        src = NODES[src_name]
        dst = NODES[dst_name]
        sx, sy = src["x"], src["y"] + NODE_H // 2
        dx, dy = dst["x"], dst["y"] - NODE_H // 2

        # Check if this edge is on the active path
        on_path = False
        path_edge_idx = -1
        for ei in range(len(path_keys) - 1):
            if path_keys[ei] == src_name and path_keys[ei + 1] == dst_name:
                on_path = True
                path_edge_idx = ei
                break

        if on_path and path_edge_idx <= active_edge:
            # Animated: bright color with glow effect
            if path_edge_idx < active_edge:
                ecol = ORANGE
            else:
                pulse = 0.5 + 0.5 * math.sin(edge_t * math.pi)
                ecol = lerp_color(DIM, ORANGE, pulse)
            ewidth = 3
        else:
            ecol = BORDER
            ewidth = 1

        draw_arrow(draw, sx, sy, dx, dy, ecol, width=ewidth)

        # Edge label — use bright color and larger font for readability
        if elbl:
            mx = (sx + dx) // 2 + 8
            my = (sy + dy) // 2 - 8
            elbl_col = CYAN if not (on_path and path_edge_idx <= active_edge) else ORANGE
            draw.text((mx, my), elbl, fill=elbl_col, font=font_body)

    # Draw scan dot on active edge
    if 0 <= active_edge < num_edges:
        src_name = path_keys[active_edge]
        dst_name = path_keys[active_edge + 1]
        src = NODES[src_name]
        dst = NODES[dst_name]
        sx, sy = src["x"], src["y"] + NODE_H // 2
        dx, dy = dst["x"], dst["y"] - NODE_H // 2
        dot_x = int(sx + (dx - sx) * edge_t)
        dot_y = int(sy + (dy - sy) * edge_t)
        draw.ellipse((dot_x - 5, dot_y - 5, dot_x + 5, dot_y + 5), fill=ORANGE)

    # Draw all nodes
    for nname, node in NODES.items():
        nx = node["x"] - NODE_W // 2
        ny = node["y"] - NODE_H // 2
        col = node["color"]
        bg_col = node["bg"]

        # Is this node on the current path?
        on_path = nname in path_keys
        node_path_idx = path_keys.index(nname) if on_path else -1
        # Node is "reached" if scan has passed it
        reached = on_path and (node_path_idx <= active_edge or (node_path_idx == active_edge + 1 and edge_t > 0.9))

        if reached:
            pulse = 0.5 + 0.5 * math.sin(local_t * math.pi * 3)
            fill = lerp_color(bg_col, col, 0.15 + pulse * 0.1)
            border = lerp_color(col, WHITE, pulse * 0.3)
            text_col = WHITE
        else:
            fill = DARK_BOX
            border = BORDER
            text_col = col if on_path else DIM

        draw_rounded_rect(draw, (nx, ny, nx + NODE_W, ny + NODE_H), fill=fill, outline=border, radius=8)

        # Node label
        lw2, _ = text_size(draw, node["label"], font_header)
        draw.text((nx + (NODE_W - lw2) // 2, ny + 6), node["label"], fill=text_col, font=font_header)

        # Detail
        dw, _ = text_size(draw, node["detail"], font_small)
        draw.text((nx + (NODE_W - dw) // 2, ny + 26), node["detail"], fill=lerp_color(DIM, text_col, 0.5), font=font_small)

    # Nibble path visualization at bottom
    nibble_y = 460
    draw.text((60, nibble_y), "Path nibbles:", fill=DIM, font=font_small)
    key_str = current_path["label"].split('"')[1]
    nx_start = 160
    for ci, ch in enumerate(key_str):
        # Which part of the path is this nibble in?
        # Highlight nibbles up to scan progress
        nibbles_reached = int(scan_progress * len(key_str))
        if ci < nibbles_reached:
            ncol = ORANGE
        elif ci == nibbles_reached:
            pulse = 0.5 + 0.5 * math.sin(local_t * math.pi * 4)
            ncol = lerp_color(DIM, ORANGE, pulse)
        else:
            ncol = DIM
        cx_pos = nx_start + ci * 24
        draw_rounded_rect(draw, (cx_pos, nibble_y - 2, cx_pos + 18, nibble_y + 16), fill=PANEL, outline=BORDER, radius=3)
        cw, _ = text_size(draw, ch, font_body)
        draw.text((cx_pos + (18 - cw) // 2, nibble_y), ch, fill=ncol, font=font_body)

    return img


frames = [draw_frame(i) for i in range(FRAMES)]
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
print(f"Saved {OUT} ({len(frames)} frames)")
