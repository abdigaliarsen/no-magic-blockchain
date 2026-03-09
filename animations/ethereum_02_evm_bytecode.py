"""
EVM Bytecode - Variant B: Architecture Overview
EVM architecture diagram: Bytecode -> Stack + Memory + Storage side by side.
"""
from PIL import Image, ImageDraw, ImageFont

# --- Constants ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
BG = (13, 17, 23)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
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
YELLOW_BG = (58, 50, 14)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)


def load_fonts():
    fonts = {}
    try:
        fonts["title"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
        fonts["header"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        fonts["body"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        fonts["small"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        fonts["big"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except OSError:
        f = ImageFont.load_default()
        fonts = {"title": f, "header": f, "body": f, "small": f, "big": f}
    return fonts


FONTS = load_fonts()


def rr(draw, xy, fill, outline, radius=8):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def draw_dashed_arrow(draw, x0, y0, x1, y1, color, frame_idx, horizontal=True):
    """Draw animated dashed arrow."""
    scan = (frame_idx * 4) % 16
    length = abs(x1 - x0) if horizontal else abs(y1 - y0)
    for seg in range(0, int(length), 10):
        if (seg + scan) % 20 < 10:
            frac0 = seg / max(length, 1)
            frac1 = min((seg + 5) / max(length, 1), 1.0)
            if horizontal:
                draw.line((x0 + (x1 - x0) * frac0, y0, x0 + (x1 - x0) * frac1, y1), fill=color, width=2)
            else:
                draw.line((x0, y0 + (y1 - y0) * frac0, x1, y0 + (y1 - y0) * frac1), fill=color, width=2)
    # Arrowhead
    if horizontal:
        dx = 1 if x1 > x0 else -1
        draw.polygon([(x1, y1 - 5), (x1 - 8 * dx, y1), (x1, y1 + 5)], fill=color)
    else:
        dy = 1 if y1 > y0 else -1
        draw.polygon([(x1 - 5, y1), (x1, y1 + 8 * dy), (x1 + 5, y1)], fill=color)


def draw_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # --- Title ---
    draw.text((W // 2, 28), "EVM Architecture", fill=WHITE, font=FONTS["title"], anchor="mm")
    draw.text((W // 2, 52), "Bytecode execution with three data regions", fill=DIM, font=FONTS["small"], anchor="mm")

    # --- Bytecode box (top-left) ---
    bx, by, bw, bh = 50, 80, 180, 150
    rr(draw, (bx, by, bx + bw, by + bh), PANEL, CYAN)
    draw.text((bx + bw // 2, by + 18), "BYTECODE", fill=CYAN, font=FONTS["header"], anchor="mm")
    draw.line((bx + 12, by + 34, bx + bw - 12, by + 34), fill=BORDER, width=1)

    opcodes = ["60 03  PUSH1 3", "60 05  PUSH1 5", "01     ADD", "52     MSTORE"]
    for i, op in enumerate(opcodes):
        oy = by + 48 + i * 26
        rr(draw, (bx + 12, oy, bx + bw - 12, oy + 22), DARK_BOX, BORDER)
        draw.text((bx + bw // 2, oy + 11), op, fill=DIM, font=FONTS["small"], anchor="mm")

    # Animated scan line over bytecode
    scan_y = by + 48 + ((fi * 3) % (bh - 60))
    draw.line((bx + 12, scan_y, bx + bw - 12, scan_y), fill=CYAN, width=1)

    # --- EVM Processor box (center) ---
    px, py, pw, ph = 290, 80, 200, 150
    rr(draw, (px, py, px + pw, py + ph), PANEL, YELLOW)
    draw.text((px + pw // 2, py + 18), "EVM PROCESSOR", fill=YELLOW, font=FONTS["header"], anchor="mm")
    draw.line((px + 12, py + 34, px + pw - 12, py + 34), fill=BORDER, width=1)

    # Processor internals
    labels = [("PC", "Program Counter"), ("GAS", "Gas Meter"), ("SP", "Stack Pointer")]
    for i, (short, desc) in enumerate(labels):
        ly = py + 48 + i * 34
        rr(draw, (px + 12, ly, px + 60, ly + 26), YELLOW_BG, YELLOW)
        draw.text((px + 36, ly + 13), short, fill=YELLOW, font=FONTS["body"], anchor="mm")
        draw.text((px + 70, ly + 13), desc, fill=DIM, font=FONTS["small"], anchor="lm")

    # --- Arrow: Bytecode -> Processor ---
    draw_dashed_arrow(draw, bx + bw + 8, by + bh // 2, px - 8, py + ph // 2, CYAN, fi)

    # === Three data regions (bottom row) ===
    regions = [
        {
            "title": "STACK",
            "color": GREEN,
            "bg": GREEN_BG,
            "x": 50,
            "type": "LIFO",
            "desc": "1024 deep",
            "items": ["0x08 (8)", "0x03 (3)", "---", "---"],
        },
        {
            "title": "MEMORY",
            "color": PURPLE,
            "bg": PURPLE_BG,
            "x": 290,
            "type": "Byte Array",
            "desc": "Expandable",
            "items": ["0x00: 00 00 00", "0x20: 00 08 00", "0x40: 00 00 00", "0x60: 00 00 00"],
        },
        {
            "title": "STORAGE",
            "color": ORANGE,
            "bg": (50, 35, 15),
            "x": 540,
            "type": "Key-Value",
            "desc": "Persistent",
            "items": ["slot0: 0x00", "slot1: 0xFF", "slot2: 0x00", "slot3: 0x00"],
        },
    ]

    ry = 275
    rw = 210
    rh = 230

    for reg in regions:
        rx = reg["x"]
        rr(draw, (rx, ry, rx + rw, ry + rh), PANEL, reg["color"])
        draw.text((rx + rw // 2, ry + 18), reg["title"], fill=reg["color"], font=FONTS["big"], anchor="mm")
        draw.line((rx + 12, ry + 34, rx + rw - 12, ry + 34), fill=BORDER, width=1)

        # Type badge
        rr(draw, (rx + 12, ry + 44, rx + 90, ry + 62), reg["bg"], reg["color"])
        draw.text((rx + 51, ry + 53), reg["type"], fill=reg["color"], font=FONTS["small"], anchor="mm")
        draw.text((rx + 100, ry + 53), reg["desc"], fill=DIM, font=FONTS["small"], anchor="lm")

        # Items
        for i, item in enumerate(reg["items"]):
            iy = ry + 75 + i * 36
            rr(draw, (rx + 12, iy, rx + rw - 12, iy + 28), DARK_BOX, BORDER)
            draw.text((rx + rw // 2, iy + 14), item, fill=DIM, font=FONTS["small"], anchor="mm")

    # --- Arrows from Processor down to each region ---
    proc_bottom = py + ph
    for i, reg in enumerate(regions):
        rx = reg["x"]
        target_x = rx + rw // 2
        draw_dashed_arrow(draw, px + pw // 2, proc_bottom + 5, px + pw // 2, proc_bottom + 20, YELLOW, fi, horizontal=False)

    # Horizontal distribution line
    hl_y = proc_bottom + 28
    draw.line((50 + rw // 2, hl_y, 540 + rw // 2, hl_y), fill=BORDER, width=2)
    for reg in regions:
        rx = reg["x"] + rw // 2
        # Vertical drop from horizontal line to region
        draw_dashed_arrow(draw, rx, hl_y, rx, ry - 5, reg["color"], fi, horizontal=False)

    # --- Right info box ---
    ix, iy2 = 540, 80
    iw2, ih2 = 210, 150
    rr(draw, (ix, iy2, ix + iw2, iy2 + ih2), PANEL, PURPLE)
    draw.text((ix + iw2 // 2, iy2 + 18), "EXECUTION MODEL", fill=PURPLE, font=FONTS["header"], anchor="mm")
    draw.line((ix + 12, iy2 + 34, ix + iw2 - 12, iy2 + 34), fill=BORDER, width=1)

    facts = [
        "256-bit word size",
        "Big-endian byte order",
        "Deterministic execution",
        "Metered by gas",
    ]
    for i, fact in enumerate(facts):
        fy = iy2 + 48 + i * 26
        draw.text((ix + 20, fy), ">", fill=PURPLE, font=FONTS["body"])
        draw.text((ix + 35, fy), fact, fill=DIM, font=FONTS["small"])

    # --- Bottom scan line ---
    scan_x = 30 + ((fi * 7) % (W - 60))
    draw.line((scan_x, H - 15, scan_x + 40, H - 15), fill=(*CYAN[:3],), width=2)

    return img


def main():
    frames = [draw_frame(i) for i in range(FRAMES)]
    frames[0].save(
        "assets/gifs/ethereum_02_evm_bytecode.gif",
        save_all=True,
        append_images=frames[1:],
        duration=DELAY,
        loop=0,
        optimize=True,
    )
    print("Saved assets/gifs/ethereum_02_evm_bytecode.gif")


if __name__ == "__main__":
    main()
