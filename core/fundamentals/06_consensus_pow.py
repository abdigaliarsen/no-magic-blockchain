"""
TITLE: Proof of Work Consensus
CATEGORY: core

WHAT THIS IMPLEMENTS:
    A proof-of-work mining system built from scratch. Miners search for a nonce
    value such that the SHA-256 hash of the block header falls below a difficulty
    target, then a difficulty adjustment algorithm adapts the target based on
    how fast blocks are being produced.

KEY CONCEPTS:
    - Mining and nonce search
    - Difficulty targets (leading zero bits)
    - Difficulty adjustment (retargeting based on block times)

PREREQUISITE SCRIPTS:
    - core/01_hashing.py
    - core/05_blockchain.py

REAL-WORLD RELEVANCE:
    Bitcoin uses proof-of-work with SHA-256 double-hashing and adjusts difficulty
    every 2016 blocks to maintain a ~10-minute block interval. This mechanism
    secures hundreds of billions of dollars in value.
"""

import hashlib
import struct
import time

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# The default difficulty in bits — 16 bits means the hash must start with
# 16 leading zero bits (i.e., 4 leading hex zeros like "0000...")
DEFAULT_DIFFICULTY_BITS = 16

# How long we want each block to take (in seconds) for difficulty adjustment
TARGET_BLOCK_TIME = 1.0

# How many blocks between difficulty adjustments
ADJUSTMENT_INTERVAL = 3

# Clamp factor: difficulty can at most double or halve per adjustment
# This prevents wild swings, just like Bitcoin's 4x clamp
MAX_ADJUSTMENT_FACTOR = 2.0

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2.1 — Difficulty Target
# ----------------------------------------------------------------------------

def bits_to_target(difficulty_bits: int) -> int:
    """Convert a difficulty in bits to a numeric target.

    The target is a 256-bit number. A hash must be numerically less than the
    target to be valid. More leading zero bits → smaller target → harder to mine.

    For example, 16 bits of difficulty means the top 16 bits of the 256-bit
    hash must all be zero, so the target is 2^(256-16) - 1.
    """
    # Shift 1 left by (256 - difficulty_bits) to create the threshold
    return (1 << (256 - difficulty_bits)) - 1


def target_to_hex(target: int) -> str:
    """Format a 256-bit target as a 64-character hex string for display."""
    return f"{target:064x}"


# ----------------------------------------------------------------------------
# 2.2 — Block Header
# ----------------------------------------------------------------------------

class BlockHeader:
    """Represents the data that gets hashed during mining.

    In real blockchains, this includes prev_hash, merkle_root, timestamp, etc.
    We keep it simple but faithful to the structure.
    """

    def __init__(self, index: int, prev_hash: str, data: str, timestamp: float):
        self.index = index                  # Block number in the chain
        self.prev_hash = prev_hash          # Hash of the previous block header
        self.data = data                    # Simplified: just a string payload
        self.timestamp = timestamp          # Unix timestamp when mining started

    def serialize(self, nonce: int) -> bytes:
        """Pack header fields + nonce into bytes for hashing.

        We concatenate all fields in a deterministic order so that any change
        to any field (including the nonce) produces a completely different hash.
        """
        # Encode each field into bytes and concatenate
        header_bytes = (
            struct.pack(">I", self.index)               # 4 bytes, big-endian
            + self.prev_hash.encode("utf-8")            # previous hash as ASCII hex
            + self.data.encode("utf-8")                 # payload
            + struct.pack(">d", self.timestamp)         # 8 bytes, double-precision float
            + struct.pack(">Q", nonce)                  # 8 bytes, unsigned 64-bit int
        )
        return header_bytes


# ----------------------------------------------------------------------------
# 2.3 — SHA-256 Hashing
# ----------------------------------------------------------------------------

def sha256(data: bytes) -> str:
    """Compute SHA-256 and return the hex digest.

    We use hashlib here for speed so the demo finishes quickly.
    See core/01_hashing.py for a from-scratch SHA-256 implementation.
    """
    return hashlib.sha256(data).hexdigest()


def hash_to_int(hex_hash: str) -> int:
    """Convert a hex hash string to an integer for numeric comparison with target."""
    return int(hex_hash, 16)


# ----------------------------------------------------------------------------
# 2.4 — Mining (Proof-of-Work Search)
# ----------------------------------------------------------------------------

def mine_block(header: BlockHeader, difficulty_bits: int) -> tuple[int, str, int]:
    """Search for a nonce that makes the block hash fall below the target.

    This is the core of proof-of-work: brute-force trial and error.
    There's no shortcut — you must try nonces one by one until you find
    a hash that satisfies the difficulty requirement.

    Returns:
        (nonce, hash_hex, attempts) — the winning nonce, resulting hash, and
        how many nonces were tried.
    """
    target = bits_to_target(difficulty_bits)   # Compute the numeric threshold
    nonce = 0                                   # Start searching from zero

    while True:
        # Serialize the header with the current nonce candidate
        raw = header.serialize(nonce)

        # Hash it
        hash_hex = sha256(raw)

        # Check if the hash (as a number) is below the target
        if hash_to_int(hash_hex) <= target:
            # Found a valid nonce — the "proof" of work
            return nonce, hash_hex, nonce + 1

        # Not valid — increment and try again
        nonce += 1


# ----------------------------------------------------------------------------
# 2.5 — Block (mined result)
# ----------------------------------------------------------------------------

class MinedBlock:
    """A block that has been successfully mined (header + valid nonce + hash)."""

    def __init__(self, header: BlockHeader, nonce: int, hash_hex: str,
                 attempts: int, mining_time: float, difficulty_bits: int):
        self.header = header
        self.nonce = nonce
        self.hash = hash_hex
        self.attempts = attempts                # How many nonces were tried
        self.mining_time = mining_time          # Seconds spent mining
        self.difficulty_bits = difficulty_bits   # Difficulty used for this block


# ----------------------------------------------------------------------------
# 2.6 — Difficulty Adjustment
# ----------------------------------------------------------------------------

def adjust_difficulty(blocks: list[MinedBlock], current_difficulty: int,
                      target_time: float, interval: int) -> int:
    """Adjust difficulty based on how fast recent blocks were mined.

    If blocks came too fast → increase difficulty (smaller target).
    If blocks came too slow → decrease difficulty (larger target).

    This is analogous to Bitcoin's retarget every 2016 blocks, but we
    use a shorter interval for demonstration purposes.
    """
    if len(blocks) < interval:
        return current_difficulty   # Not enough blocks yet to adjust

    # Look at the last `interval` blocks to measure actual mining speed
    recent_blocks = blocks[-interval:]
    total_time = sum(b.mining_time for b in recent_blocks)

    # Expected time for `interval` blocks at the target rate
    expected_time = target_time * interval

    # Ratio: >1 means blocks were too slow, <1 means too fast
    ratio = total_time / expected_time if expected_time > 0 else 1.0

    # Clamp the ratio to prevent extreme swings
    ratio = max(1.0 / MAX_ADJUSTMENT_FACTOR, min(ratio, MAX_ADJUSTMENT_FACTOR))

    # If blocks were fast (ratio < 1), we need MORE difficulty (more bits)
    # If blocks were slow (ratio > 1), we need LESS difficulty (fewer bits)
    # We adjust by 1 bit at a time for stability
    if ratio < 0.75:
        new_difficulty = current_difficulty + 1     # Blocks too fast → harder
    elif ratio > 1.5:
        new_difficulty = current_difficulty - 1     # Blocks too slow → easier
    else:
        new_difficulty = current_difficulty          # Close enough — no change

    # Never go below 1 bit of difficulty (trivial) or above 32 (too slow for demo)
    new_difficulty = max(1, min(new_difficulty, 32))

    return new_difficulty


# ----------------------------------------------------------------------------
# 2.7 — Proof Verification
# ----------------------------------------------------------------------------

def verify_proof_of_work(header: BlockHeader, nonce: int, difficulty_bits: int) -> bool:
    """Verify that a given nonce actually produces a valid hash below the target.

    This is the key asymmetry of PoW: mining is expensive (millions of hashes),
    but verification is cheap (just one hash + one comparison).
    """
    target = bits_to_target(difficulty_bits)
    raw = header.serialize(nonce)
    hash_hex = sha256(raw)
    return hash_to_int(hash_hex) <= target


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of proof-of-work mining and difficulty adjustment."""

    print("=" * 65)
    print("  PROOF OF WORK CONSENSUS")
    print("=" * 65)

    # ---- Part 1: Mine a chain of blocks at fixed difficulty ----

    difficulty_bits = DEFAULT_DIFFICULTY_BITS
    leading_hex_zeros = difficulty_bits // 4     # 16 bits = 4 hex zeros of "0"

    print(f"\n--- Part 1: Mining Blocks ---")
    print(f"Difficulty: {difficulty_bits} bits "
          f"(hash must start with {leading_hex_zeros} hex zeros)\n")

    blocks: list[MinedBlock] = []
    prev_hash = "0" * 64       # Genesis block has no predecessor

    num_blocks = 5
    for i in range(1, num_blocks + 1):
        # Create a block header with some example data
        data = f"Block #{i} transactions: Alice->Bob {i * 10} coins"
        header = BlockHeader(
            index=i,
            prev_hash=prev_hash,
            data=data,
            timestamp=time.time(),
        )

        print(f"Mining Block #{i}...")

        # Mine it — this is the expensive part
        start = time.time()
        nonce, hash_hex, attempts = mine_block(header, difficulty_bits)
        elapsed = time.time() - start

        # Store the mined block
        block = MinedBlock(header, nonce, hash_hex, attempts, elapsed, difficulty_bits)
        blocks.append(block)

        # Display results
        print(f"  Attempts: {attempts:,}")
        print(f"  Time:     {elapsed:.2f}s")
        print(f"  Nonce:    {nonce:,}")
        print(f"  Hash:     {hash_hex}")

        # Verify the proof (should always pass for a freshly mined block)
        valid = verify_proof_of_work(header, nonce, difficulty_bits)
        print(f"  Valid:    {'YES' if valid else 'NO'}")
        print()

        # Next block's prev_hash is this block's hash — forming the chain
        prev_hash = hash_hex

    # Summary statistics
    total_attempts = sum(b.attempts for b in blocks)
    total_time = sum(b.mining_time for b in blocks)
    print(f"  Total attempts: {total_attempts:,}")
    print(f"  Total time:     {total_time:.2f}s")
    print(f"  Avg time/block: {total_time / len(blocks):.2f}s")

    # ---- Part 2: Show the asymmetry — verification is instant ----

    print(f"\n--- Part 2: Verification Asymmetry ---")
    print("Mining is expensive, but verification is cheap (just 1 hash).\n")

    last_block = blocks[-1]
    start = time.time()
    valid = verify_proof_of_work(
        last_block.header, last_block.nonce, last_block.difficulty_bits
    )
    verify_time = time.time() - start

    print(f"  Mining Block #{last_block.header.index} took:   "
          f"{last_block.mining_time:.4f}s ({last_block.attempts:,} hashes)")
    print(f"  Verifying took:                 {verify_time:.6f}s (1 hash)")
    ratio = last_block.mining_time / verify_time if verify_time > 0 else float("inf")
    print(f"  Mining was ~{ratio:,.0f}x slower than verification")

    # ---- Part 3: Wrong nonce fails verification ----

    print(f"\n--- Part 3: Tamper Detection ---")
    print("Using a wrong nonce must fail verification.\n")

    wrong_nonce = last_block.nonce + 1      # Off by one — should fail
    valid_wrong = verify_proof_of_work(
        last_block.header, wrong_nonce, last_block.difficulty_bits
    )
    print(f"  Correct nonce ({last_block.nonce:,}): "
          f"{'PASS' if verify_proof_of_work(last_block.header, last_block.nonce, last_block.difficulty_bits) else 'FAIL'}")
    print(f"  Wrong nonce   ({wrong_nonce:,}): "
          f"{'PASS' if valid_wrong else 'FAIL'}")

    # ---- Part 4: Difficulty adjustment demo ----

    print(f"\n--- Part 4: Difficulty Adjustment ---")
    print(f"Target block time: {TARGET_BLOCK_TIME:.1f}s")
    print(f"Adjustment every {ADJUSTMENT_INTERVAL} blocks\n")

    # Start with a low difficulty so adjustment is visible
    adj_difficulty = 8      # Very easy — will need to increase
    adj_blocks: list[MinedBlock] = []
    adj_prev_hash = "0" * 64

    num_adj_blocks = 9      # Mine 9 blocks, triggering 2 adjustments
    for i in range(1, num_adj_blocks + 1):
        # Check if it's time to adjust
        if i > 1 and (i - 1) % ADJUSTMENT_INTERVAL == 0:
            old = adj_difficulty
            adj_difficulty = adjust_difficulty(
                adj_blocks, adj_difficulty, TARGET_BLOCK_TIME, ADJUSTMENT_INTERVAL
            )
            if adj_difficulty != old:
                direction = "UP" if adj_difficulty > old else "DOWN"
                print(f"  >> Difficulty adjusted {direction}: "
                      f"{old} bits -> {adj_difficulty} bits\n")
            else:
                print(f"  >> Difficulty unchanged at {adj_difficulty} bits\n")

        header = BlockHeader(
            index=i,
            prev_hash=adj_prev_hash,
            data=f"Adj block {i}",
            timestamp=time.time(),
        )

        start = time.time()
        nonce, hash_hex, attempts = mine_block(header, adj_difficulty)
        elapsed = time.time() - start

        block = MinedBlock(header, nonce, hash_hex, attempts, elapsed, adj_difficulty)
        adj_blocks.append(block)

        print(f"  Block #{i:2d} | diff={adj_difficulty:2d} bits | "
              f"{attempts:>8,} attempts | {elapsed:.3f}s | {hash_hex[:16]}...")

        adj_prev_hash = hash_hex

    # ---- Part 5: Visual chain ----

    print(f"\n--- Part 5: Mined Chain (first {num_blocks} blocks) ---\n")

    for i, block in enumerate(blocks):
        h = block.hash
        ph = block.header.prev_hash
        print(f"Block #{block.header.index}")
        print("┌─────────────────────────────────────────────────────┐")
        print(f"│ prev_hash:  {ph[:24]}...  │")
        print(f"│ data:       {block.header.data[:38]:<38s} │")
        print(f"│ nonce:      {block.nonce:<40,} │")
        print(f"│ difficulty: {block.difficulty_bits:<40} │")
        print(f"│ hash:       {h[:24]}...  │")
        print("└─────────────────────────────────────────────────────┘")
        if i < len(blocks) - 1:
            print("                          │")
            print("                          ▼")

    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
