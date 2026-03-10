"""
Variant B: Casper FFG Finality — Beacon Chain PoS
Shows chain of epochs: Proposed -> Justified -> Finalized.
Two rounds of supermajority voting. Visual pipeline.
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- CONSTANTS ---
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
    except Exception:
        fb = ImageFont.load_default()
        fonts = {"title": fb, "header": fb, "body": fb, "small": fb}
    return fonts

FONTS = load_fonts()

def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def draw_rounded_rect(draw, xy, fill, outline=None, radius=6):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)

def draw_arrow(draw, x1, y1, x2, y2, color, width=2):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    # arrowhead
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    size = 6
    draw.polygon([
        (x2, y2),
        (x2 - ux * size + px * size * 0.5, y2 - uy * size + py * size * 0.5),
        (x2 - ux * size - px * size * 0.5, y2 - uy * size - py * size * 0.5),
    ], fill=color)

def make_frame(frame_idx):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Title
    title = "Casper FFG Finality"
    tw, _ = text_size(draw, title, FONTS["title"])
    draw.text(((W - tw) // 2, 12), title, fill=GREEN, font=FONTS["title"])

    # --- EPOCH CHAIN (top section) ---
    chain_y = 65
    draw_rounded_rect(draw, (20, chain_y, W - 20, chain_y + 110), fill=PANEL, outline=BORDER)
    draw.text((30, chain_y + 6), "Epoch Chain", fill=WHITE, font=FONTS["header"])

    # 6 epoch boxes in a chain
    epochs = ["E60", "E61", "E62", "E63", "E64", "E65"]
    # States evolve with frame: earlier epochs finalize as animation progresses
    # phase: 0-11 = round 1 voting, 12-23 = round 2 voting, 24-35 = finalization
    phase = frame_idx // 12  # 0, 1, 2

    epoch_states = []
    for i in range(6):
        if i <= 1:
            epoch_states.append("finalized")
        elif i == 2:
            epoch_states.append(["justified", "justified", "finalized"][phase])
        elif i == 3:
            epoch_states.append(["proposed", "justified", "justified"][phase])
        elif i == 4:
            epoch_states.append(["proposed", "proposed", "justified"][phase])
        else:
            epoch_states.append("proposed")

    box_w, box_h = 100, 55
    gap = 18
    total_w = 6 * box_w + 5 * gap
    start_x = (W - total_w) // 2
    ey = chain_y + 35

    state_styles = {
        "finalized": (GREEN_BG, GREEN, "FINAL"),
        "justified": (YELLOW_BG, YELLOW, "JUST"),
        "proposed":  (PURPLE_BG, PURPLE, "PROP"),
    }

    for i, (ep, state) in enumerate(zip(epochs, epoch_states)):
        bx = start_x + i * (box_w + gap)
        bg, col, tag = state_styles[state]
        # Pulse outline for the epoch currently being voted on
        voting_idx = [3, 4, 5][min(phase, 2)]
        outline = WHITE if i == voting_idx and (frame_idx % 6 < 3) else col
        draw_rounded_rect(draw, (bx, ey, bx + box_w, ey + box_h), fill=bg, outline=outline)
        # Epoch label
        tw1, _ = text_size(draw, ep, FONTS["header"])
        draw.text((bx + (box_w - tw1) // 2, ey + 6), ep, fill=WHITE, font=FONTS["header"])
        # State tag
        tw2, _ = text_size(draw, tag, FONTS["small"])
        draw.text((bx + (box_w - tw2) // 2, ey + box_h - 18), tag, fill=col, font=FONTS["small"])

        # Chain arrow
        if i < 5:
            ax = bx + box_w + 2
            ay = ey + box_h // 2
            draw_arrow(draw, ax, ay, ax + gap - 4, ay, DIM)

    # --- VOTING ROUNDS PANEL ---
    vote_y = 195
    draw_rounded_rect(draw, (20, vote_y, W - 20, vote_y + 160), fill=PANEL, outline=BORDER)
    draw.text((30, vote_y + 8), "Supermajority Voting (2/3 required)", fill=YELLOW, font=FONTS["header"])

    # Two round boxes side by side
    round_labels = ["Round 1: Source -> Target", "Round 2: Justify -> Finalize"]
    round_w = 350
    for ri in range(2):
        rx = 40 + ri * (round_w + 30)
        ry = vote_y + 35
        rh = 110
        active = (ri == 0 and phase >= 0) or (ri == 1 and phase >= 1)
        completed = (ri == 0 and phase >= 1) or (ri == 1 and phase >= 2)
        box_col = GREEN if completed else (CYAN if active else BORDER)
        box_bg = GREEN_BG if completed else (CYAN_BG if active else DARK_BOX)

        draw_rounded_rect(draw, (rx, ry, rx + round_w, ry + rh), fill=box_bg, outline=box_col)
        draw.text((rx + 10, ry + 8), round_labels[ri], fill=WHITE, font=FONTS["body"])

        # Vote progress bar
        bar_x = rx + 15
        bar_y_inner = ry + 35
        bar_w = round_w - 30
        bar_h = 18
        draw_rounded_rect(draw, (bar_x, bar_y_inner, bar_x + bar_w, bar_y_inner + bar_h),
                          fill=DARK_BOX, outline=BORDER)

        if completed:
            pct = 1.0
        elif active:
            sub_frame = frame_idx % 12
            pct = min(1.0, sub_frame / 10.0)
        else:
            pct = 0.0

        if pct > 0:
            fill_w = int(bar_w * pct)
            c = GREEN if pct >= 0.67 else CYAN
            draw_rounded_rect(draw, (bar_x, bar_y_inner, bar_x + fill_w, bar_y_inner + bar_h),
                              fill=c, outline=c)

        # 2/3 threshold marker
        marker_x = bar_x + int(bar_w * 0.667)
        draw.line([(marker_x, bar_y_inner - 3), (marker_x, bar_y_inner + bar_h + 3)],
                  fill=YELLOW, width=2)

        # Vote count
        votes = int(128 * pct)
        thresh = 86
        label = f"{votes}/128 votes"
        draw.text((bar_x, bar_y_inner + bar_h + 6), label, fill=WHITE, font=FONTS["small"])
        status = "PASSED" if votes >= thresh else "Voting..."
        scol = GREEN if votes >= thresh else DIM
        draw.text((bar_x + 150, bar_y_inner + bar_h + 6), status, fill=scol, font=FONTS["small"])

        # Checkmark or spinner
        icon_x = rx + round_w - 30
        icon_y = ry + 8
        if completed:
            draw.text((icon_x, icon_y), "[OK]", fill=GREEN, font=FONTS["small"])
        elif active:
            dots = "." * ((frame_idx % 3) + 1)
            draw.text((icon_x - 5, icon_y), dots, fill=CYAN, font=FONTS["small"])

    # --- FINALITY GUARANTEE PANEL ---
    fin_y = 375
    draw_rounded_rect(draw, (20, fin_y, W - 20, fin_y + 110), fill=PANEL, outline=BORDER)
    draw.text((30, fin_y + 8), "Finality Status", fill=GREEN, font=FONTS["header"])

    # Checkpoint visualization
    checkpoints = [
        ("Checkpoint A (E62)", GREEN if phase >= 2 else (YELLOW if phase >= 0 else DIM)),
        ("Checkpoint B (E63)", GREEN if phase >= 2 else (YELLOW if phase >= 1 else DIM)),
        ("Checkpoint C (E64)", YELLOW if phase >= 2 else DIM),
    ]
    cx_start = 50
    for ci, (label, col) in enumerate(checkpoints):
        cx = cx_start + ci * 230
        cy = fin_y + 38
        draw.ellipse((cx, cy, cx + 18, cy + 18), fill=col, outline=WHITE)
        draw.text((cx + 26, cy + 2), label, fill=WHITE, font=FONTS["body"])
        if ci < 2:
            draw_arrow(draw, cx + 180, cy + 9, cx + 225, cy + 9, col)

    # Finality message
    if phase >= 2:
        msg = "E62 FINALIZED -- cannot be reverted (1/3 stake slashed)"
        msg_col = GREEN
    elif phase >= 1:
        msg = "E62 justified, awaiting second supermajority vote..."
        msg_col = YELLOW
    else:
        msg = "First round of attestation voting in progress..."
        msg_col = CYAN

    tw, _ = text_size(draw, msg, FONTS["body"])
    draw.text(((W - tw) // 2, fin_y + 78), msg, fill=msg_col, font=FONTS["body"])

    # --- SCANNING LINE ---
    # Horizontal scan across the voting panel
    scan_x = 40 + int((W - 80) * ((frame_idx % 18) / 17.0))
    draw.line([(scan_x, vote_y + 32), (scan_x, vote_y + 33)], fill=WHITE, width=1)

    return img

frames = [make_frame(i) for i in range(FRAMES)]
frames[0].save("assets/gifs/ethereum_07_pos_beacon.gif", save_all=True, append_images=frames[1:],
               duration=DELAY, loop=0, optimize=True)
print("Saved assets/gifs/ethereum_07_pos_beacon.gif")
