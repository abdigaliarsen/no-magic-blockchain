"""
TITLE: Taproot & MAST (BIP 341)
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    Taproot output construction using tweaked public keys and Merkelized
    Alternative Script Trees (MAST). Demonstrates key-path spending (a single
    signature with no scripts revealed) and script-path spending (reveal one
    script branch plus a Merkle proof to the commitment).

KEY CONCEPTS:
    - Taproot output: P = Q + hash(Q || script_tree_root) * G
    - Key-path spend: sign with tweaked private key (nothing revealed)
    - Script-path spend: reveal script + Merkle proof + internal pubkey
    - MAST: only the executed branch is revealed, all others stay hidden

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - core/04_merkle_trees.py (Merkle tree construction)
    - bitcoin/intermediate/09_schnorr_signatures.py (Schnorr sign/verify)

REAL-WORLD RELEVANCE:
    Taproot (BIP 341) activated on Bitcoin in November 2021. It combines Schnorr
    signatures with MAST to make complex spending conditions (multisig, timelocks,
    etc.) look identical to simple single-key spends on-chain, dramatically
    improving privacy and reducing transaction sizes for complex scripts.
"""

import hashlib  # For SHA-256 and tagged hashing
import os       # For random number generation

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# secp256k1 parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (GX, GY)

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Elliptic curve helpers ---

def _mod_inverse(a, m):
    """Modular inverse using extended Euclidean algorithm."""
    if a < 0:
        a = a % m
    g, x, _ = _ext_gcd(a, m)
    if g != 1:
        raise ValueError("No inverse")
    return x % m


def _ext_gcd(a, b):
    """Extended GCD."""
    if a == 0:
        return b, 0, 1
    g, x1, y1 = _ext_gcd(b % a, a)
    return g, y1 - (b // a) * x1, x1


def point_add(p1, p2):
    """Add two secp256k1 points."""
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and y1 != y2:
        return None
    if x1 == x2:
        lam = (3 * x1 * x1 * _mod_inverse(2 * y1, P)) % P
    else:
        lam = ((y2 - y1) * _mod_inverse(x2 - x1, P)) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def scalar_mult(k, point):
    """Scalar multiplication via double-and-add."""
    result = None
    addend = point
    k = k % N
    while k > 0:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1
    return result


def has_even_y(point):
    """BIP 340: check if Y coordinate is even."""
    return point[1] % 2 == 0


def x_only(point):
    """Extract 32-byte x-only public key."""
    return point[0].to_bytes(32, "big")


def lift_x(x_bytes):
    """Recover full point from x-only key (even Y)."""
    x = int.from_bytes(x_bytes, "big")
    if x >= P:
        return None
    y_sq = (pow(x, 3, P) + 7) % P
    y = pow(y_sq, (P + 1) // 4, P)
    if pow(y, 2, P) != y_sq:
        return None
    if y % 2 != 0:
        y = P - y
    return (x, y)


# --- Tagged hashes (BIP 340/341) ---

def tagged_hash(tag, data):
    """Domain-separated hash: SHA256(SHA256(tag) || SHA256(tag) || data)."""
    tag_hash = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()


# --- Schnorr sign/verify (minimal, for Taproot key-path spending) ---

def schnorr_sign(secret_key_int, message):
    """Sign a 32-byte message using Schnorr (BIP 340)."""
    d = secret_key_int
    pub = scalar_mult(d, G)
    if not has_even_y(pub):
        d = N - d  # Negate so pubkey has even Y

    # Deterministic nonce
    aux = os.urandom(32)
    t = bytes(a ^ b for a, b in zip(d.to_bytes(32, "big"), tagged_hash("BIP0340/aux", aux)))
    k_hash = tagged_hash("BIP0340/nonce", t + x_only(pub) + message)
    k = int.from_bytes(k_hash, "big") % N
    if k == 0:
        k = 1

    R = scalar_mult(k, G)
    if not has_even_y(R):
        k = N - k
        R = scalar_mult(k, G)

    e_hash = tagged_hash("BIP0340/challenge", x_only(R) + x_only(pub) + message)
    e = int.from_bytes(e_hash, "big") % N
    s = (k + e * d) % N

    return x_only(R) + s.to_bytes(32, "big")


def schnorr_verify(pubkey_bytes, message, sig):
    """Verify a BIP 340 Schnorr signature."""
    R_x = sig[:32]
    s = int.from_bytes(sig[32:], "big")
    if s >= N:
        return False
    pub = lift_x(pubkey_bytes)
    if pub is None:
        return False
    e_hash = tagged_hash("BIP0340/challenge", R_x + pubkey_bytes + message)
    e = int.from_bytes(e_hash, "big") % N
    sG = scalar_mult(s, G)
    eP = scalar_mult(e, pub)
    neg_eP = (eP[0], P - eP[1])
    R_computed = point_add(sG, neg_eP)
    if R_computed is None or not has_even_y(R_computed):
        return False
    return R_computed[0].to_bytes(32, "big") == R_x


# --- Script representation (simplified) ---

class TapScript:
    """A simplified taproot script leaf."""
    def __init__(self, name, script_bytes):
        self.name = name                      # Human-readable name
        self.script_bytes = script_bytes      # Opaque script content
        self.leaf_version = 0xC0              # BIP 342 default leaf version

    def leaf_hash(self):
        """Compute the tagged hash for this script leaf."""
        # TapLeaf = tagged_hash("TapLeaf", leaf_version || compact_size(script) || script)
        size = len(self.script_bytes)
        return tagged_hash("TapLeaf",
                           bytes([self.leaf_version]) +
                           size.to_bytes(1, "big") +
                           self.script_bytes)


# --- MAST (Merkelized Alternative Script Tree) ---

def build_mast(scripts):
    """
    Build a MAST from a list of TapScript leaves.
    Returns (root_hash, tree_structure) where tree_structure allows
    computing Merkle proofs for any leaf.

    We build a balanced binary tree. Each internal node is:
      tagged_hash("TapBranch", sorted(left || right))
    Sorting ensures the tree is deterministic regardless of insert order.
    """
    if len(scripts) == 0:
        return None, None

    # Compute leaf hashes
    leaves = [(s.leaf_hash(), s) for s in scripts]

    # Build tree bottom-up, storing structure for proof generation
    # tree_map[leaf_hash] = list of (sibling_hash, position) pairs
    tree_map = {h: [] for h, _ in leaves}

    level = [h for h, _ in leaves]
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                left, right = level[i], level[i + 1]
                # BIP 341: sort the two children lexicographically
                if left > right:
                    left, right = right, left
                parent = tagged_hash("TapBranch", left + right)
                # Record sibling for proof path
                for h in tree_map:
                    if _is_descendant(h, level[i], tree_map) or h == level[i]:
                        tree_map[h].append(level[i + 1])
                    elif _is_descendant(h, level[i + 1], tree_map) or h == level[i + 1]:
                        tree_map[h].append(level[i])
                next_level.append(parent)
            else:
                next_level.append(level[i])  # Odd one out, promote
        level = next_level

    root = level[0]
    return root, (leaves, tree_map)


def _is_descendant(leaf_hash, node_hash, tree_map):
    """Check if leaf_hash is a descendant of node_hash (simplified)."""
    return False  # Not needed for our proof approach


def get_merkle_proof(scripts, target_index):
    """
    Build the MAST and return the Merkle proof (list of sibling hashes)
    for the script at target_index.
    Uses a direct approach: build tree level by level, track the target.
    """
    leaf_hashes = [s.leaf_hash() for s in scripts]

    proof = []
    level = leaf_hashes[:]
    target_pos = target_index

    while len(level) > 1:
        next_level = []
        next_pos = target_pos // 2

        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                left, right = level[i], level[i + 1]
                # If our target is one of these two, record the sibling
                if i == target_pos or i + 1 == target_pos:
                    sibling = level[i + 1] if i == target_pos else level[i]
                    proof.append(sibling)
                # Sort for deterministic hashing
                if left > right:
                    left, right = right, left
                parent = tagged_hash("TapBranch", left + right)
                next_level.append(parent)
            else:
                next_level.append(level[i])

        level = next_level
        target_pos = next_pos

    return proof, level[0]  # proof path + root hash


def verify_merkle_proof(leaf_hash, proof, root):
    """Verify a Merkle proof for a leaf against the MAST root."""
    current = leaf_hash
    for sibling in proof:
        # BIP 341: always sort before hashing
        if current > sibling:
            current, sibling = sibling, current
        current = tagged_hash("TapBranch", current + sibling)
    return current == root


# --- Taproot key tweaking ---

def compute_tweak(internal_pubkey_bytes, mast_root):
    """
    Compute the Taproot tweak: t = tagged_hash("TapTweak", P || root).
    If there are no scripts (key-only), t = tagged_hash("TapTweak", P).
    """
    if mast_root is not None:
        return tagged_hash("TapTweak", internal_pubkey_bytes + mast_root)
    else:
        return tagged_hash("TapTweak", internal_pubkey_bytes)


def taproot_tweak_pubkey(internal_point, mast_root):
    """
    Compute the tweaked output key: Q = P + t*G.
    Returns (tweaked_point, tweak_int).
    """
    internal_pk = x_only(internal_point)
    t_bytes = compute_tweak(internal_pk, mast_root)
    t = int.from_bytes(t_bytes, "big") % N

    # Q = P + t*G
    tG = scalar_mult(t, G)
    # Ensure P has even Y for tweaking
    p = internal_point
    if not has_even_y(p):
        p = (p[0], P - p[1])
    Q = point_add(p, tG)

    return Q, t


def taproot_tweak_seckey(secret_key_int, mast_root):
    """
    Compute the tweaked secret key: d' = d + t (mod N).
    If d's public key has odd Y, negate d first.
    """
    pub = scalar_mult(secret_key_int, G)
    d = secret_key_int
    if not has_even_y(pub):
        d = N - d  # Negate to match even Y convention

    internal_pk = x_only(scalar_mult(d, G))
    t_bytes = compute_tweak(internal_pk, mast_root)
    t = int.from_bytes(t_bytes, "big") % N

    d_prime = (d + t) % N
    return d_prime


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Demonstrate Taproot output creation, key-path and script-path spending."""

    print("=" * 70)
    print("        TAPROOT & MAST (BIP 341)")
    print("=" * 70)

    # --- Generate internal key ---
    print("\n--- Step 1: Generate Internal Key ---\n")
    sk_int = int.from_bytes(os.urandom(32), "big") % N
    if sk_int == 0:
        sk_int = 1
    internal_pub = scalar_mult(sk_int, G)
    if not has_even_y(internal_pub):
        internal_pub = (internal_pub[0], P - internal_pub[1])
    print(f"  Internal public key (x): {x_only(internal_pub).hex()[:32]}...")

    # --- Create script branches ---
    print("\n--- Step 2: Create Script Tree (MAST) ---\n")

    # Three alternative spending conditions
    scripts = [
        TapScript("2-of-3 Multisig",     b"\x52\x21" + os.urandom(33) + b"\x21" + os.urandom(33) + b"\x52\xae"),
        TapScript("Timelock (1 year)",    b"\x03\x01\x00\x40\xb1\x75"),
        TapScript("Hash preimage reveal", b"\xa8\x20" + hashlib.sha256(b"secret").digest() + b"\x87"),
    ]

    print("  Script tree:")
    print("          ┌─────────┐")
    print("          │  root   │")
    print("          └────┬────┘")
    print("         ┌─────┴─────┐")
    print("         │           │")
    print("    ┌────┴───┐  ┌────┴───────────┐")
    for i, s in enumerate(scripts):
        leaf_h = s.leaf_hash().hex()[:16]
        print(f"    │ Script {i}: │  {s.name}")
        print(f"    │ {leaf_h}│")
    print()

    # Build MAST
    leaf_hashes = [s.leaf_hash() for s in scripts]
    _, mast_root = get_merkle_proof(scripts, 0)  # Just to get root

    print(f"  MAST root: {mast_root.hex()[:32]}...")

    # --- Tweak the key ---
    print("\n--- Step 3: Create Taproot Output ---\n")

    Q, tweak = taproot_tweak_pubkey(internal_pub, mast_root)
    output_key = x_only(Q)
    print(f"  Tweaked output key Q:  {output_key.hex()[:32]}...")
    print(f"  Tweak value t:         {tweak:#010x}...")
    print(f"\n  Q = P + t*G")
    print(f"  This single key commits to both the internal key AND all scripts.")
    print(f"  On-chain, it looks identical to any other Schnorr public key.")

    # --- Key-path spend ---
    print("\n--- Step 4: Key-Path Spend (cooperative) ---\n")

    message = hashlib.sha256(b"spend taproot output via key path").digest()
    tweaked_sk = taproot_tweak_seckey(sk_int, mast_root)

    # Sign with tweaked key
    sig = schnorr_sign(tweaked_sk, message)
    valid = schnorr_verify(x_only(scalar_mult(tweaked_sk, G)), message, sig)

    print(f"  Spending message: \"spend taproot output via key path\"")
    print(f"  Signature: {sig.hex()[:32]}...")
    print(f"  Verification: {'PASS' if valid else 'FAIL'}")
    print(f"\n  Witness data:")
    print(f"  ┌──────────────────────────────────────────┐")
    print(f"  │ signature (64 bytes)                     │")
    print(f"  └──────────────────────────────────────────┘")
    print(f"  Total witness: 64 bytes")
    print(f"  No scripts revealed! Maximum privacy.")

    # --- Script-path spend ---
    print("\n--- Step 5: Script-Path Spend (uncooperative) ---\n")

    # Spend via script index 2 (hash preimage reveal)
    spend_index = 2
    spend_script = scripts[spend_index]
    proof, root = get_merkle_proof(scripts, spend_index)

    print(f"  Revealing script: \"{spend_script.name}\" (index {spend_index})")
    print(f"  Script leaf hash: {spend_script.leaf_hash().hex()[:32]}...")

    # Verify proof
    proof_valid = verify_merkle_proof(spend_script.leaf_hash(), proof, root)
    print(f"\n  Merkle proof ({len(proof)} sibling(s)):")
    for i, sib in enumerate(proof):
        print(f"    [{i}] {sib.hex()[:32]}...")

    print(f"\n  Proof verification: {'PASS' if proof_valid else 'FAIL'}")

    print(f"\n  Witness data:")
    print(f"  ┌──────────────────────────────────────────┐")
    print(f"  │ script satisfaction (preimage, etc.)      │")
    print(f"  │ script ({len(spend_script.script_bytes)} bytes)           │")
    print(f"  │ control block:                            │")
    print(f"  │   internal pubkey (32 bytes)              │")
    for i in range(len(proof)):
        print(f"  │   proof sibling [{i}] (32 bytes)             │")
    print(f"  └──────────────────────────────────────────┘")

    script_witness = (len(spend_script.script_bytes) + 32 + 1 +
                      32 * len(proof) + 32)  # script + internal key + leaf version + proof + satisfaction
    print(f"  Total witness: ~{script_witness} bytes")

    # --- Privacy comparison ---
    print("\n--- Step 6: Privacy Comparison ---\n")

    num_scripts = len(scripts)
    print(f"  {num_scripts} spending conditions were committed to.")
    print(f"  Key-path spend:    0 conditions revealed (looks like single-sig)")
    print(f"  Script-path spend: 1 condition revealed, {num_scripts - 1} stay hidden")
    print()
    print("  ┌─────────────────────┬───────────┬──────────────────┐")
    print("  │ Spend type          │ Witness   │ Scripts revealed │")
    print("  ├─────────────────────┼───────────┼──────────────────┤")
    print("  │ Key-path            │  64 bytes │       0          │")
    print(f"  │ Script-path (leaf)  │ ~{script_witness:3d} bytes│       1          │")
    print("  │ P2SH (old style)    │ variable  │  ALL of them     │")
    print("  └─────────────────────┴───────────┴──────────────────┘")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
