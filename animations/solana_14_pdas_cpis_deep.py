"""PDAs & CPIs Deep Dive: PDA derivation, CPI flow, and escrow pattern."""
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

OUT = "assets/gifs/solana_14_pdas_cpis_deep.gif"

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
    title = "PDAs & Cross-Program Invocations"
    tw, _ = text_size(d, title, title_font)
    d.text(((W - tw) // 2, 10), title, fill=CYAN, font=title_font)
    sub = "Deterministic addresses and program composability"
    sw, _ = text_size(d, sub, body_font)
    d.text(((W - sw) // 2, 40), sub, fill=DIM, font=body_font)

    # === TOP LEFT: PDA Derivation ===
    pda_x, pda_y = 25, 65
    pda_w, pda_h = 350, 175
    draw_rounded_rect(d, (pda_x, pda_y, pda_x + pda_w, pda_y + pda_h), PANEL, BORDER)
    d.text((pda_x + 12, pda_y + 8), "PDA Derivation", fill=PURPLE, font=header_font)

    # Seed boxes
    seed_y = pda_y + 35
    seeds = [("seed: \"escrow\"", CYAN), ("user_pubkey", GREEN), ("program_id", YELLOW)]
    seed_box_w = 95
    seed_gap = 10
    total_seeds_w = len(seeds) * seed_box_w + (len(seeds) - 1) * seed_gap
    seed_start_x = pda_x + (pda_w - total_seeds_w) // 2

    for i, (label, color) in enumerate(seeds):
        bx = seed_start_x + i * (seed_box_w + seed_gap)
        draw_rounded_rect(d, (bx, seed_y, bx + seed_box_w, seed_y + 28),
                          DARK_BOX, lerp_color(BORDER, color, 0.4), r=4)
        lw, _ = text_size(d, label, tiny_font)
        d.text((bx + (seed_box_w - lw) // 2, seed_y + 7), label, fill=color, font=tiny_font)

    # Arrow down to SHA-256
    hash_y = seed_y + 40
    mid_x = pda_x + pda_w // 2
    d.line([(mid_x, seed_y + 30), (mid_x, hash_y)], fill=DIM, width=1)
    d.polygon([(mid_x, hash_y), (mid_x - 3, hash_y - 5), (mid_x + 3, hash_y - 5)], fill=DIM)

    # SHA-256 box
    hash_box_w = 120
    hash_bx = mid_x - hash_box_w // 2
    hash_col = lerp_color(BORDER, ORANGE, 0.3 + 0.2 * pulse)
    draw_rounded_rect(d, (hash_bx, hash_y, hash_bx + hash_box_w, hash_y + 26),
                      DARK_BOX, hash_col, r=4)
    d.text((hash_bx + 18, hash_y + 5), "SHA-256 Hash", fill=ORANGE, font=small_font)

    # Arrow to check
    check_y = hash_y + 38
    d.line([(mid_x, hash_y + 28), (mid_x, check_y)], fill=DIM, width=1)
    d.polygon([(mid_x, check_y), (mid_x - 3, check_y - 5), (mid_x + 3, check_y - 5)], fill=DIM)

    # Off-curve check box
    check_w = 140
    check_bx = mid_x - check_w // 2
    draw_rounded_rect(d, (check_bx, check_y, check_bx + check_w, check_y + 26),
                      DARK_BOX, lerp_color(BORDER, GREEN, 0.4), r=4)
    d.text((check_bx + 8, check_y + 5), "Off-curve? -> PDA", fill=GREEN, font=small_font)

    # Bump seed note
    d.text((pda_x + 12, check_y + 30), "If on-curve: bump seed 255..0", fill=DIM, font=tiny_font)

    # === TOP RIGHT: CPI Flow ===
    cpi_x, cpi_y = 400, 65
    cpi_w, cpi_h = 375, 175
    draw_rounded_rect(d, (cpi_x, cpi_y, cpi_x + cpi_w, cpi_y + cpi_h), PANEL, BORDER)
    d.text((cpi_x + 12, cpi_y + 8), "CPI: Cross-Program Invocation", fill=GREEN, font=header_font)

    # Program A box
    pa_x, pa_y = cpi_x + 20, cpi_y + 35
    pa_w, pa_h = 100, 55
    draw_rounded_rect(d, (pa_x, pa_y, pa_x + pa_w, pa_y + pa_h),
                      DARK_BOX, lerp_color(BORDER, CYAN, 0.5), r=6)
    d.text((pa_x + 10, pa_y + 6), "Program A", fill=CYAN, font=small_font)
    d.text((pa_x + 10, pa_y + 22), "(Escrow)", fill=DIM, font=tiny_font)
    d.text((pa_x + 10, pa_y + 36), "invoke()", fill=YELLOW, font=tiny_font)

    # Arrow to Program B
    pb_x = cpi_x + 160
    arr_mid_y = pa_y + pa_h // 2
    d.line([(pa_x + pa_w + 3, arr_mid_y), (pb_x - 5, arr_mid_y)], fill=YELLOW, width=2)
    d.polygon([(pb_x - 2, arr_mid_y), (pb_x - 8, arr_mid_y - 4), (pb_x - 8, arr_mid_y + 4)], fill=YELLOW)

    # CPI label on arrow
    d.text((pa_x + pa_w + 7, arr_mid_y - 14), "CPI", fill=YELLOW, font=tiny_font)

    # Program B box
    pb_w, pb_h = 100, 55
    draw_rounded_rect(d, (pb_x, pa_y, pb_x + pb_w, pa_y + pb_h),
                      DARK_BOX, lerp_color(BORDER, GREEN, 0.5), r=6)
    d.text((pb_x + 10, pa_y + 6), "Program B", fill=GREEN, font=small_font)
    d.text((pb_x + 10, pa_y + 22), "(Token)", fill=DIM, font=tiny_font)
    d.text((pb_x + 10, pa_y + 36), "transfer()", fill=ORANGE, font=tiny_font)

    # PDA signer box
    pda_sign_x = pb_x + pb_w + 20
    pda_sign_w = 75
    draw_rounded_rect(d, (pda_sign_x, pa_y + 5, pda_sign_x + pda_sign_w, pa_y + pa_h - 5),
                      PURPLE_BG, lerp_color(BORDER, PURPLE, 0.4 + 0.2 * pulse), r=4)
    d.text((pda_sign_x + 8, pa_y + 12), "PDA", fill=PURPLE, font=small_font)
    d.text((pda_sign_x + 8, pa_y + 28), "Signer", fill=PURPLE, font=small_font)

    # Arrow from PDA to Program B
    d.line([(pda_sign_x, pa_y + pa_h // 2), (pb_x + pb_w + 3, pa_y + pa_h // 2)],
           fill=PURPLE, width=1)

    # Depth note
    d.text((cpi_x + 15, cpi_y + 105), "Max CPI depth: 4 levels", fill=DIM, font=tiny_font)
    d.text((cpi_x + 15, cpi_y + 120), "PDA signs without private key", fill=DIM, font=tiny_font)

    # Signer seeds flow
    d.text((cpi_x + 15, cpi_y + 140), "invoke_signed(&[seeds], program_b, accounts)", fill=ORANGE, font=tiny_font)

    # === BOTTOM: Escrow Pattern ===
    esc_y = 255
    esc_h = 170
    draw_rounded_rect(d, (30, esc_y, W - 30, esc_y + esc_h), PANEL, BORDER)
    d.text((50, esc_y + 8), "Escrow Pattern: Token Swap via PDA", fill=YELLOW, font=header_font)

    # Alice box
    alice_x, actor_y = 55, esc_y + 40
    actor_w, actor_h = 80, 50
    draw_rounded_rect(d, (alice_x, actor_y, alice_x + actor_w, actor_y + actor_h),
                      DARK_BOX, lerp_color(BORDER, CYAN, 0.4), r=5)
    d.text((alice_x + 15, actor_y + 6), "Alice", fill=CYAN, font=small_font)
    d.text((alice_x + 8, actor_y + 24), "10 USDC", fill=DIM, font=tiny_font)

    # PDA Escrow vault
    vault_x = 260
    vault_w = 140
    vault_col = lerp_color(BORDER, PURPLE, 0.4 + 0.2 * pulse)
    draw_rounded_rect(d, (vault_x, actor_y - 8, vault_x + vault_w, actor_y + actor_h + 8),
                      PURPLE_BG, vault_col, r=6)
    d.text((vault_x + 15, actor_y + 2), "PDA Escrow", fill=PURPLE, font=small_font)
    d.text((vault_x + 15, actor_y + 20), "Vault Account", fill=DIM, font=tiny_font)
    d.text((vault_x + 15, actor_y + 36), "owner: program", fill=DIM, font=tiny_font)

    # Bob box
    bob_x = 520
    draw_rounded_rect(d, (bob_x, actor_y, bob_x + actor_w, actor_y + actor_h),
                      DARK_BOX, lerp_color(BORDER, GREEN, 0.4), r=5)
    d.text((bob_x + 20, actor_y + 6), "Bob", fill=GREEN, font=small_font)
    d.text((bob_x + 8, actor_y + 24), "5 SOL", fill=DIM, font=tiny_font)

    # Escrow program box
    ep_x, ep_y = 640, actor_y
    ep_w = 110
    draw_rounded_rect(d, (ep_x, ep_y, ep_x + ep_w, ep_y + actor_h),
                      DARK_BOX, lerp_color(BORDER, YELLOW, 0.4), r=5)
    d.text((ep_x + 10, ep_y + 6), "Escrow", fill=YELLOW, font=small_font)
    d.text((ep_x + 10, ep_y + 22), "Program", fill=YELLOW, font=small_font)
    d.text((ep_x + 10, ep_y + 36), "(on-chain)", fill=DIM, font=tiny_font)

    # Flow arrows
    # Alice -> Vault (deposit)
    arr1_y = actor_y + 15
    d.line([(alice_x + actor_w + 3, arr1_y), (vault_x - 5, arr1_y)], fill=CYAN, width=2)
    d.polygon([(vault_x - 2, arr1_y), (vault_x - 8, arr1_y - 4), (vault_x - 8, arr1_y + 4)], fill=CYAN)
    d.text((alice_x + actor_w + 15, arr1_y - 14), "deposit", fill=CYAN, font=tiny_font)

    # Vault -> Bob (release)
    arr2_y = actor_y + actor_h - 12
    d.line([(vault_x + vault_w + 3, arr2_y), (bob_x - 5, arr2_y)], fill=GREEN, width=2)
    d.polygon([(bob_x - 2, arr2_y), (bob_x - 8, arr2_y - 4), (bob_x - 8, arr2_y + 4)], fill=GREEN)
    d.text((vault_x + vault_w + 10, arr2_y - 14), "release", fill=GREEN, font=tiny_font)

    # Step labels below
    steps_y = actor_y + actor_h + 20
    steps = [
        ("1. Alice deposits USDC into PDA vault", CYAN),
        ("2. Bob sends SOL to Alice", GREEN),
        ("3. Program releases USDC to Bob via CPI", YELLOW),
    ]
    for i, (step, color) in enumerate(steps):
        d.text((55, steps_y + i * 16), step, fill=color, font=small_font)

    # === BOTTOM: Rotating explanations ===
    exp_y = 440
    draw_rounded_rect(d, (30, exp_y, W - 30, H - 14), PANEL, BORDER)
    explanations = [
        ("PDA = Program Derived Address", "Deterministic address with no private key -- only the program can sign", PURPLE),
        ("CPI = Cross-Program Invocation", "Programs call other programs atomically -- composability foundation", GREEN),
        ("invoke_signed()", "Program provides seeds to prove PDA ownership -- runtime verifies derivation", ORANGE),
        ("Bump Seed", "Tries 255..0 until SHA-256(seeds ++ program_id) lands off ed25519 curve", CYAN),
    ]
    idx = fi % len(explanations)
    et, ed, ec = explanations[idx]
    etw, _ = text_size(d, et, header_font)
    d.text(((W - etw) // 2, exp_y + 10), et, fill=ec, font=header_font)
    edw, _ = text_size(d, ed, body_font)
    d.text(((W - edw) // 2, exp_y + 32), ed, fill=DIM, font=body_font)

    # Animated data flow dots in escrow
    dot_phase = (fi % 18) / 18.0
    path = [
        (alice_x + actor_w, arr1_y),
        (vault_x, arr1_y),
        (vault_x + vault_w, arr2_y),
        (bob_x, arr2_y),
    ]
    for dot_i in range(3):
        dp = (dot_phase + dot_i * 0.33) % 1.0
        seg = int(dp * 3)
        seg_t = (dp * 3) - seg
        if seg < len(path) - 1:
            x1, y1 = path[seg]
            x2, y2 = path[seg + 1]
            dx = int(x1 + (x2 - x1) * seg_t)
            dy = int(y1 + (y2 - y1) * seg_t)
            c = CYAN if seg == 0 else GREEN if seg == 2 else PURPLE
            d.ellipse((dx - 3, dy - 3, dx + 3, dy + 3), fill=c)

    return img


if __name__ == "__main__":
    frames = [make_frame(i) for i in range(FRAMES)]
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DUR, loop=0, optimize=True)
    print(f"Saved {OUT} ({len(frames)} frames)")
