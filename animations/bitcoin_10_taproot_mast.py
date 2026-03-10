"""Taproot & MAST animation."""
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
YELLOW_BG = (58, 50, 14)

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

    for f in range(FRAMES):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        t = f / FRAMES
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

        # Title
        draw.text((W // 2, 22), "Taproot: MAST Tree", fill=CYAN, font=title_font, anchor="mt")
        draw.text((W // 2, 52), "Key-path or script-path spending", fill=DIM, font=body_font, anchor="mt")

        # ---- MAST tree (left half) ----
        # Internal key (top of tree)
        ik_x, ik_y = 200, 85
        glow_ik = lerp_color(BORDER, CYAN, pulse * 0.4)
        draw_rounded_rect(draw, (ik_x - 70, ik_y, ik_x + 70, ik_y + 40), CYAN_BG, glow_ik)
        draw.text((ik_x, ik_y + 12), "Internal Key P", fill=CYAN, font=header_font, anchor="mt")

        # Merkle root
        mr_y = 155
        draw_rounded_rect(draw, (ik_x - 55, mr_y, ik_x + 55, mr_y + 35), DARK_BOX, YELLOW)
        draw.text((ik_x, mr_y + 10), "Merkle Root", fill=YELLOW, font=small_font, anchor="mt")

        # Lines from key to root
        draw.line([(ik_x, ik_y + 40), (ik_x, mr_y)], fill=DIM, width=1)

        # Intermediate hashes
        h1_x, h1_y = 130, 215
        h2_x, h2_y = 270, 215
        draw_rounded_rect(draw, (h1_x - 40, h1_y, h1_x + 40, h1_y + 30), DARK_BOX, BORDER)
        draw.text((h1_x, h1_y + 8), "H(A|B)", fill=DIM, font=small_font, anchor="mt")
        draw_rounded_rect(draw, (h2_x - 40, h2_y, h2_x + 40, h2_y + 30), DARK_BOX, BORDER)
        draw.text((h2_x, h2_y + 8), "H(C)", fill=DIM, font=small_font, anchor="mt")

        # Lines root -> hashes
        draw.line([(ik_x, mr_y + 35), (h1_x, h1_y)], fill=DIM, width=1)
        draw.line([(ik_x, mr_y + 35), (h2_x, h2_y)], fill=DIM, width=1)

        # Leaf scripts
        leaves = [("Script A", 75, GREEN, GREEN_BG, "2-of-3 MS"),
                  ("Script B", 175, PURPLE, PURPLE_BG, "Timelock"),
                  ("Script C", 275, ORANGE, YELLOW_BG, "Hashlock")]
        leaf_y = 275
        for name, lx, col, bg, desc in leaves:
            draw_rounded_rect(draw, (lx - 45, leaf_y, lx + 45, leaf_y + 50), bg, col)
            draw.text((lx, leaf_y + 12), name, fill=col, font=small_font, anchor="mt")
            draw.text((lx, leaf_y + 32), desc, fill=DIM, font=small_font, anchor="mt")

        # Lines hashes -> leaves
        draw.line([(h1_x, h1_y + 30), (75, leaf_y)], fill=DIM, width=1)
        draw.line([(h1_x, h1_y + 30), (175, leaf_y)], fill=DIM, width=1)
        draw.line([(h2_x, h2_y + 30), (275, leaf_y)], fill=DIM, width=1)

        # ---- Right side: spend paths ----
        # Key-path spend
        kp_x = 530
        kp_y = 85
        glow_kp = lerp_color(BORDER, GREEN, pulse * 0.35)
        draw_rounded_rect(draw, (kp_x, kp_y, 770, kp_y + 100), GREEN_BG, glow_kp)
        draw.text((kp_x + 120, kp_y + 12), "Key-Path Spend", fill=GREEN, font=header_font, anchor="mt")
        draw.text((kp_x + 120, kp_y + 35), "Just 1 Schnorr sig", fill=WHITE, font=body_font, anchor="mt")
        draw.text((kp_x + 120, kp_y + 55), "No tree revealed", fill=DIM, font=small_font, anchor="mt")
        draw.text((kp_x + 120, kp_y + 75), "64 bytes on-chain", fill=DIM, font=small_font, anchor="mt")

        # Arrow from internal key to key-path
        draw_marching_arrow(draw, ik_x + 70, ik_y + 20, kp_x - 2, kp_y + 50, GREEN, f)

        # Script-path spend
        sp_y = 210
        glow_sp = lerp_color(BORDER, ORANGE, pulse * 0.35)
        draw_rounded_rect(draw, (kp_x, sp_y, 770, sp_y + 120), YELLOW_BG, glow_sp)
        draw.text((kp_x + 120, sp_y + 12), "Script-Path Spend", fill=ORANGE, font=header_font, anchor="mt")
        draw.text((kp_x + 120, sp_y + 35), "Reveal 1 leaf script", fill=WHITE, font=body_font, anchor="mt")
        draw.text((kp_x + 120, sp_y + 55), "+ Merkle proof", fill=DIM, font=small_font, anchor="mt")
        draw.text((kp_x + 120, sp_y + 75), "Other scripts stay", fill=DIM, font=small_font, anchor="mt")
        draw.text((kp_x + 120, sp_y + 95), "hidden (privacy!)", fill=DIM, font=small_font, anchor="mt")

        # Arrow from tree leaf to script-path
        draw_marching_arrow(draw, 320, leaf_y + 25, kp_x - 2, sp_y + 60, ORANGE, f)

        # ---- Bottom: privacy badge ----
        draw_rounded_rect(draw, (50, 385, 750, 470), PANEL, BORDER)
        draw.text((400, 402), "Privacy Advantage", fill=WHITE, font=header_font, anchor="mt")

        # Key-path row
        draw.text((80, 425), "Key-path:", fill=GREEN, font=body_font)
        draw_rounded_rect(draw, (180, 418, 450, 440), GREEN_BG, GREEN, r=4)
        draw.text((315, 424), "Looks like any regular P2TR payment", fill=WHITE, font=small_font, anchor="mt")

        # Script-path row
        draw.text((80, 450), "Script-path:", fill=ORANGE, font=body_font)
        draw_rounded_rect(draw, (180, 443, 450, 465), YELLOW_BG, ORANGE, r=4)
        draw.text((315, 449), "Only reveals the executed branch", fill=WHITE, font=small_font, anchor="mt")

        # Badge
        badge_col = lerp_color(GREEN, WHITE, pulse * 0.3)
        draw_rounded_rect(draw, (500, 420, 730, 460), GREEN_BG, badge_col, r=12)
        draw.text((615, 434), "Indistinguishable on-chain", fill=badge_col, font=small_font, anchor="mm")

        # Scanning highlight
        scan_y = int(80 + (t * 400) % 400)
        draw.line([(0, scan_y), (W, scan_y)], fill=CYAN, width=1)

        # Footer
        draw.text((W // 2, H - 15), "BIP 341 (Taproot) -- Activated Nov 2021", fill=DIM, font=small_font, anchor="mt")

        frames.append(img)

    frames[0].save("assets/gifs/bitcoin_10_taproot_mast.gif", save_all=True,
                   append_images=frames[1:], duration=DUR, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_10_taproot_mast.gif")
