"""CORE09-A: Shamir's Secret Sharing — split secret into shares, reconstruct with threshold."""
from PIL import Image, ImageDraw, ImageFont
import math, os

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
header_font = load_font(15, True)
body_font = load_font(13)
small_font = load_font(11)
big_font = load_font(18, True)

def text_w(draw, txt, font):
    bb = draw.textbbox((0, 0), txt, font=font)
    return bb[2] - bb[0]

def draw_rounded_box(draw, x, y, w, h, fill, border_col, r=8):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill, outline=border_col, width=2)

def marching_hline(draw, x1, x2, y, color, frame, idx=0):
    dash_len = 6
    offset = (frame * 2 + idx * 5) % (dash_len * 2)
    direction = 1 if x2 > x1 else -1
    length = abs(x2 - x1)
    pos = offset % (dash_len * 2)
    while pos < length:
        sx = x1 + direction * pos
        ex = x1 + direction * min(pos + dash_len, length)
        draw.line([(sx, y), (ex, y)], fill=color, width=2)
        pos += dash_len * 2
    if direction > 0:
        draw.polygon([(x2, y), (x2 - 8, y - 5), (x2 - 8, y + 5)], fill=color)
    else:
        draw.polygon([(x2, y), (x2 + 8, y - 5), (x2 + 8, y + 5)], fill=color)

def marching_vline(draw, x, y1, y2, color, frame, idx=0):
    dash_len = 6
    offset = (frame * 2 + idx * 3) % (dash_len * 2)
    direction = 1 if y2 > y1 else -1
    length = abs(y2 - y1)
    pos = offset % (dash_len * 2)
    while pos < length:
        sy = y1 + direction * pos
        ey = y1 + direction * min(pos + dash_len, length)
        draw.line([(x, sy), (x, ey)], fill=color, width=2)
        pos += dash_len * 2
    if direction > 0:
        draw.polygon([(x, y2), (x - 5, y2 - 8), (x + 5, y2 - 8)], fill=color)
    else:
        draw.polygon([(x, y2), (x - 5, y2 + 8), (x + 5, y2 + 8)], fill=color)

def draw_curve(draw, points, color, width=2):
    """Draw a smooth curve through a list of (x,y) points."""
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=color, width=width)

def poly_y(x, coeffs):
    """Evaluate polynomial: coeffs[0] + coeffs[1]*x + coeffs[2]*x^2 ..."""
    return sum(c * x ** i for i, c in enumerate(coeffs))

def make_frame(f):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    pulse = 0.5 + 0.5 * math.sin(f * 2 * math.pi / FRAMES)

    # Title
    title = "Shamir's Secret Sharing"
    tw = text_w(draw, title, title_font)
    draw.text(((W - tw) // 2, 12), title, fill=CYAN, font=title_font)

    subtitle = "Split a secret into n shares, reconstruct with any k"
    sw = text_w(draw, subtitle, small_font)
    draw.text(((W - sw) // 2, 44), subtitle, fill=DIM, font=small_font)

    # === Left panel: Secret + polynomial curve + shares ===
    panel_x, panel_y = 30, 70
    panel_w, panel_h = 350, 260
    draw_rounded_box(draw, panel_x, panel_y, panel_w, panel_h, PANEL, BORDER)

    lbl = "SPLITTING (k=3, n=5)"
    lbl_w = text_w(draw, lbl, header_font)
    draw.text((panel_x + (panel_w - lbl_w) // 2, panel_y + 8), lbl, fill=ORANGE, font=header_font)

    # Secret box
    sec_x, sec_y = panel_x + 15, panel_y + 35
    sec_w, sec_h = 90, 30
    glow_y = tuple(int(c * (0.7 + 0.3 * pulse)) for c in YELLOW)
    draw_rounded_box(draw, sec_x, sec_y, sec_w, sec_h, YELLOW_BG, glow_y, 4)
    st = "Secret: 42"
    st_w = text_w(draw, st, body_font)
    draw.text((sec_x + (sec_w - st_w) // 2, sec_y + 7), st, fill=YELLOW, font=body_font)

    # Polynomial label
    poly_lbl = "f(x) = 42 + 7x + 3x^2"
    draw.text((sec_x + sec_w + 15, sec_y + 8), poly_lbl, fill=DIM, font=small_font)

    # Draw polynomial curve in a chart area
    chart_x, chart_y = panel_x + 20, panel_y + 75
    chart_w, chart_h = 310, 130

    # Chart background
    draw_rounded_box(draw, chart_x, chart_y, chart_w, chart_h, DARK_BOX, BORDER, 4)

    # Axes
    ax_x = chart_x + 30
    ax_y = chart_y + chart_h - 20
    ax_w = chart_w - 50
    ax_h = chart_h - 35
    draw.line([(ax_x, chart_y + 10), (ax_x, ax_y)], fill=DIM, width=1)
    draw.line([(ax_x, ax_y), (ax_x + ax_w, ax_y)], fill=DIM, width=1)

    # Polynomial coefficients: f(x) = 42 + 7x + 3x^2
    coeffs = [42, 7, 3]
    # Evaluate at x = 1..5 for shares
    share_xs = [1, 2, 3, 4, 5]
    share_ys = [poly_y(x, coeffs) for x in share_xs]
    max_val = max(share_ys) * 1.1

    def to_screen(vx, vy):
        sx = ax_x + (vx / 6) * ax_w
        sy = ax_y - (vy / max_val) * ax_h
        return (int(sx), int(sy))

    # Draw curve
    curve_pts = []
    for i in range(61):
        vx = i * 5.5 / 60
        vy = poly_y(vx, coeffs)
        curve_pts.append(to_screen(vx, vy))
    draw_curve(draw, curve_pts, PURPLE, 2)

    # Draw share points
    share_colors = [CYAN, GREEN, ORANGE, RED, PURPLE]
    share_labels = ["S1", "S2", "S3", "S4", "S5"]
    for i in range(len(share_xs)):
        px, py = to_screen(share_xs[i], share_ys[i])
        r = 5
        # Pulsing highlight on the active share (cycling)
        active = (f * 5 // FRAMES) % 5
        col = share_colors[i]
        if i == active:
            glow_r = int(r + 3 * pulse)
            gcol = tuple(int(c * 0.3) for c in col)
            draw.ellipse([px - glow_r, py - glow_r, px + glow_r, py + glow_r], fill=gcol)
        draw.ellipse([px - r, py - r, px + r, py + r], fill=col)
        draw.text((px + 8, py - 6), f"{share_labels[i]}({share_xs[i]},{share_ys[i]})", fill=col, font=small_font)

    # Arrow from secret to curve
    marching_vline(draw, sec_x + sec_w // 2, sec_y + sec_h, chart_y, YELLOW, f, 0)

    # === Right panel: Reconstruction ===
    rpanel_x = 410
    rpanel_y = 70
    rpanel_w = 360
    rpanel_h = 260
    draw_rounded_box(draw, rpanel_x, rpanel_y, rpanel_w, rpanel_h, PANEL, BORDER)

    # Top half: 3 shares = success
    succ_y = rpanel_y + 8
    succ_lbl = "3 SHARES = RECONSTRUCT"
    succ_lbl_w = text_w(draw, succ_lbl, header_font)
    draw.text((rpanel_x + (rpanel_w - succ_lbl_w) // 2, succ_y), succ_lbl, fill=GREEN, font=header_font)

    # Three share boxes
    share_box_y = succ_y + 28
    share_box_w = 65
    share_gap = 18
    total_share_w = 3 * share_box_w + 2 * share_gap
    share_start_x = rpanel_x + (rpanel_w - total_share_w) // 2
    picked = [0, 2, 4]  # shares S1, S3, S5
    for i, si in enumerate(picked):
        bx = share_start_x + i * (share_box_w + share_gap)
        col = share_colors[si]
        bg = CYAN_BG if si == 0 else GREEN_BG if si == 2 else PURPLE_BG
        draw_rounded_box(draw, bx, share_box_y, share_box_w, 26, bg, col, 4)
        stxt = f"{share_labels[si]}({share_xs[si]},{share_ys[si]})"
        stxt_w = text_w(draw, stxt, small_font)
        draw.text((bx + (share_box_w - stxt_w) // 2, share_box_y + 6), stxt, fill=col, font=small_font)

    # Arrow down to result
    arrow_cx = rpanel_x + rpanel_w // 2
    arrow_top = share_box_y + 30
    arrow_bot = share_box_y + 55
    marching_vline(draw, arrow_cx, arrow_top, arrow_bot, GREEN, f, 2)

    # Result box
    res_y = share_box_y + 58
    res_w = 140
    res_x = rpanel_x + (rpanel_w - res_w) // 2
    glow_g = tuple(int(c * (0.7 + 0.3 * pulse)) for c in GREEN)
    draw_rounded_box(draw, res_x, res_y, res_w, 28, GREEN_BG, glow_g, 4)
    rtxt = "Secret = 42"
    rtxt_w = text_w(draw, rtxt, body_font)
    draw.text((res_x + (res_w - rtxt_w) // 2, res_y + 6), rtxt, fill=GREEN, font=body_font)

    # Checkmark
    draw.text((res_x + res_w + 8, res_y + 5), "OK", fill=GREEN, font=body_font)

    # Divider
    div_y = res_y + 42
    draw.line([(rpanel_x + 20, div_y), (rpanel_x + rpanel_w - 20, div_y)], fill=BORDER, width=1)

    # Bottom half: 2 shares = fail
    fail_y = div_y + 10
    fail_lbl = "2 SHARES = IMPOSSIBLE"
    fail_lbl_w = text_w(draw, fail_lbl, header_font)
    draw.text((rpanel_x + (rpanel_w - fail_lbl_w) // 2, fail_y), fail_lbl, fill=RED, font=header_font)

    # Two share boxes
    fail_box_y = fail_y + 28
    total_fail_w = 2 * share_box_w + share_gap
    fail_start_x = rpanel_x + (rpanel_w - total_fail_w) // 2
    fail_picked = [1, 3]  # S2, S4
    for i, si in enumerate(fail_picked):
        bx = fail_start_x + i * (share_box_w + share_gap)
        col = share_colors[si]
        bg = CYAN_BG if si == 1 else RED_BG
        draw_rounded_box(draw, bx, fail_box_y, share_box_w, 26, bg, col, 4)
        stxt = f"{share_labels[si]}({share_xs[si]},{share_ys[si]})"
        stxt_w = text_w(draw, stxt, small_font)
        draw.text((bx + (share_box_w - stxt_w) // 2, fail_box_y + 6), stxt, fill=col, font=small_font)

    # Arrow down to unknown
    fail_arrow_top = fail_box_y + 30
    fail_arrow_bot = fail_box_y + 55
    marching_vline(draw, arrow_cx, fail_arrow_top, fail_arrow_bot, RED, f, 3)

    # Unknown result
    unk_y = fail_box_y + 58
    unk_w = 140
    unk_x = rpanel_x + (rpanel_w - unk_w) // 2
    glow_r = tuple(int(c * (0.7 + 0.3 * pulse)) for c in RED)
    draw_rounded_box(draw, unk_x, unk_y, unk_w, 28, RED_BG, glow_r, 4)
    utxt = "Secret = ???"
    utxt_w = text_w(draw, utxt, body_font)
    draw.text((unk_x + (unk_w - utxt_w) // 2, unk_y + 6), utxt, fill=RED, font=body_font)
    draw.text((unk_x + unk_w + 8, unk_y + 5), "FAIL", fill=RED, font=body_font)

    # === Bottom panel: Key properties ===
    bot_y = 345
    bot_h = 190
    draw_rounded_box(draw, 30, bot_y, 740, bot_h, PANEL, BORDER)

    props_lbl = "KEY PROPERTIES"
    props_lbl_w = text_w(draw, props_lbl, header_font)
    draw.text(((W - props_lbl_w) // 2, bot_y + 10), props_lbl, fill=CYAN, font=header_font)

    # Three columns of properties
    col_w = 220
    col_gap = 20
    total_col_w = 3 * col_w + 2 * col_gap
    col_start = (W - total_col_w) // 2

    props = [
        ("Threshold", "Any k shares can", "reconstruct the secret", ORANGE, ORANGE),
        ("Security", "Fewer than k shares", "reveal NOTHING", GREEN, GREEN),
        ("No Single Point", "Secret never stored", "in one place", PURPLE, PURPLE),
    ]

    for i, (hdr, line1, line2, hcol, bcol) in enumerate(props):
        cx = col_start + i * (col_w + col_gap)
        cy = bot_y + 38

        # Header
        hdr_w = text_w(draw, hdr, header_font)
        draw.text((cx + (col_w - hdr_w) // 2, cy), hdr, fill=hcol, font=header_font)

        # Box for description
        box_y = cy + 25
        draw_rounded_box(draw, cx + 5, box_y, col_w - 10, 50, DARK_BOX, BORDER, 4)
        l1w = text_w(draw, line1, body_font)
        l2w = text_w(draw, line2, body_font)
        draw.text((cx + 5 + (col_w - 10 - l1w) // 2, box_y + 8), line1, fill=WHITE, font=body_font)
        draw.text((cx + 5 + (col_w - 10 - l2w) // 2, box_y + 26), line2, fill=bcol, font=body_font)

    # Use case
    use = "Used in: key management, multi-sig wallets, distributed custody"
    use_w = text_w(draw, use, small_font)
    draw.text(((W - use_w) // 2, bot_y + bot_h - 30), use, fill=DIM, font=small_font)

    # Scheme label
    scheme = "k-of-n scheme: any 3 of 5 shares recover the secret"
    scheme_w = text_w(draw, scheme, body_font)
    draw.text(((W - scheme_w) // 2, bot_y + bot_h - 52), scheme, fill=YELLOW, font=body_font)

    return img

if __name__ == "__main__":
    frames = [make_frame(f) for f in range(FRAMES)]
    frames[0].save("assets/gifs/core_09_shamirs_secret_sharing.gif", save_all=True,
                   append_images=frames[1:], duration=DELAY, loop=0, optimize=True)
    print("Saved assets/gifs/core_09_shamirs_secret_sharing.gif")
