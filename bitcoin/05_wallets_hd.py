"""
TITLE: HD Wallets (BIP-32 Hierarchical Deterministic Key Derivation)
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    A BIP-32 hierarchical deterministic wallet that derives an entire tree of
    private/public keypairs from a single master seed. Uses HMAC-SHA512 for
    key derivation with support for hardened and normal child keys.

KEY CONCEPTS:
    - Master key generation from seed via HMAC-SHA512
    - Child key derivation (hardened vs normal)
    - Derivation paths (m/44'/0'/0'/0/N) for organized key hierarchies
    - One seed → unlimited addresses (deterministic and recoverable)

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - core/02_public_key_crypto.py (elliptic curve math)

REAL-WORLD RELEVANCE:
    Every modern Bitcoin wallet (Electrum, Ledger, Trezor) uses BIP-32 HD
    derivation. Users back up a single seed phrase and can regenerate all
    their addresses. BIP-44 standardizes paths like m/44'/0'/0'/0/N.
"""

import hashlib  # For SHA-256 and SHA-512 in HMAC and address generation
import hmac     # For HMAC-SHA512 key derivation
import struct   # For packing 32-bit integers into bytes
import os       # For generating random seed bytes

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# --- secp256k1 curve parameters ---
# The elliptic curve used by Bitcoin: y^2 = x^3 + 7 (mod p)
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F  # Field prime
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141  # Curve order
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798  # Generator x
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8  # Generator y
G = (GX, GY)  # Generator point on the curve

# BIP-32 uses this key for the initial HMAC when generating master keys
BIP32_SEED_KEY = b"Bitcoin seed"

# Hardened derivation starts at index 2^31 (0x80000000)
# Hardened keys cannot be used to derive parent keys, adding security
HARDENED_OFFSET = 0x80000000

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Modular arithmetic helpers for elliptic curve math ---

def mod_inverse(a, m):
    """Extended Euclidean algorithm for modular inverse: a^(-1) mod m."""
    if a < 0:
        a = a % m  # Ensure positive input
    g, x, _ = _extended_gcd(a, m)
    if g != 1:
        raise ValueError("No modular inverse exists")
    return x % m


def _extended_gcd(a, b):
    """Compute gcd and Bezout coefficients: ax + by = gcd(a,b)."""
    if a == 0:
        return b, 0, 1
    g, x1, y1 = _extended_gcd(b % a, a)
    return g, y1 - (b // a) * x1, x1


# --- Elliptic curve point operations on secp256k1 ---

def point_add(p1, p2):
    """Add two points on secp256k1. None represents the point at infinity."""
    if p1 is None:
        return p2  # Infinity + P = P
    if p2 is None:
        return p1  # P + Infinity = P

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and y1 != y2:
        return None  # P + (-P) = Infinity (point and its inverse)

    if x1 == x2 and y1 == y2:
        # Point doubling: tangent line slope = (3x^2 + a) / (2y)
        # For secp256k1, a=0, so slope = 3x^2 / 2y
        lam = (3 * x1 * x1 * mod_inverse(2 * y1, P)) % P
    else:
        # Point addition: slope = (y2 - y1) / (x2 - x1)
        lam = ((y2 - y1) * mod_inverse(x2 - x1, P)) % P

    # New point coordinates from the slope
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def scalar_multiply(k, point):
    """Multiply point by scalar k using double-and-add algorithm."""
    result = None  # Start at point at infinity (identity element)
    addend = point

    while k > 0:
        if k & 1:  # If current bit is 1, add the current power of the point
            result = point_add(result, addend)
        addend = point_add(addend, addend)  # Double the point each iteration
        k >>= 1  # Move to next bit
    return result


# --- Serialization helpers ---

def serialize_public_key(point, compressed=True):
    """Serialize an EC point to bytes. Compressed format uses 33 bytes."""
    if point is None:
        raise ValueError("Cannot serialize point at infinity")
    x, y = point
    if compressed:
        # Prefix 02 if y is even, 03 if y is odd — saves 32 bytes vs uncompressed
        prefix = b'\x02' if y % 2 == 0 else b'\x03'
        return prefix + x.to_bytes(32, 'big')
    else:
        # Prefix 04 followed by full x and y coordinates (65 bytes total)
        return b'\x04' + x.to_bytes(32, 'big') + y.to_bytes(32, 'big')


def private_key_to_bytes(key_int):
    """Convert a private key integer to 32 bytes big-endian."""
    return key_int.to_bytes(32, 'big')


def bytes_to_private_key(key_bytes):
    """Convert 32 bytes to a private key integer."""
    return int.from_bytes(key_bytes, 'big')


# --- Hash functions used in Bitcoin address generation ---

def sha256(data):
    """Compute SHA-256 hash."""
    return hashlib.sha256(data).digest()


def hash160(data):
    """HASH160 = RIPEMD-160(SHA-256(data)) — used for Bitcoin addresses."""
    return hashlib.new('ripemd160', sha256(data)).digest()


def double_sha256(data):
    """Double SHA-256, used for Bitcoin checksums."""
    return sha256(sha256(data))


# --- Base58Check encoding for Bitcoin addresses ---

# Base58 alphabet: like Base64 but without 0/O/I/l to avoid visual confusion
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def base58check_encode(version_byte, payload):
    """Encode payload with version byte and 4-byte checksum in Base58."""
    versioned = version_byte + payload  # Prepend version byte
    checksum = double_sha256(versioned)[:4]  # First 4 bytes of double-SHA256
    data = versioned + checksum

    # Convert bytes to a big integer, then repeatedly divide by 58
    num = int.from_bytes(data, 'big')
    result = []
    while num > 0:
        num, remainder = divmod(num, 58)
        result.append(BASE58_ALPHABET[remainder])

    # Preserve leading zero bytes as '1' characters (Bitcoin convention)
    for byte in data:
        if byte == 0:
            result.append('1')
        else:
            break

    return ''.join(reversed(result))


# --- BIP-32 HD Wallet implementation ---

class HDKey:
    """Represents a node in the BIP-32 key hierarchy tree."""

    def __init__(self, private_key, chain_code, depth=0, parent_fingerprint=b'\x00\x00\x00\x00', child_index=0):
        self.private_key = private_key          # 32-byte private key integer
        self.chain_code = chain_code            # 32-byte chain code (extra entropy for derivation)
        self.depth = depth                      # How many derivation steps from master (0 = master)
        self.parent_fingerprint = parent_fingerprint  # First 4 bytes of parent's HASH160(pubkey)
        self.child_index = child_index          # Which child number this is

    @property
    def public_key_point(self):
        """Compute the public key point by multiplying generator by private key."""
        return scalar_multiply(self.private_key, G)

    @property
    def public_key_bytes(self):
        """Get compressed public key bytes (33 bytes)."""
        return serialize_public_key(self.public_key_point)

    @property
    def fingerprint(self):
        """First 4 bytes of HASH160 of compressed public key — identifies this key."""
        return hash160(self.public_key_bytes)[:4]

    def derive_child(self, index):
        """
        Derive a child key at the given index.

        If index >= HARDENED_OFFSET, this is a hardened derivation.
        Hardened: HMAC-SHA512(chain_code, 0x00 || private_key || index)
        Normal:   HMAC-SHA512(chain_code, public_key || index)
        """
        if index >= HARDENED_OFFSET:
            # Hardened derivation — uses private key directly
            # This prevents public-key-only wallets from deriving children,
            # adding a security boundary in the key tree
            data = b'\x00' + private_key_to_bytes(self.private_key) + struct.pack('>I', index)
        else:
            # Normal derivation — uses compressed public key
            # Allows deriving child public keys from parent public key alone
            # (useful for watch-only wallets that receive but can't spend)
            data = self.public_key_bytes + struct.pack('>I', index)

        # HMAC-SHA512 produces 64 bytes: left half = key material, right half = new chain code
        hmac_result = hmac.new(self.chain_code, data, hashlib.sha512).digest()
        child_key_material = hmac_result[:32]  # First 32 bytes tweak the parent key
        child_chain_code = hmac_result[32:]    # Last 32 bytes become new chain code

        # Child private key = (parent_key + key_material) mod N
        # Addition mod curve order ensures result is a valid private key
        child_private_key = (self.private_key + bytes_to_private_key(child_key_material)) % N

        if child_private_key == 0:
            raise ValueError("Derived key is zero — extremely unlikely, skip this index")

        return HDKey(
            private_key=child_private_key,
            chain_code=child_chain_code,
            depth=self.depth + 1,
            parent_fingerprint=self.fingerprint,
            child_index=index,
        )

    def derive_path(self, path):
        """
        Derive a key from a BIP-32 path string like "m/44'/0'/0'/0/0".

        Apostrophe (') means hardened derivation.
        Each number between slashes is one derivation step deeper in the tree.
        """
        if not path.startswith("m"):
            raise ValueError(f"Path must start with 'm', got: {path}")

        key = self  # Start from the current key (should be master for full paths)
        if path == "m":
            return key

        # Split "m/44'/0'/0'/0/0" into ["44'", "0'", "0'", "0", "0"]
        components = path.split("/")[1:]  # Skip the 'm' prefix

        for component in components:
            if component.endswith("'"):
                # Hardened: strip apostrophe and add offset
                index = int(component[:-1]) + HARDENED_OFFSET
            else:
                # Normal derivation
                index = int(component)
            key = key.derive_child(index)

        return key

    def get_address(self):
        """Generate a Bitcoin P2PKH address from this key's public key."""
        # P2PKH: version byte 0x00 for mainnet, then HASH160 of compressed pubkey
        pubkey_hash = hash160(self.public_key_bytes)
        return base58check_encode(b'\x00', pubkey_hash)


def master_key_from_seed(seed_bytes):
    """
    Generate BIP-32 master key from seed bytes.

    HMAC-SHA512 with key "Bitcoin seed" produces:
    - Left 32 bytes: master private key
    - Right 32 bytes: master chain code
    """
    hmac_result = hmac.new(BIP32_SEED_KEY, seed_bytes, hashlib.sha512).digest()
    master_private = bytes_to_private_key(hmac_result[:32])
    master_chain_code = hmac_result[32:]

    if master_private == 0 or master_private >= N:
        raise ValueError("Invalid master key — regenerate with different seed")

    return HDKey(private_key=master_private, chain_code=master_chain_code)


def format_path_description(path):
    """Explain what a BIP-44 derivation path means in human terms."""
    parts = path.split("/")
    if len(parts) < 2:
        return "Master key"

    descriptions = {
        "44'": "purpose=BIP-44 (multi-account)",
        "0'": "coin=Bitcoin",
        "1'": "coin=Bitcoin Testnet",
        "60'": "coin=Ethereum",
    }

    explanations = []
    labels = ["purpose", "coin_type", "account", "change", "address_index"]
    for i, part in enumerate(parts[1:]):  # Skip 'm'
        label = labels[i] if i < len(labels) else f"level_{i}"
        desc = descriptions.get(part, part)
        explanations.append(f"{label}={desc}")

    return " / ".join(explanations)


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of HD wallet key derivation."""
    print("=" * 72)
    print("  HD WALLETS: One Seed → Unlimited Addresses (BIP-32)")
    print("=" * 72)

    # --- Step 1: Generate a deterministic seed ---
    # In real wallets, this comes from a 12/24-word mnemonic phrase (BIP-39)
    # We use a fixed seed for reproducible output
    seed = bytes.fromhex(
        "000102030405060708090a0b0c0d0e0f"
        "101112131415161718191a1b1c1d1e1f"
    )
    print(f"\n  Seed (32 bytes): {seed.hex()}")
    print(f"  (In practice, derived from a 24-word mnemonic phrase)")

    # --- Step 2: Generate master key ---
    print("\n" + "─" * 72)
    print("  STEP 1: Generate Master Key")
    print("─" * 72)

    master = master_key_from_seed(seed)

    print(f"\n  HMAC-SHA512(key='Bitcoin seed', data=seed)")
    print(f"  ├── Master Private Key : {private_key_to_bytes(master.private_key).hex()[:32]}...")
    print(f"  └── Master Chain Code  : {master.chain_code.hex()[:32]}...")
    print(f"\n  The chain code adds entropy to each derivation step,")
    print(f"  preventing related-key attacks between siblings.")

    # --- Step 3: Explain derivation path ---
    print("\n" + "─" * 72)
    print("  STEP 2: BIP-44 Derivation Path")
    print("─" * 72)

    path_base = "m/44'/0'/0'"
    print(f"""
  Path: m / 44' / 0' / 0' / 0 / N
        │    │     │     │    │   └── Address index (0, 1, 2, ...)
        │    │     │     │    └────── 0=external (receive), 1=internal (change)
        │    │     │     └─────────── Account number (0=first account)
        │    │     └───────────────── Coin type (0=Bitcoin, 60=Ethereum)
        │    └─────────────────────── Purpose (44=BIP-44 multi-account)
        └──────────────────────────── Master key

  Apostrophe (') = hardened derivation
    → Uses private key in HMAC (not public key)
    → Child public keys CANNOT be derived from parent public key
    → Protects against key leakage cascading up the tree
    """)

    # --- Step 4: Derive keys at hardened path ---
    print("─" * 72)
    print("  STEP 3: Hardened Derivation (m/44'/0'/0')")
    print("─" * 72)

    # Derive the account key step by step to show the process
    purpose_key = master.derive_child(44 + HARDENED_OFFSET)
    print(f"\n  m/44' (purpose):")
    print(f"    Private: {private_key_to_bytes(purpose_key.private_key).hex()[:24]}...")
    print(f"    Depth: {purpose_key.depth}, Index: 44' (hardened)")

    coin_key = purpose_key.derive_child(0 + HARDENED_OFFSET)
    print(f"\n  m/44'/0' (coin=Bitcoin):")
    print(f"    Private: {private_key_to_bytes(coin_key.private_key).hex()[:24]}...")
    print(f"    Depth: {coin_key.depth}, Index: 0' (hardened)")

    account_key = coin_key.derive_child(0 + HARDENED_OFFSET)
    print(f"\n  m/44'/0'/0' (account=0):")
    print(f"    Private: {private_key_to_bytes(account_key.private_key).hex()[:24]}...")
    print(f"    Depth: {account_key.depth}, Index: 0' (hardened)")

    # --- Step 5: Derive external chain ---
    print("\n" + "─" * 72)
    print("  STEP 4: Normal Derivation — External Address Chain")
    print("─" * 72)

    # 0 = external/receive, 1 = internal/change
    external_chain = account_key.derive_child(0)  # Normal (not hardened)
    print(f"\n  m/44'/0'/0'/0 (external chain — normal derivation):")
    print(f"    This level uses NORMAL derivation so watch-only wallets")
    print(f"    can derive public keys without knowing the private key.\n")

    # --- Step 6: Derive 5 receive addresses ---
    print("─" * 72)
    print("  STEP 5: Derive 5 Receive Addresses")
    print("─" * 72)

    addresses = []
    for i in range(5):
        child = external_chain.derive_child(i)
        addr = child.get_address()
        priv_hex = private_key_to_bytes(child.private_key).hex()
        pub_hex = child.public_key_bytes.hex()
        addresses.append((i, addr, priv_hex, pub_hex))

    print()
    for idx, addr, priv, pub in addresses:
        path = f"m/44'/0'/0'/0/{idx}"
        print(f"  ┌─ {path}")
        print(f"  │  Private: {priv[:16]}...{priv[-8:]}")
        print(f"  │  Public:  {pub[:16]}...{pub[-8:]}")
        print(f"  │  Address: {addr}")
        if idx < 4:
            print(f"  │")

    # --- Step 7: Show key independence ---
    print("\n" + "─" * 72)
    print("  KEY PROPERTIES")
    print("─" * 72)

    # Show that each key is completely different despite sequential derivation
    key0 = external_chain.derive_child(0)
    key1 = external_chain.derive_child(1)
    priv0 = private_key_to_bytes(key0.private_key).hex()
    priv1 = private_key_to_bytes(key1.private_key).hex()

    # Count differing hex chars to show keys are unrelated
    diffs = sum(1 for a, b in zip(priv0, priv1) if a != b)
    total = len(priv0)
    print(f"\n  Key at index 0: {priv0[:32]}...")
    print(f"  Key at index 1: {priv1[:32]}...")
    print(f"  Differing hex chars: {diffs}/{total} ({diffs*100//total}%)")
    print(f"  → Keys look completely unrelated (no pattern to exploit)")

    # --- Step 8: Demonstrate recoverability ---
    print("\n" + "─" * 72)
    print("  RECOVERABILITY: Same Seed → Same Addresses")
    print("─" * 72)

    # Re-derive from the same seed to prove determinism
    master2 = master_key_from_seed(seed)
    addr_original = master.derive_path("m/44'/0'/0'/0/0").get_address()
    addr_recovered = master2.derive_path("m/44'/0'/0'/0/0").get_address()

    print(f"\n  Original:  {addr_original}")
    print(f"  Recovered: {addr_recovered}")
    print(f"  Match: {'✓ YES — identical!' if addr_original == addr_recovered else '✗ NO — bug!'}")
    print(f"\n  → Back up seed once, recover ALL addresses forever.")

    # --- Step 9: Show different accounts ---
    print("\n" + "─" * 72)
    print("  MULTIPLE ACCOUNTS: Separate Funds, Same Seed")
    print("─" * 72)

    print()
    for acct in range(3):
        path = f"m/44'/0'/{acct}'/0/0"
        key = master.derive_path(path)
        addr = key.get_address()
        print(f"  Account {acct}: {path} → {addr}")

    print(f"\n  → Each account is cryptographically isolated.")
    print(f"     Compromising account 0 doesn't reveal account 1's keys.")

    print("\n" + "=" * 72)
    print("  HD wallets: one seed phrase protects unlimited Bitcoin addresses.")
    print("=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
