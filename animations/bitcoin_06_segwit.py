"""BTC06-B: The Malleability Fix — SegWit excludes witness from txid calculation."""
from PIL import Image, ImageDraw, ImageFont
import math, os, hashlib

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
RED_BG = (50, 20, 20)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
PANEL = (17, 21, 28)
YELLOW_BG = (58, 50, 14)

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
mono_font = load_font(11)

def text_w(draw, txt, font):
    bb = draw.textbbox((0,0), txt, font=font)
    return bb[2] - bb[0]

def draw_rounded_box(draw, x, y, w, h, fill, border_col, r=8):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=r, fill=fill, outline=border_col, width=2)

def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    pulse = 0.5 + 0.5 * math.sin(f * 2 * math.pi / FRAMES)

    # Title
    title = "The Malleability Fix"
    tw = text_w(draw, title, title_font)
    draw.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)

    # Divider
    mid_x = W // 2
    draw.line([(mid_x, 48), (mid_x, 430)], fill=BORDER, width=2)

    # === LEFT: Legacy Problem ===
    lx = 25
    draw.text((lx + 50, 50), "LEGACY (Problem)", fill=RED, font=header_font)

    # TX box
    tx_y = 80
    draw_rounded_box(draw, lx, tx_y, 350, 110, DARK_BOX, RED)
    draw.text((lx + 10, tx_y + 8), "Transaction Data", fill=WHITE, font=body_font)
    draw.text((lx + 20, tx_y + 30), "inputs + outputs + ...", fill=DIM, font=small_font)

    # Signature inside the tx
    sig_pulse = tuple(int(c * (0.6 + 0.4 * pulse)) for c in RED)
    draw_rounded_box(draw, lx + 20, tx_y + 50, 310, 30, RED_BG, sig_pulse, 4)
    # Cycling signature bytes
    sig_shift = f % 16
    draw.text((lx + 30, tx_y + 56), f"scriptSig: 3045022100{sig_shift:x}f8a...{(sig_shift+3)%16:x}e2", fill=RED, font=mono_font)

    # Arrow to hash
    draw.text((lx + 80, tx_y + 118), "Hash(ALL of above)", fill=DIM, font=small_font)
    draw.line([(lx + 175, tx_y + 115), (lx + 175, tx_y + 140)], fill=RED, width=2)
    draw.polygon([(lx+175, tx_y+145), (lx+170, tx_y+138), (lx+180, tx_y+138)], fill=RED)

    # TxID box - changes with signature
    txid_y = tx_y + 148
    h1 = hashlib.sha256(f"legacy-sig-{sig_shift}".encode()).hexdigest()[:16]
    txid_col = RED if f % 6 < 3 else ORANGE  # Flickering to show instability
    draw_rounded_box(draw, lx + 40, txid_y, 280, 35, RED_BG, txid_col)
    draw.text((lx + 50, txid_y + 4), "TxID:", fill=DIM, font=small_font)
    draw.text((lx + 50, txid_y + 17), f"{h1}...", fill=txid_col, font=mono_font)

    # Problem label
    prob_y = txid_y + 50
    draw_rounded_box(draw, lx, prob_y, 350, 55, RED_BG, RED)
    draw.text((lx + 10, prob_y + 5), "PROBLEM: Change sig bytes", fill=RED, font=header_font)
    draw.text((lx + 10, prob_y + 25), "= different TxID (same valid tx!)", fill=RED, font=body_font)
    draw.text((lx + 10, prob_y + 40), "Breaks chains of unconfirmed txs", fill=ORANGE, font=small_font)

    # === RIGHT: SegWit Solution ===
    rx = mid_x + 20
    draw.text((rx + 50, 50), "SEGWIT (Solution)", fill=GREEN, font=header_font)

    # TX box without witness
    draw_rounded_box(draw, rx, tx_y, 350, 70, DARK_BOX, GREEN)
    draw.text((rx + 10, tx_y + 8), "Transaction Data", fill=WHITE, font=body_font)
    draw.text((rx + 20, tx_y + 30), "inputs + outputs + ...", fill=DIM, font=small_font)
    draw.text((rx + 20, tx_y + 46), "(NO signature here)", fill=GREEN, font=small_font)

    # Separate witness box
    wit_y = tx_y + 80
    draw_rounded_box(draw, rx, wit_y, 350, 35, PURPLE_BG, PURPLE)
    wit_shift = f % 16
    draw.text((rx + 10, wit_y + 8), f"Witness: 3045022100{wit_shift:x}f8a...{(wit_shift+3)%16:x}e2", fill=PURPLE, font=mono_font)
    draw.text((rx + 280, wit_y + 8), "separate!", fill=YELLOW, font=small_font)

    # Arrow to hash (only tx data)
    draw.text((rx + 60, wit_y + 45), "Hash(tx data ONLY)", fill=DIM, font=small_font)
    draw.line([(rx + 175, wit_y + 42), (rx + 175, wit_y + 62)], fill=GREEN, width=2)
    draw.polygon([(rx+175, wit_y+67), (rx+170, wit_y+60), (rx+180, wit_y+60)], fill=GREEN)

    # Stable TxID
    stxid_y = wit_y + 70
    stable_hash = hashlib.sha256(b"segwit-stable").hexdigest()[:16]
    glow_green = tuple(int(c * (0.5 + 0.5 * pulse)) for c in GREEN)
    draw_rounded_box(draw, rx + 40, stxid_y, 280, 35, GREEN_BG, glow_green)
    draw.text((rx + 50, stxid_y + 4), "TxID:", fill=DIM, font=small_font)
    draw.text((rx + 50, stxid_y + 17), f"{stable_hash}...", fill=GREEN, font=mono_font)

    # Solution label
    sol_y = stxid_y + 50
    draw_rounded_box(draw, rx, sol_y, 350, 55, GREEN_BG, GREEN)
    draw.text((rx + 10, sol_y + 5), "FIXED: Sig excluded from TxID", fill=GREEN, font=header_font)
    draw.text((rx + 10, sol_y + 25), "= TxID is stable forever", fill=GREEN, font=body_font)
    draw.text((rx + 10, sol_y + 40), "Enables: Lightning, atomic swaps, etc.", fill=CYAN, font=small_font)

    # Status indicators below TxID boxes (not overlapping text)
    cross_pulse = int(255 * (0.6 + 0.4 * pulse))
    draw.text((lx + 155, txid_y + 40), "UNSTABLE", fill=(cross_pulse, 50, 50), font=header_font)
    check_pulse = int(255 * (0.6 + 0.4 * pulse))
    draw.text((rx + 155, stxid_y + 40), "STABLE", fill=(20, check_pulse, 80), font=header_font)

    # Bottom
    draw_rounded_box(draw, 20, 460, 760, 70, PANEL, BORDER)
    draw.text((40, 468), "Malleability = ability to change tx appearance without invalidating it", fill=YELLOW, font=header_font)
    draw.text((40, 490), "SegWit separates witness (signature) data so it can't affect the transaction ID.", fill=WHITE, font=body_font)
    draw.text((40, 508), "This was critical for building Layer 2 protocols like Lightning Network.", fill=DIM, font=body_font)

    return img

if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save("assets/gifs/bitcoin_06_segwit.gif", save_all=True,
                   append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_06_segwit.gif")
