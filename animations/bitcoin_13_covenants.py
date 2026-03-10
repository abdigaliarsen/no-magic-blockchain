"""Bitcoin Covenants (OP_CTV) animation — vault withdrawal flow."""
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
                except: pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(15, True)
body_font = load_font(13)
small_font = load_font(11)

def draw_rounded_rect(draw, xy, fill, outline, r=8):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)

def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * max(0, min(1, t))) for a, b in zip(c1, c2))

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

def draw_arrow_down(draw, cx, y0, y1, color, frame):
    draw_marching_arrow(draw, cx, y0, cx, y1, color, frame)

frames = []
for f in range(FRAMES):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / FRAMES
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

    # Title
    draw.text((W // 2, 22), "Covenants: OP_CTV Vault", fill=CYAN, font=title_font, anchor="mt")
    draw.text((W // 2, 50), "Restrict where coins can be spent next", fill=DIM, font=body_font, anchor="mt")

    # === VAULT BOX (top center) ===
    vx, vy = 310, 75
    vw, vh = 180, 60
    vault_glow = lerp_color(CYAN_BG, CYAN, pulse * 0.15)
    draw_rounded_rect(draw, (vx, vy, vx + vw, vy + vh), CYAN_BG, CYAN)
    draw.text((vx + vw // 2, vy + 14), "VAULT", fill=CYAN, font=header_font, anchor="mt")
    draw.text((vx + vw // 2, vy + 36), "10.0 BTC", fill=WHITE, font=body_font, anchor="mt")

    # Template hash badge
    draw_rounded_rect(draw, (520, 80, 750, 128), DARK_BOX, BORDER)
    draw.text((635, 90), "Template Hash (CTV)", fill=YELLOW, font=small_font, anchor="mt")
    draw.text((635, 108), "Constrains next tx outputs", fill=DIM, font=small_font, anchor="mt")

    # Arrow vault -> initiate
    draw_arrow_down(draw, 400, 137, 168, YELLOW, f)

    # === INITIATE WITHDRAWAL (middle) ===
    ix, iy = 270, 170
    iw, ih = 260, 55
    draw_rounded_rect(draw, (ix, iy, ix + iw, iy + ih), DARK_BOX, YELLOW)
    draw.text((ix + iw // 2, iy + 12), "Initiate Withdrawal", fill=YELLOW, font=header_font, anchor="mt")
    draw.text((ix + iw // 2, iy + 34), "Starts timelock countdown", fill=DIM, font=small_font, anchor="mt")

    # Timelock bar
    bar_x, bar_y = 270, 240
    bar_w, bar_h = 260, 18
    draw_rounded_rect(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), DARK_BOX, BORDER)
    fill_w = int(bar_w * ((f % 36) / 35))
    if fill_w > 2:
        draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), radius=4, fill=ORANGE)
    draw.text((bar_x + bar_w // 2, bar_y + 3), f"Timelock: {int((f % 36) / 35 * 144)}/144 blocks", fill=WHITE, font=small_font, anchor="mt")

    # Two paths from initiate
    # Left: Cancel -> back to vault
    draw_marching_arrow(draw, 320, 260, 180, 310, RED, f)
    # Right: Complete -> withdraw
    draw_marching_arrow(draw, 480, 260, 620, 310, GREEN, f)

    # === CANCEL BOX (bottom left) ===
    cx, cy = 60, 312
    cw, ch = 240, 65
    draw_rounded_rect(draw, (cx, cy, cx + cw, cy + ch), RED_BG, RED)
    draw.text((cx + cw // 2, cy + 12), "Cancel (Clawback)", fill=RED, font=header_font, anchor="mt")
    draw.text((cx + cw // 2, cy + 34), "Coins return to vault", fill=DIM, font=small_font, anchor="mt")
    draw.text((cx + cw // 2, cy + 50), "Owner's cold key", fill=DIM, font=small_font, anchor="mt")

    # Arrow cancel -> back to vault
    draw_marching_arrow(draw, 130, 312, 350, 137, CYAN, f)

    # === COMPLETE WITHDRAWAL (bottom right) ===
    wx, wy = 530, 312
    ww, wh = 240, 65
    draw_rounded_rect(draw, (wx, wy, wx + ww, wy + wh), GREEN_BG, GREEN)
    draw.text((wx + ww // 2, wy + 12), "Complete Withdrawal", fill=GREEN, font=header_font, anchor="mt")
    draw.text((wx + ww // 2, wy + 34), "After timelock expires", fill=DIM, font=small_font, anchor="mt")
    draw.text((wx + ww // 2, wy + 50), "10.0 BTC to destination", fill=WHITE, font=small_font, anchor="mt")

    # === ATTACKER BLOCKED badge ===
    abx, aby = 60, 402
    abw, abh = 240, 50
    glow_red = lerp_color(RED_BG, RED, pulse * 0.3)
    draw_rounded_rect(draw, (abx, aby, abx + abw, aby + abh), RED_BG, glow_red)
    draw.text((abx + abw // 2, aby + 10), "ATTACKER BLOCKED", fill=RED, font=header_font, anchor="mt")
    draw.text((abx + abw // 2, aby + 30), "Cannot bypass template", fill=DIM, font=small_font, anchor="mt")

    # === Bottom explanation panel ===
    draw_rounded_rect(draw, (40, 468, 760, 535), PANEL, BORDER)
    draw.text((400, 480), "How OP_CTV Covenants Work", fill=WHITE, font=header_font, anchor="mt")
    draw.text((55, 498), "CTV locks coins to a specific next-transaction template (outputs, amounts)", fill=DIM, font=body_font)
    draw.text((55, 516), "Vault pattern: deposit -> initiate (timelock) -> complete OR cancel", fill=DIM, font=body_font)

    # Scan line
    scan_y = int(70 + (t * 400) % 400)
    draw.line([(0, scan_y), (W, scan_y)], fill=(*CYAN[:3], 20), width=1)

    frames.append(img)

if __name__ == "__main__":
    frames[0].save("assets/gifs/bitcoin_13_covenants.gif", save_all=True, append_images=frames[1:], duration=DUR, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_13_covenants.gif")
