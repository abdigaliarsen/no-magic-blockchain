"""Bitcoin UTXO Transaction Chain animation."""
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
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
RED = (248, 113, 113)
YELLOW_BG = (58, 50, 14)

def load_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()

def load_mono(size):
    paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(14, True)
body_font = load_font(12)
small_font = load_font(10)
mono_font = load_mono(12)

def draw_rounded_rect(draw, xy, fill, outline, r=8):
    x0, y0, x1, y1 = xy
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
    # arrowhead
    ax, ay = x1, y1
    draw.polygon([(ax, ay), (ax - dx * 10 - dy * 5, ay - dy * 10 + dx * 5),
                  (ax - dx * 10 + dy * 5, ay - dy * 10 - dx * 5)], fill=color)

if __name__ == "__main__":
    frames = []
    for f in range(FRAMES):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        t = f / FRAMES
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

        # Title
        draw.text((W // 2, 25), "UTXO: Transaction Chain", fill=CYAN, font=title_font, anchor="mt")
        draw.text((W // 2, 55), "Inputs are consumed, outputs are created", fill=DIM, font=body_font, anchor="mt")

        # Input UTXOs (left side)
        inputs = [("UTXO A", "0.5 BTC", 120), ("UTXO B", "1.0 BTC", 210)]
        for label, amt, y in inputs:
            glow = lerp_color(CYAN_BG, CYAN, pulse * 0.3)
            draw_rounded_rect(draw, (50, y, 220, y + 70), CYAN_BG, CYAN)
            draw.text((135, y + 15), label, fill=CYAN, font=header_font, anchor="mt")
            draw.text((135, y + 42), amt, fill=WHITE, font=mono_font, anchor="mt")

        # Transaction box (center)
        tx_y = 140
        draw_rounded_rect(draw, (300, tx_y, 500, tx_y + 160), DARK_BOX, YELLOW)
        draw.text((400, tx_y + 15), "Transaction", fill=YELLOW, font=header_font, anchor="mt")
        draw.text((400, tx_y + 45), "Fee: 0.01 BTC", fill=ORANGE, font=mono_font, anchor="mt")
        draw.text((400, tx_y + 70), "Total In:  1.50", fill=DIM, font=small_font, anchor="mt")
        draw.text((400, tx_y + 90), "Total Out: 1.49", fill=DIM, font=small_font, anchor="mt")
        draw.text((400, tx_y + 115), "Miner gets fee", fill=DIM, font=small_font, anchor="mt")

        # Output UTXOs (right side)
        outputs = [("Payment", "1.19 BTC", 120, GREEN, GREEN_BG), ("Change", "0.30 BTC", 210, YELLOW, YELLOW_BG)]
        for label, amt, y, col, bg in outputs:
            draw_rounded_rect(draw, (580, y, 750, y + 70), bg, col)
            draw.text((665, y + 15), label, fill=col, font=header_font, anchor="mt")
            draw.text((665, y + 42), amt, fill=WHITE, font=mono_font, anchor="mt")

        # Arrows: inputs -> tx
        draw_marching_arrow(draw, 222, 155, 298, 195, CYAN, f)
        draw_marching_arrow(draw, 222, 245, 298, 235, CYAN, f)

        # Arrows: tx -> outputs
        draw_marching_arrow(draw, 502, 195, 578, 155, GREEN, f)
        draw_marching_arrow(draw, 502, 235, 578, 245, YELLOW, f)

        # Labels
        draw.text((260, 160), "IN", fill=CYAN, font=small_font, anchor="mt")
        draw.text((260, 240), "IN", fill=CYAN, font=small_font, anchor="mt")
        draw.text((540, 150), "OUT", fill=GREEN, font=small_font, anchor="mt")
        draw.text((540, 240), "OUT", fill=YELLOW, font=small_font, anchor="mt")

        # Bottom explanation
        draw_rounded_rect(draw, (50, 340, 750, 440), PANEL, BORDER)
        draw.text((400, 360), "How UTXO Transactions Work", fill=WHITE, font=header_font, anchor="mt")
        draw.text((70, 385), "Inputs (0.5 + 1.0 = 1.5 BTC) must fully cover outputs + fee", fill=DIM, font=body_font)
        draw.text((70, 405), "Payment: 1.19 BTC to recipient  |  Change: 0.30 BTC back to sender", fill=DIM, font=body_font)
        draw.text((70, 425), "Miner fee: 0.01 BTC (implicit: inputs - outputs)", fill=ORANGE, font=small_font)

        # Scanning line effect
        scan_y = int(80 + (t * 380) % 380)
        draw.line([(0, scan_y), (W, scan_y)], fill=(*CYAN[:3], 30), width=1)

        # Bottom bar
        cycle_val = f"UTXO Set Size: {3 + (f * 7) % 12}"
        draw.text((W // 2, H - 20), cycle_val, fill=DIM, font=small_font, anchor="mt")

        frames.append(img)

    frames[0].save("assets/gifs/bitcoin_01_utxo_model.gif", save_all=True, append_images=frames[1:], duration=DUR, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_01_utxo_model.gif")
