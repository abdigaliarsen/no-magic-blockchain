"""
Variant C: "Solana vs Ethereum"
Side-by-side: Ethereum (contract = code + storage) vs Solana (program = code only, separate accounts).
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- Config ---
W, H = 800, 550
FRAMES = 36
DELAY = 90
OUT = "assets/gifs/solana_03_programs.gif"

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

try:
    font_bold_26 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    font_bold_16 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    font_bold_14 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    font_bold_12 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
    font_12 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    font_10 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except Exception:
    font_bold_26 = ImageFont.load_default()
    font_bold_16 = font_bold_26
    font_bold_14 = font_bold_26
    font_bold_12 = font_bold_26
    font_12 = font_bold_26
    font_10 = font_bold_26


def text_center(draw, x, y, text, font, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((x - tw // 2, y - th // 2), text, font=font, fill=fill)


def rounded_rect(draw, box, fill, outline, r=8):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=2)


def draw_arrow_v(draw, x, y1, y2, color, t_frac):
    draw.line([(x, y1), (x, y2)], fill=color, width=2)
    d = 8 if y2 > y1 else -8
    draw.polygon([(x, y2), (x - 5, y2 - d), (x + 5, y2 - d)], fill=color)
    sy = y1 + (y2 - y1) * t_frac
    draw.ellipse([x - 4, sy - 4, x + 4, sy + 4], fill=color)


def draw_scan_h(draw, x1, x2, y, color, t_frac):
    """Horizontal scan line."""
    sx = x1 + (x2 - x1) * t_frac
    draw.line([(sx, y - 20), (sx, y + 20)], fill=color, width=2)


def make_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = fi / (FRAMES - 1)

    # --- Title ---
    text_center(draw, W // 2, 28, "Solana vs Ethereum: Program Model", font_bold_26, CYAN)
    draw.line([(60, 50), (W - 60, 50)], fill=BORDER, width=1)

    # --- Dividing line (vertical center) ---
    cx = W // 2
    draw.line([(cx, 60), (cx, H - 40)], fill=BORDER, width=2)

    # =============================================
    # LEFT SIDE: Ethereum
    # =============================================
    lmid = cx // 2
    text_center(draw, lmid, 68, "Ethereum", font_bold_16, PURPLE)

    # Smart Contract box (code + storage combined)
    scx, scy = 30, 95
    scw, sch = cx - 60, 200
    rounded_rect(draw, [scx, scy, scx + scw, scy + sch], PURPLE_BG, PURPLE)
    text_center(draw, lmid, scy + 18, "Smart Contract", font_bold_14, PURPLE)
    draw.line([(scx + 10, scy + 32), (scx + scw - 10, scy + 32)], fill=BORDER, width=1)

    # Code section inside contract
    code_y = scy + 40
    rounded_rect(draw, [scx + 12, code_y, scx + scw - 12, code_y + 60], DARK_BOX, BORDER, r=4)
    text_center(draw, lmid, code_y + 12, "Code (bytecode)", font_bold_12, WHITE)
    draw.text((scx + 22, code_y + 28), "function transfer()", font=font_10, fill=DIM)
    draw.text((scx + 22, code_y + 42), "function balanceOf()", font=font_10, fill=DIM)

    # Storage section inside contract
    stor_y = code_y + 70
    rounded_rect(draw, [scx + 12, stor_y, scx + scw - 12, stor_y + 80], DARK_BOX, RED, r=4)
    text_center(draw, lmid, stor_y + 12, "Storage (state)", font_bold_12, RED)
    draw.text((scx + 22, stor_y + 28), "slot[0]: totalSupply", font=font_10, fill=DIM)
    draw.text((scx + 22, stor_y + 44), "slot[1]: balances map", font=font_10, fill=DIM)
    draw.text((scx + 22, stor_y + 60), "slot[2]: allowances", font=font_10, fill=DIM)

    # Scan line inside the contract
    draw_scan_h(draw, scx + 12, scx + scw - 12, scy + sch // 2, PURPLE, t)

    # Label: "Tightly coupled"
    lbl_y = scy + sch + 15
    rounded_rect(draw, [scx + 20, lbl_y, scx + scw - 20, lbl_y + 28], RED_BG, RED, r=6)
    text_center(draw, lmid, lbl_y + 14, "Code + State = Coupled", font_bold_12, RED)

    # Ethereum properties
    prop_y = lbl_y + 42
    props_eth = [
        ("Each contract owns its storage", DIM),
        ("State is internal, private", DIM),
        ("Deploy = new code + new storage", DIM),
        ("Upgrade = complex proxy pattern", ORANGE),
    ]
    for j, (txt, col) in enumerate(props_eth):
        draw.text((scx + 14, prop_y + j * 16), txt, font=font_10, fill=col)

    # =============================================
    # RIGHT SIDE: Solana
    # =============================================
    rmid = cx + (W - cx) // 2
    text_center(draw, rmid, 68, "Solana", font_bold_16, CYAN)

    # Program box (code only)
    spx = cx + 30
    spw = (W - cx) - 60
    spy = 95
    sph = 85
    rounded_rect(draw, [spx, spy, spx + spw, spy + sph], CYAN_BG, CYAN)
    text_center(draw, rmid, spy + 18, "Program (code only)", font_bold_14, CYAN)
    draw.line([(spx + 10, spy + 32), (spx + spw - 10, spy + 32)], fill=BORDER, width=1)
    draw.text((spx + 16, spy + 40), "fn process_instruction(", font=font_10, fill=WHITE)
    draw.text((spx + 16, spy + 54), "  accounts, data", font=font_10, fill=WHITE)
    draw.text((spx + 16, spy + 68), ")", font=font_10, fill=WHITE)

    # Separate account boxes
    acc_y = spy + sph + 55
    acw, ach = (spw - 20) // 2, 85
    acc_gap = 20

    # Arrow program -> accounts
    draw_arrow_v(draw, rmid - acw // 2 - acc_gap // 2 + acw // 2, spy + sph + 4, acc_y - 4, GREEN, t)
    draw_arrow_v(draw, rmid + acw // 2 + acc_gap // 2 - acw // 2 + acw // 2, spy + sph + 4, acc_y - 4, GREEN, t)

    # "operates on" label
    text_center(draw, rmid, spy + sph + 25, "operates on", font_10, DIM)

    # Account 1
    a1x = spx
    rounded_rect(draw, [a1x, acc_y, a1x + acw, acc_y + ach], GREEN_BG, GREEN, r=6)
    text_center(draw, a1x + acw // 2, acc_y + 14, "Data Account 1", font_bold_12, GREEN)
    draw.text((a1x + 10, acc_y + 32), "owner: Program", font=font_10, fill=DIM)
    draw.text((a1x + 10, acc_y + 48), "data: balance=1000", font=font_10, fill=WHITE)
    draw.text((a1x + 10, acc_y + 64), "lamports: 890880", font=font_10, fill=DIM)

    # Account 2
    a2x = spx + acw + acc_gap
    rounded_rect(draw, [a2x, acc_y, a2x + acw, acc_y + ach], GREEN_BG, GREEN, r=6)
    text_center(draw, a2x + acw // 2, acc_y + 14, "Data Account 2", font_bold_12, GREEN)
    draw.text((a2x + 10, acc_y + 32), "owner: Program", font=font_10, fill=DIM)
    draw.text((a2x + 10, acc_y + 48), "data: balance=200", font=font_10, fill=WHITE)
    draw.text((a2x + 10, acc_y + 64), "lamports: 890880", font=font_10, fill=DIM)

    # Label: "Decoupled"
    dlbl_y = acc_y + ach + 15
    rounded_rect(draw, [spx + 20, dlbl_y, spx + spw - 20, dlbl_y + 28], GREEN_BG, GREEN, r=6)
    text_center(draw, rmid, dlbl_y + 14, "Code / State = Decoupled", font_bold_12, GREEN)

    # Solana properties
    sprop_y = dlbl_y + 42
    props_sol = [
        ("Programs are stateless executables", DIM),
        ("State lives in separate accounts", DIM),
        ("Deploy = just upload new code", DIM),
        ("Upgrade = swap program binary", GREEN),
    ]
    for j, (txt, col) in enumerate(props_sol):
        draw.text((spx + 14, sprop_y + j * 16), txt, font=font_10, fill=col)

    # --- Bottom insight ---
    iy = H - 38
    draw.line([(40, iy - 8), (W - 40, iy - 8)], fill=BORDER, width=1)
    text_center(draw, W // 2, iy + 5, "Solana separates code from state -- enabling parallel execution", font_bold_14, YELLOW)

    # Scan dot on bottom text
    scan_x = int(100 + (W - 200) * t)
    draw.ellipse([scan_x - 3, iy - 3, scan_x + 3, iy + 3], fill=YELLOW)

    return img


frames = [make_frame(i) for i in range(FRAMES)]
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=DELAY, loop=0)
print(f"Saved {OUT} ({len(frames)} frames)")
