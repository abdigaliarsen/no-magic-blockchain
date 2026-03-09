"""
TITLE: Merkle Patricia Trie
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    A Modified Merkle Patricia Trie (MPT) as used in Ethereum for storing world
    state, transaction receipts, and storage. Supports insert, lookup, delete,
    and Merkle proof generation/verification — all from scratch.

KEY CONCEPTS:
    - Hex-prefix (compact) encoding for nibble paths
    - Four node types: blank, leaf, extension, branch (17-element array)
    - Deterministic root hash for any set of key-value pairs
    - Cryptographic proofs of inclusion/exclusion

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing fundamentals)
    - core/04_merkle_trees.py (basic Merkle tree concepts)

REAL-WORLD RELEVANCE:
    Ethereum's state trie, transaction trie, and receipt trie are all MPTs.
    The state root in each block header commits to the entire world state,
    enabling light clients to verify account balances with compact proofs.
"""

import hashlib  # SHA-256 for node hashing — stdlib only
import json     # For serializing nodes into hashable byte strings

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# How many hex chars of a hash to display (full SHA-256 = 64 hex chars)
HASH_DISPLAY_LEN = 12

# Branch nodes have 16 slots (one per hex nibble 0-f) plus a value slot
BRANCH_WIDTH = 17

# Hex-prefix flags used in compact encoding
HP_FLAG_LEAF = 2       # Bit flag indicating this path ends at a leaf
HP_FLAG_ODD = 1        # Bit flag indicating the nibble count is odd

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Hashing ---------------------------------------------------------------

def sha256(data: bytes) -> bytes:
    """Compute SHA-256 digest of raw bytes."""
    return hashlib.sha256(data).digest()


def hash_node(node) -> str:
    """Compute a deterministic hash of any trie node.

    We serialize the node to JSON bytes, then SHA-256 it.
    Returns a hex string for readability.
    """
    # Convert node structure to a canonical JSON representation
    raw = json.dumps(node, sort_keys=True).encode("utf-8")
    return sha256(raw).hex()


# --- Nibble helpers --------------------------------------------------------
# Ethereum keys are byte strings. We work with them as sequences of nibbles
# (half-bytes, values 0-15), since the trie branches on each hex digit.

def bytes_to_nibbles(data: bytes) -> list[int]:
    """Convert a byte string to a list of nibbles (4-bit values).

    Example: b'\\xab\\xcd' → [10, 11, 12, 13]
    Each byte produces two nibbles: high 4 bits, then low 4 bits.
    """
    nibbles = []
    for byte in data:
        nibbles.append(byte >> 4)        # High nibble
        nibbles.append(byte & 0x0F)      # Low nibble
    return nibbles


def nibbles_to_hex_str(nibbles: list[int]) -> str:
    """Convert nibbles to a readable hex string for display."""
    return "".join(f"{n:x}" for n in nibbles)


# --- Hex-prefix (compact) encoding ----------------------------------------
# Ethereum uses "hex-prefix" encoding to store nibble paths compactly.
# The first nibble of the encoded result carries two flags:
#   bit 1 (value 2): 1 = leaf node, 0 = extension node
#   bit 0 (value 1): 1 = odd number of nibbles (no padding needed)
# If the nibble count is even, a zero-padding nibble is inserted after the flag.

def hex_prefix_encode(nibbles: list[int], is_leaf: bool) -> list[int]:
    """Encode a nibble path with hex-prefix flags.

    Args:
        nibbles: The path as a list of 0-15 values.
        is_leaf: True for leaf nodes, False for extension nodes.

    Returns:
        Encoded nibble list with flag nibble (and optional padding) prepended.
    """
    # Build the flag nibble from leaf/extension bit and odd/even length bit
    flag = HP_FLAG_LEAF if is_leaf else 0
    if len(nibbles) % 2 == 1:
        # Odd length: flag nibble absorbs first data nibble — no padding needed
        flag |= HP_FLAG_ODD
        return [flag] + nibbles
    else:
        # Even length: insert a zero-padding nibble after the flag
        return [flag, 0] + nibbles


def hex_prefix_decode(encoded: list[int]) -> tuple[list[int], bool]:
    """Decode a hex-prefix encoded path back to nibbles + leaf flag.

    Returns:
        (nibbles, is_leaf) tuple.
    """
    flag = encoded[0]
    is_leaf = (flag & HP_FLAG_LEAF) != 0  # Check the leaf bit
    if flag & HP_FLAG_ODD:
        # Odd: data starts right after the flag nibble
        return encoded[1:], is_leaf
    else:
        # Even: skip the flag nibble AND the padding nibble
        return encoded[2:], is_leaf


# --- Shared prefix utility -------------------------------------------------

def shared_prefix_length(a: list[int], b: list[int]) -> int:
    """Return the number of leading elements that a and b share.

    Example: [1,2,3,4] and [1,2,5,6] → 2 (they share [1,2]).
    """
    length = 0
    for x, y in zip(a, b):
        if x != y:
            break
        length += 1
    return length


# --- Merkle Patricia Trie --------------------------------------------------

# Node types represented as Python data structures:
#   Blank:     None
#   Leaf:      ("leaf", encoded_path, value)
#   Extension: ("extension", encoded_path, child_hash)
#   Branch:    ("branch", [slot_0, slot_1, ..., slot_15, value])
#     Each slot is either None or a node hash (string).
#     slot[16] is the value stored at exactly this prefix (or None).

class MerklePatriciaTrie:
    """A Modified Merkle Patricia Trie with insert, lookup, delete, and proofs.

    Internally stores nodes in a dict keyed by their hash, with a root hash
    pointer. This mimics Ethereum's key-value DB backend (LevelDB/RocksDB).
    """

    def __init__(self):
        self.db: dict[str, object] = {}  # hash → node mapping (our "database")
        self.root_hash: str | None = None  # Hash of the root node, or None if empty

    # --- Node storage ------------------------------------------------------

    def _store_node(self, node) -> str:
        """Serialize and store a node, returning its hash."""
        h = hash_node(node)
        self.db[h] = node  # Persist node in our simulated DB
        return h

    def _get_node(self, node_hash: str):
        """Retrieve a node by its hash from the DB."""
        return self.db.get(node_hash)

    # --- Insert ------------------------------------------------------------

    def insert(self, key: bytes, value: str):
        """Insert a key-value pair into the trie.

        Args:
            key: Raw bytes key (will be converted to nibbles internally).
            value: The value to store (a string for simplicity).
        """
        nibbles = bytes_to_nibbles(key)  # Convert key to nibble path
        self.root_hash = self._insert(self.root_hash, nibbles, value)

    def _insert(self, node_hash: str | None, path: list[int], value: str) -> str:
        """Recursively insert into the subtrie rooted at node_hash.

        Returns the hash of the (possibly new) root of this subtrie.
        """
        if node_hash is None:
            # Empty subtrie — create a leaf holding the full remaining path
            encoded = hex_prefix_encode(path, is_leaf=True)
            return self._store_node(("leaf", encoded, value))

        node = self._get_node(node_hash)
        node_type = node[0]

        if node_type == "leaf":
            return self._insert_at_leaf(node, path, value)
        elif node_type == "extension":
            return self._insert_at_extension(node, path, value)
        elif node_type == "branch":
            return self._insert_at_branch(node, path, value)
        else:
            raise ValueError(f"Unknown node type: {node_type}")

    def _insert_at_leaf(self, leaf, path: list[int], value: str) -> str:
        """Handle insertion when we've reached an existing leaf node.

        If the paths match exactly, update the value.
        Otherwise, split into a branch (and possibly extensions).
        """
        existing_path, _ = hex_prefix_decode(leaf[1])
        existing_value = leaf[2]

        if existing_path == path:
            # Same key — update the value
            encoded = hex_prefix_encode(path, is_leaf=True)
            return self._store_node(("leaf", encoded, value))

        # Find where the paths diverge
        shared_len = shared_prefix_length(existing_path, path)

        # Create a branch node at the divergence point
        branch_slots = [None] * BRANCH_WIDTH  # 16 child slots + 1 value slot

        # --- Place the existing leaf in the branch ---
        if shared_len == len(existing_path):
            # The existing key is a prefix of the new key — its value goes
            # in the branch's value slot (index 16)
            branch_slots[16] = existing_value
        else:
            # The existing leaf continues beyond the branch — create a new leaf
            # with the remaining path after the divergence nibble
            remaining_existing = existing_path[shared_len + 1:]
            enc = hex_prefix_encode(remaining_existing, is_leaf=True)
            child_hash = self._store_node(("leaf", enc, existing_value))
            branch_slots[existing_path[shared_len]] = child_hash  # Slot by diverging nibble

        # --- Place the new value in the branch ---
        if shared_len == len(path):
            # The new key is a prefix of the existing key — store in value slot
            branch_slots[16] = value
        else:
            remaining_new = path[shared_len + 1:]
            enc = hex_prefix_encode(remaining_new, is_leaf=True)
            child_hash = self._store_node(("leaf", enc, value))
            branch_slots[path[shared_len]] = child_hash  # Slot by diverging nibble

        branch_hash = self._store_node(("branch", branch_slots))

        if shared_len > 0:
            # The shared prefix becomes an extension node pointing to the branch
            enc = hex_prefix_encode(path[:shared_len], is_leaf=False)
            return self._store_node(("extension", enc, branch_hash))
        else:
            return branch_hash

    def _insert_at_extension(self, ext, path: list[int], value: str) -> str:
        """Handle insertion when we've reached an extension node."""
        ext_path, _ = hex_prefix_decode(ext[1])
        ext_child = ext[2]  # Hash of the child node this extension points to

        shared_len = shared_prefix_length(ext_path, path)

        if shared_len == len(ext_path):
            # The new key shares the entire extension prefix — recurse into child
            new_child = self._insert(ext_child, path[shared_len:], value)
            enc = hex_prefix_encode(ext_path, is_leaf=False)
            return self._store_node(("extension", enc, new_child))

        # Partial match — split the extension
        branch_slots = [None] * BRANCH_WIDTH

        # Handle the remainder of the original extension after the split
        if shared_len + 1 == len(ext_path):
            # Only one nibble left — point directly to the original child
            branch_slots[ext_path[shared_len]] = ext_child
        else:
            # Multiple nibbles left — create a shorter extension
            remaining = ext_path[shared_len + 1:]
            enc = hex_prefix_encode(remaining, is_leaf=False)
            branch_slots[ext_path[shared_len]] = self._store_node(
                ("extension", enc, ext_child)
            )

        # Place the new value
        if shared_len == len(path):
            branch_slots[16] = value
        else:
            remaining_new = path[shared_len + 1:]
            enc = hex_prefix_encode(remaining_new, is_leaf=True)
            branch_slots[path[shared_len]] = self._store_node(
                ("leaf", enc, value)
            )

        branch_hash = self._store_node(("branch", branch_slots))

        if shared_len > 0:
            # Shared prefix becomes a new extension pointing to the branch
            enc = hex_prefix_encode(path[:shared_len], is_leaf=False)
            return self._store_node(("extension", enc, branch_hash))
        else:
            return branch_hash

    def _insert_at_branch(self, branch, path: list[int], value: str) -> str:
        """Handle insertion at a branch node."""
        slots = list(branch[1])  # Copy the slots list so we don't mutate the original

        if len(path) == 0:
            # We've consumed the entire path — store value in the branch's value slot
            slots[16] = value
        else:
            # Recurse into the appropriate child slot based on the next nibble
            nibble = path[0]
            slots[nibble] = self._insert(slots[nibble], path[1:], value)

        return self._store_node(("branch", slots))

    # --- Lookup ------------------------------------------------------------

    def lookup(self, key: bytes) -> str | None:
        """Look up a key in the trie, returning its value or None."""
        nibbles = bytes_to_nibbles(key)
        return self._lookup(self.root_hash, nibbles)

    def _lookup(self, node_hash: str | None, path: list[int]) -> str | None:
        """Recursively traverse the trie to find a value."""
        if node_hash is None:
            return None  # Empty subtrie — key not found

        node = self._get_node(node_hash)
        node_type = node[0]

        if node_type == "leaf":
            leaf_path, _ = hex_prefix_decode(node[1])
            if leaf_path == path:
                return node[2]  # Paths match — return the stored value
            return None  # Different path — key not found

        elif node_type == "extension":
            ext_path, _ = hex_prefix_decode(node[1])
            if path[:len(ext_path)] == ext_path:
                # Path starts with the extension prefix — follow it
                return self._lookup(node[2], path[len(ext_path):])
            return None  # Path doesn't match the extension

        elif node_type == "branch":
            slots = node[1]
            if len(path) == 0:
                return slots[16]  # Value stored at exactly this prefix
            nibble = path[0]
            return self._lookup(slots[nibble], path[1:])

        return None

    # --- Delete ------------------------------------------------------------

    def delete(self, key: bytes) -> bool:
        """Delete a key from the trie. Returns True if the key existed."""
        nibbles = bytes_to_nibbles(key)
        result = self._delete(self.root_hash, nibbles)
        if result is False:
            return False  # Key not found
        self.root_hash = result  # May be None if trie is now empty
        return True

    def _delete(self, node_hash: str | None, path: list[int]):
        """Recursively delete from the subtrie. Returns new hash, None, or False."""
        if node_hash is None:
            return False  # Key not in trie

        node = self._get_node(node_hash)
        node_type = node[0]

        if node_type == "leaf":
            leaf_path, _ = hex_prefix_decode(node[1])
            if leaf_path == path:
                return None  # Remove this leaf entirely
            return False  # Different key — nothing to delete

        elif node_type == "extension":
            ext_path, _ = hex_prefix_decode(node[1])
            if path[:len(ext_path)] != ext_path:
                return False  # Path doesn't match
            result = self._delete(node[2], path[len(ext_path):])
            if result is False:
                return False
            if result is None:
                return None  # Child gone — extension is pointless
            # Re-create extension pointing to the new child
            child = self._get_node(result)
            if child and child[0] == "leaf":
                # Merge extension + leaf into a single leaf
                child_path, _ = hex_prefix_decode(child[1])
                merged = ext_path + child_path
                enc = hex_prefix_encode(merged, is_leaf=True)
                return self._store_node(("leaf", enc, child[2]))
            elif child and child[0] == "extension":
                # Merge two extensions into one
                child_path, _ = hex_prefix_decode(child[1])
                merged = ext_path + child_path
                enc = hex_prefix_encode(merged, is_leaf=False)
                return self._store_node(("extension", enc, child[2]))
            enc = hex_prefix_encode(ext_path, is_leaf=False)
            return self._store_node(("extension", enc, result))

        elif node_type == "branch":
            slots = list(node[1])
            if len(path) == 0:
                slots[16] = None  # Remove value at this branch
            else:
                nibble = path[0]
                result = self._delete(slots[nibble], path[1:])
                if result is False:
                    return False
                slots[nibble] = result

            # Count remaining children to see if we can collapse the branch
            children = [(i, slots[i]) for i in range(16) if slots[i] is not None]
            has_value = slots[16] is not None

            if len(children) == 0 and not has_value:
                return None  # Branch is empty
            elif len(children) == 1 and not has_value:
                # Only one child left — collapse branch into extension or leaf
                idx, child_hash = children[0]
                child = self._get_node(child_hash)
                if child and child[0] == "leaf":
                    child_path, _ = hex_prefix_decode(child[1])
                    merged = [idx] + child_path
                    enc = hex_prefix_encode(merged, is_leaf=True)
                    return self._store_node(("leaf", enc, child[2]))
                elif child and child[0] == "extension":
                    child_path, _ = hex_prefix_decode(child[1])
                    merged = [idx] + child_path
                    enc = hex_prefix_encode(merged, is_leaf=False)
                    return self._store_node(("extension", enc, child[2]))
                else:
                    enc = hex_prefix_encode([idx], is_leaf=False)
                    return self._store_node(("extension", enc, child_hash))
            elif len(children) == 0 and has_value:
                # No children, just a value — convert to leaf with empty path
                enc = hex_prefix_encode([], is_leaf=True)
                return self._store_node(("leaf", enc, slots[16]))
            else:
                return self._store_node(("branch", slots))

        return False

    # --- Proof generation and verification ---------------------------------

    def generate_proof(self, key: bytes) -> list:
        """Generate a Merkle proof for a key (list of nodes along the path).

        The proof contains each node visited from root to the target,
        allowing independent verification without the full trie.
        """
        nibbles = bytes_to_nibbles(key)
        proof = []
        self._collect_proof(self.root_hash, nibbles, proof)
        return proof

    def _collect_proof(self, node_hash: str | None, path: list[int], proof: list):
        """Walk the trie, collecting every node on the path."""
        if node_hash is None:
            return
        node = self._get_node(node_hash)
        proof.append(node)  # Include this node in the proof

        node_type = node[0]
        if node_type == "leaf":
            return  # Leaf is the end of the path
        elif node_type == "extension":
            ext_path, _ = hex_prefix_decode(node[1])
            if path[:len(ext_path)] == ext_path:
                self._collect_proof(node[2], path[len(ext_path):], proof)
        elif node_type == "branch":
            if len(path) > 0:
                nibble = path[0]
                self._collect_proof(node[1][nibble], path[1:], proof)

    @staticmethod
    def verify_proof(proof: list, key: bytes, expected_value: str) -> bool:
        """Verify a Merkle proof for a key-value pair.

        Walks the proof nodes (which mirror the trie path) and checks that
        the final leaf contains the expected value at the expected path.
        """
        nibbles = bytes_to_nibbles(key)
        pos = 0  # Current position in the nibble path

        for i, node in enumerate(proof):
            node_type = node[0]

            if node_type == "leaf":
                leaf_path, _ = hex_prefix_decode(node[1])
                remaining = nibbles[pos:]
                # The leaf path must match the remaining nibbles
                if leaf_path == remaining and node[2] == expected_value:
                    return True
                return False

            elif node_type == "extension":
                ext_path, _ = hex_prefix_decode(node[1])
                remaining = nibbles[pos:pos + len(ext_path)]
                if remaining != ext_path:
                    return False  # Extension path doesn't match
                pos += len(ext_path)  # Advance past the extension

            elif node_type == "branch":
                if pos >= len(nibbles):
                    # We've consumed the full path — check the value slot
                    return node[1][16] == expected_value
                # Advance by one nibble (consumed by branch routing)
                pos += 1

        return False

    # --- Visualization -----------------------------------------------------

    def visualize(self, indent: int = 0):
        """Print a human-readable visualization of the trie structure."""
        if self.root_hash is None:
            print("  (empty trie)")
            return
        self._visualize_node(self.root_hash, indent)

    def _visualize_node(self, node_hash: str | None, indent: int):
        """Recursively print each node with tree-drawing characters."""
        if node_hash is None:
            return
        node = self._get_node(node_hash)
        prefix = "  " * indent  # Indentation for tree depth
        node_type = node[0]
        short_hash = node_hash[:HASH_DISPLAY_LEN]  # Truncated hash for display

        if node_type == "leaf":
            path, _ = hex_prefix_decode(node[1])
            path_str = nibbles_to_hex_str(path) if path else "(empty)"
            print(f"{prefix}├─ LEAF [{short_hash}] path={path_str} → \"{node[2]}\"")

        elif node_type == "extension":
            path, _ = hex_prefix_decode(node[1])
            path_str = nibbles_to_hex_str(path)
            print(f"{prefix}├─ EXT  [{short_hash}] path={path_str}")
            self._visualize_node(node[2], indent + 1)

        elif node_type == "branch":
            print(f"{prefix}├─ BRANCH [{short_hash}]")
            slots = node[1]
            for i in range(16):
                if slots[i] is not None:
                    print(f"{prefix}│  slot[{i:x}]:")
                    self._visualize_node(slots[i], indent + 2)
            if slots[16] is not None:
                print(f"{prefix}│  value: \"{slots[16]}\"")


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of the Merkle Patricia Trie."""

    print("=" * 70)
    print("  MERKLE PATRICIA TRIE — Ethereum's State Storage Structure")
    print("=" * 70)

    # --- Part 1: Hex-prefix encoding demo ----------------------------------
    print("\n--- Part 1: Hex-Prefix (Compact) Encoding ---\n")
    print("Ethereum stores nibble paths with a flag nibble that encodes:")
    print("  - Whether this is a leaf or extension node")
    print("  - Whether the nibble count is odd or even\n")

    test_cases = [
        ([1, 2, 3], True,  "leaf, odd nibbles "),
        ([1, 2, 3], False, "extension, odd     "),
        ([1, 2],    True,  "leaf, even nibbles "),
        ([1, 2],    False, "extension, even    "),
    ]

    print(f"  {'Description':<24} {'Original':>12} {'Encoded':>16} {'Decoded':>12}")
    print(f"  {'─' * 24} {'─' * 12} {'─' * 16} {'─' * 12}")
    for nibbles, is_leaf, desc in test_cases:
        encoded = hex_prefix_encode(nibbles, is_leaf)
        decoded_path, decoded_leaf = hex_prefix_decode(encoded)
        orig_str = nibbles_to_hex_str(nibbles)
        enc_str = nibbles_to_hex_str(encoded)
        dec_str = nibbles_to_hex_str(decoded_path)
        print(f"  {desc:<24} {orig_str:>12} {enc_str:>16} {dec_str:>12}")

    # --- Part 2: Building the trie -----------------------------------------
    print("\n--- Part 2: Building a Trie with 5 Key-Value Pairs ---\n")

    trie = MerklePatriciaTrie()

    # Use short keys for readable visualization
    entries = [
        (b"\xca\xfe", "coffee_balance"),     # Key: cafe
        (b"\xca\xbb", "cabbage_balance"),     # Key: cabb — shares prefix "ca" with cafe
        (b"\xde\xad", "dead_balance"),        # Key: dead — different prefix
        (b"\xca\xfe\x01", "coffee_v1"),       # Key: cafe01 — extends cafe
        (b"\xbe\xef", "beef_balance"),        # Key: beef — different prefix
    ]

    for i, (key, val) in enumerate(entries, 1):
        key_hex = key.hex()
        trie.insert(key, val)
        print(f"  [{i}] INSERT key=0x{key_hex} → \"{val}\"")

    print(f"\n  Root hash: {trie.root_hash[:HASH_DISPLAY_LEN]}...")
    print(f"  Total nodes in DB: {len(trie.db)}")

    print("\n  Trie structure:")
    trie.visualize(indent=1)

    # --- Part 3: Lookup demonstration --------------------------------------
    print("\n--- Part 3: Key Lookup ---\n")

    lookup_keys = [b"\xca\xfe", b"\xde\xad", b"\xff\xff"]
    for key in lookup_keys:
        result = trie.lookup(key)
        status = f"\"{result}\"" if result else "NOT FOUND"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} lookup(0x{key.hex()}) → {status}")

    # --- Part 4: Merkle proof generation and verification ------------------
    print("\n--- Part 4: Merkle Proof Generation & Verification ---\n")

    proof_key = b"\xca\xfe"
    proof_value = "coffee_balance"
    proof = trie.generate_proof(proof_key)

    print(f"  Generating proof for key=0x{proof_key.hex()} (value=\"{proof_value}\")")
    print(f"  Proof contains {len(proof)} node(s):\n")

    for i, node in enumerate(proof):
        node_type = node[0].upper()
        node_hash = hash_node(node)[:HASH_DISPLAY_LEN]
        if node_type == "LEAF":
            path, _ = hex_prefix_decode(node[1])
            print(f"    [{i}] {node_type:<6} hash={node_hash} path={nibbles_to_hex_str(path)}")
        elif node_type == "EXTENSION":
            path, _ = hex_prefix_decode(node[1])
            print(f"    [{i}] {node_type:<6} hash={node_hash} path={nibbles_to_hex_str(path)}")
        elif node_type == "BRANCH":
            active = [f"{j:x}" for j in range(16) if node[1][j] is not None]
            print(f"    [{i}] {node_type:<6} hash={node_hash} active_slots=[{','.join(active)}]")

    # Verify the proof
    valid = MerklePatriciaTrie.verify_proof(proof, proof_key, proof_value)
    print(f"\n  Proof verification: {'✓ VALID' if valid else '✗ INVALID'}")

    # Try verifying with a wrong value — should fail
    tampered = MerklePatriciaTrie.verify_proof(proof, proof_key, "TAMPERED_VALUE")
    print(f"  Tampered verification: {'✓ VALID' if tampered else '✗ INVALID (expected)'}")

    # --- Part 5: Delete operation ------------------------------------------
    print("\n--- Part 5: Delete Operation ---\n")

    delete_key = b"\xca\xbb"
    print(f"  Before delete: lookup(0x{delete_key.hex()}) → \"{trie.lookup(delete_key)}\"")

    old_root = trie.root_hash[:HASH_DISPLAY_LEN]
    deleted = trie.delete(delete_key)
    new_root = trie.root_hash[:HASH_DISPLAY_LEN] if trie.root_hash else "(empty)"

    print(f"  Deleted key 0x{delete_key.hex()}: {'✓ success' if deleted else '✗ not found'}")
    print(f"  After delete:  lookup(0x{delete_key.hex()}) → {trie.lookup(delete_key)}")
    print(f"\n  Root changed: {old_root}... → {new_root}...")
    print("  (Deleting any key changes the root hash — Merkle property!)")

    print("\n  Updated trie structure:")
    trie.visualize(indent=1)

    print("\n" + "=" * 70)
    print("  KEY TAKEAWAY: The MPT gives Ethereum a single root hash that")
    print("  commits to the entire world state. Any change to any account")
    print("  produces a different root, and light clients can verify individual")
    print("  values with compact Merkle proofs.")
    print("=" * 70)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
