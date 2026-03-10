"""
TITLE: Schnorr Signatures (BIP 340)
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    Schnorr signature scheme over secp256k1 following BIP 340 conventions (x-only
    public keys, tagged hashes). Also implements a simplified MuSig key aggregation
    protocol where multiple signers cooperate to produce a single compact signature.

KEY CONCEPTS:
    - Schnorr sign/verify: s = k + e*d (linear, enabling aggregation)
    - BIP 340 x-only public keys: 32 bytes instead of 33 (always even Y)
    - Tagged hashes: domain separation via SHA-256(tag || tag || msg)
    - MuSig: aggregate N public keys into one, produce one combined signature

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - core/02_public_key_crypto.py (elliptic curve math)
    - core/03_digital_signatures.py (ECDSA for comparison)

REAL-WORLD RELEVANCE:
    Schnorr signatures were activated on Bitcoin with Taproot (November 2021).
    They are more efficient than ECDSA (64-byte sigs, batch verification), and
    their linearity enables MuSig multisig that looks like a single-key spend
    on-chain, improving privacy and reducing fees.
"""

import hashlib  # For SHA-256 hashing
import os       # For cryptographic random number generation
import time     # For timing demonstrations

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# secp256k1 curve parameters — the same curve used by Bitcoin
# y^2 = x^3 + 7 (mod P)
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F  # Field prime
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141  # Group order
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (GX, GY)  # Generator point

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Finite field and elliptic curve arithmetic ---

def mod_inverse(a, m):
    """Compute modular inverse using extended Euclidean algorithm."""
    if a < 0:
        a = a % m
    g, x, _ = _ext_gcd(a, m)
    if g != 1:
        raise ValueError("No modular inverse exists")
    return x % m


def _ext_gcd(a, b):
    """Extended GCD: returns (gcd, x, y) where ax + by = gcd."""
    if a == 0:
        return b, 0, 1
    g, x1, y1 = _ext_gcd(b % a, a)
    return g, y1 - (b // a) * x1, x1


def point_add(p1, p2):
    """Add two points on secp256k1 (or return None for point at infinity)."""
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and y1 != y2:
        return None  # Point + its inverse = infinity
    if x1 == x2:
        # Point doubling: tangent slope = 3x^2 / 2y
        lam = (3 * x1 * x1 * mod_inverse(2 * y1, P)) % P
    else:
        # Point addition: slope = (y2 - y1) / (x2 - x1)
        lam = ((y2 - y1) * mod_inverse(x2 - x1, P)) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def scalar_mult(k, point):
    """Multiply a curve point by scalar k using double-and-add."""
    result = None  # Start at point at infinity (identity)
    addend = point
    k = k % N  # Reduce modulo group order
    while k > 0:
        if k & 1:  # If current bit is set, add
            result = point_add(result, addend)
        addend = point_add(addend, addend)  # Double
        k >>= 1
    return result


def has_even_y(point):
    """Check if point has even Y coordinate (BIP 340 convention)."""
    return point[1] % 2 == 0


def x_only(point):
    """Extract x-only public key (32 bytes) — BIP 340 uses only the X coordinate."""
    return point[0].to_bytes(32, "big")


def lift_x(x_bytes):
    """Recover full point from x-only key, choosing even Y (BIP 340 rule)."""
    x = int.from_bytes(x_bytes, "big")
    if x >= P:
        return None
    # Compute y^2 = x^3 + 7 (mod P)
    y_sq = (pow(x, 3, P) + 7) % P
    # Compute square root via Tonelli-Shanks (P % 4 == 3 for secp256k1)
    y = pow(y_sq, (P + 1) // 4, P)
    if pow(y, 2, P) != y_sq:
        return None  # No valid point at this x
    # BIP 340: always pick the even Y
    if y % 2 != 0:
        y = P - y
    return (x, y)


# --- BIP 340 tagged hashes ---

def tagged_hash(tag, data):
    """
    SHA-256 with domain separation: H(SHA256(tag) || SHA256(tag) || data).
    This prevents cross-protocol attacks where a hash from one context
    could be replayed in another.
    """
    tag_hash = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()


# --- Schnorr signature (BIP 340) ---

def schnorr_sign(secret_key, message):
    """
    Sign a 32-byte message with a secret key following BIP 340.
    Returns a 64-byte signature (R_x || s).
    """
    d = int.from_bytes(secret_key, "big")
    if d == 0 or d >= N:
        raise ValueError("Invalid secret key")

    # Compute public key point
    pub_point = scalar_mult(d, G)

    # BIP 340: if P has odd Y, negate the secret key so it corresponds to even Y
    if not has_even_y(pub_point):
        d = N - d

    # Deterministic nonce: k = tagged_hash("BIP0340/aux", aux_rand) XOR d, then hash
    # Simplified: we use random aux data for nonce generation
    aux = os.urandom(32)
    t = bytes(a ^ b for a, b in zip(d.to_bytes(32, "big"), tagged_hash("BIP0340/aux", aux)))
    k_hash = tagged_hash("BIP0340/nonce", t + x_only(pub_point) + message)
    k = int.from_bytes(k_hash, "big") % N
    if k == 0:
        raise ValueError("Nonce is zero — astronomically unlikely")

    # R = k * G
    R = scalar_mult(k, G)

    # BIP 340: if R has odd Y, negate k so R has even Y
    if not has_even_y(R):
        k = N - k
        R = scalar_mult(k, G)

    # Challenge: e = tagged_hash("BIP0340/challenge", R_x || P_x || message)
    e_hash = tagged_hash("BIP0340/challenge", x_only(R) + x_only(pub_point) + message)
    e = int.from_bytes(e_hash, "big") % N

    # Signature: s = (k + e * d) mod N
    s = (k + e * d) % N

    # Return 64-byte signature: R_x (32 bytes) || s (32 bytes)
    sig = x_only(R) + s.to_bytes(32, "big")
    return sig


def schnorr_verify(pubkey_bytes, message, signature):
    """
    Verify a BIP 340 Schnorr signature.
    pubkey_bytes: 32-byte x-only public key
    message: 32-byte message
    signature: 64-byte (R_x || s)
    Returns True if valid.
    """
    if len(signature) != 64:
        return False

    # Parse signature
    R_x_bytes = signature[:32]
    s = int.from_bytes(signature[32:], "big")
    if s >= N:
        return False

    # Lift public key from x-only representation
    pub_point = lift_x(pubkey_bytes)
    if pub_point is None:
        return False

    # Recompute challenge
    e_hash = tagged_hash("BIP0340/challenge", R_x_bytes + pubkey_bytes + message)
    e = int.from_bytes(e_hash, "big") % N

    # Verify: s*G == R + e*P
    # Rearranged: R = s*G - e*P
    sG = scalar_mult(s, G)
    eP = scalar_mult(e, pub_point)
    neg_eP = (eP[0], P - eP[1])  # Negate Y to subtract
    R_computed = point_add(sG, neg_eP)

    if R_computed is None:
        return False
    if not has_even_y(R_computed):
        return False  # BIP 340: R must have even Y
    if R_computed[0].to_bytes(32, "big") != R_x_bytes:
        return False  # R_x must match

    return True


# --- MuSig (simplified 2-round key aggregation) ---

def musig_aggregate_pubkeys(pubkeys):
    """
    Aggregate multiple x-only public keys into one combined key.
    Uses a simple commitment scheme: each key is weighted by
    H(L || P_i) where L is the hash of all keys concatenated.
    This prevents rogue-key attacks.
    """
    # L = hash of all public keys concatenated (binds the key set)
    L = tagged_hash("MuSig/keylist", b"".join(pubkeys))

    agg_point = None
    coefficients = []
    for pk in pubkeys:
        # Each signer gets a coefficient based on L and their key
        coeff_hash = tagged_hash("MuSig/coeff", L + pk)
        coeff = int.from_bytes(coeff_hash, "big") % N
        coefficients.append(coeff)

        # Weighted public key: coeff * P_i
        point = lift_x(pk)
        weighted = scalar_mult(coeff, point)
        agg_point = point_add(agg_point, weighted)

    return agg_point, coefficients


def musig_sign(secret_keys, message):
    """
    Simplified MuSig signing: all signers cooperate to produce one signature.
    In practice this is interactive (multiple rounds), but we simulate it
    with all keys available locally.
    Returns (aggregate_pubkey_x, 64-byte signature).
    """
    n = len(secret_keys)

    # Compute individual public keys (x-only)
    pub_points = []
    pubkeys = []
    for sk in secret_keys:
        d = int.from_bytes(sk, "big")
        pp = scalar_mult(d, G)
        pub_points.append(pp)
        pubkeys.append(x_only(pp))

    # Aggregate public keys
    agg_point, coefficients = musig_aggregate_pubkeys(pubkeys)

    # Ensure aggregate key has even Y
    negate_agg = not has_even_y(agg_point)
    if negate_agg:
        agg_point = (agg_point[0], P - agg_point[1])

    agg_pubkey = x_only(agg_point)

    # Each signer generates a nonce
    nonces = []
    nonce_points = []
    for i in range(n):
        k_hash = tagged_hash("MuSig/nonce",
                              secret_keys[i] + message + os.urandom(32))
        k = int.from_bytes(k_hash, "big") % N
        if k == 0:
            k = 1
        R_i = scalar_mult(k, G)
        nonces.append(k)
        nonce_points.append(R_i)

    # Aggregate nonce: R = sum of all R_i
    R_agg = None
    for rp in nonce_points:
        R_agg = point_add(R_agg, rp)

    # If R has odd Y, negate all nonces
    negate_R = not has_even_y(R_agg)
    if negate_R:
        nonces = [(N - k) for k in nonces]
        R_agg = (R_agg[0], P - R_agg[1])

    # Challenge
    e_hash = tagged_hash("BIP0340/challenge", x_only(R_agg) + agg_pubkey + message)
    e = int.from_bytes(e_hash, "big") % N

    # Each signer computes partial signature
    s_total = 0
    for i in range(n):
        d = int.from_bytes(secret_keys[i], "big")
        # Negate d if individual pubkey had odd Y (BIP 340)
        if not has_even_y(pub_points[i]):
            d = N - d
        # Negate d if aggregate was negated
        if negate_agg:
            d = N - d
        s_i = (nonces[i] + e * coefficients[i] * d) % N
        s_total = (s_total + s_i) % N

    sig = x_only(R_agg) + s_total.to_bytes(32, "big")
    return agg_pubkey, sig


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Schnorr signatures and MuSig."""

    print("=" * 70)
    print("        SCHNORR SIGNATURES (BIP 340) & MuSig")
    print("=" * 70)

    # --- Part 1: Single signer Schnorr ---
    print("\n--- Part 1: Single-Signer Schnorr Signature ---\n")

    # Generate a keypair
    secret_key = os.urandom(32)
    d = int.from_bytes(secret_key, "big") % N
    if d == 0:
        d = 1
    secret_key = d.to_bytes(32, "big")
    pub_point = scalar_mult(d, G)
    pubkey = x_only(pub_point)

    print(f"  Secret key (d):  {secret_key.hex()[:32]}...")
    print(f"  Public key (x):  {pubkey.hex()[:32]}...")
    print(f"  Key size:        32 bytes (x-only, vs 33 bytes compressed ECDSA)")

    # Sign a message
    message = hashlib.sha256(b"Hello, Schnorr!").digest()
    print(f"\n  Message hash:    {message.hex()[:32]}...")

    t0 = time.time()
    signature = schnorr_sign(secret_key, message)
    sign_time = time.time() - t0

    print(f"\n  Signature (64 bytes):")
    print(f"    R_x: {signature[:32].hex()[:32]}...")
    print(f"    s:   {signature[32:].hex()[:32]}...")
    print(f"    Time: {sign_time*1000:.1f} ms")

    # Verify
    t0 = time.time()
    valid = schnorr_verify(pubkey, message, signature)
    verify_time = time.time() - t0

    print(f"\n  Verification: {'PASS' if valid else 'FAIL'}  ({verify_time*1000:.1f} ms)")

    # Tamper with message
    tampered = hashlib.sha256(b"Hello, Schnorr?").digest()
    valid_tampered = schnorr_verify(pubkey, tampered, signature)
    print(f"  Tampered msg:  {'PASS' if valid_tampered else 'FAIL (expected)'}  ")

    # --- Comparison table ---
    print("\n  ┌──────────────────┬───────────────┬───────────────┐")
    print("  │                  │    ECDSA      │   Schnorr     │")
    print("  ├──────────────────┼───────────────┼───────────────┤")
    print("  │ Signature size   │   ~72 bytes   │   64 bytes    │")
    print("  │ Public key       │   33 bytes    │   32 bytes    │")
    print("  │ Batch verify     │      No       │     Yes       │")
    print("  │ Key aggregation  │   Complex     │   Natural     │")
    print("  │ Malleability     │     Yes       │      No       │")
    print("  └──────────────────┴───────────────┴───────────────┘")

    # --- Part 2: MuSig (3-of-3) ---
    print("\n--- Part 2: MuSig 3-of-3 Multisig ---\n")

    signers = ["Alice", "Bob", "Carol"]
    secret_keys = []
    pub_points = []
    pubkeys = []

    for name in signers:
        sk_int = int.from_bytes(os.urandom(32), "big") % N
        if sk_int == 0:
            sk_int = 1
        sk = sk_int.to_bytes(32, "big")
        pp = scalar_mult(sk_int, G)
        pk = x_only(pp)
        secret_keys.append(sk)
        pub_points.append(pp)
        pubkeys.append(pk)
        print(f"  {name:>5}: pubkey = {pk.hex()[:24]}...")

    # Aggregate
    agg_point, _ = musig_aggregate_pubkeys(pubkeys)
    agg_pk = x_only(agg_point) if has_even_y(agg_point) else x_only((agg_point[0], P - agg_point[1]))
    print(f"\n  Aggregated key:  {agg_pk.hex()[:24]}...")
    print(f"  (Looks like a single public key on-chain!)")

    # Sign
    message = hashlib.sha256(b"Pay 1 BTC to Dave").digest()
    print(f"\n  Message: \"Pay 1 BTC to Dave\"")

    t0 = time.time()
    agg_pubkey_result, musig_sig = musig_sign(secret_keys, message)
    musig_time = time.time() - t0

    print(f"  MuSig signature: {musig_sig.hex()[:32]}...")
    print(f"  Time: {musig_time*1000:.1f} ms")

    # Verify with standard Schnorr verifier — this is the beauty of MuSig!
    valid_musig = schnorr_verify(agg_pubkey_result, message, musig_sig)
    print(f"\n  Verified with standard Schnorr verifier: {'PASS' if valid_musig else 'FAIL'}")

    # --- Part 3: Bandwidth savings ---
    print("\n--- Part 3: Bandwidth Savings ---\n")

    n_signers = 3
    ecdsa_size = n_signers * 72 + n_signers * 33  # N sigs + N pubkeys
    schnorr_musig_size = 64 + 32                   # 1 sig + 1 pubkey

    print(f"  3-of-3 multisig on-chain footprint:")
    print(f"  ┌─────────────────────┬──────────────────┐")
    print(f"  │ Method              │ Witness data     │")
    print(f"  ├─────────────────────┼──────────────────┤")
    print(f"  │ ECDSA (OP_MULTISIG) │ {ecdsa_size:>5} bytes      │")
    print(f"  │ Schnorr + MuSig     │ {schnorr_musig_size:>5} bytes      │")
    print(f"  │ Savings             │ {(1 - schnorr_musig_size/ecdsa_size)*100:>5.1f}%         │")
    print(f"  └─────────────────────┴──────────────────┘")
    print(f"\n  MuSig is indistinguishable from a single-key spend,")
    print(f"  improving both privacy and efficiency.\n")


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
