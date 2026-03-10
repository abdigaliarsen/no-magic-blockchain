"""
Blob Transactions (EIP-4844): Type-3 tx structure with execution payload
and blob sidecar. Blob shown as colored cell grid. Fee market chart
with exponential pricing curve.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/ethereum_11_blob_transactions.gif"

CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
RED = (248, 113, 113)
PURPLE = (167, 139, 250)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)
BG = (13, 17, 23)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)

CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
YELLOW_BG = (58, 50, 14)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)


def load_font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for n in names:
        for p in [f"/usr/share/fonts/truetype/dejavu/{n}", f"/usr/share/fonts/truetype/liberation/{n}", f"/usr/share/fonts/{n}"]:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
    return ImageFont.load_default()


font_title = load_font(26, bold=True)
font_header = load_font(15, bold=True)
font_body = load_font(13)
font_small = load_font(11)


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def draw_rounded_rect(draw, xy, fill, outline=None, radius=8):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / (FRAMES - 1)

    # --- Title ---
    draw.text((30, 18), "Blob Transactions (EIP-4844)", font=font_title, fill=WHITE)
    draw.line((30, 52, 770, 52), fill=BORDER, width=1)

    # --- Left: Type-3 Transaction structure ---
    draw.text((40, 62), "Type-3 Transaction", font=font_header, fill=CYAN)

    # Execution payload box
    exec_box = (40, 86, 280, 230)
    draw_rounded_rect(draw, exec_box, fill=DARK_BOX, outline=CYAN)
    draw.text((55, 92), "Execution Payload", font=font_body, fill=CYAN)
    fields_exec = [
        ("type: 0x03", CYAN),
        ("to: 0xabcd...", DIM),
        ("value: 0", DIM),
        ("maxFeePerGas", DIM),
        ("maxFeePerBlobGas", YELLOW),
        ("blob_versioned_hashes", ORANGE),
    ]
    fy = 114
    for label, color in fields_exec:
        draw.text((60, fy), label, font=font_small, fill=color)
        fy += 18

    # Blob sidecar box
    sidecar_box = (40, 245, 280, 340)
    draw_rounded_rect(draw, sidecar_box, fill=DARK_BOX, outline=ORANGE)
    draw.text((55, 252), "Blob Sidecar", font=font_body, fill=ORANGE)
    draw.text((60, 274), "blobs: [Blob]", font=font_small, fill=ORANGE)
    draw.text((60, 292), "commitments: [KZG]", font=font_small, fill=YELLOW)
    draw.text((60, 310), "proofs: [KZG]", font=font_small, fill=YELLOW)

    # Arrow connecting exec to sidecar
    draw.line((160, 233, 160, 242), fill=DIM, width=2)
    draw.polygon([(160, 245), (156, 239), (164, 239)], fill=ORANGE)

    # --- Middle: Blob data grid ---
    draw.text((310, 62), "Blob Data (~128 KB)", font=font_header, fill=ORANGE)

    # Draw a grid of colored cells representing blob data
    grid_x, grid_y = 310, 86
    cell_size = 14
    cols, rows = 16, 10
    # Use a deterministic color pattern with animation
    for row in range(rows):
        for col in range(cols):
            seed = row * cols + col
            # Cycle colors based on frame
            phase = (seed * 0.1 + t * 2) % 1.0
            if phase < 0.25:
                c = lerp_color(CYAN_BG, CYAN, 0.3 + 0.3 * math.sin(phase * math.pi * 8))
            elif phase < 0.5:
                c = lerp_color(GREEN_BG, GREEN, 0.3 + 0.3 * math.sin(phase * math.pi * 8))
            elif phase < 0.75:
                c = lerp_color(PURPLE_BG, PURPLE, 0.3 + 0.3 * math.sin(phase * math.pi * 8))
            else:
                c = lerp_color(YELLOW_BG, YELLOW, 0.3 + 0.3 * math.sin(phase * math.pi * 8))
            cx = grid_x + col * (cell_size + 2)
            cy = grid_y + row * (cell_size + 2)
            draw.rectangle((cx, cy, cx + cell_size, cy + cell_size), fill=c)

    # Scanning line across blob
    scan_col = int(cols * ((t * 2) % 1.0))
    sx = grid_x + scan_col * (cell_size + 2)
    draw.rectangle((sx, grid_y, sx + cell_size, grid_y + rows * (cell_size + 2) - 2), outline=WHITE, width=1)

    blob_bottom = grid_y + rows * (cell_size + 2) + 5
    draw.text((310, blob_bottom), "4096 field elements per blob", font=font_small, fill=DIM)
    draw.text((310, blob_bottom + 16), "Max 6 blobs per block", font=font_small, fill=DIM)

    # KZG commitment box
    kzg_y = blob_bottom + 38
    kzg_box = (310, kzg_y, 560, kzg_y + 40)
    draw_rounded_rect(draw, kzg_box, fill=YELLOW_BG, outline=YELLOW)
    draw.text((325, kzg_y + 5), "KZG Commitment", font=font_body, fill=YELLOW)
    draw.text((325, kzg_y + 22), "polynomial commitment scheme", font=font_small, fill=DIM)

    # --- Right: Fee market chart ---
    draw.line((30, 355, 770, 355), fill=BORDER, width=1)
    draw.text((40, 365), "Blob Fee Market (Exponential Pricing)", font=font_header, fill=RED)

    # Chart area
    chart_x, chart_y = 60, 395
    chart_w, chart_h = 320, 130

    # Axes
    draw.line((chart_x, chart_y + chart_h, chart_x + chart_w, chart_y + chart_h), fill=DIM, width=1)
    draw.line((chart_x, chart_y, chart_x, chart_y + chart_h), fill=DIM, width=1)
    draw.text((chart_x + chart_w // 2 - 30, chart_y + chart_h + 5), "blob count", font=font_small, fill=DIM)
    draw.text((chart_x - 5, chart_y - 15), "price", font=font_small, fill=DIM)

    # Exponential curve
    points = []
    for i in range(chart_w):
        x = i / chart_w
        # Exponential: price = e^(excess * factor) - show steep rise
        y = math.exp(x * 3.5) / math.exp(3.5)
        px = chart_x + i
        py = chart_y + chart_h - int(y * chart_h * 0.9)
        py = max(chart_y, py)
        points.append((px, py))

    for i in range(1, len(points)):
        draw.line((points[i - 1][0], points[i - 1][1], points[i][0], points[i][1]), fill=RED, width=2)

    # Animated dot on curve showing current blob gas price
    dot_idx = int((0.2 + 0.6 * (math.sin(t * math.pi * 2) + 1) / 2) * (len(points) - 1))
    dx, dy = points[dot_idx]
    draw.ellipse((dx - 5, dy - 5, dx + 5, dy + 5), fill=RED)

    # Target line at 3 blobs
    target_x = chart_x + int(chart_w * 0.5)
    draw.line((target_x, chart_y, target_x, chart_y + chart_h), fill=GREEN, width=1)
    draw.text((target_x + 4, chart_y + 2), "target=3", font=font_small, fill=GREEN)

    # --- Right panel: data availability ---
    draw.text((430, 365), "Data Availability", font=font_header, fill=GREEN)
    da_items = [
        ("Blobs pruned after ~18 days", GREEN),
        ("NOT in execution layer", ORANGE),
        ("Verified via KZG proofs", YELLOW),
        ("Separate fee market", RED),
        ("Scales L2 rollup data", CYAN),
    ]
    iy = 392
    for label, color in da_items:
        pulse = 0.5 + 0.5 * math.sin(t * math.pi * 2 + iy * 0.03)
        dc = lerp_color(DIM, color, pulse)
        draw.rectangle((440, iy + 4, 448, iy + 12), fill=dc)
        draw.text((456, iy), label, font=font_small, fill=color)
        iy += 22

    # Bottom note
    draw.text((40, 530), "Proto-danksharding: separate data layer for rollup scalability", font=font_small, fill=DIM)

    return img


if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print(f"Saved {OUT}")
