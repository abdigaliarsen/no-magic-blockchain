"""
TITLE: SPL Token Program
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    A simplified version of Solana's SPL Token program. Implements mint accounts
    (define a token's supply and authorities), token accounts (hold balances for
    a specific mint), and the core instructions: InitializeMint, InitializeAccount,
    MintTo, Transfer, and Burn.

KEY CONCEPTS:
    - Mint accounts control token supply and authorities
    - Token accounts hold per-user balances for a specific token
    - Authority checks enforce who can mint, transfer, and burn
    - Separation of mint authority vs token account ownership

PREREQUISITE SCRIPTS:
    - solana/01_accounts_model.py

REAL-WORLD RELEVANCE:
    The SPL Token program is Solana's standard for fungible tokens (like ERC-20 on
    Ethereum). USDC, USDT, and thousands of other tokens on Solana all use this
    program. Every DeFi protocol on Solana interacts with SPL Token accounts.
"""

import hashlib
import os

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"  # Real SPL Token program ID
MAX_SUPPLY = 2**64 - 1       # Maximum supply any token can have (u64 max)
DEFAULT_DECIMALS = 9          # Solana tokens typically use 9 decimal places

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --------------------------------------------------------------------------
# Mint Account — defines a token type
# --------------------------------------------------------------------------

class MintAccount:
    """Represents an SPL Token mint — the definition of a token.

    Controls total supply, decimal precision, and who can create new tokens.
    """

    def __init__(self, address: str, decimals: int, mint_authority: str,
                 freeze_authority: str | None = None):
        self.address = address                    # Unique mint address
        self.decimals = decimals                  # How many decimal places (e.g., 9 for SOL-like)
        self.supply = 0                           # Total tokens in circulation (raw units)
        self.mint_authority = mint_authority       # Who can mint new tokens (or None to disable)
        self.freeze_authority = freeze_authority   # Who can freeze token accounts (optional)
        self.is_initialized = True                # Mint has been set up

    def display_amount(self, raw_amount: int) -> str:
        """Convert raw token units to human-readable form with decimals."""
        if self.decimals == 0:
            return str(raw_amount)
        whole = raw_amount // (10 ** self.decimals)
        frac = raw_amount % (10 ** self.decimals)
        return f"{whole}.{str(frac).zfill(self.decimals).rstrip('0') or '0'}"


# --------------------------------------------------------------------------
# Token Account — holds a user's balance for one token type
# --------------------------------------------------------------------------

class TokenAccount:
    """Represents an SPL Token account — holds tokens for a specific mint.

    Each user needs a separate token account for each token type they hold.
    """

    def __init__(self, address: str, mint: str, owner: str):
        self.address = address    # Unique address of this token account
        self.mint = mint          # Which mint (token type) this account holds
        self.owner = owner        # Who controls this account (can transfer/burn)
        self.amount = 0           # Token balance in raw units
        self.is_frozen = False    # Whether transfers are frozen
        self.is_initialized = True


# --------------------------------------------------------------------------
# Token Program — processes instructions
# --------------------------------------------------------------------------

class TokenProgram:
    """The SPL Token program that processes all token instructions.

    This is a stateless program: it reads/writes to accounts passed to it,
    enforcing authority rules on every instruction.
    """

    def __init__(self):
        self.mints: dict[str, MintAccount] = {}           # address -> MintAccount
        self.token_accounts: dict[str, TokenAccount] = {} # address -> TokenAccount
        self.instruction_log: list[dict] = []             # Audit trail of all instructions

    def _generate_address(self, seed: str) -> str:
        """Generate a deterministic address from a seed string."""
        return hashlib.sha256(seed.encode()).hexdigest()[:44]

    def _log(self, instruction: str, details: dict, status: str = "OK"):
        """Record an instruction execution for the audit trail."""
        self.instruction_log.append({
            "instruction": instruction,
            "status": status,
            **details,
        })

    # --- InitializeMint ---

    def initialize_mint(self, mint_address: str, decimals: int,
                        mint_authority: str,
                        freeze_authority: str | None = None) -> MintAccount:
        """Create a new token type (mint).

        Only needs to be called once per token. Sets the authority who can
        create new supply and optionally freeze accounts.
        """
        if mint_address in self.mints:
            raise ValueError(f"Mint {mint_address} already exists")

        mint = MintAccount(mint_address, decimals, mint_authority, freeze_authority)
        self.mints[mint_address] = mint

        self._log("InitializeMint", {
            "mint": mint_address,
            "decimals": decimals,
            "mint_authority": mint_authority,
            "freeze_authority": freeze_authority or "(none)",
        })
        return mint

    # --- InitializeAccount ---

    def initialize_account(self, owner: str, mint_address: str,
                           account_seed: str | None = None) -> TokenAccount:
        """Create a token account that can hold tokens of the given mint.

        Each user needs one of these per token type they want to hold.
        """
        if mint_address not in self.mints:
            raise ValueError(f"Mint {mint_address} does not exist")

        # Generate a unique address for this token account
        seed = account_seed or f"{owner}:{mint_address}:{len(self.token_accounts)}"
        address = self._generate_address(seed)

        if address in self.token_accounts:
            raise ValueError(f"Token account {address} already exists")

        acct = TokenAccount(address, mint_address, owner)
        self.token_accounts[address] = acct

        self._log("InitializeAccount", {
            "account": address[:16] + "...",
            "mint": mint_address,
            "owner": owner,
        })
        return acct

    # --- MintTo ---

    def mint_to(self, mint_address: str, destination: str,
                amount: int, signer: str) -> None:
        """Mint new tokens into a destination token account.

        Only the mint_authority can call this. Increases total supply.
        """
        # Validate mint exists
        if mint_address not in self.mints:
            raise ValueError(f"Mint {mint_address} does not exist")
        mint = self.mints[mint_address]

        # Authority check: only mint_authority can create new tokens
        if mint.mint_authority != signer:
            self._log("MintTo", {"error": "unauthorized"}, status="FAILED")
            raise PermissionError(
                f"Signer '{signer}' is not the mint authority ('{mint.mint_authority}')"
            )

        # Validate destination account
        if destination not in self.token_accounts:
            raise ValueError(f"Token account {destination} does not exist")
        dest_acct = self.token_accounts[destination]

        # Destination must be for the same mint
        if dest_acct.mint != mint_address:
            raise ValueError("Destination account is for a different mint")

        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Credit the tokens
        dest_acct.amount += amount
        mint.supply += amount      # Track total supply across all accounts

        self._log("MintTo", {
            "mint": mint_address,
            "destination": destination[:16] + "...",
            "amount": amount,
            "new_supply": mint.supply,
            "signer": signer,
        })

    # --- Transfer ---

    def transfer(self, source: str, destination: str,
                 amount: int, signer: str) -> None:
        """Transfer tokens between two token accounts.

        Only the source account's owner can authorize the transfer.
        Both accounts must be for the same mint.
        """
        if source not in self.token_accounts:
            raise ValueError(f"Source account {source} does not exist")
        if destination not in self.token_accounts:
            raise ValueError(f"Destination account {destination} does not exist")

        src_acct = self.token_accounts[source]
        dst_acct = self.token_accounts[destination]

        # Authority check: only owner of the source account can transfer
        if src_acct.owner != signer:
            self._log("Transfer", {"error": "unauthorized"}, status="FAILED")
            raise PermissionError(
                f"Signer '{signer}' does not own source account (owner: '{src_acct.owner}')"
            )

        # Both accounts must hold the same token type
        if src_acct.mint != dst_acct.mint:
            raise ValueError("Source and destination are for different mints")

        if src_acct.is_frozen or dst_acct.is_frozen:
            raise ValueError("Cannot transfer to/from a frozen account")

        if amount <= 0:
            raise ValueError("Amount must be positive")

        if src_acct.amount < amount:
            raise ValueError(
                f"Insufficient balance: have {src_acct.amount}, need {amount}"
            )

        # Move tokens: debit source, credit destination
        src_acct.amount -= amount
        dst_acct.amount += amount

        self._log("Transfer", {
            "source": source[:16] + "...",
            "destination": destination[:16] + "...",
            "amount": amount,
            "signer": signer,
        })

    # --- Burn ---

    def burn(self, account: str, mint_address: str,
             amount: int, signer: str) -> None:
        """Burn (destroy) tokens from a token account, reducing total supply.

        Only the account owner can burn their own tokens.
        """
        if account not in self.token_accounts:
            raise ValueError(f"Token account {account} does not exist")
        if mint_address not in self.mints:
            raise ValueError(f"Mint {mint_address} does not exist")

        acct = self.token_accounts[account]
        mint = self.mints[mint_address]

        # Authority check: only account owner can burn
        if acct.owner != signer:
            self._log("Burn", {"error": "unauthorized"}, status="FAILED")
            raise PermissionError(
                f"Signer '{signer}' does not own account (owner: '{acct.owner}')"
            )

        if acct.mint != mint_address:
            raise ValueError("Account is not for the specified mint")

        if amount <= 0:
            raise ValueError("Amount must be positive")

        if acct.amount < amount:
            raise ValueError(
                f"Insufficient balance: have {acct.amount}, need {amount}"
            )

        # Destroy the tokens: debit account and reduce total supply
        acct.amount -= amount
        mint.supply -= amount

        self._log("Burn", {
            "account": account[:16] + "...",
            "mint": mint_address,
            "amount": amount,
            "new_supply": mint.supply,
            "signer": signer,
        })


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of the SPL Token program."""

    print("=" * 70)
    print("  SPL TOKEN PROGRAM (Simplified)")
    print("=" * 70)
    print()

    program = TokenProgram()

    # --- Step 1: Create the MAGIC token ---
    print("-" * 70)
    print("  STEP 1: Initialize Mint — Create the MAGIC token")
    print("-" * 70)
    print()

    mint = program.initialize_mint(
        mint_address="MAGIC",
        decimals=9,              # 9 decimal places like SOL
        mint_authority="Admin",  # Admin can create new tokens
        freeze_authority="Admin",
    )

    print("  ┌─────────────────────────────────────────────┐")
    print(f"  │ Mint: {mint.address:<39}│")
    print(f"  │ Decimals: {mint.decimals:<35}│")
    print(f"  │ Supply: {mint.display_amount(mint.supply):<37}│")
    print(f"  │ Mint Authority: {mint.mint_authority:<28}│")
    print(f"  │ Freeze Authority: {mint.freeze_authority:<26}│")
    print("  └─────────────────────────────────────────────┘")
    print()

    # --- Step 2: Create token accounts for Alice and Bob ---
    print("-" * 70)
    print("  STEP 2: Initialize Token Accounts for Alice and Bob")
    print("-" * 70)
    print()

    alice_acct = program.initialize_account("Alice", "MAGIC", "alice-magic-account")
    bob_acct = program.initialize_account("Bob", "MAGIC", "bob-magic-account")

    for name, acct in [("Alice", alice_acct), ("Bob", bob_acct)]:
        print(f"  {name}'s Token Account:")
        print(f"    address: {acct.address[:32]}...")
        print(f"    mint:    {acct.mint}")
        print(f"    owner:   {acct.owner}")
        print(f"    balance: {mint.display_amount(acct.amount)} MAGIC")
        print()

    # --- Step 3: Mint 1000 MAGIC to Alice ---
    print("-" * 70)
    print("  STEP 3: Mint 1,000 MAGIC to Alice")
    print("-" * 70)
    print()

    raw_amount = 1000 * (10 ** mint.decimals)  # Convert human amount to raw units
    program.mint_to("MAGIC", alice_acct.address, raw_amount, signer="Admin")

    print(f"  Admin mints 1,000 MAGIC → Alice")
    print(f"  Alice balance: {mint.display_amount(alice_acct.amount)} MAGIC")
    print(f"  Total supply:  {mint.display_amount(mint.supply)} MAGIC")
    print()

    # --- Step 3b: Unauthorized mint attempt ---
    print("  Attempting unauthorized mint (Bob tries to mint)...")
    try:
        program.mint_to("MAGIC", bob_acct.address, raw_amount, signer="Bob")
    except PermissionError as e:
        print(f"  ✗ REJECTED: {e}")
    print()

    # --- Step 4: Alice transfers 300 MAGIC to Bob ---
    print("-" * 70)
    print("  STEP 4: Alice Transfers 300 MAGIC to Bob")
    print("-" * 70)
    print()

    transfer_amount = 300 * (10 ** mint.decimals)
    program.transfer(alice_acct.address, bob_acct.address, transfer_amount, signer="Alice")

    print(f"  Alice → 300 MAGIC → Bob")
    print()
    print(f"  Alice balance: {mint.display_amount(alice_acct.amount)} MAGIC")
    print(f"  Bob balance:   {mint.display_amount(bob_acct.amount)} MAGIC")
    print(f"  Total supply:  {mint.display_amount(mint.supply)} MAGIC  (unchanged)")
    print()

    # --- Step 4b: Unauthorized transfer attempt ---
    print("  Attempting unauthorized transfer (Admin tries to move Bob's tokens)...")
    try:
        program.transfer(bob_acct.address, alice_acct.address, transfer_amount, signer="Admin")
    except PermissionError as e:
        print(f"  ✗ REJECTED: {e}")
    print()

    # --- Step 5: Bob burns 100 MAGIC ---
    print("-" * 70)
    print("  STEP 5: Bob Burns 100 MAGIC")
    print("-" * 70)
    print()

    burn_amount = 100 * (10 ** mint.decimals)
    program.burn(bob_acct.address, "MAGIC", burn_amount, signer="Bob")

    print(f"  Bob burns 100 MAGIC (destroyed permanently)")
    print()
    print(f"  Alice balance: {mint.display_amount(alice_acct.amount)} MAGIC")
    print(f"  Bob balance:   {mint.display_amount(bob_acct.amount)} MAGIC")
    print(f"  Total supply:  {mint.display_amount(mint.supply)} MAGIC  (reduced by 100)")
    print()

    # --- Final state ---
    print("-" * 70)
    print("  FINAL STATE")
    print("-" * 70)
    print()
    print("  Token: MAGIC (9 decimals)")
    print(f"  Total Supply: {mint.display_amount(mint.supply)} MAGIC")
    print()
    print("  ┌───────────┬─────────────────────┬──────────────┐")
    print("  │  Owner    │  Token Account      │  Balance     │")
    print("  ├───────────┼─────────────────────┼──────────────┤")
    for name, acct in [("Alice", alice_acct), ("Bob", bob_acct)]:
        bal = mint.display_amount(acct.amount)
        print(f"  │  {name:<8}│  {acct.address[:18]}… │  {bal:>8} MAGIC│")
    print("  └───────────┴─────────────────────┴──────────────┘")
    print()

    # --- Instruction log ---
    print("-" * 70)
    print("  INSTRUCTION LOG")
    print("-" * 70)
    print()
    for i, entry in enumerate(program.instruction_log, 1):
        status = entry.pop("status", "OK")
        instr = entry.pop("instruction")
        marker = "✓" if status == "OK" else "✗"
        print(f"  {i}. [{marker}] {instr}")
        for k, v in entry.items():
            if k != "error":
                print(f"       {k}: {v}")
        print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
