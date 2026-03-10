"""
TITLE: SHA-256 Hashing From Scratch
CATEGORY: core

WHAT THIS IMPLEMENTS:
    A complete SHA-256 hash function built from pure bit manipulation, following
    the FIPS 180-4 specification. No cryptographic libraries are used for the
    hashing itself — only stdlib's hashlib is imported to verify correctness.

KEY CONCEPTS:
    - Bitwise operations (AND, OR, XOR, NOT, right-rotate, right-shift)
    - Merkle-Damgård construction (padding, blocks, compression)
    - Avalanche effect (tiny input change → ~50% output bits flip)
    - One-way functions (easy to compute, infeasible to reverse)

PREREQUISITE SCRIPTS:
    - None (this is the foundation for everything else)

REAL-WORLD RELEVANCE:
    SHA-256 is the backbone of Bitcoin's proof-of-work mining (double-SHA-256),
    Merkle trees, transaction IDs, and address generation. Ethereum uses Keccak-256
    but the principles are identical.
"""

import hashlib  # Only used in demo() to VERIFY our implementation, not to compute
import struct   # For packing/unpacking bytes to 32-bit words

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Mask to keep values within 32 bits — Python ints are arbitrary precision,
# so we must manually truncate after every arithmetic operation
MASK_32 = 0xFFFFFFFF

# --- Initial hash values (H0..H7) -----------------------------------------
# These are the first 32 bits of the fractional parts of the square roots
# of the first 8 prime numbers (2, 3, 5, 7, 11, 13, 17, 19).
# They serve as the starting state of the hash — no "magic numbers",
# they come from an auditable mathematical process.
H_INITIAL = [
    0x6a09e667,  # frac(sqrt(2))
    0xbb67ae85,  # frac(sqrt(3))
    0x3c6ef372,  # frac(sqrt(5))
    0xa54ff53a,  # frac(sqrt(7))
    0x510e527f,  # frac(sqrt(11))
    0x9b05688c,  # frac(sqrt(13))
    0x1f83d9ab,  # frac(sqrt(17))
    0x5be0cd19,  # frac(sqrt(19))
]

# --- Round constants (K0..K63) ---------------------------------------------
# First 32 bits of the fractional parts of the cube roots of the first
# 64 prime numbers. One constant per compression round — ensures each
# round mixes data differently.
K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Bitwise helper functions -----------------------------------------------
# SHA-256 relies on six bitwise operations applied to 32-bit words.
# We define them as small functions so the compression loop reads clearly.

def right_rotate(value, amount):
    """Circular right rotation of a 32-bit integer.

    Unlike a right shift (which discards bits), rotation wraps the
    fallen-off bits back to the left side. This preserves information
    while mixing bit positions.
    """
    return ((value >> amount) | (value << (32 - amount))) & MASK_32


def right_shift(value, amount):
    """Logical right shift — bits shifted out on the right are lost."""
    return value >> amount


def ch(x, y, z):
    """Choice function: for each bit position, if x=1 pick y, else pick z.

    Think of x as a selector switch: it 'chooses' between y and z
    at every bit position independently.
    """
    return ((x & y) ^ (~x & z)) & MASK_32


def maj(x, y, z):
    """Majority function: output bit is whatever 2-of-3 inputs agree on.

    Acts as a voting mechanism — the majority wins at each bit position.
    """
    return (x & y) ^ (x & z) ^ (y & z)


def big_sigma0(x):
    """Upper-case Sigma_0: used in the compression function.

    Combines three rotations/shifts to thoroughly mix bits.
    The specific rotation amounts (2, 13, 22) are chosen so that
    after many rounds, every output bit depends on every input bit.
    """
    return right_rotate(x, 2) ^ right_rotate(x, 13) ^ right_rotate(x, 22)


def big_sigma1(x):
    """Upper-case Sigma_1: used in the compression function.

    Rotation amounts (6, 11, 25) complement Sigma_0 to ensure
    full diffusion across all 32 bit positions.
    """
    return right_rotate(x, 6) ^ right_rotate(x, 11) ^ right_rotate(x, 25)


def small_sigma0(x):
    """Lower-case sigma_0: used in the message schedule expansion.

    Mixes bits of earlier message words to create new schedule words.
    Uses two rotations and one shift (7, 18, 3).
    """
    return right_rotate(x, 7) ^ right_rotate(x, 18) ^ right_shift(x, 3)


def small_sigma1(x):
    """Lower-case sigma_1: used in the message schedule expansion.

    Complements sigma_0 with rotation/shift amounts (17, 19, 10).
    """
    return right_rotate(x, 17) ^ right_rotate(x, 19) ^ right_shift(x, 10)


# --- Padding ----------------------------------------------------------------

def pad_message(message_bytes):
    """Pad the message to a multiple of 512 bits (64 bytes) per FIPS 180-4.

    Padding layout:
      [original message] [1-bit] [zero bits...] [64-bit big-endian length]

    The 1-bit acts as a delimiter between message and padding.
    The 64-bit length at the end prevents length-extension ambiguity:
    without it, "ab\\x00" and "ab" would pad to the same block.
    """
    msg_len_bits = len(message_bytes) * 8  # Original length in bits

    # Append the 0x80 byte — this is a 1-bit followed by 7 zero bits
    message_bytes += b'\x80'

    # Pad with zero bytes until length ≡ 448 mod 512 (in bits),
    # i.e., length ≡ 56 mod 64 (in bytes).
    # This leaves exactly 8 bytes at the end for the 64-bit length.
    while len(message_bytes) % 64 != 56:
        message_bytes += b'\x00'

    # Append the original message length as a 64-bit big-endian integer
    message_bytes += struct.pack('>Q', msg_len_bits)

    return message_bytes


# --- Message schedule -------------------------------------------------------

def create_message_schedule(block):
    """Expand a 64-byte (512-bit) block into 64 thirty-two-bit words.

    Words 0-15 come directly from the block.
    Words 16-63 are derived by mixing earlier words with sigma functions.
    This expansion ensures that every bit of the original message
    influences many rounds of compression.
    """
    # Unpack the 64-byte block into 16 big-endian 32-bit words
    w = list(struct.unpack('>16I', block))

    # Extend from 16 words to 64 words
    for i in range(16, 64):
        # Each new word mixes four earlier words via sigma functions
        w.append(
            (small_sigma1(w[i - 2]) + w[i - 7] +
             small_sigma0(w[i - 15]) + w[i - 16]) & MASK_32
        )

    return w


# --- Compression function ---------------------------------------------------

def compress(state, message_schedule):
    """Run 64 rounds of SHA-256 compression on the given state.

    Each round takes the 8 working variables (a..h), mixes them using
    Ch, Maj, Sigma functions, the round constant K[i], and the
    schedule word W[i]. After 64 rounds, the working variables are
    added back to the input state (Merkle-Damgård construction).
    """
    a, b, c, d, e, f, g, h = state  # Unpack 8 working variables

    for i in range(64):
        # T1 combines: Sigma1(e), Ch(e,f,g), h, K[i], W[i]
        t1 = (h + big_sigma1(e) + ch(e, f, g) + K[i] + message_schedule[i]) & MASK_32

        # T2 combines: Sigma0(a), Maj(a,b,c)
        t2 = (big_sigma0(a) + maj(a, b, c)) & MASK_32

        # Shift all working variables down by one position,
        # inject T1+T2 at the top and T1 into the middle
        h = g
        g = f
        f = e
        e = (d + t1) & MASK_32  # d gets bumped up, mixed with T1
        d = c
        c = b
        b = a
        a = (t1 + t2) & MASK_32  # New 'a' is the most mixed variable

    # Add compressed chunk back to the running hash state
    # This is the Merkle-Damgård "finalization" for this block
    result = [
        (state[0] + a) & MASK_32,
        (state[1] + b) & MASK_32,
        (state[2] + c) & MASK_32,
        (state[3] + d) & MASK_32,
        (state[4] + e) & MASK_32,
        (state[5] + f) & MASK_32,
        (state[6] + g) & MASK_32,
        (state[7] + h) & MASK_32,
    ]
    return result


# --- Main hash function -----------------------------------------------------

def sha256(message):
    """Compute the SHA-256 hash of a byte string.

    Steps:
      1. Pad the message to a multiple of 512 bits
      2. Split into 512-bit (64-byte) blocks
      3. For each block: expand to message schedule, compress into state
      4. Concatenate final state words into 256-bit digest

    Args:
        message: bytes to hash

    Returns:
        Hex string of the 256-bit hash
    """
    if isinstance(message, str):
        message = message.encode('utf-8')  # Convert string to bytes

    # Step 1: Pad
    padded = pad_message(bytearray(message))

    # Step 2: Initialize hash state with the "nothing-up-my-sleeve" constants
    state = list(H_INITIAL)

    # Step 3: Process each 64-byte block
    num_blocks = len(padded) // 64
    for block_idx in range(num_blocks):
        block = padded[block_idx * 64 : (block_idx + 1) * 64]
        schedule = create_message_schedule(bytes(block))
        state = compress(state, schedule)

    # Step 4: Produce the final 256-bit hash as a hex string
    return ''.join(f'{word:08x}' for word in state)


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def count_bit_differences(hex_a, hex_b):
    """Count how many bits differ between two hex strings.

    XOR the integers — each 1-bit in the result is a position
    where the two hashes disagree.
    """
    int_a = int(hex_a, 16)
    int_b = int(hex_b, 16)
    xor = int_a ^ int_b
    return bin(xor).count('1')  # popcount via string conversion


def demo():
    """Run a visual demonstration of SHA-256 and the avalanche effect."""

    # --- Part 1: Basic hashing and verification ----------------------------
    print("=" * 60)
    print("  SHA-256 From Scratch")
    print("=" * 60)
    print()

    test_inputs = [
        "hello",
        "hello world",
        "blockchain",
        "",                    # Edge case: empty string
        "a" * 1000,            # Edge case: long input spanning multiple blocks
    ]

    all_match = True
    for text in test_inputs:
        our_hash = sha256(text)
        lib_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        match = our_hash == lib_hash

        # Truncate display for very long inputs
        display = text if len(text) <= 30 else text[:27] + "..."

        print(f'  Input:   "{display}"')
        print(f"  Ours:    {our_hash}")
        print(f"  hashlib: {lib_hash}")
        print(f"  Match:   {'YES' if match else 'NO <<<< MISMATCH!'}")
        print()

        if not match:
            all_match = False

    if all_match:
        print("  All hashes match hashlib — implementation is correct.")
    else:
        print("  WARNING: Some hashes did not match!")
    print()

    # --- Part 2: Avalanche effect ------------------------------------------
    print("=" * 60)
    print("  Avalanche Effect")
    print("=" * 60)
    print()
    print("  Changing a single character should flip ~50% of output bits.")
    print("  (A good hash function has no correlation between input and output.)")
    print()

    avalanche_pairs = [
        ("hello", "hallo"),        # One vowel changed
        ("hello", "hellp"),        # Last letter changed
        ("blockchain", "Blockchain"),  # Case change
        ("test1", "test2"),        # One digit changed
    ]

    for original, modified in avalanche_pairs:
        hash_orig = sha256(original)
        hash_mod = sha256(modified)
        flipped = count_bit_differences(hash_orig, hash_mod)
        pct = (flipped / 256) * 100  # 256 bits total in SHA-256

        print(f'  "{original}"')
        print(f"    → {hash_orig}")
        print(f'  "{modified}"')
        print(f"    → {hash_mod}")
        print(f"    Bits flipped: {flipped}/256 = {pct:.1f}%")
        print()

    # --- Part 3: Show the internal structure of a hash ---------------------
    print("=" * 60)
    print("  Inside a SHA-256 Hash")
    print("=" * 60)
    print()
    print("  A SHA-256 digest is 8 × 32-bit words concatenated:")
    print()

    example = "hello"
    h = sha256(example)
    words = [h[i:i+8] for i in range(0, 64, 8)]  # Split into 8-char chunks

    print(f'  Input: "{example}"')
    print("  ┌──────────┬────────────┐")
    print("  │  Word    │   Value    │")
    print("  ├──────────┼────────────┤")
    for i, w in enumerate(words):
        print(f"  │  H[{i}]    │  {w}  │")
    print("  └──────────┴────────────┘")
    print()
    print(f"  Full hash: {h}")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
