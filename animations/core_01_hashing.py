"""
Generate an animated GIF showing SHA-256 hashing and the avalanche effect.
Style: dark background, colored rounded boxes, arrows, monospace text.
Requires: Pillow (PIL)
Output: assets/gifs/core_01_hashing.gif
"""

import hashlib
from PIL import Image, ImageDraw, ImageFont
import struct

# ============================================================================
# CONFIGURATION
# ============================================================================

WIDTH, HEIGHT = 960, 540
BG = (13, 17, 23)            # GitHub dark bg
BOX_INPUT = (30, 80, 120)    # Blue
BOX_SHA = (120, 50, 80)      # Magenta
BOX_OUTPUT = (20, 100, 80)   # Teal
BOX_CHANGED = (180, 60, 40)  # Red-orange
ARROW_COLOR = (100, 120, 140)
TEXT_WHITE = (220, 225, 230)
TEXT_DIM = (130, 140, 155)
TEXT_ACCENT = (100, 200, 180)
TEXT_TITLE = (200, 210, 225)
HIGHLIGHT = (255, 200, 60)

FONT_SIZE = 18
FONT_SIZE_SM = 14
FONT_SIZE_LG = 26
FONT_SIZE_TITLE = 32

FRAME_DURATION = 120  # ms per frame


def get_font(size):
    """Try to load a monospace font, fall back to default."""
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


FONT = get_font(FONT_SIZE)
FONT_SM = get_font(FONT_SIZE_SM)
FONT_LG = get_font(FONT_SIZE_LG)
FONT_TITLE = get_font(FONT_SIZE_TITLE)


# ============================================================================
# DRAWING HELPERS
# ============================================================================

def rounded_rect(draw, xy, fill, radius=12, outline=None):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def draw_arrow(draw, start, end, color=ARROW_COLOR, width=2):
    """Draw an arrow from start to end."""
    draw.line([start, end], fill=color, width=width)
    # Arrowhead
    import math
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle = math.atan2(dy, dx)
    head_len = 10
    for side in [-1, 1]:
        hx = end[0] - head_len * math.cos(angle + side * 0.4)
        hy = end[1] - head_len * math.sin(angle + side * 0.4)
        draw.line([end, (hx, hy)], fill=color, width=width)


def text_center(draw, text, x, y, font, fill=TEXT_WHITE):
    """Draw text centered at (x, y)."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((x - tw // 2, y - th // 2), text, font=font, fill=fill)


def make_frame():
    """Create a blank frame."""
    return Image.new("RGB", (WIDTH, HEIGHT), BG)


# ============================================================================
# SCENE BUILDERS
# ============================================================================

def scene_title():
    """Title card."""
    frames = []
    img = make_frame()
    draw = ImageDraw.Draw(img)
    text_center(draw, "SHA-256 From Scratch", WIDTH // 2, HEIGHT // 2 - 40,
                FONT_TITLE, TEXT_TITLE)
    text_center(draw, "Hashing & Avalanche Effect", WIDTH // 2, HEIGHT // 2 + 20,
                FONT_LG, TEXT_ACCENT)
    text_center(draw, "core/01_hashing.py", WIDTH // 2, HEIGHT // 2 + 65,
                FONT_SM, TEXT_DIM)
    frames.extend([img] * 12)
    return frames


def scene_hash_flow():
    """Show input → SHA-256 → output flow."""
    frames = []
    input_text = '"hello"'
    hash_out = hashlib.sha256(b"hello").hexdigest()

    # Step 1: Show input box
    img = make_frame()
    draw = ImageDraw.Draw(img)
    text_center(draw, "How SHA-256 Works", WIDTH // 2, 40, FONT_LG, TEXT_TITLE)

    # Input box
    rounded_rect(draw, (60, 120, 280, 190), BOX_INPUT, outline=(60, 130, 200))
    text_center(draw, "Input", 170, 115, FONT_SM, TEXT_DIM)
    text_center(draw, input_text, 170, 155, FONT_LG, TEXT_WHITE)
    frames.extend([img] * 6)

    # Step 2: Add SHA-256 box
    img = img.copy()
    draw = ImageDraw.Draw(img)
    rounded_rect(draw, (360, 120, 600, 190), BOX_SHA, outline=(180, 80, 130))
    text_center(draw, "SHA-256", 480, 150, FONT_LG, TEXT_WHITE)
    text_center(draw, "64 rounds of compression", 480, 180, FONT_SM, TEXT_DIM)
    draw_arrow(draw, (280, 155), (360, 155), ARROW_COLOR, 3)
    frames.extend([img] * 6)

    # Step 3: Add output box
    img = img.copy()
    draw = ImageDraw.Draw(img)
    rounded_rect(draw, (60, 260, 900, 340), BOX_OUTPUT, outline=(40, 160, 130))
    text_center(draw, "Output (256 bits)", 480, 255, FONT_SM, TEXT_DIM)
    text_center(draw, hash_out, 480, 300, FONT, HIGHLIGHT)
    draw_arrow(draw, (480, 190), (480, 260), ARROW_COLOR, 3)
    frames.extend([img] * 6)

    # Step 4: Add properties
    img = img.copy()
    draw = ImageDraw.Draw(img)
    props = [
        "Deterministic — same input always gives same output",
        "One-way — cannot reverse the hash to find input",
        "Fixed size — always 256 bits regardless of input",
    ]
    for i, prop in enumerate(props):
        y = 380 + i * 35
        text_center(draw, f"• {prop}", WIDTH // 2, y, FONT_SM, TEXT_ACCENT)
    frames.extend([img] * 10)

    return frames


def scene_avalanche():
    """Show the avalanche effect — 1 bit change flips ~50% of output."""
    frames = []

    input_a = "hello"
    input_b = "hallo"  # one char change
    hash_a = hashlib.sha256(input_a.encode()).hexdigest()
    hash_b = hashlib.sha256(input_b.encode()).hexdigest()

    # Count bit differences
    bits_a = bin(int(hash_a, 16))[2:].zfill(256)
    bits_b = bin(int(hash_b, 16))[2:].zfill(256)
    flipped = sum(a != b for a, b in zip(bits_a, bits_b))
    pct = flipped / 256 * 100

    # Step 1: Show both inputs
    img = make_frame()
    draw = ImageDraw.Draw(img)
    text_center(draw, "Avalanche Effect", WIDTH // 2, 35, FONT_LG, TEXT_TITLE)
    text_center(draw, "Change 1 character → ~50% of output bits flip",
                WIDTH // 2, 72, FONT_SM, TEXT_DIM)

    # Input A
    rounded_rect(draw, (50, 110, 250, 170), BOX_INPUT, outline=(60, 130, 200))
    text_center(draw, f'"{input_a}"', 150, 140, FONT_LG, TEXT_WHITE)

    # Input B
    rounded_rect(draw, (50, 200, 250, 260), BOX_INPUT, outline=(60, 130, 200))
    # highlight the changed char
    text_center(draw, f'"{input_b}"', 150, 230, FONT_LG, TEXT_WHITE)
    # Mark the difference
    text_center(draw, "e → a", 330, 230, FONT_SM, HIGHLIGHT)

    frames.extend([img] * 8)

    # Step 2: Show both hashes
    img = img.copy()
    draw = ImageDraw.Draw(img)

    # Hash A
    rounded_rect(draw, (30, 300, 930, 355), BOX_OUTPUT, outline=(40, 160, 130))
    draw.text((40, 305), f"  {hash_a}", font=FONT_SM, fill=TEXT_ACCENT)
    draw.text((40, 325), f'  "{input_a}"', font=FONT_SM, fill=TEXT_DIM)
    draw_arrow(draw, (150, 170), (150, 300), ARROW_COLOR, 2)

    # Hash B — color chars that differ
    y_b = 380
    rounded_rect(draw, (30, y_b - 5, 930, y_b + 50), (60, 30, 25), outline=(200, 70, 50))
    x_start = 48
    for i, (ca, cb) in enumerate(zip(hash_a, hash_b)):
        color = (255, 80, 60) if ca != cb else (80, 100, 80)
        draw.text((x_start + i * 13.5, y_b), cb, font=FONT_SM, fill=color)
    draw.text((40, y_b + 22), f'  "{input_b}"', font=FONT_SM, fill=TEXT_DIM)
    draw_arrow(draw, (150, 260), (150, y_b - 5), ARROW_COLOR, 2)

    frames.extend([img] * 8)

    # Step 3: Show stats
    img = img.copy()
    draw = ImageDraw.Draw(img)

    stats_y = 460
    rounded_rect(draw, (200, stats_y - 5, 760, stats_y + 45), (40, 50, 60),
                 outline=(80, 100, 120))
    text_center(draw, f"Bits flipped: {flipped}/256 = {pct:.1f}%",
                480, stats_y + 18, FONT_LG, HIGHLIGHT)

    frames.extend([img] * 14)

    return frames


def scene_bit_grid():
    """Visual bit comparison grid showing which bits flipped."""
    frames = []

    hash_a = hashlib.sha256(b"hello").hexdigest()
    hash_b = hashlib.sha256(b"hallo").hexdigest()
    bits_a = bin(int(hash_a, 16))[2:].zfill(256)
    bits_b = bin(int(hash_b, 16))[2:].zfill(256)

    img = make_frame()
    draw = ImageDraw.Draw(img)
    text_center(draw, "256-Bit Comparison", WIDTH // 2, 30, FONT_LG, TEXT_TITLE)
    text_center(draw, "Red = flipped bit", WIDTH // 2, 60, FONT_SM, TEXT_DIM)

    # Draw 256 small squares in a 32x8 grid
    cell = 10
    gap = 2
    grid_w = 32 * (cell + gap)
    x_off = (WIDTH - grid_w) // 2
    y_off = 90

    for row in range(8):
        for col in range(32):
            idx = row * 32 + col
            same = bits_a[idx] == bits_b[idx]
            color = (30, 60, 50) if same else (220, 60, 40)
            x = x_off + col * (cell + gap)
            y = y_off + row * (cell + gap)
            draw.rectangle([x, y, x + cell, y + cell], fill=color)

    flipped = sum(a != b for a, b in zip(bits_a, bits_b))
    y_bottom = y_off + 8 * (cell + gap) + 20

    # Legend
    draw.rectangle([x_off, y_bottom, x_off + cell, y_bottom + cell],
                   fill=(30, 60, 50))
    draw.text((x_off + 16, y_bottom - 2), "= same", font=FONT_SM, fill=TEXT_DIM)
    draw.rectangle([x_off + 120, y_bottom, x_off + 120 + cell, y_bottom + cell],
                   fill=(220, 60, 40))
    draw.text((x_off + 136, y_bottom - 2), f"= flipped ({flipped}/256)",
              font=FONT_SM, fill=(220, 60, 40))

    # Show the key insight
    text_center(draw, "A tiny input change cascades through all 64 rounds,",
                WIDTH // 2, y_bottom + 60, FONT, TEXT_ACCENT)
    text_center(draw, "producing an essentially random new output.",
                WIDTH // 2, y_bottom + 90, FONT, TEXT_ACCENT)

    # SHA-256 internals summary
    y_box = y_bottom + 140
    rounded_rect(draw, (80, y_box, 880, y_box + 130), (25, 30, 40),
                 outline=(60, 80, 100))
    text_center(draw, "SHA-256 Internals", WIDTH // 2, y_box + 20, FONT, TEXT_TITLE)
    steps = [
        "1. Pad message to 512-bit blocks",
        "2. Expand 16 words → 64 words (message schedule)",
        "3. Run 64 rounds: Ch, Maj, Σ₀, Σ₁, σ₀, σ₁",
        "4. Add compressed result to running hash state",
    ]
    for i, s in enumerate(steps):
        draw.text((120, y_box + 42 + i * 22), s, font=FONT_SM, fill=TEXT_ACCENT)

    frames.extend([img] * 18)
    return frames


# ============================================================================
# MAIN
# ============================================================================

def main():
    frames = []
    frames.extend(scene_title())
    frames.extend(scene_hash_flow())
    frames.extend(scene_avalanche())
    frames.extend(scene_bit_grid())

    # Add a brief pause at end then loop
    frames.extend([frames[-1]] * 5)

    out = "assets/gifs/core_01_hashing.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_DURATION,
        loop=0,
        optimize=True,
    )
    print(f"Saved {out} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
