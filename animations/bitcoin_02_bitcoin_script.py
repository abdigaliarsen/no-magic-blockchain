"""Bitcoin Script Lock and Unlock animation."""
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
RED_BG = (50, 20, 20)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
PURPLE = (167, 139, 250)
PURPLE_BG = (35, 28, 58)

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

def draw_marching_arrow(draw, x0, y0, x1, y1, color, frame, thickness=2):
    draw.line([(x0, y0), (x1, y1)], fill=color, width=thickness)
    dash_len = 8
    total = math.hypot(x1 - x0, y1 - y0)
    if total == 0:
        return
    dx, dy = (x1 - x0) / total, (y1 - y0) / total
    offset = (frame * 3) % (dash_len * 2)
    d = -offset
    while d < total:
        s = max(0, d)
        e = min(total, d + dash_len)
        if e > s:
            sx, sy = x0 + dx * s, y0 + dy * s
            ex, ey = x0 + dx * e, y0 + dy * e
            draw.line([(sx, sy), (ex, ey)], fill=WHITE, width=thickness)
        d += dash_len * 2
    ax, ay = x1, y1
    draw.polygon([(ax, ay), (ax - dx * 10 - dy * 5, ay - dy * 10 + dx * 5),
                  (ax - dx * 10 + dy * 5, ay - dy * 10 - dx * 5)], fill=color)

frames = []
for f in range(FRAMES):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / FRAMES
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

    draw.text((W // 2, 25), "Script: Lock and Unlock", fill=CYAN, font=title_font, anchor="mt")
    draw.text((W // 2, 55), "Two scripts combine to authorize spending", fill=DIM, font=body_font, anchor="mt")

    # Left: Locking Script (scriptPubKey) - Lock
    lock_x, lock_y = 50, 100
    lock_w, lock_h = 280, 200
    red_glow = int(180 + 75 * pulse)
    draw.rounded_rectangle((lock_x, lock_y, lock_x + lock_w, lock_y + lock_h),
                           radius=10, fill=RED_BG, outline=(red_glow, 80, 80), width=2)

    # Lock icon (simple padlock shape)
    lx, ly = lock_x + 140, lock_y + 45
    draw.arc((lx - 12, ly - 15, lx + 12, ly + 5), 0, 360, fill=RED, width=3)
    draw.rounded_rectangle((lx - 16, ly + 2, lx + 16, ly + 22), radius=3, fill=RED, outline=RED)

    draw.text((lock_x + 140, ly + 38), "Locking Script", fill=RED, font=header_font, anchor="mt")
    draw.text((lock_x + 140, ly + 58), "(scriptPubKey)", fill=DIM, font=small_font, anchor="mt")

    # Locking script contents
    lock_ops = ["OP_DUP", "OP_HASH160", "<pubKeyHash>", "OP_EQUALVERIFY", "OP_CHECKSIG"]
    for i, op in enumerate(lock_ops):
        y = lock_y + 110 + i * 18
        col = ORANGE if op.startswith("<") else DIM
        draw.text((lock_x + 20, y), op, fill=col, font=mono_font)

    # Right: Unlocking Script (scriptSig) - Key
    key_x, key_y = 470, 100
    key_w, key_h = 280, 200
    grn_glow = int(100 + 155 * pulse)
    draw.rounded_rectangle((key_x, key_y, key_x + key_w, key_y + key_h),
                           radius=10, fill=GREEN_BG, outline=(52, grn_glow, 153), width=2)

    # Key icon (simple key shape)
    kx, ky = key_x + 140, key_y + 45
    draw.ellipse((kx - 10, ky - 10, kx + 10, ky + 10), outline=GREEN, width=2)
    draw.line([(kx + 10, ky), (kx + 30, ky)], fill=GREEN, width=2)
    draw.line([(kx + 25, ky), (kx + 25, ky + 8)], fill=GREEN, width=2)
    draw.line([(kx + 30, ky), (kx + 30, ky + 8)], fill=GREEN, width=2)

    draw.text((key_x + 140, ky + 20), "Unlocking Script", fill=GREEN, font=header_font, anchor="mt")
    draw.text((key_x + 140, ky + 40), "(scriptSig)", fill=DIM, font=small_font, anchor="mt")

    # Unlocking script contents
    unlock_ops = ["<signature>", "<publicKey>"]
    for i, op in enumerate(unlock_ops):
        y = key_y + 110 + i * 18
        draw.text((key_x + 20, y), op, fill=CYAN, font=mono_font)

    draw.text((key_x + 140, key_y + 165), "Provided by spender", fill=DIM, font=small_font, anchor="mt")

    # Center: Combine arrows
    center_x = W // 2
    draw_marching_arrow(draw, lock_x + lock_w + 5, 200, center_x - 35, 350, RED, f)
    draw_marching_arrow(draw, key_x - 5, 200, center_x + 35, 350, GREEN, f)

    draw.text((center_x, 330), "+", fill=WHITE, font=title_font, anchor="mm")

    # Execution box
    exec_y = 360
    draw.rounded_rectangle((center_x - 150, exec_y, center_x + 150, exec_y + 60),
                           radius=10, fill=DARK_BOX, outline=YELLOW, width=2)
    draw.text((center_x, exec_y + 15), "Combined Script Execution", fill=YELLOW, font=header_font, anchor="mt")
    draw.text((center_x, exec_y + 38), "scriptSig + scriptPubKey", fill=DIM, font=small_font, anchor="mt")

    # Arrow down to result
    draw_marching_arrow(draw, center_x, exec_y + 62, center_x, exec_y + 100, YELLOW, f)

    # Result box
    res_y = exec_y + 105
    result_glow = int(100 + 155 * pulse)
    draw.rounded_rectangle((center_x - 120, res_y, center_x + 120, res_y + 55),
                           radius=10, fill=GREEN_BG, outline=(52, result_glow, 153), width=2)
    draw.text((center_x, res_y + 15), "Result: TRUE", fill=GREEN, font=header_font, anchor="mt")
    draw.text((center_x, res_y + 38), "Spend authorized!", fill=WHITE, font=small_font, anchor="mt")

    # Bottom explanation
    draw.text((W // 2, H - 30), "Lock defines the condition  |  Key provides the proof  |  VM verifies both", fill=DIM, font=small_font, anchor="mt")

    frames.append(img)

frames[0].save("assets/gifs/bitcoin_02_bitcoin_script.gif", save_all=True, append_images=frames[1:], duration=DUR, loop=0)
print("Saved assets/gifs/bitcoin_02_bitcoin_script.gif")
