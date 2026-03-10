"""
EVM Precompiles: Grid of 9 precompile boxes (0x01-0x09),
highlight one showing input -> computation -> output,
gas cost comparison: precompile vs EVM bytecode equivalent.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# --- Constants ---
W, H = 800, 550
FRAMES = 72
DELAY = 90
OUT = "assets/gifs/ethereum_15_evm_precompiles.gif"

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
ORANGE_BG = (55, 35, 15)


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
font_tiny = load_font(10)


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def draw_rounded_rect(draw, xy, fill, outline=None, radius=8):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def draw_arrow_h(draw, x1, x2, y, color, t_anim):
    """Horizontal arrow with animated dot."""
    draw.line((x1, y, x2, y), fill=DIM, width=2)
    direction = 1 if x2 > x1 else -1
    draw.polygon([(x2, y), (x2 - direction * 6, y - 4), (x2 - direction * 6, y + 4)], fill=color)
    dx = x1 + (x2 - x1) * (t_anim % 1.0)
    draw.ellipse((dx - 3, y - 3, dx + 3, y + 3), fill=color)


PRECOMPILES = [
    ("0x01", "ecRecover", "ECDSA recovery", 3000, CYAN),
    ("0x02", "SHA-256", "SHA-256 hash", 60, GREEN),
    ("0x03", "RIPEMD160", "RIPEMD-160 hash", 600, GREEN),
    ("0x04", "identity", "Data copy", 15, YELLOW),
    ("0x05", "modexp", "Modular exponent", 200, ORANGE),
    ("0x06", "ecAdd", "BN256 EC add", 150, PURPLE),
    ("0x07", "ecMul", "BN256 EC multiply", 6000, PURPLE),
    ("0x08", "ecPairing", "BN256 pairing", 45000, RED),
    ("0x09", "blake2f", "BLAKE2b compress", 1, CYAN),
]


def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = f / (FRAMES - 1)

    # --- Title ---
    draw.text((30, 18), "EVM Precompiled Contracts", font=font_title, fill=WHITE)
    draw.line((30, 52, 770, 52), fill=BORDER, width=1)

    # === Precompile Grid (3x3) ===
    draw.text((40, 60), "Precompiles (0x01 - 0x09)", font=font_header, fill=CYAN)
    draw.text((40, 78), "Native code at fixed addresses, cheaper than EVM bytecode", font=font_small, fill=DIM)

    # Which precompile is highlighted (cycles through)
    highlight_idx = f // 8 % 9

    grid_x0 = 40
    grid_y0 = 98
    cell_w = 235
    cell_h = 40
    gap_x = 8
    gap_y = 6

    for i, (addr, name, desc, gas, color) in enumerate(PRECOMPILES):
        row = i // 3
        col = i % 3
        cx = grid_x0 + col * (cell_w + gap_x)
        cy = grid_y0 + row * (cell_h + gap_y)

        is_hl = (i == highlight_idx)
        bg = CYAN_BG if is_hl and color == CYAN else GREEN_BG if is_hl and color == GREEN else PURPLE_BG if is_hl and color == PURPLE else YELLOW_BG if is_hl and color == YELLOW else ORANGE_BG if is_hl and color == ORANGE else RED_BG if is_hl and color == RED else DARK_BOX
        outline = color if is_hl else BORDER

        box = (cx, cy, cx + cell_w, cy + cell_h)
        draw_rounded_rect(draw, box, fill=bg, outline=outline)
        draw.text((cx + 8, cy + 4), addr, font=font_small, fill=color)
        draw.text((cx + 48, cy + 4), name, font=font_small, fill=WHITE if is_hl else DIM)
        draw.text((cx + 8, cy + 20), desc, font=font_tiny, fill=DIM)
        draw.text((cx + 160, cy + 20), f"{gas} gas", font=font_tiny, fill=color if is_hl else DIM)

    # === Highlighted Precompile Detail ===
    detail_y = grid_y0 + 3 * (cell_h + gap_y) + 10
    draw.line((30, detail_y, 770, detail_y), fill=BORDER, width=1)

    hl = PRECOMPILES[highlight_idx]
    hl_addr, hl_name, hl_desc, hl_gas, hl_color = hl
    draw.text((40, detail_y + 8), f"Detail: {hl_addr} {hl_name}", font=font_header, fill=hl_color)

    # Input -> Precompile -> Output flow
    flow_y = detail_y + 32
    # Input box
    in_box = (40, flow_y, 200, flow_y + 42)
    draw_rounded_rect(draw, in_box, fill=DARK_BOX, outline=BORDER)
    draw.text((52, flow_y + 4), "Input (calldata)", font=font_small, fill=DIM)
    draw.text((52, flow_y + 20), "msg.data bytes", font=font_tiny, fill=DIM)

    # Precompile box (highlighted)
    pulse = 0.5 + 0.5 * math.sin(t * math.pi * 4)
    pc_color = lerp_color(BORDER, hl_color, pulse)
    pc_box = (260, flow_y, 490, flow_y + 42)
    draw_rounded_rect(draw, pc_box, fill=DARK_BOX, outline=pc_color)
    draw.text((275, flow_y + 4), f"CALL {hl_addr}", font=font_body, fill=hl_color)
    draw.text((275, flow_y + 22), f"native: {hl_gas} gas", font=font_tiny, fill=DIM)

    # Output box
    out_box = (550, flow_y, 760, flow_y + 42)
    draw_rounded_rect(draw, out_box, fill=DARK_BOX, outline=BORDER)
    draw.text((562, flow_y + 4), "Output (return)", font=font_small, fill=DIM)
    draw.text((562, flow_y + 20), "result bytes", font=font_tiny, fill=DIM)

    # Arrows
    ary = flow_y + 21
    draw_arrow_h(draw, 205, 255, ary, hl_color, t * 3)
    draw_arrow_h(draw, 495, 545, ary, hl_color, t * 3 + 0.5)

    # === Gas Comparison ===
    cmp_y = flow_y + 56
    draw.line((30, cmp_y, 770, cmp_y), fill=BORDER, width=1)
    draw.text((40, cmp_y + 8), "Gas Cost: Precompile vs EVM Bytecode", font=font_header, fill=YELLOW)

    bar_y = cmp_y + 30
    # Precompile bar
    max_bar = 600
    pc_gas = hl_gas
    evm_gas = hl_gas * 15  # EVM equivalent is ~15x more expensive
    scale = max_bar / evm_gas if evm_gas > 0 else 1

    pc_w = max(30, int(pc_gas * scale))
    evm_w = max(30, int(evm_gas * scale))

    draw_rounded_rect(draw, (150, bar_y, 150 + pc_w, bar_y + 22), fill=GREEN_BG, outline=GREEN, radius=4)
    draw.text((40, bar_y + 3), "Precompile", font=font_small, fill=GREEN)
    draw.text((155, bar_y + 3), f"{pc_gas} gas", font=font_small, fill=GREEN)

    draw_rounded_rect(draw, (150, bar_y + 30, 150 + evm_w, bar_y + 52), fill=RED_BG, outline=RED, radius=4)
    draw.text((40, bar_y + 33), "EVM equiv.", font=font_small, fill=RED)
    draw.text((155, bar_y + 33), f"~{evm_gas} gas", font=font_small, fill=RED)

    # Savings
    savings = ((evm_gas - pc_gas) / evm_gas) * 100
    sav_pulse = lerp_color(DIM, GREEN, 0.5 + 0.5 * math.sin(t * math.pi * 2))
    draw.text((150 + evm_w + 10, bar_y + 14), f"{savings:.0f}% cheaper", font=font_body, fill=sav_pulse)

    # === Why Precompiles ===
    why_y = bar_y + 62
    draw.line((30, why_y, 770, why_y), fill=BORDER, width=1)
    reasons = [
        ("Cryptography", "Complex math ops needed\nby many contracts", CYAN, CYAN_BG),
        ("Performance", "Native code runs 10-100x\nfaster than EVM", GREEN, GREEN_BG),
        ("Gas Efficiency", "Fixed low gas cost\nfor heavy operations", YELLOW, YELLOW_BG),
    ]

    rx = 40
    for label, desc, color, bg in reasons:
        rbox = (rx, why_y + 8, rx + 232, why_y + 56)
        draw_rounded_rect(draw, rbox, fill=bg, outline=color)
        draw.text((rx + 10, why_y + 12), label, font=font_body, fill=color)
        lines = desc.split("\n")
        for j, line in enumerate(lines):
            draw.text((rx + 10, why_y + 28 + j * 13), line, font=font_tiny, fill=DIM)
        rx += 242

    # Bottom note
    draw.text((40, 530), "Precompiles: native performance at EVM-accessible addresses", font=font_small, fill=DIM)

    return img


if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print(f"Saved {OUT}")
