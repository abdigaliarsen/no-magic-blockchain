"""Generate animated GIF: ECDSA Digital Signatures — Tamper Detection."""

from PIL import Image, ImageDraw, ImageFont
import math
import struct

# =============================================================================
# COLORS
# =============================================================================
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
GREEN_BG = (14, 48, 40)
RED_BG = (50, 20, 20)

PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)

W, H = 800, 550
N_FRAMES = 36
DELAY_MS = 90

# =============================================================================
# FONTS
# =============================================================================
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

title_font = _font(22, bold=True)
subtitle_font = _font(13)
label_font = _font(13, bold=True)
small_font = _font(12)
mono_font = _mono(14)
mono_sm = _mono(12)
badge_font = _font(12, bold=True)
result_font = _font(16, bold=True)
char_font = _mono(15)

# =============================================================================
# HELPERS
# =============================================================================

def draw_rounded_rect(d, xy, radius, fill=None, outline=None, width=1):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    r = radius
    # Corners
    d.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill, outline=outline, width=width)
    d.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill, outline=outline, width=width)
    d.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill, outline=outline, width=width)
    d.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill, outline=outline, width=width)
    # Rectangles filling the gaps
    d.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    d.rectangle([x0, y0 + r, x0 + r, y1 - r], fill=fill)
    d.rectangle([x1 - r, y0 + r, x1, y1 - r], fill=fill)
    # Outline edges (top, bottom, left, right)
    if outline:
        d.line([x0 + r, y0, x1 - r, y0], fill=outline, width=width)
        d.line([x0 + r, y1, x1 - r, y1], fill=outline, width=width)
        d.line([x0, y0 + r, x0, y1 - r], fill=outline, width=width)
        d.line([x1, y0 + r, x1, y1 - r], fill=outline, width=width)


def marching_arrow_v(d, x, y0, y1, color, frame, seg=6, head_size=6):
    """Draw a vertical marching-ant arrow from y0 to y1 at x."""
    offset = frame % (seg * 2)
    y = y0
    while y < y1 - head_size:
        pos_in_cycle = (y - y0 + offset) % (seg * 2)
        if pos_in_cycle < seg:
            end = min(y + seg - pos_in_cycle, y1 - head_size)
            d.line([x, y, x, end], fill=color, width=2)
        y += 1
    # Arrowhead
    ay = y1
    d.polygon([(x, ay), (x - head_size, ay - head_size), (x + head_size, ay - head_size)],
              fill=color)


def draw_char_cells(d, text, x_start, y, highlight_indices=None, highlight_color=YELLOW,
                    normal_bg=DARK_BOX, cell_w=17, cell_h=22):
    """Draw text in individual character cells, optionally highlighting some."""
    for i, ch in enumerate(text):
        cx = x_start + i * cell_w
        bg = normal_bg
        fg = WHITE
        if highlight_indices and i in highlight_indices:
            bg = YELLOW_BG
            fg = highlight_color
        d.rectangle([cx, y, cx + cell_w - 2, y + cell_h], fill=bg, outline=BORDER)
        # Center character in cell
        bbox = d.textbbox((0, 0), ch, font=char_font)
        cw = bbox[2] - bbox[0]
        ch_h = bbox[3] - bbox[1]
        d.text((cx + (cell_w - 2 - cw) // 2, y + (cell_h - ch_h) // 2 - 1), ch,
               fill=fg, font=char_font)
    return cell_w * len(text)


def text_center(d, text, cx, y, font, fill):
    """Draw text centered at cx."""
    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    d.text((cx - tw // 2, y), text, fill=fill, font=font)


def text_width(d, text, font):
    bbox = d.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


# =============================================================================
# FRAME GENERATION
# =============================================================================

def make_frame(fi):
    """Generate frame fi of N_FRAMES."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    t = fi / N_FRAMES  # 0..1 progress

    # --- Title area ---
    text_center(d, "ECDSA Digital Signatures", W // 2, 14, title_font, CYAN)
    text_center(d, "Tamper Detection: Any change to the message invalidates the signature",
                W // 2, 42, subtitle_font, DIM)

    # --- Main panel ---
    panel_x0, panel_y0 = 20, 66
    panel_x1, panel_y1 = W - 20, H - 46
    draw_rounded_rect(d, (panel_x0, panel_y0, panel_x1, panel_y1), 8,
                      fill=PANEL, outline=BORDER)

    mid_x = W // 2
    # Divider line
    d.line([mid_x, panel_y0 + 10, mid_x, panel_y1 - 10], fill=BORDER, width=1)

    # =====================================================================
    # LEFT SIDE — Original Message (GREEN)
    # =====================================================================
    lx = panel_x0 + 20  # left margin for left side
    lw = mid_x - panel_x0 - 40  # available width
    lcx = (panel_x0 + mid_x) // 2  # center x

    # Section label
    text_center(d, "Original Message", lcx, panel_y0 + 14, label_font, GREEN)

    # -- Message box --
    msg_text = "Pay Alice 5 BTC"
    msg_y = panel_y0 + 40
    msg_box_x0 = lcx - 140
    msg_box_x1 = lcx + 140
    msg_box_y1 = msg_y + 50
    draw_rounded_rect(d, (msg_box_x0, msg_y, msg_box_x1, msg_box_y1), 5,
                      fill=DARK_BOX, outline=GREEN)
    # Label
    d.text((msg_box_x0 + 8, msg_y + 4), "MSG", fill=DIM, font=small_font)
    # Character cells for message
    cell_w = 17
    total_w = cell_w * len(msg_text)
    cx_start = lcx - total_w // 2
    draw_char_cells(d, msg_text, cx_start, msg_y + 22)

    # -- Arrow: message -> signature --
    arrow1_y0 = msg_box_y1 + 4
    arrow1_y1 = msg_box_y1 + 40
    marching_arrow_v(d, lcx, arrow1_y0, arrow1_y1, GREEN, fi)

    # Sign label
    d.text((lcx + 10, arrow1_y0 + 8), "Sign", fill=GREEN, font=small_font)

    # -- Signature box --
    sig_y0 = arrow1_y1 + 2
    sig_y1 = sig_y0 + 52
    sig_box_x0 = lcx - 130
    sig_box_x1 = lcx + 130
    draw_rounded_rect(d, (sig_box_x0, sig_y0, sig_box_x1, sig_y1), 5,
                      fill=DARK_BOX, outline=YELLOW)
    d.text((sig_box_x0 + 8, sig_y0 + 4), "SIGNATURE", fill=DIM, font=small_font)
    text_center(d, "(r, s)", lcx, sig_y0 + 22, mono_font, YELLOW)

    # -- Arrow: signature -> verify --
    arrow2_y0 = sig_y1 + 4
    arrow2_y1 = sig_y1 + 40
    marching_arrow_v(d, lcx, arrow2_y0, arrow2_y1, GREEN, fi)

    d.text((lcx + 10, arrow2_y0 + 8), "Verify", fill=GREEN, font=small_font)

    # -- Verify result box --
    ver_y0 = arrow2_y1 + 2
    ver_y1 = ver_y0 + 50
    ver_box_x0 = lcx - 100
    ver_box_x1 = lcx + 100

    # Pulsing green glow effect
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)
    g_fill = tuple(int(GREEN_BG[i] + (GREEN[i] - GREEN_BG[i]) * 0.3 * pulse) for i in range(3))
    draw_rounded_rect(d, (ver_box_x0, ver_y0, ver_box_x1, ver_y1), 5,
                      fill=g_fill, outline=GREEN, width=2)

    # Checkmark + VALID
    text_center(d, "VALID", lcx, ver_y0 + 14, result_font, GREEN)

    # =====================================================================
    # RIGHT SIDE — Tampered Message (RED)
    # =====================================================================
    rx = mid_x + 20
    rw = panel_x1 - mid_x - 40
    rcx = (mid_x + panel_x1) // 2

    # Section label
    text_center(d, "Tampered Message", rcx, panel_y0 + 14, label_font, RED)

    # -- Message box --
    tampered_text = "Pay Alice 50 BTC"
    # The tampered char is the '0' added after '5', so indices shift
    # Original: "Pay Alice 5 BTC" (len=15)
    # Tampered: "Pay Alice 50 BTC" (len=16) — '0' inserted at index 11
    # Highlight '5' and '0' at indices 10 and 11
    tmsg_y = panel_y0 + 40
    tmsg_box_x0 = rcx - 148
    tmsg_box_x1 = rcx + 148
    tmsg_box_y1 = tmsg_y + 50
    draw_rounded_rect(d, (tmsg_box_x0, tmsg_y, tmsg_box_x1, tmsg_box_y1), 5,
                      fill=DARK_BOX, outline=RED)
    d.text((tmsg_box_x0 + 8, tmsg_y + 4), "MSG", fill=DIM, font=small_font)

    # Character cells — highlight the changed chars
    t_cell_w = 17
    t_total_w = t_cell_w * len(tampered_text)
    t_cx_start = rcx - t_total_w // 2

    # Pulsing highlight for tampered characters
    highlight_pulse = 0.6 + 0.4 * math.sin(2 * math.pi * t * 2)
    highlight_col = tuple(int(YELLOW[i] * highlight_pulse + RED[i] * (1 - highlight_pulse))
                          for i in range(3))
    draw_char_cells(d, tampered_text, t_cx_start, tmsg_y + 22,
                    highlight_indices={10, 11}, highlight_color=highlight_col)

    # -- Arrow: message -> signature --
    t_arrow1_y0 = tmsg_box_y1 + 4
    t_arrow1_y1 = tmsg_box_y1 + 40
    marching_arrow_v(d, rcx, t_arrow1_y0, t_arrow1_y1, RED, fi)

    d.text((rcx + 10, t_arrow1_y0 + 8), "Verify", fill=RED, font=small_font)

    # -- Signature box (same signature) --
    t_sig_y0 = t_arrow1_y1 + 2
    t_sig_y1 = t_sig_y0 + 52
    t_sig_box_x0 = rcx - 130
    t_sig_box_x1 = rcx + 130
    draw_rounded_rect(d, (t_sig_box_x0, t_sig_y0, t_sig_box_x1, t_sig_y1), 5,
                      fill=DARK_BOX, outline=YELLOW)
    d.text((t_sig_box_x0 + 8, t_sig_y0 + 4), "SIGNATURE", fill=DIM, font=small_font)
    text_center(d, "(r, s)  same!", rcx, t_sig_y0 + 22, mono_font, YELLOW)

    # -- Arrow: signature -> verify --
    t_arrow2_y0 = t_sig_y1 + 4
    t_arrow2_y1 = t_sig_y1 + 40
    marching_arrow_v(d, rcx, t_arrow2_y0, t_arrow2_y1, RED, fi)

    d.text((rcx + 10, t_arrow2_y0 + 8), "Check", fill=RED, font=small_font)

    # -- Verify result box (INVALID) --
    t_ver_y0 = t_arrow2_y1 + 2
    t_ver_y1 = t_ver_y0 + 50
    t_ver_box_x0 = rcx - 100
    t_ver_box_x1 = rcx + 100

    # Pulsing red glow
    r_pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t + math.pi)
    r_fill = tuple(int(RED_BG[i] + (RED[i] - RED_BG[i]) * 0.25 * r_pulse) for i in range(3))
    draw_rounded_rect(d, (t_ver_box_x0, t_ver_y0, t_ver_box_x1, t_ver_y1), 5,
                      fill=r_fill, outline=RED, width=2)

    # X + INVALID
    text_center(d, "INVALID", rcx, t_ver_y0 + 14, result_font, RED)

    # =====================================================================
    # VS divider emblem
    # =====================================================================
    vs_y = (panel_y0 + panel_y1) // 2 - 10
    d.ellipse([mid_x - 16, vs_y - 12, mid_x + 16, vs_y + 16], fill=BG, outline=BORDER, width=2)
    text_center(d, "vs", mid_x, vs_y - 6, small_font, DIM)

    # =====================================================================
    # Bottom badge
    # =====================================================================
    badge_y = H - 40
    badge_text = "Changing even 1 character breaks the signature"
    btw = text_width(d, badge_text, badge_font)
    bx0 = W // 2 - btw // 2 - 18
    bx1 = W // 2 + btw // 2 + 18
    draw_rounded_rect(d, (bx0, badge_y - 4, bx1, badge_y + 22), 6,
                      fill=CYAN_BG, outline=CYAN)
    text_center(d, badge_text, W // 2, badge_y, badge_font, CYAN)

    return img


# =============================================================================
# MAIN
# =============================================================================

def main():
    frames = [make_frame(i) for i in range(N_FRAMES)]
    frames[0].save(
        "assets/gifs/core_03_digital_signatures.gif",
        save_all=True,
        append_images=frames[1:],
        duration=DELAY_MS,
        loop=0,
        optimize=True,
    )
    print(f"Saved assets/gifs/core_03_digital_signatures.gif  ({N_FRAMES} frames, {DELAY_MS}ms)")

if __name__ == "__main__":
    main()
