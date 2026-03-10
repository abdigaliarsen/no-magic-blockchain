"""
TITLE: EVM Precompiled Contracts
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    Simplified versions of Ethereum's precompiled contracts — special contracts
    at addresses 0x01 through 0x09 that implement cryptographic primitives
    natively rather than in EVM bytecode. Covers ecRecover, SHA-256, RIPEMD-160,
    identity, modexp, and elliptic curve operations on the alt_bn128 curve.

KEY CONCEPTS:
    - Precompiles: native code at fixed addresses, callable like contracts
    - Gas pricing: each precompile has a specific gas cost formula
    - ecRecover (0x01): recover signer address from ECDSA signature
    - modexp (0x05): modular exponentiation for RSA, ZK proofs
    - alt_bn128 curve operations (0x06-0x08): EC add, mul, pairing for ZK-SNARKs

PREREQUISITE SCRIPTS:
    - core/fundamentals/01_hashing.py (SHA-256 basics)
    - core/fundamentals/02_public_key_crypto.py (EC math)
    - core/fundamentals/03_digital_signatures.py (ECDSA)
    - ethereum/fundamentals/02_evm_bytecode.py (EVM execution context)

REAL-WORLD RELEVANCE:
    Precompiles are critical infrastructure — ecRecover enables signature
    verification in smart contracts (used by every DeFi protocol), and the
    alt_bn128 precompiles (added in Byzantium) enable on-chain ZK-SNARK
    verification, powering zkRollups like zkSync and Polygon zkEVM.
"""

import hashlib
import struct
import math

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# secp256k1 curve parameters (used by ecRecover, same as Ethereum)
SECP256K1_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
SECP256K1_GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
SECP256K1_GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
SECP256K1_G = (SECP256K1_GX, SECP256K1_GY)

# alt_bn128 curve parameters (used by precompiles 0x06-0x08)
# Curve: y^2 = x^3 + 3 over F_p
ALT_BN128_P = 21888242871839275222246405745257275088696311157297823662689037894645226208583
ALT_BN128_N = 21888242871839275222246405745257275088548364400416034343698204186575808495617
ALT_BN128_G = (1, 2)  # Generator point
ALT_BN128_B = 3       # Curve coefficient b in y^2 = x^3 + b

# Point at infinity
POINT_INF = None

# Gas costs for each precompile
PRECOMPILE_GAS = {
    0x01: 3_000,      # ecRecover — fixed cost
    0x02: 60,         # SHA-256 — base cost (+ 12 per word)
    0x03: 600,        # RIPEMD-160 — base cost (+ 120 per word)
    0x04: 15,         # Identity — base cost (+ 3 per word)
    0x05: None,       # modexp — dynamic (based on operand sizes)
    0x06: 150,        # ecAdd (alt_bn128) — Istanbul pricing
    0x07: 6_000,      # ecMul (alt_bn128) — Istanbul pricing
    0x08: 45_000,     # ecPairing — base (+ 34,000 per pair)
    0x09: 4_000,      # blake2f — per round
}


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# Elliptic curve arithmetic (shared by ecRecover and alt_bn128 precompiles)
# ----------------------------------------------------------------------------

def mod_inv(a: int, p: int) -> int:
    """Modular inverse using extended Euclidean algorithm."""
    if a == 0:
        raise ValueError("No inverse for zero")
    g, x, _ = _extended_gcd(a % p, p)
    if g != 1:
        raise ValueError(f"No inverse: gcd({a}, {p}) = {g}")
    return x % p


def _extended_gcd(a: int, b: int) -> tuple[int, int, int]:
    """Extended Euclidean algorithm: returns (gcd, x, y) where ax + by = gcd."""
    if a == 0:
        return b, 0, 1
    g, x, y = _extended_gcd(b % a, a)
    return g, y - (b // a) * x, x


def ec_add_generic(p1, p2, curve_p: int, curve_a: int = 0):
    """Add two points on curve y^2 = x^3 + ax + b (mod curve_p)."""
    if p1 is POINT_INF:
        return p2
    if p2 is POINT_INF:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and y1 == (curve_p - y2) % curve_p:
        return POINT_INF  # P + (-P) = O

    if x1 == x2 and y1 == y2:
        # Point doubling
        lam = (3 * x1 * x1 + curve_a) * mod_inv(2 * y1, curve_p) % curve_p
    else:
        # Point addition
        lam = (y2 - y1) * mod_inv(x2 - x1, curve_p) % curve_p

    x3 = (lam * lam - x1 - x2) % curve_p
    y3 = (lam * (x1 - x3) - y1) % curve_p
    return (x3, y3)


def ec_mul_generic(point, scalar: int, curve_p: int, curve_a: int = 0):
    """Scalar multiplication using double-and-add."""
    if scalar == 0 or point is POINT_INF:
        return POINT_INF
    scalar = scalar % SECP256K1_N if curve_p == SECP256K1_P else scalar
    result = POINT_INF
    addend = point
    while scalar > 0:
        if scalar & 1:
            result = ec_add_generic(result, addend, curve_p, curve_a)
        addend = ec_add_generic(addend, addend, curve_p, curve_a)
        scalar >>= 1
    return result


# ----------------------------------------------------------------------------
# Precompile 0x01: ecRecover
# ----------------------------------------------------------------------------

def precompile_ec_recover(msg_hash: bytes, v: int, r: int, s: int) -> bytes | None:
    """Recover the signer's Ethereum address from an ECDSA signature.

    This is the most-used precompile — every signature verification in
    Solidity (ecrecover) calls this. It recovers the public key from
    (hash, v, r, s) and returns the corresponding 20-byte address.
    """
    # v must be 27 or 28 (Ethereum's recovery id convention)
    if v not in (27, 28):
        return None
    recovery_flag = v - 27  # 0 or 1

    # r and s must be in valid range
    if not (0 < r < SECP256K1_N and 0 < s < SECP256K1_N):
        return None

    # Recover the public key from the signature
    # Step 1: Compute the point R from r (x-coordinate)
    x = r
    # Compute y from x: y^2 = x^3 + 7 (mod P)
    y_sq = (pow(x, 3, SECP256K1_P) + 7) % SECP256K1_P
    y = pow(y_sq, (SECP256K1_P + 1) // 4, SECP256K1_P)  # Square root

    # Select correct y based on recovery flag
    if y % 2 != recovery_flag:
        y = SECP256K1_P - y

    R = (x, y)

    # Step 2: Compute public key Q = r^(-1) * (s*R - hash*G)
    r_inv = mod_inv(r, SECP256K1_N)
    z = int.from_bytes(msg_hash, "big")

    # s*R
    sR = ec_mul_generic(R, s, SECP256K1_P)
    # z*G (z = message hash as integer)
    zG = ec_mul_generic(SECP256K1_G, z, SECP256K1_P)
    # s*R - z*G
    neg_zG = (zG[0], (SECP256K1_P - zG[1]) % SECP256K1_P) if zG else POINT_INF
    point = ec_add_generic(sR, neg_zG, SECP256K1_P)
    # Q = r^(-1) * (s*R - z*G)
    pub_key = ec_mul_generic(point, r_inv, SECP256K1_P)

    if pub_key is POINT_INF:
        return None

    # Step 3: Derive Ethereum address = keccak256(pubkey_bytes)[12:]
    # Using SHA-256 as stand-in for keccak256 (stdlib only)
    pub_bytes = (pub_key[0].to_bytes(32, "big") +
                 pub_key[1].to_bytes(32, "big"))
    addr_hash = hashlib.sha256(pub_bytes).digest()
    return addr_hash[12:]  # Last 20 bytes = Ethereum address


# ----------------------------------------------------------------------------
# Precompile 0x02: SHA-256
# ----------------------------------------------------------------------------

def precompile_sha256(data: bytes) -> bytes:
    """SHA-256 hash — straightforward but cheaper as a precompile.

    In EVM bytecode, SHA-256 would cost ~1000s of gas per operation.
    As a precompile, it costs only 60 + 12 * ceil(len/32) gas.
    """
    return hashlib.sha256(data).digest()


def sha256_gas(data: bytes) -> int:
    """Calculate gas cost for SHA-256 precompile."""
    words = math.ceil(len(data) / 32)  # Round up to 32-byte words
    return 60 + 12 * words


# ----------------------------------------------------------------------------
# Precompile 0x03: RIPEMD-160
# ----------------------------------------------------------------------------

def precompile_ripemd160(data: bytes) -> bytes:
    """RIPEMD-160 hash — used in Bitcoin address generation.

    Returns 20 bytes, left-padded to 32 bytes (EVM word size).
    """
    h = hashlib.new("ripemd160", data).digest()
    return b'\x00' * 12 + h  # Left-pad to 32 bytes


def ripemd160_gas(data: bytes) -> int:
    """Calculate gas cost for RIPEMD-160 precompile."""
    words = math.ceil(len(data) / 32)
    return 600 + 120 * words


# ----------------------------------------------------------------------------
# Precompile 0x04: Identity (data copy)
# ----------------------------------------------------------------------------

def precompile_identity(data: bytes) -> bytes:
    """Identity function — just returns the input data.

    Why does this exist? Because CALLDATACOPY into memory costs gas per byte,
    and this precompile offers a cheaper path for copying data in contracts.
    """
    return data


def identity_gas(data: bytes) -> int:
    """Calculate gas cost for identity precompile."""
    words = math.ceil(len(data) / 32)
    return 15 + 3 * words


# ----------------------------------------------------------------------------
# Precompile 0x05: modexp (modular exponentiation)
# ----------------------------------------------------------------------------

def precompile_modexp(base: int, exponent: int, modulus: int) -> int:
    """Modular exponentiation: base^exponent mod modulus.

    Essential for RSA signature verification and various ZK proof schemes.
    Python's built-in pow(base, exp, mod) uses fast modular exponentiation.
    """
    if modulus == 0:
        return 0
    return pow(base, exponent, modulus)


def modexp_gas(base_len: int, exp_len: int, mod_len: int, exponent: int) -> int:
    """Calculate gas cost for modexp (EIP-2565 pricing).

    Gas = max(200, floor(mult_complexity * iter_count / 3))
    """
    max_len = max(base_len, mod_len)
    # Multiplication complexity
    if max_len <= 64:
        mult_complexity = max_len * max_len
    elif max_len <= 1024:
        mult_complexity = max_len * max_len // 4 + 96 * max_len - 3072
    else:
        mult_complexity = max_len * max_len // 16 + 480 * max_len - 199680

    # Iteration count based on exponent size
    if exp_len <= 32:
        if exponent == 0:
            iter_count = 0
        else:
            iter_count = exponent.bit_length() - 1
    else:
        iter_count = 8 * (exp_len - 32) + max(exponent.bit_length() - 1, 0)

    gas = mult_complexity * max(iter_count, 1) // 3
    return max(200, gas)


# ----------------------------------------------------------------------------
# Precompile 0x06: ecAdd (alt_bn128 point addition)
# ----------------------------------------------------------------------------

def precompile_ec_add(x1: int, y1: int, x2: int, y2: int) -> tuple | None:
    """Add two points on the alt_bn128 curve.

    alt_bn128 (also called bn256) is used for ZK-SNARK verification.
    The curve equation is y^2 = x^3 + 3 over a 254-bit prime field.
    """
    # Handle points at infinity (encoded as (0, 0))
    p1 = POINT_INF if (x1 == 0 and y1 == 0) else (x1, y1)
    p2 = POINT_INF if (x2 == 0 and y2 == 0) else (x2, y2)

    result = ec_add_generic(p1, p2, ALT_BN128_P)
    if result is POINT_INF:
        return (0, 0)
    return result


# ----------------------------------------------------------------------------
# Precompile 0x07: ecMul (alt_bn128 scalar multiplication)
# ----------------------------------------------------------------------------

def precompile_ec_mul(x: int, y: int, scalar: int) -> tuple | None:
    """Multiply a point on alt_bn128 by a scalar.

    This is the core operation for ZK-SNARK proof verification —
    verifiers compute linear combinations of curve points.
    """
    point = POINT_INF if (x == 0 and y == 0) else (x, y)
    result = ec_mul_generic(point, scalar, ALT_BN128_P)
    if result is POINT_INF:
        return (0, 0)
    return result


# ----------------------------------------------------------------------------
# Precompile 0x08: ecPairing (simplified)
# ----------------------------------------------------------------------------

def precompile_ec_pairing_check(pairs: list[tuple]) -> bool:
    """Simplified pairing check on alt_bn128.

    A real pairing check verifies: e(A1, B1) * e(A2, B2) * ... == 1
    where e is a bilinear map. This is the heart of ZK-SNARK verification.

    We simulate the pairing algebraically: for points (a_i, b_i),
    check that the sum of scalar products equals zero (simplified).
    """
    # In reality, this uses the Tate/Weil/Ate pairing over extension fields.
    # We simulate by checking a simplified algebraic relation.
    if not pairs:
        return True  # Empty pairing is trivially true

    # Simplified check: verify that point relationships are consistent
    # Real implementation would use F_p^12 arithmetic
    accumulator = 0
    for g1_point, g2_scalar in pairs:
        if g1_point is not POINT_INF and g1_point != (0, 0):
            # Use x-coordinate * scalar as simplified "pairing value"
            accumulator += g1_point[0] * g2_scalar
    # In a real pairing, the product would equal the identity in GT
    return accumulator % ALT_BN128_N == 0


# ----------------------------------------------------------------------------
# Precompile 0x09: blake2f (BLAKE2b compression)
# ----------------------------------------------------------------------------

def precompile_blake2f(rounds: int, h: bytes, m: bytes, t: bytes,
                       final_flag: bool) -> bytes:
    """BLAKE2b F compression function.

    Added in EIP-152 (Istanbul). Enables efficient BLAKE2b hashing in
    smart contracts, useful for Zcash interoperability (Zcash uses BLAKE2b).

    We use hashlib's blake2b as the implementation.
    """
    # Simplified: use hashlib's blake2b with the message
    # Real precompile takes raw state and runs `rounds` compression rounds
    hasher = hashlib.blake2b(m, digest_size=64)
    return hasher.digest()


# ----------------------------------------------------------------------------
# Precompile Registry
# ----------------------------------------------------------------------------

class PrecompileRegistry:
    """Registry of all EVM precompiled contracts.

    Precompiles live at addresses 0x01-0x09. When the EVM encounters a CALL
    to these addresses, it executes native code instead of EVM bytecode.
    """

    PRECOMPILES = {
        0x01: ("ecRecover", "Recover signer address from ECDSA signature"),
        0x02: ("SHA-256", "SHA-256 hash function"),
        0x03: ("RIPEMD-160", "RIPEMD-160 hash function"),
        0x04: ("identity", "Data copy (identity function)"),
        0x05: ("modexp", "Modular exponentiation (big integers)"),
        0x06: ("ecAdd", "alt_bn128 elliptic curve point addition"),
        0x07: ("ecMul", "alt_bn128 elliptic curve scalar multiplication"),
        0x08: ("ecPairing", "alt_bn128 bilinear pairing check"),
        0x09: ("blake2f", "BLAKE2b compression function"),
    }

    @classmethod
    def call(cls, address: int, input_data: dict) -> dict:
        """Call a precompile by address, return output and gas used."""
        if address not in cls.PRECOMPILES:
            raise ValueError(f"No precompile at address 0x{address:02x}")

        name, _ = cls.PRECOMPILES[address]
        result = {"precompile": name, "address": f"0x{address:02x}"}

        if address == 0x01:
            output = precompile_ec_recover(**input_data)
            result["output"] = output.hex() if output else "FAILED"
            result["gas"] = PRECOMPILE_GAS[0x01]

        elif address == 0x02:
            data = input_data["data"]
            output = precompile_sha256(data)
            result["output"] = output.hex()
            result["gas"] = sha256_gas(data)

        elif address == 0x03:
            data = input_data["data"]
            output = precompile_ripemd160(data)
            result["output"] = output.hex()
            result["gas"] = ripemd160_gas(data)

        elif address == 0x04:
            data = input_data["data"]
            output = precompile_identity(data)
            result["output"] = output.hex()
            result["gas"] = identity_gas(data)

        elif address == 0x05:
            output = precompile_modexp(**input_data)
            result["output"] = output
            base_len = (input_data["base"].bit_length() + 7) // 8
            exp_len = (input_data["exponent"].bit_length() + 7) // 8
            mod_len = (input_data["modulus"].bit_length() + 7) // 8
            result["gas"] = modexp_gas(base_len, exp_len, mod_len,
                                       input_data["exponent"])

        elif address == 0x06:
            output = precompile_ec_add(**input_data)
            result["output"] = output
            result["gas"] = PRECOMPILE_GAS[0x06]

        elif address == 0x07:
            output = precompile_ec_mul(**input_data)
            result["output"] = output
            result["gas"] = PRECOMPILE_GAS[0x07]

        elif address == 0x08:
            output = precompile_ec_pairing_check(**input_data)
            result["output"] = output
            result["gas"] = PRECOMPILE_GAS[0x08] + 34_000 * len(input_data.get("pairs", []))

        elif address == 0x09:
            output = precompile_blake2f(**input_data)
            result["output"] = output.hex()
            result["gas"] = input_data.get("rounds", 12) * PRECOMPILE_GAS[0x09]

        return result


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of all EVM precompiles."""

    print("=" * 72)
    print("  EVM PRECOMPILED CONTRACTS — Native Crypto at Fixed Addresses")
    print("=" * 72)

    # --- Overview ---
    print("\n--- Precompile Address Map ---\n")
    print(f"  {'Address':<10} {'Name':<15} {'Gas Cost':<18} {'Description'}")
    print(f"  {'─' * 10} {'─' * 15} {'─' * 18} {'─' * 35}")
    for addr, (name, desc) in PrecompileRegistry.PRECOMPILES.items():
        gas = PRECOMPILE_GAS[addr]
        gas_str = f"{gas:,}" if gas else "dynamic"
        print(f"  0x{addr:02x}      {name:<15} {gas_str:<18} {desc}")

    # --- 0x01: ecRecover ---
    print("\n\n--- 0x01: ecRecover (ECDSA Signature Recovery) ---\n")

    # Generate a keypair for demo
    private_key = 0xDEADBEEF12345678  # Demo private key
    pub_key = ec_mul_generic(SECP256K1_G, private_key, SECP256K1_P)

    # Sign a message
    msg = b"Transfer 1 ETH to 0xBob"
    msg_hash = hashlib.sha256(msg).digest()
    z = int.from_bytes(msg_hash, "big") % SECP256K1_N

    # ECDSA signing: k = random nonce, R = k*G, r = R.x, s = (z + r*privkey) / k
    k = 0x1234567890ABCDEF  # Fixed nonce for demo (NEVER do this in production!)
    R_point = ec_mul_generic(SECP256K1_G, k, SECP256K1_P)
    r = R_point[0] % SECP256K1_N
    s = (mod_inv(k, SECP256K1_N) * (z + r * private_key)) % SECP256K1_N
    v = 27 + (R_point[1] % 2)  # Recovery id

    print(f"  Message: \"{msg.decode()}\"")
    print(f"  Hash:    {msg_hash.hex()[:32]}...")
    print(f"  Signature:")
    print(f"    v = {v}")
    print(f"    r = {hex(r)[:24]}...")
    print(f"    s = {hex(s)[:24]}...")

    result = PrecompileRegistry.call(0x01, {
        "msg_hash": msg_hash, "v": v, "r": r, "s": s
    })
    print(f"\n  ecRecover result:")
    print(f"    Recovered address: 0x{result['output'][:40]}")
    print(f"    Gas used: {result['gas']:,}")

    # --- 0x02: SHA-256 ---
    print("\n\n--- 0x02: SHA-256 ---\n")

    test_data = b"Hello, Ethereum!"
    result = PrecompileRegistry.call(0x02, {"data": test_data})
    print(f"  Input:  \"{test_data.decode()}\" ({len(test_data)} bytes)")
    print(f"  Output: {result['output'][:32]}...")
    print(f"  Gas:    {result['gas']:,} (base 60 + 12 per 32-byte word)")

    # Show why precompile is cheaper than EVM
    evm_sha256_estimate = 250 * 64  # ~64 SHA-256 rounds, ~250 gas each in EVM
    print(f"\n  Cost comparison:")
    print(f"    Precompile: {result['gas']:>8,} gas")
    print(f"    EVM opcode: {evm_sha256_estimate:>8,} gas (estimated)")
    print(f"    Savings:    {evm_sha256_estimate // max(result['gas'], 1):>8}x cheaper")

    # --- 0x03: RIPEMD-160 ---
    print("\n\n--- 0x03: RIPEMD-160 ---\n")

    result = PrecompileRegistry.call(0x03, {"data": test_data})
    # The actual hash is the last 20 bytes (first 12 are zero-padding)
    print(f"  Input:  \"{test_data.decode()}\"")
    print(f"  Output: {result['output']}")
    print(f"  Hash:   {result['output'][24:]}  (20 bytes, left-padded to 32)")
    print(f"  Gas:    {result['gas']:,}")

    # --- 0x04: Identity ---
    print("\n\n--- 0x04: Identity (Data Copy) ---\n")

    result = PrecompileRegistry.call(0x04, {"data": test_data})
    print(f"  Input:  {test_data.hex()}")
    print(f"  Output: {result['output']}")
    print(f"  Match:  {result['output'] == test_data.hex()}")
    print(f"  Gas:    {result['gas']:,}")
    print(f"  Use case: cheaper than CALLDATACOPY for large data moves")

    # --- 0x05: modexp ---
    print("\n\n--- 0x05: modexp (Modular Exponentiation) ---\n")

    # RSA-like example: compute base^exp mod modulus
    base, exp, modulus = 4, 13, 497
    result = PrecompileRegistry.call(0x05, {
        "base": base, "exponent": exp, "modulus": modulus
    })
    print(f"  Compute: {base}^{exp} mod {modulus}")
    print(f"  Result:  {result['output']}")
    print(f"  Verify:  {base}^{exp} = {base**exp}, mod {modulus} = {base**exp % modulus}")
    print(f"  Gas:     {result['gas']:,}")

    # Larger example — RSA-2048 style
    big_base = 2**255 - 19
    big_exp = 2**128 + 7
    big_mod = 2**256 - 189
    result2 = PrecompileRegistry.call(0x05, {
        "base": big_base, "exponent": big_exp, "modulus": big_mod
    })
    print(f"\n  Big modexp (256-bit base, 128-bit exp):")
    print(f"  Result: {hex(result2['output'])[:32]}...")
    print(f"  Gas:    {result2['gas']:,}")

    # --- 0x06: ecAdd (alt_bn128) ---
    print("\n\n--- 0x06: ecAdd (alt_bn128 Point Addition) ---\n")

    # Add generator to itself: G + G = 2G
    gx, gy = ALT_BN128_G
    result = PrecompileRegistry.call(0x06, {
        "x1": gx, "y1": gy, "x2": gx, "y2": gy
    })
    print(f"  G = ({gx}, {gy})")
    print(f"  G + G = {result['output']}")
    print(f"  Gas: {result['gas']:,}")

    # Verify: 2*G should give same result
    double_g = ec_mul_generic(ALT_BN128_G, 2, ALT_BN128_P)
    print(f"  2*G  = {double_g}")
    print(f"  Match: {result['output'] == double_g}")

    # --- 0x07: ecMul (alt_bn128) ---
    print("\n\n--- 0x07: ecMul (alt_bn128 Scalar Multiplication) ---\n")

    scalar = 42
    result = PrecompileRegistry.call(0x07, {
        "x": gx, "y": gy, "scalar": scalar
    })
    print(f"  {scalar} * G = {result['output']}")
    print(f"  Gas: {result['gas']:,}")

    # Show that scalar mul is ~40x more expensive than addition
    print(f"\n  Cost comparison:")
    print(f"    ecAdd: {PRECOMPILE_GAS[0x06]:>8,} gas")
    print(f"    ecMul: {PRECOMPILE_GAS[0x07]:>8,} gas  "
          f"({PRECOMPILE_GAS[0x07] // PRECOMPILE_GAS[0x06]}x more)")
    print(f"  (Scalar mul requires ~256 point additions internally)")

    # --- 0x08: ecPairing ---
    print("\n\n--- 0x08: ecPairing (Bilinear Pairing Check) ---\n")

    # Simplified pairing demonstration
    # In ZK-SNARKs, pairings verify: e(A, B) * e(C, D) == 1
    print(f"  Pairing check: e(A1, B1) * e(A2, B2) == 1 ?")
    print(f"  (Simplified — real pairing uses F_p^12 tower arithmetic)\n")

    # Construct pairs that satisfy our simplified check
    pairs = [
        (ALT_BN128_G, ALT_BN128_N - 1),  # These cancel out
        (ALT_BN128_G, 1),                  # in our simplified model
    ]
    result = PrecompileRegistry.call(0x08, {"pairs": pairs})
    n_pairs = len(pairs)
    gas = PRECOMPILE_GAS[0x08] + 34_000 * n_pairs
    print(f"  Pairs: {n_pairs}")
    print(f"  Result: {result['output']} (True = pairing check passed)")
    print(f"  Gas: {gas:,} (base {PRECOMPILE_GAS[0x08]:,} + "
          f"{34_000:,} per pair)")

    print(f"\n  Use case: ZK-SNARK proof verification on-chain")
    print(f"  A Groth16 proof verification typically needs 1 ecPairing call")
    print(f"  with 3-4 pairs = ~{45_000 + 34_000 * 4:,} gas total")

    # --- 0x09: blake2f ---
    print("\n\n--- 0x09: blake2f (BLAKE2b Compression) ---\n")

    result = PrecompileRegistry.call(0x09, {
        "rounds": 12, "h": b'\x00' * 64, "m": b"Zcash interop",
        "t": b'\x00' * 16, "final_flag": True
    })
    print(f"  Input:  \"Zcash interop\" (12 rounds)")
    print(f"  Output: {result['output'][:32]}...")
    print(f"  Gas:    {result['gas']:,} (12 rounds x {PRECOMPILE_GAS[0x09]:,})")
    print(f"  Use case: Zcash bridge verification on Ethereum")

    # --- Summary ---
    print("\n\n--- Why Precompiles Exist ---\n")

    print(f"  ┌──────────────────────────────────────────────────────────────┐")
    print(f"  │ PROBLEM: Some operations are too expensive in EVM bytecode  │")
    print(f"  │                                                            │")
    print(f"  │ SHA-256 in EVM bytecode:  ~16,000 gas                      │")
    print(f"  │ SHA-256 as precompile:        ~72 gas  (222x cheaper)      │")
    print(f"  │                                                            │")
    print(f"  │ ecMul in EVM bytecode:   ~500,000 gas                      │")
    print(f"  │ ecMul as precompile:        6,000 gas  (83x cheaper)       │")
    print(f"  │                                                            │")
    print(f"  │ SOLUTION: Implement critical crypto as native code at       │")
    print(f"  │ fixed addresses. The EVM CALLs them like regular contracts  │")
    print(f"  │ but they execute compiled code, not EVM bytecode.           │")
    print(f"  │                                                            │")
    print(f"  │ Adding new precompiles requires a hard fork — that's why    │")
    print(f"  │ there are only 9 (as of Cancun). Each must justify the     │")
    print(f"  │ added complexity to all Ethereum clients.                   │")
    print(f"  └──────────────────────────────────────────────────────────────┘")

    print("\n" + "=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
