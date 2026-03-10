"""
TITLE: Compact Block Relay (BIP 152)
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    Compact block relay protocol that reduces block propagation bandwidth by
    sending short transaction IDs (6-byte SipHash-based) instead of full
    transactions. Receiving nodes reconstruct the full block from their mempool,
    requesting only the transactions they are missing.

KEY CONCEPTS:
    - SipHash-2-4 for generating short 6-byte transaction IDs
    - Compact block = header + short IDs + prefilled transactions (coinbase)
    - Mempool-based reconstruction: match short IDs to known transactions
    - Bandwidth savings: ~99% reduction for well-connected nodes

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - core/05_blockchain.py (block structure)
    - bitcoin/fundamentals/03_mining.py (block construction)

REAL-WORLD RELEVANCE:
    BIP 152 (Compact Blocks) was deployed in Bitcoin Core 0.13.0 (2016). It
    dramatically reduced block relay bandwidth and latency, from ~1MB per block
    to ~15-25KB on average, making faster propagation possible and reducing
    the advantage of well-connected mining pools.
"""

import hashlib  # For SHA-256 hashing
import struct   # For packing bytes in SipHash
import os       # For random nonce generation
import time     # For timestamps

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Short ID length in bytes (BIP 152 uses 6 bytes = 48 bits)
SHORT_ID_LENGTH = 6

# SipHash parameters (SipHash-2-4 as used in Bitcoin)
SIPHASH_C_ROUNDS = 2   # Compression rounds
SIPHASH_D_ROUNDS = 4   # Finalization rounds

# Simulated block parameters
NUM_TRANSACTIONS = 200   # Typical block has ~2000, we use 200 for speed
MEMPOOL_SIZE = 500       # Node's mempool is larger than one block
MEMPOOL_HIT_RATE = 0.95  # 95% of block txs are in our mempool (typical)

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- SipHash-2-4 implementation ---

def _rotl64(x, b):
    """Rotate 64-bit integer left by b bits."""
    return ((x << b) | (x >> (64 - b))) & 0xFFFFFFFFFFFFFFFF


def siphash_2_4(key, data):
    """
    SipHash-2-4: a fast, short-input PRF.
    key: 16 bytes (two 64-bit words k0, k1)
    data: arbitrary bytes
    Returns a 64-bit integer.

    Bitcoin uses SipHash for compact block short IDs because it is:
    1. Fast for short inputs (transaction hashes)
    2. Resistant to hash-flooding attacks
    3. Produces well-distributed outputs with a keyed PRF
    """
    # Parse 16-byte key into two 64-bit little-endian words
    k0 = struct.unpack("<Q", key[:8])[0]
    k1 = struct.unpack("<Q", key[8:16])[0]

    # Initialize state with key XOR'd into constants
    v0 = k0 ^ 0x736F6D6570736575  # "somepseu" in ASCII
    v1 = k1 ^ 0x646F72616E646F6D  # "dorandom"
    v2 = k0 ^ 0x6C7967656E657261  # "lygenera"
    v3 = k1 ^ 0x7465646279746573  # "tedbytes"

    # Process data in 8-byte blocks
    length = len(data)
    # Pad data to process full 8-byte blocks
    blocks = length // 8
    for i in range(blocks):
        m = struct.unpack("<Q", data[i*8:(i+1)*8])[0]
        v3 ^= m
        for _ in range(SIPHASH_C_ROUNDS):
            v0, v1, v2, v3 = _sip_round(v0, v1, v2, v3)
        v0 ^= m

    # Handle last partial block (remaining bytes + length byte)
    last = length & 0xFF  # Length mod 256 goes in the high byte
    remaining = data[blocks * 8:]
    # Pack remaining bytes into a 64-bit word, MSB = length mod 256
    m = last << 56
    for i, byte in enumerate(remaining):
        m |= byte << (i * 8)

    v3 ^= m
    for _ in range(SIPHASH_C_ROUNDS):
        v0, v1, v2, v3 = _sip_round(v0, v1, v2, v3)
    v0 ^= m

    # Finalization
    v2 ^= 0xFF
    for _ in range(SIPHASH_D_ROUNDS):
        v0, v1, v2, v3 = _sip_round(v0, v1, v2, v3)

    return (v0 ^ v1 ^ v2 ^ v3) & 0xFFFFFFFFFFFFFFFF


def _sip_round(v0, v1, v2, v3):
    """One SipHash round: mix the four state words."""
    mask = 0xFFFFFFFFFFFFFFFF
    v0 = (v0 + v1) & mask
    v1 = _rotl64(v1, 13)
    v1 ^= v0
    v0 = _rotl64(v0, 32)
    v2 = (v2 + v3) & mask
    v3 = _rotl64(v3, 16)
    v3 ^= v2
    v0 = (v0 + v3) & mask
    v3 = _rotl64(v3, 21)
    v3 ^= v0
    v2 = (v2 + v1) & mask
    v1 = _rotl64(v1, 17)
    v1 ^= v2
    v2 = _rotl64(v2, 32)
    return v0, v1, v2, v3


# --- Transaction simulation ---

class Transaction:
    """A simplified transaction with a hash (txid)."""
    def __init__(self, sender, receiver, amount, nonce=None):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.nonce = nonce or os.urandom(8).hex()  # Unique per tx
        self.txid = self._compute_txid()
        self.size = 250  # Average transaction size in bytes

    def _compute_txid(self):
        """Transaction ID = SHA-256 of the transaction data."""
        data = f"{self.sender}:{self.receiver}:{self.amount}:{self.nonce}"
        return hashlib.sha256(data.encode()).digest()

    def __repr__(self):
        return f"Tx({self.sender}->{self.receiver}: {self.amount} BTC)"


# --- Block and compact block structures ---

class BlockHeader:
    """Simplified block header (80 bytes in Bitcoin)."""
    def __init__(self, prev_hash, merkle_root, timestamp, nonce=0):
        self.version = 2
        self.prev_hash = prev_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.bits = 0x1d00ffff  # Difficulty target (placeholder)
        self.nonce = nonce
        self.size = 80  # Fixed header size in bytes

    def hash(self):
        """Double-SHA256 of header data."""
        data = (self.version.to_bytes(4, "little") +
                self.prev_hash +
                self.merkle_root +
                self.timestamp.to_bytes(4, "little") +
                self.bits.to_bytes(4, "little") +
                self.nonce.to_bytes(4, "little"))
        return hashlib.sha256(hashlib.sha256(data).digest()).digest()


class FullBlock:
    """A full block with header and all transactions."""
    def __init__(self, header, transactions):
        self.header = header
        self.transactions = transactions  # First tx is always coinbase

    def total_size(self):
        """Total block size in bytes."""
        return self.header.size + sum(tx.size for tx in self.transactions)


class CompactBlock:
    """
    BIP 152 compact block: header + nonce + short IDs + prefilled txs.
    Instead of sending all transaction data, we send:
    1. The block header (80 bytes)
    2. A random nonce for SipHash keying (8 bytes)
    3. Short transaction IDs (6 bytes each, vs 250+ bytes per full tx)
    4. Prefilled transactions (always includes coinbase, which isn't in mempool)
    """
    def __init__(self, full_block):
        self.header = full_block.header
        self.nonce = os.urandom(8)  # Random nonce for SipHash key derivation

        # Derive SipHash key from block header hash and nonce
        self.siphash_key = self._derive_key()

        # Prefill coinbase (index 0) — it won't be in anyone's mempool
        self.prefilled = [(0, full_block.transactions[0])]

        # Compute short IDs for all other transactions
        self.short_ids = []
        for tx in full_block.transactions[1:]:  # Skip coinbase
            short_id = self._compute_short_id(tx.txid)
            self.short_ids.append(short_id)

    def _derive_key(self):
        """Derive SipHash key from header hash and nonce."""
        header_hash = self.header.hash()
        # Key = first 16 bytes of SHA256(header_hash || nonce)
        key_material = hashlib.sha256(header_hash + self.nonce).digest()
        return key_material[:16]

    def _compute_short_id(self, txid):
        """Compute 6-byte short ID for a transaction."""
        # SipHash the txid, take lowest 6 bytes
        h = siphash_2_4(self.siphash_key, txid)
        return h & ((1 << 48) - 1)  # Mask to 48 bits = 6 bytes

    def total_size(self):
        """Size of compact block message."""
        header_size = 80
        nonce_size = 8
        # Each short ID is 6 bytes + 2 bytes varint overhead ~ 8 bytes
        short_ids_size = len(self.short_ids) * SHORT_ID_LENGTH
        prefilled_size = sum(tx.size for _, tx in self.prefilled)
        return header_size + nonce_size + short_ids_size + prefilled_size


# --- Node with mempool ---

class Node:
    """A Bitcoin node with a mempool that can reconstruct compact blocks."""
    def __init__(self, name):
        self.name = name
        self.mempool = {}  # txid -> Transaction

    def add_to_mempool(self, tx):
        """Add a transaction to this node's mempool."""
        self.mempool[tx.txid] = tx

    def reconstruct_block(self, compact_block):
        """
        Attempt to reconstruct a full block from a compact block.
        1. Start with prefilled transactions (coinbase)
        2. For each short ID, search mempool for matching transaction
        3. Return (reconstructed_txs, missing_indices)
        """
        # Build short ID -> mempool tx mapping
        # Compute short IDs for all mempool transactions using the same key
        mempool_index = {}
        for txid, tx in self.mempool.items():
            short_id = siphash_2_4(compact_block.siphash_key, txid) & ((1 << 48) - 1)
            mempool_index[short_id] = tx

        # Reconstruct transaction list
        reconstructed = [None] * (len(compact_block.short_ids) + len(compact_block.prefilled))

        # Place prefilled transactions
        for idx, tx in compact_block.prefilled:
            reconstructed[idx] = tx

        # Match short IDs to mempool
        missing = []
        for i, short_id in enumerate(compact_block.short_ids):
            tx_idx = i + 1  # Offset by 1 because index 0 is coinbase
            if short_id in mempool_index:
                reconstructed[tx_idx] = mempool_index[short_id]
            else:
                missing.append(tx_idx)

        return reconstructed, missing


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Demonstrate compact block relay with bandwidth savings."""

    print("=" * 70)
    print("        COMPACT BLOCK RELAY (BIP 152)")
    print("=" * 70)

    # --- Step 1: Create transactions ---
    print("\n--- Step 1: Simulating Network Activity ---\n")

    senders = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace"]
    receivers = ["Zara", "Yuki", "Xavier", "Wendy", "Victor", "Uma", "Tom"]

    # Create a large pool of transactions
    all_transactions = []
    for i in range(MEMPOOL_SIZE):
        s = senders[i % len(senders)]
        r = receivers[i % len(receivers)]
        amount = round(0.001 * (i + 1), 8)
        tx = Transaction(s, r, amount)
        all_transactions.append(tx)

    # Coinbase transaction (reward to miner)
    coinbase = Transaction("coinbase", "Miner_Pool", 6.25)

    # Select transactions for the block
    block_txs = [coinbase] + all_transactions[:NUM_TRANSACTIONS]

    print(f"  Total mempool transactions:     {MEMPOOL_SIZE}")
    print(f"  Transactions selected for block: {NUM_TRANSACTIONS}")
    print(f"  (+ 1 coinbase = {len(block_txs)} total)")

    # --- Step 2: Mine a full block ---
    print("\n--- Step 2: Mining a Full Block ---\n")

    merkle = hashlib.sha256(b"".join(tx.txid for tx in block_txs)).digest()
    header = BlockHeader(
        prev_hash=bytes(32),  # Genesis
        merkle_root=merkle,
        timestamp=int(time.time()),
    )
    full_block = FullBlock(header, block_txs)

    print(f"  Block hash:      {header.hash().hex()[:32]}...")
    print(f"  Transactions:    {len(block_txs)}")
    print(f"  Full block size: {full_block.total_size():,} bytes")

    # --- Step 3: Create compact block ---
    print("\n--- Step 3: Creating Compact Block ---\n")

    compact = CompactBlock(full_block)

    print(f"  Compact block contents:")
    print(f"  ┌─────────────────────────────────────────┐")
    print(f"  │ Header                    80 bytes       │")
    print(f"  │ SipHash nonce              8 bytes       │")
    print(f"  │ Prefilled txs              1 (coinbase)  │")
    print(f"  │ Short IDs          {len(compact.short_ids):>8} x 6 bytes  │")
    print(f"  └─────────────────────────────────────────┘")
    print(f"  Compact block size:  {compact.total_size():,} bytes")
    print(f"  Full block size:     {full_block.total_size():,} bytes")
    savings = (1 - compact.total_size() / full_block.total_size()) * 100
    print(f"  Bandwidth savings:   {savings:.1f}%")

    # --- Step 4: Show short ID computation ---
    print("\n--- Step 4: Short ID Computation ---\n")

    print(f"  SipHash key: {compact.siphash_key.hex()}")
    print(f"\n  Transaction ID (32 bytes)            Short ID (6 bytes)")
    print(f"  {'─' * 34}    {'─' * 14}")
    for i in range(min(5, len(block_txs) - 1)):
        tx = block_txs[i + 1]
        short_id = compact.short_ids[i]
        txid_hex = tx.txid.hex()[:34]
        sid_hex = f"{short_id:012x}"
        print(f"  {txid_hex}  =>  {sid_hex}")
    if len(block_txs) > 6:
        print(f"  ... ({len(block_txs) - 6} more transactions)")

    # --- Step 5: Receiving node reconstructs block ---
    print("\n--- Step 5: Receiving Node Reconstructs Block ---\n")

    node = Node("Node_B")

    # Populate mempool — most block txs are known, but not all
    num_known = int(NUM_TRANSACTIONS * MEMPOOL_HIT_RATE)
    num_missing = NUM_TRANSACTIONS - num_known

    # Add known transactions to mempool
    for tx in all_transactions[:num_known]:
        node.add_to_mempool(tx)
    # Add extra mempool txs that aren't in the block
    for tx in all_transactions[NUM_TRANSACTIONS:]:
        node.add_to_mempool(tx)

    print(f"  {node.name} mempool: {len(node.mempool)} transactions")
    print(f"  Block txs in mempool: {num_known}/{NUM_TRANSACTIONS} ({MEMPOOL_HIT_RATE*100:.0f}%)")

    # Reconstruct
    reconstructed, missing = node.reconstruct_block(compact)
    found = NUM_TRANSACTIONS - len(missing)

    print(f"\n  Reconstruction result:")
    print(f"  ┌────────────────────────────────────────┐")
    print(f"  │ Prefilled (coinbase):  1               │")
    print(f"  │ Matched from mempool:  {found:<16}  │")
    print(f"  │ Missing (need fetch):  {len(missing):<16}  │")
    print(f"  └────────────────────────────────────────┘")

    # --- Step 6: Request missing transactions ---
    if missing:
        print(f"\n--- Step 6: Fetching Missing Transactions ---\n")
        missing_size = len(missing) * 250  # Average tx size
        print(f"  Requesting {len(missing)} missing transactions ({missing_size:,} bytes)")
        print(f"  (In practice, this is a getblocktxn / blocktxn round-trip)")

        total_transferred = compact.total_size() + missing_size
        print(f"\n  Total data transferred:")
        print(f"    Compact block:      {compact.total_size():>8,} bytes")
        print(f"    Missing txs:        {missing_size:>8,} bytes")
        print(f"    ─────────────────────────────────")
        print(f"    Total:              {total_transferred:>8,} bytes")
        print(f"    Full block would be:{full_block.total_size():>8,} bytes")
        final_savings = (1 - total_transferred / full_block.total_size()) * 100
        print(f"    Actual savings:     {final_savings:>7.1f}%")

    # --- Step 7: Summary comparison ---
    print(f"\n--- Summary: Relay Methods Compared ---\n")

    full_bw = full_block.total_size()
    compact_bw = compact.total_size()
    headers_only = 80

    print("  ┌──────────────────────┬──────────────┬──────────┐")
    print("  │ Relay Method         │ Data Sent    │ Savings  │")
    print("  ├──────────────────────┼──────────────┼──────────┤")
    print(f"  │ Full block           │ {full_bw:>8,} B   │    0.0%  │")
    print(f"  │ Compact block        │ {compact_bw:>8,} B   │  {savings:>5.1f}%  │")
    print(f"  │ Headers-only (SPV)   │ {headers_only:>8,} B   │  {(1-headers_only/full_bw)*100:>5.1f}%  │")
    print("  └──────────────────────┴──────────────┴──────────┘")
    print()
    print("  Compact blocks achieve near-header-only efficiency while")
    print("  still allowing full block validation — the best of both worlds.")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
