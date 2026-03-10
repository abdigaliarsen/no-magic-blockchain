"""
TITLE: Reed-Solomon Erasure Coding
CATEGORY: core

WHAT THIS IMPLEMENTS:
    Reed-Solomon erasure coding over a prime field GF(p). Data is encoded as
    polynomial coefficients, evaluated at n points to produce n chunks. Any k
    chunks (out of n) are sufficient to reconstruct the original data using
    Lagrange interpolation. Lost chunks are recovered without any redundancy waste.

KEY CONCEPTS:
    - Polynomial evaluation over finite fields GF(p)
    - Lagrange interpolation for polynomial reconstruction
    - (k, n) erasure code: k data chunks encoded into n total, any k suffice
    - Non-systematic encoding: all chunks are polynomial evaluations (not raw data)

PREREQUISITE SCRIPTS:
    - core/intermediate/09_shamirs_secret_sharing.py (same polynomial math)
    - core/fundamentals/01_hashing.py (data integrity concepts)

REAL-WORLD RELEVANCE:
    Erasure coding is used in Solana's Turbine protocol (block propagation),
    Ethereum's Danksharding (data availability sampling), IPFS/Filecoin
    (distributed storage), and RAID-6 storage systems.
"""

import random

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Prime for our finite field — all arithmetic is modular.
# Using a smallish prime so demo values are human-readable.
# In production, this would be a 256-bit prime.
FIELD_PRIME = 257  # Smallest prime > 256 (so we can encode any byte value)

# Default encoding parameters
DEFAULT_K = 4  # Number of data chunks (minimum to reconstruct)
DEFAULT_N = 6  # Total chunks produced (n - k = 2 redundancy chunks)

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# Finite field arithmetic over GF(p)
# ----------------------------------------------------------------------------

def fp_add(a: int, b: int, p: int = FIELD_PRIME) -> int:
    """Add two field elements."""
    return (a + b) % p


def fp_sub(a: int, b: int, p: int = FIELD_PRIME) -> int:
    """Subtract two field elements."""
    return (a - b) % p


def fp_mul(a: int, b: int, p: int = FIELD_PRIME) -> int:
    """Multiply two field elements."""
    return (a * b) % p


def fp_inv(a: int, p: int = FIELD_PRIME) -> int:
    """Multiplicative inverse via Fermat's little theorem: a^(p-2) mod p."""
    if a == 0:
        raise ValueError("Cannot invert zero")
    return pow(a, p - 2, p)


def fp_div(a: int, b: int, p: int = FIELD_PRIME) -> int:
    """Divide a by b in GF(p): a * b^(-1) mod p."""
    return fp_mul(a, fp_inv(b, p), p)


# ----------------------------------------------------------------------------
# Polynomial operations over GF(p)
# ----------------------------------------------------------------------------

def poly_evaluate(coeffs: list[int], x: int, p: int = FIELD_PRIME) -> int:
    """Evaluate polynomial at point x using Horner's method.

    coeffs[i] is the coefficient of x^i.
    Horner's: f(x) = c0 + x*(c1 + x*(c2 + ... + x*c_{n-1}))
    This avoids computing powers of x separately.
    """
    result = 0
    for coeff in reversed(coeffs):
        result = (result * x + coeff) % p
    return result


def lagrange_interpolate(points: list[tuple[int, int]], x_target: int,
                          p: int = FIELD_PRIME) -> int:
    """Recover polynomial value at x_target from k points using Lagrange interpolation.

    Given k points (x_i, y_i) on a degree-(k-1) polynomial, this recovers
    the polynomial's value at any point. The formula is:
        f(x) = sum_i y_i * product_{j!=i} (x - x_j) / (x_i - x_j)
    """
    k = len(points)
    result = 0

    for i in range(k):
        x_i, y_i = points[i]

        # Compute Lagrange basis polynomial L_i(x_target)
        numerator = 1
        denominator = 1
        for j in range(k):
            if i == j:
                continue
            x_j = points[j][0]
            numerator = fp_mul(numerator, fp_sub(x_target, x_j, p), p)
            denominator = fp_mul(denominator, fp_sub(x_i, x_j, p), p)

        # L_i(x) = numerator / denominator
        basis = fp_div(numerator, denominator, p)
        # f(x) += y_i * L_i(x)
        result = fp_add(result, fp_mul(y_i, basis, p), p)

    return result


# ----------------------------------------------------------------------------
# Reed-Solomon encoding and decoding
# ----------------------------------------------------------------------------

def encode(data: list[int], n: int, k: int = None,
           p: int = FIELD_PRIME) -> list[tuple[int, int]]:
    """Encode k data values into n coded chunks using polynomial evaluation.

    The data values become coefficients of a degree-(k-1) polynomial:
        f(x) = data[0] + data[1]*x + data[2]*x^2 + ... + data[k-1]*x^{k-1}

    We evaluate f at n distinct points (1, 2, ..., n) to get n chunks.
    Any k of these chunks can reconstruct the polynomial (and thus the data).

    Args:
        data: List of k integers in [0, p-1]
        n: Total number of chunks to produce
        k: Number of data chunks (defaults to len(data))
        p: Field prime

    Returns:
        List of (evaluation_point, chunk_value) pairs
    """
    if k is None:
        k = len(data)
    if len(data) != k:
        raise ValueError(f"Data length {len(data)} != k={k}")
    if n < k:
        raise ValueError(f"n={n} must be >= k={k}")

    # The data IS the polynomial coefficients
    coeffs = data

    # Evaluate at points 1, 2, ..., n (never at 0 — that would just give coeffs[0])
    chunks = []
    for i in range(1, n + 1):
        value = poly_evaluate(coeffs, i, p)
        chunks.append((i, value))

    return chunks


def decode(chunks: list[tuple[int, int]], k: int,
           p: int = FIELD_PRIME) -> list[int]:
    """Reconstruct original k data values from any k chunks.

    Uses Lagrange interpolation to recover the polynomial coefficients.
    We evaluate the recovered polynomial at x=0 won't give us all coefficients,
    so instead we interpolate at each coefficient index.

    Actually, the cleanest approach: interpolate to find f(0), f(x) for enough
    points, then recover coefficients. But for simplicity, we recover each
    coefficient by interpolating at enough points and solving.

    Simpler approach: recover the polynomial by evaluating at points 0..k-1
    using Lagrange, but this gives f(0), f(1), ..., f(k-1), not coefficients.

    Best approach: use Lagrange to evaluate at k fresh points, then solve
    the Vandermonde system. OR just use Lagrange to reconstruct each
    original data point (coefficient) directly.

    Since data[i] = coefficient of x^i, we need to recover the polynomial
    itself, not just evaluate it. We'll reconstruct f(0) which gives data[0],
    then use the relationship between evaluations to get all coefficients.
    """
    if len(chunks) < k:
        raise ValueError(f"Need at least k={k} chunks, got {len(chunks)}")

    # Use exactly k chunks
    selected = chunks[:k]

    # Recover polynomial coefficients from k evaluation points.
    # We know f(x_1)=y_1, ..., f(x_k)=y_k for a degree-(k-1) polynomial.
    # To recover coefficients, we evaluate the interpolated polynomial at
    # x = 0, 1, 2, ..., k-1 and then solve for coefficients.
    # But there's a simpler way: build the coefficient form directly.

    # Method: Newton's forward differences / coefficient extraction
    # Evaluate the Lagrange polynomial at x = 0 to get c_0, then use
    # a system of equations. Actually, let's just recover coefficients
    # by building the polynomial in coefficient form from the points.

    coeffs = _recover_coefficients(selected, k, p)
    return coeffs


def _recover_coefficients(points: list[tuple[int, int]], k: int,
                           p: int = FIELD_PRIME) -> list[int]:
    """Recover polynomial coefficients from k evaluation points.

    Uses the fact that if we know f(x) at k points, we can build the
    coefficient-form polynomial by constructing Lagrange basis polynomials
    in coefficient form and summing them.
    """
    # Initialize coefficient array (degree k-1, so k coefficients)
    coeffs = [0] * k

    for i, (x_i, y_i) in enumerate(points):
        # Build the i-th Lagrange basis polynomial in coefficient form
        # L_i(x) = product_{j!=i} (x - x_j) / (x_i - x_j)

        # Start with the constant polynomial [1]
        basis_coeffs = [1]

        # Multiply by (x - x_j) for each j != i
        denominator = 1
        for j, (x_j, _) in enumerate(points):
            if i == j:
                continue
            denominator = fp_mul(denominator, fp_sub(x_i, x_j, p), p)

            # Multiply current polynomial by (x - x_j)
            # If current is [a0, a1, ...], result is [-x_j*a0, a0-x_j*a1, a1-x_j*a2, ...]
            new_coeffs = [0] * (len(basis_coeffs) + 1)
            for idx, c in enumerate(basis_coeffs):
                # x * c contributes to index idx+1
                new_coeffs[idx + 1] = fp_add(new_coeffs[idx + 1], c, p)
                # -x_j * c contributes to index idx
                new_coeffs[idx] = fp_sub(new_coeffs[idx], fp_mul(x_j, c, p), p)
            basis_coeffs = new_coeffs

        # Scale by y_i / denominator
        scale = fp_div(y_i, denominator, p)
        for idx in range(len(basis_coeffs)):
            if idx < k:
                coeffs[idx] = fp_add(coeffs[idx], fp_mul(scale, basis_coeffs[idx], p), p)

    return coeffs


def string_to_chunks(text: str) -> list[int]:
    """Convert a string to a list of byte values (field elements)."""
    return [b for b in text.encode("utf-8")]


def chunks_to_string(values: list[int]) -> str:
    """Convert a list of byte values back to a string."""
    return bytes(v % 256 for v in values).decode("utf-8", errors="replace")


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Reed-Solomon erasure coding."""

    print("=" * 70)
    print("  Reed-Solomon Erasure Coding")
    print("=" * 70)

    # --- Explain the concept ---
    print("\n--- What Is Erasure Coding? ---\n")
    print("  ┌──────────────────────────────────────────────────────────┐")
    print("  │  Problem: Distribute data across unreliable nodes.      │")
    print("  │  Simple replication (3 copies) wastes 3x storage.       │")
    print("  │                                                         │")
    print("  │  Erasure coding: encode k data chunks into n chunks.    │")
    print("  │  ANY k of the n chunks can reconstruct the original.    │")
    print("  │  Storage overhead: only n/k (e.g., 6/4 = 1.5x).        │")
    print("  │                                                         │")
    print("  │  Math: data values become polynomial coefficients.      │")
    print("  │  Evaluate the polynomial at n points → n chunks.        │")
    print("  │  Lagrange interpolation recovers the polynomial from    │")
    print("  │  any k points (k points determine a degree-k-1 poly).  │")
    print("  └──────────────────────────────────────────────────────────┘")

    # === Example 1: Simple numeric encoding ===
    print("\n" + "-" * 70)
    print("  Example 1: Encode [10, 20, 30, 40] with (k=4, n=6)")
    print("-" * 70)

    data = [10, 20, 30, 40]
    k, n = 4, 6

    print(f"\n  Original data (k={k} values): {data}")
    print(f"  These become polynomial coefficients:")
    print(f"    f(x) = {data[0]} + {data[1]}x + {data[2]}x^2 + {data[3]}x^3")
    print()

    # Encode
    chunks = encode(data, n, k)
    print(f"  Encoded into n={n} chunks (evaluating f at x=1..{n}):")
    print(f"  {'Point (x)':>12s}  {'Value f(x)':>12s}")
    print(f"  {'-'*12}  {'-'*12}")
    for x_val, y_val in chunks:
        # Verify by hand for the first point
        # Non-systematic encoding: all chunks are polynomial evaluations,
        # none contain the original data directly
        print(f"  {x_val:>12d}  {y_val:>12d}")

    # Verify f(1) by hand
    f1 = (10 + 20*1 + 30*1 + 40*1) % FIELD_PRIME
    print(f"\n  Verify: f(1) = 10 + 20(1) + 30(1) + 40(1) = {f1}")

    # --- Lose 2 chunks and reconstruct ---
    print(f"\n  --- Simulate losing 2 chunks ---\n")

    # Remove chunks at positions 2 and 5 (arbitrary choice)
    lost_indices = [1, 4]  # 0-indexed positions in the chunk list
    surviving = [c for i, c in enumerate(chunks) if i not in lost_indices]
    lost = [chunks[i] for i in lost_indices]

    print(f"  Lost chunks at x = {[c[0] for c in lost]}")
    print(f"  Surviving chunks ({len(surviving)}/{n}):")
    for x_val, y_val in surviving:
        print(f"    x={x_val}: {y_val}")

    # Reconstruct
    recovered = decode(surviving, k)
    print(f"\n  Reconstructed data: {recovered}")
    print(f"  Original data:      {data}")
    print(f"  Match: {'YES' if recovered == data else 'NO'}")

    # === Example 2: Encode a string ===
    print("\n" + "-" * 70)
    print("  Example 2: Encode 'BLOCKCHAIN' with (k=10, n=15)")
    print("-" * 70)

    text = "BLOCKCHAIN"
    data_bytes = string_to_chunks(text)
    k2, n2 = len(data_bytes), 15

    print(f"\n  Original text: '{text}'")
    print(f"  As bytes: {data_bytes}")
    print(f"  k={k2} (data chunks), n={n2} (total chunks)")
    print(f"  Redundancy: {n2 - k2} extra chunks ({(n2-k2)*100//k2}% overhead)")
    print()

    # Encode
    chunks2 = encode(data_bytes, n2, k2)
    print(f"  Encoded chunks:")
    for i, (x_val, y_val) in enumerate(chunks2):
        print(f"    Chunk {i+1:2d} (x={x_val:2d}): {y_val:3d}")

    # --- Lose 5 chunks (the maximum we can lose) ---
    print(f"\n  --- Lose 5 random chunks (max tolerable: {n2 - k2}) ---\n")

    random.seed(42)  # Reproducible demo
    lose_positions = random.sample(range(n2), n2 - k2)
    surviving2 = [c for i, c in enumerate(chunks2) if i not in lose_positions]
    lost2 = [chunks2[i] for i in sorted(lose_positions)]

    print(f"  Lost chunks: x = {[c[0] for c in lost2]}")
    print(f"  Surviving: {len(surviving2)} chunks (exactly k={k2})")

    # Show surviving vs lost visually
    status = ""
    for i in range(n2):
        if i in lose_positions:
            status += " X "
        else:
            status += " O "
    print(f"\n  Chunk status: {status}")
    print(f"                {''.join(f'{i+1:^3d}' for i in range(n2))}")
    print(f"  (O = available, X = lost)")

    # Reconstruct
    recovered_bytes = decode(surviving2, k2)
    recovered_text = chunks_to_string(recovered_bytes)

    print(f"\n  Reconstructed bytes: {recovered_bytes}")
    print(f"  Reconstructed text:  '{recovered_text}'")
    print(f"  Original text:       '{text}'")
    print(f"  Match: {'YES' if recovered_text == text else 'NO'}")

    # === Example 3: Too many losses ===
    print("\n" + "-" * 70)
    print("  Example 3: Lose Too Many Chunks (Reconstruction Fails)")
    print("-" * 70)

    data3 = [100, 200, 50, 75]
    k3, n3 = 4, 6
    chunks3 = encode(data3, n3, k3)

    # Lose 3 chunks (only 3 survive, but we need k=4)
    surviving3 = chunks3[:3]
    print(f"\n  Data: {data3}, k={k3}, n={n3}")
    print(f"  Lost 3 chunks, only {len(surviving3)} survive (need {k3})")
    print(f"  Surviving: {surviving3}")

    try:
        recovered3 = decode(surviving3, k3)
        print(f"  Attempted reconstruction: {recovered3}")
        print(f"  Match: {'YES' if recovered3 == data3 else 'NO (expected failure)'}")
    except ValueError as e:
        print(f"  Error: {e}")
        print(f"  Cannot reconstruct — need at least k={k3} chunks!")

    # === How this is used in blockchains ===
    print("\n" + "-" * 70)
    print("  Blockchain Applications")
    print("-" * 70)
    print()
    print("  ┌──────────────────────────────────────────────────────────┐")
    print("  │  Solana Turbine                                         │")
    print("  │    Blocks are shredded into chunks with erasure coding.  │")
    print("  │    Validators only need k of n shreds to reconstruct.   │")
    print("  │    This reduces bandwidth by ~n/k compared to sending   │")
    print("  │    the full block to every validator.                    │")
    print("  │                                                         │")
    print("  │  Ethereum Danksharding (EIP-4844)                       │")
    print("  │    Blob data is erasure-coded so validators can sample   │")
    print("  │    random chunks. If enough random samples are valid,   │")
    print("  │    the full data is available with high probability.     │")
    print("  │    This is called Data Availability Sampling (DAS).     │")
    print("  │                                                         │")
    print("  │  Key Insight: Erasure coding lets you verify data       │")
    print("  │  availability WITHOUT downloading the full data.        │")
    print("  └──────────────────────────────────────────────────────────┘")

    print()
    print("=" * 70)
    print("  Reed-Solomon Erasure Coding complete.")
    print("=" * 70)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
