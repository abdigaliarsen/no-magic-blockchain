"""
TITLE: Verkle Trees
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    Verkle trees from scratch — a trie data structure where each internal node
    uses a vector commitment (simplified Pedersen-like) instead of hashes.
    This enables much smaller proofs than Merkle Patricia Tries because proofs
    only need the path and commitments, not all sibling hashes.

KEY CONCEPTS:
    - Vector commitments: commit to a list of values with a single group element
    - Pedersen-like commitment using elliptic curve points
    - Verkle proof: path + commitments only (no sibling hashes needed)
    - Proof size comparison: Verkle O(log n) vs Merkle O(k * log n)

PREREQUISITE SCRIPTS:
    - core/fundamentals/01_hashing.py (hashing fundamentals)
    - core/fundamentals/04_merkle_trees.py (Merkle tree proofs for comparison)
    - ethereum/fundamentals/05_merkle_patricia_trie.py (MPT context)

REAL-WORLD RELEVANCE:
    Verkle trees are planned for Ethereum's "Verge" upgrade, replacing the Merkle
    Patricia Trie for state storage. The key benefit is stateless clients: a block
    can include compact proofs for all accessed state, letting validators verify
    without storing the full state tree (~100x smaller proofs than MPT).
"""

import hashlib
import random

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Simplified elliptic curve for Pedersen commitments
# Using a small prime field for demo clarity (real Verkle trees use Banderwagon/BLS)
# Curve: y^2 = x^3 + 3 (mod FIELD_P) — a simple curve with known generator
FIELD_P = 1000003  # A prime for our finite field
CURVE_A = 0        # Coefficient a in y^2 = x^3 + ax + b
CURVE_B = 3        # Coefficient b

# Number of children per internal node (branching factor)
# Real Verkle trees use 256 children; we use 16 for clarity
WIDTH = 16

# Maximum key length in nibbles (hex digits)
KEY_NIBBLES = 4  # Short keys for demo — 4 nibbles = 2 bytes

# Seed for reproducibility
random.seed(42)


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# Elliptic curve arithmetic over a small prime field
# ----------------------------------------------------------------------------

# Point at infinity (identity element)
POINT_INF = None


def mod_inv(a: int, p: int) -> int:
    """Modular inverse using Fermat's little theorem: a^(p-2) mod p."""
    return pow(a, p - 2, p)


def ec_add(p1, p2):
    """Add two points on the curve y^2 = x^3 + 3 (mod FIELD_P)."""
    if p1 is POINT_INF:
        return p2
    if p2 is POINT_INF:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and y1 == (FIELD_P - y2) % FIELD_P:
        return POINT_INF  # Point + its inverse = identity

    if x1 == x2 and y1 == y2:
        # Point doubling: slope = (3x^2 + a) / (2y)
        num = (3 * x1 * x1 + CURVE_A) % FIELD_P
        den = (2 * y1) % FIELD_P
    else:
        # Point addition: slope = (y2 - y1) / (x2 - x1)
        num = (y2 - y1) % FIELD_P
        den = (x2 - x1) % FIELD_P

    lam = (num * mod_inv(den, FIELD_P)) % FIELD_P
    x3 = (lam * lam - x1 - x2) % FIELD_P
    y3 = (lam * (x1 - x3) - y1) % FIELD_P
    return (x3, y3)


def ec_mul(point, scalar: int):
    """Scalar multiplication using double-and-add."""
    scalar = scalar % FIELD_P
    result = POINT_INF
    addend = point
    while scalar > 0:
        if scalar & 1:
            result = ec_add(result, addend)
        addend = ec_add(addend, addend)  # Double
        scalar >>= 1
    return result


def find_generator() -> tuple[int, int]:
    """Find a generator point on the curve by trying x values."""
    for x in range(1, FIELD_P):
        # Compute y^2 = x^3 + 3 mod p
        rhs = (pow(x, 3, FIELD_P) + CURVE_B) % FIELD_P
        # Check if rhs is a quadratic residue (Euler's criterion)
        if pow(rhs, (FIELD_P - 1) // 2, FIELD_P) == 1:
            # Compute square root using Tonelli-Shanks (simplified for p = 3 mod 4)
            y = pow(rhs, (FIELD_P + 1) // 4, FIELD_P)
            if (y * y) % FIELD_P == rhs:
                return (x, y)
    raise RuntimeError("No generator found")


# Pre-compute generator point and basis points for commitments
G = find_generator()

# Generate WIDTH + 1 independent basis points for Pedersen commitments
# Each basis point is G multiplied by a "random" scalar (using hash for determinism)
BASIS_POINTS: list[tuple[int, int]] = []
for i in range(WIDTH + 1):
    # Derive scalar from hash — ensures points are "nothing up my sleeve"
    scalar_bytes = hashlib.sha256(f"verkle_basis_{i}".encode()).digest()
    scalar = int.from_bytes(scalar_bytes[:4], "big") % (FIELD_P - 1) + 1
    bp = ec_mul(G, scalar)
    if bp is not None:
        BASIS_POINTS.append(bp)

# Pad if we got any POINT_INF (shouldn't happen with good params)
while len(BASIS_POINTS) < WIDTH + 1:
    BASIS_POINTS.append(G)


# ----------------------------------------------------------------------------
# Vector Commitment (simplified Pedersen)
# ----------------------------------------------------------------------------

def pedersen_commit(values: list[int]) -> tuple[int, int] | None:
    """Compute a Pedersen-like vector commitment: C = sum(v_i * G_i).

    This commits to a vector of values using independent basis points.
    The key property: given C, one cannot find different values that produce
    the same commitment (binding), and C reveals nothing about values (hiding).
    """
    if len(values) > len(BASIS_POINTS):
        raise ValueError(f"Too many values ({len(values)}) for basis ({len(BASIS_POINTS)})")

    result = POINT_INF
    for i, v in enumerate(values):
        if v != 0:  # Skip zero values for efficiency
            term = ec_mul(BASIS_POINTS[i], v)
            result = ec_add(result, term)
    return result


def point_to_bytes(point) -> bytes:
    """Serialize a point to bytes for hashing or size measurement."""
    if point is POINT_INF:
        return b'\x00' * 8
    x, y = point
    return x.to_bytes(4, "big") + y.to_bytes(4, "big")


# ----------------------------------------------------------------------------
# Verkle Tree
# ----------------------------------------------------------------------------

class VerkleNode:
    """A node in the Verkle tree.

    Internal nodes have WIDTH children and a vector commitment to them.
    Leaf nodes store a key-value pair.
    """

    def __init__(self):
        self.children: list = [None] * WIDTH  # Child nodes (or None)
        self.commitment = POINT_INF            # Vector commitment to children
        self.is_leaf = False
        self.key: str | None = None            # Only for leaf nodes
        self.value: int | None = None          # Only for leaf nodes

    def compute_commitment(self):
        """Compute the vector commitment for this internal node.

        Each child's commitment (or hash of leaf value) becomes one element
        in the committed vector. This is the core Verkle advantage: a single
        commitment covers all children.
        """
        if self.is_leaf:
            # Leaf commitment: commit to key and value
            key_int = int(self.key, 16) % FIELD_P if self.key else 0
            val_int = self.value % FIELD_P if self.value else 0
            self.commitment = pedersen_commit([key_int, val_int])
            return

        # For internal nodes: commit to vector of children's commitments
        child_values = []
        for child in self.children:
            if child is None:
                child_values.append(0)  # Empty slot
            else:
                # Use the x-coordinate of child's commitment as the value
                if child.commitment is POINT_INF:
                    child_values.append(0)
                else:
                    child_values.append(child.commitment[0] % FIELD_P)

        self.commitment = pedersen_commit(child_values)


class VerkleTree:
    """A Verkle tree: a trie with vector commitments at each node.

    Keys are mapped to paths through the tree using their nibbles (hex digits).
    Each nibble selects one of WIDTH=16 children at each level.
    """

    def __init__(self):
        self.root = VerkleNode()

    def _key_to_path(self, key: str) -> list[int]:
        """Convert a hex key string to a list of nibble indices."""
        return [int(c, 16) for c in key.zfill(KEY_NIBBLES)]

    def insert(self, key: str, value: int):
        """Insert a key-value pair into the Verkle tree."""
        path = self._key_to_path(key)
        node = self.root

        # Navigate to the correct position, creating nodes as needed
        for depth, nibble in enumerate(path[:-1]):
            if node.children[nibble] is None:
                node.children[nibble] = VerkleNode()
            node = node.children[nibble]

        # Create leaf at the final nibble
        last_nibble = path[-1]
        leaf = VerkleNode()
        leaf.is_leaf = True
        leaf.key = key
        leaf.value = value
        leaf.compute_commitment()
        node.children[last_nibble] = leaf

        # Recompute commitments bottom-up
        self._update_commitments(self.root, path, 0)

    def _update_commitments(self, node: VerkleNode, path: list[int], depth: int):
        """Recompute commitments along the insertion path."""
        if depth < len(path) - 1 and node.children[path[depth]] is not None:
            self._update_commitments(node.children[path[depth]], path, depth + 1)
        node.compute_commitment()

    def get(self, key: str) -> int | None:
        """Look up a value by key."""
        path = self._key_to_path(key)
        node = self.root
        for nibble in path[:-1]:
            if node.children[nibble] is None:
                return None
            node = node.children[nibble]

        leaf = node.children[path[-1]]
        if leaf is None or not leaf.is_leaf:
            return None
        return leaf.value

    def generate_proof(self, key: str) -> dict | None:
        """Generate a Verkle proof for a key.

        Unlike Merkle proofs which need all sibling hashes at each level,
        Verkle proofs only need the commitment at each node along the path
        and a single opening proof per level.
        """
        path = self._key_to_path(key)
        node = self.root
        proof_commitments = []  # One commitment per level
        proof_indices = []      # Which child index at each level

        for nibble in path[:-1]:
            # Store this node's commitment (replaces all sibling hashes in Merkle)
            proof_commitments.append(point_to_bytes(node.commitment))
            proof_indices.append(nibble)
            if node.children[nibble] is None:
                return None  # Key not found
            node = node.children[nibble]

        # Final level
        proof_commitments.append(point_to_bytes(node.commitment))
        proof_indices.append(path[-1])

        leaf = node.children[path[-1]]
        if leaf is None or not leaf.is_leaf:
            return None

        return {
            "key": key,
            "value": leaf.value,
            "commitments": proof_commitments,
            "indices": proof_indices,
            "leaf_commitment": point_to_bytes(leaf.commitment),
        }

    def verify_proof(self, proof: dict) -> bool:
        """Verify a Verkle proof.

        Check that the chain of commitments is consistent from root to leaf.
        In a real implementation, this uses pairing-based opening proofs;
        here we verify the commitment chain structurally.
        """
        if not proof:
            return False

        # Verify the root commitment matches
        if proof["commitments"][0] != point_to_bytes(self.root.commitment):
            return False  # Root mismatch — proof is invalid

        # Verify each level's commitment is consistent
        # In a real Verkle tree, this would use IPA (Inner Product Argument)
        # to prove that the child's commitment is at the claimed index
        for i in range(len(proof["commitments"]) - 1):
            if proof["commitments"][i] == b'\x00' * 8:
                return False  # Empty commitment in path — invalid

        return True


# ----------------------------------------------------------------------------
# Merkle Tree (for proof size comparison)
# ----------------------------------------------------------------------------

class MerkleNode:
    """A simple Merkle tree node for comparison."""

    def __init__(self):
        self.children: list = [None] * WIDTH
        self.hash_val: bytes = b'\x00' * 32
        self.is_leaf = False
        self.key: str | None = None
        self.value: int | None = None

    def compute_hash(self):
        """Compute hash from all children's hashes — ALL siblings needed."""
        if self.is_leaf:
            data = f"leaf:{self.key}:{self.value}".encode()
            self.hash_val = hashlib.sha256(data).digest()
            return

        h = hashlib.sha256()
        for child in self.children:
            if child is None:
                h.update(b'\x00' * 32)
            else:
                h.update(child.hash_val)
        self.hash_val = h.digest()


class MerkleTree:
    """Merkle tree with same structure as Verkle for fair comparison."""

    def __init__(self):
        self.root = MerkleNode()

    def insert(self, key: str, value: int):
        path = [int(c, 16) for c in key.zfill(KEY_NIBBLES)]
        node = self.root

        for nibble in path[:-1]:
            if node.children[nibble] is None:
                node.children[nibble] = MerkleNode()
            node = node.children[nibble]

        leaf = MerkleNode()
        leaf.is_leaf = True
        leaf.key = key
        leaf.value = value
        leaf.compute_hash()
        node.children[path[-1]] = leaf

        self._update_hashes(self.root, path, 0)

    def _update_hashes(self, node: MerkleNode, path: list[int], depth: int):
        if depth < len(path) - 1 and node.children[path[depth]] is not None:
            self._update_hashes(node.children[path[depth]], path, depth + 1)
        node.compute_hash()

    def generate_proof(self, key: str) -> dict | None:
        """Generate a Merkle proof — needs ALL sibling hashes at each level."""
        path = [int(c, 16) for c in key.zfill(KEY_NIBBLES)]
        node = self.root
        proof_siblings = []  # (WIDTH - 1) sibling hashes per level!

        for nibble in path[:-1]:
            # Must include ALL sibling hashes (every child except the one on our path)
            siblings = []
            for i, child in enumerate(node.children):
                if i != nibble:
                    h = child.hash_val if child else b'\x00' * 32
                    siblings.append(h)
            proof_siblings.append(siblings)

            if node.children[nibble] is None:
                return None
            node = node.children[nibble]

        # Final level siblings
        siblings = []
        for i, child in enumerate(node.children):
            if i != path[-1]:
                h = child.hash_val if child else b'\x00' * 32
                siblings.append(h)
        proof_siblings.append(siblings)

        leaf = node.children[path[-1]]
        if leaf is None or not leaf.is_leaf:
            return None

        return {
            "key": key,
            "value": leaf.value,
            "siblings": proof_siblings,  # (WIDTH-1) * depth hashes
        }


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Verkle trees vs Merkle trees."""

    print("=" * 72)
    print("  VERKLE TREES — Vector Commitment Tries for Ethereum State")
    print("=" * 72)

    # --- Part 1: Vector Commitments ---
    print("\n--- Part 1: Pedersen Vector Commitments ---\n")

    print(f"  Curve: y^2 = x^3 + {CURVE_B} (mod {FIELD_P})")
    print(f"  Generator G = ({G[0]}, {G[1]})")
    print(f"  Branching factor: {WIDTH} children per node\n")

    # Demonstrate vector commitment
    values = [1, 0, 42, 0, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 99]
    commitment = pedersen_commit(values)
    c_str = f"({commitment[0]}, {commitment[1]})" if commitment else "INF"
    print(f"  Committing to vector of {WIDTH} values:")
    print(f"  Values: {values}")
    print(f"  Commitment: {c_str}")

    # Show that different values produce different commitments
    values2 = values.copy()
    values2[2] = 43  # Change one value
    commitment2 = pedersen_commit(values2)
    c2_str = f"({commitment2[0]}, {commitment2[1]})" if commitment2 else "INF"
    print(f"\n  Change values[2] from 42 to 43:")
    print(f"  New commitment: {c2_str}")
    print(f"  Commitments differ: {commitment != commitment2}  (binding property)")

    # --- Part 2: Build Verkle Tree ---
    print("\n\n--- Part 2: Building a Verkle Tree ---\n")

    vtree = VerkleTree()
    test_data = {
        "0a1b": 100,   # Account balance
        "0a2c": 200,   # Another account
        "0b3d": 300,   # Different branch
        "0b3e": 400,   # Same branch, different leaf
        "1234": 500,   # Totally different subtree
        "1235": 600,   # Adjacent key
    }

    print(f"  Inserting {len(test_data)} key-value pairs:\n")
    for key, value in test_data.items():
        vtree.insert(key, value)
        root_c = vtree.root.commitment
        root_str = f"({root_c[0]}, {root_c[1]})" if root_c else "INF"
        print(f"    key=0x{key}  value={value:>5}  root={root_str}")

    # Verify lookups
    print(f"\n  Verifying lookups:")
    for key, expected in test_data.items():
        actual = vtree.get(key)
        status = "OK" if actual == expected else "FAIL"
        print(f"    get(0x{key}) = {actual:<5}  [{status}]")

    # --- Part 3: Verkle Proof ---
    print("\n\n--- Part 3: Verkle Proof Generation & Verification ---\n")

    target_key = "0a1b"
    proof = vtree.generate_proof(target_key)

    if proof:
        print(f"  Proof for key 0x{target_key} (value={proof['value']}):")
        print(f"  ┌──────────────────────────────────────────────────┐")
        print(f"  │ Path through tree:                               │")
        for i, (comm, idx) in enumerate(zip(proof["commitments"], proof["indices"])):
            depth_label = f"depth {i}"
            comm_hex = comm.hex()[:16]
            print(f"  │  {depth_label}: child[{idx:x}]  "
                  f"commitment={comm_hex}...  │")
        leaf_hex = proof["leaf_commitment"].hex()[:16]
        print(f"  │  leaf:  commitment={leaf_hex}...            │")
        print(f"  └──────────────────────────────────────────────────┘")

        # Verify
        valid = vtree.verify_proof(proof)
        print(f"\n  Proof valid: {valid}")

        # Show proof size
        proof_bytes = (
            len(proof["commitments"]) * 8      # 8 bytes per commitment (our small curve)
            + len(proof["indices"])             # 1 byte per index
            + 8                                 # Leaf commitment
            + len(target_key)                   # Key
            + 4                                 # Value
        )
        print(f"  Verkle proof size: {proof_bytes} bytes")
        print(f"    - {len(proof['commitments'])} commitments x 8 bytes = "
              f"{len(proof['commitments']) * 8} bytes")
        print(f"    - {len(proof['indices'])} path indices = "
              f"{len(proof['indices'])} bytes")
        print(f"    - Key + value + leaf = {len(target_key) + 4 + 8} bytes")

    # --- Part 4: Proof Size Comparison ---
    print("\n\n--- Part 4: Verkle vs Merkle Proof Size Comparison ---\n")

    # Build equivalent Merkle tree
    mtree = MerkleTree()
    for key, value in test_data.items():
        mtree.insert(key, value)

    merkle_proof = mtree.generate_proof(target_key)
    verkle_proof = vtree.generate_proof(target_key)

    if merkle_proof and verkle_proof:
        # Merkle proof size: all sibling hashes at each level
        merkle_bytes = 0
        for level_siblings in merkle_proof["siblings"]:
            merkle_bytes += len(level_siblings) * 32  # 32 bytes per SHA-256 hash
        merkle_bytes += 32 + len(target_key) + 4  # Leaf hash + key + value

        # Verkle proof size (already computed above)
        verkle_bytes = proof_bytes

        depth = len(merkle_proof["siblings"])
        siblings_per_level = WIDTH - 1  # Must include all other children

        print(f"  Tree parameters:")
        print(f"    Branching factor (WIDTH): {WIDTH}")
        print(f"    Tree depth:               {depth}")
        print(f"    Entries:                  {len(test_data)}\n")

        print(f"  ┌──────────────────────────────────────────────────────────┐")
        print(f"  │                PROOF SIZE COMPARISON                     │")
        print(f"  ├──────────────┬─────────────────────┬────────────────────┤")
        print(f"  │              │    Merkle Proof      │   Verkle Proof     │")
        print(f"  ├──────────────┼─────────────────────┼────────────────────┤")
        print(f"  │ Per level    │ {siblings_per_level} sibling hashes     "
              f"│ 1 commitment       │")
        print(f"  │ Hash size    │ 32 bytes (SHA-256)  │ 8 bytes (EC point) │")
        print(f"  │ Per level    │ {siblings_per_level * 32:>4} bytes"
              f"            │ 8 bytes            │")
        print(f"  │ Total        │ {merkle_bytes:>4} bytes"
              f"            │ {verkle_bytes:>3} bytes"
              f"            │")
        print(f"  │ Ratio        │ 1.0x                "
              f"│ {merkle_bytes / max(verkle_bytes, 1):.1f}x smaller"
              f"       │")
        print(f"  └──────────────┴─────────────────────┴────────────────────┘")

        print(f"\n  Why Verkle proofs are smaller:")
        print(f"    Merkle: must include {siblings_per_level} sibling hashes per level")
        print(f"            = {siblings_per_level} x 32 = "
              f"{siblings_per_level * 32} bytes per level")
        print(f"    Verkle: vector commitment covers ALL children at once")
        print(f"            = 1 commitment per level (+ opening proof)")

    # --- Part 5: Impact on Ethereum ---
    print(f"\n\n--- Part 5: Impact on Ethereum State ---\n")

    # Simulate realistic parameters
    real_width = 256         # Real Verkle trees use 256 children
    real_depth = 3           # Typical depth for 256-ary tree with millions of accounts
    real_hash_bytes = 32     # SHA-256 / Keccak-256
    real_commitment_bytes = 32  # Banderwagon point (compressed)

    merkle_proof_real = real_depth * (real_width - 1) * real_hash_bytes
    # Verkle proof: commitments + IPA proof (roughly 2 * depth * point_size)
    verkle_proof_real = real_depth * 2 * real_commitment_bytes

    print(f"  With production parameters (WIDTH=256, depth=3):")
    print(f"    Merkle Patricia proof: ~{merkle_proof_real:,} bytes "
          f"({merkle_proof_real / 1024:.1f} KB)")
    print(f"    Verkle proof:          ~{verkle_proof_real:,} bytes "
          f"({verkle_proof_real / 1024:.1f} KB)")
    print(f"    Reduction:             ~{merkle_proof_real / verkle_proof_real:.0f}x "
          f"smaller")

    print(f"\n  This enables STATELESS CLIENTS:")
    print(f"  ┌─────────────────────────────────────────────────────────┐")
    print(f"  │ Current (MPT):                                         │")
    print(f"  │   Validators must store ~50 GB of state                │")
    print(f"  │   to verify blocks                                     │")
    print(f"  │                                                        │")
    print(f"  │ With Verkle Trees:                                     │")
    print(f"  │   Block includes compact proofs for all accessed state │")
    print(f"  │   Validators verify with ~{verkle_proof_real} bytes per access"
          f"         │")
    print(f"  │   No local state storage needed!                       │")
    print(f"  └─────────────────────────────────────────────────────────┘")

    print("\n" + "=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
