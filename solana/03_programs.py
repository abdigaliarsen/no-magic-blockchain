"""
TITLE: Stateless Programs (Smart Contracts)
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    Solana's stateless program model from scratch. Programs don't store state
    internally — instead, they receive accounts as inputs and modify them.
    Includes instruction processing, account validation, and Cross-Program
    Invocation (CPI) where one program calls another.

KEY CONCEPTS:
    - Stateless programs: code is separate from data (accounts hold all state)
    - Instructions: program_id + account keys (with signer/writable flags) + data
    - Program entrypoint: process_instruction(program_id, accounts, data)
    - Cross-Program Invocation (CPI): one program invokes another's entrypoint

PREREQUISITE SCRIPTS:
    - solana/01_accounts_model.py (account structure and ownership rules)
    - core/01_hashing.py (SHA-256 fundamentals)

REAL-WORLD RELEVANCE:
    Every Solana smart contract follows this model. Programs like the Token
    Program, Associated Token Account Program, and Metaplex are all stateless
    programs that operate on accounts passed to them. CPI enables composability
    — the DeFi "money legos" pattern.
"""

import hashlib
import struct
import json

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# System program ID — handles account creation, transfers, ownership
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111111111111111"

# Maximum instruction data size in bytes
MAX_INSTRUCTION_DATA = 1024

# Maximum accounts per instruction
MAX_ACCOUNTS_PER_IX = 32

# Maximum CPI depth — prevents infinite recursion
MAX_CPI_DEPTH = 4

# Counter program instruction codes (like function selectors in Ethereum)
COUNTER_IX_INITIALIZE = 0  # Create and initialize counter
COUNTER_IX_INCREMENT = 1   # Increment counter by 1
COUNTER_IX_DECREMENT = 2   # Decrement counter by 1
COUNTER_IX_SET = 3         # Set counter to specific value

# Proxy program instruction codes
PROXY_IX_INCREMENT_VIA_CPI = 0  # Call counter program's increment via CPI


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: Account structure (simplified from 01_accounts_model.py)
# ----------------------------------------------------------------------------

class AccountInfo:
    """Runtime view of an account passed to a program.

    Programs see accounts through this lens — they can read/write data
    and lamports, but only if the account is marked writable and the
    program is the owner.
    """

    def __init__(self, pubkey, is_signer, is_writable, owner, lamports, data):
        self.pubkey = pubkey          # Account's public key
        self.is_signer = is_signer    # Did this account sign the transaction?
        self.is_writable = is_writable  # Can this account be modified?
        self.owner = owner            # Program that owns this account
        self.lamports = lamports      # Balance in lamports
        self.data = bytearray(data)   # Mutable byte array for state

    def __repr__(self):
        short = self.pubkey[:8]
        return (f"AccountInfo({short}..., signer={self.is_signer}, "
                f"writable={self.is_writable}, lamports={self.lamports})")


class AccountMeta:
    """Metadata about an account reference in an instruction.

    This tells the runtime HOW the account will be used (read vs write,
    signer vs non-signer) so it can enforce access rules.
    """

    def __init__(self, pubkey, is_signer=False, is_writable=False):
        self.pubkey = pubkey
        self.is_signer = is_signer      # Must this account have signed?
        self.is_writable = is_writable  # Will this account be modified?

    def __repr__(self):
        flags = []
        if self.is_signer:
            flags.append("signer")
        if self.is_writable:
            flags.append("writable")
        return f"AccountMeta({self.pubkey[:8]}..., {', '.join(flags)})"


# ----------------------------------------------------------------------------
# 2b: Instruction structure
# ----------------------------------------------------------------------------

class Instruction:
    """A single instruction to be processed by a program.

    On Solana, transactions contain one or more instructions. Each instruction
    specifies which program to call, which accounts to pass, and what data
    (the "calldata") to send.
    """

    def __init__(self, program_id, accounts, data):
        """
        Args:
            program_id: Pubkey of the program to invoke
            accounts: List of AccountMeta describing account references
            data: Bytes containing the instruction payload
        """
        self.program_id = program_id
        self.accounts = accounts  # List[AccountMeta]
        self.data = data          # bytes — program-specific payload


# ----------------------------------------------------------------------------
# 2c: Runtime — processes instructions and enforces rules
# ----------------------------------------------------------------------------

class ProgramRuntime:
    """Simulated Solana runtime that processes instructions.

    The runtime is responsible for:
    1. Loading accounts from state
    2. Validating signer/writable permissions
    3. Invoking the target program's entrypoint
    4. Committing account changes back to state
    """

    def __init__(self):
        self.accounts = {}          # Global account state: pubkey → dict
        self.programs = {}          # Registered programs: program_id → callable
        self.cpi_depth = 0          # Current CPI recursion depth
        self.execution_log = []     # Log of program invocations for demo output

    def register_program(self, program_id, process_fn):
        """Register a program's entrypoint function.

        In real Solana, programs are BPF bytecode deployed to executable
        accounts. Here we register Python functions for clarity.
        """
        self.programs[program_id] = process_fn
        # Create an executable account for the program
        self.accounts[program_id] = {
            "pubkey": program_id,
            "owner": "BPFLoader",      # Programs are owned by the BPF loader
            "lamports": 0,
            "data": b"",
            "executable": True,
        }

    def create_account(self, pubkey, owner, lamports=0, data_size=0):
        """Create a new account in the global state."""
        self.accounts[pubkey] = {
            "pubkey": pubkey,
            "owner": owner,
            "lamports": lamports,
            "data": bytearray(data_size),
            "executable": False,
        }

    def process_instruction(self, instruction, signers=None):
        """Process a single instruction — the core of the runtime.

        Steps:
        1. Look up the target program
        2. Load and validate all referenced accounts
        3. Call the program's entrypoint
        4. Commit changes back to global state
        """
        if signers is None:
            signers = set()

        program_id = instruction.program_id

        # Step 1: Find the program
        if program_id not in self.programs:
            raise ValueError(f"Program {program_id[:12]}... not found")

        # Step 2: Load accounts and build AccountInfo list
        account_infos = []
        for meta in instruction.accounts:
            acct_data = self.accounts.get(meta.pubkey)
            if acct_data is None:
                raise ValueError(f"Account {meta.pubkey[:12]}... not found")

            # Validate signer requirement
            if meta.is_signer and meta.pubkey not in signers:
                raise PermissionError(
                    f"Account {meta.pubkey[:12]}... must be a signer"
                )

            # Build the AccountInfo view that the program will see
            info = AccountInfo(
                pubkey=meta.pubkey,
                is_signer=meta.is_signer,
                is_writable=meta.is_writable,
                owner=acct_data["owner"],
                lamports=acct_data["lamports"],
                data=acct_data["data"],
            )
            account_infos.append(info)

        # Step 3: Invoke the program's entrypoint
        indent = "  " * (self.cpi_depth + 1)
        self.execution_log.append(
            f"{indent}→ Invoke [{program_id[:16]}...] "
            f"with {len(account_infos)} accounts"
        )

        process_fn = self.programs[program_id]
        process_fn(program_id, account_infos, instruction.data, self)

        # Step 4: Commit changes from AccountInfo back to global state
        for meta, info in zip(instruction.accounts, account_infos):
            acct_data = self.accounts[meta.pubkey]

            if meta.is_writable:
                # Ownership check: only the owner program can modify data
                if info.data != bytearray(acct_data["data"]):
                    if acct_data["owner"] != program_id:
                        raise PermissionError(
                            f"Program {program_id[:12]}... cannot modify "
                            f"account owned by {acct_data['owner'][:12]}..."
                        )

                # Commit changes
                acct_data["lamports"] = info.lamports
                acct_data["data"] = bytes(info.data)

        self.execution_log.append(f"{indent}✓ Success")

    def invoke_cpi(self, instruction, account_infos_from_caller):
        """Cross-Program Invocation — one program calls another.

        CPI is how Solana achieves composability. The calling program
        passes along account references to the called program.

        Rules:
        - Max CPI depth is 4 (prevents infinite recursion)
        - Signer privileges can be extended (but not fabricated)
        - The caller's writable/signer flags are inherited
        """
        if self.cpi_depth >= MAX_CPI_DEPTH:
            raise RuntimeError(
                f"CPI depth exceeded: {self.cpi_depth} >= {MAX_CPI_DEPTH}"
            )

        # Build a lookup of the caller's account infos
        caller_accounts = {ai.pubkey: ai for ai in account_infos_from_caller}

        # Collect signers — accounts that signed the original transaction
        signers = {
            ai.pubkey for ai in account_infos_from_caller if ai.is_signer
        }

        self.cpi_depth += 1
        try:
            self.process_instruction(instruction, signers=signers)
        finally:
            self.cpi_depth -= 1

        # After CPI, update the caller's account infos with any changes
        for meta in instruction.accounts:
            if meta.pubkey in caller_accounts:
                updated = self.accounts[meta.pubkey]
                caller_ai = caller_accounts[meta.pubkey]
                caller_ai.lamports = updated["lamports"]
                caller_ai.data = bytearray(updated["data"])


# ----------------------------------------------------------------------------
# 2d: Counter program — a simple stateful program
# ----------------------------------------------------------------------------

COUNTER_PROGRAM_ID = "CounterProg" + "0" * 33  # 44 chars

def process_counter(program_id, accounts, instruction_data, runtime):
    """Entrypoint for the Counter program.

    This program manages a simple u64 counter stored in an account.
    It demonstrates the pattern of reading/writing account data.

    Instruction layout:
        byte 0: instruction code (0=init, 1=increment, 2=decrement, 3=set)
        bytes 1-8: value (only for 'set' instruction)
    """
    if len(instruction_data) < 1:
        raise ValueError("Counter: missing instruction code")

    ix_code = instruction_data[0]  # First byte is the instruction discriminator

    if ix_code == COUNTER_IX_INITIALIZE:
        # Initialize a new counter account
        if len(accounts) < 2:
            raise ValueError("Counter init: need [counter_account, payer]")

        counter_acct = accounts[0]  # Account to store the counter
        payer = accounts[1]         # Who's paying (must be signer)

        if not payer.is_signer:
            raise PermissionError("Counter init: payer must sign")
        if not counter_acct.is_writable:
            raise PermissionError("Counter init: counter must be writable")

        # Initialize counter to 0 (write u64 little-endian)
        struct.pack_into("<Q", counter_acct.data, 0, 0)

    elif ix_code == COUNTER_IX_INCREMENT:
        # Increment the counter by 1
        if len(accounts) < 1:
            raise ValueError("Counter increment: need [counter_account]")

        counter_acct = accounts[0]
        if not counter_acct.is_writable:
            raise PermissionError("Counter increment: counter must be writable")

        # Read current value, add 1, write back
        current = struct.unpack_from("<Q", counter_acct.data, 0)[0]
        struct.pack_into("<Q", counter_acct.data, 0, current + 1)

    elif ix_code == COUNTER_IX_DECREMENT:
        # Decrement the counter by 1
        if len(accounts) < 1:
            raise ValueError("Counter decrement: need [counter_account]")

        counter_acct = accounts[0]
        if not counter_acct.is_writable:
            raise PermissionError("Counter decrement: counter must be writable")

        current = struct.unpack_from("<Q", counter_acct.data, 0)[0]
        if current == 0:
            raise ValueError("Counter decrement: already at zero")
        struct.pack_into("<Q", counter_acct.data, 0, current - 1)

    elif ix_code == COUNTER_IX_SET:
        # Set counter to a specific value (requires signer authority)
        if len(accounts) < 2:
            raise ValueError("Counter set: need [counter_account, authority]")
        if len(instruction_data) < 9:
            raise ValueError("Counter set: need 8 bytes for value")

        counter_acct = accounts[0]
        authority = accounts[1]

        if not authority.is_signer:
            raise PermissionError("Counter set: authority must sign")
        if not counter_acct.is_writable:
            raise PermissionError("Counter set: counter must be writable")

        # Read the desired value from instruction data (bytes 1-8)
        value = struct.unpack_from("<Q", instruction_data, 1)[0]
        struct.pack_into("<Q", counter_acct.data, 0, value)

    else:
        raise ValueError(f"Counter: unknown instruction {ix_code}")


# ----------------------------------------------------------------------------
# 2e: Proxy program — demonstrates Cross-Program Invocation (CPI)
# ----------------------------------------------------------------------------

PROXY_PROGRAM_ID = "ProxyProgram" + "0" * 32  # 44 chars

def process_proxy(program_id, accounts, instruction_data, runtime):
    """Entrypoint for the Proxy program.

    This program doesn't manage any state itself — it demonstrates CPI
    by forwarding calls to the Counter program. In real Solana, this
    pattern is used everywhere: DEX aggregators calling AMMs, lending
    protocols calling token programs, etc.

    Instruction layout:
        byte 0: proxy instruction code
    """
    if len(instruction_data) < 1:
        raise ValueError("Proxy: missing instruction code")

    ix_code = instruction_data[0]

    if ix_code == PROXY_IX_INCREMENT_VIA_CPI:
        # Forward an increment call to the counter program via CPI
        if len(accounts) < 2:
            raise ValueError("Proxy CPI: need [counter_account, counter_program]")

        counter_acct = accounts[0]
        counter_program = accounts[1]  # The counter program's account

        # Read current value before CPI for logging
        before = struct.unpack_from("<Q", counter_acct.data, 0)[0]

        # Build the CPI instruction — tells runtime to call the counter program
        cpi_instruction = Instruction(
            program_id=COUNTER_PROGRAM_ID,
            accounts=[
                # Pass the counter account as writable (same flags as we received)
                AccountMeta(
                    counter_acct.pubkey,
                    is_signer=False,
                    is_writable=True,
                ),
            ],
            data=bytes([COUNTER_IX_INCREMENT]),  # Increment instruction
        )

        # Execute CPI — this calls process_counter through the runtime
        runtime.invoke_cpi(cpi_instruction, accounts)

        # Read value after CPI to confirm it changed
        after = struct.unpack_from("<Q", counter_acct.data, 0)[0]
        runtime.execution_log.append(
            f"    (Proxy: counter {before} → {after} via CPI)"
        )

    else:
        raise ValueError(f"Proxy: unknown instruction {ix_code}")


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Solana's stateless program model."""

    print("=" * 70)
    print("  SOLANA STATELESS PROGRAMS — From Scratch")
    print("=" * 70)

    # --- Setup ---------------------------------------------------------------
    runtime = ProgramRuntime()

    # Register our programs
    runtime.register_program(COUNTER_PROGRAM_ID, process_counter)
    runtime.register_program(PROXY_PROGRAM_ID, process_proxy)

    # Create user accounts
    alice_pubkey = "Alice" + "0" * 39          # 44 chars
    counter_pubkey = "CounterData" + "0" * 33  # 44 chars

    runtime.create_account(alice_pubkey, SYSTEM_PROGRAM_ID, lamports=10_000_000_000)
    runtime.create_account(counter_pubkey, COUNTER_PROGRAM_ID, data_size=8)

    # --- Instruction structure -----------------------------------------------
    print("\n--- 1. Instruction Structure ---\n")
    print("  A Solana instruction contains three things:")
    print("  ┌─────────────────────────────────────────────────┐")
    print("  │  program_id:  which program to call             │")
    print("  │  accounts:    list of accounts + access flags   │")
    print("  │  data:        bytes payload (program-specific)  │")
    print("  └─────────────────────────────────────────────────┘")
    print()
    print("  Account access flags:")
    print("  • is_signer:   account must have signed the transaction")
    print("  • is_writable: account's data/lamports may be modified")

    # --- Initialize counter --------------------------------------------------
    print("\n--- 2. Initialize Counter ---\n")

    init_ix = Instruction(
        program_id=COUNTER_PROGRAM_ID,
        accounts=[
            AccountMeta(counter_pubkey, is_signer=False, is_writable=True),
            AccountMeta(alice_pubkey, is_signer=True, is_writable=False),
        ],
        data=bytes([COUNTER_IX_INITIALIZE]),  # Instruction code 0 = initialize
    )

    runtime.process_instruction(init_ix, signers={alice_pubkey})

    counter_data = runtime.accounts[counter_pubkey]["data"]
    value = struct.unpack_from("<Q", counter_data, 0)[0]
    print(f"  Counter initialized to: {value}")
    print(f"\n  Execution log:")
    for line in runtime.execution_log:
        print(f"  {line}")
    runtime.execution_log.clear()

    # --- Increment counter ---------------------------------------------------
    print("\n--- 3. Increment Counter (3 times) ---\n")

    for i in range(3):
        inc_ix = Instruction(
            program_id=COUNTER_PROGRAM_ID,
            accounts=[
                AccountMeta(counter_pubkey, is_signer=False, is_writable=True),
            ],
            data=bytes([COUNTER_IX_INCREMENT]),
        )
        runtime.process_instruction(inc_ix, signers=set())

        counter_data = runtime.accounts[counter_pubkey]["data"]
        value = struct.unpack_from("<Q", counter_data, 0)[0]
        print(f"  Increment #{i+1}: counter = {value}")

    print(f"\n  Execution log:")
    for line in runtime.execution_log:
        print(f"  {line}")
    runtime.execution_log.clear()

    # --- Set counter (requires signer) ---------------------------------------
    print("\n--- 4. Set Counter (Requires Authority) ---\n")

    # Set counter to 100
    set_data = bytes([COUNTER_IX_SET]) + struct.pack("<Q", 100)
    set_ix = Instruction(
        program_id=COUNTER_PROGRAM_ID,
        accounts=[
            AccountMeta(counter_pubkey, is_signer=False, is_writable=True),
            AccountMeta(alice_pubkey, is_signer=True, is_writable=False),
        ],
        data=set_data,
    )
    runtime.process_instruction(set_ix, signers={alice_pubkey})

    counter_data = runtime.accounts[counter_pubkey]["data"]
    value = struct.unpack_from("<Q", counter_data, 0)[0]
    print(f"  Set counter to: {value}")

    # Try without signer — should fail
    print(f"\n  Attempting set without signer...")
    try:
        set_ix_nosign = Instruction(
            program_id=COUNTER_PROGRAM_ID,
            accounts=[
                AccountMeta(counter_pubkey, is_signer=False, is_writable=True),
                AccountMeta(alice_pubkey, is_signer=True, is_writable=False),
            ],
            data=bytes([COUNTER_IX_SET]) + struct.pack("<Q", 999),
        )
        runtime.process_instruction(set_ix_nosign, signers=set())  # No signers!
    except PermissionError as e:
        print(f"  ✗ Blocked: {e}")

    runtime.execution_log.clear()

    # --- Ownership enforcement -----------------------------------------------
    print("\n--- 5. Ownership Enforcement ---\n")

    # Try to modify counter from a program that doesn't own it
    rogue_program_id = "RogueProgram" + "0" * 32
    runtime.register_program(rogue_program_id, lambda pid, accts, data, rt:
        struct.pack_into("<Q", accts[0].data, 0, 99999))

    print("  Rogue program tries to modify counter account...")
    try:
        rogue_ix = Instruction(
            program_id=rogue_program_id,
            accounts=[
                AccountMeta(counter_pubkey, is_signer=False, is_writable=True),
            ],
            data=b"\x00",
        )
        runtime.process_instruction(rogue_ix, signers=set())
    except PermissionError as e:
        print(f"  ✗ Blocked: {e}")

    print(f"\n  Counter value unchanged: "
          f"{struct.unpack_from('<Q', runtime.accounts[counter_pubkey]['data'], 0)[0]}")
    runtime.execution_log.clear()

    # --- Cross-Program Invocation (CPI) --------------------------------------
    print("\n--- 6. Cross-Program Invocation (CPI) ---\n")

    print("  The Proxy program calls the Counter program via CPI:")
    print("  ┌──────────────┐     CPI      ┌──────────────────┐")
    print("  │ Proxy Program│ ──────────→   │ Counter Program  │")
    print("  │ (no state)   │              │ (modifies data)  │")
    print("  └──────────────┘              └──────────────────┘")
    print()

    # Read counter before CPI
    before = struct.unpack_from(
        "<Q", runtime.accounts[counter_pubkey]["data"], 0
    )[0]

    # Call proxy program, which internally calls counter program
    cpi_ix = Instruction(
        program_id=PROXY_PROGRAM_ID,
        accounts=[
            AccountMeta(counter_pubkey, is_signer=False, is_writable=True),
            AccountMeta(COUNTER_PROGRAM_ID, is_signer=False, is_writable=False),
        ],
        data=bytes([PROXY_IX_INCREMENT_VIA_CPI]),
    )
    runtime.process_instruction(cpi_ix, signers=set())

    # Read counter after CPI
    after = struct.unpack_from(
        "<Q", runtime.accounts[counter_pubkey]["data"], 0
    )[0]

    print(f"  Counter before CPI: {before}")
    print(f"  Counter after CPI:  {after}")
    print(f"\n  Execution log (shows nested invocations):")
    for line in runtime.execution_log:
        print(f"  {line}")
    runtime.execution_log.clear()

    # --- Multiple CPI calls --------------------------------------------------
    print("\n--- 7. Multiple CPI Calls ---\n")

    print("  Calling proxy 5 more times to demonstrate repeated CPI:")
    for i in range(5):
        runtime.process_instruction(cpi_ix, signers=set())
        val = struct.unpack_from(
            "<Q", runtime.accounts[counter_pubkey]["data"], 0
        )[0]
        print(f"  CPI call #{i+1}: counter = {val}")

    runtime.execution_log.clear()

    # --- CPI depth limit -----------------------------------------------------
    print("\n--- 8. CPI Depth Limit ---\n")

    # Create a recursive program that calls itself
    recursive_prog_id = "RecursiveProg" + "0" * 31

    call_count = [0]  # Use list to allow mutation in closure

    def process_recursive(program_id, accounts, data, rt):
        call_count[0] += 1
        # Try to call itself again via CPI
        recursive_ix = Instruction(
            program_id=recursive_prog_id,
            accounts=[AccountMeta(accounts[0].pubkey, is_writable=True)],
            data=b"\x00",
        )
        rt.invoke_cpi(recursive_ix, accounts)

    runtime.register_program(recursive_prog_id, process_recursive)
    dummy_pubkey = "DummyAccount" + "0" * 32
    runtime.create_account(dummy_pubkey, recursive_prog_id, data_size=8)

    print(f"  Max CPI depth: {MAX_CPI_DEPTH}")
    print(f"  Recursive program tries to call itself infinitely...")
    try:
        recursive_ix = Instruction(
            program_id=recursive_prog_id,
            accounts=[AccountMeta(dummy_pubkey, is_signer=False, is_writable=True)],
            data=b"\x00",
        )
        runtime.process_instruction(recursive_ix, signers=set())
    except RuntimeError as e:
        print(f"  ✗ Stopped at depth {call_count[0]}: {e}")

    runtime.execution_log.clear()

    # --- Summary -------------------------------------------------------------
    print("\n--- Summary ---\n")

    print("  ┌──────────────────────────────────────────────────┐")
    print("  │           Solana Program Model                   │")
    print("  ├──────────────────────────────────────────────────┤")
    print("  │ • Programs are STATELESS (code only)            │")
    print("  │ • All state lives in ACCOUNTS                   │")
    print("  │ • Instructions specify program + accounts + data│")
    print("  │ • Only OWNER program can modify account data    │")
    print("  │ • CPI enables composability (max depth = 4)     │")
    print("  │ • Signer checks enforce authorization           │")
    print("  └──────────────────────────────────────────────────┘")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
