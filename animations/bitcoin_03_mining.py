"""Bitcoin Mining Block Assembly animation."""
from PIL import Image, ImageDraw, ImageFont
import math

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
YELLOW_BG = (58, 50, 14)
RED = (248, 113, 113)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
PURPLE = (167, 139, 250)
PURPLE_BG = (35, 28, 58)

def load_font(size, bold=False):
    for p in (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"] if bold else
              ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]):
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()

def load_mono(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(14, True)
body_font = load_font(12)
small_font = load_font(10)
mono_font = load_mono(11)
mono_sm = load_mono(9)

def marching_arrow_v(draw, x, y0, y1, color, frame, w=2):
    dash = 6
    total = abs(y1 - y0)
    dy = 1 if y1 > y0 else -1
    offset = (frame * 3) % (dash * 2)
    d = -offset
    while d < total:
        s = max(0, d)
        e = min(total, d + dash)
        if e > s and int(d / dash) % 2 == 0:
            draw.line([(x, y0 + dy * s), (x, y0 + dy * e)], fill=color, width=w)
        d += dash * 2
    draw.polygon([(x, y1), (x - 5, y1 - dy * 8), (x + 5, y1 - dy * 8)], fill=color)

if __name__ == "__main__":
    frames_list = []
    for f in range(FRAMES):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        t = f / FRAMES
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)

        draw.text((W // 2, 20), "Bitcoin Mining: Block Assembly", fill=CYAN, font=title_font, anchor="mt")

        # Row 1: Transactions
        tx_y = 60
        # Coinbase
        draw.rounded_rectangle((50, tx_y, 200, tx_y + 55), radius=6, fill=YELLOW_BG, outline=YELLOW, width=2)
        draw.text((125, tx_y + 12), "Coinbase Tx", fill=YELLOW, font=header_font, anchor="mt")
        draw.text((125, tx_y + 32), "6.25 BTC reward", fill=WHITE, font=small_font, anchor="mt")

        # Regular txs
        txs = [("Tx1: A->B", 240), ("Tx2: C->D", 390), ("Tx3: E->F", 540)]
        for label, x in txs:
            draw.rounded_rectangle((x, tx_y, x + 130, tx_y + 55), radius=6, fill=CYAN_BG, outline=CYAN)
            draw.text((x + 65, tx_y + 12), label, fill=CYAN, font=mono_font, anchor="mt")
            draw.text((x + 65, tx_y + 32), "0.001 fee", fill=DIM, font=small_font, anchor="mt")

        # Arrows down to Merkle root
        for x in [125, 305, 455, 605]:
            marching_arrow_v(draw, x, tx_y + 57, tx_y + 85, DIM, f)

        # Row 2: Merkle Root
        mk_y = tx_y + 88
        draw.rounded_rectangle((200, mk_y, 560, mk_y + 40), radius=6, fill=PURPLE_BG, outline=PURPLE)
        draw.text((380, mk_y + 10), "Merkle Root: a3f2...8b1c", fill=PURPLE, font=mono_font, anchor="mt")

        # Arrow down to block header
        marching_arrow_v(draw, 380, mk_y + 42, mk_y + 65, PURPLE, f)

        # Row 3: Block Header
        hdr_y = mk_y + 68
        draw.rounded_rectangle((100, hdr_y, 660, hdr_y + 140), radius=10, fill=DARK_BOX, outline=ORANGE, width=2)
        draw.text((380, hdr_y + 12), "Block Header (80 bytes)", fill=ORANGE, font=header_font, anchor="mt")

        fields = [
            ("version:", "0x20000000", CYAN),
            ("prev_hash:", "00000000000000000003a1...", CYAN),
            ("merkle_root:", "a3f2...8b1c", PURPLE),
            ("timestamp:", "2024-01-15 14:23:07", DIM),
            ("bits:", "0x17034219 (difficulty)", DIM),
            ("nonce:", f"{(f * 7919 + 12345) % 999999:06d}", YELLOW),
        ]
        for i, (name, val, col) in enumerate(fields):
            row = i // 2
            col_idx = i % 2
            x = 120 + col_idx * 280
            y = hdr_y + 35 + row * 22
            draw.text((x, y), name, fill=DIM, font=mono_sm)
            draw.text((x + 90, y), val, fill=col, font=mono_sm)

        # Nonce cycling effect
        nonce_y = hdr_y + 35 + 2 * 22
        nonce_x = 120 + 1 * 280 + 90
        cycling = f"{(f * 7919 + 12345) % 999999:06d}"

        # Arrow to double hash
        hash_y = hdr_y + 145
        marching_arrow_v(draw, 380, hdr_y + 142, hash_y + 5, ORANGE, f)

        # Row 4: Double SHA-256
        draw.rounded_rectangle((200, hash_y + 8, 560, hash_y + 48), radius=6, fill=PANEL, outline=YELLOW)
        draw.text((380, hash_y + 18), "SHA-256( SHA-256( header ) )", fill=YELLOW, font=mono_font, anchor="mt")

        # Arrow to result
        marching_arrow_v(draw, 380, hash_y + 50, hash_y + 72, YELLOW, f)

        # Row 5: Result hash
        res_y = hash_y + 75
        # Simulated hash that starts with zeros
        hash_prefix = "0000000000000000"
        hash_rest = f"{(f * 31337) % 0xFFFFFFFF:08x}{'a1b2c3d4e5f6'}"
        result_hash = hash_prefix + hash_rest[:48]

        valid = True
        border_col = GREEN if valid else RED
        glow = int(100 + 155 * pulse)
        draw.rounded_rectangle((80, res_y, 680, res_y + 45), radius=6, fill=GREEN_BG,
                               outline=(52, glow, 153), width=2)
        draw.text((380, res_y + 8), f"Hash: {result_hash[:40]}...", fill=WHITE, font=mono_sm, anchor="mt")
        # Highlight leading zeros
        draw.text((116, res_y + 8), f"Hash: {hash_prefix}", fill=GREEN, font=mono_sm)
        draw.text((380, res_y + 28), "Starts with enough zeros = VALID BLOCK!", fill=GREEN, font=small_font, anchor="mt")

        # Bottom summary
        draw.rounded_rectangle((50, H - 70, 750, H - 15), radius=8, fill=PANEL, outline=BORDER)
        draw.text((400, H - 55), "Miner increments nonce until hash < target difficulty", fill=WHITE, font=body_font, anchor="mt")
        draw.text((400, H - 35), "Block reward (6.25 BTC) + transaction fees go to miner's coinbase tx", fill=DIM, font=small_font, anchor="mt")

        frames_list.append(img)

    frames_list[0].save("assets/gifs/bitcoin_03_mining.gif", save_all=True, append_images=frames_list[1:], duration=DUR, loop=0, optimize=True)
    print("Saved assets/gifs/bitcoin_03_mining.gif")
