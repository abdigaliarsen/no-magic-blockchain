"""
TITLE: ECDSA Digital Signatures
CATEGORY: core

WHAT THIS IMPLEMENTS:
    Elliptic Curve Digital Signature Algorithm (ECDSA) built entirely from scratch
    using secp256k1 curve parameters. Implements signing (hash, random k, compute r & s)
    and verification (recover point from u1/u2, check r matches) with no external deps.

KEY CONCEPTS:
    - ECDSA signing: r = (k*G).x mod n, s = k_inv * (hash + r*privkey) mod n
    - ECDSA verification: compute u1 = hash * s_inv, u2 = r * s_inv, check (u1*G + u2*PubKey).x == r
    - Modular inverse via Fermat's little theorem (a^(p-2) mod p)
    - Message hashing with SHA-256 before signing (never sign raw data)

PREREQUISITE SCRIPTS:
    - core/02_public_key_crypto.py

REAL-WORLD RELEVANCE:
    Every Bitcoin and Ethereum transaction is authorized by an ECDSA signature.
    When you "sign a transaction" in a wallet, this exact math runs under the hood.
"""

import hashlib
import secrets

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# secp256k1 curve parameters — the same curve Bitcoin and Ethereum use
# Curve equation: y^2 = x^3 + 7 (mod p)
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F  # prime field
A = 0   # curve coefficient a (secp256k1 has a=0)
B = 7   # curve coefficient b (secp256k1 has b=7)
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141  # group order
# Generator point G — the "starting point" everyone agrees on
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (GX, GY)

# Point at infinity — the "zero" element for elliptic curve addition
INFINITY = None

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: Modular arithmetic helpers
# ----------------------------------------------------------------------------

def mod_inv(a, m):
    """Compute modular inverse using Fermat's little theorem: a^(m-2) mod m.
    Works because m is prime, so a^(m-1) = 1 mod m, thus a^(m-2) = a^(-1) mod m."""
    return pow(a, m - 2, m)

# ----------------------------------------------------------------------------
# 2b: Elliptic curve point arithmetic (self-contained, no imports from 02)
# ----------------------------------------------------------------------------

def point_add(p1, p2):
    """Add two points on the secp256k1 curve. Returns the sum point."""
    if p1 is INFINITY:
        return p2  # adding infinity is identity
    if p2 is INFINITY:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and y1 != y2:
        return INFINITY  # point + its inverse = infinity (vertical line)

    if x1 == x2 and y1 == y2:
        # Point doubling — tangent line slope: (3*x1^2 + a) / (2*y1)
        lam = (3 * x1 * x1 + A) * mod_inv(2 * y1, P) % P
    else:
        # Point addition — secant line slope: (y2 - y1) / (x2 - x1)
        lam = (y2 - y1) * mod_inv(x2 - x1, P) % P

    # New point from the slope
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def scalar_mult(k, point):
    """Multiply a point by scalar k using double-and-add (binary method).
    This is the core operation — fast even for 256-bit scalars."""
    result = INFINITY  # start with identity
    addend = point      # current power of 2 times the point

    while k > 0:
        if k & 1:  # if lowest bit is set, add current power
            result = point_add(result, addend)
        addend = point_add(addend, addend)  # double for next bit
        k >>= 1  # shift to next bit
    return result

# ----------------------------------------------------------------------------
# 2c: Key generation
# ----------------------------------------------------------------------------

def generate_keypair():
    """Generate a private/public key pair on secp256k1.
    Private key is a random integer in [1, n-1]. Public key is privkey * G."""
    privkey = secrets.randbelow(N - 1) + 1  # random in [1, n-1]
    pubkey = scalar_mult(privkey, G)          # public key = privkey * generator
    return privkey, pubkey

# ----------------------------------------------------------------------------
# 2d: Message hashing
# ----------------------------------------------------------------------------

def hash_message(message):
    """Hash a message with SHA-256 and return the digest as an integer.
    We sign the hash, never the raw message — this ensures fixed-length input."""
    digest = hashlib.sha256(message.encode("utf-8")).digest()
    return int.from_bytes(digest, "big")  # convert 32 bytes to integer

# ----------------------------------------------------------------------------
# 2e: ECDSA signing
# ----------------------------------------------------------------------------

def ecdsa_sign(privkey, message):
    """Sign a message using ECDSA.

    Steps:
        1. Hash the message to get z
        2. Pick random k (the "nonce" — MUST be unique per signature)
        3. Compute r = (k * G).x mod n
        4. Compute s = k^(-1) * (z + r * privkey) mod n
        5. Return (r, s)

    WARNING: Reusing k with the same key leaks the private key!
    This is how the PS3 was hacked — Sony reused k."""
    z = hash_message(message)  # step 1: hash

    while True:
        k = secrets.randbelow(N - 1) + 1  # step 2: random nonce in [1, n-1]
        point = scalar_mult(k, G)           # step 3a: compute k * G
        r = point[0] % N                    # step 3b: r is the x-coordinate mod n

        if r == 0:  # extremely unlikely, but r=0 would break the math
            continue

        k_inv = mod_inv(k, N)               # need k^(-1) for step 4
        s = (k_inv * (z + r * privkey)) % N  # step 4: the signature equation

        if s == 0:  # also extremely unlikely
            continue

        return (r, s)

# ----------------------------------------------------------------------------
# 2f: ECDSA verification
# ----------------------------------------------------------------------------

def ecdsa_verify(pubkey, message, signature):
    """Verify an ECDSA signature.

    Steps:
        1. Hash the message to get z
        2. Compute s_inv = s^(-1) mod n
        3. Compute u1 = z * s_inv mod n
        4. Compute u2 = r * s_inv mod n
        5. Compute point = u1*G + u2*PubKey
        6. Signature is valid if point.x mod n == r

    The math works because:
        u1*G + u2*PubKey = u1*G + u2*privkey*G = (u1 + u2*privkey)*G
        = (z*s_inv + r*s_inv*privkey)*G = s_inv*(z + r*privkey)*G
        = (k*s/s)*(1/s_inv_cancelled)... = k*G
        So we recover the same point the signer computed!"""
    r, s = signature

    # Basic validity checks
    if not (1 <= r < N and 1 <= s < N):
        return False  # r and s must be in [1, n-1]

    z = hash_message(message)       # step 1: same hash the signer used
    s_inv = mod_inv(s, N)           # step 2: modular inverse of s
    u1 = (z * s_inv) % N            # step 3: weight for generator point
    u2 = (r * s_inv) % N            # step 4: weight for public key point

    # step 5: recover the point — this is the expensive part
    point1 = scalar_mult(u1, G)         # u1 * G
    point2 = scalar_mult(u2, pubkey)    # u2 * PubKey
    point = point_add(point1, point2)   # sum them

    if point is INFINITY:
        return False  # degenerate case

    # step 6: check if x-coordinate matches r
    return point[0] % N == r

# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of ECDSA signing and verification."""
    print("=" * 60)
    print("       ECDSA Digital Signatures (secp256k1)")
    print("=" * 60)

    # --- Key generation ---
    print("\n--- Step 1: Generate Key Pair ---\n")
    privkey, pubkey = generate_keypair()
    print(f"  Private key : 0x{privkey:064x}")
    print(f"  Public key x: 0x{pubkey[0]:064x}")
    print(f"  Public key y: 0x{pubkey[1]:064x}")

    # --- Sign a message ---
    print("\n--- Step 2: Sign a Message ---\n")
    message = "Transfer 5 BTC to Alice"
    print(f'  Message: "{message}"')

    z = hash_message(message)
    print(f"  SHA-256 hash (z): 0x{z:064x}")

    signature = ecdsa_sign(privkey, message)
    r, s = signature
    print(f"\n  Signature:")
    print(f"    r: 0x{r:064x}")
    print(f"    s: 0x{s:064x}")

    # --- Verify the signature ---
    print("\n--- Step 3: Verify Signature ---\n")
    valid = ecdsa_verify(pubkey, message, signature)
    status = "VALID \u2713" if valid else "INVALID \u2717"
    print(f'  Message:      "{message}"')
    print(f"  Verification: {status}")

    # --- Tamper with the message ---
    print("\n--- Step 4: Tamper Detection ---\n")
    tampered = "Transfer 50 BTC to Alice"
    print(f'  Tampered message: "{tampered}"')
    print(f"  (changed 5 -> 50, a single character difference)\n")

    z_tampered = hash_message(tampered)
    print(f"  Original hash:  0x{z:064x}")
    print(f"  Tampered hash:  0x{z_tampered:064x}")

    # Count how many hex digits differ — shows avalanche effect
    orig_hex = f"{z:064x}"
    tamp_hex = f"{z_tampered:064x}"
    diff_count = sum(1 for a, b in zip(orig_hex, tamp_hex) if a != b)
    print(f"  Hex digits changed: {diff_count}/64 (~{diff_count*100//64}%)")

    valid_tampered = ecdsa_verify(pubkey, tampered, signature)
    status_tampered = "VALID \u2713" if valid_tampered else "INVALID \u2717"
    print(f"\n  Verification: {status_tampered}")

    # --- Wrong key detection ---
    print("\n--- Step 5: Wrong Key Detection ---\n")
    _, wrong_pubkey = generate_keypair()  # different keypair
    print(f"  Using a different public key to verify...")
    valid_wrong = ecdsa_verify(wrong_pubkey, message, signature)
    status_wrong = "VALID \u2713" if valid_wrong else "INVALID \u2717"
    print(f"  Verification: {status_wrong}")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Original message + correct key:   VALID \u2713")
    print(f"  Tampered message + correct key:    INVALID \u2717")
    print(f"  Original message + wrong key:      INVALID \u2717")
    print("\n  ECDSA ensures both message integrity AND sender identity.")
    print("=" * 60)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
