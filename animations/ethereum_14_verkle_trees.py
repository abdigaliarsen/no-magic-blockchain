"""
Verkle Trees: Tree diagram with vector commitments at nodes,
side-by-side proof size comparison Merkle vs Verkle, bandwidth savings.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/ethereum_14_verkle_trees.gif"

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


def draw_node(draw, cx, cy, r, color, label, font, is_highlight=False):
    """Draw a tree node as a colored dot with label."""
    fill = color if is_highlight else DARK_BOX
    outline = color
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=outline, width=2)
    tw, th = text_size(draw, label, font)
    draw.text((cx - tw // 2, cy - th // 2), label, font=font, fill=WHITE if is_highlight else color)


def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / (FRAMES - 1)

    # --- Title ---
    draw.text((30, 18), "Verkle Trees", font=font_title, fill=WHITE)
    draw.line((30, 52, 770, 52), fill=BORDER, width=1)

    # === Left: Merkle Tree (for comparison) ===
    draw.text((40, 60), "Merkle Tree", font=font_header, fill=RED)
    draw.text((40, 78), "Hash-based nodes", font=font_small, fill=DIM)

    # Merkle tree structure: root -> 2 children -> 4 leaves
    mx_root = 190
    my_root = 110
    # Level 1
    mx_l = 120
    mx_r = 260
    my_1 = 155
    # Level 2 (leaves)
    mx_ll, mx_lr = 90, 150
    mx_rl, mx_rr = 230, 290
    my_2 = 200

    # Draw edges first
    draw.line((mx_root, my_root + 12, mx_l, my_1 - 12), fill=DIM, width=1)
    draw.line((mx_root, my_root + 12, mx_r, my_1 - 12), fill=DIM, width=1)
    draw.line((mx_l, my_1 + 12, mx_ll, my_2 - 12), fill=DIM, width=1)
    draw.line((mx_l, my_1 + 12, mx_lr, my_2 - 12), fill=DIM, width=1)
    draw.line((mx_r, my_1 + 12, mx_rl, my_2 - 12), fill=DIM, width=1)
    draw.line((mx_r, my_1 + 12, mx_rr, my_2 - 12), fill=DIM, width=1)

    # Draw nodes
    draw_node(draw, mx_root, my_root, 12, RED, "H", font_small)
    draw_node(draw, mx_l, my_1, 12, RED, "H", font_small)
    draw_node(draw, mx_r, my_1, 12, RED, "H", font_small)
    draw_node(draw, mx_ll, my_2, 10, ORANGE, "L0", font_small)
    draw_node(draw, mx_lr, my_2, 10, ORANGE, "L1", font_small)
    draw_node(draw, mx_rl, my_2, 10, ORANGE, "L2", font_small)
    draw_node(draw, mx_rr, my_2, 10, ORANGE, "L3", font_small)

    # Highlight proof path for L0: needs sibling L1, sibling H(right)
    pulse = 0.5 + 0.5 * math.sin(t * math.pi * 3)
    proof_color = lerp_color(DIM, YELLOW, pulse)
    # Sibling highlights
    draw.ellipse((mx_lr - 13, my_2 - 13, mx_lr + 13, my_2 + 13), outline=proof_color, width=2)
    draw.ellipse((mx_r - 13, my_1 - 13, mx_r + 13, my_1 + 13), outline=proof_color, width=2)
    draw.text((300, my_1 - 5), "siblings", font=font_small, fill=proof_color)
    draw.text((300, my_1 + 8), "needed", font=font_small, fill=proof_color)

    # === Right: Verkle Tree ===
    draw.text((420, 60), "Verkle Tree", font=font_header, fill=GREEN)
    draw.text((420, 78), "Vector commitment nodes", font=font_small, fill=DIM)

    # Verkle tree: root -> 4 children (wider branching)
    vx_root = 590
    vy_root = 110
    # 4 children
    vc_xs = [480, 540, 640, 700]
    vy_1 = 160
    # 8 leaves (2 per child)
    vl_xs = [465, 495, 525, 555, 625, 655, 685, 715]
    vy_2 = 205

    # Edges
    for vx in vc_xs:
        draw.line((vx_root, vy_root + 12, vx, vy_1 - 12), fill=DIM, width=1)
    for i, vx in enumerate(vl_xs):
        parent = vc_xs[i // 2]
        draw.line((parent, vy_1 + 10, vx, vy_2 - 8), fill=DIM, width=1)

    # Nodes (colored dots = vector commitments)
    draw_node(draw, vx_root, vy_root, 12, GREEN, "C", font_small, is_highlight=True)
    for i, vx in enumerate(vc_xs):
        draw_node(draw, vx, vy_1, 10, CYAN, "C", font_small)
    for i, vx in enumerate(vl_xs):
        draw_node(draw, vx, vy_2, 7, PURPLE, str(i), font_small)

    # Proof: just the path, no siblings!
    path_pulse = lerp_color(DIM, GREEN, pulse)
    draw.ellipse((vc_xs[0] - 13, vy_1 - 13, vc_xs[0] + 13, vy_1 + 13), outline=path_pulse, width=2)
    draw.text((420, vy_1 + 18), "path only!", font=font_small, fill=path_pulse)

    # === Proof Size Comparison ===
    draw.line((30, 230, 770, 230), fill=BORDER, width=1)
    draw.text((40, 238), "Proof Size Comparison", font=font_header, fill=YELLOW)

    # Bar chart
    bar_y = 268
    bar_h = 30

    # Merkle proof bar
    merkle_w = 500  # wider = more data
    draw_rounded_rect(draw, (40, bar_y, 40 + merkle_w, bar_y + bar_h), fill=RED_BG, outline=RED, radius=4)
    draw.text((50, bar_y + 7), "Merkle: ~4 KB proof (log2(n) sibling hashes)", font=font_small, fill=RED)

    # Verkle proof bar
    verkle_w = 120  # much smaller
    draw_rounded_rect(draw, (40, bar_y + 42, 40 + verkle_w, bar_y + 42 + bar_h), fill=GREEN_BG, outline=GREEN, radius=4)
    draw.text((50, bar_y + 49), "Verkle: ~150 B", font=font_small, fill=GREEN)

    # Savings label
    savings_pulse = lerp_color(DIM, GREEN, 0.5 + 0.5 * math.sin(t * math.pi * 2))
    draw.text((180, bar_y + 49), "~96% smaller!", font=font_small, fill=savings_pulse)

    # === Bottom: Key Properties ===
    draw.line((30, bar_y + 88, 770, bar_y + 88), fill=BORDER, width=1)
    prop_y = bar_y + 98
    draw.text((40, prop_y), "Key Differences", font=font_header, fill=CYAN)

    props = [
        ("Branching", "Binary (2)", "Wide (256)", RED, GREEN),
        ("Proof Data", "All siblings on path", "Just path + opening", RED, GREEN),
        ("Commitment", "Hash (SHA/Keccak)", "Polynomial (IPA/KZG)", RED, GREEN),
        ("Stateless", "Large witness", "Compact witness", RED, GREEN),
    ]

    py = prop_y + 24
    for label, merkle_val, verkle_val, mc, vc in props:
        draw.text((50, py), label, font=font_small, fill=WHITE)
        draw.text((180, py), merkle_val, font=font_small, fill=mc)
        draw.text((420, py), verkle_val, font=font_small, fill=vc)
        py += 20

    # Column headers
    draw.text((180, prop_y + 6), "Merkle", font=font_small, fill=RED)
    draw.text((420, prop_y + 6), "Verkle", font=font_small, fill=GREEN)

    # === Bottom: Statelessness note ===
    draw.line((30, py + 10, 770, py + 10), fill=BORDER, width=1)
    note_y = py + 18
    draw.text((40, note_y), "Ethereum Statelessness", font=font_header, fill=PURPLE)

    # Animated benefit boxes
    benefits = [
        ("No full state", "Validators don't need\nfull state to verify", PURPLE),
        ("Smaller proofs", "Witnesses fit in\nblock bandwidth", GREEN),
        ("Weak nodes OK", "Light clients can\nverify everything", CYAN),
    ]

    bx = 40
    for label, desc, color in benefits:
        bg = PURPLE_BG if color == PURPLE else GREEN_BG if color == GREEN else CYAN_BG
        bbox = (bx, note_y + 22, bx + 230, note_y + 70)
        draw_rounded_rect(draw, bbox, fill=bg, outline=color)
        draw.text((bx + 10, note_y + 26), label, font=font_body, fill=color)
        lines = desc.split("\n")
        for j, line in enumerate(lines):
            draw.text((bx + 10, note_y + 42 + j * 13), line, font=font_small, fill=DIM)
        bx += 242

    # Bottom note
    draw.text((40, 530), "Verkle trees: enabling stateless Ethereum with compact proofs", font=font_small, fill=DIM)

    return img


if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print(f"Saved {OUT}")
