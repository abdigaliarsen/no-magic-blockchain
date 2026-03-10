"""Versioned Transactions: Legacy vs v0 with Address Lookup Tables."""
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

OUT = "assets/gifs/solana_11_versioned_transactions.gif"

def load_font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for n in names:
        for p in [f"/usr/share/fonts/truetype/dejavu/{n}", f"/usr/share/fonts/truetype/liberation/{n}", f"/usr/share/fonts/{n}"]:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except (OSError, IOError): pass
    return ImageFont.load_default()

title_font = load_font(26, True)
header_font = load_font(15, True)
body_font = load_font(13)
small_font = load_font(11)
tiny_font = load_font(10)

def draw_rounded_rect(d, xy, fill, outline, r=8):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


# Sample addresses (shortened for display)
ADDRS = [
    "9WzD..q3Fk",
    "Vote..Prog",
    "Sys..Prog1",
    "Token..Prg",
    "ATA..xProg",
    "Sysv..Rent",
    "Sysv..Clok",
    "Pool..Addr",
    "User..Acct",
    "Dest..Acct",
]


def make_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    t = fi / (FRAMES - 1)

    # Title
    title = "Versioned Transactions"
    tw, _ = text_size(d, title, title_font)
    d.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)
    sub = "Address Lookup Tables reduce transaction size"
    sw, _ = text_size(d, sub, body_font)
    d.text(((W - sw) // 2, 44), sub, fill=DIM, font=body_font)

    # === LEFT: Legacy Transaction ===
    left_x, left_w = 25, 230
    panel_top, panel_bot = 68, 370
    draw_rounded_rect(d, (left_x, panel_top, left_x + left_w, panel_bot), PANEL, BORDER)
    hdr = "Legacy Transaction"
    hw, _ = text_size(d, hdr, header_font)
    d.text((left_x + (left_w - hw) // 2, panel_top + 8), hdr, fill=RED, font=header_font)

    # Show 10 full addresses embedded in tx
    d.text((left_x + 10, panel_top + 28), "10 full addresses inline:", fill=DIM, font=small_font)
    addr_start_y = panel_top + 44
    addr_h = 20
    addr_gap = 4

    for i, addr in enumerate(ADDRS):
        ay = addr_start_y + i * (addr_h + addr_gap)
        pulse = 0.5 + 0.5 * math.sin(t * math.pi * 3 + i * 0.6)
        draw_rounded_rect(d, (left_x + 12, ay, left_x + left_w - 12, ay + addr_h),
                          DARK_BOX, lerp_color(BORDER, RED, 0.2 + 0.15 * pulse), r=4)
        # 32-byte icon
        d.text((left_x + 18, ay + 4), f"[32B] {addr}", fill=lerp_color(DIM, RED, 0.4), font=tiny_font)

    # Size label
    size_text = "~1232 bytes"
    stw, _ = text_size(d, size_text, small_font)
    d.text((left_x + (left_w - stw) // 2, panel_bot - 22), size_text, fill=RED, font=small_font)

    # === CENTER: Address Lookup Table ===
    center_x, center_w = 268, 160
    alt_top = panel_top + 30
    alt_bot = panel_bot - 30
    draw_rounded_rect(d, (center_x, alt_top, center_x + center_w, alt_bot), PURPLE_BG, lerp_color(BORDER, PURPLE, 0.4))
    hdr2 = "Lookup Table"
    hw2, _ = text_size(d, hdr2, header_font)
    d.text((center_x + (center_w - hw2) // 2, alt_top + 6), hdr2, fill=PURPLE, font=header_font)
    d.text((center_x + 8, alt_top + 24), "On-chain ALT:", fill=DIM, font=tiny_font)

    # Index → Address mappings
    alt_entries = [
        (0, "9WzD..q3Fk"),
        (1, "Vote..Prog"),
        (2, "Sys..Prog1"),
        (3, "Token..Prg"),
        (4, "ATA..xProg"),
        (5, "Sysv..Rent"),
        (6, "Sysv..Clok"),
    ]
    entry_y = alt_top + 40
    entry_h = 18
    for i, (idx, addr) in enumerate(alt_entries):
        ey = entry_y + i * (entry_h + 3)
        # Highlight scanning
        dist = abs(t * len(alt_entries) * (entry_h + 3) + entry_y - (ey + entry_h // 2))
        hl = max(0, 1.0 - dist / 20)
        label = f"{idx} -> {addr}"
        d.text((center_x + 12, ey + 2), label,
               fill=lerp_color(DIM, PURPLE, 0.4 + hl * 0.6), font=tiny_font)

    # Arrows from ALT to right panel
    arrow_pulse = 0.5 + 0.5 * math.sin(t * math.pi * 4)
    ac = lerp_color(DIM, PURPLE, arrow_pulse)
    d.line([(center_x + center_w + 2, (alt_top + alt_bot) // 2),
            (center_x + center_w + 22, (alt_top + alt_bot) // 2)], fill=ac, width=2)
    ax = center_x + center_w + 22
    ay = (alt_top + alt_bot) // 2
    d.polygon([(ax, ay), (ax - 5, ay - 4), (ax - 5, ay + 4)], fill=ac)

    # === RIGHT: v0 Transaction ===
    right_x, right_w = 445, 330
    draw_rounded_rect(d, (right_x, panel_top, right_x + right_w, panel_bot), PANEL, BORDER)
    hdr3 = "v0 Transaction"
    hw3, _ = text_size(d, hdr3, header_font)
    d.text((right_x + (right_w - hw3) // 2, panel_top + 8), hdr3, fill=GREEN, font=header_font)

    # v0 structure
    v0_start = panel_top + 30
    sections = [
        ("version: 0", CYAN, 22),
        ("ALT ref: LookupAddr", PURPLE, 22),
        ("Static keys: [signer]", GREEN, 22),
    ]
    sy = v0_start
    for label, color, sh in sections:
        draw_rounded_rect(d, (right_x + 12, sy, right_x + right_w - 12, sy + sh),
                          DARK_BOX, lerp_color(BORDER, color, 0.3), r=4)
        d.text((right_x + 20, sy + 5), label, fill=color, font=small_font)
        sy += sh + 6

    # Index references instead of full addresses
    d.text((right_x + 12, sy + 2), "Account indices (1 byte each):", fill=DIM, font=small_font)
    sy += 18
    idx_box_w = 36
    idx_gap = 6
    indices_per_row = 7
    for i in range(10):
        row = i // indices_per_row
        col = i % indices_per_row
        ix = right_x + 18 + col * (idx_box_w + idx_gap)
        iy = sy + row * (22 + idx_gap)
        pulse = 0.5 + 0.5 * math.sin(t * math.pi * 3 + i * 0.5)
        draw_rounded_rect(d, (ix, iy, ix + idx_box_w, iy + 20),
                          lerp_color(DARK_BOX, GREEN_BG, 0.2),
                          lerp_color(BORDER, GREEN, 0.3 + 0.2 * pulse), r=4)
        idx_label = f"#{i}"
        iw, _ = text_size(d, idx_label, small_font)
        d.text((ix + (idx_box_w - iw) // 2, iy + 4), idx_label,
               fill=lerp_color(DIM, GREEN, 0.6), font=small_font)

    # Instruction data
    instr_y = sy + 2 * (22 + idx_gap) + 12
    draw_rounded_rect(d, (right_x + 12, instr_y, right_x + right_w - 12, instr_y + 24),
                      DARK_BOX, lerp_color(BORDER, YELLOW, 0.3), r=4)
    d.text((right_x + 20, instr_y + 5), "Instruction data: [swap params]", fill=YELLOW, font=small_font)

    # Size comparison
    size2 = "~450 bytes"
    s2w, _ = text_size(d, size2, small_font)
    d.text((right_x + (right_w - s2w) // 2, panel_bot - 22), size2, fill=GREEN, font=small_font)

    # === Bottom Panel: Size comparison bar + explanation ===
    bot_y = 380
    draw_rounded_rect(d, (30, bot_y, W - 30, H - 14), PANEL, BORDER)

    # Bar chart comparison
    bar_y = bot_y + 10
    bar_h = 18
    max_bar_w = 350
    legacy_w = max_bar_w
    v0_w = int(max_bar_w * 450 / 1232)

    d.text((50, bar_y + 2), "Legacy:", fill=DIM, font=small_font)
    bar_sx = 120
    draw_rounded_rect(d, (bar_sx, bar_y, bar_sx + legacy_w, bar_y + bar_h), RED_BG, lerp_color(BORDER, RED, 0.3), r=3)
    d.text((bar_sx + legacy_w // 2 - 30, bar_y + 3), "1232 bytes", fill=RED, font=small_font)

    d.text((50, bar_y + bar_h + 8), "v0:", fill=DIM, font=small_font)
    draw_rounded_rect(d, (bar_sx, bar_y + bar_h + 6, bar_sx + v0_w, bar_y + 2 * bar_h + 6),
                      GREEN_BG, lerp_color(BORDER, GREEN, 0.3), r=3)
    d.text((bar_sx + v0_w // 2 - 25, bar_y + bar_h + 9), "450 bytes", fill=GREEN, font=small_font)

    # Savings
    pulse = 0.6 + 0.4 * math.sin(t * math.pi * 3)
    save_text = "63% smaller"
    svw, _ = text_size(d, save_text, header_font)
    d.text((bar_sx + legacy_w + 20, bar_y + 8), save_text,
           fill=lerp_color(DIM, GREEN, pulse), font=header_font)

    # Explanation
    explanations = [
        ("Address Lookup Tables (ALTs)", "Store common addresses on-chain, reference by 1-byte index", PURPLE),
        ("More Accounts Per Transaction", "Legacy: max ~35 accounts. v0: up to 256 via ALTs", GREEN),
        ("DeFi Composability", "Complex swaps touching many programs fit in a single tx", YELLOW),
        ("Backward Compatible", "version field lets validators handle both formats", CYAN),
    ]
    idx = (fi // 18) % len(explanations)
    et, ed, ec = explanations[idx]
    etw, _ = text_size(d, et, header_font)
    d.text(((W - etw) // 2, bot_y + 60), et, fill=ec, font=header_font)
    edw, _ = text_size(d, ed, body_font)
    d.text(((W - edw) // 2, bot_y + 82), ed, fill=DIM, font=body_font)

    # Key insight at bottom
    key = "32-byte address -> 1-byte index = massive savings"
    kw, _ = text_size(d, key, small_font)
    d.text(((W - kw) // 2, H - 30), key, fill=lerp_color(DIM, PURPLE, 0.5 + 0.3 * math.sin(t * math.pi * 2)), font=small_font)

    return img


if __name__ == "__main__":
    frames = [make_frame(i) for i in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DUR, loop=0, optimize=True)
    print(f"Saved {OUT} ({len(frames)} frames)")
