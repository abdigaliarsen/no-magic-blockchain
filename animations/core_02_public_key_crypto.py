"""Generate animated GIF: Elliptic Curve Key Generation Flow."""
from PIL import Image, ImageDraw, ImageFont
import math, struct

# === PALETTE ===
BG = (13, 17, 23)
CYAN = (56, 189, 248)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
ORANGE = (251, 146, 60)
RED = (248, 113, 113)
PURPLE = (167, 139, 250)
WHITE = (235, 240, 245)
DIM = (100, 110, 125)
CYAN_BG = (18, 50, 68)
PURPLE_BG = (35, 28, 58)
YELLOW_BG = (58, 50, 14)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)
RED_BG = (58, 22, 22)
GREEN_BG = (18, 50, 38)
ORANGE_BG = (58, 38, 14)

W, H = 800, 550
N_FRAMES = 36
DELAY_MS = 90

# === FONTS ===
def _font(size, bold=False):
    names = (["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold
             else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
    for n in names:
        for d in ["/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/truetype/liberation/"]:
            try: return ImageFont.truetype(d + n, size)
            except (OSError, IOError): continue
    return ImageFont.load_default()

def _mono(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]:
        try: return ImageFont.truetype(p, size)
        except (OSError, IOError): continue
    return ImageFont.load_default()

title_font = _font(26, bold=True)
header_font = _font(14, bold=True)
body_font = _font(12)
small_font = _font(10)
small_bold = _font(10, bold=True)
mono_font = _mono(12)
mono_sm = _mono(10)
subtitle_font = _font(11)

# === HELPERS ===
def rrect(draw, xy, r, fill=None, outline=None, width=1):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    # Clamp radius
    r = min(r, (x1 - x0) // 2, (y1 - y0) // 2)
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)

def txt_c(draw, text, cx, cy, font, fill=WHITE):
    """Draw text centered at (cx, cy)."""
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((cx - tw // 2, cy - th // 2), text, font=font, fill=fill)

def txt_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]

def lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))

def ease_out(t):
    return 1 - (1 - t) ** 3

def draw_arrow_h(draw, x0, y, x1, color, width=2, head=8, dash=False, progress=1.0):
    """Draw horizontal arrow from x0 to x1 at y, with optional dash and progress."""
    actual_x1 = lerp(x0, x1, progress)
    if dash:
        seg = 6
        gap = 4
        cx = x0
        while cx < actual_x1 - head:
            ex = min(cx + seg, actual_x1 - head)
            draw.line([(cx, y), (ex, y)], fill=color, width=width)
            cx = ex + gap
    else:
        draw.line([(x0, y), (actual_x1, y)], fill=color, width=width)
    # arrowhead
    if progress > 0.3:
        draw.polygon([(actual_x1, y), (actual_x1 - head, y - head // 2),
                       (actual_x1 - head, y + head // 2)], fill=color)

def draw_curve_silhouette(draw, cx, cy, size, color, alpha=1.0):
    """Draw a simplified elliptic curve shape (y^2 = x^3 + ax + b silhouette)."""
    points_top = []
    points_bot = []
    for i in range(30):
        t = i / 29.0
        x = -1.2 + t * 2.4
        val = x ** 3 - x + 1  # y^2 = x^3 - x + 1
        if val < 0:
            continue
        y = math.sqrt(val)
        px = int(cx + x * size * 0.38)
        py_t = int(cy - y * size * 0.32)
        py_b = int(cy + y * size * 0.32)
        points_top.append((px, py_t))
        points_bot.append((px, py_b))

    col = tuple(int(c * alpha) + int(BG[i] * (1 - alpha)) for i, c in enumerate(color))
    if len(points_top) > 1:
        draw.line(points_top, fill=col, width=2)
    if len(points_bot) > 1:
        draw.line(points_bot, fill=col, width=2)


def make_frame(fi):
    """Generate frame fi of N_FRAMES."""
    t = fi / (N_FRAMES - 1)  # 0..1 over full loop
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # === TITLE ===
    txt_c(draw, "Elliptic Curve Key Generation", W // 2, 22, title_font, WHITE)
    txt_c(draw, "How a private key becomes a public key", W // 2, 50, subtitle_font, DIM)

    # === FLOW BOXES ===
    # Three boxes: Private Key -> k x G -> Public Key
    box_w, box_h = 185, 130
    box_y = 85
    gap = 60  # gap between boxes for arrows

    # Positions (centered)
    total_w = 3 * box_w + 2 * gap
    start_x = (W - total_w) // 2

    bx1 = start_x
    bx2 = start_x + box_w + gap
    bx3 = start_x + 2 * (box_w + gap)

    # --- Box 1: Private Key (red/orange) ---
    rrect(draw, (bx1, box_y, bx1 + box_w, box_y + box_h), 10,
           fill=RED_BG, outline=RED, width=2)
    txt_c(draw, "PRIVATE KEY", bx1 + box_w // 2, box_y + 16, header_font, RED)

    # Lock icon (simple)
    lx, ly = bx1 + box_w // 2, box_y + 42
    draw.arc((lx - 7, ly - 10, lx + 7, ly + 2), 0, 180, fill=ORANGE, width=2)
    rrect(draw, (lx - 10, ly, lx + 10, ly + 12), 2, fill=ORANGE)

    # Random number that "shifts" occasionally
    shift = (fi // 6) % 4
    hex_vals = ["7a3f9b21c5e8", "d41f0c82a7b3", "92e6f1d054a8", "3b8c27e9f610"]
    hex_str = f"k = {hex_vals[shift]}..."
    txt_c(draw, hex_str, bx1 + box_w // 2, box_y + 75, mono_sm, ORANGE)

    txt_c(draw, "(secret random number)", bx1 + box_w // 2, box_y + 100, small_font, DIM)
    txt_c(draw, "KEEP SECRET", bx1 + box_w // 2, box_y + 115, small_bold, RED)

    # --- Box 2: Curve Operation (purple) ---
    rrect(draw, (bx2, box_y, bx2 + box_w, box_y + box_h), 10,
           fill=PURPLE_BG, outline=PURPLE, width=2)
    txt_c(draw, "CURVE MULTIPLY", bx2 + box_w // 2, box_y + 16, header_font, PURPLE)

    # Formula
    txt_c(draw, "k  x  G", bx2 + box_w // 2, box_y + 44, _font(18, bold=True), WHITE)

    # Draw small curve silhouette inside box
    draw_curve_silhouette(draw, bx2 + box_w // 2, box_y + 82, 80, PURPLE, alpha=0.7)

    # Animated dot on curve
    dot_t = (t * 3) % 1.0
    dot_x_param = -1.2 + dot_t * 2.4
    dot_val = dot_x_param ** 3 - dot_x_param + 1
    if dot_val >= 0:
        dot_y_val = math.sqrt(dot_val)
        # Alternate top/bottom
        sign = 1 if (fi // 12) % 2 == 0 else -1
        dpx = int(bx2 + box_w // 2 + dot_x_param * 80 * 0.38)
        dpy = int(box_y + 82 + sign * (-dot_y_val) * 80 * 0.32)
        draw.ellipse((dpx - 4, dpy - 4, dpx + 4, dpy + 4), fill=YELLOW)

    txt_c(draw, "G = generator point", bx2 + box_w // 2, box_y + 115, small_font, DIM)

    # --- Box 3: Public Key (green) ---
    rrect(draw, (bx3, box_y, bx3 + box_w, box_y + box_h), 10,
           fill=GREEN_BG, outline=GREEN, width=2)
    txt_c(draw, "PUBLIC KEY", bx3 + box_w // 2, box_y + 16, header_font, GREEN)

    # Globe icon (simple circle with lines)
    gx, gy = bx3 + box_w // 2, box_y + 42
    draw.ellipse((gx - 9, gy - 9, gx + 9, gy + 9), outline=GREEN, width=2)
    draw.line([(gx - 9, gy), (gx + 9, gy)], fill=GREEN, width=1)
    draw.line([(gx, gy - 9), (gx, gy + 9)], fill=GREEN, width=1)

    # Coordinates
    txt_c(draw, "P = (x, y)", bx3 + box_w // 2, box_y + 68, mono_font, GREEN)
    txt_c(draw, "x: 4e2d8f....", bx3 + box_w // 2, box_y + 86, mono_sm, (140, 220, 190))
    txt_c(draw, "y: b19c3a....", bx3 + box_w // 2, box_y + 100, mono_sm, (140, 220, 190))
    txt_c(draw, "SHARE FREELY", bx3 + box_w // 2, box_y + 115, small_bold, GREEN)

    # === ANIMATED ARROWS between boxes ===
    arr_y = box_y + box_h // 2

    # Arrow 1: Private Key -> Curve Op
    # Pulsing progress
    a1_prog = ease_out((t * 2) % 1.0)
    a1_color = CYAN
    ax1_start = bx1 + box_w + 4
    ax1_end = bx2 - 4
    draw_arrow_h(draw, ax1_start, arr_y, ax1_end, a1_color, width=3, head=10, progress=a1_prog)

    # Arrow 2: Curve Op -> Public Key
    a2_prog = ease_out(((t * 2) - 0.3) % 1.0) if t > 0.15 else 0
    ax2_start = bx2 + box_w + 4
    ax2_end = bx3 - 4
    draw_arrow_h(draw, ax2_start, arr_y, ax2_end, a2_color := CYAN, width=3, head=10, progress=a2_prog)

    # === TRAPDOOR PANEL ===
    panel_y = 235
    panel_h = 140
    panel_x = 55
    panel_w = W - 110
    rrect(draw, (panel_x, panel_y, panel_x + panel_w, panel_y + panel_h), 10,
           fill=PANEL, outline=BORDER, width=1)

    txt_c(draw, "THE TRAPDOOR FUNCTION", W // 2, panel_y + 16, header_font, YELLOW)

    # Two rows inside panel
    row1_y = panel_y + 48
    row2_y = panel_y + 90

    lbl_x = panel_x + 100
    arr_start_x = panel_x + 190
    arr_end_x = panel_x + panel_w - 190
    time_x = panel_x + panel_w - 100

    # --- Easy direction (top row) ---
    # Label
    txt_c(draw, "FORWARD", lbl_x, row1_y, small_bold, GREEN)

    # Thick green arrow, animated smoothly
    fwd_prog = ease_out((t * 1.5) % 1.0)
    draw_arrow_h(draw, arr_start_x, row1_y, arr_end_x, GREEN, width=4, head=12, progress=fwd_prog)

    # Speed label
    txt_c(draw, "EASY", time_x, row1_y - 10, _font(13, bold=True), GREEN)
    txt_c(draw, "nanoseconds", time_x, row1_y + 8, small_font, (100, 200, 150))

    # --- Hard direction (bottom row) ---
    txt_c(draw, "REVERSE", lbl_x, row2_y, small_bold, RED)

    # Thin dashed red arrow going right-to-left
    rev_prog = ease_out((t * 0.7) % 1.0)
    # Draw reversed (from right to left)
    rev_x1 = arr_end_x
    rev_x0 = arr_start_x
    actual_end = lerp(rev_x1, rev_x0, rev_prog)
    # Dashed line segments
    seg = 6
    gap_d = 5
    cx = rev_x1
    while cx > actual_end + 10:
        ex = max(cx - seg, actual_end + 10)
        draw.line([(cx, row2_y), (ex, row2_y)], fill=RED, width=2)
        cx = ex - gap_d
    # Arrowhead pointing left
    if rev_prog > 0.3:
        ax = actual_end
        draw.polygon([(ax, row2_y), (ax + 8, row2_y - 5), (ax + 8, row2_y + 5)], fill=RED)

    # X mark - animated blinking
    if (fi // 4) % 2 == 0:
        xx = (arr_start_x + arr_end_x) // 2
        draw.line([(xx - 8, row2_y - 8), (xx + 8, row2_y + 8)], fill=RED, width=3)
        draw.line([(xx + 8, row2_y - 8), (xx - 8, row2_y + 8)], fill=RED, width=3)

    txt_c(draw, "IMPOSSIBLE", time_x, row2_y - 10, _font(13, bold=True), RED)
    txt_c(draw, "billions of years", time_x, row2_y + 8, small_font, (200, 120, 120))

    # Divider line between rows
    draw.line([(arr_start_x - 30, (row1_y + row2_y) // 2),
               (arr_end_x + 30, (row1_y + row2_y) // 2)], fill=BORDER, width=1)

    # === INSIGHT TEXT ===
    insight_y = panel_y + panel_h + 18
    txt_c(draw, "Multiplying a point on an elliptic curve is fast,", W // 2, insight_y, body_font, DIM)
    txt_c(draw, "but reversing it (discrete log problem) is computationally infeasible.", W // 2, insight_y + 18, body_font, DIM)

    # === PROPERTY BADGES ===
    badge_y = 430
    badge_h = 45
    badge_w = 220
    badge_gap = 40

    badges = [
        ("Anyone Can Verify", "signatures + ownership", GREEN, GREEN_BG),
        ("Only Owner Signs", "private key required", ORANGE, ORANGE_BG),
        ("One-Way Function", "cannot reverse multiply", PURPLE, PURPLE_BG),
    ]

    total_badges_w = len(badges) * badge_w + (len(badges) - 1) * badge_gap
    badges_start = (W - total_badges_w) // 2

    for i, (title, sub, col, bg) in enumerate(badges):
        bx = badges_start + i * (badge_w + badge_gap)
        # Subtle pulse on one badge at a time
        active = (fi // 12) % 3 == i
        bord = col if active else BORDER
        w = 2 if active else 1
        rrect(draw, (bx, badge_y, bx + badge_w, badge_y + badge_h), 8,
               fill=bg if active else DARK_BOX, outline=bord, width=w)

        # Dot indicator
        draw.ellipse((bx + 10, badge_y + badge_h // 2 - 4,
                       bx + 18, badge_y + badge_h // 2 + 4), fill=col)

        txt_c(draw, title, bx + badge_w // 2 + 6, badge_y + 14, small_bold, col)
        txt_c(draw, sub, bx + badge_w // 2 + 6, badge_y + 30, small_font, DIM)

    # === FOOTER ===
    footer_y = H - 32
    draw.line([(60, footer_y - 8), (W - 60, footer_y - 8)], fill=BORDER, width=1)
    txt_c(draw, "no-magic-blockchain", 130, footer_y + 4, small_font, DIM)
    txt_c(draw, "core/02_public_key_crypto.py", W // 2, footer_y + 4, mono_sm, DIM)

    # Animated scan line (subtle)
    scan_y = int(box_y + (t * (panel_y + panel_h - box_y)))
    draw.line([(30, scan_y), (W - 30, scan_y)], fill=(*CYAN[:3], ), width=1)
    # Make it very subtle by only drawing every other pixel conceptually
    # Actually just use a dim version
    # Overwrite with a dim scanline
    for sx in range(30, W - 30, 3):
        draw.point((sx, scan_y), fill=(CYAN[0] // 4, CYAN[1] // 4, CYAN[2] // 4))

    return img


# === GENERATE GIF ===
frames = [make_frame(i) for i in range(N_FRAMES)]
frames[0].save(
    "assets/gifs/core_02_public_key_crypto.gif",
    save_all=True,
    append_images=frames[1:],
    duration=DELAY_MS,
    loop=0,
    optimize=True,
)
print(f"Saved assets/gifs/core_02_public_key_crypto.gif  ({N_FRAMES} frames, {DELAY_MS}ms)")
