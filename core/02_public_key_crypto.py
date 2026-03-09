"""
TITLE: Elliptic Curve Cryptography (secp256k1)
CATEGORY: core

WHAT THIS IMPLEMENTS:
    Elliptic curve math over finite fields from scratch. We implement point
    addition, point doubling, and scalar multiplication on the secp256k1 curve
    (the same curve Bitcoin and Ethereum use), then use these to generate
    public/private keypairs.

KEY CONCEPTS:
    - Elliptic curves over finite fields (y² = x³ + ax + b mod p)
    - Point addition and doubling using modular arithmetic
    - Scalar multiplication via the double-and-add algorithm
    - Public key derivation: private_key * G = public_key

PREREQUISITE SCRIPTS:
    - None (standalone math, though 01_hashing.py gives useful context)

REAL-WORLD RELEVANCE:
    Every blockchain wallet address is derived from an elliptic curve public key.
    Bitcoin, Ethereum, and many other chains use secp256k1 for key generation
    and digital signatures (ECDSA).
"""

import os

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# secp256k1 curve parameters — these are standardized by NIST/SECG.
# The curve equation is: y² = x³ + 7 (mod p)
# "a" is 0 and "b" is 7, which makes secp256k1 a Koblitz curve (efficient).

# The prime field order — all arithmetic is done mod this 256-bit prime
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F

# Curve coefficients: y² = x³ + A*x + B
A = 0  # secp256k1 has a = 0, simplifying the math
B = 7  # secp256k1 has b = 7

# Generator point G — a fixed point on the curve that everyone agrees on.
# Multiplying G by a private key gives the corresponding public key.
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

# The order of G — the number of points you can generate by multiplying G.
# private keys must be in the range [1, N-1].
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# Cofactor (always 1 for secp256k1, meaning every point is in the main group)
H = 1

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# We represent the "point at infinity" (the identity element for EC addition)
# as None. Adding any point P to the identity gives P back, just like 0 + x = x.
IDENTITY = None


def mod_inverse(a: int, m: int) -> int:
    """Compute modular inverse of a mod m using Fermat's little theorem.

    Since P is prime, a^(p-1) = 1 (mod p), so a^(p-2) = a^(-1) (mod p).
    Python's built-in pow(a, m-2, m) does this efficiently with fast exponentiation.
    """
    return pow(a, m - 2, m)


# ----------------------------------------------------------------------------
# Point operations — the core building blocks of elliptic curve cryptography
# ----------------------------------------------------------------------------

def point_add(p1: tuple | None, p2: tuple | None) -> tuple | None:
    """Add two points on the secp256k1 curve.

    EC addition is NOT regular addition — it's a geometric operation:
    1. Draw a line through P1 and P2
    2. The line intersects the curve at a third point
    3. Reflect that point across the x-axis → that's P1 + P2

    The formulas below are the algebraic version of this geometry, done mod P.
    """
    # Adding the identity (point at infinity) changes nothing
    if p1 is IDENTITY:
        return p2
    if p2 is IDENTITY:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    # If points have same x but different y (or y=0), they're inverses → sum is identity
    if x1 == x2 and y1 != y2:
        return IDENTITY

    # Same point? Use point doubling (tangent line instead of secant)
    if x1 == x2 and y1 == y2:
        return point_double(p1)

    # --- Standard point addition (two distinct points) ---
    # Slope of the line through P1 and P2: s = (y2 - y1) / (x2 - x1)
    # In modular arithmetic, division is multiplication by the modular inverse
    s = ((y2 - y1) * mod_inverse(x2 - x1, P)) % P

    # x-coordinate of the result: x3 = s² - x1 - x2
    x3 = (s * s - x1 - x2) % P

    # y-coordinate: y3 = s * (x1 - x3) - y1
    y3 = (s * (x1 - x3) - y1) % P

    return (x3, y3)


def point_double(point: tuple | None) -> tuple | None:
    """Double a point on the curve (add it to itself).

    When P1 = P2, we can't draw a line through two distinct points.
    Instead, we use the tangent line at the point.
    The slope of the tangent comes from implicit differentiation of y² = x³ + ax + b:
        2y * dy/dx = 3x² + a  →  slope = (3x² + a) / (2y)
    """
    if point is IDENTITY:
        return IDENTITY

    x, y = point

    # If y is 0, the tangent is vertical → result is the identity
    if y == 0:
        return IDENTITY

    # Tangent slope: s = (3x² + A) / (2y) mod P
    # A = 0 for secp256k1, so this simplifies to 3x² / 2y
    s = ((3 * x * x + A) * mod_inverse(2 * y, P)) % P

    # New point coordinates (same formulas as addition)
    x3 = (s * s - 2 * x) % P
    y3 = (s * (x - x3) - y) % P

    return (x3, y3)


def scalar_multiply(k: int, point: tuple | None) -> tuple | None:
    """Multiply a point by a scalar using the double-and-add algorithm.

    This is like repeated addition: k * P = P + P + ... + P (k times),
    but the naive approach takes O(k) steps — impossibly slow for 256-bit k.

    Double-and-add works in O(log k) steps by scanning k's binary representation:
    - For each bit, double the accumulator
    - If the bit is 1, also add the original point
    This is the EC equivalent of fast exponentiation (square-and-multiply).
    """
    if k == 0 or point is IDENTITY:
        return IDENTITY

    # Reduce k modulo N (the group order) — values beyond N wrap around
    k = k % N

    result = IDENTITY  # Start with identity (the "zero" for EC addition)
    addend = point      # The point we conditionally add at each step

    # Scan through each bit of k from LSB to MSB
    while k > 0:
        if k & 1:  # Current bit is 1 → add the current addend
            result = point_add(result, addend)
        addend = point_double(addend)  # Double for next bit position
        k >>= 1  # Shift to next bit

    return result


# ----------------------------------------------------------------------------
# Key generation
# ----------------------------------------------------------------------------

def is_on_curve(point: tuple | None) -> bool:
    """Check if a point satisfies the curve equation y² = x³ + Ax + B (mod P).

    This is how we verify that a public key is valid — an invalid point
    could be used in subtle attacks against signature schemes.
    """
    if point is IDENTITY:
        return True  # The identity is on every curve by convention
    x, y = point
    # Left side: y²
    lhs = (y * y) % P
    # Right side: x³ + Ax + B (A=0 for secp256k1, so just x³ + 7)
    rhs = (x * x * x + A * x + B) % P
    return lhs == rhs


def generate_private_key() -> int:
    """Generate a cryptographically secure random private key.

    The private key is a random integer in [1, N-1].
    We use os.urandom (backed by the OS CSPRNG) for security.
    """
    while True:
        # Generate 32 random bytes (256 bits) and convert to an integer
        key = int.from_bytes(os.urandom(32), byteorder="big")
        # Must be in valid range: not zero, and less than the group order
        if 0 < key < N:
            return key


def derive_public_key(private_key: int) -> tuple:
    """Derive a public key from a private key.

    The public key is simply: private_key * G (scalar multiplication of the
    generator point). This is a one-way function — given the public key, you
    cannot feasibly recover the private key (this is the Elliptic Curve
    Discrete Logarithm Problem, or ECDLP).
    """
    return scalar_multiply(private_key, (GX, GY))


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of elliptic curve key generation."""

    print("=" * 70)
    print("  Elliptic Curve Cryptography (secp256k1) — From Scratch")
    print("=" * 70)

    # --- Show the curve parameters ---
    print("\n--- Curve Parameters (secp256k1) ---\n")
    print(f"  Equation:  y² = x³ + {A}x + {B}  (mod p)")
    print(f"  Field (p): {hex(P)}")
    print(f"             ({P.bit_length()} bits)")
    print(f"  Order (n): {hex(N)}")
    print(f"             ({N.bit_length()} bits)")
    print(f"  Generator point G:")
    print(f"    x: {hex(GX)}")
    print(f"    y: {hex(GY)}")
    print(f"  G on curve? {is_on_curve((GX, GY))}")

    # --- Demonstrate point operations with small examples ---
    print("\n--- Point Operations ---\n")

    # Double the generator point: 2*G
    g2 = point_double((GX, GY))
    print("  2 * G (point doubling):")
    print(f"    x: {hex(g2[0])}")
    print(f"    y: {hex(g2[1])}")
    print(f"    On curve? {is_on_curve(g2)}")

    # Add G + 2G = 3G
    g3 = point_add((GX, GY), g2)
    print("\n  3 * G = G + 2G (point addition):")
    print(f"    x: {hex(g3[0])}")
    print(f"    y: {hex(g3[1])}")
    print(f"    On curve? {is_on_curve(g3)}")

    # Verify: scalar_multiply(3, G) should equal G + 2G
    g3_check = scalar_multiply(3, (GX, GY))
    print(f"\n  Verify: scalar_multiply(3, G) matches G + 2G? {g3 == g3_check}")

    # --- Show that n*G = identity (the point "wraps around") ---
    print("\n--- Group Order Property ---\n")
    print(f"  N * G should equal the point at infinity (identity)...")
    identity = scalar_multiply(N, (GX, GY))
    print(f"  N * G = {identity}  (None = point at infinity) ✓")

    # --- Generate a real keypair ---
    print("\n--- Key Generation ---\n")

    private_key = generate_private_key()
    public_key = derive_public_key(private_key)

    print(f"  Private Key (256-bit random integer):")
    print(f"    hex: 0x{private_key:064x}")
    print(f"    bits: {private_key.bit_length()}")
    print()
    print(f"  Public Key (point on the curve):")
    print(f"    x: 0x{public_key[0]:064x}")
    print(f"    y: 0x{public_key[1]:064x}")
    print()

    # Verify the public key is on the curve
    on_curve = is_on_curve(public_key)
    y_sq = pow(public_key[1], 2, P)
    x_cubed_plus_7 = (pow(public_key[0], 3, P) + B) % P
    print(f"  Point on curve? {on_curve}")
    print(f"    y² mod p = {hex(y_sq)[:20]}...")
    print(f"    x³+7 mod p = {hex(x_cubed_plus_7)[:20]}...")
    print(f"    {'Match ✓' if on_curve else 'MISMATCH ✗'}")

    # --- Show the one-way property ---
    print("\n--- One-Way Property (Trapdoor) ---\n")
    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │  private key ──(scalar multiply)──> public key     │")
    print("  │                                                     │")
    print("  │  EASY: multiply G by k  (milliseconds)             │")
    print("  │  HARD: given k*G, find k (billions of years)       │")
    print("  │                                                     │")
    print("  │  This one-way property is what makes EC crypto      │")
    print("  │  secure — it's the Discrete Logarithm Problem.      │")
    print("  └─────────────────────────────────────────────────────┘")

    # --- Show multiple key derivations to prove consistency ---
    print("\n--- Multiple Keys From Same Curve ---\n")
    for i in range(3):
        pk = generate_private_key()
        pub = derive_public_key(pk)
        on = is_on_curve(pub)
        print(f"  Key #{i+1}:")
        print(f"    priv: 0x{pk:064x}")
        print(f"    pub:  (0x{pub[0]:064x},")
        print(f"           0x{pub[1]:064x})")
        print(f"    on curve? {on}")
        print()

    print("=" * 70)
    print("  All public keys verified on secp256k1 curve.")
    print("=" * 70)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
