"""
TITLE: PDAs & Cross-Program Invocations (Deep Dive)
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    Program Derived Addresses (PDAs) and Cross-Program Invocations (CPIs) —
    the two mechanisms that enable composable, trustless program interactions
    on Solana. PDAs are deterministic addresses that only a program can "sign"
    for, enabling programs to own accounts without holding private keys.

KEY CONCEPTS:
    - PDA derivation: SHA-256(seeds || program_id || "ProgramDerivedAddress")
    - Bump seed: iterate 255→0 to find the first seed that puts the point off-curve
    - CPI (Cross-Program Invocation): one program calling another with account list
    - CPI with signer seeds: PDA acts as a signer using its derivation seeds
    - Canonical bump: always use the highest valid bump for determinism

PREREQUISITE SCRIPTS:
    - solana/fundamentals/01_accounts_model.py (account structure and ownership)
    - solana/fundamentals/03_programs.py (program model and instruction processing)
    - core/fundamentals/02_public_key_crypto.py (elliptic curve basics)

REAL-WORLD RELEVANCE:
    Every Solana DeFi protocol uses PDAs — escrow accounts in DEXes, vault
    accounts in lending protocols, metadata accounts in NFT programs. CPIs
    enable the composability that makes DeFi possible: one program can call
    another atomically within a single transaction.
"""

import hashlib
import struct

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# The "magic" suffix appended during PDA derivation — this is a real Solana constant.
# It ensures PDA derivation is domain-separated from normal key generation.
PDA_MARKER = b"ProgramDerivedAddress"

# Maximum bump seed value — we iterate from 255 down to 0
MAX_BUMP = 255

# secp256k1 curve order — a PDA must NOT be a valid point on this curve.
# In real Solana, this uses ed25519. We simulate by checking if the hash
# modulo the curve order equals zero (simplified off-curve check).
# Real curve order for ed25519:
ED25519_ORDER = (2**252 + 27742317777372353535851937790883648493)

# Maximum CPI depth — Solana limits how deep programs can call each other
# to prevent infinite recursion. Real limit is 4.
MAX_CPI_DEPTH = 4

# Simulated program IDs — in real Solana these are base58-encoded public keys
SYSTEM_PROGRAM = "11111111111111111111111111111111"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ESCROW_PROGRAM = "EscrowProgramXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
VAULT_PROGRAM = "VaultProgramYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY"


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: PDA derivation — finding addresses that are OFF the elliptic curve
# ----------------------------------------------------------------------------

def hash_seeds(seeds, program_id):
    """Hash seeds together with program ID and PDA marker.

    Real derivation: SHA-256(seed1 || seed2 || ... || program_id || "ProgramDerivedAddress")
    The result is checked against the elliptic curve — it must NOT be a valid point.
    """
    hasher = hashlib.sha256()
    for seed in seeds:
        if isinstance(seed, str):
            seed = seed.encode()        # Convert strings to bytes
        elif isinstance(seed, int):
            seed = bytes([seed])        # Single byte for bump seeds
        hasher.update(seed)
    hasher.update(program_id.encode())  # Program ID determines which program "owns" this PDA
    hasher.update(PDA_MARKER)           # Domain separator prevents collision with normal keys
    return hasher.digest()


def is_on_curve(hash_bytes):
    """Check if a hash corresponds to a valid point on the elliptic curve.

    In real Solana, this checks if the 32-byte hash is a valid ed25519 public key.
    We simulate this: if the hash interpreted as an integer is divisible by a
    specific factor, we consider it "on curve" (roughly ~50% of hashes pass).
    """
    # Interpret the hash as a big integer
    value = int.from_bytes(hash_bytes, "big")
    # Simplified check: if the last byte is even, we say it's "on curve"
    # This gives roughly 50% on-curve rate, similar to real ed25519
    return (value % 2) == 0


def find_program_address(seeds, program_id):
    """Find a PDA by iterating bump seeds from 255 down to 0.

    The bump seed is appended to the seeds list. We try 255, 254, 253...
    until we find a hash that is NOT a valid curve point. The first valid
    bump found is the "canonical bump" — always use this one for determinism.

    Returns: (address_hex, bump_seed, attempts)
    """
    for bump in range(MAX_BUMP, -1, -1):  # 255, 254, ..., 0
        # Append bump as the last seed
        candidate_hash = hash_seeds(seeds + [bump], program_id)

        if not is_on_curve(candidate_hash):
            # Found a valid PDA — this hash is NOT on the curve
            address = candidate_hash.hex()[:40]  # Truncate for display
            return address, bump, MAX_BUMP - bump + 1

    raise ValueError("Could not find valid PDA — all 256 bumps were on-curve")


def create_program_address(seeds, program_id):
    """Create a PDA with a known bump seed (no search needed).

    Used when the bump is already known — skips the iteration.
    Raises an error if the result IS on the curve (invalid PDA).
    """
    candidate_hash = hash_seeds(seeds, program_id)

    if is_on_curve(candidate_hash):
        raise ValueError("Seeds produce an on-curve address — not a valid PDA")

    return candidate_hash.hex()[:40]


# ----------------------------------------------------------------------------
# 2b: Account — simplified Solana account for PDA demonstration
# ----------------------------------------------------------------------------

class Account:
    """A Solana account that can be owned by a program and hold data."""

    def __init__(self, address, owner, lamports=0, data=None, is_signer=False):
        self.address = address          # Account public key (or PDA)
        self.owner = owner              # Program that owns this account
        self.lamports = lamports        # SOL balance in lamports
        self.data = data or {}          # Account data (arbitrary bytes, stored as dict)
        self.is_signer = is_signer      # Whether this account signed the transaction
        self.is_pda = False             # Set to True if this is a PDA
        self.pda_seeds = None           # Seeds used to derive this PDA
        self.pda_bump = None            # Bump seed for this PDA

    def __repr__(self):
        pda_tag = " [PDA]" if self.is_pda else ""
        return f"Account({self.address[:12]}...{pda_tag}, {self.lamports} lamports)"


# ----------------------------------------------------------------------------
# 2c: Program — simulates a Solana program that uses PDAs and CPIs
# ----------------------------------------------------------------------------

class Program:
    """A simulated Solana program that can derive PDAs and invoke CPIs."""

    def __init__(self, program_id, name):
        self.program_id = program_id
        self.name = name
        self.accounts = {}              # Accounts owned by this program
        self.cpi_log = []               # Log of CPI calls made

    def derive_pda(self, seeds):
        """Derive a PDA owned by this program."""
        address, bump, attempts = find_program_address(seeds, self.program_id)
        return address, bump, attempts

    def create_pda_account(self, seeds, lamports=0, data=None):
        """Create a PDA-owned account — only this program can modify it."""
        address, bump, attempts = self.derive_pda(seeds)

        account = Account(
            address=address,
            owner=self.program_id,
            lamports=lamports,
            data=data or {},
        )
        account.is_pda = True
        account.pda_seeds = seeds
        account.pda_bump = bump

        self.accounts[address] = account
        return account, bump, attempts

    def invoke_cpi(self, target_program, instruction, accounts, signer_seeds=None,
                   depth=0):
        """Invoke another program via CPI.

        If signer_seeds is provided, the PDA derived from those seeds
        is marked as a signer — this is how PDAs "sign" transactions.
        The runtime verifies that the seeds + bump actually derive to
        the PDA address, ensuring only the owning program can sign.
        """
        if depth >= MAX_CPI_DEPTH:
            raise RecursionError(
                f"CPI depth {depth} exceeds maximum of {MAX_CPI_DEPTH}")

        cpi_record = {
            "caller": self.name,
            "target": target_program.name,
            "instruction": instruction,
            "depth": depth,
            "signer_seeds": signer_seeds,
            "pda_signer": None,
        }

        # If signer seeds are provided, verify the PDA and mark it as signer
        if signer_seeds is not None:
            pda_address, bump, _ = find_program_address(
                signer_seeds, self.program_id)
            cpi_record["pda_signer"] = pda_address

            # Mark the PDA account as a signer for this CPI call
            for acc in accounts:
                if acc.address == pda_address:
                    acc.is_signer = True  # PDA is now a "signer" in this CPI

        self.cpi_log.append(cpi_record)

        # Execute the target program's instruction
        result = target_program.process_instruction(
            instruction, accounts, depth + 1)

        return result

    def process_instruction(self, instruction, accounts, depth=0):
        """Process an instruction — override in specific program implementations."""
        return {"status": "ok", "instruction": instruction, "depth": depth}


# ----------------------------------------------------------------------------
# 2d: Escrow program — demonstrates PDA as an escrow authority
# ----------------------------------------------------------------------------

class EscrowProgram(Program):
    """An escrow program that uses a PDA to hold funds trustlessly.

    The PDA acts as the escrow authority — it holds tokens until conditions
    are met, then the program releases them via CPI with PDA signer seeds.
    No human holds the private key; only the program can authorize releases.
    """

    def __init__(self):
        super().__init__(ESCROW_PROGRAM, "Escrow")
        self.escrows = {}  # Active escrows: {escrow_id: details}

    def initialize_escrow(self, escrow_id, depositor, amount, recipient):
        """Create a new escrow with a PDA as the authority.

        Seeds: ["escrow", escrow_id] — deterministic and unique per escrow.
        """
        seeds = ["escrow", escrow_id]
        pda_account, bump, attempts = self.create_pda_account(
            seeds=seeds,
            lamports=amount,
            data={
                "escrow_id": escrow_id,
                "depositor": depositor,
                "recipient": recipient,
                "amount": amount,
                "state": "initialized",
            }
        )

        self.escrows[escrow_id] = {
            "pda": pda_account,
            "bump": bump,
            "seeds": seeds,
        }

        return pda_account, bump, attempts

    def release_escrow(self, escrow_id, token_program):
        """Release escrowed funds via CPI — PDA signs the transfer.

        The escrow PDA "signs" the CPI call to the token program using
        its derivation seeds + bump. This is how the program authorizes
        the transfer without any human private key.
        """
        escrow = self.escrows[escrow_id]
        pda_account = escrow["pda"]

        # The signer seeds include the bump — this is required for CPI
        signer_seeds = escrow["seeds"] + [escrow["bump"]]

        # Create recipient account
        recipient = Account(
            address=hashlib.sha256(
                pda_account.data["recipient"].encode()).hexdigest()[:40],
            owner=TOKEN_PROGRAM,
            lamports=0,
        )

        # CPI: escrow program calls token program to transfer funds
        # PDA signs the transfer using its derivation seeds
        result = self.invoke_cpi(
            target_program=token_program,
            instruction={
                "type": "transfer",
                "from": pda_account.address,
                "to": recipient.address,
                "amount": pda_account.data["amount"],
            },
            accounts=[pda_account, recipient],
            signer_seeds=signer_seeds[:-1],  # Seeds without bump for derivation
        )

        # Update escrow state
        pda_account.data["state"] = "released"
        pda_account.lamports = 0

        return result, recipient


# ----------------------------------------------------------------------------
# 2e: Token program — simplified SPL token program for CPI targets
# ----------------------------------------------------------------------------

class TokenProgram(Program):
    """Simplified token program that processes transfer instructions via CPI."""

    def __init__(self):
        super().__init__(TOKEN_PROGRAM, "Token")

    def process_instruction(self, instruction, accounts, depth=0):
        """Process a token transfer instruction."""
        if instruction["type"] == "transfer":
            from_acc = accounts[0]
            to_acc = accounts[1]
            amount = instruction["amount"]

            # Verify the sender signed the transaction (or is a PDA signer)
            if not from_acc.is_signer:
                return {"status": "error", "message": "Missing required signature"}

            # Execute the transfer
            from_acc.lamports -= amount
            to_acc.lamports += amount

            return {
                "status": "ok",
                "type": "transfer",
                "from": from_acc.address[:12],
                "to": to_acc.address[:12],
                "amount": amount,
                "depth": depth,
            }

        return {"status": "error", "message": f"Unknown instruction: {instruction}"}


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of PDAs and CPIs."""
    print("=" * 72)
    print("  PDAs & CROSS-PROGRAM INVOCATIONS — Deep Dive")
    print("=" * 72)

    # --- Step 1: PDA Derivation —  bump seed search ---
    print("\n─── Step 1: PDA Derivation (Bump Seed Search) ───────────────────────")
    print("Finding an address that is NOT on the elliptic curve...\n")

    seeds = ["escrow", "order-001"]
    program_id = ESCROW_PROGRAM

    print(f"  Seeds:      {seeds}")
    print(f"  Program ID: {program_id[:20]}...")
    print(f"  Searching bump from 255 down to 0...\n")

    # Show the search process
    found = False
    for bump in range(MAX_BUMP, MAX_BUMP - 10, -1):  # Show first 10 attempts
        candidate = hash_seeds(seeds + [bump], program_id)
        on_curve = is_on_curve(candidate)
        status = "ON CURVE (skip)" if on_curve else "OFF CURVE (valid PDA!)"
        marker = "  " if on_curve else ">>"

        print(f"  {marker} bump={bump:>3} │ hash={candidate.hex()[:24]}... │ {status}")

        if not on_curve and not found:
            found = True
            canonical_bump = bump
            canonical_address = candidate.hex()[:40]

    # Get the actual canonical PDA
    address, bump, attempts = find_program_address(seeds, program_id)
    print(f"\n  Canonical PDA found:")
    print(f"  ┌─────────────────────────────────────────────────────┐")
    print(f"  │  Address: {address[:20]}...           │")
    print(f"  │  Bump:    {bump:>3}                                      │")
    print(f"  │  Search:  {attempts} attempt(s)                             │")
    print(f"  └─────────────────────────────────────────────────────┘")

    # --- Step 2: Multiple PDAs from different seeds ---
    print("\n─── Step 2: Deterministic PDA Derivation ────────────────────────────")
    print("Same seeds always produce the same PDA — different seeds, different PDAs\n")

    seed_examples = [
        (["vault", "user-alice"], VAULT_PROGRAM),
        (["vault", "user-bob"], VAULT_PROGRAM),
        (["vault", "user-alice"], ESCROW_PROGRAM),  # Same seeds, different program
        (["escrow", "order-001"], ESCROW_PROGRAM),
        (["escrow", "order-002"], ESCROW_PROGRAM),
    ]

    print(f"  {'Seeds':<30} {'Program':<12} {'Bump':>4} {'Address':<24}")
    print(f"  {'─' * 30} {'─' * 12} {'─' * 4} {'─' * 24}")

    for seeds_ex, prog_id in seed_examples:
        addr, b, _ = find_program_address(seeds_ex, prog_id)
        prog_name = "Escrow" if prog_id == ESCROW_PROGRAM else "Vault"
        seeds_str = str(seeds_ex)
        if len(seeds_str) > 28:
            seeds_str = seeds_str[:28] + ".."
        print(f"  {seeds_str:<30} {prog_name:<12} {b:>4} {addr[:24]}")

    # Verify determinism — same inputs produce same output
    addr1, b1, _ = find_program_address(["vault", "user-alice"], VAULT_PROGRAM)
    addr2, b2, _ = find_program_address(["vault", "user-alice"], VAULT_PROGRAM)
    match = "MATCH" if addr1 == addr2 else "MISMATCH"
    print(f"\n  Determinism check: derive same seeds twice → {match}")

    # --- Step 3: Escrow with PDA ---
    print("\n─── Step 3: Escrow Using PDA Authority ─────────────────────────────")
    print("PDA holds funds — no private key exists, only the program can sign\n")

    escrow = EscrowProgram()
    token = TokenProgram()

    pda_account, bump, attempts = escrow.initialize_escrow(
        escrow_id="order-42",
        depositor="Alice",
        amount=5_000_000_000,  # 5 SOL in lamports
        recipient="Bob",
    )

    print(f"  Escrow initialized:")
    print(f"  ┌─────────────────────────────────────────────────────┐")
    print(f"  │  Escrow ID:  order-42                               │")
    print(f"  │  PDA:        {pda_account.address[:20]}...           │")
    print(f"  │  Bump:       {bump}                                     │")
    print(f"  │  Depositor:  Alice                                  │")
    print(f"  │  Recipient:  Bob                                    │")
    print(f"  │  Amount:     5,000,000,000 lamports (5 SOL)         │")
    print(f"  │  State:      {pda_account.data['state']:<12}                         │")
    print(f"  └─────────────────────────────────────────────────────┘")

    print(f"\n  Why this is trustless:")
    print(f"    - No private key exists for {pda_account.address[:16]}...")
    print(f"    - The PDA is OFF the elliptic curve — no key can sign for it")
    print(f"    - ONLY the Escrow program can produce the signer seeds")
    print(f"    - The runtime verifies: SHA-256(seeds || program_id) == PDA address")

    # --- Step 4: CPI with PDA signer ---
    print("\n─── Step 4: CPI with PDA Signer ────────────────────────────────────")
    print("Escrow program releases funds via CPI to Token program...\n")

    print(f"  Execution flow:")
    print(f"  ┌──────────────┐    CPI     ┌───────────────┐")
    print(f"  │   Escrow     │───────────>│  Token        │")
    print(f"  │   Program    │            │  Program      │")
    print(f"  │              │  PDA signs │               │")
    print(f"  │  seeds+bump  │  transfer  │  from → to    │")
    print(f"  └──────────────┘            └───────────────┘")

    result, recipient = escrow.release_escrow("order-42", token)

    print(f"\n  CPI Result:")
    print(f"  ┌─────────────────────────────────────────────────────┐")
    print(f"  │  Status:      {result['status']:<10}                          │")
    print(f"  │  Type:        {result['type']:<10}                          │")
    print(f"  │  From (PDA):  {result['from']}...                      │")
    print(f"  │  To:          {result['to']}...                      │")
    print(f"  │  Amount:      5,000,000,000 lamports                │")
    print(f"  │  CPI Depth:   {result['depth']}                                │")
    print(f"  └─────────────────────────────────────────────────────┘")

    print(f"\n  Escrow state after release:")
    print(f"    PDA balance:  {pda_account.lamports} lamports (drained)")
    print(f"    PDA state:    {pda_account.data['state']}")
    print(f"    Bob received: {recipient.lamports:,} lamports")

    # --- Step 5: CPI call chain ---
    print("\n─── Step 5: CPI Call Chain (Nested Invocations) ─────────────────────")
    print(f"Programs can CPI into other programs (max depth: {MAX_CPI_DEPTH})...\n")

    # Create a chain of programs calling each other
    program_a = Program("ProgramAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "ProgramA")
    program_b = Program("ProgramBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", "ProgramB")
    program_c = Program("ProgramCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC", "ProgramC")

    dummy_account = Account("dummy", SYSTEM_PROGRAM, 1000)

    # A calls B (depth 0 → 1)
    print(f"  ProgramA → CPI → ProgramB (depth 0 → 1)")
    r1 = program_a.invoke_cpi(program_b, {"type": "action1"}, [dummy_account],
                              depth=0)
    print(f"    Result: {r1['status']} (depth {r1['depth']})")

    # B calls C (depth 1 → 2)
    print(f"  ProgramB → CPI → ProgramC (depth 1 → 2)")
    r2 = program_b.invoke_cpi(program_c, {"type": "action2"}, [dummy_account],
                              depth=1)
    print(f"    Result: {r2['status']} (depth {r2['depth']})")

    # Try exceeding max depth
    print(f"\n  Attempting CPI at depth {MAX_CPI_DEPTH} (exceeds maximum)...")
    try:
        program_a.invoke_cpi(program_b, {"type": "too-deep"}, [dummy_account],
                             depth=MAX_CPI_DEPTH)
    except RecursionError as e:
        print(f"    Error: {e}")

    print(f"\n  CPI depth limits prevent infinite recursion between programs")

    # --- Step 6: CPI log ---
    print("\n─── Step 6: CPI Audit Log ──────────────────────────────────────────")
    print("All CPI calls are logged for transparency:\n")

    all_logs = (escrow.cpi_log + program_a.cpi_log + program_b.cpi_log)

    print(f"  {'#':<3} {'Caller':<10} {'Target':<10} {'Depth':>5} "
          f"{'PDA Signer':<24} {'Instruction'}")
    print(f"  {'─' * 3} {'─' * 10} {'─' * 10} {'─' * 5} {'─' * 24} {'─' * 20}")

    for i, log in enumerate(all_logs):
        pda = log["pda_signer"][:20] + ".." if log["pda_signer"] else "None"
        instr = str(log["instruction"].get("type", ""))[:18]
        print(f"  {i + 1:<3} {log['caller']:<10} {log['target']:<10} "
              f"{log['depth']:>5} {pda:<24} {instr}")

    print("\n" + "=" * 72)
    print("  KEY TAKEAWAYS")
    print("=" * 72)
    print("  1. PDAs are addresses OFF the curve — no private key exists")
    print("  2. Bump seed search: try 255→0 until hash is off-curve")
    print("  3. Same seeds + program_id always produce the same PDA")
    print("  4. PDAs 'sign' via CPI when the program provides signer seeds")
    print("  5. CPI depth is limited to 4 to prevent infinite recursion")
    print("  6. PDAs enable trustless escrows, vaults, and protocol-owned accounts")
    print("=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
