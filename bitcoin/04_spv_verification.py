"""
TITLE: Simplified Payment Verification (SPV)
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    A lightweight SPV client that verifies a transaction's inclusion in a block
    using only 80-byte block headers and a Merkle proof — no full blocks needed.
    This is how mobile Bitcoin wallets verify payments without downloading the
    entire blockchain (500+ GB).

KEY CONCEPTS:
    - Block headers (80 bytes: version, prev_hash, merkle_root, timestamp, bits, nonce)
    - Merkle inclusion proofs (logarithmic-size path from leaf to root)
    - SPV verification (headers + proof = trustless lightweight validation)
    - Data savings (megabytes of transactions reduced to a few hundred bytes)

PREREQUISITE SCRIPTS:
    - core/01_hashing.py
    - core/04_merkle_trees.py
    - core/05_blockchain.py

REAL-WORLD RELEVANCE:
    Satoshi described SPV in Section 8 of the Bitcoin whitepaper. Mobile wallets
    like Electrum and Breadwallet use SPV to verify payments with ~50 MB of
    headers instead of the full ~500 GB blockchain. SPV nodes trust that the
    longest proof-of-work chain is honest (they can't validate transactions
    themselves, only that transactions are buried under enough work).
"""

import hashlib   # SHA-256 for hashing — stdlib, zero external deps
import struct    # For packing block header fields into raw bytes
import time      # Timestamps for block headers
import math      # For log2 in data savings calculation

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# How many hex characters to show when displaying truncated hashes
HASH_DISPLAY_LEN = 16

# Width of box-drawing content area
BOX_WIDTH = 58

# Bitcoin block header is always exactly 80 bytes:
#   4 (version) + 32 (prev_hash) + 32 (merkle_root) + 4 (timestamp) + 4 (bits) + 4 (nonce)
HEADER_SIZE_BYTES = 80

# Average Bitcoin transaction size in bytes (used for data savings comparison)
AVG_TX_SIZE_BYTES = 250

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Hashing utilities -------------------------------------------------------

def sha256(data: bytes) -> bytes:
    """Compute a single SHA-256 hash of raw bytes."""
    return hashlib.sha256(data).digest()


def double_sha256(data: bytes) -> bytes:
    """Bitcoin uses double-SHA-256 (hash the hash) for block headers and txids.

    This guards against length-extension attacks that affect single-round SHA-256.
    """
    return sha256(sha256(data))


def hash_pair(left: bytes, right: bytes) -> bytes:
    """Hash two Merkle tree children together to produce their parent.

    Bitcoin concatenates left + right and double-SHA-256's the result.
    """
    return double_sha256(left + right)


def _short(h: bytes) -> str:
    """Truncate a hash to a readable hex snippet."""
    return h.hex()[:HASH_DISPLAY_LEN]


# --- Transaction -------------------------------------------------------

class Transaction:
    """A simplified Bitcoin transaction (just enough for SPV demonstration).

    Real Bitcoin transactions have inputs, outputs, scripts, and witnesses.
    Here we use a sender/receiver/amount model to keep focus on SPV mechanics.
    """

    def __init__(self, sender: str, receiver: str, amount: float):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        # Serialize to bytes and double-hash to get the txid (transaction ID)
        self.data = f"{sender}->{receiver}:{amount}".encode()
        self.txid = double_sha256(self.data)  # Unique identifier for this tx

    def __repr__(self) -> str:
        return f"{self.sender} -> {self.receiver}: {self.amount} BTC"

    def size_bytes(self) -> int:
        """Estimated size of this transaction in bytes (simplified)."""
        return AVG_TX_SIZE_BYTES  # Use average size for realistic comparison


# --- Merkle Tree (self-contained, mirrors core/04 but uses double-SHA-256) ---

class MerkleTree:
    """Binary Merkle tree using Bitcoin's double-SHA-256 convention.

    Duplicates the last leaf if the count is odd (Bitcoin convention).
    """

    def __init__(self, txids: list[bytes]):
        """Build the tree from a list of transaction IDs (already hashed)."""
        if not txids:
            raise ValueError("Cannot build Merkle tree from zero transactions")
        self.levels = self._build(txids)

    @property
    def root(self) -> bytes:
        """The 32-byte Merkle root at the top of the tree."""
        return self.levels[-1][0]

    @staticmethod
    def _build(leaves: list[bytes]) -> list[list[bytes]]:
        """Build all levels bottom-up, duplicating the last node if odd."""
        levels = [list(leaves)]  # Level 0 = leaf txids
        current = list(leaves)

        while len(current) > 1:
            if len(current) % 2 == 1:
                current.append(current[-1])  # Duplicate last node for even pairing

            next_level = []
            for i in range(0, len(current), 2):
                parent = hash_pair(current[i], current[i + 1])
                next_level.append(parent)

            levels.append(next_level)
            current = next_level

        return levels

    def get_proof(self, leaf_index: int) -> list[tuple[bytes, str]]:
        """Generate an inclusion proof: list of (sibling_hash, direction) tuples.

        Direction is 'L' if sibling is on the left, 'R' if on the right.
        Walk from leaf up to root, collecting the sibling at each level.
        """
        if leaf_index < 0 or leaf_index >= len(self.levels[0]):
            raise IndexError(f"Leaf index {leaf_index} out of range")

        proof = []
        idx = leaf_index

        for level_num in range(len(self.levels) - 1):
            current_level = self.levels[level_num]

            # Mirror build logic: duplicate last if odd
            if len(current_level) % 2 == 1:
                current_level = current_level + [current_level[-1]]

            if idx % 2 == 0:
                sibling_idx = idx + 1
                direction = "R"  # Sibling is to our right
            else:
                sibling_idx = idx - 1
                direction = "L"  # Sibling is to our left

            proof.append((current_level[sibling_idx], direction))
            idx //= 2  # Parent index in the next level

        return proof

    @staticmethod
    def verify_proof(txid: bytes, proof: list[tuple[bytes, str]],
                     expected_root: bytes) -> bool:
        """Verify a Merkle inclusion proof against an expected root.

        Start with the txid, combine with each sibling in the proof,
        and check if we arrive at the expected Merkle root.
        """
        current = txid

        for sibling_hash, direction in proof:
            if direction == "L":
                current = hash_pair(sibling_hash, current)  # Sibling on the left
            else:
                current = hash_pair(current, sibling_hash)  # Sibling on the right

        return current == expected_root


# --- Block Header (80 bytes, the only thing SPV clients store) ---------------

class BlockHeader:
    """An 80-byte Bitcoin block header — the minimal unit SPV nodes store.

    In Bitcoin, full nodes store entire blocks (header + all transactions).
    SPV nodes store ONLY headers, which is enough to verify the proof-of-work
    chain and check Merkle proofs for specific transactions.
    """

    def __init__(self, version: int, prev_hash: bytes, merkle_root: bytes,
                 timestamp: int, bits: int, nonce: int):
        self.version = version           # Protocol version (e.g., 2)
        self.prev_hash = prev_hash       # 32-byte hash of the previous header
        self.merkle_root = merkle_root   # 32-byte Merkle root of all txs in this block
        self.timestamp = timestamp       # Unix timestamp (seconds since epoch)
        self.bits = bits                 # Compact target representation (difficulty)
        self.nonce = nonce               # Value miners iterate to find valid hash

    def serialize(self) -> bytes:
        """Pack header fields into exactly 80 bytes (Bitcoin's wire format).

        Format: little-endian version(4) + prev_hash(32) + merkle_root(32)
                + timestamp(4) + bits(4) + nonce(4) = 80 bytes total.
        """
        return (
            struct.pack("<I", self.version)      # 4 bytes, little-endian uint32
            + self.prev_hash                     # 32 bytes, raw hash
            + self.merkle_root                   # 32 bytes, raw hash
            + struct.pack("<I", self.timestamp)   # 4 bytes
            + struct.pack("<I", self.bits)        # 4 bytes
            + struct.pack("<I", self.nonce)       # 4 bytes
        )                                        # Total: 80 bytes

    def block_hash(self) -> bytes:
        """Compute this header's hash (double-SHA-256 of the 80-byte serialization).

        This hash is what miners try to get below the target, and what links
        headers into a chain.
        """
        return double_sha256(self.serialize())


# --- Full Block (what a full node stores) ------------------------------------

class FullBlock:
    """A complete block: header + all transactions.

    Full nodes store these. SPV clients only need the header.
    """

    def __init__(self, transactions: list[Transaction], prev_hash: bytes,
                 version: int = 2, bits: int = 0x1d00ffff, nonce: int = 0):
        self.transactions = transactions

        # Build Merkle tree from transaction IDs
        txids = [tx.txid for tx in transactions]
        self.merkle_tree = MerkleTree(txids)

        # Construct the 80-byte header with the Merkle root
        self.header = BlockHeader(
            version=version,
            prev_hash=prev_hash,
            merkle_root=self.merkle_tree.root,
            timestamp=int(time.time()),
            bits=bits,
            nonce=nonce,
        )

    def get_merkle_proof(self, tx_index: int) -> list[tuple[bytes, str]]:
        """Generate a Merkle proof for the transaction at tx_index."""
        return self.merkle_tree.get_proof(tx_index)

    def total_size_bytes(self) -> int:
        """Estimated total size: header + all transactions."""
        tx_sizes = sum(tx.size_bytes() for tx in self.transactions)
        return HEADER_SIZE_BYTES + tx_sizes


# --- Header Chain (what an SPV client maintains) -----------------------------

class HeaderChain:
    """A chain of block headers — the backbone of an SPV client's state.

    SPV clients download ALL headers (tiny: ~80 bytes each) but ZERO
    transaction data. They verify the proof-of-work chain is valid,
    then use Merkle proofs to check individual transactions.
    """

    def __init__(self):
        self.headers: list[BlockHeader] = []

    def add_header(self, header: BlockHeader) -> None:
        """Append a header to the chain after validating linkage."""
        if self.headers:
            expected_prev = self.headers[-1].block_hash()
            actual_prev = header.prev_hash
            if actual_prev != expected_prev:
                raise ValueError(
                    f"Header chain broken: prev_hash {_short(actual_prev)} "
                    f"doesn't match last header hash {_short(expected_prev)}"
                )
        self.headers.append(header)

    def total_size_bytes(self) -> int:
        """Total storage for all headers."""
        return len(self.headers) * HEADER_SIZE_BYTES

    def validate_chain(self) -> bool:
        """Verify that every header links to the previous one."""
        for i in range(1, len(self.headers)):
            expected = self.headers[i - 1].block_hash()
            if self.headers[i].prev_hash != expected:
                return False
        return True


# --- SPV Client (lightweight verifier) ---------------------------------------

class SPVClient:
    """A Simplified Payment Verification client.

    The SPV client stores only block headers (~80 bytes each) and can verify
    any transaction's inclusion in a block by requesting a Merkle proof from
    a full node. It trusts that the longest PoW chain is honest.

    What it DOES:
        - Store block headers (tiny: 80 bytes per block)
        - Verify Merkle proofs against header merkle_roots
        - Confirm a transaction has N confirmations (depth in the chain)

    What it CANNOT do:
        - Validate transaction rules (double-spend, script validity)
        - Detect invalid transactions buried in valid-looking blocks
        - Protect against 51% attacks (it trusts the longest chain)
    """

    def __init__(self):
        self.header_chain = HeaderChain()

    def receive_header(self, header: BlockHeader) -> None:
        """Receive and store a block header from the network."""
        self.header_chain.add_header(header)

    def verify_transaction(self, txid: bytes,
                           proof: list[tuple[bytes, str]],
                           block_index: int) -> tuple[bool, str]:
        """Verify that a transaction is included in a specific block.

        Args:
            txid: The transaction ID (double-SHA-256 of tx data).
            proof: Merkle proof (list of sibling hashes + directions).
            block_index: Which block in our header chain to check against.

        Returns:
            (success, message) tuple.
        """
        # Step 1: Check that we have the header for this block
        if block_index < 0 or block_index >= len(self.header_chain.headers):
            return False, f"Block #{block_index} not in our header chain"

        header = self.header_chain.headers[block_index]

        # Step 2: Verify the Merkle proof against the header's merkle_root
        # This is the core of SPV — we trust the header chain (backed by PoW)
        # and verify the tx is in the block's Merkle tree
        valid = MerkleTree.verify_proof(txid, proof, header.merkle_root)

        if valid:
            # Step 3: Count confirmations (blocks built on top of this one)
            confirmations = len(self.header_chain.headers) - block_index
            return True, (
                f"Transaction verified in block #{block_index} "
                f"with {confirmations} confirmation(s)"
            )
        else:
            return False, "Merkle proof INVALID — transaction not in this block"

    def storage_size(self) -> int:
        """Total bytes stored by this SPV client."""
        return self.header_chain.total_size_bytes()


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def _print_header_box(header: BlockHeader, block_num: int, tx_count: int = 0):
    """Render a block header as a visual box."""
    label = f"Block #{block_num}" + (" (Genesis)" if block_num == 0 else "")
    top    = f"  ┌{'─' * BOX_WIDTH}┐"
    bottom = f"  └{'─' * BOX_WIDTH}┘"

    lines = [
        f"version:     {header.version}",
        f"prev_hash:   {_short(header.prev_hash)}...",
        f"merkle_root: {_short(header.merkle_root)}...",
        f"timestamp:   {header.timestamp}",
        f"bits:        0x{header.bits:08x}",
        f"nonce:       {header.nonce}",
    ]
    if tx_count > 0:
        lines.append(f"tx_count:    {tx_count} transactions")

    print(f"  {label}")
    print(top)
    for line in lines:
        print(f"  │ {line:<{BOX_WIDTH - 2}} │")
    print(bottom)


def _print_proof_path(txid: bytes, proof: list[tuple[bytes, str]],
                      merkle_root: bytes):
    """Visualize the Merkle proof path from leaf to root."""
    print(f"    Leaf (txid):  {_short(txid)}...")
    current = txid
    for step, (sibling, direction) in enumerate(proof):
        side = "LEFT " if direction == "L" else "RIGHT"
        print(f"         │")
        print(f"         ├── Step {step}: combine with {side} sibling {_short(sibling)}...")
        if direction == "L":
            current = hash_pair(sibling, current)
        else:
            current = hash_pair(current, sibling)
        print(f"         │   result: {_short(current)}...")
    print(f"         │")
    print(f"         ▼")
    print(f"    Root:         {_short(merkle_root)}...")
    match = current == merkle_root
    print(f"    Match: {'✓ YES' if match else '✗ NO'}")


def demo():
    """Run a visual demonstration of SPV verification."""

    print("=" * 65)
    print("  SIMPLIFIED PAYMENT VERIFICATION (SPV)")
    print("  Verify transactions without downloading the full blockchain")
    print("=" * 65)

    # --- Part 1: Full node builds blocks with transactions -------------------

    print()
    print("─" * 65)
    print("  PART 1: Full Node Creates Blocks")
    print("─" * 65)
    print()
    print("  A full node stores complete blocks (header + ALL transactions).")
    print("  An SPV client stores ONLY the 80-byte headers.")
    print()

    # Create transactions for 3 blocks (genesis has no txs for simplicity)
    block_txs = [
        # Block 0 (genesis) — coinbase only
        [Transaction("coinbase", "Miner", 50.0)],
        # Block 1 — several transactions
        [
            Transaction("Alice", "Bob", 5.0),
            Transaction("Charlie", "Dave", 2.5),
            Transaction("Eve", "Frank", 1.0),
            Transaction("Grace", "Heidi", 3.0),
            Transaction("Ivan", "Judy", 0.5),
            Transaction("Karl", "Laura", 7.0),
            Transaction("Miner", "Alice", 6.25),
            Transaction("Bob", "Charlie", 1.5),
        ],
        # Block 2 — more transactions
        [
            Transaction("Dave", "Eve", 4.0),
            Transaction("Frank", "Grace", 0.75),
            Transaction("Heidi", "Ivan", 2.0),
            Transaction("Judy", "Karl", 1.25),
        ],
        # Block 3 — our target transaction is here
        [
            Transaction("Laura", "Miner", 3.0),
            Transaction("Alice", "Charlie", 1.5),
            Transaction("Bob", "Dave", 2.0),       # <-- We'll verify this one (index 2)
            Transaction("Eve", "Grace", 0.5),
            Transaction("Frank", "Heidi", 4.5),
            Transaction("Ivan", "Laura", 1.0),
        ],
    ]

    # Build the full blocks
    genesis_prev = b"\x00" * 32  # Genesis block has all-zero prev_hash
    full_blocks: list[FullBlock] = []

    for i, txs in enumerate(block_txs):
        prev = genesis_prev if i == 0 else full_blocks[i - 1].header.block_hash()
        block = FullBlock(transactions=txs, prev_hash=prev, nonce=i * 1000)
        full_blocks.append(block)

    # Display the full blocks
    for i, block in enumerate(full_blocks):
        _print_header_box(block.header, i, len(block.transactions))
        if i < len(full_blocks) - 1:
            print("           │")
            print("           ▼")

    # --- Part 2: SPV client receives only headers ----------------------------

    print()
    print("─" * 65)
    print("  PART 2: SPV Client Downloads Only Headers")
    print("─" * 65)
    print()

    spv = SPVClient()

    # Feed just the headers (no transactions!) to the SPV client
    for block in full_blocks:
        spv.receive_header(block.header)

    print(f"  SPV client received {len(spv.header_chain.headers)} block headers.")
    print(f"  Header chain valid: {'✓ YES' if spv.header_chain.validate_chain() else '✗ NO'}")
    print()
    print(f"  SPV client stores ONLY headers:")
    for i, hdr in enumerate(spv.header_chain.headers):
        label = "(Genesis)" if i == 0 else ""
        print(f"    Header #{i} {label:10s} "
              f"merkle_root={_short(hdr.merkle_root)}... "
              f"hash={_short(hdr.block_hash())}...")
    print()

    # --- Part 3: Verify a transaction using Merkle proof ---------------------

    print("─" * 65)
    print("  PART 3: SPV Verification — Prove a Transaction is in Block #3")
    print("─" * 65)
    print()

    # The transaction we want to verify (index 2 in block 3)
    target_block_idx = 3
    target_tx_idx = 2
    target_tx = block_txs[target_block_idx][target_tx_idx]

    print(f"  Transaction to verify: {target_tx}")
    print(f"  Transaction ID (txid): {_short(target_tx.txid)}...")
    print(f"  Located in Block #{target_block_idx}, position {target_tx_idx}")
    print()

    # Full node generates the Merkle proof
    proof = full_blocks[target_block_idx].get_merkle_proof(target_tx_idx)

    print(f"  Full node provides Merkle proof ({len(proof)} sibling hashes):")
    print()

    # Visualize the proof path
    _print_proof_path(
        target_tx.txid,
        proof,
        full_blocks[target_block_idx].header.merkle_root,
    )
    print()

    # SPV client verifies using ONLY the header's merkle_root + proof
    success, message = spv.verify_transaction(
        target_tx.txid, proof, target_block_idx
    )

    symbol = "✓" if success else "✗"
    print(f"  SPV Result: {symbol} {message}")

    # --- Part 4: Reject a tampered/fake transaction --------------------------

    print()
    print("─" * 65)
    print("  PART 4: SPV Rejects a Fake Transaction")
    print("─" * 65)
    print()

    fake_tx = Transaction("Bob", "Dave", 9999.0)  # Attacker claims huge payment
    print(f"  Fake transaction:  {fake_tx}")
    print(f"  Fake txid:         {_short(fake_tx.txid)}...")
    print(f"  Using the SAME Merkle proof from the real transaction...")
    print()

    # Try to verify the fake tx with the real proof — should fail
    fake_success, fake_message = spv.verify_transaction(
        fake_tx.txid, proof, target_block_idx
    )

    symbol = "✓" if fake_success else "✗"
    print(f"  SPV Result: {symbol} {fake_message}")
    print()
    print("  The Merkle proof only works for the EXACT transaction it was")
    print("  generated for. Changing even one byte produces a different txid,")
    print("  which won't hash up to the merkle_root stored in the header.")

    # --- Part 5: Data savings comparison -------------------------------------

    print()
    print("─" * 65)
    print("  PART 5: Data Savings — SPV vs Full Node")
    print("─" * 65)
    print()

    # Calculate sizes for our demo chain
    full_node_size = sum(b.total_size_bytes() for b in full_blocks)
    spv_size = spv.storage_size()
    proof_size = len(proof) * 32  # Each sibling hash is 32 bytes

    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │              Our Demo Chain (4 blocks)                  │")
    print("  ├──────────────────────────┬──────────────────────────────┤")
    print(f"  │ Full node stores         │ {full_node_size:>10,} bytes              │")
    print(f"  │ SPV client stores        │ {spv_size:>10,} bytes (headers)    │")
    print(f"  │ Merkle proof size        │ {proof_size:>10,} bytes              │")
    print(f"  │ SPV total to verify 1 tx │ {spv_size + proof_size:>10,} bytes              │")
    savings_pct = (1 - (spv_size + proof_size) / full_node_size) * 100
    print(f"  │ Data savings             │ {savings_pct:>9.1f}%                  │")
    print("  └──────────────────────────┴──────────────────────────────┘")

    # Real-world scaling
    print()
    print("  Real-world Bitcoin scaling (as of ~2024):")
    print()
    print(f"    {'Metric':<30s} {'Full Node':>15s}  {'SPV Client':>15s}")
    print(f"    {'─' * 30} {'─' * 15}  {'─' * 15}")

    btc_blocks = 850_000                                         # Approximate block height
    btc_full_size_gb = 550                                       # Full blockchain ~550 GB
    btc_header_size = btc_blocks * HEADER_SIZE_BYTES             # All headers
    btc_header_size_mb = btc_header_size / (1024 * 1024)         # Convert to MB
    avg_txs_per_block = 2500                                     # Average txs per block
    proof_hashes = math.ceil(math.log2(avg_txs_per_block))       # ~12 sibling hashes
    single_proof_bytes = proof_hashes * 32                       # ~384 bytes per proof

    print(f"    {'Blockchain storage':<30s} {btc_full_size_gb:>12} GB  "
          f"{btc_header_size_mb:>12.0f} MB")
    print(f"    {'To verify 1 transaction':<30s} {'(already has)':>15s}  "
          f"{single_proof_bytes:>12} B")
    print(f"    {'Block headers':<30s} {btc_blocks:>12,}x  "
          f"{btc_blocks:>12,}x")
    print(f"    {'Transaction data':<30s} {'ALL txs':>15s}  "
          f"{'0 txs':>15s}")

    savings_real = (1 - (btc_header_size_mb / 1024) / btc_full_size_gb) * 100
    print()
    print(f"    Storage savings: {savings_real:.2f}%")
    print(f"    SPV needs only ~{btc_header_size_mb:.0f} MB of headers vs "
          f"~{btc_full_size_gb} GB full chain")
    print(f"    That's a {btc_full_size_gb * 1024 / btc_header_size_mb:.0f}x reduction!")

    # --- Part 6: Confirmation depth ------------------------------------------

    print()
    print("─" * 65)
    print("  PART 6: Confirmation Depth Matters")
    print("─" * 65)
    print()
    print("  SPV clients also check how many blocks are built ON TOP of the")
    print("  block containing the transaction. More confirmations = safer.")
    print()

    confirmations = len(spv.header_chain.headers) - target_block_idx
    print(f"  Transaction is in block #{target_block_idx}")
    print(f"  Chain height: {len(spv.header_chain.headers)} blocks")
    print(f"  Confirmations: {confirmations}")
    print()

    # Show confirmation safety levels
    safety_levels = [
        (1, "Seen (not safe — could be reversed)"),
        (3, "Lightly confirmed (small purchases)"),
        (6, "Standard (most exchanges accept this)"),
        (60, "Deep (virtually irreversible)"),
    ]

    print("  Confirmation safety levels:")
    for threshold, description in safety_levels:
        marker = "◄── current" if threshold == confirmations else ""
        indicator = "●" if confirmations >= threshold else "○"
        print(f"    {indicator} {threshold:>3} conf — {description} {marker}")

    print()
    print("=" * 65)
    print("  KEY TAKEAWAYS")
    print("=" * 65)
    print()
    print("  1. SPV clients store only 80-byte headers (not full blocks)")
    print("  2. Merkle proofs verify tx inclusion with O(log n) hashes")
    print("  3. SPV trusts the longest PoW chain (can't validate tx rules)")
    print("  4. More confirmations = harder to reverse = safer")
    print("  5. Enables mobile wallets on bandwidth/storage-constrained devices")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
