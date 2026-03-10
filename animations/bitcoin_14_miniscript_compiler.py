"""Bitcoin Miniscript Compiler animation — policy tree to Bitcoin Script."""
from PIL import Image, ImageDraw, ImageFont
import math, os

W, H, FRAMES, DUR = 800, 550, 36, 90
BG = (13, 17, 23)
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
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)

def load_font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for n in names:
        for p in [f"/usr/share/fonts/truetype/dejavu/{n}", f"/usr/share/fonts/truetype/liberation/{n}", f"/usr/share/fonts/{n}"]:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except (OSError, IOError): pass
    return ImageFont.load_default()

def load_mono(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]:
        try: return ImageFont.truetype(p, size)
        except (OSError, IOError): pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(15, True)
body_font = load_font(13)
small_font = load_font(11)
mono_font = load_mono(11)

def draw_rounded_rect(draw, xy, fill, outline, r=8):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)

def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * max(0, min(1, t))) for a, b in zip(c1, c2))

def draw_marching_arrow(draw, x0, y0, x1, y1, color, frame, thickness=2):
    draw.line([(x0, y0), (x1, y1)], fill=color, width=thickness)
    dash_len = 8
    total = math.hypot(x1 - x0, y1 - y0)
    if total == 0: return
    dx, dy = (x1 - x0) / total, (y1 - y0) / total
    offset = (frame * 3) % (dash_len * 2)
    d = -offset
    while d < total:
        s = max(0, d)
        e = min(total, d + dash_len)
        if e > s:
            draw.line([(x0 + dx * s, y0 + dy * s), (x0 + dx * e, y0 + dy * e)], fill=WHITE, width=thickness)
        d += dash_len * 2
    draw.polygon([(x1, y1), (x1 - dx * 10 - dy * 5, y1 - dy * 10 + dx * 5),
                  (x1 - dx * 10 + dy * 5, y1 - dy * 10 - dx * 5)], fill=color)

# Tree node positions for the AST (left side)
# Root: or()
# Left child: and(pk(A), pk(B))
# Right child: and(pk(C), after(144))
TREE = {
    "or":     (150, 115),
    "and_L":  (85, 195),
    "and_R":  (215, 195),
    "pk_A":   (55, 275),
    "pk_B":   (115, 275),
    "pk_C":   (185, 275),
    "after":  (245, 275),
}

SCRIPT_LINES = [
    ("OP_IF", CYAN),
    ("  <pk_A>", GREEN),
    ("  OP_CHECKSIGVERIFY", CYAN),
    ("  <pk_B>", GREEN),
    ("  OP_CHECKSIG", CYAN),
    ("OP_ELSE", YELLOW),
    ("  <pk_C>", GREEN),
    ("  OP_CHECKSIGVERIFY", CYAN),
    ("  144 OP_CHECKSEQ..", ORANGE),
    ("OP_ENDIF", YELLOW),
]

frames = []
for f in range(FRAMES):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / FRAMES
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

    # Title
    draw.text((W // 2, 20), "Miniscript Compiler", fill=CYAN, font=title_font, anchor="mt")
    draw.text((W // 2, 48), "Policy tree -> optimized Bitcoin Script", fill=DIM, font=body_font, anchor="mt")

    # --- LEFT SIDE: Policy AST ---
    draw.text((150, 72), "Policy (AST)", fill=YELLOW, font=header_font, anchor="mt")

    # Draw tree edges
    edges = [
        ("or", "and_L"), ("or", "and_R"),
        ("and_L", "pk_A"), ("and_L", "pk_B"),
        ("and_R", "pk_C"), ("and_R", "after"),
    ]
    for parent, child in edges:
        px, py = TREE[parent]
        cx, cy = TREE[child]
        draw.line([(px, py + 16), (cx, cy - 16)], fill=BORDER, width=2)

    # Draw tree nodes
    node_data = [
        ("or", "or()", YELLOW, DARK_BOX),
        ("and_L", "and()", CYAN, CYAN_BG),
        ("and_R", "and()", CYAN, CYAN_BG),
        ("pk_A", "pk(A)", GREEN, GREEN_BG),
        ("pk_B", "pk(B)", GREEN, GREEN_BG),
        ("pk_C", "pk(C)", GREEN, GREEN_BG),
        ("after", "after", ORANGE, DARK_BOX),
    ]
    for key, label, color, bg in node_data:
        nx, ny = TREE[key]
        nw, nh = 56, 28
        draw_rounded_rect(draw, (nx - nw // 2, ny - nh // 2, nx + nw // 2, ny + nh // 2), bg, color, r=6)
        draw.text((nx, ny), label, fill=color, font=small_font, anchor="mm")

    # after(144) extra label
    draw.text((245, 295), "(144 blks)", fill=DIM, font=small_font, anchor="mt")

    # --- CENTER: Compilation arrows ---
    arrow_x0, arrow_x1 = 310, 420
    arrow_y = 190
    for i in range(3):
        ay = arrow_y + i * 40
        draw_marching_arrow(draw, arrow_x0, ay, arrow_x1, ay, PURPLE, f)

    draw_rounded_rect(draw, (335, 155, 395, 175), PURPLE_BG, PURPLE, r=6)
    draw.text((365, 165), "compile", fill=PURPLE, font=small_font, anchor="mm")

    # --- RIGHT SIDE: Bitcoin Script ---
    draw.text((600, 72), "Bitcoin Script", fill=GREEN, font=header_font, anchor="mt")
    sx, sy = 445, 90
    sw, sh = 320, 220
    draw_rounded_rect(draw, (sx, sy, sx + sw, sy + sh), DARK_BOX, BORDER)

    for i, (line, color) in enumerate(SCRIPT_LINES):
        ly = sy + 14 + i * 20
        # Highlight current line with pulse
        highlight_line = (f * len(SCRIPT_LINES) // FRAMES) % len(SCRIPT_LINES)
        if i == highlight_line:
            draw.rectangle((sx + 4, ly - 2, sx + sw - 4, ly + 16), fill=lerp_color(DARK_BOX, color, 0.15))
        draw.text((sx + 14, ly), line, fill=color, font=mono_font)

    # --- BOTTOM: Witness cost comparison ---
    draw_rounded_rect(draw, (40, 340, 760, 530), PANEL, BORDER)
    draw.text((400, 355), "Witness Cost Comparison", fill=WHITE, font=header_font, anchor="mt")

    # Path A: 2-of-2 multisig
    draw.text((80, 382), "Path A: pk(A) + pk(B)", fill=GREEN, font=body_font)
    bar_a_w = 180
    draw_rounded_rect(draw, (80, 400, 80 + bar_a_w, 418), GREEN_BG, GREEN, r=4)
    glow_a = lerp_color(GREEN_BG, GREEN, pulse * 0.4)
    draw.rounded_rectangle((80, 400, 80 + int(bar_a_w * 0.65), 418), radius=4, fill=glow_a)
    draw.text((80 + bar_a_w + 10, 403), "~208 vbytes", fill=DIM, font=small_font)

    # Path B: pk(C) + timelock
    draw.text((80, 432), "Path B: pk(C) + after(144)", fill=ORANGE, font=body_font)
    bar_b_w = 180
    draw_rounded_rect(draw, (80, 450, 80 + bar_b_w, 468), DARK_BOX, ORANGE, r=4)
    glow_b = lerp_color(DARK_BOX, ORANGE, pulse * 0.4)
    draw.rounded_rectangle((80, 450, 80 + int(bar_b_w * 0.45), 468), radius=4, fill=glow_b)
    draw.text((80 + bar_b_w + 10, 453), "~152 vbytes", fill=DIM, font=small_font)

    # Benefits
    draw.text((450, 382), "Miniscript Benefits:", fill=PURPLE, font=header_font)
    benefits = [
        ("Automatic optimization", GREEN),
        ("Composable policies", CYAN),
        ("Provable spending analysis", YELLOW),
        ("Compatible with all wallets", DIM),
    ]
    for i, (txt, col) in enumerate(benefits):
        draw.text((465, 402 + i * 20), "-", fill=col, font=small_font)
        draw.text((478, 402 + i * 20), txt, fill=col, font=small_font)

    # Bottom label
    draw.text((400, 510), "or( and(pk(A),pk(B)), and(pk(C),after(144)) )", fill=DIM, font=small_font, anchor="mt")

    # Scan line
    scan_y = int(70 + (t * 460) % 460)
    draw.line([(0, scan_y), (W, scan_y)], fill=(*CYAN[:3], 20), width=1)

    frames.append(img)

if __name__ == "__main__":
    frames[0].save("assets/gifs/bitcoin_14_miniscript_compiler.gif", save_all=True, append_images=frames[1:], duration=DUR, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_14_miniscript_compiler.gif")
