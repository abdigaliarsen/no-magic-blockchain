"""
TITLE: Versioned Transactions and Address Lookup Tables
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    Versioned transactions (v0 format) and Address Lookup Tables (ALTs) — Solana's
    solution to the transaction size limit. ALTs store frequently-used addresses in
    on-chain tables, letting transactions reference them by 1-byte index instead of
    full 32-byte pubkeys, dramatically reducing transaction size.

KEY CONCEPTS:
    - Legacy vs v0 transaction format differences
    - Address Lookup Tables: on-chain tables mapping indexes to 32-byte addresses
    - Table lookups: writable and readonly address references via (table, index) pairs
    - Size reduction: from 32 bytes per address to 1 byte per lookup
    - Backwards compatibility: v0 transactions carry a version prefix byte

PREREQUISITE SCRIPTS:
    - solana/fundamentals/04_transactions.py (legacy transaction format)
    - solana/fundamentals/01_accounts_model.py (account structure)

REAL-WORLD RELEVANCE:
    Before versioned transactions, Solana DeFi protocols hit the 1232-byte transaction
    limit when interacting with many accounts (e.g., DEX routing through multiple pools).
    ALTs enabled complex DeFi transactions that were previously impossible, and are now
    used by Jupiter, Raydium, and virtually every Solana DeFi application.
"""

import hashlib
import struct
import os

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Maximum transaction size in bytes (Solana uses a single UDP packet)
MAX_TX_SIZE = 1232

# Size of a public key / address in bytes
PUBKEY_SIZE = 32

# Size of a signature in bytes (Ed25519)
SIGNATURE_SIZE = 64

# Version prefix for v0 transactions — the high bit is set to indicate
# a versioned transaction, and the remaining 7 bits encode the version
V0_PREFIX = 0x80  # Binary: 10000000 — version 0

# Maximum number of accounts addressable via lookup table
# (limited by u8 index = 256 entries per table)
MAX_TABLE_ENTRIES = 256

# Compact-u16 encoding overhead per array
COMPACT_U16_OVERHEAD = 1  # For small counts (< 128)


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: Address generation helpers
# ----------------------------------------------------------------------------

def make_address(name):
    """Create a deterministic 32-byte address from a name.

    In real Solana, addresses are Ed25519 public keys (32 bytes).
    We simulate them with SHA-256 hashes for reproducibility.
    """
    return hashlib.sha256(name.encode()).digest()


def addr_short(addr_bytes):
    """Short display form of an address (first 8 hex chars)."""
    return addr_bytes.hex()[:8] + "..."


def encode_compact_u16(value):
    """Encode an integer as Solana's compact-u16 format.

    Uses 1-3 bytes with continuation bits to save space on small values.
    """
    result = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value > 0:
            byte |= 0x80  # Set continuation bit
            result.append(byte)
        else:
            result.append(byte)
            break
    return bytes(result)


# ----------------------------------------------------------------------------
# 2b: Address Lookup Table (ALT)
# ----------------------------------------------------------------------------

class AddressLookupTable:
    """An on-chain Address Lookup Table (ALT).

    ALTs are special accounts that store a list of up to 256 addresses.
    Transactions can reference these addresses by (table_address, index)
    instead of including the full 32-byte address, saving 31 bytes per reference.

    Lifecycle: create → extend (add addresses) → freeze (optional) → close
    """

    def __init__(self, authority, table_address=None):
        self.authority = authority    # Who can modify this table
        # Table has its own on-chain address
        self.address = table_address or make_address(f"ALT-{authority.hex()[:8]}")
        self.addresses = []          # List of 32-byte addresses stored in table
        self.is_frozen = False       # Frozen tables cannot be modified
        self.deactivation_slot = None  # Set when table is being deactivated

    def extend(self, new_addresses):
        """Add addresses to the table (like appending rows).

        Returns the starting index of newly added addresses.
        """
        if self.is_frozen:
            raise ValueError("Cannot extend frozen table")
        if len(self.addresses) + len(new_addresses) > MAX_TABLE_ENTRIES:
            raise ValueError(
                f"Table would exceed {MAX_TABLE_ENTRIES} entries"
            )

        start_idx = len(self.addresses)
        self.addresses.extend(new_addresses)
        return start_idx

    def lookup(self, index):
        """Look up an address by index. Returns the 32-byte address."""
        if index >= len(self.addresses):
            raise IndexError(f"Index {index} out of range (table has {len(self.addresses)})")
        return self.addresses[index]

    def find_index(self, address):
        """Find the index of an address in the table. Returns -1 if not found."""
        try:
            return self.addresses.index(address)
        except ValueError:
            return -1

    def freeze(self):
        """Freeze the table — no more modifications allowed."""
        self.is_frozen = True

    def serialized_size(self):
        """Size of the table account data on-chain."""
        # Header (56 bytes) + addresses (32 bytes each)
        return 56 + len(self.addresses) * PUBKEY_SIZE


# ----------------------------------------------------------------------------
# 2c: Legacy Transaction (pre-versioned)
# ----------------------------------------------------------------------------

class LegacyTransaction:
    """A legacy (pre-v0) Solana transaction.

    Layout:
    ┌─────────────────────────────────────────┐
    │ compact-u16: num_signatures             │
    │ signatures: [64 bytes × num_signatures] │
    │ message:                                │
    │   header: 3 bytes                       │
    │   compact-u16: num_account_keys         │
    │   account_keys: [32 bytes × num_keys]   │
    │   recent_blockhash: 32 bytes            │
    │   compact-u16: num_instructions         │
    │   instructions: [...]                   │
    └─────────────────────────────────────────┘

    Every account used MUST be included as a full 32-byte key in account_keys.
    """

    def __init__(self, signers, readonly_signed, writable_unsigned,
                 readonly_unsigned, recent_blockhash, instructions):
        self.signers = signers                      # Writable signers
        self.readonly_signed = readonly_signed      # Readonly signers
        self.writable_unsigned = writable_unsigned  # Writable non-signers
        self.readonly_unsigned = readonly_unsigned  # Readonly non-signers
        self.recent_blockhash = recent_blockhash
        self.instructions = instructions            # List of (program_idx, acct_idxs, data)

        # Build the full account keys list in Solana's required order
        self.account_keys = (
            self.signers + self.readonly_signed +
            self.writable_unsigned + self.readonly_unsigned
        )

    def estimate_size(self):
        """Estimate serialized transaction size in bytes."""
        num_sigs = len(self.signers) + len(self.readonly_signed)
        size = 0
        size += len(encode_compact_u16(num_sigs))     # Signature count
        size += num_sigs * SIGNATURE_SIZE              # Signatures
        size += 3                                      # Message header
        size += len(encode_compact_u16(len(self.account_keys)))  # Key count
        size += len(self.account_keys) * PUBKEY_SIZE   # Account keys
        size += 32                                     # Recent blockhash
        size += len(encode_compact_u16(len(self.instructions)))  # Instruction count
        for prog_idx, acct_idxs, data in self.instructions:
            size += 1                                   # Program ID index
            size += len(encode_compact_u16(len(acct_idxs)))  # Account index count
            size += len(acct_idxs)                      # Account indexes (1 byte each)
            size += len(encode_compact_u16(len(data)))  # Data length
            size += len(data)                           # Instruction data
        return size


# ----------------------------------------------------------------------------
# 2d: Versioned Transaction (v0)
# ----------------------------------------------------------------------------

class MessageAddressTableLookup:
    """A reference to addresses in an Address Lookup Table.

    Instead of including full 32-byte addresses, v0 transactions include:
    - The ALT's address (32 bytes, but shared across many lookups)
    - Writable indexes (1 byte each)
    - Readonly indexes (1 byte each)

    Net saving: (N_lookups - 1) × 31 bytes per table referenced.
    """

    def __init__(self, table_address, writable_indexes, readonly_indexes):
        self.table_address = table_address       # 32-byte ALT address
        self.writable_indexes = writable_indexes  # u8 indexes into ALT for writable accounts
        self.readonly_indexes = readonly_indexes  # u8 indexes into ALT for readonly accounts

    def serialized_size(self):
        """Size contribution to the transaction."""
        size = PUBKEY_SIZE                                 # Table address
        size += len(encode_compact_u16(len(self.writable_indexes)))
        size += len(self.writable_indexes)                 # 1 byte per writable index
        size += len(encode_compact_u16(len(self.readonly_indexes)))
        size += len(self.readonly_indexes)                 # 1 byte per readonly index
        return size


class VersionedTransaction:
    """A v0 versioned Solana transaction with Address Lookup Table support.

    Layout:
    ┌──────────────────────────────────────────────┐
    │ compact-u16: num_signatures                  │
    │ signatures: [64 bytes × num_signatures]      │
    │ message_prefix: 0x80 (v0)                    │
    │ message:                                     │
    │   header: 3 bytes                            │
    │   compact-u16: num_static_account_keys       │
    │   static_account_keys: [32B × num_static]    │
    │   recent_blockhash: 32 bytes                 │
    │   compact-u16: num_instructions              │
    │   instructions: [...]                        │
    │   compact-u16: num_address_table_lookups     │  ← NEW
    │   address_table_lookups: [...]               │  ← NEW
    └──────────────────────────────────────────────┘

    Accounts can come from two sources:
    1. Static keys: included directly (like legacy) — for signers and programs
    2. Table lookups: referenced by (table_address, index) — for non-signers
    """

    def __init__(self, signers, readonly_signed, writable_unsigned_static,
                 readonly_unsigned_static, recent_blockhash, instructions,
                 table_lookups=None):
        self.signers = signers
        self.readonly_signed = readonly_signed
        self.writable_unsigned_static = writable_unsigned_static
        self.readonly_unsigned_static = readonly_unsigned_static
        self.recent_blockhash = recent_blockhash
        self.instructions = instructions
        self.table_lookups = table_lookups or []

        # Static keys are included directly in the transaction
        self.static_account_keys = (
            self.signers + self.readonly_signed +
            self.writable_unsigned_static + self.readonly_unsigned_static
        )

    def total_accounts(self):
        """Total number of accounts accessible to this transaction."""
        lookup_count = sum(
            len(tl.writable_indexes) + len(tl.readonly_indexes)
            for tl in self.table_lookups
        )
        return len(self.static_account_keys) + lookup_count

    def estimate_size(self):
        """Estimate serialized transaction size in bytes."""
        num_sigs = len(self.signers) + len(self.readonly_signed)
        size = 0
        size += len(encode_compact_u16(num_sigs))     # Signature count
        size += num_sigs * SIGNATURE_SIZE              # Signatures
        size += 1                                      # Version prefix (0x80)
        size += 3                                      # Message header
        size += len(encode_compact_u16(len(self.static_account_keys)))
        size += len(self.static_account_keys) * PUBKEY_SIZE  # Static keys
        size += 32                                     # Recent blockhash
        size += len(encode_compact_u16(len(self.instructions)))  # IX count
        for prog_idx, acct_idxs, data in self.instructions:
            size += 1                                   # Program ID index
            size += len(encode_compact_u16(len(acct_idxs)))
            size += len(acct_idxs)
            size += len(encode_compact_u16(len(data)))
            size += len(data)
        # Address table lookups (NEW in v0)
        size += len(encode_compact_u16(len(self.table_lookups)))
        for tl in self.table_lookups:
            size += tl.serialized_size()
        return size


# ----------------------------------------------------------------------------
# 2e: Transaction builder — converts legacy to versioned using ALTs
# ----------------------------------------------------------------------------

class VersionedTransactionBuilder:
    """Builds a v0 transaction from a legacy transaction using ALTs.

    Strategy:
    - Signers and program IDs MUST remain as static keys (they need to sign
      or be identified by index in instructions)
    - Non-signer accounts that exist in an ALT are converted to lookups
    - Non-signer accounts not in any ALT remain as static keys
    """

    @staticmethod
    def from_legacy(legacy_tx, alt_tables):
        """Convert a legacy transaction to v0 using available ALTs.

        Args:
            legacy_tx: LegacyTransaction to convert
            alt_tables: List of AddressLookupTable objects available

        Returns:
            (VersionedTransaction, conversion_stats)
        """
        # Accounts that MUST be static: signers and program IDs
        must_be_static = set()
        for addr in legacy_tx.signers:
            must_be_static.add(addr.hex())
        for addr in legacy_tx.readonly_signed:
            must_be_static.add(addr.hex())
        # Programs are referenced by index in instructions, so keep static
        for prog_idx, _, _ in legacy_tx.instructions:
            prog_addr = legacy_tx.account_keys[prog_idx]
            must_be_static.add(prog_addr.hex())

        # Try to look up non-signer accounts in ALTs
        lookups_by_table = {}  # table_address → {writable: [], readonly: []}
        converted = set()

        # Check writable unsigned accounts
        remaining_writable = []
        for addr in legacy_tx.writable_unsigned:
            if addr.hex() in must_be_static:
                remaining_writable.append(addr)
                continue
            found = False
            for alt in alt_tables:
                idx = alt.find_index(addr)
                if idx >= 0:
                    key = alt.address.hex()
                    if key not in lookups_by_table:
                        lookups_by_table[key] = {
                            "table": alt, "writable": [], "readonly": []
                        }
                    lookups_by_table[key]["writable"].append(idx)
                    converted.add(addr.hex())
                    found = True
                    break  # Use first matching table
            if not found:
                remaining_writable.append(addr)

        # Check readonly unsigned accounts
        remaining_readonly = []
        for addr in legacy_tx.readonly_unsigned:
            if addr.hex() in must_be_static:
                remaining_readonly.append(addr)
                continue
            found = False
            for alt in alt_tables:
                idx = alt.find_index(addr)
                if idx >= 0:
                    key = alt.address.hex()
                    if key not in lookups_by_table:
                        lookups_by_table[key] = {
                            "table": alt, "writable": [], "readonly": []
                        }
                    lookups_by_table[key]["readonly"].append(idx)
                    converted.add(addr.hex())
                    found = True
                    break
            if not found:
                remaining_readonly.append(addr)

        # Build table lookup objects
        table_lookups = []
        for entry in lookups_by_table.values():
            table_lookups.append(MessageAddressTableLookup(
                table_address=entry["table"].address,
                writable_indexes=entry["writable"],
                readonly_indexes=entry["readonly"],
            ))

        v0_tx = VersionedTransaction(
            signers=legacy_tx.signers,
            readonly_signed=legacy_tx.readonly_signed,
            writable_unsigned_static=remaining_writable,
            readonly_unsigned_static=remaining_readonly,
            recent_blockhash=legacy_tx.recent_blockhash,
            instructions=legacy_tx.instructions,
            table_lookups=table_lookups,
        )

        stats = {
            "accounts_converted": len(converted),
            "accounts_static": len(v0_tx.static_account_keys),
            "tables_used": len(table_lookups),
        }

        return v0_tx, stats


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of versioned transactions and ALTs."""

    print("=" * 70)
    print("  VERSIONED TRANSACTIONS — Address Lookup Tables")
    print("=" * 70)

    # --- The Problem: Transaction Size Limit ----------------------------------
    print("\n--- 1. The Problem: Transaction Size Limit ---\n")

    print(f"  Max transaction size: {MAX_TX_SIZE} bytes (1 UDP packet)")
    print(f"  Each account key:     {PUBKEY_SIZE} bytes")
    print(f"  Each signature:       {SIGNATURE_SIZE} bytes")
    print()

    # Show how quickly we run out of space
    print(f"  {'# Accounts':>11s}  {'Key Bytes':>10s}  "
          f"{'Remaining':>10s}  {'Status'}")
    print(f"  {'─'*11}  {'─'*10}  {'─'*10}  {'─'*20}")

    overhead = 64 + 3 + 32 + 2 + 20  # 1 sig + header + blockhash + ix overhead
    for n_accounts in [5, 10, 15, 20, 25, 30, 35]:
        key_bytes = n_accounts * PUBKEY_SIZE
        remaining = MAX_TX_SIZE - overhead - key_bytes
        status = "✓ fits" if remaining > 0 else "✗ EXCEEDS LIMIT"
        print(f"  {n_accounts:>11d}  {key_bytes:>10d}  "
              f"{remaining:>10d}  {status}")

    print(f"\n  DeFi transactions often need 20-35 accounts (DEX routing,")
    print(f"  lending protocols, etc.) — they hit this limit!")

    # --- Create an Address Lookup Table ---------------------------------------
    print("\n--- 2. Create Address Lookup Table ---\n")

    # Generate some common DeFi addresses
    defi_names = [
        "USDC_Mint", "USDT_Mint", "SOL_Mint", "RAY_Mint",
        "Pool_USDC_SOL", "Pool_USDC_USDT", "Pool_SOL_RAY",
        "Fee_Account", "Oracle_USDC", "Oracle_SOL",
        "Authority_DEX", "Config_DEX",
        "Pool_LP_USDC_SOL", "Pool_LP_USDC_USDT",
        "Vault_A", "Vault_B",
    ]
    defi_addresses = {name: make_address(name) for name in defi_names}

    authority = make_address("table_authority")
    alt = AddressLookupTable(authority)
    alt.extend(list(defi_addresses.values()))

    print(f"  Table address:  {addr_short(alt.address)}")
    print(f"  Authority:      {addr_short(authority)}")
    print(f"  Entries:        {len(alt.addresses)}")
    print(f"  On-chain size:  {alt.serialized_size()} bytes")
    print()

    print(f"  {'Index':>5s}  {'Name':>20s}  {'Address':>12s}")
    print(f"  {'─'*5}  {'─'*20}  {'─'*12}")
    for i, name in enumerate(defi_names):
        addr = defi_addresses[name]
        print(f"  {i:>5d}  {name:>20s}  {addr_short(addr)}")

    # --- Build a Legacy Transaction -------------------------------------------
    print("\n--- 3. Legacy Transaction (Before ALTs) ---\n")

    # Simulate a complex DEX swap: USDC → SOL → RAY through two pools
    user = make_address("user_wallet")
    user_usdc = make_address("user_usdc_account")
    user_sol = make_address("user_sol_account")
    user_ray = make_address("user_ray_account")
    dex_program = make_address("dex_program")

    # All accounts needed for the swap
    legacy_tx = LegacyTransaction(
        signers=[user],                           # Fee payer + authority
        readonly_signed=[],
        writable_unsigned=[
            user_usdc, user_sol, user_ray,         # User token accounts
            defi_addresses["Pool_USDC_SOL"],       # Pool accounts
            defi_addresses["Pool_SOL_RAY"],
            defi_addresses["Pool_LP_USDC_SOL"],
            defi_addresses["Pool_LP_USDC_USDT"],
            defi_addresses["Vault_A"],
            defi_addresses["Vault_B"],
            defi_addresses["Fee_Account"],
        ],
        readonly_unsigned=[
            dex_program,                            # Program
            defi_addresses["USDC_Mint"],
            defi_addresses["SOL_Mint"],
            defi_addresses["RAY_Mint"],
            defi_addresses["Oracle_USDC"],
            defi_addresses["Oracle_SOL"],
            defi_addresses["Authority_DEX"],
            defi_addresses["Config_DEX"],
        ],
        recent_blockhash=make_address("recent_blockhash"),
        instructions=[
            (11, [1, 2, 3, 4, 5, 12, 13, 15, 16], b"\x01\x00\x00\x00" + b"\xe8\x03"),
            (11, [2, 3, 6, 7, 8, 14, 16, 17], b"\x01\x00\x00\x00" + b"\xe8\x03"),
        ],
    )

    legacy_size = legacy_tx.estimate_size()
    total_accounts = len(legacy_tx.account_keys)

    print(f"  DEX Swap: USDC → SOL → RAY (2-hop route)")
    print(f"  ┌─────────────────────────────────────────┐")
    print(f"  │ Accounts:        {total_accounts:>3d}                    │")
    print(f"  │ Signers:         {len(legacy_tx.signers):>3d}                    │")
    print(f"  │ Writable:        {len(legacy_tx.writable_unsigned):>3d}                    │")
    print(f"  │ Readonly:        {len(legacy_tx.readonly_unsigned):>3d}                    │")
    print(f"  │ Instructions:    {len(legacy_tx.instructions):>3d}                    │")
    print(f"  ├─────────────────────────────────────────┤")
    print(f"  │ Total size:      {legacy_size:>3d} bytes              │")
    print(f"  │ Account keys:    {total_accounts * PUBKEY_SIZE:>3d} bytes "
          f"({total_accounts}×{PUBKEY_SIZE}B)     │")
    fits = "✓" if legacy_size <= MAX_TX_SIZE else "✗"
    print(f"  │ Fits in packet:   {fits}                     │")
    print(f"  └─────────────────────────────────────────┘")

    # --- Convert to Versioned Transaction -------------------------------------
    print("\n--- 4. Versioned Transaction (v0 with ALT) ---\n")

    v0_tx, stats = VersionedTransactionBuilder.from_legacy(legacy_tx, [alt])

    v0_size = v0_tx.estimate_size()

    print(f"  Conversion results:")
    print(f"  ┌─────────────────────────────────────────┐")
    print(f"  │ Accounts converted to lookups: {stats['accounts_converted']:>3d}       │")
    print(f"  │ Static accounts remaining:     {stats['accounts_static']:>3d}       │")
    print(f"  │ Lookup tables used:            {stats['tables_used']:>3d}       │")
    print(f"  │ Total accessible accounts:     {v0_tx.total_accounts():>3d}       │")
    print(f"  ├─────────────────────────────────────────┤")
    print(f"  │ v0 size:    {v0_size:>4d} bytes                 │")
    print(f"  │ Legacy size: {legacy_size:>4d} bytes                │")
    print(f"  │ Saved:       {legacy_size - v0_size:>4d} bytes "
          f"({(legacy_size - v0_size) / legacy_size * 100:.0f}% reduction)  │")
    fits_v0 = "✓" if v0_size <= MAX_TX_SIZE else "✗"
    print(f"  │ Fits in packet:   {fits_v0}                     │")
    print(f"  └─────────────────────────────────────────┘")

    # --- Size Breakdown Comparison --------------------------------------------
    print("\n--- 5. Size Breakdown: Legacy vs v0 ---\n")

    num_sigs = len(legacy_tx.signers)
    sig_bytes = num_sigs * SIGNATURE_SIZE

    # Legacy breakdown
    legacy_keys_bytes = total_accounts * PUBKEY_SIZE
    legacy_other = legacy_size - sig_bytes - legacy_keys_bytes

    # v0 breakdown
    v0_static_keys = len(v0_tx.static_account_keys) * PUBKEY_SIZE
    v0_lookup_bytes = sum(tl.serialized_size() for tl in v0_tx.table_lookups)
    v0_lookup_bytes += len(encode_compact_u16(len(v0_tx.table_lookups)))
    v0_other = v0_size - sig_bytes - v0_static_keys - v0_lookup_bytes - 1  # -1 for version prefix

    bar_scale = 40 / max(legacy_size, 1)

    print("  Legacy transaction:")
    sig_bar = int(sig_bytes * bar_scale)
    key_bar = int(legacy_keys_bytes * bar_scale)
    other_bar = int(legacy_other * bar_scale)
    print(f"  [{'S' * sig_bar}{'K' * key_bar}{'.' * other_bar}]  {legacy_size} bytes")
    print(f"   S=signatures({sig_bytes}B) K=keys({legacy_keys_bytes}B) .=other({legacy_other}B)")
    print()

    print("  v0 transaction:")
    v0_sig_bar = int(sig_bytes * bar_scale)
    v0_key_bar = int(v0_static_keys * bar_scale)
    v0_lk_bar = int(v0_lookup_bytes * bar_scale)
    v0_other_bar = max(1, int(v0_other * bar_scale))
    print(f"  [{'S' * v0_sig_bar}{'K' * v0_key_bar}{'L' * v0_lk_bar}{'.' * v0_other_bar}]  {v0_size} bytes")
    print(f"   S=signatures({sig_bytes}B) K=static keys({v0_static_keys}B) "
          f"L=lookups({v0_lookup_bytes}B) .=other")
    print()
    print(f"  Key savings: {legacy_keys_bytes}B → {v0_static_keys + v0_lookup_bytes}B "
          f"for account references")

    # --- How Lookups Work -----------------------------------------------------
    print("\n--- 6. How Address Lookup Works ---\n")

    print("  Legacy: every account is a full 32-byte key in the transaction")
    print("  v0:     non-signer accounts can be 1-byte indexes into ALTs\n")

    print("  Example — Pool_USDC_SOL account:")
    pool_addr = defi_addresses["Pool_USDC_SOL"]
    pool_idx = alt.find_index(pool_addr)
    print(f"    Full address:  {pool_addr.hex()}")
    print(f"                   ({PUBKEY_SIZE} bytes)")
    print()
    print(f"    ALT reference: table={addr_short(alt.address)}, index={pool_idx}")
    print(f"                   ({PUBKEY_SIZE} bytes table addr + 1 byte index)")
    print(f"                   But table addr is shared across ALL lookups!")
    print()

    # Show per-lookup savings
    num_lookups = stats["accounts_converted"]
    per_lookup_overhead = PUBKEY_SIZE / num_lookups + 1  # Amortized table addr + 1-byte index
    per_lookup_savings = PUBKEY_SIZE - per_lookup_overhead
    print(f"  With {num_lookups} lookups from one table:")
    print(f"    Table address cost: {PUBKEY_SIZE} bytes (amortized: "
          f"{PUBKEY_SIZE / num_lookups:.1f} bytes/lookup)")
    print(f"    Per-lookup index:   1 byte")
    print(f"    Per-lookup total:   {per_lookup_overhead:.1f} bytes "
          f"(vs {PUBKEY_SIZE} bytes legacy)")
    print(f"    Savings per lookup: {per_lookup_savings:.1f} bytes")

    # --- Version Prefix Encoding ----------------------------------------------
    print("\n--- 7. Version Prefix Encoding ---\n")

    print("  How validators distinguish legacy from versioned transactions:\n")
    print(f"  Legacy:  first byte is num_signatures (compact-u16)")
    print(f"           Valid range: 1-127 (0x01-0x7F, high bit = 0)")
    print()
    print(f"  v0:      first message byte is 0x{V0_PREFIX:02X} "
          f"(binary: {V0_PREFIX:08b})")
    print(f"           High bit = 1 → versioned transaction")
    print(f"           Low 7 bits = {V0_PREFIX & 0x7F} → version 0")
    print()
    print(f"  This encoding is backwards-compatible because no legacy")
    print(f"  transaction would have a num_signatures byte with high bit set")
    print(f"  (that would mean 128+ signatures, which is impossible).")

    # --- Scaling Analysis -----------------------------------------------------
    print("\n--- 8. Scaling: Accounts vs Transaction Size ---\n")

    print(f"  {'Accounts':>8s}  {'Legacy':>8s}  {'v0+ALT':>8s}  "
          f"{'Savings':>8s}  {'Comparison'}")
    print(f"  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*30}")

    for n_accts in [5, 10, 15, 20, 25, 30, 35, 40]:
        # Estimate legacy size: 1 sig + header + N keys + blockhash + 1 ix
        leg = 1 + 64 + 3 + 1 + n_accts * 32 + 32 + 1 + 10
        # Estimate v0 size: 1 sig + header + 3 static keys + blockhash + 1 ix + ALT ref
        n_static = 3  # signer + program + 1 other
        n_lookup = max(0, n_accts - n_static)
        v0 = (1 + 64 + 1 + 3 + 1 + n_static * 32 + 32 + 1 + 10 +
              1 + 32 + 1 + n_lookup + 1 + 0)  # ALT overhead

        saved = leg - v0
        leg_bar = "█" * min(leg // 30, 20)
        v0_bar = "█" * min(v0 // 30, 20)
        fits_leg = "✓" if leg <= MAX_TX_SIZE else "✗"
        fits_v0 = "✓" if v0 <= MAX_TX_SIZE else "✓"
        print(f"  {n_accts:>8d}  {leg:>7d}{fits_leg}  {v0:>7d}{fits_v0}  "
              f"{saved:>8d}  {leg_bar} → {v0_bar}")

    # --- Summary --------------------------------------------------------------
    print("\n--- Summary ---\n")
    print("  Versioned transactions and Address Lookup Tables:")
    print(f"  • Legacy transactions include all accounts as full {PUBKEY_SIZE}-byte keys")
    print(f"  • This limits complex DeFi transactions to ~{(MAX_TX_SIZE - 200) // PUBKEY_SIZE} accounts")
    print("  • ALTs store addresses on-chain, referenced by 1-byte index")
    print("  • v0 transactions use ALT lookups for non-signer accounts")
    print(f"  • Our example: {legacy_size} bytes → {v0_size} bytes "
          f"({(legacy_size - v0_size) / legacy_size * 100:.0f}% reduction)")
    print("  • Version prefix (0x80) enables backwards-compatible detection")
    print("  • Signers and programs MUST remain as static keys")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
