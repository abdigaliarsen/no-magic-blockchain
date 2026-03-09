"""
TITLE: Merkle Trees
CATEGORY: core

WHAT THIS IMPLEMENTS:
    A binary Merkle tree built from transaction hashes. Supports constructing
    the full tree, generating logarithmic-size inclusion proofs, and verifying
    that a given leaf belongs to a tree without needing the entire dataset.

KEY CONCEPTS:
    - Binary hash trees (pairwise hashing from leaves to a single root)
    - Inclusion proofs (sibling hashes + left/right direction flags)
    - Logarithmic verification (prove membership with O(log n) hashes)

PREREQUISITE SCRIPTS:
    - core/01_hashing.py

REAL-WORLD RELEVANCE:
    Merkle trees are used in every major blockchain: Bitcoin stores transaction
    hashes in a Merkle tree per block (enabling SPV), Ethereum uses a variant
    (Merkle Patricia Trie) for state/receipts, and Solana uses them for PoH.
"""

import hashlib  # SHA-256 for hashing — stdlib, zero external deps
import math     # For log2 calculation in proof size analysis

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Number of hex characters to show when displaying truncated hashes.
# Full SHA-256 is 64 hex chars; 8 is enough to visually distinguish nodes.
HASH_DISPLAY_LEN = 8

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

def sha256(data: bytes) -> bytes:
    """Compute SHA-256 hash of raw bytes."""
    return hashlib.sha256(data).digest()


def hash_pair(left: bytes, right: bytes) -> bytes:
    """Hash two child nodes together to produce their parent.

    Concatenate left + right, then SHA-256 the result.
    This is exactly how Bitcoin builds its Merkle trees.
    """
    return sha256(left + right)


# --- MerkleTree class -------------------------------------------------------

class MerkleTree:
    """A binary Merkle tree built bottom-up from a list of data items.

    Internal representation: `self.levels` is a list of lists.
    levels[0] = leaf hashes, levels[-1] = [root_hash].
    """

    def __init__(self, data_items: list[bytes]):
        """Build the full tree from a list of raw data items.

        Args:
            data_items: List of byte strings (e.g., transaction data).
                        Must contain at least one item.
        """
        if not data_items:
            raise ValueError("Cannot build a Merkle tree with zero items")

        # Hash each data item to get the leaf layer
        leaves = [sha256(item) for item in data_items]

        # Store original data for display purposes
        self.data_items = data_items

        # Build all levels from leaves up to root
        self.levels = self._build_levels(leaves)

    @property
    def root(self) -> bytes:
        """The single hash at the top of the tree — the Merkle root."""
        return self.levels[-1][0]

    @property
    def leaf_count(self) -> int:
        """Number of leaves (original data items) in the tree."""
        return len(self.levels[0])

    @property
    def height(self) -> int:
        """Number of levels in the tree (leaves = level 0, root = top)."""
        return len(self.levels)

    # ---- Tree construction --------------------------------------------------

    @staticmethod
    def _build_levels(leaves: list[bytes]) -> list[list[bytes]]:
        """Build the tree bottom-up, returning all levels.

        If a level has an odd number of nodes, the last node is duplicated
        before pairing. This is the standard Bitcoin Merkle tree behavior.
        """
        levels = [leaves]          # Level 0 = leaf hashes
        current = leaves

        while len(current) > 1:    # Keep hashing pairs until one node remains
            # If odd number of nodes, duplicate the last one so we can pair evenly.
            # Bitcoin does this too — it's simpler than leaving an orphan.
            if len(current) % 2 == 1:
                current = current + [current[-1]]  # Duplicate last node

            # Pair up adjacent nodes and hash each pair
            next_level = []
            for i in range(0, len(current), 2):
                parent = hash_pair(current[i], current[i + 1])
                next_level.append(parent)

            levels.append(next_level)
            current = next_level

        return levels

    # ---- Inclusion proof generation -----------------------------------------

    def get_proof(self, leaf_index: int) -> list[tuple[bytes, str]]:
        """Generate an inclusion proof for the leaf at `leaf_index`.

        Returns a list of (sibling_hash, direction) tuples, where direction
        is 'L' if the sibling is on the left, 'R' if on the right.

        To verify: start with the leaf hash, and at each step combine it
        with the sibling in the indicated direction, hashing upward until
        you reach the root.
        """
        if leaf_index < 0 or leaf_index >= len(self.levels[0]):
            raise IndexError(f"Leaf index {leaf_index} out of range")

        proof = []
        idx = leaf_index

        # Walk from the leaf level up to (but not including) the root level
        for level in range(len(self.levels) - 1):
            current_level = self.levels[level]

            # Handle odd-length levels: duplicate last node (mirrors build logic)
            if len(current_level) % 2 == 1:
                current_level = current_level + [current_level[-1]]

            # Determine sibling index: if idx is even, sibling is idx+1 (right);
            # if idx is odd, sibling is idx-1 (left)
            if idx % 2 == 0:
                sibling_idx = idx + 1
                direction = "R"    # Sibling sits to our right
            else:
                sibling_idx = idx - 1
                direction = "L"    # Sibling sits to our left

            proof.append((current_level[sibling_idx], direction))

            # Move up: our parent is at index idx // 2 in the next level
            idx = idx // 2

        return proof

    # ---- Static proof verification ------------------------------------------

    @staticmethod
    def verify_proof(leaf_data: bytes, proof: list[tuple[bytes, str]],
                     expected_root: bytes) -> bool:
        """Verify a Merkle inclusion proof without needing the full tree.

        Args:
            leaf_data: The original data item (will be hashed to get leaf hash).
            proof: List of (sibling_hash, direction) from get_proof().
            expected_root: The known Merkle root to verify against.

        Returns:
            True if the proof is valid (leaf is in the tree), False otherwise.
        """
        current = sha256(leaf_data)  # Start with the leaf hash

        for sibling_hash, direction in proof:
            if direction == "L":
                # Sibling is on the left → sibling comes first
                current = hash_pair(sibling_hash, current)
            else:
                # Sibling is on the right → we come first
                current = hash_pair(current, sibling_hash)

        return current == expected_root  # Does our computed root match?


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def _short(h: bytes) -> str:
    """Return a truncated hex representation of a hash for display."""
    return h.hex()[:HASH_DISPLAY_LEN]


def _print_tree(tree: MerkleTree):
    """Print the Merkle tree with box-drawing characters."""
    print()
    print("=== Merkle Tree Structure ===")
    print()

    # Print from root (top) down to leaves (bottom)
    for level_idx in range(tree.height - 1, -1, -1):
        level = tree.levels[level_idx]

        if level_idx == tree.height - 1:
            label = "Root"
        elif level_idx == 0:
            label = "Leaves"
        else:
            label = f"Level {level_idx}"

        # Build node boxes for this level
        nodes_str = "   ".join(f"[{_short(h)}]" for h in level)
        print(f"  {label:>8}:  {nodes_str}")

        # Draw connecting lines (except below the leaf level)
        if level_idx > 0:
            # Draw downward connectors from each parent to its two children
            connectors = []
            for i in range(len(level)):
                connectors.append("    ┌──┴──┐  ")
            print(f"{'':>11}{''.join(connectors)}")


def _print_proof(tree: MerkleTree, leaf_index: int, tx_label: str):
    """Print the inclusion proof for a specific leaf."""
    proof = tree.get_proof(leaf_index)
    leaf_hash = tree.levels[0][leaf_index]

    print()
    print(f"=== Inclusion Proof for {tx_label} (leaf #{leaf_index}) ===")
    print()
    print(f"  Leaf hash: {_short(leaf_hash)}")
    print(f"  Proof path ({len(proof)} sibling hashes):")
    print()

    for step, (sibling, direction) in enumerate(proof):
        side = "left" if direction == "L" else "right"
        print(f"    Step {step}: sibling {_short(sibling)} on the {side}")

    print()
    print(f"  Expected root: {_short(tree.root)}")


def demo():
    """Run a visual demonstration of Merkle trees."""

    # --- 1. Build tree from 8 transactions -----------------------------------

    print("=" * 60)
    print("  MERKLE TREES — Binary Hash Trees for Blockchains")
    print("=" * 60)
    print()
    print("Building a Merkle tree from 8 transactions...")

    # Simulate 8 blockchain transactions as raw byte data
    transactions = [
        b"Alice -> Bob: 5 BTC",
        b"Bob -> Charlie: 2 BTC",
        b"Charlie -> Dave: 1 BTC",
        b"Dave -> Eve: 3 BTC",
        b"Eve -> Frank: 0.5 BTC",
        b"Frank -> Grace: 1.5 BTC",
        b"Grace -> Heidi: 4 BTC",
        b"Heidi -> Alice: 2 BTC",
    ]

    tree = MerkleTree(transactions)

    # Show leaf hashes
    print()
    print("--- Leaf Hashes (one per transaction) ---")
    for i, tx in enumerate(transactions):
        print(f"  TX{i}: {tx.decode():30s} → {_short(tree.levels[0][i])}")

    # Show full tree structure
    _print_tree(tree)

    print()
    print(f"  Merkle Root: {tree.root.hex()}")
    print(f"  Tree height: {tree.height} levels")

    # --- 2. Generate and verify an inclusion proof ---------------------------

    target_index = 3  # Prove TX3 is in the tree
    target_tx = transactions[target_index]
    tx_label = f"TX{target_index}"

    _print_proof(tree, target_index, tx_label)

    proof = tree.get_proof(target_index)
    valid = MerkleTree.verify_proof(target_tx, proof, tree.root)

    print(f"  Verification: {'✓ VALID' if valid else '✗ INVALID'} — "
          f"leaf belongs to the tree")

    # --- 3. Tamper with data and show proof fails ----------------------------

    print()
    print("=== Tamper Detection ===")
    print()

    tampered_tx = b"Dave -> Eve: 9999 BTC"  # Attacker modifies the amount
    tampered_valid = MerkleTree.verify_proof(tampered_tx, proof, tree.root)

    print(f"  Original TX:  {target_tx.decode()}")
    print(f"  Tampered TX:  {tampered_tx.decode()}")
    print(f"  Same proof still valid? {'✓ YES' if tampered_valid else '✗ NO'}")
    print()
    print("  The Merkle root acts as a fingerprint of ALL data.")
    print("  Changing even one byte in one transaction changes the root.")

    # --- 4. Proof size efficiency --------------------------------------------

    print()
    print("=== Proof Size Efficiency ===")
    print()
    print("  To prove one transaction is in a block, you need:")
    print(f"    • Number of transactions:  {len(transactions)}")
    print(f"    • Proof size (siblings):   {len(proof)} hashes")
    print(f"    • That's log₂({len(transactions)}) = "
          f"{math.log2(len(transactions)):.0f} hashes")
    print()

    # Show scaling for larger trees
    print("  Scaling comparison:")
    print(f"    {'Transactions':>15s}  {'Proof hashes':>15s}  {'Savings':>10s}")
    print(f"    {'─' * 15}  {'─' * 15}  {'─' * 10}")
    for n in [8, 64, 1_024, 65_536, 1_000_000]:
        proof_size = math.ceil(math.log2(n))
        savings = (1 - proof_size / n) * 100
        print(f"    {n:>15,d}  {proof_size:>15d}  {savings:>9.4f}%")

    print()
    print("  With 1M transactions, you only need ~20 hashes to prove inclusion!")

    # --- 5. Odd-number handling demo -----------------------------------------

    print()
    print("=== Odd Number of Leaves ===")
    print()

    odd_txs = [b"TX_A", b"TX_B", b"TX_C", b"TX_D", b"TX_E"]
    odd_tree = MerkleTree(odd_txs)

    print(f"  Built tree from {len(odd_txs)} transactions (odd count).")
    print(f"  The last leaf is duplicated when pairing, so every node")
    print(f"  has a partner. Tree height: {odd_tree.height} levels.")
    print()

    # Verify proof still works with odd count
    odd_proof = odd_tree.get_proof(4)  # Last leaf (the one that gets duplicated)
    odd_valid = MerkleTree.verify_proof(b"TX_E", odd_proof, odd_tree.root)
    print(f"  Proof for last leaf (TX_E): "
          f"{'✓ VALID' if odd_valid else '✗ INVALID'}")

    print()
    print("=" * 60)
    print("  Done. Merkle trees let you verify data integrity")
    print("  with just O(log n) hashes instead of the full dataset.")
    print("=" * 60)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
