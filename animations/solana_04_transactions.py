"""
Variant A: "Transaction Anatomy"
Shows a Solana transaction as a structured box with color-coded sections:
Signatures[], Message{Header, Account Keys[], Recent Blockhash, Instructions[]}
Animated scan line sweeps across the transaction structure.
"""

from PIL import Image, ImageDraw, ImageFont
import math

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

W, H = 800, 550
FRAMES = 36
DELAY = 90

# --- Fonts ---
try:
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    font_head = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except:
    font_title = ImageFont.load_default()
    font_head = ImageFont.load_default()
    font_body = ImageFont.load_default()
    font_small = ImageFont.load_default()


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def draw_rounded_rect(draw, xy, fill, outline, radius=6):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def draw_section_box(draw, x, y, w, h, label, fill, outline, label_color):
    """Draw a labeled section box."""
    draw_rounded_rect(draw, (x, y, x + w, y + h), fill=fill, outline=outline, radius=5)
    draw.text((x + 8, y + 4), label, fill=label_color, font=font_head)


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def generate_frame(frame_idx):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    t = frame_idx / FRAMES  # 0..1 normalized time

    # --- Title ---
    title = "Solana Transaction Anatomy"
    tw, _ = text_size(draw, title, font_title)
    draw.text(((W - tw) // 2, 14), title, fill=WHITE, font=font_title)

    # --- Outer transaction box ---
    tx_x, tx_y, tx_w, tx_h = 40, 55, 720, 470
    draw_rounded_rect(draw, (tx_x, tx_y, tx_x + tx_w, tx_y + tx_h),
                      fill=PANEL, outline=BORDER, radius=8)
    draw.text((tx_x + 12, tx_y + 6), "Transaction", fill=DIM, font=font_head)

    # ---- Section 1: Signatures (left column, top) ----
    sig_x, sig_y, sig_w, sig_h = 60, 85, 300, 120
    draw_section_box(draw, sig_x, sig_y, sig_w, sig_h,
                     "Signatures[]", PURPLE_BG, PURPLE, PURPLE)

    sigs = ["sig[0]: 7Fk3...a9Qm (fee payer)", "sig[1]: Bx2L...nR4p (authority)"]
    for i, s in enumerate(sigs):
        sy = sig_y + 28 + i * 38
        draw_rounded_rect(draw, (sig_x + 12, sy, sig_x + sig_w - 12, sy + 30),
                          fill=DARK_BOX, outline=BORDER, radius=4)
        draw.text((sig_x + 20, sy + 7), s, fill=PURPLE, font=font_body)

    # ---- Section 2: Message (right side spans full height) ----
    msg_x, msg_y, msg_w, msg_h = 380, 85, 360, 425
    draw_rounded_rect(draw, (msg_x, msg_y, msg_x + msg_w, msg_y + msg_h),
                      fill=DARK_BOX, outline=CYAN, radius=7)
    draw.text((msg_x + 10, msg_y + 6), "Message", fill=CYAN, font=font_head)

    # -- Header sub-box --
    hdr_x, hdr_y, hdr_w, hdr_h = msg_x + 14, msg_y + 30, msg_w - 28, 75
    draw_section_box(draw, hdr_x, hdr_y, hdr_w, hdr_h,
                     "Header", YELLOW_BG, YELLOW, YELLOW)
    hdr_lines = [
        "num_required_sigs: 2",
        "num_readonly_signed: 0",
        "num_readonly_unsigned: 1",
    ]
    for i, line in enumerate(hdr_lines):
        draw.text((hdr_x + 12, hdr_y + 24 + i * 16), line, fill=YELLOW, font=font_small)

    # -- Account Keys sub-box --
    ak_x, ak_y, ak_w, ak_h = msg_x + 14, hdr_y + hdr_h + 12, msg_w - 28, 110
    draw_section_box(draw, ak_x, ak_y, ak_w, ak_h,
                     "Account Keys[]", GREEN_BG, GREEN, GREEN)
    accts = [
        "[0] 9xQe...Fp2W  (signer, writable)",
        "[1] 3kMn...uT8v  (signer, writable)",
        "[2] 11111111...1111  (program)",
    ]
    for i, a in enumerate(accts):
        draw.text((ak_x + 12, ak_y + 26 + i * 24), a, fill=GREEN, font=font_small)

    # -- Recent Blockhash sub-box --
    bh_x, bh_y, bh_w, bh_h = msg_x + 14, ak_y + ak_h + 12, msg_w - 28, 48
    draw_section_box(draw, bh_x, bh_y, bh_w, bh_h,
                     "Recent Blockhash", RED_BG, RED, RED)
    draw.text((bh_x + 12, bh_y + 26), "GHtX...k9Lm  (slot 28401537)", fill=RED, font=font_small)

    # -- Instructions sub-box --
    ix_x, ix_y, ix_w, ix_h = msg_x + 14, bh_y + bh_h + 12, msg_w - 28, 130
    draw_section_box(draw, ix_x, ix_y, ix_w, ix_h,
                     "Instructions[]", CYAN_BG, ORANGE, ORANGE)
    instr_lines = [
        "ix[0]: program_id_idx=2",
        "       accounts=[0, 1]",
        "       data=CreateAccount{..}",
        "ix[1]: program_id_idx=2",
        "       accounts=[0, 1]",
        "       data=Transfer{lamports:1e9}",
    ]
    for i, line in enumerate(instr_lines):
        draw.text((ix_x + 12, ix_y + 26 + i * 16), line, fill=ORANGE, font=font_small)

    # ---- Arrow from Signatures to Message ----
    arr_x0 = sig_x + sig_w + 5
    arr_x1 = msg_x - 5
    arr_y = sig_y + sig_h // 2
    # Pulsing arrow
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)
    arr_col = lerp_color(DIM, PURPLE, pulse)
    draw.line([(arr_x0, arr_y), (arr_x1, arr_y)], fill=arr_col, width=2)
    draw.polygon([(arr_x1, arr_y), (arr_x1 - 8, arr_y - 5), (arr_x1 - 8, arr_y + 5)],
                 fill=arr_col)
    draw.text((arr_x0 + 4, arr_y - 16), "signs", fill=DIM, font=font_small)

    # ---- Legend (bottom-left) ----
    leg_y = 220
    draw.text((60, leg_y), "Legend:", fill=DIM, font=font_head)
    legend_items = [
        (PURPLE, "Signatures (Ed25519)"),
        (YELLOW, "Header (counts)"),
        (GREEN, "Account Keys (pubkeys)"),
        (RED, "Recent Blockhash"),
        (ORANGE, "Instructions (data)"),
    ]
    for i, (col, label) in enumerate(legend_items):
        ly = leg_y + 22 + i * 22
        draw.rounded_rectangle((66, ly, 82, ly + 14), radius=3, fill=col)
        draw.text((90, ly), label, fill=DIM, font=font_small)

    # ---- Animated scan line (horizontal, sweeps down the transaction) ----
    scan_y = tx_y + int((tx_h) * ((frame_idx % FRAMES) / FRAMES))
    scan_alpha = int(80 + 40 * math.sin(2 * math.pi * t))
    scan_col = (*CYAN[:3], )
    # Draw a faint horizontal highlight line
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.line([(tx_x + 2, scan_y), (tx_x + tx_w - 2, scan_y)],
            fill=(*CYAN, scan_alpha), width=2)
    # Blend
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # ---- Animated dot indicators on section labels ----
    # Small blinking dots next to each section to indicate "active"
    blink = int(3 + 3 * math.sin(2 * math.pi * t * 2))
    sections_dots = [
        (sig_x + sig_w - 18, sig_y + 8, PURPLE),
        (hdr_x + hdr_w - 18, hdr_y + 8, YELLOW),
        (ak_x + ak_w - 18, ak_y + 8, GREEN),
        (bh_x + bh_w - 18, bh_y + 8, RED),
        (ix_x + ix_w - 18, ix_y + 8, ORANGE),
    ]
    draw2 = ImageDraw.Draw(img)
    for dx, dy, col in sections_dots:
        draw2.ellipse((dx - blink, dy - blink, dx + blink, dy + blink), fill=col)

    # ---- Bottom bar: byte size indicator ----
    draw2.text((60, 510), "Serialized size: ~234 bytes", fill=DIM, font=font_small)
    bar_x, bar_y, bar_w = 240, 512, 200
    draw2.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + 12),
                            radius=3, fill=DARK_BOX, outline=BORDER)
    fill_w = int(bar_w * (0.5 + 0.5 * math.sin(2 * math.pi * t * 0.5)))
    if fill_w > 2:
        draw2.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + 12),
                                radius=3, fill=CYAN_BG)

    return img


frames = [generate_frame(i) for i in range(FRAMES)]
frames[0].save(
    "assets/gifs/solana_04_transactions.gif",
    save_all=True,
    append_images=frames[1:],
    duration=DELAY,
    loop=0,
    optimize=True,
)
print("Saved assets/gifs/solana_04_transactions.gif")
