"""Clockwork Automation: Threads with trigger conditions, crankers, and DCA example."""
from PIL import Image, ImageDraw, ImageFont
import math, os

W, H, FRAMES, DUR = 800, 550, 36, 90
BG = (13, 17, 23)
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)
RED = (248, 113, 113)
PURPLE = (167, 139, 250)
CYAN_BG = (18, 50, 68)
GREEN_BG = (14, 48, 40)
PURPLE_BG = (35, 28, 58)
RED_BG = (50, 20, 20)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
YELLOW_BG = (58, 50, 14)

OUT = "assets/gifs/solana_15_clockwork_automation.gif"

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

def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def draw_rounded_rect(d, xy, fill, outline, r=8):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline)


def make_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    t = fi / (FRAMES - 1)
    pulse = 0.5 + 0.5 * math.sin(fi * 2 * math.pi / 10)

    # Title
    title = "Clockwork Automation"
    tw, _ = text_size(d, title, title_font)
    d.text(((W - tw) // 2, 10), title, fill=CYAN, font=title_font)
    sub = "On-chain cron jobs: scheduled and conditional execution"
    sw, _ = text_size(d, sub, body_font)
    d.text(((W - sw) // 2, 40), sub, fill=DIM, font=body_font)

    # === LEFT: Thread box with trigger ===
    th_x, th_y = 25, 68
    th_w, th_h = 230, 175
    draw_rounded_rect(d, (th_x, th_y, th_x + th_w, th_y + th_h), PANEL, BORDER)
    d.text((th_x + 12, th_y + 8), "Clockwork Thread", fill=PURPLE, font=header_font)

    # Thread fields
    fields = [
        ("authority:", "user_pubkey", CYAN),
        ("trigger:", "Cron(*/5 * * * *)", YELLOW),
        ("target_ix:", "dca_swap()", GREEN),
        ("fee:", "0.001 SOL/exec", DIM),
        ("status:", "Active", GREEN),
    ]
    fy = th_y + 32
    for label, value, color in fields:
        d.text((th_x + 15, fy), label, fill=DIM, font=tiny_font)
        d.text((th_x + 85, fy), value, fill=color, font=tiny_font)
        fy += 18

    # Trigger types below
    d.text((th_x + 12, th_y + 130), "Trigger Types:", fill=ORANGE, font=small_font)
    triggers = ["Cron", "Account", "Epoch", "Slot"]
    tx = th_x + 15
    for i, trig in enumerate(triggers):
        tw2, _ = text_size(d, trig, tiny_font)
        active = i == (fi // 9) % 4  # Rotate highlight
        bg = YELLOW_BG if active else DARK_BOX
        bord = YELLOW if active else BORDER
        draw_rounded_rect(d, (tx, th_y + 148, tx + tw2 + 12, th_y + 165), bg, bord, r=3)
        d.text((tx + 6, th_y + 150), trig, fill=YELLOW if active else DIM, font=tiny_font)
        tx += tw2 + 18

    # === MIDDLE: Cranker mechanism ===
    cr_x, cr_y = 280, 68
    cr_w, cr_h = 150, 175
    draw_rounded_rect(d, (cr_x, cr_y, cr_x + cr_w, cr_y + cr_h), PANEL, BORDER)
    d.text((cr_x + 20, cr_y + 8), "Cranker Node", fill=ORANGE, font=header_font)

    # Crank gear visual
    gear_cx, gear_cy = cr_x + cr_w // 2, cr_y + 75
    gear_r = 25
    angle_offset = fi * 10  # Rotate gear
    n_teeth = 8
    for i in range(n_teeth):
        angle = math.radians(angle_offset + i * 360 / n_teeth)
        x1 = gear_cx + int((gear_r - 5) * math.cos(angle))
        y1 = gear_cy + int((gear_r - 5) * math.sin(angle))
        x2 = gear_cx + int((gear_r + 5) * math.cos(angle))
        y2 = gear_cy + int((gear_r + 5) * math.sin(angle))
        col = lerp_color(DIM, ORANGE, 0.5 + 0.3 * pulse)
        d.line([(x1, y1), (x2, y2)], fill=col, width=3)
    d.ellipse((gear_cx - 8, gear_cy - 8, gear_cx + 8, gear_cy + 8),
              fill=DARK_BOX, outline=ORANGE)

    # Cranker labels
    d.text((cr_x + 15, cr_y + 110), "Monitors threads", fill=DIM, font=tiny_font)
    d.text((cr_x + 15, cr_y + 125), "Checks triggers", fill=DIM, font=tiny_font)
    d.text((cr_x + 15, cr_y + 140), "Submits crank tx", fill=DIM, font=tiny_font)
    d.text((cr_x + 15, cr_y + 155), "Earns crank fee", fill=YELLOW, font=tiny_font)

    # Arrow Thread -> Cranker
    d.line([(th_x + th_w + 3, th_y + th_h // 2), (cr_x - 5, cr_y + cr_h // 2)],
           fill=PURPLE, width=2)
    d.polygon([(cr_x - 2, cr_y + cr_h // 2),
               (cr_x - 8, cr_y + cr_h // 2 - 4),
               (cr_x - 8, cr_y + cr_h // 2 + 4)], fill=PURPLE)

    # === RIGHT: Target Program ===
    tp_x, tp_y = 460, 68
    tp_w, tp_h = 310, 175
    draw_rounded_rect(d, (tp_x, tp_y, tp_x + tp_w, tp_y + tp_h), PANEL, BORDER)
    d.text((tp_x + 12, tp_y + 8), "Target: DCA Swap Program", fill=GREEN, font=header_font)

    # DCA config
    dca_fields = [
        ("Token In:", "USDC", CYAN),
        ("Token Out:", "SOL", GREEN),
        ("Amount/Exec:", "50 USDC", YELLOW),
        ("Total Budget:", "500 USDC", DIM),
        ("Remaining:", f"{max(0, 500 - int(t * 500))} USDC", ORANGE),
    ]
    dy = tp_y + 32
    for label, value, color in dca_fields:
        d.text((tp_x + 15, dy), label, fill=DIM, font=tiny_font)
        d.text((tp_x + 110, dy), value, fill=color, font=tiny_font)
        dy += 18

    # Progress bar for DCA completion
    bar_y = tp_y + 128
    bar_w = tp_w - 40
    bar_h = 14
    draw_rounded_rect(d, (tp_x + 20, bar_y, tp_x + 20 + bar_w, bar_y + bar_h),
                      DARK_BOX, BORDER, r=4)
    fill_w = int(bar_w * t)
    if fill_w > 4:
        draw_rounded_rect(d, (tp_x + 20, bar_y, tp_x + 20 + fill_w, bar_y + bar_h),
                          GREEN_BG, lerp_color(BORDER, GREEN, 0.5), r=4)
    d.text((tp_x + 20 + bar_w + 8, bar_y), f"{int(t * 100)}%", fill=GREEN, font=tiny_font)

    d.text((tp_x + 20, bar_y + 20), "Executions completed over time", fill=DIM, font=tiny_font)

    # Arrow Cranker -> Target
    d.line([(cr_x + cr_w + 3, cr_y + cr_h // 2), (tp_x - 5, tp_y + tp_h // 2)],
           fill=GREEN, width=2)
    d.polygon([(tp_x - 2, tp_y + tp_h // 2),
               (tp_x - 8, tp_y + tp_h // 2 - 4),
               (tp_x - 8, tp_y + tp_h // 2 + 4)], fill=GREEN)
    d.text((cr_x + cr_w + 6, cr_y + cr_h // 2 - 14), "crank", fill=GREEN, font=tiny_font)

    # === BOTTOM: Execution Timeline ===
    tl_y = 260
    tl_h = 140
    draw_rounded_rect(d, (30, tl_y, W - 30, tl_y + tl_h), PANEL, BORDER)
    d.text((50, tl_y + 8), "Execution Timeline (DCA every 5 min)", fill=YELLOW, font=header_font)

    # Timeline
    line_y = tl_y + 55
    line_x1, line_x2 = 60, W - 60
    d.line([(line_x1, line_y), (line_x2, line_y)], fill=BORDER, width=2)

    n_execs = 8
    exec_spacing = (line_x2 - line_x1) / (n_execs - 1)
    scan_pos = t * (n_execs - 1)

    for i in range(n_execs):
        ex = line_x1 + int(i * exec_spacing)
        executed = i <= scan_pos

        # Execution dot
        dot_col = GREEN if executed else BORDER
        d.ellipse((ex - 6, line_y - 6, ex + 6, line_y + 6), fill=dot_col)

        # Time label
        time_label = f"T+{i*5}m"
        tlw, _ = text_size(d, time_label, tiny_font)
        d.text((ex - tlw // 2, line_y + 12), time_label, fill=DIM, font=tiny_font)

        # Amount label
        if executed:
            amt = "50 USDC"
            aw, _ = text_size(d, amt, tiny_font)
            d.text((ex - aw // 2, line_y - 22), amt, fill=GREEN, font=tiny_font)

    # Scan line
    scan_x = line_x1 + int(scan_pos * exec_spacing)
    scan_col = lerp_color(DIM, YELLOW, 0.5 + 0.3 * pulse)
    d.line([(scan_x, line_y - 30), (scan_x, line_y + 30)], fill=scan_col, width=2)

    # Summary at bottom of timeline
    total_bought = int(scan_pos + 1) * 50
    d.text((60, tl_y + tl_h - 30), f"Total spent: {min(total_bought, 400)} USDC", fill=CYAN, font=small_font)
    d.text((280, tl_y + tl_h - 30), f"SOL acquired: ~{min(total_bought, 400) / 25:.1f} SOL", fill=GREEN, font=small_font)
    d.text((520, tl_y + tl_h - 30), f"Avg price: ~$25.00", fill=YELLOW, font=small_font)

    # === BOTTOM: Explanations ===
    exp_y = 415
    draw_rounded_rect(d, (30, exp_y, W - 30, H - 14), PANEL, BORDER)
    explanations = [
        ("Clockwork = On-Chain Cron", "Schedule recurring transactions without off-chain bots", PURPLE),
        ("Cranker = Permissionless Executor", "Anyone can crank threads and earn fees -- no centralized keeper", ORANGE),
        ("DCA = Dollar Cost Average", "Buy fixed amounts at intervals -- reduces timing risk", GREEN),
        ("Thread Account = Automation Config", "Stores trigger, target instruction, and fee budget on-chain", CYAN),
    ]
    idx = fi % len(explanations)
    et, ed, ec = explanations[idx]
    etw, _ = text_size(d, et, header_font)
    d.text(((W - etw) // 2, exp_y + 10), et, fill=ec, font=header_font)
    edw, _ = text_size(d, ed, body_font)
    d.text(((W - edw) // 2, exp_y + 32), ed, fill=DIM, font=body_font)

    # Use case tags
    tags = ["DCA", "Auto-compound", "Limit orders", "Liquidations"]
    tag_y = exp_y + 58
    tag_x = (W - sum(text_size(d, tg, tiny_font)[0] + 20 for tg in tags) - (len(tags) - 1) * 8) // 2
    colors = [GREEN, CYAN, YELLOW, ORANGE]
    for i, (tg, col) in enumerate(zip(tags, colors)):
        tgw, _ = text_size(d, tg, tiny_font)
        active = i == (fi // 9) % len(tags)
        bg = lerp_color(DARK_BOX, col, 0.15 if active else 0.0)
        bord = col if active else BORDER
        draw_rounded_rect(d, (tag_x, tag_y, tag_x + tgw + 18, tag_y + 18), bg, bord, r=3)
        d.text((tag_x + 9, tag_y + 2), tg, fill=col if active else DIM, font=tiny_font)
        tag_x += tgw + 26

    return img


if __name__ == "__main__":
    frames = [make_frame(i) for i in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DUR, loop=0, optimize=True)
    print(f"Saved {OUT} ({len(frames)} frames)")
