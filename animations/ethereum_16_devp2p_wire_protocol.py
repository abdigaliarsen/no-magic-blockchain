"""
devp2p Wire Protocol: Two node circles connected, RLPx frame structure,
capability negotiation badges, message exchange with marching arrows.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/ethereum_16_devp2p_wire_protocol.gif"

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
ORANGE_BG = (55, 35, 15)


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
font_tiny = load_font(10)


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def draw_rounded_rect(draw, xy, fill, outline=None, radius=8):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def draw_node_circle(draw, cx, cy, r, color, label, sublabel, font_l, font_s):
    """Draw a large node circle with label."""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=DARK_BOX, outline=color, width=3)
    tw, th = text_size(draw, label, font_l)
    draw.text((cx - tw // 2, cy - th // 2 - 6), label, font=font_l, fill=color)
    sw, sh = text_size(draw, sublabel, font_s)
    draw.text((cx - sw // 2, cy - sh // 2 + 10), sublabel, font=font_s, fill=DIM)


def draw_marching_dot(draw, x1, y1, x2, y2, color, t_anim):
    """Draw an animated dot moving along a line."""
    prog = t_anim % 1.0
    dx = x1 + (x2 - x1) * prog
    dy = y1 + (y2 - y1) * prog
    draw.ellipse((dx - 4, dy - 4, dx + 4, dy + 4), fill=color)


def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / (FRAMES - 1)

    # --- Title ---
    draw.text((30, 18), "devp2p Wire Protocol", font=font_title, fill=WHITE)
    draw.line((30, 52, 770, 52), fill=BORDER, width=1)

    # === Top: Two Nodes Connected ===
    draw.text((40, 60), "Peer Connection (RLPx)", font=font_header, fill=CYAN)

    # Node A
    na_cx, na_cy, na_r = 140, 120, 35
    draw_node_circle(draw, na_cx, na_cy, na_r, CYAN, "Node A", "enode://a1b2", font_body, font_tiny)

    # Node B
    nb_cx, nb_cy, nb_r = 660, 120, 35
    draw_node_circle(draw, nb_cx, nb_cy, nb_r, GREEN, "Node B", "enode://c3d4", font_body, font_tiny)

    # Connection line between nodes
    line_x1 = na_cx + na_r + 5
    line_x2 = nb_cx - nb_r - 5
    line_y = 120
    draw.line((line_x1, line_y, line_x2, line_y), fill=BORDER, width=2)

    # Encrypted label on connection
    enc_pulse = 0.5 + 0.5 * math.sin(t * math.pi * 3)
    enc_color = lerp_color(DIM, YELLOW, enc_pulse)
    draw.text((360, line_y - 16), "ECIES encrypted", font=font_small, fill=enc_color)

    # Marching dots in both directions
    draw_marching_dot(draw, line_x1, line_y - 3, line_x2, line_y - 3, CYAN, t * 2)
    draw_marching_dot(draw, line_x2, line_y + 3, line_x1, line_y + 3, GREEN, t * 2 + 0.5)

    # Capability badges under each node
    caps_a = [("eth/68", CYAN), ("snap/1", PURPLE), ("les/4", ORANGE)]
    caps_b = [("eth/68", CYAN), ("snap/1", PURPLE)]

    bx = na_cx - 55
    for cap, color in caps_a:
        cw = len(cap) * 7 + 12
        draw_rounded_rect(draw, (bx, 162, bx + cw, 178), fill=DARK_BOX, outline=color, radius=4)
        draw.text((bx + 6, 164), cap, font=font_tiny, fill=color)
        bx += cw + 5

    bx = nb_cx - 40
    for cap, color in caps_b:
        cw = len(cap) * 7 + 12
        draw_rounded_rect(draw, (bx, 162, bx + cw, 178), fill=DARK_BOX, outline=color, radius=4)
        draw.text((bx + 6, 164), cap, font=font_tiny, fill=color)
        bx += cw + 5

    # === Middle: RLPx Frame Structure ===
    draw.line((30, 190, 770, 190), fill=BORDER, width=1)
    draw.text((40, 198), "RLPx Frame Structure", font=font_header, fill=YELLOW)

    frame_y = 222
    frame_h = 38

    # Frame sections
    sections = [
        ("Header", "16 bytes", CYAN, CYAN_BG, 40, 130),
        ("Header MAC", "16 bytes", DIM, DARK_BOX, 175, 110),
        ("Frame Data", "variable", GREEN, GREEN_BG, 290, 250),
        ("Frame MAC", "16 bytes", DIM, DARK_BOX, 545, 110),
        ("Padding", "0-15 B", BORDER, DARK_BOX, 660, 100),
    ]

    for label, size_str, color, bg, sx, sw in sections:
        box = (sx, frame_y, sx + sw, frame_y + frame_h)
        draw_rounded_rect(draw, box, fill=bg, outline=color, radius=4)
        draw.text((sx + 6, frame_y + 3), label, font=font_small, fill=color)
        draw.text((sx + 6, frame_y + 19), size_str, font=font_tiny, fill=DIM)

    # Bracket under frame
    draw.line((40, frame_y + frame_h + 4, 760, frame_y + frame_h + 4), fill=DIM, width=1)
    draw.text((340, frame_y + frame_h + 6), "AES-256-CTR encrypted", font=font_tiny, fill=DIM)

    # === Message Exchange Sequence ===
    msg_y = frame_y + frame_h + 26
    draw.line((30, msg_y, 770, msg_y), fill=BORDER, width=1)
    draw.text((40, msg_y + 6), "eth/68 Message Exchange", font=font_header, fill=GREEN)

    # Two vertical lines (timelines)
    tl_a_x = 140
    tl_b_x = 660
    seq_top = msg_y + 28
    seq_bot = 490
    draw.line((tl_a_x, seq_top, tl_a_x, seq_bot), fill=DIM, width=1)
    draw.line((tl_b_x, seq_top, tl_b_x, seq_bot), fill=DIM, width=1)
    draw.text((tl_a_x - 15, seq_top - 2), "A", font=font_body, fill=CYAN)
    draw.text((tl_b_x - 15, seq_top - 2), "B", font=font_body, fill=GREEN)

    # Messages (arrows between timelines)
    messages = [
        ("Status", "chain head, genesis, forkID", CYAN, True),       # A -> B
        ("Status", "chain head, genesis, forkID", GREEN, False),      # B -> A
        ("NewBlockHashes", "announce new block hash", YELLOW, True),  # A -> B
        ("GetBlockHeaders", "request headers by hash", ORANGE, False),  # B -> A
        ("BlockHeaders", "respond with headers", PURPLE, True),       # A -> B
    ]

    row_h = (seq_bot - seq_top - 20) / len(messages)
    for i, (msg_name, desc, color, left_to_right) in enumerate(messages):
        my = seq_top + 14 + int(i * row_h)
        if left_to_right:
            ax1, ax2 = tl_a_x + 5, tl_b_x - 5
        else:
            ax1, ax2 = tl_b_x - 5, tl_a_x + 5

        # Arrow line
        draw.line((ax1, my, ax2, my), fill=DIM, width=1)
        # Arrowhead
        direction = 1 if ax2 > ax1 else -1
        draw.polygon([(ax2, my), (ax2 - direction * 8, my - 4), (ax2 - direction * 8, my + 4)], fill=color)

        # Animated dot
        phase = t * 2 + i * 0.2
        draw_marching_dot(draw, ax1, my, ax2, my, color, phase)

        # Label above arrow
        label_x = (ax1 + ax2) // 2
        tw, _ = text_size(draw, msg_name, font_small)
        draw.text((label_x - tw // 2, my - 14), msg_name, font=font_small, fill=color)

        # Description below arrow
        dw, _ = text_size(draw, desc, font_tiny)
        draw.text((label_x - dw // 2, my + 4), desc, font=font_tiny, fill=DIM)

    # === Bottom: Protocol Stack ===
    draw.line((30, seq_bot + 8, 770, seq_bot + 8), fill=BORDER, width=1)
    stack_y = seq_bot + 14
    draw.text((40, stack_y), "Stack:", font=font_small, fill=DIM)

    layers = [
        ("TCP/IP", DIM),
        ("RLPx", YELLOW),
        ("devp2p", CYAN),
        ("eth/68", GREEN),
        ("snap/1", PURPLE),
    ]

    lx = 100
    for layer, color in layers:
        lw = len(layer) * 7 + 16
        draw_rounded_rect(draw, (lx, stack_y - 2, lx + lw, stack_y + 16), fill=DARK_BOX, outline=color, radius=4)
        draw.text((lx + 8, stack_y), layer, font=font_small, fill=color)
        # Arrow between layers
        if layer != "snap/1":
            draw.text((lx + lw + 3, stack_y), "->", font=font_small, fill=DIM)
        lx += lw + 22

    # Bottom note
    draw.text((40, 530), "devp2p: Ethereum's peer-to-peer networking layer", font=font_small, fill=DIM)

    return img


if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print(f"Saved {OUT}")
