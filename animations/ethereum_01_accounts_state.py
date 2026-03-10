"""
Variant B: State Transition — Before/After world state with transaction arrow.
Generates assets/gifs/ethereum_01_accounts_state.gif
"""

from PIL import Image, ImageDraw, ImageFont
import math

# === COLORS ===
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

# === FONTS ===
try:
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
except Exception:
    font_title = ImageFont.load_default()
    font_header = ImageFont.load_default()
    font_body = ImageFont.load_default()
    font_small = ImageFont.load_default()


def tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def draw_rrect(draw, xy, fill, outline, radius=6):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def draw_account_card(draw, x, y, name, addr, nonce, balance, nonce_color, bal_color, highlight_nonce, highlight_bal):
    """Draw a compact account card. Returns height."""
    card_w = 155
    card_h = 105

    border = CYAN if "Alice" in name else (GREEN if "Bob" in name else ORANGE)
    bg = CYAN_BG if "Alice" in name else (GREEN_BG if "Bob" in name else YELLOW_BG)

    draw_rrect(draw, (x, y, x + card_w, y + card_h), fill=bg, outline=border, radius=8)

    # Name header
    draw.text((x + 8, y + 6), name, fill=border, font=font_header)
    # Address
    draw.text((x + 8, y + 24), addr, fill=DIM, font=font_small)

    # Nonce row
    ny = y + 42
    nc = WHITE if not highlight_nonce else YELLOW
    draw.text((x + 8, ny), "nonce:", fill=DIM, font=font_body)
    draw.text((x + 70, ny), str(nonce), fill=nc, font=font_body)
    if highlight_nonce:
        draw_rrect(draw, (x + 66, ny - 2, x + 66 + tw(draw, str(nonce), font_body) + 8, ny + 14),
                   fill=None, outline=YELLOW, radius=3)

    # Balance row
    by = y + 62
    bc = WHITE if not highlight_bal else GREEN
    draw.text((x + 8, by), "balance:", fill=DIM, font=font_body)
    draw.text((x + 70, by), balance, fill=bc, font=font_body)
    if highlight_bal:
        draw_rrect(draw, (x + 66, by - 2, x + 66 + tw(draw, balance, font_body) + 8, by + 14),
                   fill=None, outline=GREEN, radius=3)

    # Code/storage hint
    draw.text((x + 8, y + 84), "code: --  storage: --", fill=DIM, font=font_small)

    return card_h


def draw_tx_arrow(draw, x0, y_center, x1, frame):
    """Draw an animated transaction arrow from x0 to x1 at y_center."""
    # Arrow body
    draw.line((x0, y_center, x1 - 10, y_center), fill=YELLOW, width=2)
    # Arrow head
    draw.polygon([
        (x1, y_center),
        (x1 - 12, y_center - 6),
        (x1 - 12, y_center + 6),
    ], fill=YELLOW)

    # Animated dot traveling along the arrow
    cycle = FRAMES
    frac = (frame % cycle) / cycle
    dot_x = int(x0 + frac * (x1 - x0))
    draw.ellipse((dot_x - 4, y_center - 4, dot_x + 4, y_center + 4), fill=YELLOW)


def draw_state_label(draw, cx, y, text, color):
    w = tw(draw, text, font_header)
    draw_rrect(draw, (cx - w // 2 - 12, y, cx + w // 2 + 12, y + 24), fill=DARK_BOX, outline=color, radius=5)
    draw.text((cx - w // 2, y + 4), text, fill=color, font=font_header)


def generate_frame(frame):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Title
    title_text = "Ethereum State Transition"
    t_w = tw(draw, title_text, font_title)
    draw.text((W // 2 - t_w // 2, 14), title_text, fill=WHITE, font=font_title)

    # Subtitle
    sub = "Transaction: Alice sends 2.0 ETH to Bob"
    sw = tw(draw, sub, font_small)
    draw.text((W // 2 - sw // 2, 48), sub, fill=DIM, font=font_small)

    # ---- BEFORE state (left) ----
    before_cx = 195
    draw_state_label(draw, before_cx, 72, "BEFORE", CYAN)

    # Before accounts
    bx = before_cx - 77
    draw_account_card(draw, bx, 108, "Alice", "0xA1ce..3f", 5, "10.0 ETH", WHITE, WHITE, False, False)
    draw_account_card(draw, bx, 228, "Bob", "0xB0b0..7a", 0, "3.0 ETH", WHITE, WHITE, False, False)
    draw_account_card(draw, bx, 348, "Carol", "0xCa01..e2", 2, "7.5 ETH", WHITE, WHITE, False, False)

    # ---- AFTER state (right) ----
    after_cx = W - 195
    draw_state_label(draw, after_cx, 72, "AFTER", GREEN)

    ax = after_cx - 77
    # Alice: nonce +1, balance -2
    draw_account_card(draw, ax, 108, "Alice", "0xA1ce..3f", 6, "8.0 ETH", YELLOW, GREEN, True, True)
    # Bob: balance +2
    draw_account_card(draw, ax, 228, "Bob", "0xB0b0..7a", 0, "5.0 ETH", WHITE, GREEN, False, True)
    # Carol: unchanged
    draw_account_card(draw, ax, 348, "Carol", "0xCa01..e2", 2, "7.5 ETH", WHITE, WHITE, False, False)

    # ---- Transaction arrow in the middle ----
    mid_x = W // 2
    arrow_x0 = before_cx + 90
    arrow_x1 = after_cx - 90

    # Transaction box in center
    tx_box_w = 120
    tx_box_h = 80
    tx_x = mid_x - tx_box_w // 2
    tx_y = 175
    draw_rrect(draw, (tx_x, tx_y, tx_x + tx_box_w, tx_y + tx_box_h),
               fill=YELLOW_BG, outline=YELLOW, radius=8)
    draw.text((tx_x + 8, tx_y + 6), "Transaction", fill=YELLOW, font=font_header)
    draw.text((tx_x + 8, tx_y + 26), "from: Alice", fill=DIM, font=font_small)
    draw.text((tx_x + 8, tx_y + 40), "to:   Bob", fill=DIM, font=font_small)
    draw.text((tx_x + 8, tx_y + 54), "val:  2.0 ETH", fill=WHITE, font=font_small)

    # Arrows from before -> tx box -> after (animated dots)
    draw_tx_arrow(draw, arrow_x0, 160, tx_x - 2, frame)
    draw_tx_arrow(draw, tx_x + tx_box_w + 2, 160, arrow_x1, frame)

    # Change annotations with animated pulse
    pulse = 0.6 + 0.4 * math.sin(2 * math.pi * frame / FRAMES)

    # Delta labels near the after cards
    delta_x = ax + 160
    # Alice delta
    c1 = tuple(int(c * pulse) for c in RED)
    draw.text((delta_x, 140), "-2.0", fill=c1, font=font_header)
    c2 = tuple(int(c * pulse) for c in YELLOW)
    draw.text((delta_x, 120), "+1", fill=c2, font=font_small)

    # Bob delta
    c3 = tuple(int(c * pulse) for c in GREEN)
    draw.text((delta_x, 260), "+2.0", fill=c3, font=font_header)

    # Carol - no change indicator
    draw.text((delta_x, 375), "---", fill=DIM, font=font_small)

    # Horizontal scan line across both state columns
    scan_frac = (frame % FRAMES) / FRAMES
    scan_y = int(108 + scan_frac * 340)
    if scan_y < 460:
        draw.line((30, scan_y, W - 30, scan_y), fill=(30, 40, 55), width=1)

    # Bottom note
    note = "State root hash changes with every transaction"
    nw = tw(draw, note, font_small)
    draw.text((W // 2 - nw // 2, H - 28), note, fill=DIM, font=font_small)

    return img


if __name__ == "__main__":
    frames = [generate_frame(f) for f in range(FRAMES)]
    frames[0].save(
        "assets/gifs/ethereum_01_accounts_state.gif",
        save_all=True,
        append_images=frames[1:],
        duration=DELAY,
        loop=0,
        optimize=True,
    )
    print("Saved assets/gifs/ethereum_01_accounts_state.gif")
