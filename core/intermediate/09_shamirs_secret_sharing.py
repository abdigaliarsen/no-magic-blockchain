"""
TITLE: Shamir's Secret Sharing
CATEGORY: core

WHAT THIS IMPLEMENTS:
    Shamir's Secret Sharing scheme over a finite field GF(p). A secret is split
    into n shares such that any k shares can reconstruct it, but k-1 shares
    reveal absolutely nothing. Uses polynomial evaluation for splitting and
    Lagrange interpolation for reconstruction.

KEY CONCEPTS:
    - Polynomial evaluation over finite fields GF(p)
    - Lagrange interpolation to recover a polynomial from k points
    - (k, n) threshold scheme: k-of-n shares needed to reconstruct
    - Information-theoretic security (fewer than k shares give zero information)

PREREQUISITE SCRIPTS:
    - core/fundamentals/01_hashing.py (context for why secrets matter)
    - core/fundamentals/02_public_key_crypto.py (modular arithmetic background)

REAL-WORLD RELEVANCE:
    Shamir's Secret Sharing is used in multi-sig wallet recovery, distributed
    key management (e.g., Hashicorp Vault), and threshold signature schemes
    that underpin many blockchain validator networks.
"""

import os
import random

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# A large prime for our finite field. We use a 256-bit prime so the field
# can hold any 256-bit secret (like a private key). This is a safe prime
# commonly used in cryptographic protocols.
PRIME = (1 << 256) - (1 << 32) - 977
# This is actually the secp256k1 field prime: 2^256 - 2^32 - 977
# Any prime larger than our secret works, but this one is convenient.

# How many hex chars to show when displaying large numbers
DISPLAY_LEN = 16

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================


def mod_inverse(a: int, p: int) -> int:
    """Compute modular inverse a^(-1) mod p using Fermat's little theorem.

    Since p is prime, a^(p-1) = 1 mod p, so a^(p-2) = a^(-1) mod p.
    """
    return pow(a, p - 2, p)


# ----------------------------------------------------------------------------
# Polynomial operations over GF(p)
# ----------------------------------------------------------------------------

def _make_polynomial(secret: int, degree: int) -> list[int]:
    """Create a random polynomial of given degree with secret as constant term.

    The polynomial is: f(x) = secret + a1*x + a2*x^2 + ... + a_{k-1}*x^{k-1}
    where a1..a_{k-1} are random coefficients in [1, PRIME-1].

    The secret is f(0) — this is the key insight of Shamir's scheme.
    """
    # Constant term is the secret itself
    coefficients = [secret]
    for _ in range(degree):
        # Each coefficient is a random element of GF(p), excluding zero
        # to ensure the polynomial is truly of the stated degree
        coeff = random.SystemRandom().randint(1, PRIME - 1)
        coefficients.append(coeff)
    return coefficients


def _evaluate_polynomial(coefficients: list[int], x: int) -> int:
    """Evaluate polynomial at point x using Horner's method over GF(p).

    Horner's method: f(x) = c0 + x*(c1 + x*(c2 + ... + x*c_{n-1}))
    This is more efficient than computing each power of x separately.
    """
    # Start from the highest-degree coefficient and work down
    result = 0
    for coeff in reversed(coefficients):
        # Multiply accumulator by x, add next coefficient, reduce mod PRIME
        result = (result * x + coeff) % PRIME
    return result


# ----------------------------------------------------------------------------
# Split and reconstruct
# ----------------------------------------------------------------------------

def split_secret(secret: int, n: int, k: int) -> list[tuple[int, int]]:
    """Split a secret into n shares with threshold k.

    Args:
        secret: The integer secret to split (must be < PRIME)
        n: Total number of shares to generate
        k: Minimum shares needed to reconstruct

    Returns:
        List of (x, y) pairs where y = f(x) for the random polynomial f
        with f(0) = secret. Each x is a unique point in [1, n].
    """
    if k > n:
        raise ValueError("Threshold k cannot exceed total shares n")
    if secret >= PRIME:
        raise ValueError("Secret must be less than the field prime")

    # Build a random polynomial of degree k-1 (so k points determine it uniquely)
    polynomial = _make_polynomial(secret, degree=k - 1)

    # Evaluate at x = 1, 2, ..., n to create n shares
    # We never evaluate at x=0 because that would reveal the secret directly
    shares = []
    for i in range(1, n + 1):
        y = _evaluate_polynomial(polynomial, i)
        shares.append((i, y))

    return shares


def reconstruct_secret(shares: list[tuple[int, int]]) -> int:
    """Reconstruct the secret from k or more shares using Lagrange interpolation.

    Lagrange interpolation finds the unique polynomial of degree k-1 that
    passes through k given points, then evaluates it at x=0 to recover the secret.

    The Lagrange formula for f(0) is:
        f(0) = sum_{i} y_i * product_{j != i} (0 - x_j) / (x_i - x_j)

    All arithmetic is done mod PRIME to stay in the finite field.
    """
    k = len(shares)
    secret = 0

    for i in range(k):
        x_i, y_i = shares[i]

        # Compute the Lagrange basis polynomial L_i(0)
        # L_i(0) = product_{j != i} (0 - x_j) / (x_i - x_j)
        numerator = 1
        denominator = 1
        for j in range(k):
            if i == j:
                continue
            x_j = shares[j][0]
            # At x=0: numerator term is (0 - x_j) = -x_j
            numerator = (numerator * (-x_j)) % PRIME
            # Denominator term is (x_i - x_j)
            denominator = (denominator * (x_i - x_j)) % PRIME

        # Lagrange term: y_i * L_i(0) = y_i * numerator / denominator
        # Division in GF(p) is multiplication by modular inverse
        lagrange_term = (y_i * numerator * mod_inverse(denominator, PRIME)) % PRIME
        secret = (secret + lagrange_term) % PRIME

    return secret


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def _fmt(n: int) -> str:
    """Format a large integer for display, showing first/last hex chars."""
    h = f"{n:064x}"
    if len(h) > DISPLAY_LEN:
        return f"0x{h[:DISPLAY_LEN//2]}...{h[-DISPLAY_LEN//2:]}"
    return f"0x{h}"


def demo():
    """Run a visual demonstration of Shamir's Secret Sharing."""

    print("=" * 70)
    print("  Shamir's Secret Sharing — Threshold Cryptography")
    print("=" * 70)

    # --- Example 1: Basic 3-of-5 sharing ---
    print("\n--- Scenario: Split a Secret Key into 5 Shares (threshold = 3) ---\n")

    # Use a realistic secret: a 256-bit private key
    secret = int.from_bytes(os.urandom(32), "big") % PRIME
    n, k = 5, 3  # 5 total shares, any 3 can reconstruct

    print(f"  Original secret:  {_fmt(secret)}")
    print(f"  Scheme:           ({k}, {n}) — need {k} of {n} shares\n")

    # Split into shares
    shares = split_secret(secret, n, k)

    print("  Generated shares:")
    print("  " + "-" * 55)
    for i, (x, y) in enumerate(shares):
        label = f"Share #{i+1}"
        print(f"  {label:10s}  x={x}  y={_fmt(y)}")
    print("  " + "-" * 55)

    # --- Reconstruct with exactly k shares ---
    print(f"\n--- Reconstruction with exactly {k} shares ---\n")

    # Pick k random shares
    chosen = random.sample(shares, k)
    chosen_indices = [s[0] for s in chosen]
    print(f"  Using shares at x = {chosen_indices}")

    recovered = reconstruct_secret(chosen)
    match = recovered == secret

    print(f"  Recovered secret: {_fmt(recovered)}")
    print(f"  Original secret:  {_fmt(secret)}")
    print(f"  Match: {'YES' if match else 'NO'}")
    print()
    print("  " + ("+" * 50 if match else "!" * 50))
    msg = f"  Reconstruction successful with {k} shares!"
    print(f"  {msg:^50s}" if match
          else f"  {'  RECONSTRUCTION FAILED':^50s}")
    print("  " + ("+" * 50 if match else "!" * 50))

    # --- Show k-1 shares are insufficient ---
    print(f"\n--- Attempt with only {k-1} shares (should fail) ---\n")

    too_few = shares[:k - 1]
    wrong_result = reconstruct_secret(too_few)
    failed = wrong_result != secret

    print(f"  Using only {k-1} shares: x = {[s[0] for s in too_few]}")
    print(f"  Got:      {_fmt(wrong_result)}")
    print(f"  Expected: {_fmt(secret)}")
    print(f"  Match: {'YES (unexpected!)' if not failed else 'NO (correct — secret is safe)'}")

    # --- Show that ANY k shares work ---
    print(f"\n--- All possible {k}-share combinations ---\n")

    from itertools import combinations
    all_combos = list(combinations(shares, k))
    all_correct = True
    print(f"  Testing all {len(all_combos)} combinations of {k} shares from {n}:")
    print()
    for combo in all_combos:
        indices = [s[0] for s in combo]
        result = reconstruct_secret(list(combo))
        ok = result == secret
        if not ok:
            all_correct = False
        status = "OK" if ok else "FAIL"
        print(f"    Shares x={indices!s:15s} -> {status}")

    print()
    if all_correct:
        print(f"  All {len(all_combos)} combinations reconstruct correctly!")
    else:
        print("  ERROR: Some combinations failed!")

    # --- Diagram ---
    print("\n--- How It Works ---\n")
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  Secret S is the constant term of a random polynomial  │")
    print("  │  of degree k-1:                                        │")
    print("  │                                                        │")
    print("  │    f(x) = S + a1*x + a2*x^2 + ... + a_{k-1}*x^{k-1}  │")
    print("  │                                                        │")
    print("  │  Each share is a point (x_i, f(x_i)) on this curve.    │")
    print("  │  k points uniquely determine a degree-(k-1) polynomial │")
    print("  │  but k-1 points leave the constant term (S) completely │")
    print("  │  unconstrained — giving zero information about S.      │")
    print("  └─────────────────────────────────────────────────────────┘")

    # --- Show a simple visual with a small secret ---
    print("\n--- Visual: Small Example (secret=42, k=3, n=5) ---\n")
    small_shares = split_secret(42, 5, 3)
    small_recovered = reconstruct_secret(small_shares[:3])
    print(f"  Secret: 42")
    print(f"  Shares: {[(x, y % 1000) for x, y in small_shares]}  (y mod 1000 for display)")
    print(f"  Reconstructed from first 3 shares: {small_recovered}")

    print()
    print("=" * 70)
    print("  Shamir's Secret Sharing complete.")
    print("=" * 70)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
