"""BTC05-C: Derivation Path — m/44'/0'/0'/0/0 as horizontal chain of labeled boxes."""
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
YELLOW_BG = (58, 50, 14)
RED_BG = (50, 20, 20)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
PANEL = (17, 21, 28)

def load_font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for n in names:
        for p in [f"/usr/share/fonts/truetype/dejavu/{n}", f"/usr/share/fonts/truetype/liberation/{n}", f"/usr/share/fonts/{n}"]:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except (OSError, IOError): pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(14, True)
body_font = load_font(12)
small_font = load_font(10)
mono_font = load_font(12)

def text_w(draw, txt, font):
    bb = draw.textbbox((0,0), txt, font=font)
    return bb[2] - bb[0]

def draw_rounded_box(draw, x, y, w, h, fill, border_col, r=8):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=border_col, width=2)

def marching_hline(draw, x1, x2, y, color, frame, idx=0):
    dash_len = 6
    offset = (frame * 2 + idx * 5) % (dash_len * 2)
    if x2 < x1: x1, x2 = x2, x1
    pos = offset % (dash_len * 2)
    while pos < (x2 - x1):
        sx = x1 + pos
        ex = min(x1 + pos + dash_len, x2)
        draw.line([(sx, y), (ex, y)], fill=color, width=2)
        pos += dash_len * 2
    # arrowhead
    draw.polygon([(x2, y), (x2-8, y-5), (x2-8, y+5)], fill=color)

def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    pulse = 0.5 + 0.5 * math.sin(f * 2 * math.pi / FRAMES)

    # Title
    title = "BIP-32 Derivation Path"
    tw = text_w(draw, title, title_font)
    draw.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)

    # Full path display
    path_str = "m / 44' / 0' / 0' / 0 / 0"
    pw = text_w(draw, path_str, mono_font)
    draw.text(((W - pw) // 2, 50), path_str, fill=YELLOW, font=mono_font)

    # Chain of boxes horizontally
    segments = [
        ("m", "Master", "Root key", YELLOW, YELLOW_BG),
        ("44'", "Purpose", "BIP-44", GREEN, GREEN_BG),
        ("0'", "Coin", "Bitcoin", CYAN, CYAN_BG),
        ("0'", "Account", "Default", PURPLE, PURPLE_BG),
        ("0", "Change", "External", ORANGE, (48, 38, 14)),
        ("0", "Index", "1st addr", WHITE, DARK_BOX),
    ]

    box_w, box_h = 100, 100
    total_w = len(segments) * box_w + (len(segments) - 1) * 30
    start_x = (W - total_w) // 2
    box_y = 90

    # Scan line effect: highlight one box at a time
    scan_idx = (f * len(segments) // FRAMES) % len(segments)

    for i, (val, label, desc, col, fill) in enumerate(segments):
        bx = start_x + i * (box_w + 30)
        by = box_y

        # Glow on scanned box
        if i == scan_idx:
            glow = tuple(int(c * (0.4 + 0.4 * pulse)) for c in col)
            draw_rounded_box(draw, bx-3, by-3, box_w+6, box_h+6, BG, glow, 10)

        draw_rounded_box(draw, bx, by, box_w, box_h, fill, col)

        # Value (the path segment)
        vw = text_w(draw, val, header_font)
        draw.text((bx + (box_w - vw)//2, by + 12), val, fill=col, font=header_font)

        # Label
        lw = text_w(draw, label, body_font)
        draw.text((bx + (box_w - lw)//2, by + 38), label, fill=WHITE, font=body_font)

        # Description
        dw = text_w(draw, desc, small_font)
        draw.text((bx + (box_w - dw)//2, by + 58), desc, fill=DIM, font=small_font)

        # Hardened indicator
        if "'" in val:
            ht = "hardened"
            hw = text_w(draw, ht, small_font)
            draw.text((bx + (box_w - hw)//2, by + 78), ht, fill=RED, font=small_font)
        else:
            nt = "normal"
            nw = text_w(draw, nt, small_font)
            draw.text((bx + (box_w - nw)//2, by + 78), nt, fill=GREEN, font=small_font)

        # Arrow between boxes
        if i < len(segments) - 1:
            marching_hline(draw, bx + box_w + 2, bx + box_w + 28, by + box_h//2, col, f, i)

    # Result arrow and address box
    result_y = 220
    arrow_start_x = start_x + (len(segments)-1) * (box_w + 30) + box_w // 2
    arrow_end_y = result_y + 20

    # Final address box
    addr_bx = (W - 350) // 2
    addr_by = result_y + 30
    draw_rounded_box(draw, addr_bx, addr_by, 350, 50, CYAN_BG, CYAN)
    draw.text((addr_bx + 15, addr_by + 8), "Derived Address:", fill=DIM, font=body_font)
    # Cycling address
    cycle = (f * 2) % 16
    addr = f"1A1zP1eP5QGefi2DMPTf{cycle:x}L5v7Dh"
    draw.text((addr_bx + 15, addr_by + 26), addr, fill=CYAN, font=mono_font)

    # Explanation panels below
    panels = [
        ("Hardened Derivation (')", "Parent public key CANNOT derive children.\nMore secure -- used for purpose/coin/account.", RED, RED_BG),
        ("Normal Derivation", "Parent public key CAN derive children.\nUsed for change/index -- enables watch-only.", GREEN, GREEN_BG),
    ]

    panel_y = 320
    for i, (ptitle, pdesc, pcol, pfill) in enumerate(panels):
        px = 30 + i * 390
        pw_val = 350
        ph = 90
        draw_rounded_box(draw, px, panel_y, pw_val, ph, pfill, pcol)
        draw.text((px + 15, panel_y + 10), ptitle, fill=pcol, font=header_font)
        for j, line in enumerate(pdesc.split("\n")):
            draw.text((px + 15, panel_y + 32 + j * 18), line, fill=WHITE, font=body_font)

    # Bottom: Why it matters
    why_y = 435
    draw_rounded_box(draw, 30, why_y, 740, 90, PANEL, BORDER)
    draw.text((50, why_y + 10), "Why Derivation Paths Matter:", fill=YELLOW, font=header_font)
    bullets = [
        "Wallets agree on same paths = interoperability (restore in any wallet)",
        "Each account is isolated -- compromise one, others are safe",
        "Hardened levels prevent public key leaks from exposing parent",
    ]
    for i, b in enumerate(bullets):
        draw.text((50, why_y + 32 + i * 18), b, fill=WHITE, font=body_font)

    return img

if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save("assets/gifs/bitcoin_05_wallets_hd.gif", save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_05_wallets_hd.gif")
