"""Timelocks & HTLCs (Atomic Swap) animation."""
from PIL import Image, ImageDraw, ImageFont
import math, os

W, H, FRAMES, DUR = 800, 550, 72, 90
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

def draw_clock(draw, cx, cy, r, color, frame):
    """Draw a simple clock icon."""
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=color, width=2)
    # Hour hand
    angle = -math.pi / 2 + (frame / 72) * 2 * math.pi
    hx = cx + int(r * 0.5 * math.cos(angle))
    hy = cy + int(r * 0.5 * math.sin(angle))
    draw.line([(cx, cy), (hx, hy)], fill=color, width=2)
    # Minute hand
    m_angle = -math.pi / 2 + (frame / 72) * 2 * math.pi * 4
    mx = cx + int(r * 0.7 * math.cos(m_angle))
    my = cy + int(r * 0.7 * math.sin(m_angle))
    draw.line([(cx, cy), (mx, my)], fill=color, width=1)

def draw_key_icon(draw, cx, cy, color):
    """Draw a simple key shape."""
    # Circle head
    draw.ellipse([(cx - 6, cy - 6), (cx + 6, cy + 6)], outline=color, width=2)
    # Shaft
    draw.line([(cx + 6, cy), (cx + 22, cy)], fill=color, width=2)
    # Teeth
    draw.line([(cx + 16, cy), (cx + 16, cy + 5)], fill=color, width=2)
    draw.line([(cx + 20, cy), (cx + 20, cy + 5)], fill=color, width=2)

if __name__ == "__main__":
    frames = []

    for f in range(FRAMES):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        t = f / FRAMES
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

        # Title
        draw.text((W // 2, 22), "Timelocks & HTLCs", fill=CYAN, font=title_font, anchor="mt")
        draw.text((W // 2, 52), "Atomic Swap: trustless cross-chain exchange", fill=DIM, font=body_font, anchor="mt")

        # ---- Alice (left) ----
        alice_x, alice_y = 120, 110
        glow_a = lerp_color(BORDER, CYAN, pulse * 0.3)
        draw_rounded_rect(draw, (alice_x - 80, alice_y, alice_x + 80, alice_y + 60), CYAN_BG, glow_a)
        draw.text((alice_x, alice_y + 12), "Alice", fill=CYAN, font=header_font, anchor="mt")
        draw.text((alice_x, alice_y + 35), "Has 1.0 BTC", fill=WHITE, font=small_font, anchor="mt")

        # ---- Bob (right) ----
        bob_x, bob_y = 680, 110
        glow_b = lerp_color(BORDER, GREEN, pulse * 0.3)
        draw_rounded_rect(draw, (bob_x - 80, bob_y, bob_x + 80, bob_y + 60), GREEN_BG, glow_b)
        draw.text((bob_x, bob_y + 12), "Bob", fill=GREEN, font=header_font, anchor="mt")
        draw.text((bob_x, bob_y + 35), "Has 50 LTC", fill=WHITE, font=small_font, anchor="mt")

        # ---- Center: Hash preimage (secret) ----
        secret_y = 88
        draw_rounded_rect(draw, (335, secret_y, 465, secret_y + 34), PURPLE_BG, PURPLE)
        draw.text((400, secret_y + 10), "Secret S", fill=PURPLE, font=small_font, anchor="mt")

        # ---- HTLC boxes ----
        # BTC HTLC (Alice -> Bob)
        htlc1_y = 200
        draw_rounded_rect(draw, (50, htlc1_y, 380, htlc1_y + 110), DARK_BOX, ORANGE)
        draw.text((215, htlc1_y + 10), "HTLC on Bitcoin", fill=ORANGE, font=header_font, anchor="mt")

        # Hash lock icon + label
        draw_key_icon(draw, 80, htlc1_y + 48, YELLOW)
        draw.text((115, htlc1_y + 42), "Hash Lock:", fill=YELLOW, font=small_font)
        draw.text((200, htlc1_y + 42), "H(S)", fill=DIM, font=mono_font)

        # Time lock icon + label
        draw_clock(draw, 88, htlc1_y + 80, 10, RED, f)
        draw.text((115, htlc1_y + 74), "Time Lock:", fill=RED, font=small_font)
        draw.text((200, htlc1_y + 74), "48 hours", fill=DIM, font=mono_font)

        draw.text((310, htlc1_y + 50), "1.0 BTC", fill=CYAN, font=header_font, anchor="mt")
        draw.text((310, htlc1_y + 75), "locked", fill=DIM, font=small_font, anchor="mt")

        # LTC HTLC (Bob -> Alice)
        htlc2_y = 200
        draw_rounded_rect(draw, (420, htlc2_y, 750, htlc2_y + 110), DARK_BOX, PURPLE)
        draw.text((585, htlc2_y + 10), "HTLC on Litecoin", fill=PURPLE, font=header_font, anchor="mt")

        draw_key_icon(draw, 450, htlc2_y + 48, YELLOW)
        draw.text((485, htlc2_y + 42), "Hash Lock:", fill=YELLOW, font=small_font)
        draw.text((570, htlc2_y + 42), "H(S)", fill=DIM, font=mono_font)

        draw_clock(draw, 458, htlc2_y + 80, 10, RED, f)
        draw.text((485, htlc2_y + 74), "Time Lock:", fill=RED, font=small_font)
        draw.text((570, htlc2_y + 74), "24 hours", fill=DIM, font=mono_font)

        draw.text((685, htlc2_y + 50), "50 LTC", fill=GREEN, font=header_font, anchor="mt")
        draw.text((685, htlc2_y + 75), "locked", fill=DIM, font=small_font, anchor="mt")

        # ---- Crossing arrows between HTLCs ----
        # Alice creates BTC HTLC for Bob
        draw_marching_arrow(draw, alice_x + 80, alice_y + 50, 215, htlc1_y, CYAN, f)
        # Bob creates LTC HTLC for Alice
        draw_marching_arrow(draw, bob_x - 80, bob_y + 50, 585, htlc2_y, GREEN, f)

        # ---- Bottom: swap steps ----
        draw_rounded_rect(draw, (40, 340, 760, 470), PANEL, BORDER)
        draw.text((400, 355), "Atomic Swap Steps", fill=WHITE, font=header_font, anchor="mt")

        steps = [
            ("1.", "Alice picks secret S, publishes H(S)", CYAN),
            ("2.", "Alice locks 1.0 BTC in HTLC (48h timeout)", ORANGE),
            ("3.", "Bob locks 50 LTC in HTLC using same H(S) (24h)", PURPLE),
            ("4.", "Alice claims 50 LTC by revealing S", GREEN),
            ("5.", "Bob sees S on-chain, claims 1.0 BTC", GREEN),
        ]

        # Highlight current step based on frame
        active_step = (f // 14) % 5
        for i, (num, text, col) in enumerate(steps):
            sy = 378 + i * 17
            if i == active_step:
                step_col = lerp_color(col, WHITE, pulse * 0.4)
                draw.text((65, sy), num, fill=step_col, font=small_font)
                draw.text((82, sy), text, fill=step_col, font=small_font)
                # Small indicator
                draw.rectangle([(52, sy + 1), (58, sy + 11)], fill=col)
            else:
                draw.text((65, sy), num, fill=DIM, font=small_font)
                draw.text((82, sy), text, fill=DIM, font=small_font)

        # Right side: properties
        prop_x = 530
        draw.text((prop_x, 380), "Properties:", fill=WHITE, font=small_font)
        draw.text((prop_x + 15, 398), "Trustless (no third party)", fill=GREEN, font=small_font)
        draw.text((prop_x + 15, 416), "Atomic (all or nothing)", fill=GREEN, font=small_font)
        draw.text((prop_x + 15, 434), "Timeout = refund safety", fill=YELLOW, font=small_font)
        draw.text((prop_x + 15, 452), "Cross-chain compatible", fill=CYAN, font=small_font)

        # Footer
        draw.text((W // 2, H - 15), "HTLCs power Lightning Network & atomic swaps", fill=DIM, font=small_font, anchor="mt")

        # Subtle scanning
        scan_y = int(80 + (t * 400) % 400)
        draw.line([(0, scan_y), (W, scan_y)], fill=(*CYAN[:3],), width=1)

        frames.append(img)

    frames[0].save("assets/gifs/bitcoin_12_timelocks_htlcs.gif", save_all=True,
                   append_images=frames[1:], duration=DUR, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_12_timelocks_htlcs.gif")
