"""Schnorr Signatures & MuSig animation."""
from PIL import Image, ImageDraw, ImageFont
import math, os

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
PURPLE = (167, 139, 250)
PURPLE_BG = (35, 28, 58)
RED = (248, 113, 113)
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
mono_font = load_mono(12)

def draw_rounded_rect(draw, xy, fill, outline, r=8):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)

def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

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

if __name__ == "__main__":
    frames = []
    signers = [("Signer A", "sk_a", CYAN, CYAN_BG, 100),
               ("Signer B", "sk_b", GREEN, GREEN_BG, 185),
               ("Signer C", "sk_c", PURPLE, PURPLE_BG, 270)]

    for f in range(FRAMES):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        t = f / FRAMES
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

        # Title
        draw.text((W // 2, 22), "Schnorr Signatures: MuSig", fill=CYAN, font=title_font, anchor="mt")
        draw.text((W // 2, 52), "n signers produce 1 compact aggregated signature", fill=DIM, font=body_font, anchor="mt")

        # Left: 3 signer boxes
        for name, sk, col, bg, y in signers:
            glow_out = lerp_color(BORDER, col, pulse * 0.3)
            draw_rounded_rect(draw, (30, y, 190, y + 65), bg, glow_out)
            draw.text((110, y + 14), name, fill=col, font=header_font, anchor="mt")
            draw.text((110, y + 38), sk, fill=DIM, font=mono_font, anchor="mt")

        # Center: aggregated signature box
        agg_x, agg_y = 330, 155
        agg_w, agg_h = 160, 80
        glow_agg = lerp_color(BORDER, YELLOW, pulse * 0.4)
        draw_rounded_rect(draw, (agg_x, agg_y, agg_x + agg_w, agg_y + agg_h), DARK_BOX, glow_agg)
        draw.text((agg_x + agg_w // 2, agg_y + 18), "MuSig", fill=YELLOW, font=header_font, anchor="mt")
        draw.text((agg_x + agg_w // 2, agg_y + 42), "sig_agg", fill=WHITE, font=mono_font, anchor="mt")
        draw.text((agg_x + agg_w // 2, agg_y + 62), "64 bytes", fill=DIM, font=small_font, anchor="mt")

        # Arrows: each signer -> aggregated
        for _, _, col, _, y in signers:
            draw_marching_arrow(draw, 192, y + 32, agg_x - 2, agg_y + 40, col, f)

        # Right side: comparison panel
        cmp_x = 540
        # ECDSA multisig
        draw_rounded_rect(draw, (cmp_x, 95, 770, 210), RED_BG, RED)
        draw.text((cmp_x + 115, 108), "ECDSA 3-of-3", fill=RED, font=header_font, anchor="mt")
        for i in range(3):
            bx = cmp_x + 15 + i * 72
            draw_rounded_rect(draw, (bx, 130, bx + 65, 165), DARK_BOX, DIM)
            draw.text((bx + 32, 142), f"sig_{i+1}", fill=DIM, font=small_font, anchor="mt")
        draw.text((cmp_x + 115, 180), "3 x 72 = 216 bytes", fill=RED, font=mono_font, anchor="mt")

        # Schnorr MuSig
        draw_rounded_rect(draw, (cmp_x, 230, 770, 335), GREEN_BG, GREEN)
        draw.text((cmp_x + 115, 243), "Schnorr MuSig", fill=GREEN, font=header_font, anchor="mt")
        draw_rounded_rect(draw, (cmp_x + 40, 265, cmp_x + 190, 300), DARK_BOX, GREEN)
        draw.text((cmp_x + 115, 277), "sig_agg", fill=WHITE, font=mono_font, anchor="mt")
        draw.text((cmp_x + 115, 315), "1 x 64 = 64 bytes", fill=GREEN, font=mono_font, anchor="mt")

        # Bottom: savings panel
        draw_rounded_rect(draw, (50, 370, 750, 460), PANEL, BORDER)
        draw.text((400, 388), "Bandwidth Savings", fill=WHITE, font=header_font, anchor="mt")

        # Bar chart comparison
        bar_y = 410
        # ECDSA bar
        ecdsa_w = 280
        draw_rounded_rect(draw, (130, bar_y, 130 + ecdsa_w, bar_y + 18), RED_BG, RED, r=4)
        draw.text((125, bar_y + 5), "ECDSA", fill=RED, font=small_font, anchor="rm")
        draw.text((130 + ecdsa_w + 8, bar_y + 5), "216 B", fill=DIM, font=small_font, anchor="lm")

        # Schnorr bar
        schnorr_w = int(280 * 64 / 216)
        draw_rounded_rect(draw, (130, bar_y + 26, 130 + schnorr_w, bar_y + 44), GREEN_BG, GREEN, r=4)
        draw.text((125, bar_y + 31), "Schnorr", fill=GREEN, font=small_font, anchor="rm")
        draw.text((130 + schnorr_w + 8, bar_y + 31), "64 B", fill=DIM, font=small_font, anchor="lm")

        # Savings percentage
        savings_col = lerp_color(GREEN, WHITE, pulse * 0.3)
        draw.text((620, bar_y + 18), "-70% size", fill=savings_col, font=header_font, anchor="mm")

        # Bottom info
        draw.text((400, 480), "Key: all signers aggregate nonces and partial sigs off-chain", fill=DIM, font=small_font, anchor="mt")

        # Scanning highlight
        scan_x = int(30 + (t * 740) % 740)
        draw.line([(scan_x, 80), (scan_x, 350)], fill=(*CYAN[:3],), width=1)

        # Footer
        draw.text((W // 2, H - 15), "Schnorr: linear, provably secure, aggregatable", fill=DIM, font=small_font, anchor="mt")

        frames.append(img)

    frames[0].save("assets/gifs/bitcoin_09_schnorr_signatures.gif", save_all=True,
                   append_images=frames[1:], duration=DUR, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_09_schnorr_signatures.gif")
