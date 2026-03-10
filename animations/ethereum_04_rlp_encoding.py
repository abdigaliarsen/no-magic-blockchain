"""
RLP Encoding - Variant C: Nested Structure
Generates: assets/gifs/ethereum_04_rlp_encoding.gif
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- Config ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
BG = (13, 17, 23)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
RED = (248, 113, 113)
PURPLE = (167, 139, 250)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)
CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
YELLOW_BG = (58, 50, 14)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)

def load_fonts():
    fonts = {}
    try:
        fonts["title"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
        fonts["header"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        fonts["body"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        fonts["small"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except Exception:
        f = ImageFont.load_default()
        fonts = {"title": f, "header": f, "body": f, "small": f}
    return fonts

FONTS = load_fonts()

def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def draw_rounded_rect(draw, xy, fill, outline, r=8, width=1):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

# The nested structure: ["cat", ["dog", "bird"]]
# RLP encoding:
#   "cat" = 0x83, 'c','a','t'  (3 bytes, prefix 0x80+3)
#   "dog" = 0x83, 'd','o','g'
#   "bird" = 0x84, 'b','i','r','d'  (4 bytes, prefix 0x80+4)
#   inner list ["dog","bird"] = contents 9 bytes, prefix 0xC0+9 = 0xC9
#     = 0xC9, 0x83,'d','o','g', 0x84,'b','i','r','d'  (10 bytes)
#   outer list = contents 4+10 = 14 bytes, prefix 0xC0+14 = 0xCE
#     = 0xCE, 0x83,'c','a','t', 0xC9, 0x83,'d','o','g', 0x84,'b','i','r','d'

FULL_BYTES = [
    ("CE", "outer list prefix", PURPLE, 0),
    ("83", '"cat" prefix', GREEN, 1),
    ("63", "'c'", CYAN, 1),
    ("61", "'a'", CYAN, 1),
    ("74", "'t'", CYAN, 1),
    ("C9", "inner list prefix", ORANGE, 1),
    ("83", '"dog" prefix', GREEN, 2),
    ("64", "'d'", CYAN, 2),
    ("6F", "'o'", CYAN, 2),
    ("67", "'g'", CYAN, 2),
    ("84", '"bird" prefix', GREEN, 2),
    ("62", "'b'", CYAN, 2),
    ("69", "'i'", CYAN, 2),
    ("72", "'r'", CYAN, 2),
    ("64", "'d'", CYAN, 2),
]

# Nesting level colors for box outlines
LEVEL_COLORS = [PURPLE, YELLOW, ORANGE]
LEVEL_BG = [PURPLE_BG, YELLOW_BG, (40, 35, 18)]

def render_frame(frame_idx):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    cycle = frame_idx / max(FRAMES - 1, 1)

    # Title
    title = "RLP Nested Structure"
    tw, th = text_size(draw, title, FONTS["title"])
    draw.text(((W - tw) // 2, 12), title, fill=WHITE, font=FONTS["title"])

    sub = '["cat", ["dog", "bird"]]'
    sw, sh = text_size(draw, sub, FONTS["body"])
    draw.text(((W - sw) // 2, 44), sub, fill=DIM, font=FONTS["body"])

    # --- Top section: Nested box diagram ---
    # Outer list box
    outer_x, outer_y = 50, 75
    outer_w, outer_h = W - 100, 200

    # Scan line sweeps across the nested boxes
    scan_x_frac = cycle  # 0..1 across the outer box

    # Draw outer list box (level 0)
    scan_dist_0 = abs(scan_x_frac - 0.5)
    glow_0 = max(0.0, 1.0 - scan_dist_0 * 3)
    out_border = lerp_color(BORDER, PURPLE, 0.3 + glow_0 * 0.4)
    draw_rounded_rect(draw, (outer_x, outer_y, outer_x + outer_w, outer_y + outer_h),
                      fill=PURPLE_BG, outline=out_border, r=10, width=2)

    # Outer list label
    ol = "List (14 bytes) prefix=0xCE"
    olw, olh = text_size(draw, ol, FONTS["small"])
    draw.text((outer_x + 10, outer_y + 6), ol, fill=PURPLE, font=FONTS["small"])

    # "cat" box (level 1)
    cat_x = outer_x + 20
    cat_y = outer_y + 30
    cat_w = 180
    cat_h = 150

    cat_center = (cat_x + cat_w / 2 - outer_x) / outer_w
    cat_glow = max(0.0, 1.0 - abs(scan_x_frac - cat_center) * 5)
    cat_border = lerp_color(BORDER, GREEN, 0.3 + cat_glow * 0.7)
    draw_rounded_rect(draw, (cat_x, cat_y, cat_x + cat_w, cat_y + cat_h),
                      fill=GREEN_BG, outline=cat_border, r=8)

    cat_label = '"cat" (3 bytes)'
    clw, clh = text_size(draw, cat_label, FONTS["small"])
    draw.text((cat_x + 10, cat_y + 8), cat_label, fill=GREEN, font=FONTS["small"])

    # Show bytes for "cat"
    cat_bytes = [("0x83", "prefix", ORANGE), ("0x63", "c", CYAN), ("0x61", "a", CYAN), ("0x74", "t", CYAN)]
    cb_y = cat_y + 35
    for j, (bval, blbl, bcol) in enumerate(cat_bytes):
        bx = cat_x + 15 + j * 40
        by = cb_y

        dist = abs(scan_x_frac - (bx - outer_x) / outer_w)
        g = max(0.0, 1.0 - dist * 8)
        fc = lerp_color(DIM, bcol, 0.5 + g * 0.5)
        bg_c = lerp_color(DARK_BOX, CYAN_BG if bcol == CYAN else YELLOW_BG, g * 0.3)

        draw_rounded_rect(draw, (bx, by, bx + 34, by + 40), fill=bg_c, outline=lerp_color(BORDER, bcol, g * 0.5))
        bvw, bvh = text_size(draw, bval, FONTS["small"])
        draw.text((bx + (34 - bvw) // 2, by + 5), bval, fill=fc, font=FONTS["small"])
        blw, blh = text_size(draw, blbl, FONTS["small"])
        draw.text((bx + (34 - blw) // 2, by + 24), blbl, fill=DIM, font=FONTS["small"])

    # Decoded string
    dec_cat = '"cat"'
    dcw, dch = text_size(draw, dec_cat, FONTS["header"])
    draw.text((cat_x + (cat_w - dcw) // 2, cat_y + cat_h - 45), dec_cat, fill=GREEN, font=FONTS["header"])

    # Inner list box (level 1, contains level 2)
    inner_x = cat_x + cat_w + 25
    inner_y = outer_y + 30
    inner_w = outer_w - cat_w - 65
    inner_h = 150

    inner_center = (inner_x + inner_w / 2 - outer_x) / outer_w
    inner_glow = max(0.0, 1.0 - abs(scan_x_frac - inner_center) * 3)
    inner_border = lerp_color(BORDER, ORANGE, 0.3 + inner_glow * 0.5)
    draw_rounded_rect(draw, (inner_x, inner_y, inner_x + inner_w, inner_y + inner_h),
                      fill=YELLOW_BG, outline=inner_border, r=8)

    il = "Inner List (9 bytes) prefix=0xC9"
    ilw, ilh = text_size(draw, il, FONTS["small"])
    draw.text((inner_x + 10, inner_y + 6), il, fill=ORANGE, font=FONTS["small"])

    # "dog" sub-box
    dog_x = inner_x + 15
    dog_y = inner_y + 28
    dog_w = (inner_w - 45) // 2
    dog_h = 105

    dog_center = (dog_x + dog_w / 2 - outer_x) / outer_w
    dog_glow = max(0.0, 1.0 - abs(scan_x_frac - dog_center) * 6)
    draw_rounded_rect(draw, (dog_x, dog_y, dog_x + dog_w, dog_y + dog_h),
                      fill=DARK_BOX, outline=lerp_color(BORDER, GREEN, 0.3 + dog_glow * 0.5), r=6)

    dog_label = '"dog" (3B)'
    dlw, dlh = text_size(draw, dog_label, FONTS["small"])
    draw.text((dog_x + (dog_w - dlw) // 2, dog_y + 5), dog_label, fill=GREEN, font=FONTS["small"])

    dog_bytes = [("83", "pfx"), ("64", "d"), ("6F", "o"), ("67", "g")]
    for j, (bv, bl) in enumerate(dog_bytes):
        bx2 = dog_x + 8 + j * (dog_w - 16) // 4
        by2 = dog_y + 28
        dist2 = abs(scan_x_frac - (bx2 - outer_x) / outer_w)
        g2 = max(0.0, 1.0 - dist2 * 10)
        fc2 = lerp_color(DIM, CYAN, 0.4 + g2 * 0.6)
        bvw2, _ = text_size(draw, bv, FONTS["small"])
        draw.text((bx2, by2), bv, fill=fc2, font=FONTS["small"])
        blw2, _ = text_size(draw, bl, FONTS["small"])
        draw.text((bx2, by2 + 15), bl, fill=DIM, font=FONTS["small"])

    # decoded
    dd = '"dog"'
    ddw, _ = text_size(draw, dd, FONTS["body"])
    draw.text((dog_x + (dog_w - ddw) // 2, dog_y + dog_h - 25), dd, fill=GREEN, font=FONTS["body"])

    # "bird" sub-box
    bird_x = dog_x + dog_w + 15
    bird_y = inner_y + 28
    bird_w = dog_w
    bird_h = dog_h

    bird_center = (bird_x + bird_w / 2 - outer_x) / outer_w
    bird_glow = max(0.0, 1.0 - abs(scan_x_frac - bird_center) * 6)
    draw_rounded_rect(draw, (bird_x, bird_y, bird_x + bird_w, bird_y + bird_h),
                      fill=DARK_BOX, outline=lerp_color(BORDER, GREEN, 0.3 + bird_glow * 0.5), r=6)

    bird_label = '"bird" (4B)'
    blw3, _ = text_size(draw, bird_label, FONTS["small"])
    draw.text((bird_x + (bird_w - blw3) // 2, bird_y + 5), bird_label, fill=GREEN, font=FONTS["small"])

    bird_bytes = [("84", "pfx"), ("62", "b"), ("69", "i"), ("72", "r"), ("64", "d")]
    for j, (bv, bl) in enumerate(bird_bytes):
        bx3 = bird_x + 5 + j * (bird_w - 10) // 5
        by3 = bird_y + 28
        dist3 = abs(scan_x_frac - (bx3 - outer_x) / outer_w)
        g3 = max(0.0, 1.0 - dist3 * 10)
        fc3 = lerp_color(DIM, CYAN, 0.4 + g3 * 0.6)
        bvw3, _ = text_size(draw, bv, FONTS["small"])
        draw.text((bx3, by3), bv, fill=fc3, font=FONTS["small"])
        blw4, _ = text_size(draw, bl, FONTS["small"])
        draw.text((bx3, by3 + 15), bl, fill=DIM, font=FONTS["small"])

    bd = '"bird"'
    bdw, _ = text_size(draw, bd, FONTS["body"])
    draw.text((bird_x + (bird_w - bdw) // 2, bird_y + bird_h - 25), bd, fill=GREEN, font=FONTS["body"])

    # --- Bottom section: Full byte stream ---
    stream_y = 300
    draw_rounded_rect(draw, (40, stream_y, W - 40, stream_y + 100), fill=PANEL, outline=BORDER)

    st = "Full Encoded Byte Stream (15 bytes)"
    stw, sth = text_size(draw, st, FONTS["header"])
    draw.text(((W - stw) // 2, stream_y + 8), st, fill=WHITE, font=FONTS["header"])

    # Draw all 15 bytes in a row
    n_bytes = len(FULL_BYTES)
    cell_w = 44
    total_cells_w = n_bytes * cell_w
    cells_x = (W - total_cells_w) // 2
    cells_y = stream_y + 32

    scan_byte = cycle * n_bytes

    for i, (bval, blbl, bcol, level) in enumerate(FULL_BYTES):
        cx = cells_x + i * cell_w
        cy = cells_y

        dist = abs(scan_byte - i)
        glow = max(0.0, 1.0 - dist * 0.6)

        # Background color based on nesting level
        level_bg = [PURPLE_BG, YELLOW_BG, (30, 28, 18)]
        bg_fill = lerp_color(DARK_BOX, level_bg[min(level, 2)], 0.2 + glow * 0.4)
        out_c = lerp_color(BORDER, bcol, 0.3 + glow * 0.7)

        draw_rounded_rect(draw, (cx + 1, cy, cx + cell_w - 1, cy + 50), fill=bg_fill, outline=out_c, r=4)

        # Byte value
        fc = lerp_color(DIM, bcol, 0.5 + glow * 0.5)
        bvw, bvh = text_size(draw, bval, FONTS["body"])
        draw.text((cx + (cell_w - bvw) // 2, cy + 5), bval, fill=fc, font=FONTS["body"])

        # Level indicator (small dots)
        for lv in range(level + 1):
            dot_x = cx + cell_w // 2 - (level) * 5 + lv * 10
            dot_y = cy + 35
            r = 3
            dot_c = LEVEL_COLORS[min(lv, 2)]
            draw.ellipse((dot_x - r, dot_y - r, dot_x + r, dot_y + r),
                         fill=lerp_color(DIM, dot_c, 0.4 + glow * 0.6))

    # --- Nesting legend ---
    legend_y = 420
    draw_rounded_rect(draw, (40, legend_y, W - 40, legend_y + 100), fill=PANEL, outline=BORDER)

    leg_title = "Nesting Levels"
    ltw, lth = text_size(draw, leg_title, FONTS["header"])
    draw.text(((W - ltw) // 2, legend_y + 8), leg_title, fill=WHITE, font=FONTS["header"])

    levels_info = [
        ("Level 0", "Outer list", "0xCE = 0xC0 + 14", PURPLE),
        ("Level 1", '"cat" / inner list', "0x83 / 0xC9", GREEN),
        ("Level 2", '"dog" / "bird"', "0x83 / 0x84", CYAN),
    ]

    for i, (lvl, desc, pfx, col) in enumerate(levels_info):
        lx = 80 + i * 240
        ly = legend_y + 35

        pulse = 0.5 + 0.5 * math.sin(cycle * 2 * math.pi + i * 0.7)
        dot_c = lerp_color(DIM, col, 0.5 + 0.5 * pulse)

        draw.ellipse((lx, ly + 2, lx + 10, ly + 12), fill=dot_c)
        draw.text((lx + 16, ly), lvl, fill=col, font=FONTS["header"])

        draw.text((lx + 16, ly + 20), desc, fill=DIM, font=FONTS["small"])
        draw.text((lx + 16, ly + 36), pfx, fill=DIM, font=FONTS["small"])

    # Footer
    footer = "RLP -- Recursive Length Prefix"
    fw, fh = text_size(draw, footer, FONTS["small"])
    draw.text(((W - fw) // 2, H - 18), footer, fill=DIM, font=FONTS["small"])

    return img

def main():
    frames = [render_frame(i) for i in range(FRAMES)]
    frames[0].save(
        "assets/gifs/ethereum_04_rlp_encoding.gif",
        save_all=True,
        append_images=frames[1:],
        duration=DELAY,
        loop=0,
        optimize=True,
    )
    print("Saved assets/gifs/ethereum_04_rlp_encoding.gif")

if __name__ == "__main__":
    main()
