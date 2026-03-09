"""
TITLE: Solana Account Model
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    The Solana account model from scratch — accounts as the fundamental storage
    primitive, ownership rules enforced by the runtime, and Program-Derived
    Addresses (PDAs) for deterministic, off-curve address generation.

KEY CONCEPTS:
    - Account structure: pubkey, owner, lamports, data, executable, rent_epoch
    - Ownership rules: only the owner program can modify data; anyone can credit
    - Program-Derived Addresses (PDAs): deterministic seeds + program_id + bump
    - System program: create_account, transfer, assign

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 fundamentals)
    - core/02_public_key_crypto.py (elliptic curve keypairs)

REAL-WORLD RELEVANCE:
    Every piece of state on Solana lives in an account. Unlike Ethereum's
    key-value storage inside contracts, Solana programs are stateless and
    read/write external accounts passed to them. Understanding this model
    is essential for writing Solana programs (smart contracts).
"""

import hashlib
import secrets
import struct

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# The system program owns all new accounts by default and handles
# basic operations like transfers and account creation.
# On real Solana this is 11111111111111111111111111111111 (all ones in base58).
SYSTEM_PROGRAM_ID = "1111111111111111111111111111111111111111111111"

# Lamports per SOL — like satoshis to bitcoin, lamports are the smallest unit
LAMPORTS_PER_SOL = 1_000_000_000  # 1 SOL = 1 billion lamports

# Maximum account data size in bytes (real Solana caps at 10 MB)
MAX_ACCOUNT_DATA_SIZE = 10 * 1024 * 1024

# Rent: cost per byte-year in lamports (simplified from real Solana values)
RENT_LAMPORTS_PER_BYTE_YEAR = 3480
# Minimum 2 years of rent for exemption
RENT_EXEMPTION_YEARS = 2

# Maximum number of seeds for PDA derivation
MAX_PDA_SEEDS = 16
# Maximum seed length in bytes
MAX_SEED_LENGTH = 32


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: Key generation helpers (simplified — real Solana uses Ed25519)
# ----------------------------------------------------------------------------

def generate_keypair():
    """Generate a simplified keypair (random 32-byte public key + private key).
    Real Solana uses Ed25519 curve; we simulate with random bytes for clarity."""
    private_key = secrets.token_bytes(32)  # 32-byte random private key
    # Derive public key by hashing private key (simplified; real Ed25519 uses
    # scalar multiplication on the Edwards curve)
    public_key = hashlib.sha256(private_key).hexdigest()[:44]  # 44-char "address"
    return private_key, public_key


def pubkey_to_short(pubkey):
    """Shorten a pubkey for display purposes."""
    return f"{pubkey[:8]}...{pubkey[-4:]}"


# ----------------------------------------------------------------------------
# 2b: Account structure
# ----------------------------------------------------------------------------

class Account:
    """Represents a Solana account — the fundamental unit of state storage.

    On Solana, EVERYTHING is an account: wallets, programs, token mints,
    token balances, program state. Programs themselves are accounts with
    the executable flag set to True.
    """

    def __init__(self, pubkey, owner=SYSTEM_PROGRAM_ID, lamports=0,
                 data=b"", executable=False, rent_epoch=0):
        self.pubkey = pubkey          # Unique 256-bit address (base58 in production)
        self.owner = owner            # Program that owns this account (can modify data)
        self.lamports = lamports      # Balance in lamports (smallest unit of SOL)
        self.data = bytearray(data)   # Arbitrary byte array; programs interpret this
        self.executable = executable  # True if this account contains a deployed program
        self.rent_epoch = rent_epoch  # Epoch at which rent was last collected

    def __repr__(self):
        return (
            f"Account(pubkey={pubkey_to_short(self.pubkey)}, "
            f"owner={pubkey_to_short(self.owner)}, "
            f"lamports={self.lamports}, "
            f"data_len={len(self.data)}, "
            f"executable={self.executable})"
        )


# ----------------------------------------------------------------------------
# 2c: Runtime — enforces ownership and access rules
# ----------------------------------------------------------------------------

class SolanaRuntime:
    """Simplified Solana runtime that manages accounts and enforces rules.

    Key rules:
    1. Only the owner program can modify an account's data
    2. Only the owner program can debit lamports
    3. Anyone can credit (add) lamports to any account
    4. Only the system program can change an account's owner
    5. Executable accounts cannot be modified (immutable once deployed)
    6. Account data can only grow if the owner approves
    """

    def __init__(self):
        # All accounts indexed by pubkey — like Solana's global account state
        self.accounts = {}
        # Register the system program itself as an executable account
        sys_account = Account(
            pubkey=SYSTEM_PROGRAM_ID,
            owner=SYSTEM_PROGRAM_ID,  # System program owns itself
            lamports=0,
            executable=True,  # It's a program
        )
        self.accounts[SYSTEM_PROGRAM_ID] = sys_account

    def get_account(self, pubkey):
        """Look up an account by pubkey. Returns None if not found."""
        return self.accounts.get(pubkey)

    def create_account(self, payer_pubkey, new_pubkey, lamports, space, owner):
        """System program instruction: create a new account.

        Args:
            payer_pubkey: Who pays for the account creation
            new_pubkey: Address of the new account
            lamports: Initial balance (must cover rent exemption)
            space: Size of the data field in bytes
            owner: Program that will own the new account
        """
        # Verify payer exists and has enough lamports
        payer = self.accounts.get(payer_pubkey)
        if payer is None:
            raise ValueError(f"Payer account {pubkey_to_short(payer_pubkey)} not found")
        if payer.lamports < lamports:
            raise ValueError(
                f"Insufficient funds: have {payer.lamports}, need {lamports}"
            )

        # Verify the address isn't already in use
        if new_pubkey in self.accounts:
            raise ValueError(
                f"Account {pubkey_to_short(new_pubkey)} already exists"
            )

        # Verify space doesn't exceed maximum
        if space > MAX_ACCOUNT_DATA_SIZE:
            raise ValueError(f"Data size {space} exceeds max {MAX_ACCOUNT_DATA_SIZE}")

        # Debit the payer
        payer.lamports -= lamports

        # Create the new account with zeroed data of requested size
        new_account = Account(
            pubkey=new_pubkey,
            owner=owner,          # Owner is the program that will manage this account
            lamports=lamports,    # Funded with the transferred lamports
            data=bytes(space),    # Zero-initialized byte array
            executable=False,
            rent_epoch=0,
        )
        self.accounts[new_pubkey] = new_account
        return new_account

    def transfer(self, from_pubkey, to_pubkey, lamports):
        """System program instruction: transfer lamports between accounts.

        Only the system program can debit lamports from system-owned accounts.
        This mimics SOL transfers in the real runtime.
        """
        sender = self.accounts.get(from_pubkey)
        receiver = self.accounts.get(to_pubkey)

        if sender is None:
            raise ValueError(f"Sender {pubkey_to_short(from_pubkey)} not found")
        if receiver is None:
            raise ValueError(f"Receiver {pubkey_to_short(to_pubkey)} not found")
        if sender.lamports < lamports:
            raise ValueError(
                f"Insufficient: have {sender.lamports}, need {lamports}"
            )
        # Rule: only the owner can debit lamports
        if sender.owner != SYSTEM_PROGRAM_ID:
            raise ValueError("Only system-owned accounts can use transfer")

        sender.lamports -= lamports    # Debit sender
        receiver.lamports += lamports  # Credit receiver
        return True

    def assign(self, account_pubkey, new_owner):
        """System program instruction: change the owner of an account.

        Only works if the account is currently owned by the system program.
        Once assigned to a new program, only that program can modify the data.
        """
        account = self.accounts.get(account_pubkey)
        if account is None:
            raise ValueError(f"Account {pubkey_to_short(account_pubkey)} not found")
        # Only the current owner (system program) can reassign
        if account.owner != SYSTEM_PROGRAM_ID:
            raise ValueError("Only system-owned accounts can be reassigned")

        account.owner = new_owner  # Transfer ownership to the new program
        return True

    def modify_data(self, program_id, account_pubkey, new_data):
        """Attempt to modify an account's data. Enforces ownership rules.

        Args:
            program_id: The program trying to modify the account
            account_pubkey: The account to modify
            new_data: New data bytes to write
        """
        account = self.accounts.get(account_pubkey)
        if account is None:
            raise ValueError(f"Account {pubkey_to_short(account_pubkey)} not found")

        # Rule 1: Only the owner can modify data
        if account.owner != program_id:
            raise PermissionError(
                f"Program {pubkey_to_short(program_id)} cannot modify account "
                f"owned by {pubkey_to_short(account.owner)}"
            )

        # Rule 2: Executable accounts are immutable
        if account.executable:
            raise PermissionError("Cannot modify executable account")

        # Rule 3: Data size cannot change without realloc (simplified)
        if len(new_data) != len(account.data):
            raise ValueError(
                f"Data size mismatch: account has {len(account.data)} bytes, "
                f"got {len(new_data)} bytes"
            )

        account.data = bytearray(new_data)  # Overwrite the data field
        return True

    def add_funded_account(self, pubkey, lamports):
        """Helper: create a pre-funded wallet account (like an airdrop)."""
        account = Account(
            pubkey=pubkey,
            owner=SYSTEM_PROGRAM_ID,
            lamports=lamports,
        )
        self.accounts[pubkey] = account
        return account


# ----------------------------------------------------------------------------
# 2d: Program-Derived Addresses (PDAs)
# ----------------------------------------------------------------------------

def find_program_address(seeds, program_id):
    """Find a Program-Derived Address (PDA) by searching for a valid bump seed.

    PDAs are deterministic addresses derived from a set of seeds and a program ID.
    The key property: PDAs are guaranteed to NOT be on the Ed25519 curve, so no
    private key exists for them. This means only the program can "sign" for the PDA.

    The algorithm tries bump = 255 down to 0, appending the bump to the seeds,
    and hashing. If the resulting point is off-curve (simplified check here),
    we have a valid PDA.

    Args:
        seeds: List of byte strings used to derive the address
        program_id: The program that will own the PDA

    Returns:
        (address, bump_seed) tuple
    """
    if len(seeds) > MAX_PDA_SEEDS:
        raise ValueError(f"Too many seeds: {len(seeds)} > {MAX_PDA_SEEDS}")
    for seed in seeds:
        if len(seed) > MAX_SEED_LENGTH:
            raise ValueError(f"Seed too long: {len(seed)} > {MAX_SEED_LENGTH}")

    # Try bump seeds from 255 down to 0 — higher bumps are tried first
    # because they're more likely to produce off-curve points
    for bump in range(255, -1, -1):
        hasher = hashlib.sha256()
        # Concatenate all seeds + bump byte + program_id + "ProgramDerivedAddress" tag
        for seed in seeds:
            hasher.update(seed)
        hasher.update(bytes([bump]))                    # The bump seed (1 byte)
        hasher.update(program_id.encode("utf-8"))       # Program ID as bytes
        hasher.update(b"ProgramDerivedAddress")         # Domain separator tag

        candidate = hasher.hexdigest()[:44]  # Truncate to our address format

        # In real Solana, we check if the point is NOT on the Ed25519 curve.
        # We simulate this: if the first byte (as int) is even, consider it
        # "off-curve" (roughly 50% chance, similar to real probability).
        first_byte = int(candidate[:2], 16)
        if first_byte % 2 == 0:  # Simulated off-curve check
            return candidate, bump

    raise ValueError("Could not find valid PDA (exhausted all bump seeds)")


def create_program_address(seeds, program_id):
    """Create a PDA with explicit seeds (including bump). No searching.

    Unlike find_program_address, the caller must provide the bump seed
    as part of the seeds list. This is used when you already know the bump.
    """
    hasher = hashlib.sha256()
    for seed in seeds:
        hasher.update(seed)
    hasher.update(program_id.encode("utf-8"))
    hasher.update(b"ProgramDerivedAddress")
    return hasher.hexdigest()[:44]


# ----------------------------------------------------------------------------
# 2e: Rent calculation
# ----------------------------------------------------------------------------

def minimum_balance_for_rent_exemption(data_size):
    """Calculate the minimum lamports needed for an account to be rent-exempt.

    On Solana, accounts must hold enough lamports to cover 2 years of rent.
    If they don't, the runtime gradually deducts rent each epoch until the
    account is garbage-collected.

    Formula: (account_overhead + data_size) * rent_per_byte * 2_years
    """
    # 128 bytes of overhead for the account metadata itself
    account_overhead = 128
    total_size = account_overhead + data_size
    return total_size * RENT_LAMPORTS_PER_BYTE_YEAR * RENT_EXEMPTION_YEARS


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Solana's account model."""

    print("=" * 70)
    print("  SOLANA ACCOUNT MODEL — From Scratch")
    print("=" * 70)

    # --- Setup runtime and wallets -------------------------------------------
    runtime = SolanaRuntime()

    # Generate two "users" (wallet keypairs)
    _, alice_pubkey = generate_keypair()
    _, bob_pubkey = generate_keypair()

    # Airdrop SOL to Alice (like solana airdrop on devnet)
    alice_balance = 10 * LAMPORTS_PER_SOL  # 10 SOL
    runtime.add_funded_account(alice_pubkey, alice_balance)
    runtime.add_funded_account(bob_pubkey, 2 * LAMPORTS_PER_SOL)  # 2 SOL for Bob

    print("\n--- 1. Account Structure ---\n")
    alice = runtime.get_account(alice_pubkey)
    print(f"  Alice's Account:")
    print(f"  ┌─────────────────────────────────────────────────┐")
    print(f"  │ pubkey:     {pubkey_to_short(alice.pubkey):>36s} │")
    print(f"  │ owner:      {pubkey_to_short(alice.owner):>36s} │")
    print(f"  │ lamports:   {alice.lamports:>36,} │")
    print(f"  │ data_len:   {len(alice.data):>36} │")
    print(f"  │ executable: {str(alice.executable):>36s} │")
    print(f"  │ rent_epoch: {alice.rent_epoch:>36} │")
    print(f"  └─────────────────────────────────────────────────┘")

    # --- Transfer lamports ---------------------------------------------------
    print("\n--- 2. Transfer Lamports ---\n")
    transfer_amount = 3 * LAMPORTS_PER_SOL  # 3 SOL
    print(f"  Transferring {transfer_amount / LAMPORTS_PER_SOL:.0f} SOL "
          f"from Alice to Bob...")
    runtime.transfer(alice_pubkey, bob_pubkey, transfer_amount)

    alice = runtime.get_account(alice_pubkey)
    bob = runtime.get_account(bob_pubkey)
    print(f"  Alice: {alice.lamports / LAMPORTS_PER_SOL:.1f} SOL "
          f"({alice.lamports:,} lamports)")
    print(f"  Bob:   {bob.lamports / LAMPORTS_PER_SOL:.1f} SOL "
          f"({bob.lamports:,} lamports)")

    # --- Create a data account -----------------------------------------------
    print("\n--- 3. Create Data Account ---\n")
    _, data_account_pubkey = generate_keypair()
    program_id = "MyCounterProgram" + "0" * 28  # Fake program ID (44 chars)
    data_size = 8  # 8 bytes to store a u64 counter
    rent = minimum_balance_for_rent_exemption(data_size)

    print(f"  Data size: {data_size} bytes")
    print(f"  Rent-exempt minimum: {rent:,} lamports "
          f"({rent / LAMPORTS_PER_SOL:.4f} SOL)")

    # Alice pays to create an account owned by the counter program
    runtime.create_account(
        payer_pubkey=alice_pubkey,
        new_pubkey=data_account_pubkey,
        lamports=rent,
        space=data_size,
        owner=program_id,
    )

    data_account = runtime.get_account(data_account_pubkey)
    print(f"\n  Created account:")
    print(f"  ┌─────────────────────────────────────────────────┐")
    print(f"  │ pubkey:     {pubkey_to_short(data_account.pubkey):>36s} │")
    print(f"  │ owner:      {pubkey_to_short(data_account.owner):>36s} │")
    print(f"  │ lamports:   {data_account.lamports:>36,} │")
    print(f"  │ data:       {data_account.data.hex():>36s} │")
    print(f"  │ executable: {str(data_account.executable):>36s} │")
    print(f"  └─────────────────────────────────────────────────┘")

    # --- Ownership rules -----------------------------------------------------
    print("\n--- 4. Ownership Rules ---\n")

    # The owner program CAN modify data
    new_data = struct.pack("<Q", 42)  # Little-endian u64 with value 42
    runtime.modify_data(program_id, data_account_pubkey, new_data)
    data_account = runtime.get_account(data_account_pubkey)
    counter_value = struct.unpack("<Q", data_account.data)[0]
    print(f"  ✓ Owner program wrote counter = {counter_value}")

    # A different program CANNOT modify the data
    rogue_program = "RogueProgram" + "0" * 32  # Not the owner
    try:
        runtime.modify_data(rogue_program, data_account_pubkey, b"\x00" * 8)
        print("  ✗ ERROR: rogue program modified data (should not happen!)")
    except PermissionError as e:
        print(f"  ✗ Rogue program blocked: {e}")

    # Anyone CAN credit lamports (no ownership check for credits)
    print(f"\n  Bob credits 1 SOL to the data account...")
    # Direct credit — anyone can add lamports
    bob_acct = runtime.get_account(bob_pubkey)
    data_acct = runtime.get_account(data_account_pubkey)
    credit_amount = 1 * LAMPORTS_PER_SOL
    bob_acct.lamports -= credit_amount
    data_acct.lamports += credit_amount
    print(f"  ✓ Data account balance: {data_acct.lamports:,} lamports")

    # --- Program-Derived Addresses -------------------------------------------
    print("\n--- 5. Program-Derived Addresses (PDAs) ---\n")

    print("  PDAs are deterministic addresses with NO private key.")
    print("  Only the owning program can 'sign' for them.\n")

    # Derive a PDA for a user's counter state
    seeds = [
        b"counter",                            # Literal seed (namespace)
        alice_pubkey[:32].encode("utf-8"),      # User's pubkey as seed
    ]

    pda_address, bump = find_program_address(seeds, program_id)
    print(f"  Seeds: [b\"counter\", alice_pubkey[:32]]")
    print(f"  Program: {pubkey_to_short(program_id)}")
    print(f"  ┌─────────────────────────────────────────────────┐")
    print(f"  │ PDA address: {pubkey_to_short(pda_address):>35s} │")
    print(f"  │ Bump seed:   {bump:>35d} │")
    print(f"  └─────────────────────────────────────────────────┘")

    # Verify determinism — same seeds always produce same address
    pda_address2, bump2 = find_program_address(seeds, program_id)
    print(f"\n  Re-derived with same seeds:")
    print(f"  Address match: {pda_address == pda_address2}  "
          f"(deterministic ✓)")

    # Different seeds produce different addresses
    seeds_alt = [b"counter", b"different_user"]
    pda_alt, bump_alt = find_program_address(seeds_alt, program_id)
    print(f"  Different seeds → different PDA: "
          f"{pubkey_to_short(pda_alt)} (bump={bump_alt})")

    # --- Rent calculation overview -------------------------------------------
    print("\n--- 6. Rent Exemption Costs ---\n")

    print(f"  {'Data Size':>12s} │ {'Rent-Exempt Min':>18s} │ {'SOL':>10s}")
    print(f"  {'─' * 12}─┼─{'─' * 18}─┼─{'─' * 10}")
    for size in [0, 8, 64, 256, 1024, 10240]:
        min_bal = minimum_balance_for_rent_exemption(size)
        sol = min_bal / LAMPORTS_PER_SOL
        print(f"  {size:>10} B │ {min_bal:>16,} L │ {sol:>8.4f} SOL")

    # --- Summary -------------------------------------------------------------
    print("\n--- Summary ---\n")
    print(f"  Total accounts in runtime: {len(runtime.accounts)}")
    print(f"  Accounts: system_program, Alice, Bob, data_account")
    print()
    print("  Key takeaways:")
    print("  • Everything on Solana is an account (wallets, programs, data)")
    print("  • Only the owner program can modify an account's data")
    print("  • PDAs give programs deterministic, keyless addresses")
    print("  • Accounts must hold enough lamports for rent exemption")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
