"""
TITLE: Bitcoin Difficulty Adjustment Algorithm
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    The Bitcoin difficulty retarget algorithm that adjusts the proof-of-work
    target every 2016 blocks to maintain an average block time of 10 minutes.
    Includes the 4x clamp that prevents extreme difficulty swings.

KEY CONCEPTS:
    - Target: 256-bit number that block hashes must be below
    - Difficulty: inverse of target (higher difficulty = lower target = harder to mine)
    - Retarget period: every 2016 blocks (~2 weeks at 10 min/block)
    - Clamp: difficulty can change by at most 4x per period (up or down)

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - core/06_consensus_pow.py (proof-of-work basics)

REAL-WORLD RELEVANCE:
    Bitcoin's difficulty adjustment is what keeps block production steady at
    ~10 minutes despite massive changes in mining hash rate. Without it,
    blocks would come too fast (when hashrate rises) or too slow (when it falls).
    This is Bitcoin's self-regulating feedback loop.
"""

import hashlib  # For SHA-256 proof-of-work simulation
import time     # For timing block mining
import random   # For simulating hash rate variation

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Target block time: 10 minutes = 600 seconds
TARGET_BLOCK_TIME = 600  # seconds

# Retarget interval: every 2016 blocks
# 2016 blocks × 10 min = 20,160 min = 2 weeks exactly
RETARGET_INTERVAL = 2016

# Expected time for one retarget period
EXPECTED_PERIOD_TIME = TARGET_BLOCK_TIME * RETARGET_INTERVAL  # 1,209,600 seconds = 2 weeks

# Clamp factor: difficulty can change by at most 4× in either direction
# This prevents a sudden hash rate drop from making difficulty impossibly high,
# or a sudden increase from making it trivially low
MAX_ADJUSTMENT_FACTOR = 4

# Maximum target (easiest difficulty) — this is difficulty 1 in Bitcoin
# In real Bitcoin this is: 0x00000000FFFF0000000000000000000000000000000000000000000000000000
# We use a simpler value for demonstration
MAX_TARGET = (1 << 224) - 1  # 224 bits of ones — easiest possible target

# For simulation: we mine with tiny targets to keep demo fast
SIMULATION_BITS = 20  # Number of leading zero bits required (adjustable)

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

class DifficultyManager:
    """Manages Bitcoin's difficulty adjustment algorithm."""

    def __init__(self, initial_target=None):
        """Initialize with a starting target."""
        # If no target given, start at maximum (easiest difficulty)
        self.current_target = initial_target if initial_target else MAX_TARGET
        self.block_height = 0          # Current block number
        self.epoch_start_time = 0      # Timestamp when current epoch started
        self.history = []              # Track difficulty changes over time

    def calculate_difficulty(self, target=None):
        """
        Difficulty = MAX_TARGET / current_target.

        Higher difficulty means smaller target, meaning fewer valid hashes exist,
        meaning miners need more attempts to find a valid block.
        """
        t = target if target is not None else self.current_target
        if t == 0:
            return float('inf')
        return MAX_TARGET / t

    def retarget(self, actual_time):
        """
        Adjust the target based on how long the last 2016 blocks took.

        new_target = old_target × (actual_time / expected_time)

        If blocks came too fast (actual < expected):
          → ratio < 1 → target decreases → difficulty increases
        If blocks came too slow (actual > expected):
          → ratio > 1 → target increases → difficulty decreases
        """
        old_target = self.current_target
        old_difficulty = self.calculate_difficulty()

        # Calculate the raw adjustment ratio
        ratio = actual_time / EXPECTED_PERIOD_TIME

        # --- Apply the 4× clamp ---
        # Without this, a sudden 90% hash rate drop would make difficulty 10×,
        # potentially stalling the network for months
        if ratio < 1 / MAX_ADJUSTMENT_FACTOR:
            ratio = 1 / MAX_ADJUSTMENT_FACTOR  # Can't increase difficulty by more than 4×
        elif ratio > MAX_ADJUSTMENT_FACTOR:
            ratio = MAX_ADJUSTMENT_FACTOR       # Can't decrease difficulty by more than 4×

        # Apply the adjustment
        new_target = int(old_target * ratio)

        # Cap at maximum target (minimum difficulty)
        if new_target > MAX_TARGET:
            new_target = MAX_TARGET

        # Ensure target never goes to zero (infinite difficulty)
        if new_target < 1:
            new_target = 1

        new_difficulty = self.calculate_difficulty(new_target)

        # Record this adjustment for history
        adjustment_record = {
            'epoch': len(self.history),
            'old_target': old_target,
            'new_target': new_target,
            'old_difficulty': old_difficulty,
            'new_difficulty': new_difficulty,
            'actual_time': actual_time,
            'expected_time': EXPECTED_PERIOD_TIME,
            'ratio': ratio,
            'actual_block_time': actual_time / RETARGET_INTERVAL,
            'clamped': ratio != actual_time / EXPECTED_PERIOD_TIME,
        }
        self.history.append(adjustment_record)

        self.current_target = new_target
        return adjustment_record

    def target_to_compact(self, target=None):
        """
        Convert target to Bitcoin's compact 'nBits' format (4 bytes).

        Format: [exponent] [coefficient_byte1] [coefficient_byte2] [coefficient_byte3]
        target = coefficient × 256^(exponent - 3)

        This is how targets are stored in block headers to save space.
        """
        t = target if target is not None else self.current_target
        if t == 0:
            return 0

        # Find how many bytes we need to represent the target
        target_bytes = t.to_bytes((t.bit_length() + 7) // 8, 'big')
        size = len(target_bytes)

        # Take top 3 bytes as coefficient
        if size >= 3:
            coefficient = target_bytes[:3]
        else:
            coefficient = target_bytes.ljust(3, b'\x00')  # Pad to 3 bytes

        # If high bit is set, we need an extra byte (sign convention)
        if coefficient[0] & 0x80:
            size += 1
            coefficient = b'\x00' + coefficient[:2]

        compact = (size << 24) | int.from_bytes(coefficient[:3], 'big')
        return compact

    def compact_to_hex(self, compact):
        """Format a compact target as a readable hex string."""
        return f"0x{compact:08x}"


def simulate_mining_epoch(target_bits, hash_rate_multiplier=1.0, blocks=10):
    """
    Simulate mining a small number of blocks to estimate time for a full epoch.

    Uses actual SHA-256 hashing with a small target for demonstration.
    Returns the estimated time for RETARGET_INTERVAL blocks.
    """
    # Create a small target based on bits of difficulty
    target = (1 << (256 - target_bits)) - 1

    total_hashes = 0
    for block in range(blocks):
        nonce = random.randint(0, 2**32)
        block_data = f"block_{block}_{random.randint(0, 10**9)}".encode()

        # Mine until we find a hash below the target
        while True:
            header = block_data + nonce.to_bytes(4, 'big')
            hash_result = hashlib.sha256(header).digest()
            hash_int = int.from_bytes(hash_result, 'big')
            total_hashes += 1

            if hash_int <= target:
                break  # Found a valid block!
            nonce += 1

    # Estimate: each hash takes some time, scale by hash rate multiplier
    # Average hashes per block at this difficulty
    avg_hashes_per_block = total_hashes / blocks

    # At baseline, assume 1 hash = finding a block at 10 min
    # Scale by the expected number of hashes for the real difficulty
    estimated_avg_block_time = TARGET_BLOCK_TIME / hash_rate_multiplier
    estimated_epoch_time = estimated_avg_block_time * RETARGET_INTERVAL

    return estimated_epoch_time, avg_hashes_per_block


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Simulate Bitcoin's difficulty adjustment over multiple epochs."""
    print("=" * 72)
    print("  BITCOIN DIFFICULTY ADJUSTMENT ALGORITHM")
    print("=" * 72)

    # --- Explain the mechanism ---
    print(f"""
  Goal: Maintain average block time of {TARGET_BLOCK_TIME // 60} minutes.

  Every {RETARGET_INTERVAL} blocks (~2 weeks), Bitcoin adjusts the difficulty:
    new_target = old_target × (actual_time / expected_time)

  If miners found blocks too fast → decrease target → harder
  If miners found blocks too slow → increase target → easier

  Safety clamp: maximum {MAX_ADJUSTMENT_FACTOR}× change per period (up or down).
  This prevents catastrophic difficulty spirals.
    """)

    # --- Simulate 10 epochs with varying hash rates ---
    print("─" * 72)
    print("  SIMULATION: 10 Retarget Epochs")
    print("─" * 72)

    dm = DifficultyManager()

    # Define hash rate scenarios for each epoch
    # Each tuple: (multiplier relative to baseline, description)
    hash_rate_scenarios = [
        (1.0,  "Baseline hashrate"),
        (1.3,  "New ASIC miners join (+30%)"),
        (1.8,  "Mining farm expansion (+80%)"),
        (2.5,  "Major pool joins (+150%)"),
        (2.5,  "Hashrate stable"),
        (1.2,  "Energy crisis, miners leave (-52%)"),
        (0.5,  "China mining ban (-58%)"),
        (0.5,  "Still reduced hashrate"),
        (1.5,  "Hashrate recovery (+200%)"),
        (3.0,  "New generation ASICs (+100%)"),
    ]

    print(f"\n  {'Epoch':<6} {'Hashrate':>10} {'Actual':>10} {'Expected':>10} "
          f"{'Ratio':>8} {'Difficulty':>14} {'Change':>10}")
    print(f"  {'':─<6} {'':─>10} {'':─>10} {'':─>10} "
          f"{'':─>8} {'':─>14} {'':─>10}")

    for epoch, (hr_mult, description) in enumerate(hash_rate_scenarios):
        # Calculate how long this epoch would take at this hash rate
        # If hash rate doubles, blocks come twice as fast
        actual_time = int(EXPECTED_PERIOD_TIME / hr_mult)

        # Store old difficulty for comparison
        old_diff = dm.calculate_difficulty()

        # Perform the retarget
        record = dm.retarget(actual_time)

        new_diff = record['new_difficulty']
        change_pct = ((new_diff - old_diff) / old_diff) * 100

        # Format times as days
        actual_days = actual_time / 86400
        expected_days = EXPECTED_PERIOD_TIME / 86400

        print(f"  {epoch:<6} {hr_mult:>9.1f}× {actual_days:>8.1f}d {expected_days:>8.1f}d "
              f"{record['ratio']:>8.3f} {new_diff:>14.2f} "
              f"{'↑' if change_pct > 0 else '↓'}{abs(change_pct):>8.1f}%")

        # Print description and clamping info
        note = f"  {' ':>6} └─ {description}"
        if record['clamped']:
            note += " [CLAMPED at 4×]"
        print(note)

    # --- Show detailed breakdown of one adjustment ---
    print("\n" + "─" * 72)
    print("  DETAILED BREAKDOWN: Epoch 3 (Major Pool Joins)")
    print("─" * 72)

    rec = dm.history[3]
    print(f"""
  Hash rate increased 2.5× → blocks arrived 2.5× faster than expected.

  Actual epoch time:   {rec['actual_time']:>12,} seconds ({rec['actual_time']/86400:.1f} days)
  Expected epoch time: {rec['expected_time']:>12,} seconds ({rec['expected_time']/86400:.1f} days)

  Adjustment ratio = actual / expected
                   = {rec['actual_time']:,} / {rec['expected_time']:,}
                   = {rec['actual_time'] / rec['expected_time']:.4f}

  new_target = old_target × {rec['actual_time'] / rec['expected_time']:.4f}
  → Target decreases → Fewer valid hashes → Mining is harder
  → Difficulty: {rec['old_difficulty']:.2f} → {rec['new_difficulty']:.2f}

  Result: block time should return to ~10 minutes.""")

    # --- Show clamping in action ---
    print("\n" + "─" * 72)
    print("  CLAMPING: The Safety Valve")
    print("─" * 72)

    print(f"""
  Without clamping, extreme hash rate changes could be catastrophic:

  Scenario: 90% of miners suddenly go offline
    Actual time:  {EXPECTED_PERIOD_TIME * 10:>12,} seconds (140 days!)
    Raw ratio:    10.0 (would reduce difficulty by 10×)
    Clamped to:   {MAX_ADJUSTMENT_FACTOR:.1f} (max allowed reduction)

  Scenario: Hash rate increases 20× overnight
    Actual time:  {EXPECTED_PERIOD_TIME // 20:>12,} seconds (0.7 days!)
    Raw ratio:    0.05 (would increase difficulty by 20×)
    Clamped to:   {1/MAX_ADJUSTMENT_FACTOR:.2f} (max allowed increase)

  The 4× clamp means it takes multiple epochs to fully adjust,
  but prevents the network from becoming unusable.""")

    # --- Demonstrate clamping math ---
    print("\n  Clamping demonstration:")
    dm_clamp = DifficultyManager()

    # Extreme case: hash rate drops to 1/10
    extreme_slow = EXPECTED_PERIOD_TIME * 10  # 10× too slow
    rec_clamped = dm_clamp.retarget(extreme_slow)

    unclamped_ratio = extreme_slow / EXPECTED_PERIOD_TIME
    print(f"\n  Blocks took 10× too long:")
    print(f"    Unclamped ratio: {unclamped_ratio:.1f}×")
    print(f"    Clamped ratio:   {rec_clamped['ratio']:.1f}× (max {MAX_ADJUSTMENT_FACTOR}×)")
    print(f"    → Difficulty dropped by {MAX_ADJUSTMENT_FACTOR}× instead of {int(unclamped_ratio)}×")
    print(f"    → Takes {int(unclamped_ratio / MAX_ADJUSTMENT_FACTOR + 0.5)} more epochs to fully adjust")

    # --- Show the difficulty curve as ASCII chart ---
    print("\n" + "─" * 72)
    print("  DIFFICULTY CURVE (10 Epochs)")
    print("─" * 72)

    difficulties = [dm.history[0]['old_difficulty']]  # Start with initial
    for rec in dm.history:
        difficulties.append(rec['new_difficulty'])

    max_diff = max(difficulties)
    min_diff = min(difficulties)
    chart_width = 50
    chart_height = 12

    print()
    for row in range(chart_height, -1, -1):
        # Calculate the difficulty value for this row
        if max_diff == min_diff:
            threshold = max_diff
        else:
            threshold = min_diff + (max_diff - min_diff) * row / chart_height

        # Y-axis label
        if row == chart_height:
            label = f"{max_diff:>8.1f}"
        elif row == 0:
            label = f"{min_diff:>8.1f}"
        elif row == chart_height // 2:
            mid = (max_diff + min_diff) / 2
            label = f"{mid:>8.1f}"
        else:
            label = "        "

        # Build the row
        line = f"  {label} │"
        for col in range(len(difficulties)):
            if difficulties[col] >= threshold:
                line += " ██"
            else:
                line += "   "
        print(line)

    # X-axis
    print(f"  {'':>8} └{'───' * len(difficulties)}")
    axis_labels = "  " + " " * 10
    for i in range(len(difficulties)):
        axis_labels += f"{i:<3}"
    print(axis_labels)
    print(f"  {'':>8}   {'Epoch →':^{len(difficulties)*3}}")

    # --- Summary ---
    print("\n" + "─" * 72)
    print("  BITCOIN DIFFICULTY FACTS")
    print("─" * 72)
    print(f"""
  • Retarget every {RETARGET_INTERVAL} blocks (~2 weeks)
  • Target block time: {TARGET_BLOCK_TIME // 60} minutes
  • Maximum adjustment per period: {MAX_ADJUSTMENT_FACTOR}× (up or down)
  • Difficulty 1 (easiest) corresponds to the maximum target
  • As of 2025, Bitcoin difficulty is ~90 trillion (from 1 in 2009)
  • The adjustment algorithm has worked reliably for 15+ years,
    self-correcting through multiple 50%+ hash rate changes
    """)

    print("=" * 72)
    print("  Difficulty adjustment: Bitcoin's self-regulating heartbeat.")
    print("=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
