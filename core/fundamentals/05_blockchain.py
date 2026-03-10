"""
TITLE: Blockchain
CATEGORY: core

WHAT THIS IMPLEMENTS:
    A basic blockchain data structure from scratch. Each block contains an index,
    timestamp, arbitrary data, the previous block's hash, a nonce, and its own
    SHA-256 hash. Blocks are chained by embedding each predecessor's hash, so
    tampering with any block invalidates every block that follows it.

KEY CONCEPTS:
    - Block structure (index, timestamp, data, prev_hash, nonce, hash)
    - Chain linking via cryptographic hashes
    - Tamper detection through chain validation

PREREQUISITE SCRIPTS:
    - core/01_hashing.py

REAL-WORLD RELEVANCE:
    Every blockchain (Bitcoin, Ethereum, etc.) relies on this exact linking
    mechanism to create an append-only ledger. If any historical block is
    altered, the hash chain breaks and all honest nodes reject the forgery.
"""

import hashlib
import json
import time

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# How many hex characters of the hash to display in the visual output
HASH_DISPLAY_LEN = 16

# Width of the box-drawing display (inner content area)
BOX_WIDTH = 45

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

class Block:
    """A single block in the blockchain."""

    def __init__(self, index: int, data: str, previous_hash: str, nonce: int = 0):
        self.index = index                          # Position in the chain (0 = genesis)
        self.timestamp = time.time()                # Unix timestamp when block was created
        self.data = data                            # Arbitrary payload (e.g. transaction info)
        self.previous_hash = previous_hash          # Hash of the preceding block — the "link"
        self.nonce = nonce                          # Arbitrary number (used in mining / PoW)
        self.hash = self.compute_hash()             # This block's own hash, computed from all fields

    def compute_hash(self) -> str:
        """
        Compute SHA-256 hash of the block's contents.

        We serialize all fields into a deterministic JSON string, then hash it.
        Any change to any field produces a completely different hash (avalanche effect).
        """
        # Build a dict of every field that should be covered by the hash
        block_content = {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        # sort_keys ensures deterministic serialization across runs
        block_string = json.dumps(block_content, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()


# ----------------------------------------------------------------------------
# Blockchain — an ordered list of Blocks
# ----------------------------------------------------------------------------

class Blockchain:
    """A chain of blocks linked by cryptographic hashes."""

    def __init__(self):
        self.chain: list[Block] = []                # Ordered list of blocks
        self._create_genesis_block()                # Every chain starts with a genesis block

    def _create_genesis_block(self) -> None:
        """
        Create the very first block in the chain.

        The genesis block has no predecessor, so its previous_hash is all zeros.
        This is a convention — Bitcoin's genesis block uses the same idea.
        """
        genesis = Block(
            index=0,
            data="Genesis Block",
            previous_hash="0" * 64,                 # 64 hex zeros (256 bits of nothing)
            nonce=0,
        )
        self.chain.append(genesis)

    def add_block(self, data: str, nonce: int = 0) -> Block:
        """
        Append a new block to the chain.

        The new block's previous_hash is set to the hash of the current last block,
        which is what creates the tamper-evident chain.
        """
        previous_block = self.chain[-1]             # The block we're extending from
        new_block = Block(
            index=len(self.chain),
            data=data,
            previous_hash=previous_block.hash,      # Link to predecessor
            nonce=nonce,
        )
        self.chain.append(new_block)
        return new_block

    def validate_chain(self) -> tuple[bool, str]:
        """
        Walk the entire chain and verify two invariants for every block:
          1. The block's stored hash matches a fresh recomputation of its contents.
          2. The block's previous_hash matches the hash of the preceding block.

        Returns (True, "ok") if valid, or (False, reason) on first failure.
        """
        for i in range(len(self.chain)):
            block = self.chain[i]

            # --- Invariant 1: hash integrity ---
            # Recompute the hash from the block's current fields
            recomputed = block.compute_hash()
            if block.hash != recomputed:
                return (
                    False,
                    f"Block #{block.index} hash mismatch "
                    f"(stored {block.hash[:HASH_DISPLAY_LEN]}... "
                    f"vs computed {recomputed[:HASH_DISPLAY_LEN]}...)",
                )

            # --- Invariant 2: chain linkage ---
            # Skip genesis block — it has no predecessor to check against
            if i > 0:
                previous_block = self.chain[i - 1]
                if block.previous_hash != previous_block.hash:
                    return (
                        False,
                        f"Block #{block.index} previous_hash mismatch "
                        f"(expected {previous_block.hash[:HASH_DISPLAY_LEN]}... "
                        f"from Block #{previous_block.index}, "
                        f"got {block.previous_hash[:HASH_DISPLAY_LEN]}...)",
                    )

        return (True, "All blocks valid — chain integrity confirmed")


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def _format_block(block: Block, label: str | None = None) -> str:
    """Render a single block as an ASCII box with box-drawing characters."""
    if label is None:
        label = f"Block #{block.index}" if block.index > 0 else "Block #0 (Genesis)"

    prev_display = block.previous_hash[:HASH_DISPLAY_LEN]  # Truncate for readability
    hash_display = block.hash[:HASH_DISPLAY_LEN]
    data_display = block.data[:28]                          # Keep data short enough to fit

    # Build the lines that go inside the box
    lines = [
        f"prev_hash: {prev_display}...",
        f"data:      {data_display}",
        f"nonce:     {block.nonce}",
        f"hash:      {hash_display}...",
    ]

    # Construct box with consistent width
    top    = f"┌{'─' * BOX_WIDTH}┐"
    bottom = f"└{'─' * BOX_WIDTH}┘"

    result = f"{label}\n{top}\n"
    for line in lines:
        # Pad each line to fill the box width
        result += f"│ {line:<{BOX_WIDTH - 2}} │\n"
    result += bottom

    return result


def _print_chain(chain: Blockchain) -> None:
    """Print the full chain with arrows between blocks."""
    for i, block in enumerate(chain.chain):
        print(_format_block(block))
        if i < len(chain.chain) - 1:                # Print arrow between blocks
            print("         │")
            print("         ▼")


def demo():
    """Run a visual demonstration of the concept."""
    # --- Part 1: Build a 5-block chain ---
    print("=" * 55)
    print("  BUILDING A BLOCKCHAIN (5 BLOCKS)")
    print("=" * 55)
    print()

    bc = Blockchain()                               # Creates genesis block automatically

    # Sample transaction data for blocks 1-4
    transactions = [
        "Alice pays Bob 5 coins",
        "Bob pays Charlie 2 coins",
        "Charlie pays Diana 1 coin",
        "Diana pays Alice 3 coins",
    ]

    for tx in transactions:
        bc.add_block(data=tx)                       # Each block links to the previous one

    _print_chain(bc)

    # --- Part 2: Validate the intact chain ---
    print()
    print("-" * 55)
    print("  VALIDATING INTACT CHAIN")
    print("-" * 55)
    print()

    valid, message = bc.validate_chain()
    symbol = "✓" if valid else "✗"
    print(f"  {symbol} {message}")

    # --- Part 3: Tamper with a block and show detection ---
    print()
    print("-" * 55)
    print("  TAMPERING WITH BLOCK #2")
    print("-" * 55)
    print()

    original_data = bc.chain[2].data
    tampered_data = "Bob pays Eve 999 coins"        # Attacker changes the transaction

    print(f'  Original data: "{original_data}"')
    print(f'  Tampered data: "{tampered_data}"')
    print()

    # Modify the block's data — but do NOT recompute its hash
    # This simulates a naive attacker who changes data but forgets
    # (or can't feasibly) update the hash chain
    bc.chain[2].data = tampered_data

    valid, message = bc.validate_chain()
    symbol = "✓" if valid else "✗"
    print(f"  {symbol} {message}")

    # --- Part 4: Show that even recomputing the tampered block's hash isn't enough ---
    print()
    print("-" * 55)
    print("  RECALCULATING TAMPERED BLOCK'S HASH")
    print("-" * 55)
    print()
    print("  Even if the attacker recomputes Block #2's hash,")
    print("  Block #3's previous_hash still points to the OLD hash.")
    print()

    # Recompute the tampered block's hash so invariant 1 passes for block #2
    bc.chain[2].hash = bc.chain[2].compute_hash()

    valid, message = bc.validate_chain()
    symbol = "✓" if valid else "✗"
    print(f"  {symbol} {message}")
    print()

    # --- Part 5: Show what the chain looks like after tampering ---
    print("-" * 55)
    print("  CHAIN AFTER TAMPERING (notice hash mismatch at #3)")
    print("-" * 55)
    print()
    _print_chain(bc)

    print()
    print("=" * 55)
    print("  KEY TAKEAWAY")
    print("=" * 55)
    print()
    print("  Changing ANY block invalidates every block after it.")
    print("  An attacker would need to recompute the hashes of ALL")
    print("  subsequent blocks — and in a real blockchain with PoW,")
    print("  that means re-mining every block, which is infeasible")
    print("  if honest miners control the majority of hash power.")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
