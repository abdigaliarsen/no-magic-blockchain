"""
Generate GIF: P2P Gossip Propagation — information spreads exponentially through the network.
"""

from PIL import Image, ImageDraw, ImageFont
import math

# --- Configuration ---
W, H = 800, 550
FRAMES = 72
DELAY_MS = 90

# Colors
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

# --- Font Loading ---
def load_font(size, bold=False):
    names = []
    if bold:
        names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]
    else:
        names = ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    paths = ["/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/truetype/liberation/",
             "/usr/share/fonts/TTF/", "/usr/share/fonts/"]
    for p in paths:
        for n in names:
            try:
                return ImageFont.truetype(p + n, size)
            except (OSError, IOError):
                pass
    try:
        return ImageFont.truetype(names[0], size)
    except (OSError, IOError):
        return ImageFont.load_default()

font_title = load_font(26, bold=True)
font_header = load_font(14, bold=True)
font_body = load_font(12)
font_small = load_font(10)
font_mono = load_font(12)

# --- Node positions (8 nodes in a circle) ---
NUM_NODES = 8
CX, CY = 400, 260
RADIUS = 150
NODE_R = 22

nodes = []
for i in range(NUM_NODES):
    angle = -math.pi / 2 + 2 * math.pi * i / NUM_NODES
    x = CX + RADIUS * math.cos(angle)
    y = CY + RADIUS * math.sin(angle)
    nodes.append((int(x), int(y)))

# Adjacency: each node connects to its 2 neighbors + one across
edges = []
for i in range(NUM_NODES):
    for j in [(i + 1) % NUM_NODES, (i + 2) % NUM_NODES]:
        edge = tuple(sorted((i, j)))
        if edge not in edges:
            edges.append(edge)

# Neighbor map
neighbors = {i: set() for i in range(NUM_NODES)}
for a, b in edges:
    neighbors[a].add(b)
    neighbors[b].add(a)

# --- Gossip simulation: BFS waves from node 0 ---
SOURCE = 0
wave_assignment = {SOURCE: 0}  # node -> wave number
frontier = {SOURCE}
wave_num = 0
while len(wave_assignment) < NUM_NODES:
    wave_num += 1
    next_frontier = set()
    for n in frontier:
        for nb in neighbors[n]:
            if nb not in wave_assignment:
                wave_assignment[nb] = wave_num
                next_frontier.add(nb)
    frontier = next_frontier
max_wave = max(wave_assignment.values())

# Gossip arrows: (from, to, wave)
gossip_arrows = []
for n, w in sorted(wave_assignment.items(), key=lambda x: x[1]):
    if w == 0:
        continue
    # Find which already-infected neighbor told this node
    for nb in neighbors[n]:
        if wave_assignment.get(nb, 999) == w - 1:
            gossip_arrows.append((nb, n, w))
            break

# --- Frame timing ---
# Frames 0-3: source glows
# Frames 4-8: wave 1 arrows animate
# Frames 9-13: wave 1 nodes light up
# Continue for each wave, then hold
FRAMES_PER_PHASE = 10

def get_phase(frame):
    """Return (wave_showing, sub_phase) where sub_phase: 'arrow' or 'lit'."""
    if frame < 4:
        return (0, 'lit')  # source is lit
    f = frame - 4
    wave = f // (FRAMES_PER_PHASE * 2) + 1
    sub = f % (FRAMES_PER_PHASE * 2)
    if sub < FRAMES_PER_PHASE:
        return (wave, 'arrow', sub / FRAMES_PER_PHASE)
    else:
        return (wave, 'lit', (sub - FRAMES_PER_PHASE) / FRAMES_PER_PHASE)

def node_infected(node_id, frame):
    w = wave_assignment[node_id]
    if w == 0:
        return True
    activate_frame = 4 + (w - 1) * (FRAMES_PER_PHASE * 2) + FRAMES_PER_PHASE
    return frame >= activate_frame

def arrow_progress(arrow_wave, frame):
    """Return 0..1 for how much the arrow is drawn, or -1 if not started."""
    start_frame = 4 + (arrow_wave - 1) * (FRAMES_PER_PHASE * 2)
    end_frame = start_frame + FRAMES_PER_PHASE
    if frame < start_frame:
        return -1
    if frame >= end_frame:
        return 1.0
    return (frame - start_frame) / FRAMES_PER_PHASE

def draw_dashed_arrow(draw, x1, y1, x2, y2, color, progress, dash_len=8, gap_len=5):
    """Draw a dashed line from (x1,y1) toward (x2,y2) up to progress fraction."""
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx * dx + dy * dy)
    if dist == 0:
        return
    # Shorten to not overlap nodes
    shorten = NODE_R + 4
    ux, uy = dx / dist, dy / dist
    sx = x1 + ux * shorten
    sy = y1 + uy * shorten
    ex = x1 + ux * (shorten + (dist - 2 * shorten) * progress)
    ey = y1 + uy * (shorten + (dist - 2 * shorten) * progress)

    total = math.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)
    if total < 2:
        return
    pos = 0
    drawing = True
    while pos < total:
        seg = dash_len if drawing else gap_len
        end_pos = min(pos + seg, total)
        if drawing:
            px1 = sx + ux * pos
            py1 = sy + uy * pos
            px2 = sx + ux * end_pos
            py2 = sy + uy * end_pos
            draw.line([(px1, py1), (px2, py2)], fill=color, width=2)
        pos = end_pos
        drawing = not drawing

    # Arrowhead if progress > 0.8
    if progress > 0.8:
        arr_len = 10
        arr_angle = 0.4
        ax1 = ex - arr_len * math.cos(math.atan2(dy, dx) - arr_angle)
        ay1 = ey - arr_len * math.sin(math.atan2(dy, dx) - arr_angle)
        ax2 = ex - arr_len * math.cos(math.atan2(dy, dx) + arr_angle)
        ay2 = ey - arr_len * math.sin(math.atan2(dy, dx) + arr_angle)
        draw.polygon([(ex, ey), (ax1, ay1), (ax2, ay2)], fill=color)

def lerp_color(c1, c2, t):
    t = max(0, min(1, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

# --- Generate frames ---
frames = []
for frame in range(FRAMES):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((W // 2, 22), "Gossip Propagation", fill=WHITE, font=font_title, anchor="mt")
    draw.text((W // 2, 52), "P2P Network", fill=DIM, font=font_header, anchor="mt")

    # Draw edges (dim lines)
    for a, b in edges:
        ax, ay = nodes[a]
        bx, by = nodes[b]
        draw.line([(ax, ay), (bx, by)], fill=BORDER, width=1)

    # Draw gossip arrows
    for src, dst, w in gossip_arrows:
        prog = arrow_progress(w, frame)
        if prog < 0:
            continue
        sx, sy = nodes[src]
        dx, dy = nodes[dst]
        color = YELLOW if prog < 1.0 else GREEN
        draw_dashed_arrow(draw, sx, sy, dx, dy, color, prog)

    # Draw nodes
    for i, (x, y) in enumerate(nodes):
        infected = node_infected(i, frame)
        if i == SOURCE:
            # Source always glowing
            pulse = 0.5 + 0.5 * math.sin(frame * 0.4)
            glow_r = NODE_R + 6 + int(4 * pulse)
            glow_col = lerp_color(YELLOW_BG, YELLOW, 0.3 + 0.15 * pulse)
            draw.ellipse([x - glow_r, y - glow_r, x + glow_r, y + glow_r], fill=glow_col)
            draw.ellipse([x - NODE_R, y - NODE_R, x + NODE_R, y + NODE_R], fill=YELLOW_BG, outline=YELLOW, width=2)
            draw.text((x, y), "N0", fill=YELLOW, font=font_body, anchor="mm")
        elif infected:
            draw.ellipse([x - NODE_R - 3, y - NODE_R - 3, x + NODE_R + 3, y + NODE_R + 3],
                         fill=GREEN_BG, outline=GREEN, width=1)
            draw.ellipse([x - NODE_R, y - NODE_R, x + NODE_R, y + NODE_R],
                         fill=GREEN_BG, outline=GREEN, width=2)
            draw.text((x, y), f"N{i}", fill=GREEN, font=font_body, anchor="mm")
        else:
            draw.ellipse([x - NODE_R, y - NODE_R, x + NODE_R, y + NODE_R],
                         fill=DARK_BOX, outline=DIM, width=2)
            draw.text((x, y), f"N{i}", fill=DIM, font=font_body, anchor="mm")

    # Wave counter
    infected_count = sum(1 for i in range(NUM_NODES) if node_infected(i, frame))
    current_wave = 0
    for w in range(max_wave + 1):
        af = 4 + (w - 1) * (FRAMES_PER_PHASE * 2) if w > 0 else 0
        if frame >= af:
            current_wave = w

    # Legend box
    lx, ly = 30, 440
    draw.rounded_rectangle([lx, ly, lx + 220, ly + 80], radius=6, fill=PANEL, outline=BORDER)
    draw.text((lx + 10, ly + 8), "Gossip Round:", fill=DIM, font=font_small)
    draw.text((lx + 110, ly + 8), f"{current_wave} / {max_wave}", fill=YELLOW, font=font_header)
    draw.text((lx + 10, ly + 30), "Nodes reached:", fill=DIM, font=font_small)
    draw.text((lx + 110, ly + 30), f"{infected_count} / {NUM_NODES}", fill=GREEN, font=font_header)

    # Progress bar
    bar_x, bar_y = lx + 10, ly + 55
    bar_w, bar_h = 200, 12
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=3, fill=DARK_BOX)
    fill_w = int(bar_w * infected_count / NUM_NODES)
    if fill_w > 0:
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=3, fill=GREEN)

    # Explanation box
    ex, ey = 280, 440
    draw.rounded_rectangle([ex, ey, ex + 490, ey + 80], radius=6, fill=PANEL, outline=BORDER)
    draw.text((ex + 245, ey + 10), "Every node tells its peers", fill=WHITE, font=font_header, anchor="mt")
    draw.text((ex + 245, ey + 32), "exponential spread", fill=YELLOW, font=font_header, anchor="mt")

    # Show wave sizes
    wave_sizes = {}
    for n, w in wave_assignment.items():
        wave_sizes[w] = wave_sizes.get(w, 0) + 1
    wave_text = "  ".join(f"W{w}: {c}" for w, c in sorted(wave_sizes.items()))
    draw.text((ex + 245, ey + 56), wave_text, fill=DIM, font=font_small, anchor="mt")

    # Subtle scan line to ensure frame uniqueness
    scan_x = int(30 + (W - 60) * (frame / (FRAMES - 1)))
    draw.line([(scan_x, H - 2), (scan_x + 3, H - 2)], fill=BORDER)

    frames.append(img)

# --- Save GIF ---
if __name__ == "__main__":
    out = "assets/gifs/core_08_p2p_network.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=DELAY_MS, loop=0, optimize=True)
    print(f"Saved {out} ({len(frames)} frames)")
