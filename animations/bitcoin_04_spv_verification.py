"""Bitcoin SPV: Full Node vs Light Client animation."""
from PIL import Image, ImageDraw, ImageFont
import math

W, H, FRAMES, DUR = 800, 550, 36, 90
BG = (13, 17, 23)
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)
CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
YELLOW_BG = (58, 50, 14)
RED = (248, 113, 113)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
PURPLE = (167, 139, 250)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)

def load_font(size, bold=False):
    for p in (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"] if bold else
              ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]):
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()

def load_mono(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(14, True)
body_font = load_font(12)
small_font = load_font(10)
mono_font = load_mono(11)
mono_sm = load_mono(9)

def marching_arrow_h(draw, x0, y, x1, color, frame, w=2):
    dash = 6
    total = abs(x1 - x0)
    dx = 1 if x1 > x0 else -1
    offset = (frame * 3) % (dash * 2)
    d = -offset
    while d < total:
        s = max(0, d)
        e = min(total, d + dash)
        if e > s and int(d / dash) % 2 == 0:
            draw.line([(x0 + dx * s, y), (x0 + dx * e, y)], fill=color, width=w)
        d += dash * 2
    draw.polygon([(x1, y), (x1 - dx * 8, y - 4), (x1 - dx * 8, y + 4)], fill=color)

if __name__ == "__main__":
    frames_list = []
    for f in range(FRAMES):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        t = f / FRAMES
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

        draw.text((W // 2, 20), "Full Node vs SPV Light Client", fill=CYAN, font=title_font, anchor="mt")

        # ---- LEFT: Full Node ----
        fn_x, fn_y = 50, 65
        fn_w, fn_h = 300, 280
        draw.rounded_rectangle((fn_x, fn_y, fn_x + fn_w, fn_y + fn_h), radius=10, fill=PANEL, outline=ORANGE, width=2)
        draw.text((fn_x + fn_w // 2, fn_y + 15), "Full Node", fill=ORANGE, font=header_font, anchor="mt")
        draw.text((fn_x + fn_w // 2, fn_y + 35), "Stores EVERYTHING", fill=DIM, font=small_font, anchor="mt")

        # Stack of blocks
        block_colors = [ORANGE, YELLOW, CYAN, GREEN, PURPLE]
        for i in range(8):
            by = fn_y + 55 + i * 27
            bx = fn_x + 20
            bw = fn_w - 40
            col = block_colors[i % len(block_colors)]
            bg = tuple(int(c * 0.2) for c in col)
            draw.rounded_rectangle((bx, by, bx + bw, by + 23), radius=4, fill=bg, outline=col, width=1)
            draw.text((bx + 8, by + 5), f"Block #{800000 - i}", fill=col, font=mono_sm)
            draw.text((bx + bw - 8, by + 5), f"~1MB", fill=DIM, font=mono_sm, anchor="ra")

        # Size label
        draw.text((fn_x + fn_w // 2, fn_y + fn_h - 15), "~550 GB total", fill=RED, font=header_font, anchor="mt")

        # ---- RIGHT: SPV Node ----
        sp_x = 450
        sp_w, sp_h = 300, 280
        g = int(100 + 155 * pulse)
        draw.rounded_rectangle((sp_x, fn_y, sp_x + sp_w, fn_y + sp_h), radius=10, fill=PANEL, outline=(52, g, 153), width=2)
        draw.text((sp_x + sp_w // 2, fn_y + 15), "SPV Light Client", fill=GREEN, font=header_font, anchor="mt")
        draw.text((sp_x + sp_w // 2, fn_y + 35), "Headers ONLY", fill=DIM, font=small_font, anchor="mt")

        # Thin header strips
        for i in range(8):
            by = fn_y + 55 + i * 27
            bx = sp_x + 60
            bw = sp_w - 120
            col = GREEN
            bg = GREEN_BG
            draw.rounded_rectangle((bx, by, bx + bw, by + 23), radius=4, fill=bg, outline=col, width=1)
            draw.text((bx + 8, by + 5), f"Header #{800000 - i}", fill=GREEN, font=mono_sm)
            draw.text((bx + bw - 8, by + 5), "80B", fill=DIM, font=mono_sm, anchor="ra")

        # Size label
        draw.text((sp_x + sp_w // 2, fn_y + sp_h - 15), "~60 MB total", fill=GREEN, font=header_font, anchor="mt")

        # ---- MIDDLE: Communication ----
        mid_y = 365
        draw.rounded_rectangle((50, mid_y, 750, mid_y + 160), radius=10, fill=DARK_BOX, outline=BORDER)
        draw.text((400, mid_y + 12), "SPV Verification Process", fill=WHITE, font=header_font, anchor="mt")

        # Step 1: Question
        draw.rounded_rectangle((70, mid_y + 38, 250, mid_y + 80), radius=6, fill=GREEN_BG, outline=GREEN)
        draw.text((160, mid_y + 50), "Is Tx X in Block N?", fill=GREEN, font=small_font, anchor="mt")
        draw.text((160, mid_y + 68), "SPV asks full node", fill=DIM, font=small_font, anchor="mt")

        # Arrow
        marching_arrow_h(draw, 252, mid_y + 58, 310, GREEN, f)

        # Step 2: Proof
        draw.rounded_rectangle((312, mid_y + 35, 490, mid_y + 85), radius=6, fill=PURPLE_BG, outline=PURPLE)
        draw.text((401, mid_y + 43), "Merkle Proof", fill=PURPLE, font=small_font, anchor="mt")
        draw.text((401, mid_y + 58), "tx_hash + siblings", fill=WHITE, font=mono_sm, anchor="mt")
        draw.text((401, mid_y + 73), "~500 bytes", fill=DIM, font=small_font, anchor="mt")

        # Arrow
        marching_arrow_h(draw, 492, mid_y + 58, 550, PURPLE, f)

        # Step 3: Verify
        draw.rounded_rectangle((552, mid_y + 38, 730, mid_y + 80), radius=6, fill=CYAN_BG, outline=CYAN)
        draw.text((641, mid_y + 48), "Compute merkle root", fill=CYAN, font=small_font, anchor="mt")
        draw.text((641, mid_y + 66), "Match header? YES", fill=GREEN, font=small_font, anchor="mt")

        # Bottom labels
        draw.text((160, mid_y + 95), "Light client", fill=GREEN, font=small_font, anchor="mt")
        draw.text((401, mid_y + 95), "Network response", fill=PURPLE, font=small_font, anchor="mt")
        draw.text((641, mid_y + 95), "Local verification", fill=CYAN, font=small_font, anchor="mt")

        draw.text((400, mid_y + 120), "Trust: SPV trusts that the longest chain has valid blocks", fill=DIM, font=small_font, anchor="mt")
        draw.text((400, mid_y + 140), "Tradeoff: less security than full node, but runs on phones!", fill=ORANGE, font=small_font, anchor="mt")

        frames_list.append(img)

    frames_list[0].save("assets/gifs/bitcoin_04_spv_verification.gif", save_all=True, append_images=frames_list[1:], duration=DUR, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_04_spv_verification.gif")
