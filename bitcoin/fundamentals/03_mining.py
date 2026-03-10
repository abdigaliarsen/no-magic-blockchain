"""
TITLE: Bitcoin Mining
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    Bitcoin-specific block mining from scratch. Constructs a coinbase transaction
    (the miner's reward), assembles a block header with version, prev_hash,
    merkle_root, timestamp, difficulty bits, and nonce, then performs Proof-of-Work
    by searching for a nonce that makes the double-SHA-256 hash fall below the
    difficulty target.

KEY CONCEPTS:
    - Coinbase transaction (block reward + collected fees)
    - Block header structure (version, prev_hash, merkle_root, timestamp, bits, nonce)
    - Double SHA-256 hashing (Bitcoin hashes headers twice: SHA256(SHA256(data)))
    - Halving schedule (reward halves every 210,000 blocks: 50 → 25 → 12.5 → ...)
    - Difficulty target derived from compact "bits" representation

PREREQUISITE SCRIPTS:
    - core/01_hashing.py
    - core/04_merkle_trees.py
    - core/05_blockchain.py
    - core/06_consensus_pow.py

REAL-WORLD RELEVANCE:
    This is the core loop every Bitcoin miner runs: collect transactions, build a
    coinbase, compute the Merkle root, fill in the header, then brute-force nonces
    until the hash meets the difficulty target. The halving schedule is what caps
    Bitcoin's supply at 21 million coins.
"""

import hashlib
import struct
import time
import math

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Initial block reward in satoshis (50 BTC = 50 * 10^8 satoshis)
INITIAL_REWARD_SATOSHIS = 50 * 10**8

# Number of blocks between each halving (Bitcoin mainnet value)
HALVING_INTERVAL = 210_000

# How many hex characters of a hash to display (full = 64)
HASH_DISPLAY_LEN = 16

# Box width for visual output
BOX_WIDTH = 55

# Block version — Bitcoin currently uses version 0x20000000 (BIP 9 signaling)
BLOCK_VERSION = 0x20000000

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

def double_sha256(data: bytes) -> bytes:
    """Compute SHA256(SHA256(data)).

    Bitcoin uses double hashing everywhere — block headers, transactions, Merkle
    trees — primarily to guard against length-extension attacks that affect
    single-pass SHA-256.
    """
    first_pass = hashlib.sha256(data).digest()   # 32 raw bytes
    return hashlib.sha256(first_pass).digest()    # hash the hash


def double_sha256_hex(data: bytes) -> str:
    """Double-SHA-256, returned as a hex string for display purposes."""
    return double_sha256(data).hex()


# ----------------------------------------------------------------------------
# Satoshi / BTC helpers
# ----------------------------------------------------------------------------

def satoshis_to_btc(satoshis: int) -> float:
    """Convert satoshis to BTC for human-readable display.

    1 BTC = 100,000,000 satoshis (10^8).
    """
    return satoshis / 10**8


def compute_block_reward(block_height: int) -> int:
    """Calculate the block reward at a given height using the halving schedule.

    Every 210,000 blocks the reward halves. After 64 halvings the reward
    reaches zero (integer division floors to 0), which is when all 21 million
    BTC will have been issued.
    """
    halvings = block_height // HALVING_INTERVAL  # How many halvings have occurred
    if halvings >= 64:
        return 0  # After 64 halvings the reward is 0 (all BTC mined)
    return INITIAL_REWARD_SATOSHIS >> halvings    # Right-shift = divide by 2^halvings


# ----------------------------------------------------------------------------
# Transaction representation
# ----------------------------------------------------------------------------

class TxInput:
    """A simplified transaction input (pointer to a previous output)."""

    def __init__(self, prev_txid: str, prev_index: int, script_sig: str = ""):
        self.prev_txid = prev_txid      # Hash of the transaction we're spending from
        self.prev_index = prev_index    # Which output index in that transaction
        self.script_sig = script_sig    # Unlocking script (simplified as a string)

    def serialize(self) -> bytes:
        """Serialize the input to bytes for hashing."""
        data = bytes.fromhex(self.prev_txid)               # 32 bytes: prev tx hash
        data += struct.pack("<I", self.prev_index)          # 4 bytes: output index (little-endian)
        data += self.script_sig.encode()                    # Variable: script
        return data


class TxOutput:
    """A simplified transaction output (amount + locking script)."""

    def __init__(self, amount_satoshis: int, script_pubkey: str = ""):
        self.amount = amount_satoshis    # Value in satoshis
        self.script_pubkey = script_pubkey  # Locking script (simplified as a string)

    def serialize(self) -> bytes:
        """Serialize the output to bytes for hashing."""
        data = struct.pack("<q", self.amount)               # 8 bytes: amount (little-endian, signed)
        data += self.script_pubkey.encode()                 # Variable: script
        return data


class Transaction:
    """A simplified Bitcoin transaction with inputs and outputs."""

    def __init__(self, inputs: list[TxInput], outputs: list[TxOutput]):
        self.inputs = inputs
        self.outputs = outputs
        self.txid = self._compute_txid()  # Transaction ID = double-SHA-256 of serialized tx

    def _compute_txid(self) -> str:
        """Compute the transaction ID by double-SHA-256 hashing the serialized tx."""
        return double_sha256_hex(self.serialize())

    def serialize(self) -> bytes:
        """Serialize all inputs and outputs to bytes."""
        data = struct.pack("<I", len(self.inputs))          # Input count
        for inp in self.inputs:
            data += inp.serialize()
        data += struct.pack("<I", len(self.outputs))        # Output count
        for out in self.outputs:
            data += out.serialize()
        return data

    def total_output(self) -> int:
        """Sum of all output amounts in satoshis."""
        return sum(out.amount for out in self.outputs)

    def fee(self, input_amounts: list[int]) -> int:
        """Transaction fee = sum(inputs) - sum(outputs).

        We need input amounts passed in because inputs only reference previous
        outputs — the spending amounts aren't stored in the input itself.
        """
        return sum(input_amounts) - self.total_output()


# ----------------------------------------------------------------------------
# Coinbase transaction
# ----------------------------------------------------------------------------

def create_coinbase_tx(block_height: int, total_fees: int, miner_address: str) -> Transaction:
    """Build the coinbase transaction — the first transaction in every block.

    The coinbase is special:
    - It has exactly one input with prev_txid = all zeros and prev_index = 0xFFFFFFFF
    - The input's script_sig can contain arbitrary data (miners often embed messages)
    - The output pays the miner: block_reward + total_fees from all other transactions
    """
    reward = compute_block_reward(block_height)
    total_payout = reward + total_fees  # Miner gets subsidy + fees

    # Coinbase input: prev_txid is 32 zero bytes, prev_index is 0xFFFFFFFF
    coinbase_input = TxInput(
        prev_txid="0" * 64,         # 32 bytes of zeros (no previous tx — new coins)
        prev_index=0xFFFFFFFF,       # Sentinel value marking this as coinbase
        script_sig=f"Height:{block_height}",  # Arbitrary data (BIP 34 requires height)
    )

    # Single output paying the miner
    coinbase_output = TxOutput(
        amount_satoshis=total_payout,
        script_pubkey=f"OP_DUP OP_HASH160 {miner_address} OP_EQUALVERIFY OP_CHECKSIG",
    )

    return Transaction(inputs=[coinbase_input], outputs=[coinbase_output])


# ----------------------------------------------------------------------------
# Merkle tree (Bitcoin-specific double-SHA-256 variant)
# ----------------------------------------------------------------------------

def compute_merkle_root(txids: list[str]) -> str:
    """Build a Merkle tree from transaction IDs using double-SHA-256.

    Bitcoin's Merkle tree:
    1. If odd number of leaves, duplicate the last one
    2. Hash each pair with double-SHA-256(left + right)
    3. Repeat until one root remains
    """
    if not txids:
        return "0" * 64  # Empty block edge case

    # Convert hex txids to raw bytes for hashing
    current_level = [bytes.fromhex(txid) for txid in txids]

    while len(current_level) > 1:
        next_level = []
        # If odd count, duplicate the last element (Bitcoin's rule)
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])

        # Hash consecutive pairs
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]  # Concatenate 32+32 bytes
            parent_hash = double_sha256(combined)                # Double-hash the pair
            next_level.append(parent_hash)

        current_level = next_level  # Move up one level

    return current_level[0].hex()  # Root hash as hex string


# ----------------------------------------------------------------------------
# Block header and mining
# ----------------------------------------------------------------------------

def target_from_bits(bits: int) -> int:
    """Decode the compact "bits" field into a full 256-bit target number.

    Bitcoin's compact format: the first byte is the exponent, the remaining
    three bytes are the coefficient.
        target = coefficient * 2^(8 * (exponent - 3))

    A block's hash must be less than this target to be valid.
    """
    exponent = (bits >> 24) & 0xFF            # Top byte: how many bytes in the target
    coefficient = bits & 0x00FFFFFF           # Bottom 3 bytes: significant digits
    target = coefficient * (1 << (8 * (exponent - 3)))  # Shift coefficient into position
    return target


class BlockHeader:
    """The 80-byte Bitcoin block header — the thing miners actually hash."""

    def __init__(self, version: int, prev_hash: str, merkle_root: str,
                 timestamp: int, bits: int, nonce: int = 0):
        self.version = version            # Protocol version (signals feature support)
        self.prev_hash = prev_hash        # Hash of the previous block header
        self.merkle_root = merkle_root    # Root of the transaction Merkle tree
        self.timestamp = timestamp        # Unix time when miner started working
        self.bits = bits                  # Compact difficulty target
        self.nonce = nonce                # The value miners iterate to find valid hash

    def serialize(self) -> bytes:
        """Pack the header into exactly 80 bytes (Bitcoin's wire format).

        Field sizes: version(4) + prev_hash(32) + merkle_root(32) +
                     timestamp(4) + bits(4) + nonce(4) = 80 bytes
        All integers are little-endian, hashes are in internal byte order.
        """
        data = struct.pack("<I", self.version)                # 4 bytes
        data += bytes.fromhex(self.prev_hash)                 # 32 bytes
        data += bytes.fromhex(self.merkle_root)               # 32 bytes
        data += struct.pack("<I", self.timestamp)              # 4 bytes
        data += struct.pack("<I", self.bits)                   # 4 bytes
        data += struct.pack("<I", self.nonce)                  # 4 bytes
        return data  # Total: 80 bytes

    def hash(self) -> str:
        """Double-SHA-256 of the serialized header — this IS the block hash."""
        return double_sha256_hex(self.serialize())


def mine_block(header: BlockHeader, target: int) -> tuple[int, str, int]:
    """Increment the nonce until the block hash is below the target.

    Returns (nonce, block_hash, attempts) when a valid nonce is found.
    This is the core Proof-of-Work loop that every Bitcoin miner runs.
    """
    attempts = 0
    while True:
        header_bytes = header.serialize()                     # Re-serialize with current nonce
        block_hash_bytes = double_sha256(header_bytes)        # Double-SHA-256
        block_hash_int = int.from_bytes(block_hash_bytes, "big")  # Interpret as big-endian integer

        attempts += 1

        if block_hash_int < target:
            # Found a valid nonce — the hash is below the difficulty target
            return header.nonce, block_hash_bytes.hex(), attempts

        header.nonce += 1  # Try the next nonce


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def _print_box(lines: list[str], title: str = "") -> None:
    """Print content inside a box with Unicode box-drawing characters."""
    width = BOX_WIDTH
    if title:
        # Title centered in the top border
        padding = width - len(title) - 2
        left_pad = padding // 2
        right_pad = padding - left_pad
        print(f"┌{'─' * left_pad} {title} {'─' * right_pad}┐")
    else:
        print(f"┌{'─' * (width + 2)}┐")
    for line in lines:
        # Truncate or pad each line to fit the box
        display = line[:width]
        print(f"│ {display:<{width}} │")
    print(f"└{'─' * (width + 2)}┘")


def _trunc(h: str) -> str:
    """Truncate a hex hash for display."""
    return h[:HASH_DISPLAY_LEN] + "..."


def demo():
    """Mine a Bitcoin block with 5 transactions, showing the full process."""

    print("=" * 60)
    print("  BITCOIN MINING — From Transactions to Block Hash")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Part 1: Halving schedule
    # ------------------------------------------------------------------
    print("\n--- Halving Schedule ---\n")
    print(f"  {'Height Range':<24} {'Reward (BTC)':>14} {'Reward (sats)':>16}")
    print(f"  {'─' * 24} {'─' * 14} {'─' * 16}")
    for i in range(7):
        start = i * HALVING_INTERVAL
        end = start + HALVING_INTERVAL - 1
        reward_sats = compute_block_reward(start)
        reward_btc = satoshis_to_btc(reward_sats)
        print(f"  {start:>7,} – {end:>10,}   {reward_btc:>14.8f} {reward_sats:>16,}")

    total_btc = sum(
        satoshis_to_btc(compute_block_reward(i * HALVING_INTERVAL)) * HALVING_INTERVAL
        for i in range(64)
        if compute_block_reward(i * HALVING_INTERVAL) > 0
    )
    print(f"\n  Total supply cap: {total_btc:,.8f} BTC")

    # ------------------------------------------------------------------
    # Part 2: Create 5 sample transactions
    # ------------------------------------------------------------------
    print("\n--- Sample Transactions ---\n")

    # Simulated input amounts (what each tx spends from previous outputs)
    tx_descriptions = [
        ("Alice → Bob",    0.5,  0.0001),
        ("Bob → Charlie",  0.3,  0.0002),
        ("Dave → Eve",     1.0,  0.0001),
        ("Eve → Frank",    0.25, 0.0003),
        ("Grace → Heidi",  0.75, 0.0001),
    ]

    transactions = []  # Will hold Transaction objects (excluding coinbase)
    total_fees = 0

    for i, (desc, amount_btc, fee_btc) in enumerate(tx_descriptions):
        amount_sats = int(amount_btc * 10**8)
        fee_sats = int(fee_btc * 10**8)
        input_sats = amount_sats + fee_sats  # Input must cover output + fee

        # Build a simple 1-input, 1-output transaction
        tx = Transaction(
            inputs=[TxInput(prev_txid=f"{i:064x}", prev_index=0, script_sig=desc)],
            outputs=[TxOutput(amount_satoshis=amount_sats, script_pubkey=f"PAY:{desc.split('→')[1].strip()}")],
        )
        transactions.append(tx)
        total_fees += fee_sats

        print(f"  Tx {i + 1}: {desc:<20}  {amount_btc:.4f} BTC  (fee: {fee_btc:.4f} BTC)")
        print(f"         txid: {_trunc(tx.txid)}")

    print(f"\n  Total fees: {satoshis_to_btc(total_fees):.4f} BTC ({total_fees:,} satoshis)")

    # ------------------------------------------------------------------
    # Part 3: Create coinbase transaction
    # ------------------------------------------------------------------
    print("\n--- Coinbase Transaction ---\n")

    block_height = 840_000  # Post 4th halving (current era as of 2024)
    miner_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Satoshi's address (for fun)

    coinbase_tx = create_coinbase_tx(block_height, total_fees, miner_address)
    reward_sats = compute_block_reward(block_height)

    _print_box([
        f"Type:       COINBASE (new coins created)",
        f"Height:     {block_height:,}",
        f"Subsidy:    {satoshis_to_btc(reward_sats):.8f} BTC",
        f"Fees:       {satoshis_to_btc(total_fees):.8f} BTC",
        f"Total:      {satoshis_to_btc(reward_sats + total_fees):.8f} BTC",
        f"Miner:      {miner_address[:20]}...",
        f"Txid:       {_trunc(coinbase_tx.txid)}",
    ], title="Coinbase")

    # ------------------------------------------------------------------
    # Part 4: Build Merkle tree
    # ------------------------------------------------------------------
    print("\n--- Merkle Tree ---\n")

    # Coinbase is always the first transaction in the block
    all_txids = [coinbase_tx.txid] + [tx.txid for tx in transactions]

    print("  Leaf transactions (L0):")
    for i, txid in enumerate(all_txids):
        label = "coinbase" if i == 0 else f"tx {i}"
        print(f"    [{label:>8}] {_trunc(txid)}")

    merkle_root = compute_merkle_root(all_txids)
    print(f"\n  Merkle root: {_trunc(merkle_root)}")

    # Show the tree structure visually
    print("\n  Tree structure (6 leaves → 3 pairs → 2 pairs → root):")
    print("       ┌──────┴──────┐")
    print("     ┌─┴─┐       ┌──┴──┐")
    print("   ┌─┴─┐  │    ┌─┴─┐   │")
    print("   L0  L1  L2  L3  L4  L5*")
    print("   (* L5 is a duplicate of L4 — Bitcoin's odd-leaf rule)")

    # ------------------------------------------------------------------
    # Part 5: Assemble and mine the block
    # ------------------------------------------------------------------
    print("\n--- Mining the Block ---\n")

    # Use a low difficulty: require 2 leading hex zeros (target has top byte < 0x01)
    # bits = 0x1f00ffff means exponent=0x1f (31), coefficient=0x00ffff
    # This gives a very easy target suitable for demo purposes
    bits = 0x1f00ffff
    target = target_from_bits(bits)

    prev_block_hash = "0000000000000000000234d8e7bcd9b24a3a1e5e7f6c0d8b4a3b2c1d0e9f8a7b"

    header = BlockHeader(
        version=BLOCK_VERSION,
        prev_hash=prev_block_hash,
        merkle_root=merkle_root,
        timestamp=int(time.time()),
        bits=bits,
        nonce=0,
    )

    # Count leading zeros required
    target_hex = f"{target:064x}"
    leading_zeros = len(target_hex) - len(target_hex.lstrip("0"))

    print(f"  Difficulty bits:  0x{bits:08x}")
    print(f"  Target:           {target_hex[:16]}...")
    print(f"  Leading zeros:    {leading_zeros} hex digits")
    print(f"  Mining...", end=" ", flush=True)

    start_time = time.time()
    nonce, block_hash, attempts = mine_block(header, target)
    elapsed = time.time() - start_time

    print(f"FOUND in {elapsed:.3f}s\n")

    # ------------------------------------------------------------------
    # Part 6: Display the mined block
    # ------------------------------------------------------------------
    print("--- Mined Block ---\n")

    _print_box([
        f"Block #{block_height:,}",
        f"",
        f"version:     0x{BLOCK_VERSION:08x}",
        f"prev_hash:   {_trunc(prev_block_hash)}",
        f"merkle_root: {_trunc(merkle_root)}",
        f"timestamp:   {header.timestamp}",
        f"bits:        0x{bits:08x}",
        f"nonce:       {nonce:,}",
        f"",
        f"─── Result ───────────────────────────────",
        f"block_hash:  {_trunc(block_hash)}",
        f"attempts:    {attempts:,}",
        f"time:        {elapsed:.3f}s",
        f"hash rate:   {attempts / max(elapsed, 0.001):,.0f} H/s",
        f"",
        f"─── Transactions ({len(all_txids)}) ─────────────────",
        f"  [0] coinbase  → {satoshis_to_btc(reward_sats + total_fees):.8f} BTC",
    ] + [
        f"  [{i + 1}] {tx_descriptions[i][0]:<15} → {tx_descriptions[i][1]:.4f} BTC"
        for i in range(len(transactions))
    ], title=f"Block {block_height:,}")

    # ------------------------------------------------------------------
    # Part 7: Verify the block hash
    # ------------------------------------------------------------------
    print("\n--- Verification ---\n")

    # Re-hash the header to confirm the nonce is valid
    header.nonce = nonce
    verify_hash = header.hash()
    verify_int = int(verify_hash, 16)

    is_valid = verify_int < target
    status = "✓ VALID" if is_valid else "✗ INVALID"

    print(f"  Re-hashing header with nonce {nonce:,}...")
    print(f"  Block hash: {_trunc(verify_hash)}")
    print(f"  Hash < Target? {status}")

    # Show that double-SHA-256 differs from single SHA-256
    print("\n--- Double SHA-256 vs Single SHA-256 ---\n")
    sample = b"Bitcoin mining demo"
    single = hashlib.sha256(sample).hexdigest()
    double = double_sha256_hex(sample)
    print(f"  Input:       \"{sample.decode()}\"")
    print(f"  SHA-256:     {single[:32]}...")
    print(f"  SHA-256²:    {double[:32]}...")
    print(f"  (Completely different — double hashing is NOT redundant)\n")


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
