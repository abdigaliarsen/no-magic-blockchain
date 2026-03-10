"""
SSZ Encoding: BeaconBlockHeader struct serialized into bytes,
then Merkleized into a hash tree with root at top.
Highlights generalized index path.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/ethereum_09_ssz_encoding.gif"

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


def load_font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for n in names:
        for p in [f"/usr/share/fonts/truetype/dejavu/{n}", f"/usr/share/fonts/truetype/liberation/{n}", f"/usr/share/fonts/{n}"]:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
    return ImageFont.load_default()


font_title = load_font(26, bold=True)
font_header = load_font(15, bold=True)
font_body = load_font(13)
font_small = load_font(11)


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def draw_rounded_rect(draw, xy, fill, outline=None, radius=8):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# Struct fields for BeaconBlockHeader
FIELDS = [
    ("slot", "uint64", "8 bytes", CYAN),
    ("proposer_index", "uint64", "8 bytes", GREEN),
    ("parent_root", "Bytes32", "32 bytes", YELLOW),
    ("state_root", "Bytes32", "32 bytes", ORANGE),
]

# Merkle tree labels (leaf hashes -> intermediate -> root)
LEAVES = ["h(slot)", "h(prop)", "h(par_r)", "h(st_r)"]
MIDS = ["h(0,1)", "h(2,3)"]
ROOT = "root"


def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / (FRAMES - 1)

    # --- Title ---
    draw.text((30, 18), "SSZ: Serialize + Merkleize", font=font_title, fill=WHITE)
    draw.line((30, 52, 770, 52), fill=BORDER, width=1)

    # --- Left panel: Struct fields ---
    draw.text((40, 62), "BeaconBlockHeader", font=font_header, fill=CYAN)
    field_y = 88
    field_boxes = []
    for i, (name, typ, size, color) in enumerate(FIELDS):
        bx = (40, field_y, 260, field_y + 40)
        draw_rounded_rect(draw, bx, fill=DARK_BOX, outline=color)
        draw.text((50, field_y + 4), name, font=font_body, fill=color)
        draw.text((50, field_y + 22), f"{typ} ({size})", font=font_small, fill=DIM)
        field_boxes.append((bx, color))
        field_y += 50

    # --- Middle: Arrow showing serialization ---
    arrow_x1, arrow_x2 = 270, 320
    arrow_y = 170
    draw.line((arrow_x1, arrow_y, arrow_x2, arrow_y), fill=DIM, width=2)
    draw.polygon([(arrow_x2, arrow_y), (arrow_x2 - 6, arrow_y - 4), (arrow_x2 - 6, arrow_y + 4)], fill=WHITE)
    draw.text((272, arrow_y - 18), "serialize", font=font_small, fill=DIM)

    # Animate a dot along the arrow
    dot_x = arrow_x1 + (arrow_x2 - arrow_x1) * ((t * 3) % 1.0)
    draw.ellipse((dot_x - 3, arrow_y - 3, dot_x + 3, arrow_y + 3), fill=YELLOW)

    # --- Right panel: Byte stream ---
    draw.text((335, 62), "Serialized Bytes", font=font_header, fill=GREEN)
    byte_y = 88
    byte_segments = [
        ("00 07 00 00 00 00 00 00", CYAN, "slot = 7"),
        ("05 00 00 00 00 00 00 00", GREEN, "proposer = 5"),
        ("a1 b2 c3 ... (32 bytes)", YELLOW, "parent_root"),
        ("d4 e5 f6 ... (32 bytes)", ORANGE, "state_root"),
    ]
    total_offset = 0
    offsets = [0, 8, 16, 48]
    for i, (hex_str, color, label) in enumerate(byte_segments):
        bx = (335, byte_y, 580, byte_y + 40)
        draw_rounded_rect(draw, bx, fill=DARK_BOX, outline=color)
        draw.text((345, byte_y + 4), hex_str, font=font_small, fill=color)
        draw.text((345, byte_y + 20), f"offset {offsets[i]}: {label}", font=font_small, fill=DIM)
        byte_y += 50

    # --- Fixed-size note ---
    draw.text((335, byte_y + 5), "Total: 80 bytes (all fixed-size)", font=font_small, fill=DIM)

    # --- Bottom: Merkle tree ---
    draw.line((30, 310, 770, 310), fill=BORDER, width=1)
    draw.text((40, 318), "Merkleization (Hash Tree Root)", font=font_header, fill=PURPLE)

    # Leaf level (y=370)
    leaf_y = 380
    leaf_positions = []
    leaf_colors = [CYAN, GREEN, YELLOW, ORANGE]
    leaf_w = 100
    leaf_spacing = 140
    leaf_start_x = 110
    for i, (lbl, color) in enumerate(zip(LEAVES, leaf_colors)):
        cx = leaf_start_x + i * leaf_spacing
        bx = (cx - leaf_w // 2, leaf_y, cx + leaf_w // 2, leaf_y + 32)
        draw_rounded_rect(draw, bx, fill=DARK_BOX, outline=color)
        tw, _ = text_size(draw, lbl, font_small)
        draw.text((cx - tw // 2, leaf_y + 9), lbl, font=font_small, fill=color)
        leaf_positions.append((cx, leaf_y))

    # Mid level (y=440)
    mid_y = 440
    mid_positions = []
    mid_colors = [PURPLE, PURPLE]
    for i, lbl in enumerate(MIDS):
        cx = leaf_start_x + i * 2 * leaf_spacing + leaf_spacing // 2
        bx = (cx - leaf_w // 2, mid_y, cx + leaf_w // 2, mid_y + 32)
        draw_rounded_rect(draw, bx, fill=PURPLE_BG, outline=PURPLE)
        tw, _ = text_size(draw, lbl, font_small)
        draw.text((cx - tw // 2, mid_y + 9), lbl, font=font_small, fill=PURPLE)
        mid_positions.append((cx, mid_y))

    # Root level (y=500)
    root_y = 498
    root_cx = (mid_positions[0][0] + mid_positions[1][0]) // 2
    bx = (root_cx - leaf_w // 2, root_y, root_cx + leaf_w // 2, root_y + 32)
    draw_rounded_rect(draw, bx, fill=RED_BG, outline=RED)
    tw, _ = text_size(draw, ROOT, font_body)
    draw.text((root_cx - tw // 2, root_y + 8), ROOT, font=font_body, fill=RED)

    # Lines: leaves -> mids
    for i in range(4):
        mid_idx = i // 2
        lx, ly = leaf_positions[i]
        mx, my = mid_positions[mid_idx]
        draw.line((lx, ly + 32, mx, my), fill=DIM, width=1)

    # Lines: mids -> root
    for mx, my in mid_positions:
        draw.line((mx, my + 32, root_cx, root_y), fill=DIM, width=1)

    # Animated generalized index highlight path
    # Path: root -> h(2,3) -> h(st_r) (generalized index 7 = state_root)
    path_nodes = [
        (root_cx, root_y + 16),
        (mid_positions[1][0], mid_y + 16),
        (leaf_positions[3][0], leaf_y + 16),
    ]
    # Pulse along the path
    pulse = (t * 2) % 1.0
    for i in range(len(path_nodes) - 1):
        x1, y1 = path_nodes[i]
        x2, y2 = path_nodes[i + 1]
        seg_t = max(0.0, min(1.0, pulse * 2 - i * 0.5))
        px = x1 + (x2 - x1) * seg_t
        py = y1 + (y2 - y1) * seg_t
        draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=RED)

    # Generalized index label
    draw.text((610, 318), "gindex 7 = state_root", font=font_small, fill=RED)

    # Right side: offset table
    draw.text((620, 62), "SSZ Properties", font=font_header, fill=WHITE)
    props = [
        ("Little-endian", CYAN),
        ("Fixed offsets", GREEN),
        ("32-byte chunks", YELLOW),
        ("Deterministic", ORANGE),
    ]
    py = 88
    for label, color in props:
        # Animated check mark pulse
        pulse_v = 0.5 + 0.5 * math.sin(t * math.pi * 2 + py * 0.05)
        dot_color = lerp_color(DIM, color, pulse_v)
        draw.ellipse((625, py + 4, 635, py + 14), fill=dot_color)
        draw.text((642, py + 2), label, font=font_body, fill=color)
        py += 26

    return img


if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print(f"Saved {OUT}")
