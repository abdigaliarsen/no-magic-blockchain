"""
Smart Contracts GIF Variant C: Deploy vs Call
Side-by-side comparison: Deployment transaction vs Call transaction.
Shows the structural difference visually.
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- Config ---
W, H = 800, 550
FRAMES = 36
DELAY = 90

# --- Colors ---
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

# --- Fonts ---
def load_fonts():
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    fonts = {}
    try:
        fonts["title"] = ImageFont.truetype(paths[0], 26)
        fonts["header"] = ImageFont.truetype(paths[0], 14)
        fonts["body"] = ImageFont.truetype(paths[1], 12)
        fonts["small"] = ImageFont.truetype(paths[1], 10)
    except Exception:
        fb = ImageFont.load_default()
        fonts = {"title": fb, "header": fb, "body": fb, "small": fb}
    return fonts

FONTS = load_fonts()

def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def draw_rounded_rect(draw, xy, fill, outline, r=8):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)

def draw_arrow_v(draw, x, y0, y1, color, frame, phase=0):
    """Vertical arrow with traveling dot."""
    draw.line([(x, y0), (x, y1)], fill=color, width=2)
    d = 8 if y1 > y0 else -8
    draw.polygon([(x, y1), (x - 5, y1 - d), (x + 5, y1 - d)], fill=color)
    t = ((frame + phase) % 18) / 18.0
    ay = y0 + (y1 - y0) * t
    draw.ellipse([x - 3, ay - 3, x + 3, ay + 3], fill=color)

def draw_scan_line(draw, box_xy, frame, color, period=18):
    x0, y0, x1, y1 = box_xy
    h = y1 - y0
    t = (frame % period) / period
    sy = y0 + int(h * t)
    draw.line([(x0 + 2, sy), (x1 - 2, sy)], fill=color, width=1)

def render_frame(frame):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Title
    title = "Deploy vs Call Transaction"
    tw, _ = text_size(draw, title, FONTS["title"])
    draw.text(((W - tw) // 2, 14), title, fill=WHITE, font=FONTS["title"])

    # Vertical separator
    mid_x = W // 2
    for yy in range(55, H - 30, 8):
        draw.line([(mid_x, yy), (mid_x, yy + 3)], fill=BORDER, width=1)

    # Column headers
    dh = "DEPLOY (create)"
    ch = "CALL (execute)"
    dw, _ = text_size(draw, dh, FONTS["header"])
    cw, _ = text_size(draw, ch, FONTS["header"])
    draw.text(((mid_x - dw) // 2, 54), dh, fill=CYAN, font=FONTS["header"])
    draw.text((mid_x + (mid_x - cw) // 2, 54), ch, fill=GREEN, font=FONTS["header"])

    # ============ LEFT SIDE: DEPLOY ============
    lx = 30  # left margin
    lw_col = mid_x - 50  # column width

    # Transaction box
    tx_y = 82
    tx_h = 140
    draw_rounded_rect(draw, (lx, tx_y, lx + lw_col, tx_y + tx_h), CYAN_BG, CYAN, r=6)
    draw.text((lx + 12, tx_y + 8), "Transaction", fill=CYAN, font=FONTS["header"])

    fields_deploy = [
        ("from:", "0xDEPLOYER...", WHITE),
        ("to:", "(empty / null)", ORANGE),
        ("value:", "0 ETH", DIM),
        ("data:", "0x6080604052...", CYAN),
        ("", "(full bytecode)", DIM),
    ]
    for i, (k, v, c) in enumerate(fields_deploy):
        yy = tx_y + 32 + i * 18
        if k:
            draw.text((lx + 16, yy), k, fill=DIM, font=FONTS["body"])
            draw.text((lx + 65, yy), v, fill=c, font=FONTS["body"])
        else:
            draw.text((lx + 65, yy), v, fill=c, font=FONTS["small"])

    # Highlight "to: null" with pulsing box
    pulse = int(30 * math.sin(frame * 0.3))
    oc = (251, min(255, 146 + pulse), 60)
    draw.rectangle([lx + 60, tx_y + 47, lx + lw_col - 16, tx_y + 63], outline=oc, width=1)

    # Arrow down
    arrow_y0 = tx_y + tx_h + 8
    arrow_y1 = arrow_y0 + 50
    draw_arrow_v(draw, lx + lw_col // 2, arrow_y0, arrow_y1, CYAN, frame, 0)

    # EVM box
    evm_y = arrow_y1 + 8
    evm_h = 60
    draw_rounded_rect(draw, (lx, evm_y, lx + lw_col, evm_y + evm_h), DARK_BOX, CYAN, r=6)
    draw.text((lx + 12, evm_y + 8), "EVM: init code", fill=CYAN, font=FONTS["header"])
    draw.text((lx + 12, evm_y + 30), "Executes constructor", fill=WHITE, font=FONTS["body"])
    draw.text((lx + 12, evm_y + 46), "Returns runtime code", fill=DIM, font=FONTS["small"])
    draw_scan_line(draw, (lx, evm_y, lx + lw_col, evm_y + evm_h), frame, CYAN, 20)

    # Arrow down
    a2_y0 = evm_y + evm_h + 8
    a2_y1 = a2_y0 + 50
    draw_arrow_v(draw, lx + lw_col // 2, a2_y0, a2_y1, CYAN, frame, 6)

    # Result: new contract
    res_y = a2_y1 + 8
    res_h = 90
    draw_rounded_rect(draw, (lx, res_y, lx + lw_col, res_y + res_h), PURPLE_BG, PURPLE, r=6)
    draw.text((lx + 12, res_y + 8), "New Contract Created", fill=PURPLE, font=FONTS["header"])
    draw.text((lx + 12, res_y + 32), "addr: 0xC0N7..AC7", fill=WHITE, font=FONTS["body"])
    draw.text((lx + 12, res_y + 52), "code: stored on-chain", fill=DIM, font=FONTS["small"])
    draw.text((lx + 12, res_y + 68), "storage: initialized", fill=DIM, font=FONTS["small"])
    # Glow effect
    glow = int(20 * math.sin(frame * 0.25))
    gc = (167, min(255, 139 + glow), 250)
    draw.rounded_rectangle((lx - 1, res_y - 1, lx + lw_col + 1, res_y + res_h + 1),
                           radius=7, outline=gc, width=2)

    # ============ RIGHT SIDE: CALL ============
    rx = mid_x + 20
    rw_col = mid_x - 50

    # Transaction box
    draw_rounded_rect(draw, (rx, tx_y, rx + rw_col, tx_y + tx_h), GREEN_BG, GREEN, r=6)
    draw.text((rx + 12, tx_y + 8), "Transaction", fill=GREEN, font=FONTS["header"])

    fields_call = [
        ("from:", "0xUSER..ADDR", WHITE),
        ("to:", "0xC0N7..AC7", GREEN),
        ("value:", "0 ETH", DIM),
        ("data:", "0xd09de08a", YELLOW),
        ("", "(func selector)", DIM),
    ]
    for i, (k, v, c) in enumerate(fields_call):
        yy = tx_y + 32 + i * 18
        if k:
            draw.text((rx + 16, yy), k, fill=DIM, font=FONTS["body"])
            draw.text((rx + 65, yy), v, fill=c, font=FONTS["body"])
        else:
            draw.text((rx + 65, yy), v, fill=c, font=FONTS["small"])

    # Highlight "to: contract" with pulsing box
    pulse2 = int(30 * math.sin(frame * 0.3 + 1))
    gc2 = (52, min(255, 180 + pulse2), 153)
    draw.rectangle([rx + 60, tx_y + 47, rx + rw_col - 16, tx_y + 63], outline=gc2, width=1)

    # Arrow down
    draw_arrow_v(draw, rx + rw_col // 2, arrow_y0, arrow_y1, GREEN, frame, 3)

    # EVM box
    draw_rounded_rect(draw, (rx, evm_y, rx + rw_col, evm_y + evm_h), DARK_BOX, GREEN, r=6)
    draw.text((rx + 12, evm_y + 8), "EVM: runtime code", fill=GREEN, font=FONTS["header"])
    draw.text((rx + 12, evm_y + 30), "Match selector -> fn", fill=WHITE, font=FONTS["body"])
    draw.text((rx + 12, evm_y + 46), "Execute function body", fill=DIM, font=FONTS["small"])
    draw_scan_line(draw, (rx, evm_y, rx + rw_col, evm_y + evm_h), frame, GREEN, 20)

    # Arrow down
    draw_arrow_v(draw, rx + rw_col // 2, a2_y0, a2_y1, GREEN, frame, 9)

    # Result: state change
    draw_rounded_rect(draw, (rx, res_y, rx + rw_col, res_y + res_h), YELLOW_BG, YELLOW, r=6)
    draw.text((rx + 12, res_y + 8), "State Updated", fill=YELLOW, font=FONTS["header"])
    draw.text((rx + 12, res_y + 32), "slot[0]: 0 -> 1", fill=WHITE, font=FONTS["body"])
    draw.text((rx + 12, res_y + 52), "gas used: 43,250", fill=DIM, font=FONTS["small"])
    draw.text((rx + 12, res_y + 68), "receipt: success", fill=GREEN, font=FONTS["small"])

    # Glow on state result
    glow2 = int(20 * math.sin(frame * 0.25 + 2))
    yc = (250, min(255, 204 + glow2), 21)
    draw.rounded_rectangle((rx - 1, res_y - 1, rx + rw_col + 1, res_y + res_h + 1),
                           radius=7, outline=yc, width=2)

    # Bottom comparison labels
    labels = [
        ("to=null  ->  creates address", CYAN, lx + 30),
        ("to=addr  ->  executes code", GREEN, rx + 30),
    ]
    for text, color, x in labels:
        draw.text((x, H - 28), text, fill=color, font=FONTS["small"])

    return img

# --- Generate GIF ---
frames = [render_frame(f) for f in range(FRAMES)]
frames[0].save(
    "assets/gifs/ethereum_06_smart_contracts.gif",
    save_all=True,
    append_images=frames[1:],
    duration=DELAY,
    loop=0,
    optimize=True,
)
print("Saved assets/gifs/ethereum_06_smart_contracts.gif")
