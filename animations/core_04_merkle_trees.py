"""
Generate an animated GIF infographic: Merkle Tree Structure
Output: assets/gifs/core_04_merkle_trees.gif — 800x550, 36 frames @ 90ms
"""

from PIL import Image, ImageDraw, ImageFont
import hashlib
import math

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
GREEN_BG = (14, 48, 40)
RED_BG = (50, 20, 20)
ORANGE_BG = (60, 35, 15)
PANEL = (17, 21, 28)
DARK_BOX = (22, 27, 35)
BORDER = (40, 50, 65)

W, H = 800, 550
N_FRAMES = 36
DELAY_MS = 90


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


def sha256_short(data: str) -> str:
    """Return first 8 hex chars of SHA-256."""
    return hashlib.sha256(data.encode()).hexdigest()[:8]


def rounded_rect(draw, bbox, radius, fill, outline=None, width=1):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = bbox
    r = radius
    # Four corners
    draw.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill, outline=outline, width=width)
    draw.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill, outline=outline, width=width)
    draw.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill, outline=outline, width=width)
    draw.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill, outline=outline, width=width)
    # Fill rects between corners
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    # Outline edges (if outline)
    if outline:
        draw.line([x0 + r, y0, x1 - r, y0], fill=outline, width=width)
        draw.line([x0 + r, y1, x1 - r, y1], fill=outline, width=width)
        draw.line([x0, y0 + r, x0, y1 - r], fill=outline, width=width)
        draw.line([x1, y0 + r, x1, y1 - r], fill=outline, width=width)


def draw_marching_line(draw, x0, y0, x1, y1, color, frame, dash_len=6, gap_len=4):
    """Draw a dashed line with marching animation along the path."""
    dx = x1 - x0
    dy = y1 - y0
    length = math.sqrt(dx*dx + dy*dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    cycle = dash_len + gap_len
    offset = (frame * 2) % cycle  # marching offset
    t = -offset
    while t < length:
        seg_start = max(t, 0)
        seg_end = min(t + dash_len, length)
        if seg_end > seg_start:
            sx = x0 + ux * seg_start
            sy = y0 + uy * seg_start
            ex = x0 + ux * seg_end
            ey = y0 + uy * seg_end
            draw.line([(sx, sy), (ex, ey)], fill=color, width=2)
        t += cycle


def text_centered(draw, x, y, text, font, fill):
    """Draw text centered at (x, y)."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((x - tw // 2, y - th // 2), text, font=font, fill=fill)


def generate_gif():
    # Fonts
    title_font = _font(20, bold=True)
    node_font = _mono(11)
    label_font = _font(11, bold=True)
    small_font = _font(11)
    badge_font = _font(10, bold=True)
    insight_font = _font(12)
    insight_bold = _font(12, bold=True)

    # Compute hashes for the tree
    tx_labels = ["Tx A", "Tx B", "Tx C", "Tx D"]
    tx_data = ["Alice->Bob 5 BTC", "Bob->Carol 2 BTC", "Dave->Eve 1 BTC", "Frank->Grace 3 BTC"]

    leaf_hashes = [sha256_short(d) for d in tx_data]
    hash_01 = sha256_short(leaf_hashes[0] + leaf_hashes[1])
    hash_23 = sha256_short(leaf_hashes[2] + leaf_hashes[3])
    root_hash = sha256_short(hash_01 + hash_23)

    # Tree layout positions (cx, cy for each node)
    # Level 0 (root): 1 node
    # Level 1: 2 nodes
    # Level 2 (leaves): 4 nodes
    tree_top = 82
    level_gap = 72
    leaf_y = tree_top + level_gap * 2
    mid_y = tree_top + level_gap
    root_y = tree_top

    cx = W // 2
    leaf_spread = 170  # total spread from center to outer leaf
    leaf_xs = [cx - leaf_spread, cx - leaf_spread // 3, cx + leaf_spread // 3, cx + leaf_spread]
    mid_xs = [(leaf_xs[0] + leaf_xs[1]) // 2, (leaf_xs[2] + leaf_xs[3]) // 2]

    # Node dimensions
    leaf_w, leaf_h = 100, 36
    mid_w, mid_h = 110, 36
    root_w, root_h = 130, 42

    # Node info: (cx, cy, w, h, hash_text, color, bg_color, label_below)
    nodes = [
        # Leaves (level 2)
        (leaf_xs[0], leaf_y, leaf_w, leaf_h, leaf_hashes[0], CYAN, CYAN_BG, tx_labels[0]),
        (leaf_xs[1], leaf_y, leaf_w, leaf_h, leaf_hashes[1], CYAN, CYAN_BG, tx_labels[1]),
        (leaf_xs[2], leaf_y, leaf_w, leaf_h, leaf_hashes[2], CYAN, CYAN_BG, tx_labels[2]),
        (leaf_xs[3], leaf_y, leaf_w, leaf_h, leaf_hashes[3], CYAN, CYAN_BG, tx_labels[3]),
        # Mid (level 1)
        (mid_xs[0], mid_y, mid_w, mid_h, hash_01, PURPLE, PURPLE_BG, None),
        (mid_xs[1], mid_y, mid_w, mid_h, hash_23, PURPLE, PURPLE_BG, None),
        # Root (level 0)
        (cx, root_y, root_w, root_h, root_hash, YELLOW, YELLOW_BG, None),
    ]

    # Edges: (child_idx, parent_idx)
    edges = [
        (0, 4), (1, 4),  # leaves to mid-left
        (2, 5), (3, 5),  # leaves to mid-right
        (4, 6), (5, 6),  # mid to root
    ]

    # Insight panel
    panel_y = 310
    panel_h = 95
    panel_x = 40
    panel_w = W - 80

    # Badge area
    badge_y = 425

    frames = []

    for fi in range(N_FRAMES):
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)

        # Draw edges as marching-ant lines (upward flow: child -> parent)
        for ci, pi in edges:
            cn = nodes[ci]
            pn = nodes[pi]
            # Start from top-center of child, end at bottom-center of parent
            x0, y0 = cn[0], cn[1] - cn[3] // 2
            x1, y1 = pn[0], pn[1] + pn[3] // 2
            # Determine color based on parent level
            edge_color = DIM
            if pi == 6:
                edge_color = PURPLE  # edges to root
            elif pi in (4, 5):
                edge_color = CYAN  # edges to mid

            # Dim static line underneath
            draw.line([(x0, y0), (x1, y1)], fill=(30, 38, 50), width=1)
            # Marching ants going UP (from child to parent)
            draw_marching_line(draw, x0, y0, x1, y1, edge_color, fi)

        # Draw nodes
        for i, (ncx, ncy, nw, nh, htxt, col, bgcol, lbl) in enumerate(nodes):
            bx0 = ncx - nw // 2
            by0 = ncy - nh // 2
            bx1 = ncx + nw // 2
            by1 = ncy + nh // 2
            border_col = col

            # Pulsing glow for root
            if i == 6:
                pulse = 0.5 + 0.5 * math.sin(fi * 2 * math.pi / N_FRAMES)
                glow_col = tuple(int(c * 0.3 * pulse) for c in YELLOW)
                rounded_rect(draw, (bx0 - 4, by0 - 4, bx1 + 4, by1 + 4), 10, glow_col)

            rounded_rect(draw, (bx0, by0, bx1, by1), 8, bgcol, outline=border_col, width=2)

            # Hash text inside
            text_centered(draw, ncx, ncy - 2, htxt + "...", node_font, col)

            # Node type label above
            if i < 4:
                text_centered(draw, ncx, ncy + 10, "H(tx)", _font(8), DIM)
            elif i < 6:
                text_centered(draw, ncx, ncy + 10, "H(L+R)", _font(8), DIM)
            else:
                text_centered(draw, ncx, ncy + 14, "ROOT", _font(9, bold=True), YELLOW)

            # Tx label below leaves
            if lbl:
                text_centered(draw, ncx, by1 + 14, lbl, label_font, GREEN)

        # Flow dots: animated dots traveling upward along edges
        for ci, pi in edges:
            cn = nodes[ci]
            pn = nodes[pi]
            x0, y0 = cn[0], cn[1] - cn[3] // 2
            x1, y1 = pn[0], pn[1] + pn[3] // 2
            # Animate a dot traveling up (clamp to edge segment only)
            t = ((fi * 2) % N_FRAMES) / N_FRAMES
            # Two dots staggered
            for offset in [0.0, 0.5]:
                tt = (t + offset) % 1.0
                # Clamp tt to [0.05, 0.95] so dots stay on the visible line
                tt = 0.05 + tt * 0.9
                ax = x0 + (x1 - x0) * tt
                ay = y0 + (y1 - y0) * tt
                dot_col = CYAN if pi in (4, 5) else PURPLE
                r = 3
                draw.ellipse([ax - r, ay - r, ax + r, ay + r], fill=dot_col)

        # Title and subtitle (drawn after tree so they aren't obscured)
        text_centered(draw, cx, 22, "Merkle Tree Structure", title_font, WHITE)
        text_centered(draw, cx, 44, "Binary hash tree: leaves hash up to a single root", small_font, DIM)

        # Insight panel
        rounded_rect(draw, (panel_x, panel_y, panel_x + panel_w, panel_y + panel_h),
                      10, PANEL, outline=BORDER, width=1)

        # Insight text lines
        insights = [
            ("4 transactions", CYAN, " --> ", DIM, "1 root hash", YELLOW),
            ("Change any tx", RED, " --> ", DIM, "root changes completely", ORANGE),
            ("Verify any tx with only", WHITE, " 2 hashes ", GREEN, "(log", DIM),
        ]

        iy = panel_y + 16
        line_gap = 24

        # Line 1: "4 transactions --> 1 root hash"
        parts1 = [("4 transactions", CYAN, insight_bold), ("  -->  ", DIM, insight_font),
                   ("1 root hash", YELLOW, insight_bold)]
        _draw_text_parts(draw, cx, iy, parts1)

        # Line 2: "Change any tx --> root changes completely"
        iy += line_gap
        parts2 = [("Change any transaction", RED, insight_font), ("  -->  ", DIM, insight_font),
                   ("root changes completely", ORANGE, insight_bold)]
        _draw_text_parts(draw, cx, iy, parts2)

        # Line 3: "Verify any tx with only 2 hashes (log2 n)"
        iy += line_gap
        parts3 = [("Verify any tx with only ", WHITE, insight_font),
                   ("2 hashes", GREEN, insight_bold),
                   ("  (log n proofs)", DIM, insight_font)]
        _draw_text_parts(draw, cx, iy, parts3)

        # Bottom badges
        badges = [
            ("Bitcoin blocks", CYAN, CYAN_BG),
            ("Ethereum state", PURPLE, PURPLE_BG),
            ("O(log n) proofs", GREEN, GREEN_BG),
        ]
        badge_total_w = len(badges) * 160 + (len(badges) - 1) * 20
        bx_start = (W - badge_total_w) // 2

        for bi, (btxt, bcol, bbg) in enumerate(badges):
            bx = bx_start + bi * 180
            by = badge_y
            bw, bh = 160, 28
            rounded_rect(draw, (bx, by, bx + bw, by + bh), 14, bbg, outline=bcol, width=1)
            text_centered(draw, bx + bw // 2, by + bh // 2, btxt, badge_font, bcol)

        # Footer
        text_centered(draw, cx, H - 22, "no-magic-blockchain", _font(10), DIM)

        frames.append(img)

    # Save GIF
    frames[0].save(
        "assets/gifs/core_04_merkle_trees.gif",
        save_all=True,
        append_images=frames[1:],
        duration=DELAY_MS,
        loop=0,
        optimize=False,
    )
    print("Saved assets/gifs/core_04_merkle_trees.gif")


def _draw_text_parts(draw, center_x, y, parts):
    """Draw a line of text parts centered at center_x, y. parts = [(text, color, font), ...]"""
    # Measure total width
    total_w = 0
    widths = []
    for text, color, font in parts:
        bb = draw.textbbox((0, 0), text, font=font)
        w = bb[2] - bb[0]
        widths.append(w)
        total_w += w

    # Draw from left
    x = center_x - total_w // 2
    for i, (text, color, font) in enumerate(parts):
        bb = draw.textbbox((0, 0), text, font=font)
        th = bb[3] - bb[1]
        draw.text((x, y - th // 2), text, font=font, fill=color)
        x += widths[i]


if __name__ == "__main__":
    generate_gif()
