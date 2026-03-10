"""Stake Economics: Inflation curve, validator rewards, and commission flow."""
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

OUT = "assets/gifs/solana_12_stake_economics.gif"

def load_font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for n in names:
        for p in [f"/usr/share/fonts/truetype/dejavu/{n}", f"/usr/share/fonts/truetype/liberation/{n}", f"/usr/share/fonts/{n}"]:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except: pass
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


def make_frame(fi):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    t = fi / (FRAMES - 1)

    # Title
    title = "Solana Stake Economics"
    tw, _ = text_size(d, title, title_font)
    d.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)
    sub = "Inflation, rewards, and commission flow"
    sw, _ = text_size(d, sub, body_font)
    d.text(((W - sw) // 2, 44), sub, fill=DIM, font=body_font)

    # === TOP LEFT: Inflation Curve ===
    chart_x, chart_y = 35, 72
    chart_w, chart_h = 340, 160
    draw_rounded_rect(d, (chart_x - 5, chart_y - 5, chart_x + chart_w + 5, chart_y + chart_h + 5), PANEL, BORDER)

    d.text((chart_x + 8, chart_y + 4), "Inflation Rate Over Time", fill=YELLOW, font=header_font)

    # Chart area
    cx, cy = chart_x + 45, chart_y + 30
    cw, ch = chart_w - 60, chart_h - 50

    # Axes
    d.line([(cx, cy), (cx, cy + ch)], fill=DIM, width=1)
    d.line([(cx, cy + ch), (cx + cw, cy + ch)], fill=DIM, width=1)

    # Y-axis labels
    y_labels = ["8%", "6%", "4%", "2%", "1.5%"]
    for i, yl in enumerate(y_labels):
        yy = cy + int(i * ch / (len(y_labels) - 1))
        d.text((cx - 28, yy - 5), yl, fill=DIM, font=tiny_font)
        d.line([(cx, yy), (cx + cw, yy)], fill=lerp_color(BG, BORDER, 0.5), width=1)

    # X-axis labels (years)
    x_labels = ["Y0", "Y2", "Y5", "Y10", "Y15+"]
    for i, xl in enumerate(x_labels):
        xx = cx + int(i * cw / (len(x_labels) - 1))
        d.text((xx - 8, cy + ch + 4), xl, fill=DIM, font=tiny_font)

    # Inflation curve: starts at 8%, decays to 1.5%
    # Formula: rate = 1.5 + 6.5 * exp(-0.15 * year)
    n_points = 50
    points = []
    for i in range(n_points):
        x_frac = i / (n_points - 1)
        year = x_frac * 15
        rate = 1.5 + 6.5 * math.exp(-0.15 * year)
        # Map rate (1.5 to 8.0) to chart y
        y_frac = 1.0 - (rate - 1.5) / 6.5
        px = cx + int(x_frac * cw)
        py = cy + int(y_frac * ch)
        points.append((px, py))

    # Draw curve
    for i in range(len(points) - 1):
        d.line([points[i], points[i + 1]], fill=YELLOW, width=2)

    # Animated marker on curve
    marker_idx = int(t * (n_points - 1))
    mx, my = points[marker_idx]
    d.ellipse((mx - 5, my - 5, mx + 5, my + 5), fill=YELLOW, outline=WHITE)

    # Show current rate near marker
    year = t * 15
    rate = 1.5 + 6.5 * math.exp(-0.15 * year)
    rate_text = f"{rate:.1f}%"
    d.text((mx + 8, my - 8), rate_text, fill=YELLOW, font=small_font)

    # Terminal rate line
    terminal_y = cy + ch  # 1.5% maps to bottom
    d.line([(cx, terminal_y), (cx + cw, terminal_y)], fill=lerp_color(DIM, GREEN, 0.4), width=1)

    # === TOP RIGHT: Commission Flow ===
    flow_x, flow_w = 400, 375
    flow_y, flow_h = 72, 160
    draw_rounded_rect(d, (flow_x, flow_y, flow_x + flow_w, flow_y + flow_h), PANEL, BORDER)
    d.text((flow_x + 10, flow_y + 4), "Commission Flow", fill=GREEN, font=header_font)

    # Epoch rewards box
    rew_x, rew_y = flow_x + 20, flow_y + 30
    rew_w, rew_h = 90, 35
    pulse = 0.5 + 0.5 * math.sin(t * math.pi * 3)
    draw_rounded_rect(d, (rew_x, rew_y, rew_x + rew_w, rew_y + rew_h),
                      DARK_BOX, lerp_color(BORDER, CYAN, 0.3 + 0.2 * pulse), r=5)
    d.text((rew_x + 8, rew_y + 4), "Epoch", fill=CYAN, font=small_font)
    d.text((rew_x + 8, rew_y + 18), "Rewards", fill=CYAN, font=small_font)

    # Arrow to validator
    arr_y = rew_y + rew_h // 2
    d.line([(rew_x + rew_w + 3, arr_y), (rew_x + rew_w + 30, arr_y)], fill=YELLOW, width=2)
    d.polygon([(rew_x + rew_w + 30, arr_y),
               (rew_x + rew_w + 24, arr_y - 4),
               (rew_x + rew_w + 24, arr_y + 4)], fill=YELLOW)

    # Validator box
    val_x = rew_x + rew_w + 35
    val_w, val_h = 80, 35
    draw_rounded_rect(d, (val_x, rew_y, val_x + val_w, rew_y + val_h),
                      DARK_BOX, lerp_color(BORDER, ORANGE, 0.4), r=5)
    d.text((val_x + 6, rew_y + 4), "Validator", fill=ORANGE, font=small_font)
    d.text((val_x + 6, rew_y + 18), "10% comm", fill=ORANGE, font=small_font)

    # Two arrows out of validator: commission and staker share
    # Arrow down-right to validator commission
    comm_y = rew_y + val_h + 25
    d.line([(val_x + val_w // 4, rew_y + val_h + 2), (val_x + val_w // 4, comm_y)], fill=ORANGE, width=1)
    d.polygon([(val_x + val_w // 4, comm_y),
               (val_x + val_w // 4 - 3, comm_y - 5),
               (val_x + val_w // 4 + 3, comm_y - 5)], fill=ORANGE)

    comm_box_w = 80
    draw_rounded_rect(d, (val_x - 15, comm_y, val_x - 15 + comm_box_w, comm_y + 28),
                      DARK_BOX, lerp_color(BORDER, ORANGE, 0.3), r=4)
    d.text((val_x - 10, comm_y + 4), "10% -> Val", fill=ORANGE, font=small_font)
    d.text((val_x - 10, comm_y + 16), "(commission)", fill=DIM, font=tiny_font)

    # Arrow right to stakers
    d.line([(val_x + val_w + 3, arr_y), (val_x + val_w + 30, arr_y)], fill=GREEN, width=2)
    d.polygon([(val_x + val_w + 30, arr_y),
               (val_x + val_w + 24, arr_y - 4),
               (val_x + val_w + 24, arr_y + 4)], fill=GREEN)

    stk_x = val_x + val_w + 35
    stk_w = 85
    draw_rounded_rect(d, (stk_x, rew_y, stk_x + stk_w, rew_y + val_h),
                      DARK_BOX, lerp_color(BORDER, GREEN, 0.4), r=5)
    d.text((stk_x + 6, rew_y + 4), "Stakers", fill=GREEN, font=small_font)
    d.text((stk_x + 6, rew_y + 18), "90% share", fill=GREEN, font=small_font)

    # Staker sub-distribution
    staker_y = comm_y
    d.line([(stk_x + stk_w // 2, rew_y + val_h + 2), (stk_x + stk_w // 2, staker_y)], fill=GREEN, width=1)
    d.polygon([(stk_x + stk_w // 2, staker_y),
               (stk_x + stk_w // 2 - 3, staker_y - 5),
               (stk_x + stk_w // 2 + 3, staker_y - 5)], fill=GREEN)
    draw_rounded_rect(d, (stk_x - 5, staker_y, stk_x + stk_w + 5, staker_y + 28),
                      DARK_BOX, lerp_color(BORDER, GREEN, 0.3), r=4)
    d.text((stk_x, staker_y + 4), "Pro-rata by", fill=GREEN, font=small_font)
    d.text((stk_x, staker_y + 16), "stake weight", fill=DIM, font=tiny_font)

    # === BOTTOM: APY comparison + reward distribution ===
    bot_panel_y = 242
    bot_panel_h = 130
    draw_rounded_rect(d, (35, bot_panel_y, W - 35, bot_panel_y + bot_panel_h), PANEL, BORDER)

    # Reward distribution bars (validators)
    d.text((50, bot_panel_y + 8), "Validator Reward Distribution", fill=PURPLE, font=header_font)

    validators = [
        ("Validator A", 25.0, 5, CYAN),    # 25% stake, 5% commission
        ("Validator B", 18.0, 10, GREEN),   # 18% stake, 10% commission
        ("Validator C", 12.0, 8, YELLOW),   # 12% stake, 8% commission
        ("Validator D", 8.0, 0, ORANGE),    # 8% stake, 0% commission
    ]

    bar_x = 170
    bar_max_w = 250
    bar_h = 16
    bar_gap = 8
    bar_start_y = bot_panel_y + 30

    for i, (name, stake_pct, comm, color) in enumerate(validators):
        by = bar_start_y + i * (bar_h + bar_gap)
        # Label
        d.text((50, by + 2), name, fill=color, font=small_font)

        # Stake bar
        bw = int(bar_max_w * stake_pct / 25.0)
        draw_rounded_rect(d, (bar_x, by, bar_x + bw, by + bar_h),
                          lerp_color(DARK_BOX, CYAN_BG, 0.4), lerp_color(BORDER, color, 0.4), r=3)

        # Commission slice (darker portion at end)
        comm_w = max(2, int(bw * comm / 100))
        if comm > 0:
            draw_rounded_rect(d, (bar_x + bw - comm_w, by, bar_x + bw, by + bar_h),
                              lerp_color(DARK_BOX, ORANGE, 0.3), lerp_color(BORDER, ORANGE, 0.3), r=3)

        # Labels
        info = f"{stake_pct:.0f}% stake | {comm}% comm"
        d.text((bar_x + bw + 8, by + 2), info, fill=DIM, font=tiny_font)

    # APY column
    apy_x = 580
    d.text((apy_x, bot_panel_y + 8), "Staker APY", fill=GREEN, font=header_font)

    apys = [
        ("Val A (5%)", "7.2%", GREEN),
        ("Val B (10%)", "6.8%", GREEN),
        ("Val C (8%)", "6.9%", YELLOW),
        ("Val D (0%)", "7.5%", CYAN),
    ]
    for i, (label, apy, color) in enumerate(apys):
        ay = bar_start_y + i * (bar_h + bar_gap)
        d.text((apy_x, ay + 2), f"{label}: ", fill=DIM, font=tiny_font)
        apy_pulse = 0.6 + 0.4 * math.sin(t * math.pi * 2 + i)
        d.text((apy_x + 85, ay + 2), apy, fill=lerp_color(DIM, color, apy_pulse), font=small_font)

    # === Bottom explanations ===
    exp_y = 385
    draw_rounded_rect(d, (30, exp_y, W - 30, H - 14), PANEL, BORDER)

    explanations = [
        ("Inflation Schedule", "Starts at 8%, decreases 15%/year until 1.5% terminal rate", YELLOW),
        ("Stake-Weighted Rewards", "More stake = more rewards, but APY stays similar for all stakers", GREEN),
        ("Commission = Validator Revenue", "Validators set 0-100% commission on staker rewards", ORANGE),
        ("Effective Staking Rate", "~65% of SOL staked -- unstaked SOL gets diluted by inflation", PURPLE),
    ]
    idx = fi % len(explanations)
    et, ed, ec = explanations[idx]
    etw, _ = text_size(d, et, header_font)
    d.text(((W - etw) // 2, exp_y + 10), et, fill=ec, font=header_font)
    edw, _ = text_size(d, ed, body_font)
    d.text(((W - edw) // 2, exp_y + 32), ed, fill=DIM, font=body_font)

    # Mini inflation numbers
    mini_y = exp_y + 56
    rates = ["8.0%", "6.8%", "5.8%", "4.9%", "4.2%", "3.5%", "3.0%", "2.5%", "2.1%", "1.5%"]
    total_mw = len(rates) * 48 + (len(rates) - 1) * 4
    msx = (W - total_mw) // 2
    for i, r in enumerate(rates):
        mx = msx + i * 52
        dist = abs(t * total_mw + msx - (mx + 24))
        hl = max(0, 1.0 - dist / 50)
        c = lerp_color(DIM, YELLOW, hl)
        d.text((mx, mini_y), r, fill=c, font=tiny_font)
        if i < len(rates) - 1:
            d.text((mx + 35, mini_y), "->", fill=BORDER, font=tiny_font)

    return img


if __name__ == "__main__":
    frames = [make_frame(i) for i in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DUR, loop=0, optimize=True)
    print(f"Saved {OUT} ({len(frames)} frames)")
