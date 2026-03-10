"""Compact Block Relay (BIP 152) animation."""
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
                except: pass
    return ImageFont.load_default()

def load_mono(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]:
        try: return ImageFont.truetype(p, size)
        except: pass
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

def draw_node_circle(draw, cx, cy, r, label, color, bg, font):
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=bg, outline=color, width=2)
    draw.text((cx, cy), label, fill=color, font=font, anchor="mm")

if __name__ == "__main__":
    frames = []

    # TX grid layout: 4x3 grid of small tx boxes
    tx_ids = [f"tx{i:02d}" for i in range(12)]
    # 10 are in mempool (green), 2 missing (red)
    in_mempool = [True] * 10 + [False, False]

    for f in range(FRAMES):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        t = f / FRAMES
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

        # Title
        draw.text((W // 2, 22), "Compact Block Relay", fill=CYAN, font=title_font, anchor="mt")
        draw.text((W // 2, 52), "BIP 152: Send short IDs, reconstruct from mempool", fill=DIM, font=body_font, anchor="mt")

        # ---- Left: Sender node ----
        draw_node_circle(draw, 100, 140, 35, "Node A", CYAN, CYAN_BG, small_font)
        draw.text((100, 185), "Miner", fill=DIM, font=small_font, anchor="mt")

        # Compact block box below sender
        cb_y = 205
        draw_rounded_rect(draw, (40, cb_y, 160, cb_y + 70), DARK_BOX, CYAN)
        draw.text((100, cb_y + 12), "Compact Block", fill=CYAN, font=small_font, anchor="mt")
        draw.text((100, cb_y + 30), "Header + 12 short IDs", fill=DIM, font=small_font, anchor="mt")
        draw.text((100, cb_y + 48), "~15 KB", fill=GREEN, font=mono_font, anchor="mt")

        # ---- Right: Receiver node ----
        draw_node_circle(draw, 700, 140, 35, "Node B", GREEN, GREEN_BG, small_font)
        draw.text((700, 185), "Peer", fill=DIM, font=small_font, anchor="mt")

        # Mempool grid below receiver
        mp_y = 205
        draw_rounded_rect(draw, (560, mp_y, 770, mp_y + 120), PANEL, BORDER)
        draw.text((665, mp_y + 10), "Mempool", fill=WHITE, font=small_font, anchor="mt")

        # Draw tx grid 4x3
        for i, tid in enumerate(tx_ids):
            row, col = divmod(i, 4)
            bx = 575 + col * 48
            by = mp_y + 28 + row * 28
            if in_mempool[i]:
                highlight = lerp_color(GREEN_BG, GREEN, pulse * 0.2) if i == (f % 10) else GREEN_BG
                draw_rounded_rect(draw, (bx, by, bx + 42, by + 22), highlight, GREEN, r=4)
                draw.text((bx + 21, by + 7), tid, fill=GREEN, font=small_font, anchor="mt")
            else:
                draw_rounded_rect(draw, (bx, by, bx + 42, by + 22), RED_BG, RED, r=4)
                draw.text((bx + 21, by + 7), tid, fill=RED, font=small_font, anchor="mt")

        # ---- Arrows between nodes ----
        # Step 1: compact block A -> B
        draw_marching_arrow(draw, 140, 140, 660, 140, CYAN, f)
        draw.text((400, 125), "cmpctblock", fill=CYAN, font=small_font, anchor="mb")

        # Step 2: getblocktxn B -> A (for missing txs)
        draw_marching_arrow(draw, 660, 160, 140, 160, RED, f)
        draw.text((400, 172), "getblocktxn (2 missing)", fill=RED, font=small_font, anchor="mt")

        # ---- Bottom: reconstruction + stats ----
        draw_rounded_rect(draw, (40, 345, 460, 460), PANEL, BORDER)
        draw.text((250, 362), "Block Reconstruction", fill=WHITE, font=header_font, anchor="mt")

        # Show hit/miss stats
        draw.text((70, 390), "Mempool hits:", fill=GREEN, font=body_font)
        draw.text((200, 390), "10 / 12", fill=GREEN, font=mono_font)
        draw.text((280, 390), "(83%)", fill=DIM, font=small_font)

        draw.text((70, 415), "Missing txs:", fill=RED, font=body_font)
        draw.text((200, 415), "2 / 12", fill=RED, font=mono_font)
        draw.text((280, 415), "(requested)", fill=DIM, font=small_font)

        draw.text((70, 440), "Result:", fill=WHITE, font=body_font)
        result_col = lerp_color(GREEN, WHITE, pulse * 0.3)
        draw.text((200, 440), "Full block reconstructed", fill=result_col, font=mono_font)

        # Bandwidth comparison
        draw_rounded_rect(draw, (490, 345, 760, 460), PANEL, BORDER)
        draw.text((625, 362), "Bandwidth Saved", fill=WHITE, font=header_font, anchor="mt")

        # Full block bar
        bar_x = 520
        full_w = 200
        draw_rounded_rect(draw, (bar_x, 390, bar_x + full_w, 406), RED_BG, RED, r=4)
        draw.text((bar_x - 5, 394), "Full", fill=RED, font=small_font, anchor="rm")
        draw.text((bar_x + full_w + 5, 394), "1 MB", fill=DIM, font=small_font, anchor="lm")

        # Compact bar
        compact_w = int(full_w * 15 / 1000)  # ~15KB vs 1MB
        draw_rounded_rect(draw, (bar_x, 416, bar_x + compact_w + 4, 432), GREEN_BG, GREEN, r=4)
        draw.text((bar_x - 5, 420), "Compact", fill=GREEN, font=small_font, anchor="rm")
        draw.text((bar_x + compact_w + 10, 420), "~15 KB", fill=DIM, font=small_font, anchor="lm")

        savings_col = lerp_color(GREEN, WHITE, pulse * 0.3)
        draw.text((625, 448), "-98.5% bandwidth", fill=savings_col, font=header_font, anchor="mt")

        # Scanning line
        scan_x = int(40 + (t * 720) % 720)
        draw.line([(scan_x, 75), (scan_x, 335)], fill=CYAN, width=1)

        # Footer
        draw.text((W // 2, H - 15), "BIP 152 -- Compact Block Relay (2016)", fill=DIM, font=small_font, anchor="mt")

        frames.append(img)

    frames[0].save("assets/gifs/bitcoin_11_compact_block_relay.gif", save_all=True,
                   append_images=frames[1:], duration=DUR, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_11_compact_block_relay.gif")
