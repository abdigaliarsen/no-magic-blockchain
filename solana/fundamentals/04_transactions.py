"""
TITLE: Solana Transaction Format
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    The complete Solana transaction format from scratch — message construction
    (header, account keys, recent blockhash, compact instructions), transaction
    serialization, and signature verification using simplified ECDSA signing.

KEY CONCEPTS:
    - Message layout: header, account_keys, recent_blockhash, instructions
    - Compact instruction format: program_id_index, account_indexes, data
    - Account deduplication and ordering (signers first, then writable, then readonly)
    - Transaction signing and verification

PREREQUISITE SCRIPTS:
    - solana/01_accounts_model.py (account structure)
    - solana/03_programs.py (instruction format)
    - core/03_digital_signatures.py (ECDSA signing)

REAL-WORLD RELEVANCE:
    Every interaction with Solana — transfers, token swaps, NFT mints —
    is a transaction in this exact format. Wallets like Phantom serialize
    transactions this way before sending them to validators.
"""

import hashlib
import struct
import secrets

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Maximum number of accounts in a single transaction
MAX_ACCOUNTS = 64

# Maximum transaction size in bytes (real Solana: 1232 bytes)
MAX_TX_SIZE = 1232

# Maximum number of instructions per transaction
MAX_INSTRUCTIONS = 16

# Signature size in bytes (simplified — real Ed25519 is 64 bytes)
SIGNATURE_SIZE = 64

# secp256k1 curve parameters for simplified signing
# (same as core/03_digital_signatures.py — self-contained, no imports)
SECP256K1_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
SECP256K1_GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
SECP256K1_GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
SECP256K1_G = (SECP256K1_GX, SECP256K1_GY)

# Point at infinity — identity element for EC addition
INFINITY = None


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: Elliptic curve math (self-contained for zero-dependency requirement)
# ----------------------------------------------------------------------------

def mod_inv(a, m):
    """Modular inverse via Fermat's little theorem: a^(m-2) mod m."""
    return pow(a, m - 2, m)


def ec_add(p1, p2):
    """Add two points on the secp256k1 elliptic curve."""
    if p1 is INFINITY:
        return p2
    if p2 is INFINITY:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and y1 != y2:
        return INFINITY  # P + (-P) = O (point at infinity)

    if x1 == x2:
        # Point doubling: slope = (3*x1^2 + a) / (2*y1), where a=0 for secp256k1
        lam = (3 * x1 * x1 * mod_inv(2 * y1, SECP256K1_P)) % SECP256K1_P
    else:
        # Point addition: slope = (y2 - y1) / (x2 - x1)
        lam = ((y2 - y1) * mod_inv(x2 - x1, SECP256K1_P)) % SECP256K1_P

    x3 = (lam * lam - x1 - x2) % SECP256K1_P
    y3 = (lam * (x1 - x3) - y1) % SECP256K1_P
    return (x3, y3)


def ec_multiply(k, point):
    """Scalar multiplication using double-and-add algorithm."""
    result = INFINITY
    addend = point
    while k > 0:
        if k & 1:                   # If bit is set, add current point
            result = ec_add(result, addend)
        addend = ec_add(addend, addend)  # Double the point
        k >>= 1                     # Shift to next bit
    return result


def generate_keypair():
    """Generate an ECDSA keypair on secp256k1.

    Returns (private_key_int, public_key_point, pubkey_hex_string).
    """
    private_key = secrets.randbelow(SECP256K1_N - 1) + 1  # 1 <= k < N
    public_key = ec_multiply(private_key, SECP256K1_G)
    # Create a hex string representation of the public key
    pubkey_hex = format(public_key[0], '064x')[:44]  # 44-char address
    return private_key, public_key, pubkey_hex


def sign_message(private_key, message_bytes):
    """Sign a message using ECDSA on secp256k1.

    Returns (r, s) signature tuple.
    """
    # Hash the message to get a fixed-size digest
    z = int(hashlib.sha256(message_bytes).hexdigest(), 16)

    # Choose random k for each signature (critical for security)
    k = secrets.randbelow(SECP256K1_N - 1) + 1
    # R = k * G, r = R.x mod N
    R = ec_multiply(k, SECP256K1_G)
    r = R[0] % SECP256K1_N
    # s = k^(-1) * (z + r * private_key) mod N
    s = (mod_inv(k, SECP256K1_N) * (z + r * private_key)) % SECP256K1_N
    return (r, s)


def verify_signature(public_key_point, message_bytes, signature):
    """Verify an ECDSA signature.

    Returns True if the signature is valid.
    """
    r, s = signature
    z = int(hashlib.sha256(message_bytes).hexdigest(), 16)

    # Compute s_inv, u1, u2
    s_inv = mod_inv(s, SECP256K1_N)
    u1 = (z * s_inv) % SECP256K1_N
    u2 = (r * s_inv) % SECP256K1_N

    # Recover point: u1*G + u2*PubKey
    point = ec_add(ec_multiply(u1, SECP256K1_G),
                   ec_multiply(u2, public_key_point))

    if point is INFINITY:
        return False

    # Signature is valid if point.x mod N == r
    return point[0] % SECP256K1_N == r


# ----------------------------------------------------------------------------
# 2b: Compact encoding (Solana uses compact-u16 for array lengths)
# ----------------------------------------------------------------------------

def encode_compact_u16(value):
    """Encode an integer as Solana's compact-u16 format.

    Compact-u16 uses 1-3 bytes with a continuation bit scheme:
    - 0-127:       1 byte  (0xxxxxxx)
    - 128-16383:   2 bytes (1xxxxxxx 0xxxxxxx)
    - 16384-65535: 3 bytes (1xxxxxxx 1xxxxxxx xxxxxxxx)
    """
    if value < 0 or value > 65535:
        raise ValueError(f"compact-u16 range is 0..65535, got {value}")

    result = bytearray()
    while True:
        byte = value & 0x7F          # Take low 7 bits
        value >>= 7                  # Shift right
        if value > 0:
            byte |= 0x80            # Set continuation bit
            result.append(byte)
        else:
            result.append(byte)
            break
    return bytes(result)


def decode_compact_u16(data, offset=0):
    """Decode a compact-u16 from bytes. Returns (value, bytes_consumed)."""
    value = 0
    shift = 0
    consumed = 0
    while True:
        byte = data[offset + consumed]
        value |= (byte & 0x7F) << shift
        consumed += 1
        if byte & 0x80 == 0:        # No continuation bit — done
            break
        shift += 7
    return value, consumed


# ----------------------------------------------------------------------------
# 2c: Message — the unsigned part of a transaction
# ----------------------------------------------------------------------------

class MessageHeader:
    """Transaction message header — describes account key layout.

    The header tells the runtime how the account_keys array is partitioned:
    ┌──────────────────────────────────────────────────────┐
    │ [0..num_signers)          = required signers         │
    │ [0..num_readonly_signed)  = readonly + signed        │
    │ [num_signers..end)        = non-signers              │
    │ [end-num_readonly_unsigned..end) = readonly unsigned │
    └──────────────────────────────────────────────────────┘
    """

    def __init__(self, num_required_signatures, num_readonly_signed,
                 num_readonly_unsigned):
        self.num_required_signatures = num_required_signatures
        self.num_readonly_signed = num_readonly_signed
        self.num_readonly_unsigned = num_readonly_unsigned

    def serialize(self):
        """Serialize header to 3 bytes."""
        return bytes([
            self.num_required_signatures,
            self.num_readonly_signed,
            self.num_readonly_unsigned,
        ])


class CompiledInstruction:
    """A compiled instruction using indexes into the account_keys array.

    Instead of repeating full 32-byte pubkeys, compiled instructions
    reference accounts by their index in the message's account_keys array.
    This saves significant space in the serialized transaction.
    """

    def __init__(self, program_id_index, account_indexes, data):
        self.program_id_index = program_id_index  # Index of program in account_keys
        self.account_indexes = account_indexes     # List of indexes for accounts
        self.data = data                           # Raw instruction data bytes

    def serialize(self):
        """Serialize to bytes: program_id_index + compact accounts + compact data."""
        result = bytearray()
        result.append(self.program_id_index)       # 1 byte: program index

        # Encode account indexes array
        result.extend(encode_compact_u16(len(self.account_indexes)))
        for idx in self.account_indexes:
            result.append(idx)                     # 1 byte per account index

        # Encode data array
        result.extend(encode_compact_u16(len(self.data)))
        result.extend(self.data)

        return bytes(result)


class Message:
    """The unsigned message portion of a Solana transaction.

    Layout:
    ┌─────────────────────────────────────┐
    │ Header (3 bytes)                    │
    │ Account keys (compact array of 32B) │
    │ Recent blockhash (32 bytes)         │
    │ Instructions (compact array)        │
    └─────────────────────────────────────┘
    """

    def __init__(self, header, account_keys, recent_blockhash,
                 compiled_instructions):
        self.header = header
        self.account_keys = account_keys              # List of pubkey strings
        self.recent_blockhash = recent_blockhash      # 32-byte hash string
        self.compiled_instructions = compiled_instructions

    def serialize(self):
        """Serialize the entire message to bytes."""
        result = bytearray()

        # Header: 3 bytes
        result.extend(self.header.serialize())

        # Account keys: compact-u16 length + each key as 32 bytes
        result.extend(encode_compact_u16(len(self.account_keys)))
        for key in self.account_keys:
            # Pad or truncate key to 32 bytes for consistent sizing
            key_bytes = key.encode("utf-8")[:32].ljust(32, b'\x00')
            result.extend(key_bytes)

        # Recent blockhash: 32 bytes
        blockhash_bytes = bytes.fromhex(self.recent_blockhash[:64])
        result.extend(blockhash_bytes)

        # Instructions: compact-u16 length + each serialized instruction
        result.extend(encode_compact_u16(len(self.compiled_instructions)))
        for ix in self.compiled_instructions:
            result.extend(ix.serialize())

        return bytes(result)


# ----------------------------------------------------------------------------
# 2d: Transaction builder — high-level API for constructing transactions
# ----------------------------------------------------------------------------

class InstructionInput:
    """High-level instruction before compilation (uses pubkeys, not indexes)."""

    def __init__(self, program_id, accounts, data):
        """
        Args:
            program_id: Program pubkey string
            accounts: List of (pubkey, is_signer, is_writable) tuples
            data: Instruction data bytes
        """
        self.program_id = program_id
        self.accounts = accounts  # List of (pubkey, is_signer, is_writable)
        self.data = data


class TransactionBuilder:
    """Builds a Solana transaction from high-level instructions.

    Handles the complex account deduplication and ordering:
    1. Collect all unique accounts across all instructions
    2. Sort: writable signers → readonly signers → writable non-signers → readonly
    3. Compute header counts
    4. Compile instructions to use account indexes
    """

    @staticmethod
    def build(instructions, payer, recent_blockhash):
        """Build a Message from high-level instructions.

        Args:
            instructions: List of InstructionInput
            payer: Pubkey of the fee payer (always first signer)
            recent_blockhash: Recent blockhash for replay protection

        Returns:
            Message object ready for signing
        """
        # Step 1: Collect all unique accounts with their highest privilege level
        # An account that is writable in one instruction and readonly in another
        # is writable in the final list (highest privilege wins)
        account_flags = {}  # pubkey → (is_signer, is_writable)

        # Payer is always signer + writable (pays fees)
        account_flags[payer] = (True, True)

        for ix in instructions:
            # Program ID is always readonly, non-signer
            if ix.program_id not in account_flags:
                account_flags[ix.program_id] = (False, False)

            for pubkey, is_signer, is_writable in ix.accounts:
                existing = account_flags.get(pubkey, (False, False))
                # Merge: signer if EITHER says signer, writable if EITHER says writable
                account_flags[pubkey] = (
                    existing[0] or is_signer,
                    existing[1] or is_writable,
                )

        # Step 2: Sort accounts into Solana's required order
        # Order: writable signers → readonly signers → writable non-signers → readonly
        writable_signers = []
        readonly_signers = []
        writable_non_signers = []
        readonly_non_signers = []

        for pubkey, (is_signer, is_writable) in account_flags.items():
            if is_signer and is_writable:
                writable_signers.append(pubkey)
            elif is_signer and not is_writable:
                readonly_signers.append(pubkey)
            elif not is_signer and is_writable:
                writable_non_signers.append(pubkey)
            else:
                readonly_non_signers.append(pubkey)

        # Ensure payer is first among writable signers
        if payer in writable_signers:
            writable_signers.remove(payer)
            writable_signers.insert(0, payer)

        # Build final ordered account list
        account_keys = (writable_signers + readonly_signers +
                        writable_non_signers + readonly_non_signers)

        # Step 3: Compute header
        num_required_signatures = len(writable_signers) + len(readonly_signers)
        num_readonly_signed = len(readonly_signers)
        num_readonly_unsigned = len(readonly_non_signers)

        header = MessageHeader(
            num_required_signatures=num_required_signatures,
            num_readonly_signed=num_readonly_signed,
            num_readonly_unsigned=num_readonly_unsigned,
        )

        # Step 4: Compile instructions (convert pubkeys to indexes)
        key_index = {key: i for i, key in enumerate(account_keys)}
        compiled = []

        for ix in instructions:
            program_idx = key_index[ix.program_id]
            account_idxs = [
                key_index[pubkey] for pubkey, _, _ in ix.accounts
            ]
            compiled.append(CompiledInstruction(
                program_id_index=program_idx,
                account_indexes=account_idxs,
                data=ix.data,
            ))

        return Message(
            header=header,
            account_keys=account_keys,
            recent_blockhash=recent_blockhash,
            compiled_instructions=compiled,
        )


# ----------------------------------------------------------------------------
# 2e: Transaction — message + signatures
# ----------------------------------------------------------------------------

class Transaction:
    """A complete Solana transaction: signatures + message.

    Layout:
    ┌───────────────────────────────────────┐
    │ Compact-u16: num_signatures           │
    │ Signatures (64 bytes each)            │
    │ Message (header + keys + hash + ixs)  │
    └───────────────────────────────────────┘
    """

    def __init__(self, message):
        self.message = message
        self.signatures = {}   # pubkey → (r, s) signature

    def sign(self, private_key, public_key_point, pubkey_str):
        """Sign the transaction with a keypair.

        The signature covers the serialized message bytes, ensuring
        that any modification to the transaction invalidates it.
        """
        message_bytes = self.message.serialize()
        signature = sign_message(private_key, message_bytes)
        self.signatures[pubkey_str] = signature

    def verify_signatures(self, pubkey_points):
        """Verify all signatures on this transaction.

        Args:
            pubkey_points: Dict mapping pubkey_str → EC point

        Returns:
            (all_valid, list of (pubkey, is_valid) results)
        """
        message_bytes = self.message.serialize()
        results = []

        # Check each required signer has a valid signature
        num_signers = self.message.header.num_required_signatures
        for i in range(num_signers):
            pubkey = self.message.account_keys[i]
            sig = self.signatures.get(pubkey)

            if sig is None:
                results.append((pubkey, False, "missing signature"))
                continue

            point = pubkey_points.get(pubkey)
            if point is None:
                results.append((pubkey, False, "unknown public key"))
                continue

            valid = verify_signature(point, message_bytes, sig)
            status = "valid" if valid else "invalid signature"
            results.append((pubkey, valid, status))

        all_valid = all(v for _, v, _ in results)
        return all_valid, results

    def serialize(self):
        """Serialize the complete transaction to bytes."""
        result = bytearray()

        # Number of signatures (compact-u16)
        num_sigs = self.message.header.num_required_signatures
        result.extend(encode_compact_u16(num_sigs))

        # Signatures in account_keys order (pad missing sigs with zeros)
        for i in range(num_sigs):
            pubkey = self.message.account_keys[i]
            sig = self.signatures.get(pubkey)
            if sig:
                r, s = sig
                # Pack r and s as 32 bytes each = 64 bytes total
                result.extend(r.to_bytes(32, 'big'))
                result.extend(s.to_bytes(32, 'big'))
            else:
                result.extend(b'\x00' * SIGNATURE_SIZE)  # Zero-filled placeholder

        # Serialized message
        result.extend(self.message.serialize())

        return bytes(result)


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Solana's transaction format."""

    print("=" * 70)
    print("  SOLANA TRANSACTION FORMAT — From Scratch")
    print("=" * 70)

    # --- Generate keypairs ---------------------------------------------------
    print("\n--- 1. Generate Keypairs ---\n")

    alice_priv, alice_point, alice_pub = generate_keypair()
    bob_priv, bob_point, bob_pub = generate_keypair()

    # Known program IDs (no private keys — they're programs)
    system_program = "1111111111111111111111111111111111111111111111"
    token_program = "TokenProg" + "0" * 35

    print(f"  Alice: {alice_pub[:16]}...")
    print(f"  Bob:   {bob_pub[:16]}...")
    print(f"  System Program: {system_program[:16]}...")
    print(f"  Token Program:  {token_program[:16]}...")

    # --- Build a multi-instruction transaction --------------------------------
    print("\n--- 2. Build Multi-Instruction Transaction ---\n")

    # Simulate a recent blockhash (from a recent slot)
    recent_blockhash = hashlib.sha256(b"slot-12345-blockhash").hexdigest()
    print(f"  Recent blockhash: {recent_blockhash[:32]}...")

    # Instruction 1: Transfer SOL from Alice to Bob (system program)
    transfer_amount = 5_000_000_000  # 5 SOL in lamports
    ix1_data = struct.pack("<II", 2, 0) + struct.pack("<Q", transfer_amount)
    # Instruction code 2 = Transfer in system program, followed by lamport amount

    ix1 = InstructionInput(
        program_id=system_program,
        accounts=[
            (alice_pub, True, True),    # Source: signer + writable
            (bob_pub, False, True),     # Destination: writable (not signer)
        ],
        data=ix1_data,
    )

    # Instruction 2: Transfer tokens (token program)
    token_amount = 100
    ix2_data = struct.pack("<BQ", 3, token_amount)
    # Instruction code 3 = Transfer in token program

    alice_token_acct = "AliceToken" + "0" * 34
    bob_token_acct = "BobToken" + "0" * 36

    ix2 = InstructionInput(
        program_id=token_program,
        accounts=[
            (alice_token_acct, False, True),  # Source token account: writable
            (bob_token_acct, False, True),    # Dest token account: writable
            (alice_pub, True, False),          # Authority: signer
        ],
        data=ix2_data,
    )

    print("  Instructions:")
    print(f"  ┌─ IX #0: System Transfer ─────────────────────────┐")
    print(f"  │  program: {system_program[:20]}...              │")
    print(f"  │  Alice → Bob: {transfer_amount:,} lamports (5 SOL)   │")
    print(f"  └─────────────────────────────────────────────────────┘")
    print(f"  ┌─ IX #1: Token Transfer ──────────────────────────┐")
    print(f"  │  program: {token_program[:20]}...              │")
    print(f"  │  AliceToken → BobToken: {token_amount} tokens          │")
    print(f"  └─────────────────────────────────────────────────────┘")

    # --- Compile the transaction message -------------------------------------
    print("\n--- 3. Compile Message ---\n")

    message = TransactionBuilder.build(
        instructions=[ix1, ix2],
        payer=alice_pub,
        recent_blockhash=recent_blockhash,
    )

    print("  Account ordering (deduplicated and sorted):")
    print(f"  ┌──{'─'*5}─┬─{'─'*22}─┬─{'─'*8}─┬─{'─'*10}─┐")
    print(f"  │ {'Idx':>5s} │ {'Account':>22s} │ {'Signer':>8s} │ {'Writable':>10s} │")
    print(f"  ├──{'─'*5}─┼─{'─'*22}─┼─{'─'*8}─┼─{'─'*10}─┤")

    num_sig = message.header.num_required_signatures
    num_ro_sig = message.header.num_readonly_signed
    num_ro_unsig = message.header.num_readonly_unsigned
    total = len(message.account_keys)

    for i, key in enumerate(message.account_keys):
        is_signer = i < num_sig
        # Writable: not in readonly-signed range AND not in readonly-unsigned range
        is_readonly_signed = (num_sig - num_ro_sig) <= i < num_sig if num_ro_sig > 0 else False
        is_readonly_unsigned = i >= total - num_ro_unsig if num_ro_unsig > 0 else False
        is_writable = not is_readonly_signed and not is_readonly_unsigned

        sig_str = "  ✓" if is_signer else ""
        wr_str = "  ✓" if is_writable else ""
        print(f"  │ {i:>5d} │ {key[:22]:>22s} │ {sig_str:>8s} │ {wr_str:>10s} │")

    print(f"  └──{'─'*5}─┴─{'─'*22}─┴─{'─'*8}─┴─{'─'*10}─┘")

    print(f"\n  Header:")
    print(f"    num_required_signatures: {message.header.num_required_signatures}")
    print(f"    num_readonly_signed:     {message.header.num_readonly_signed}")
    print(f"    num_readonly_unsigned:   {message.header.num_readonly_unsigned}")

    # Show compiled instructions
    print(f"\n  Compiled instructions (using account indexes):")
    for i, cix in enumerate(message.compiled_instructions):
        print(f"    IX #{i}: program_idx={cix.program_id_index}, "
              f"account_idxs={cix.account_indexes}, "
              f"data={cix.data.hex()[:24]}...")

    # --- Compact-u16 encoding demo -------------------------------------------
    print("\n--- 4. Compact-u16 Encoding ---\n")

    print("  Solana uses compact-u16 for array lengths to save space:")
    print(f"  {'Value':>8s} │ {'Bytes':>8s} │ {'Hex':>12s}")
    print(f"  {'─'*8}─┼─{'─'*8}─┼─{'─'*12}")
    for val in [0, 1, 5, 127, 128, 255, 256, 16383, 16384]:
        encoded = encode_compact_u16(val)
        decoded, consumed = decode_compact_u16(encoded)
        assert decoded == val, f"Round-trip failed for {val}"
        print(f"  {val:>8d} │ {len(encoded):>8d} │ {encoded.hex():>12s}")

    # --- Serialize the message -----------------------------------------------
    print("\n--- 5. Serialize Message ---\n")

    msg_bytes = message.serialize()
    print(f"  Message size: {len(msg_bytes)} bytes")
    print(f"  Message hash: {hashlib.sha256(msg_bytes).hexdigest()[:32]}...")

    # Show byte layout
    print(f"\n  Byte layout:")
    print(f"  ┌─ Header ──────────────┐")
    print(f"  │ {msg_bytes[:3].hex():>24s} │  (3 bytes)")
    print(f"  ├─ Account keys ────────┤")
    # Compact-u16 length + 32 bytes per key
    key_start = 3
    key_len_bytes = encode_compact_u16(len(message.account_keys))
    key_section_size = len(key_len_bytes) + len(message.account_keys) * 32
    print(f"  │ {len(message.account_keys)} keys × 32B"
          f"{'':>9s} │  ({key_section_size} bytes)")
    print(f"  ├─ Recent blockhash ────┤")
    print(f"  │ {recent_blockhash[:24]:>24s} │  (32 bytes)")
    print(f"  ├─ Instructions ────────┤")
    ix_bytes = msg_bytes[key_start + key_section_size + 32:]
    print(f"  │ {len(message.compiled_instructions)} instructions"
          f"{'':>10s} │  ({len(ix_bytes)} bytes)")
    print(f"  └──────────────────────────┘")
    print(f"  Total: {len(msg_bytes)} bytes")

    # --- Sign the transaction ------------------------------------------------
    print("\n--- 6. Sign Transaction ---\n")

    tx = Transaction(message)

    # Alice signs (she's the only required signer in this tx)
    print("  Alice signing transaction...")
    tx.sign(alice_priv, alice_point, alice_pub)

    sig = tx.signatures[alice_pub]
    print(f"  Signature (r): {format(sig[0], 'x')[:32]}...")
    print(f"  Signature (s): {format(sig[1], 'x')[:32]}...")

    # --- Verify signatures ---------------------------------------------------
    print("\n--- 7. Verify Signatures ---\n")

    pubkey_points = {alice_pub: alice_point, bob_pub: bob_point}
    all_valid, results = tx.verify_signatures(pubkey_points)

    for pubkey, valid, status in results:
        marker = "✓" if valid else "✗"
        print(f"  {marker} {pubkey[:20]}... — {status}")

    print(f"\n  Overall: {'✓ ALL VALID' if all_valid else '✗ INVALID'}")

    # --- Serialize full transaction ------------------------------------------
    print("\n--- 8. Serialize Full Transaction ---\n")

    tx_bytes = tx.serialize()
    print(f"  Transaction size: {len(tx_bytes)} bytes "
          f"(max {MAX_TX_SIZE})")
    fits = len(tx_bytes) <= MAX_TX_SIZE
    print(f"  Fits in packet: {'✓ Yes' if fits else '✗ No'}")

    print(f"\n  Transaction layout:")
    print(f"  ┌────────────────────────────────────────┐")
    sig_section = 1 + message.header.num_required_signatures * SIGNATURE_SIZE
    msg_section = len(msg_bytes)
    print(f"  │ Signatures:  {sig_section:>4d} bytes"
          f"{'':>16s} │")
    print(f"  │   compact-u16 length: 1 byte"
          f"{'':>10s} │")
    print(f"  │   {message.header.num_required_signatures} × 64B"
          f" = {message.header.num_required_signatures * 64} bytes"
          f"{'':>16s} │")
    print(f"  │ Message:     {msg_section:>4d} bytes"
          f"{'':>16s} │")
    print(f"  │   header:            3 bytes"
          f"{'':>10s} │")
    print(f"  │   account keys:    {key_section_size:>3d} bytes"
          f"{'':>10s} │")
    print(f"  │   blockhash:        32 bytes"
          f"{'':>10s} │")
    print(f"  │   instructions:    {len(ix_bytes):>3d} bytes"
          f"{'':>10s} │")
    print(f"  ├────────────────────────────────────────┤")
    print(f"  │ Total:       {len(tx_bytes):>4d} bytes"
          f"{'':>16s} │")
    print(f"  └────────────────────────────────────────┘")

    # --- Tamper detection ----------------------------------------------------
    print("\n--- 9. Tamper Detection ---\n")

    print("  Modifying the transfer amount in instruction data...")
    # Tamper with the message — change transfer amount
    original_data = tx.message.compiled_instructions[0].data
    tampered_data = struct.pack("<II", 2, 0) + struct.pack("<Q", 999_000_000_000)
    tx.message.compiled_instructions[0].data = tampered_data

    # Re-verify — signature should now fail
    all_valid_tampered, results_tampered = tx.verify_signatures(pubkey_points)
    for pubkey, valid, status in results_tampered:
        marker = "✓" if valid else "✗"
        print(f"  {marker} {pubkey[:20]}... — {status}")

    print(f"\n  Tampering detected: "
          f"{'✗ SIGNATURE INVALID' if not all_valid_tampered else '✓ (unexpected)'}")

    # Restore original
    tx.message.compiled_instructions[0].data = original_data

    # --- Summary -------------------------------------------------------------
    print("\n--- Summary ---\n")
    print("  Solana transaction format:")
    print("  • Message = header + account_keys + blockhash + instructions")
    print("  • Accounts are deduplicated and sorted by privilege level")
    print("  • Compiled instructions use indexes (not full pubkeys)")
    print("  • Compact-u16 encoding saves space on array lengths")
    print("  • Signatures cover the serialized message bytes")
    print("  • Any modification to the message invalidates signatures")
    print(f"  • Max transaction size: {MAX_TX_SIZE} bytes (fits in one UDP packet)")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
