"""CORE11-A: Verifiable Random Functions — deterministic, provable randomness."""
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
                except (OSError, IOError): pass
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

def marching_vline(draw, x, y1, y2, color, frame, idx=0):
    dash_len = 6
    offset = (frame * 2 + idx * 3) % (dash_len * 2)
    direction = 1 if y2 > y1 else -1
    length = abs(y2 - y1)
    pos = offset % (dash_len * 2)
    while pos < length:
        sy = y1 + direction * pos
        ey = y1 + direction * min(pos + dash_len, length)
        draw.line([(x, sy), (x, ey)], fill=color, width=2)
        pos += dash_len * 2
    if direction > 0:
        draw.polygon([(x, y2), (x - 5, y2 - 8), (x + 5, y2 - 8)], fill=color)
    else:
        draw.polygon([(x, y2), (x - 5, y2 + 8), (x + 5, y2 + 8)], fill=color)

def draw_color_bar(draw, x, y, w, h, hash_seed, color):
    """Draw a small color bar representing a hash output."""
    n_cells = 8
    cell_w = w // n_cells
    for i in range(n_cells):
        # Deterministic pseudo-color from seed
        val = ((hash_seed * 31 + i * 17) % 256)
        r = int(color[0] * val / 255)
        g = int(color[1] * val / 255)
        b = int(color[2] * val / 255)
        cx = x + i * cell_w
        draw.rectangle([cx, y, cx + cell_w - 1, y + h], fill=(r, g, b))

def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    pulse = 0.5 + 0.5 * math.sin(f * 2 * math.pi / FRAMES)

    # Title
    title = "Verifiable Random Functions"
    tw = text_w(draw, title, title_font)
    draw.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)
    subtitle = "Deterministic randomness with cryptographic proof"
    sw = text_w(draw, subtitle, small_font)
    draw.text(((W - sw) // 2, 44), subtitle, fill=DIM, font=small_font)

    # === Main VRF pipeline (top section) ===
    pipe_y = 72
    pipe_h = 155
    draw_rounded_box(draw, 30, pipe_y, 740, pipe_h, PANEL, BORDER)

    pipe_lbl = "VRF EVALUATION"
    pipe_lbl_w = text_w(draw, pipe_lbl, header_font)
    draw.text(((W - pipe_lbl_w) // 2, pipe_y + 8), pipe_lbl, fill=ORANGE, font=header_font)

    # Input box (left)
    in_x, in_y = 60, pipe_y + 40
    in_w, in_h = 110, 55
    draw_rounded_box(draw, in_x, in_y, in_w, in_h, DARK_BOX, CYAN, 4)
    draw.text((in_x + 8, in_y + 5), "Input", fill=CYAN, font=header_font)
    draw.text((in_x + 8, in_y + 25), "\"block_42\"", fill=WHITE, font=small_font)

    # Secret key box (below input, feeds into VRF)
    sk_x, sk_y = 60, pipe_y + 108
    sk_w, sk_h = 110, 28
    draw_rounded_box(draw, sk_x, sk_y, sk_w, sk_h, RED_BG, RED, 4)
    skt = "Secret Key (sk)"
    skt_w = text_w(draw, skt, small_font)
    draw.text((sk_x + (sk_w - skt_w) // 2, sk_y + 6), skt, fill=RED, font=small_font)

    # VRF box (center)
    vrf_x, vrf_y = 260, pipe_y + 40
    vrf_w, vrf_h = 120, 55
    glow_p = tuple(int(c * (0.7 + 0.3 * pulse)) for c in PURPLE)
    draw_rounded_box(draw, vrf_x, vrf_y, vrf_w, vrf_h, PURPLE_BG, glow_p, 6)
    vrf_lbl = "VRF(sk, x)"
    vrf_lbl_w = text_w(draw, vrf_lbl, body_font)
    draw.text((vrf_x + (vrf_w - vrf_lbl_w) // 2, vrf_y + 18), vrf_lbl, fill=PURPLE, font=body_font)

    # Arrows: input → VRF
    marching_hline(draw, in_x + in_w + 5, vrf_x - 5, in_y + in_h // 2, CYAN, f, 0)
    # Arrow: sk → VRF
    marching_hline(draw, sk_x + sk_w + 5, vrf_x - 5, sk_y + sk_h // 2, RED, f, 1)

    # Output box (right top)
    out_x, out_y = 480, pipe_y + 32
    out_w, out_h = 130, 40
    draw_rounded_box(draw, out_x, out_y, out_w, out_h, DARK_BOX, GREEN, 4)
    draw.text((out_x + 8, out_y + 3), "Output", fill=GREEN, font=small_font)
    # Color bar for hash
    draw_color_bar(draw, out_x + 8, out_y + 20, out_w - 16, 12, 42, GREEN)

    # Proof box (right bottom)
    pr_x, pr_y = 480, pipe_y + 82
    pr_w, pr_h = 130, 40
    draw_rounded_box(draw, pr_x, pr_y, pr_w, pr_h, DARK_BOX, YELLOW, 4)
    draw.text((pr_x + 8, pr_y + 3), "Proof", fill=YELLOW, font=small_font)
    draw_color_bar(draw, pr_x + 8, pr_y + 20, pr_w - 16, 12, 97, YELLOW)

    # Arrows: VRF → outputs
    marching_hline(draw, vrf_x + vrf_w + 5, out_x - 5, out_y + out_h // 2, GREEN, f, 2)
    marching_hline(draw, vrf_x + vrf_w + 5, pr_x - 5, pr_y + pr_h // 2, YELLOW, f, 3)

    # Verification box (far right)
    ver_x, ver_y = 650, pipe_y + 55
    ver_w, ver_h = 100, 50
    glow_g = tuple(int(c * (0.7 + 0.3 * pulse)) for c in GREEN)
    draw_rounded_box(draw, ver_x, ver_y, ver_w, ver_h, GREEN_BG, glow_g, 4)
    draw.text((ver_x + 8, ver_y + 5), "Verify", fill=GREEN, font=header_font)
    draw.text((ver_x + 8, ver_y + 25), "pk + proof", fill=WHITE, font=small_font)

    # Arrow to verify
    mid_out_y = (out_y + out_h // 2 + pr_y + pr_h // 2) // 2
    marching_hline(draw, out_x + out_w + 5, ver_x - 5, mid_out_y, GREEN, f, 4)

    # === Properties section (3 panels) ===
    prop_y = 240
    panel_w = 230
    panel_h = 140
    panel_gap = 20
    total_pw = 3 * panel_w + 2 * panel_gap
    panel_start_x = (W - total_pw) // 2

    properties = [
        ("DETERMINISTIC", CYAN, CYAN_BG,
         "Same input", "always gives", "same output",
         ["\"block_42\" -> a3f2...", "\"block_42\" -> a3f2...", "Always identical!"]),
        ("UNPREDICTABLE", ORANGE, YELLOW_BG,
         "Without sk,", "output looks", "random",
         ["\"block_42\" -> a3f2...", "\"block_43\" -> 7b1e...", "No pattern!"]),
        ("VERIFIABLE", GREEN, GREEN_BG,
         "Anyone with pk", "can verify the", "output is correct",
         ["verify(pk, x, out, proof)", "-> True", "No sk needed!"]),
    ]

    for i, (hdr, col, bg, l1, l2, l3, examples) in enumerate(properties):
        px = panel_start_x + i * (panel_w + panel_gap)
        draw_rounded_box(draw, px, prop_y, panel_w, panel_h, PANEL, col)

        hdr_w = text_w(draw, hdr, header_font)
        draw.text((px + (panel_w - hdr_w) // 2, prop_y + 8), hdr, fill=col, font=header_font)

        # Description
        for j, line in enumerate([l1, l2, l3]):
            lw = text_w(draw, line, body_font)
            draw.text((px + (panel_w - lw) // 2, prop_y + 30 + j * 16), line, fill=WHITE, font=body_font)

        # Example lines in a dark box
        ex_y = prop_y + 82
        draw_rounded_box(draw, px + 8, ex_y, panel_w - 16, 48, DARK_BOX, BORDER, 4)
        # Cycle through examples
        ex_idx = (f * len(examples) // FRAMES) % len(examples)
        for k, ex in enumerate(examples):
            ecol = col if k == ex_idx else DIM
            ew = text_w(draw, ex, small_font)
            draw.text((px + (panel_w - ew) // 2, ex_y + 5 + k * 14), ex, fill=ecol, font=small_font)

    # === Bottom: Use cases ===
    bot_y = 400
    bot_h = 135
    draw_rounded_box(draw, 30, bot_y, 740, bot_h, PANEL, BORDER)

    uc_lbl = "BLOCKCHAIN APPLICATIONS"
    uc_lbl_w = text_w(draw, uc_lbl, header_font)
    draw.text(((W - uc_lbl_w) // 2, bot_y + 10), uc_lbl, fill=CYAN, font=header_font)

    use_cases = [
        ("Leader Selection", "Pick next block", "proposer fairly", PURPLE),
        ("Randomness Beacon", "On-chain random", "number generation", GREEN),
        ("Lottery / Gaming", "Provably fair", "random outcomes", ORANGE),
    ]

    uc_w = 220
    uc_gap = 20
    total_uc = 3 * uc_w + 2 * uc_gap
    uc_start = (W - total_uc) // 2

    for i, (hdr, l1, l2, col) in enumerate(use_cases):
        ux = uc_start + i * (uc_w + uc_gap)
        uy = bot_y + 35

        hdr_w = text_w(draw, hdr, header_font)
        draw.text((ux + (uc_w - hdr_w) // 2, uy), hdr, fill=col, font=header_font)

        draw_rounded_box(draw, ux + 10, uy + 22, uc_w - 20, 45, DARK_BOX, BORDER, 4)
        l1w = text_w(draw, l1, body_font)
        l2w = text_w(draw, l2, body_font)
        draw.text((ux + 10 + (uc_w - 20 - l1w) // 2, uy + 28), l1, fill=WHITE, font=body_font)
        draw.text((ux + 10 + (uc_w - 20 - l2w) // 2, uy + 46), l2, fill=col, font=body_font)

    key = "VRF = pseudorandom function + non-interactive proof of correctness"
    key_w = text_w(draw, key, body_font)
    draw.text(((W - key_w) // 2, bot_y + bot_h - 28), key, fill=YELLOW, font=body_font)

    return img

if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save("assets/gifs/core_11_verifiable_random_functions.gif", save_all=True,
                   append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print("Saved assets/gifs/core_11_verifiable_random_functions.gif")
