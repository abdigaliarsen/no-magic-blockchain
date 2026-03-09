"""
TITLE: Segregated Witness (SegWit)
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    A comparison of legacy and SegWit transaction formats, showing how SegWit
    separates witness (signature) data from the transaction structure. Demonstrates
    weight unit calculations and the malleability fix.

KEY CONCEPTS:
    - Legacy vs SegWit transaction structure
    - Weight units: non-witness bytes * 4 + witness bytes * 1
    - Transaction malleability: legacy txids include signatures, SegWit txids don't
    - Witness commitment: signatures moved to a separate witness field

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - core/03_digital_signatures.py (ECDSA signatures)
    - bitcoin/01_utxo_model.py (transaction inputs/outputs)

REAL-WORLD RELEVANCE:
    SegWit (BIP-141) activated on Bitcoin in August 2017. It fixed transaction
    malleability (enabling Lightning Network), increased effective block capacity
    from ~1MB to ~2.3MB via the weight system, and reduced fees for SegWit users.
"""

import hashlib  # For SHA-256 and double-SHA256 hashing
import struct   # For packing integers into little-endian bytes
import os       # For generating random bytes in key generation

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# secp256k1 elliptic curve parameters (same curve Bitcoin uses)
SECP256K1_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
SECP256K1_GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
SECP256K1_GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
SECP256K1_G = (SECP256K1_GX, SECP256K1_GY)

# SegWit marker and flag bytes that identify a SegWit transaction
SEGWIT_MARKER = 0x00  # Must be zero — legacy parser sees zero inputs and rejects
SEGWIT_FLAG = 0x01    # Version flag, currently always 1

# Weight limit per block: 4,000,000 weight units (replaces the old 1MB limit)
MAX_BLOCK_WEIGHT = 4_000_000

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Elliptic curve helpers (minimal, for signature simulation) ---

def _mod_inverse(a, m):
    """Modular multiplicative inverse using extended Euclidean algorithm."""
    if a < 0:
        a = a % m
    g, x, _ = _ext_gcd(a, m)
    if g != 1:
        raise ValueError("No inverse")
    return x % m


def _ext_gcd(a, b):
    """Extended GCD: returns (gcd, x, y) such that ax + by = gcd."""
    if a == 0:
        return b, 0, 1
    g, x1, y1 = _ext_gcd(b % a, a)
    return g, y1 - (b // a) * x1, x1


def _point_add(p1, p2):
    """Add two points on secp256k1."""
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and y1 != y2:
        return None
    if x1 == x2:
        lam = (3 * x1 * x1 * _mod_inverse(2 * y1, SECP256K1_P)) % SECP256K1_P
    else:
        lam = ((y2 - y1) * _mod_inverse(x2 - x1, SECP256K1_P)) % SECP256K1_P
    x3 = (lam * lam - x1 - x2) % SECP256K1_P
    y3 = (lam * (x1 - x3) - y1) % SECP256K1_P
    return (x3, y3)


def _scalar_mult(k, point):
    """Scalar multiplication using double-and-add."""
    result = None
    addend = point
    while k > 0:
        if k & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        k >>= 1
    return result


def _compress_pubkey(point):
    """Compress a public key point to 33 bytes."""
    x, y = point
    prefix = b'\x02' if y % 2 == 0 else b'\x03'
    return prefix + x.to_bytes(32, 'big')


# --- Hash helpers ---

def sha256(data):
    """Single SHA-256."""
    return hashlib.sha256(data).digest()


def double_sha256(data):
    """Double SHA-256, used for Bitcoin txids."""
    return sha256(sha256(data))


def hash160(data):
    """RIPEMD-160(SHA-256(data)) — used for Bitcoin addresses."""
    return hashlib.new('ripemd160', sha256(data)).digest()


# --- Simple ECDSA signature (deterministic for reproducibility) ---

def sign_message(private_key, message_hash):
    """Sign a 32-byte hash with a private key. Returns (r, s) tuple."""
    # Use HMAC-based deterministic k (simplified RFC 6979)
    k_bytes = hashlib.sha256(private_key.to_bytes(32, 'big') + message_hash).digest()
    k = int.from_bytes(k_bytes, 'big') % SECP256K1_N
    if k == 0:
        k = 1  # Avoid zero (astronomically unlikely)

    # r = x-coordinate of k*G mod N
    point = _scalar_mult(k, SECP256K1_G)
    r = point[0] % SECP256K1_N

    # s = k^(-1) * (hash + r * private_key) mod N
    z = int.from_bytes(message_hash, 'big')
    s = (_mod_inverse(k, SECP256K1_N) * (z + r * private_key)) % SECP256K1_N

    return (r, s)


def serialize_signature(r, s):
    """Encode signature as DER format bytes (variable length)."""
    # DER encoding: 0x30 [total-len] 0x02 [r-len] [r] 0x02 [s-len] [s]
    def encode_int(value):
        b = value.to_bytes((value.bit_length() + 7) // 8, 'big')
        if b[0] & 0x80:  # Add zero byte if high bit set (DER sign convention)
            b = b'\x00' + b
        return b

    r_bytes = encode_int(r)
    s_bytes = encode_int(s)

    # 0x30 = SEQUENCE tag, 0x02 = INTEGER tag
    der = b'\x30' + bytes([len(r_bytes) + len(s_bytes) + 4])
    der += b'\x02' + bytes([len(r_bytes)]) + r_bytes
    der += b'\x02' + bytes([len(s_bytes)]) + s_bytes
    return der


# --- Transaction structures ---

class TxInput:
    """A transaction input referencing a previous output."""

    def __init__(self, prev_txid, prev_index, script_sig=b'', sequence=0xFFFFFFFF):
        self.prev_txid = prev_txid      # 32 bytes: hash of the transaction being spent
        self.prev_index = prev_index    # Which output of that transaction
        self.script_sig = script_sig    # Unlock script (signature + pubkey in legacy)
        self.sequence = sequence        # Usually 0xFFFFFFFF (final)

    def serialize_for_txid(self, include_script=True):
        """Serialize this input for transaction ID calculation."""
        data = self.prev_txid[::-1]  # Bitcoin uses internal byte order (reversed)
        data += struct.pack('<I', self.prev_index)  # Output index, little-endian
        if include_script:
            # VarInt length prefix + script content
            data += _varint(len(self.script_sig)) + self.script_sig
        else:
            data += _varint(0)  # Empty script for signing
        data += struct.pack('<I', self.sequence)
        return data


class TxOutput:
    """A transaction output with value and locking script."""

    def __init__(self, value_satoshis, script_pubkey):
        self.value = value_satoshis      # Amount in satoshis (1 BTC = 100,000,000 sat)
        self.script_pubkey = script_pubkey  # Lock script (defines who can spend)

    def serialize(self):
        """Serialize this output."""
        data = struct.pack('<q', self.value)  # 8 bytes, little-endian signed
        data += _varint(len(self.script_pubkey)) + self.script_pubkey
        return data


def _varint(n):
    """Encode an integer as a Bitcoin CompactSize/VarInt."""
    if n < 0xFD:
        return struct.pack('<B', n)
    elif n <= 0xFFFF:
        return b'\xFD' + struct.pack('<H', n)
    elif n <= 0xFFFFFFFF:
        return b'\xFE' + struct.pack('<I', n)
    else:
        return b'\xFF' + struct.pack('<Q', n)


class LegacyTransaction:
    """A legacy (pre-SegWit) Bitcoin transaction."""

    def __init__(self, version, inputs, outputs, locktime=0):
        self.version = version
        self.inputs = inputs
        self.outputs = outputs
        self.locktime = locktime

    def serialize(self):
        """Serialize the entire transaction (including signatures)."""
        data = struct.pack('<I', self.version)  # 4-byte version
        data += _varint(len(self.inputs))       # Input count
        for inp in self.inputs:
            data += inp.serialize_for_txid()    # Each input with its scriptSig
        data += _varint(len(self.outputs))      # Output count
        for out in self.outputs:
            data += out.serialize()
        data += struct.pack('<I', self.locktime)  # 4-byte locktime
        return data

    def txid(self):
        """Transaction ID = double-SHA256 of serialized tx, displayed reversed."""
        return double_sha256(self.serialize())[::-1]  # Reversed for display

    def size(self):
        """Transaction size in bytes."""
        return len(self.serialize())

    def weight(self):
        """Legacy transactions: weight = size * 4 (all bytes are non-witness)."""
        return self.size() * 4

    def vsize(self):
        """Virtual size = weight / 4 (for fee calculation)."""
        return self.weight() // 4


class SegWitTransaction:
    """A SegWit (BIP-141) Bitcoin transaction with separate witness data."""

    def __init__(self, version, inputs, outputs, witnesses, locktime=0):
        self.version = version
        self.inputs = inputs
        self.outputs = outputs
        self.witnesses = witnesses  # List of witness stacks (one per input)
        self.locktime = locktime

    def serialize_no_witness(self):
        """Serialize WITHOUT witness data — this is what the txid hashes.
        This is the key insight: signatures are excluded from the txid!"""
        data = struct.pack('<I', self.version)
        data += _varint(len(self.inputs))
        for inp in self.inputs:
            # Inputs have EMPTY scriptSig in SegWit — sig is in witness instead
            data += inp.serialize_for_txid()
        data += _varint(len(self.outputs))
        for out in self.outputs:
            data += out.serialize()
        data += struct.pack('<I', self.locktime)
        return data

    def serialize_with_witness(self):
        """Full serialization WITH witness data — used for network transmission."""
        data = struct.pack('<I', self.version)
        data += bytes([SEGWIT_MARKER, SEGWIT_FLAG])  # SegWit flag bytes
        data += _varint(len(self.inputs))
        for inp in self.inputs:
            data += inp.serialize_for_txid()
        data += _varint(len(self.outputs))
        for out in self.outputs:
            data += out.serialize()

        # Witness data comes after outputs, before locktime
        for witness_stack in self.witnesses:
            data += _varint(len(witness_stack))  # Number of items in this witness
            for item in witness_stack:
                data += _varint(len(item)) + item  # Each witness item

        data += struct.pack('<I', self.locktime)
        return data

    def txid(self):
        """SegWit txid hashes the NON-witness serialization.
        This means changing the signature does NOT change the txid!"""
        return double_sha256(self.serialize_no_witness())[::-1]

    def wtxid(self):
        """Witness txid includes everything — used for witness commitment."""
        return double_sha256(self.serialize_with_witness())[::-1]

    def size(self):
        """Full size including witness data."""
        return len(self.serialize_with_witness())

    def non_witness_size(self):
        """Size of non-witness data."""
        return len(self.serialize_no_witness())

    def weight(self):
        """Weight = non-witness bytes * 4 + witness bytes * 1.
        This gives a 75% discount to witness data, incentivizing SegWit adoption."""
        full = self.serialize_with_witness()
        base = self.serialize_no_witness()
        witness_bytes = len(full) - len(base)
        non_witness_bytes = len(base)
        return non_witness_bytes * 4 + witness_bytes * 1

    def vsize(self):
        """Virtual size = ceil(weight / 4). Used for fee calculation."""
        w = self.weight()
        return (w + 3) // 4  # Ceiling division


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Demonstrate legacy vs SegWit transaction formats."""
    print("=" * 72)
    print("  SEGREGATED WITNESS (SegWit): Fixing Transaction Malleability")
    print("=" * 72)

    # --- Generate a keypair for signing ---
    private_key = int.from_bytes(sha256(b"demo-segwit-key"), 'big') % SECP256K1_N
    public_key_point = _scalar_mult(private_key, SECP256K1_G)
    compressed_pubkey = _compress_pubkey(public_key_point)
    pubkey_hash = hash160(compressed_pubkey)

    # --- Create a fake previous transaction to spend ---
    prev_txid = double_sha256(b"previous-transaction")

    # --- P2PKH locking script: OP_DUP OP_HASH160 <pubkeyhash> OP_EQUALVERIFY OP_CHECKSIG ---
    script_pubkey = (
        b'\x76'          # OP_DUP
        + b'\xa9'        # OP_HASH160
        + b'\x14'        # Push 20 bytes
        + pubkey_hash    # The public key hash
        + b'\x88'        # OP_EQUALVERIFY
        + b'\xac'        # OP_CHECKSIG
    )

    # --- P2WPKH locking script (SegWit): OP_0 <20-byte-pubkeyhash> ---
    # Much simpler! Just version byte + pubkey hash
    script_pubkey_segwit = b'\x00\x14' + pubkey_hash  # OP_0, push 20 bytes

    # ===================================================================
    # PART 1: Legacy Transaction
    # ===================================================================
    print("\n" + "─" * 72)
    print("  PART 1: Legacy Transaction (Pre-SegWit)")
    print("─" * 72)

    # Sign the transaction (simplified — real Bitcoin signs a specific sighash)
    msg_hash = double_sha256(b"legacy-sighash-data")
    r, s = sign_message(private_key, msg_hash)
    der_sig = serialize_signature(r, s)
    sighash_type = b'\x01'  # SIGHASH_ALL

    # scriptSig = <signature + sighash_type> <compressed_pubkey>
    sig_with_hashtype = der_sig + sighash_type
    script_sig = (
        bytes([len(sig_with_hashtype)]) + sig_with_hashtype
        + bytes([len(compressed_pubkey)]) + compressed_pubkey
    )

    legacy_input = TxInput(prev_txid, 0, script_sig=script_sig)
    legacy_output = TxOutput(50000, script_pubkey)  # 0.0005 BTC

    legacy_tx = LegacyTransaction(
        version=1,
        inputs=[legacy_input],
        outputs=[legacy_output],
    )

    legacy_txid = legacy_tx.txid().hex()

    print(f"\n  ┌─────────────────────────────────────────────────────────────┐")
    print(f"  │  LEGACY TRANSACTION                                        │")
    print(f"  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │  Version: 1                                                │")
    print(f"  │  Input:                                                    │")
    print(f"  │    prev_txid: {prev_txid.hex()[:24]}...      │")
    print(f"  │    scriptSig: <{len(script_sig)} bytes: sig + pubkey>               │")
    print(f"  │              ↑ SIGNATURE IS HERE (inside the tx)           │")
    print(f"  │  Output:                                                   │")
    print(f"  │    value: 50,000 sat                                       │")
    print(f"  │    script: P2PKH                                           │")
    print(f"  │  Locktime: 0                                               │")
    print(f"  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │  Size:   {legacy_tx.size():>4} bytes                                     │")
    print(f"  │  Weight: {legacy_tx.weight():>4} WU  (size × 4, all non-witness)         │")
    print(f"  │  vSize:  {legacy_tx.vsize():>4} vbytes                                   │")
    print(f"  │  TxID:   {legacy_txid[:24]}...              │")
    print(f"  └─────────────────────────────────────────────────────────────┘")

    # ===================================================================
    # PART 2: SegWit Transaction
    # ===================================================================
    print("\n" + "─" * 72)
    print("  PART 2: SegWit Transaction (P2WPKH)")
    print("─" * 72)

    # SegWit input has EMPTY scriptSig — signature goes in witness
    segwit_input = TxInput(prev_txid, 0, script_sig=b'')
    segwit_output = TxOutput(50000, script_pubkey_segwit)

    # Witness stack for P2WPKH: [signature, compressed_pubkey]
    witness_stack = [sig_with_hashtype, compressed_pubkey]

    segwit_tx = SegWitTransaction(
        version=2,
        inputs=[segwit_input],
        outputs=[segwit_output],
        witnesses=[witness_stack],
    )

    segwit_txid = segwit_tx.txid().hex()
    segwit_wtxid = segwit_tx.wtxid().hex()

    print(f"\n  ┌─────────────────────────────────────────────────────────────┐")
    print(f"  │  SEGWIT TRANSACTION                                        │")
    print(f"  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │  Version: 2                                                │")
    print(f"  │  Marker: 0x00  Flag: 0x01  (SegWit identifiers)           │")
    print(f"  │  Input:                                                    │")
    print(f"  │    prev_txid: {prev_txid.hex()[:24]}...      │")
    print(f"  │    scriptSig: <EMPTY>  ← signature moved to witness       │")
    print(f"  │  Output:                                                   │")
    print(f"  │    value: 50,000 sat                                       │")
    print(f"  │    script: P2WPKH (OP_0 + pubkeyhash)                     │")
    print(f"  │  Witness:                                                  │")
    print(f"  │    [0] signature: <{len(sig_with_hashtype)} bytes>                          │")
    print(f"  │    [1] pubkey:    <{len(compressed_pubkey)} bytes>                          │")
    print(f"  │              ↑ SIGNATURE IS HERE (separate from tx body)   │")
    print(f"  │  Locktime: 0                                               │")
    print(f"  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │  Full Size: {segwit_tx.size():>4} bytes  (with witness)                  │")
    print(f"  │  Base Size: {segwit_tx.non_witness_size():>4} bytes  (without witness)               │")
    print(f"  │  Weight:    {segwit_tx.weight():>4} WU  (base×4 + witness×1)             │")
    print(f"  │  vSize:     {segwit_tx.vsize():>4} vbytes                                │")
    print(f"  │  TxID:  {segwit_txid[:24]}...               │")
    print(f"  │  WTxID: {segwit_wtxid[:24]}...               │")
    print(f"  └─────────────────────────────────────────────────────────────┘")

    # ===================================================================
    # PART 3: Weight comparison
    # ===================================================================
    print("\n" + "─" * 72)
    print("  PART 3: Weight & Fee Comparison")
    print("─" * 72)

    print(f"""
  Weight formula: non_witness_bytes × 4 + witness_bytes × 1

  Legacy:
    All {legacy_tx.size()} bytes are non-witness
    Weight = {legacy_tx.size()} × 4 = {legacy_tx.weight()} WU
    vSize  = {legacy_tx.weight()} / 4 = {legacy_tx.vsize()} vbytes

  SegWit:
    Base (non-witness): {segwit_tx.non_witness_size()} bytes
    Witness: {segwit_tx.size() - segwit_tx.non_witness_size()} bytes (discounted!)
    Weight = {segwit_tx.non_witness_size()} × 4 + {segwit_tx.size() - segwit_tx.non_witness_size()} × 1 = {segwit_tx.weight()} WU
    vSize  = ⌈{segwit_tx.weight()} / 4⌉ = {segwit_tx.vsize()} vbytes

  Fee savings: {100 - segwit_tx.vsize() * 100 // legacy_tx.vsize()}% smaller vSize → lower fees!

  Block capacity (at {MAX_BLOCK_WEIGHT:,} WU limit):
    Legacy-only: ~{MAX_BLOCK_WEIGHT // legacy_tx.weight()} transactions
    SegWit-only: ~{MAX_BLOCK_WEIGHT // segwit_tx.weight()} transactions
    → SegWit effectively increases block capacity""")

    # ===================================================================
    # PART 4: Transaction malleability fix
    # ===================================================================
    print("\n" + "─" * 72)
    print("  PART 4: Transaction Malleability Fix")
    print("─" * 72)

    print(f"\n  The Problem: In legacy transactions, a third party can modify")
    print(f"  the signature encoding without invalidating it. This changes")
    print(f"  the txid, breaking chains of unconfirmed transactions.")

    # Show legacy malleability: same message, different signature → different txid
    print(f"\n  --- Legacy: Signature Change → TxID Change ---")
    print(f"\n  Original signature (DER):  {der_sig.hex()[:32]}...")
    print(f"  Original TxID:             {legacy_txid[:32]}...")

    # Simulate a "malleated" signature (in reality, DER has equivalent encodings)
    # We'll create a second valid-looking signature with different encoding
    r2, s2 = r, SECP256K1_N - s  # Negate s — both (r,s) and (r, N-s) are valid ECDSA sigs
    der_sig_malleated = serialize_signature(r2, s2)
    sig_malleated = der_sig_malleated + sighash_type

    script_sig_malleated = (
        bytes([len(sig_malleated)]) + sig_malleated
        + bytes([len(compressed_pubkey)]) + compressed_pubkey
    )

    legacy_input_mal = TxInput(prev_txid, 0, script_sig=script_sig_malleated)
    legacy_tx_mal = LegacyTransaction(
        version=1, inputs=[legacy_input_mal], outputs=[legacy_output]
    )
    legacy_txid_mal = legacy_tx_mal.txid().hex()

    print(f"\n  Malleated signature (s → N-s, still valid!):")
    print(f"  Malleated signature (DER): {der_sig_malleated.hex()[:32]}...")
    print(f"  Malleated TxID:            {legacy_txid_mal[:32]}...")
    print(f"\n  ✗ TxIDs are DIFFERENT! Same payment, different ID.")
    print(f"    A third party changed the txid without the private key!")

    # Show SegWit fix
    print(f"\n  --- SegWit: Signature Change → TxID Unchanged ---")

    segwit_txid_original = segwit_tx.txid().hex()

    # Same transaction but with malleated witness
    witness_malleated = [sig_malleated, compressed_pubkey]
    segwit_tx_mal = SegWitTransaction(
        version=2,
        inputs=[TxInput(prev_txid, 0, script_sig=b'')],
        outputs=[segwit_output],
        witnesses=[witness_malleated],
    )
    segwit_txid_mal = segwit_tx_mal.txid().hex()
    segwit_wtxid_mal = segwit_tx_mal.wtxid().hex()

    print(f"\n  Original TxID:   {segwit_txid_original[:32]}...")
    print(f"  Malleated TxID:  {segwit_txid_mal[:32]}...")
    match = segwit_txid_original == segwit_txid_mal
    print(f"\n  ✓ TxIDs are {'IDENTICAL' if match else 'DIFFERENT'}! Malleability is fixed.")
    print(f"    Signature is in the witness, NOT in the txid hash.")

    print(f"\n  WTxID (includes witness) did change:")
    print(f"    Original WTxID:  {segwit_wtxid[:32]}...")
    print(f"    Malleated WTxID: {segwit_wtxid_mal[:32]}...")

    # ===================================================================
    # PART 5: Why this matters
    # ===================================================================
    print("\n" + "─" * 72)
    print("  WHY MALLEABILITY FIX MATTERS")
    print("─" * 72)
    print(f"""
  1. Lightning Network: Payment channels reference unconfirmed txids.
     If txids could change, the entire channel construct breaks.

  2. Chained transactions: If tx B spends from unconfirmed tx A and
     someone malleates tx A's id, tx B becomes invalid.

  3. Fee bumping (CPFP): Child-pays-for-parent relies on stable txids.

  SegWit solved this by moving signatures out of the txid calculation,
  making txids immutable once the transaction is created.
    """)

    print("=" * 72)
    print("  SegWit: smaller fees, more capacity, no malleability.")
    print("=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
