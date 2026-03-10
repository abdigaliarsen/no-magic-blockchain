"""CORE10-A: Bloom Filters — probabilistic membership testing."""
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

def marching_line(draw, x1, y1, x2, y2, color, frame, idx=0):
    """Draw a marching-ant line from (x1,y1) to (x2,y2)."""
    dash_len = 6
    offset = (frame * 2 + idx * 5) % (dash_len * 2)
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    pos = offset % (dash_len * 2)
    while pos < length:
        sx = x1 + ux * pos
        sy = y1 + uy * pos
        end = min(pos + dash_len, length)
        ex = x1 + ux * end
        ey = y1 + uy * end
        draw.line([(sx, sy), (ex, ey)], fill=color, width=2)
        pos += dash_len * 2
    # Arrowhead
    draw.polygon([
        (x2, y2),
        (x2 - int(8 * ux - 5 * uy), y2 - int(8 * uy + 5 * ux)),
        (x2 - int(8 * ux + 5 * uy), y2 - int(8 * uy - 5 * ux)),
    ], fill=color)

def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    pulse = 0.5 + 0.5 * math.sin(f * 2 * math.pi / FRAMES)

    # Title
    title = "Bloom Filters"
    tw = text_w(draw, title, title_font)
    draw.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)
    subtitle = "Probabilistic set membership: fast \"maybe\" or definite \"no\""
    sw = text_w(draw, subtitle, small_font)
    draw.text(((W - sw) // 2, 44), subtitle, fill=DIM, font=small_font)

    # === Bit Array (central element) ===
    n_bits = 16
    cell_size = 32
    bit_gap = 3
    total_bit_w = n_bits * (cell_size + bit_gap) - bit_gap
    bit_x = (W - total_bit_w) // 2
    bit_y = 115

    # The bit array state: positions set by our items
    # "Alice" sets bits 2, 7, 13 (via 3 hash functions)
    # "Bob" sets bits 1, 7, 11
    # Combined set bits: {1, 2, 7, 11, 13}
    set_bits = {1, 2, 7, 11, 13}
    # "Eve" queries bits 3, 7, 13 — bit 3 is NOT set → definite No
    # "Carol" queries bits 2, 7, 11 — ALL set → false positive (Maybe!)

    bit_label = "BIT ARRAY (16 bits)"
    bl_w = text_w(draw, bit_label, header_font)
    draw.text(((W - bl_w) // 2, bit_y - 22), bit_label, fill=ORANGE, font=header_font)

    # Draw bit cells
    for i in range(n_bits):
        cx = bit_x + i * (cell_size + bit_gap)
        is_set = i in set_bits
        if is_set:
            fill = CYAN_BG
            border = CYAN
            txt_col = CYAN
            val = "1"
        else:
            fill = DARK_BOX
            border = BORDER
            txt_col = DIM
            val = "0"

        # Scanning highlight
        scan_pos = (f * n_bits // FRAMES) % n_bits
        if i == scan_pos:
            border = YELLOW
            fill = YELLOW_BG

        draw_rounded_box(draw, cx, bit_y, cell_size, cell_size, fill, border, 3)
        vw = text_w(draw, val, body_font)
        draw.text((cx + (cell_size - vw) // 2, bit_y + 8), val, fill=txt_col, font=body_font)
        # Index label
        idx_str = str(i)
        iw = text_w(draw, idx_str, small_font)
        draw.text((cx + (cell_size - iw) // 2, bit_y + cell_size + 3), idx_str, fill=DIM, font=small_font)

    # === INSERT section (left) ===
    ins_panel_x = 30
    ins_panel_y = 175
    ins_panel_w = 350
    ins_panel_h = 160
    draw_rounded_box(draw, ins_panel_x, ins_panel_y, ins_panel_w, ins_panel_h, PANEL, GREEN)
    ins_lbl = "INSERT"
    ins_lbl_w = text_w(draw, ins_lbl, header_font)
    draw.text((ins_panel_x + (ins_panel_w - ins_lbl_w) // 2, ins_panel_y + 8), ins_lbl, fill=GREEN, font=header_font)

    # Item boxes
    items = [
        ("Alice", GREEN, [2, 7, 13]),
        ("Bob", CYAN, [1, 7, 11]),
    ]
    for idx, (name, col, bits) in enumerate(items):
        ix = ins_panel_x + 20
        iy = ins_panel_y + 35 + idx * 65
        # Item box
        draw_rounded_box(draw, ix, iy, 65, 26, DARK_BOX, col, 4)
        nw = text_w(draw, name, body_font)
        draw.text((ix + (65 - nw) // 2, iy + 5), name, fill=col, font=body_font)

        # Hash function boxes
        for hi, bit_pos in enumerate(bits):
            hx = ix + 85 + hi * 80
            draw_rounded_box(draw, hx, iy, 60, 26, DARK_BOX, BORDER, 4)
            htxt = f"h{hi+1} -> {bit_pos}"
            htxt_w = text_w(draw, htxt, small_font)
            draw.text((hx + (60 - htxt_w) // 2, iy + 6), htxt, fill=col, font=small_font)

            # Arrow from hash to bit array
            target_cx = bit_x + bit_pos * (cell_size + bit_gap) + cell_size // 2
            alpha = 0.3 + 0.15 * pulse
            acol = tuple(int(c * alpha) for c in col)
            draw.line([(target_cx, bit_y + cell_size + 16), (target_cx, bit_y + cell_size + 16 + 3)],
                      fill=acol, width=1)

    # === QUERY section (right) ===
    q_panel_x = 420
    q_panel_y = 175
    q_panel_w = 350
    q_panel_h = 160
    draw_rounded_box(draw, q_panel_x, q_panel_y, q_panel_w, q_panel_h, PANEL, PURPLE)
    q_lbl = "QUERY"
    q_lbl_w = text_w(draw, q_lbl, header_font)
    draw.text((q_panel_x + (q_panel_w - q_lbl_w) // 2, q_panel_y + 8), q_lbl, fill=PURPLE, font=header_font)

    queries = [
        ("Eve", RED, [3, 7, 13], False, "Definite No"),
        ("Carol", ORANGE, [2, 7, 11], True, "Maybe (FP!)"),
    ]
    for idx, (name, col, bits, result, result_txt) in enumerate(queries):
        qx = q_panel_x + 15
        qy = q_panel_y + 35 + idx * 65
        # Item box
        draw_rounded_box(draw, qx, qy, 55, 26, DARK_BOX, col, 4)
        nw = text_w(draw, name, body_font)
        draw.text((qx + (55 - nw) // 2, qy + 5), name, fill=col, font=body_font)

        # Bit checks
        for hi, bit_pos in enumerate(bits):
            hx = qx + 70 + hi * 50
            is_set = bit_pos in set_bits
            check_col = GREEN if is_set else RED
            draw_rounded_box(draw, hx, qy, 38, 26, DARK_BOX, check_col, 4)
            ctxt = f"[{bit_pos}]"
            ctxt_w = text_w(draw, ctxt, small_font)
            draw.text((hx + (38 - ctxt_w) // 2, qy + 6), ctxt, fill=check_col, font=small_font)

        # Result
        rcol = ORANGE if result else GREEN
        if not result:
            rcol = RED
        rx = qx + 225
        glow = tuple(int(c * (0.7 + 0.3 * pulse)) for c in rcol)
        draw_rounded_box(draw, rx, qy, 100, 26, DARK_BOX, glow, 4)
        rw = text_w(draw, result_txt, small_font)
        draw.text((rx + (100 - rw) // 2, qy + 6), result_txt, fill=rcol, font=small_font)

    # === Bottom: Key properties ===
    bot_y = 355
    bot_h = 180
    draw_rounded_box(draw, 30, bot_y, 740, bot_h, PANEL, BORDER)

    props_lbl = "KEY PROPERTIES"
    props_lbl_w = text_w(draw, props_lbl, header_font)
    draw.text(((W - props_lbl_w) // 2, bot_y + 10), props_lbl, fill=CYAN, font=header_font)

    # Three property columns
    col_w = 220
    col_gap = 20
    total_col_w = 3 * col_w + 2 * col_gap
    col_start = (W - total_col_w) // 2

    props = [
        ("Space Efficient", "m bits instead of", "storing full items", GREEN),
        ("False Positives", "\"Maybe\" can be wrong", "\"No\" is always correct", ORANGE),
        ("No Deletion", "Cannot remove items", "(Counting BFs can)", RED),
    ]

    for i, (hdr, l1, l2, col) in enumerate(props):
        cx = col_start + i * (col_w + col_gap)
        cy = bot_y + 38
        hdr_w = text_w(draw, hdr, header_font)
        draw.text((cx + (col_w - hdr_w) // 2, cy), hdr, fill=col, font=header_font)

        box_y = cy + 25
        draw_rounded_box(draw, cx + 5, box_y, col_w - 10, 50, DARK_BOX, BORDER, 4)
        l1w = text_w(draw, l1, body_font)
        l2w = text_w(draw, l2, body_font)
        draw.text((cx + 5 + (col_w - 10 - l1w) // 2, box_y + 8), l1, fill=WHITE, font=body_font)
        draw.text((cx + 5 + (col_w - 10 - l2w) // 2, box_y + 26), l2, fill=col, font=body_font)

    use = "Used in: Bitcoin SPV nodes, Ethereum logs, caching, spell checkers"
    use_w = text_w(draw, use, small_font)
    draw.text(((W - use_w) // 2, bot_y + bot_h - 28), use, fill=DIM, font=small_font)

    return img

if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save("assets/gifs/core_10_bloom_filters.gif", save_all=True,
                   append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print("Saved assets/gifs/core_10_bloom_filters.gif")
