"""Bitcoin BitVM animation — circuit verification with bisection protocol."""
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
    return tuple(int(a + (b - a) * max(0, min(1, t))) for a, b in zip(c1, c2))

def draw_marching_arrow(draw, x0, y0, x1, y1, color, frame, thickness=2):
    draw.line([(x0, y0), (x1, y1)], fill=color, width=thickness)
    dash_len = 8
    total = math.hypot(x1 - x0, y1 - y0)
    if total == 0: return
    dx, dy = (x1 - x0) / total, (y1 - y0) / total
    offset = (frame * 3) % (dash_len * 2)
    d = -offset
    while d < total:
        s = max(0, d)
        e = min(total, d + dash_len)
        if e > s:
            draw.line([(x0 + dx * s, y0 + dy * s), (x0 + dx * e, y0 + dy * e)], fill=WHITE, width=thickness)
        d += dash_len * 2
    draw.polygon([(x1, y1), (x1 - dx * 10 - dy * 5, y1 - dy * 10 + dx * 5),
                  (x1 - dx * 10 + dy * 5, y1 - dy * 10 - dx * 5)], fill=color)

# NAND gate positions (3 gates in a row)
GATES = [
    {"x": 130, "y": 125, "a": "A", "b": "B", "out": "X", "ok": True},
    {"x": 350, "y": 125, "a": "X", "b": "C", "out": "Y", "ok": False},  # bad gate
    {"x": 570, "y": 125, "a": "Y", "b": "D", "out": "Z", "ok": True},
]

frames = []
for f in range(FRAMES):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / FRAMES
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

    # Title
    draw.text((W // 2, 20), "BitVM: Fraud Proof Circuit", fill=CYAN, font=title_font, anchor="mt")
    draw.text((W // 2, 48), "Verify computation on Bitcoin via bisection", fill=DIM, font=body_font, anchor="mt")

    # --- CIRCUIT: NAND gates ---
    draw.text((W // 2, 73), "NAND Gate Circuit", fill=YELLOW, font=header_font, anchor="mt")

    bad_gate_idx = 1  # gate index with fraud
    highlight_gate = (f * 3 // FRAMES) % 3  # which gate the bisection highlights

    for i, g in enumerate(GATES):
        gx, gy = g["x"], g["y"]
        gw, gh = 120, 72

        # Gate box — highlight bad gate in red, current bisection gate in yellow
        if not g["ok"]:
            fill_c = lerp_color(RED_BG, RED, pulse * 0.25)
            outline_c = RED
        elif i == highlight_gate:
            fill_c = lerp_color(DARK_BOX, YELLOW, pulse * 0.15)
            outline_c = YELLOW
        else:
            fill_c = DARK_BOX
            outline_c = BORDER

        draw_rounded_rect(draw, (gx, gy, gx + gw, gy + gh), fill_c, outline_c)
        draw.text((gx + gw // 2, gy + 12), "NAND", fill=WHITE, font=header_font, anchor="mt")

        # Input labels
        draw.text((gx + 15, gy + 35), g["a"], fill=CYAN, font=small_font)
        draw.text((gx + 15, gy + 52), g["b"], fill=CYAN, font=small_font)

        # Output label
        draw.text((gx + gw - 25, gy + 43), g["out"], fill=GREEN, font=small_font)

        # Fraud marker on bad gate
        if not g["ok"]:
            draw.text((gx + gw // 2, gy - 10), "FRAUD", fill=RED, font=small_font, anchor="mt")

    # Wires between gates
    for i in range(len(GATES) - 1):
        x0 = GATES[i]["x"] + 120
        x1 = GATES[i + 1]["x"]
        y = GATES[i]["y"] + 48
        draw_marching_arrow(draw, x0, y, x1, y, GREEN, f)

    # --- BIT COMMITMENTS ---
    draw.text((W // 2, 215), "Bit Commitments (Hash Pairs)", fill=PURPLE, font=header_font, anchor="mt")

    commit_y = 238
    bits = ["A=1", "B=0", "C=1", "D=1", "X=1", "Y=0", "Z=1"]
    bit_w = 90
    total_w = len(bits) * bit_w
    start_x = (W - total_w) // 2

    for i, label in enumerate(bits):
        bx = start_x + i * bit_w
        val = label.split("=")[1]
        col = GREEN if val == "1" else ORANGE
        bg = GREEN_BG if val == "1" else DARK_BOX
        draw_rounded_rect(draw, (bx, commit_y, bx + 82, commit_y + 42), bg, col, r=5)
        draw.text((bx + 41, commit_y + 8), label, fill=col, font=small_font, anchor="mt")
        draw.text((bx + 41, commit_y + 26), "H(pre" + val + ")", fill=DIM, font=small_font, anchor="mt")

    # Mark Y=0 as wrong (NAND(1,1)=0 is wrong, should be 0; NAND(X=1,C=1) should = 0 actually... let's say prover claims Y=1 but it's 0)
    # Highlight the bad commitment
    bad_idx = 5  # Y
    bx = start_x + bad_idx * bit_w
    draw.rectangle((bx - 2, commit_y - 2, bx + 84, commit_y + 44), outline=RED, width=2)

    # --- BISECTION PROTOCOL ---
    draw_rounded_rect(draw, (40, 305, 760, 420), PANEL, BORDER)
    draw.text((400, 318), "Bisection Protocol", fill=WHITE, font=header_font, anchor="mt")

    # Steps
    steps = [
        ("1. Prover", "Claims computation result Z=1", CYAN),
        ("2. Verifier", "Challenges -- bisects to gate #2", YELLOW),
        ("3. Reveal", "Gate NAND(1,1) != claimed output", RED),
        ("4. On-chain", "Fraud proof: prover loses deposit", GREEN),
    ]
    for i, (role, desc, col) in enumerate(steps):
        sy = 340 + i * 19
        # Highlight current step based on frame
        step_idx = (f * len(steps) // FRAMES) % len(steps)
        if i == step_idx:
            draw.rectangle((55, sy - 1, 745, sy + 16), fill=lerp_color(PANEL, col, 0.1))
        draw.text((70, sy), role, fill=col, font=small_font)
        draw.text((200, sy), desc, fill=DIM, font=body_font)

    # --- BOTTOM: Key insight ---
    draw_rounded_rect(draw, (40, 435, 760, 535), DARK_BOX, BORDER)
    draw.text((400, 450), "BitVM Key Properties", fill=PURPLE, font=header_font, anchor="mt")

    props = [
        ("Any computation as NAND gates", CYAN),
        ("Optimistic: only verify on dispute", GREEN),
        ("O(log n) on-chain steps via bisection", YELLOW),
        ("Prover posts bond, loses it on fraud", ORANGE),
    ]
    for i, (txt, col) in enumerate(props):
        px = 70 if i < 2 else 420
        py = 472 + (i % 2) * 22
        draw.text((px, py), "-", fill=col, font=small_font)
        draw.text((px + 14, py), txt, fill=col, font=body_font)

    # Bottom label
    draw.text((400, 520), "Turing-complete verification on Bitcoin", fill=DIM, font=small_font, anchor="mt")

    # Scan line
    scan_y = int(70 + (t * 460) % 460)
    draw.line([(0, scan_y), (W, scan_y)], fill=(*CYAN[:3], 20), width=1)

    frames.append(img)

if __name__ == "__main__":
    frames[0].save("assets/gifs/bitcoin_15_simplified_bitvm.gif", save_all=True, append_images=frames[1:], duration=DUR, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_15_simplified_bitvm.gif")
