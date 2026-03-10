"""
TITLE: ERC-20 Token Standard
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    A complete ERC-20 fungible token implementation from scratch. Covers the
    full interface: totalSupply, balanceOf, transfer, approve, transferFrom,
    and allowance. Includes an event log system that mirrors Ethereum's event
    emission for Transfer and Approval events.

KEY CONCEPTS:
    - Fungible tokens: interchangeable units with a fixed total supply
    - Allowance mechanism: owner approves spender to transfer on their behalf
    - Event emission: Transfer and Approval events for off-chain indexing
    - Decimal scaling: human-readable amounts vs raw integer balances

PREREQUISITE SCRIPTS:
    - ethereum/fundamentals/01_accounts_state.py (account model)
    - ethereum/fundamentals/06_smart_contracts.py (contract storage)
    - ethereum/fundamentals/08_abi_encoding.py (function selectors)

REAL-WORLD RELEVANCE:
    ERC-20 is the most widely used token standard on Ethereum. USDT, USDC,
    LINK, UNI, and thousands of other tokens follow this interface. DEXes,
    lending protocols, and bridges all depend on the approve/transferFrom
    pattern for token interactions.
"""

import hashlib  # SHA-256 for address hashing (stand-in for keccak256)
import time     # For event timestamps

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Standard ERC-20 uses 18 decimals (like ETH's wei → ether conversion)
DEFAULT_DECIMALS = 18

# Scale factor: 1 token = 10^18 smallest units
SCALE = 10 ** DEFAULT_DECIMALS

# Zero address — used for mint (from) and burn (to) events
ZERO_ADDRESS = "0x" + "0" * 40

# How many hex chars to show for addresses in output
ADDR_DISPLAY = 10


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Event system -----------------------------------------------------------

class Event:
    """Represents an emitted event, similar to Ethereum log entries.

    Events are not stored on-chain in contract storage — they live in
    transaction receipts and are indexed by topics for off-chain querying.
    """

    def __init__(self, name: str, args: dict):
        self.name = name
        self.args = args
        self.timestamp = time.monotonic()  # Simulated block timestamp

    def __repr__(self):
        args_str = ", ".join(f"{k}={v}" for k, v in self.args.items())
        return f"{self.name}({args_str})"


class EventLog:
    """Collects emitted events, like an Ethereum node's event log."""

    def __init__(self):
        self.events: list[Event] = []

    def emit(self, name: str, args: dict):
        """Emit a new event (appended to the log)."""
        event = Event(name, args)
        self.events.append(event)
        return event

    def filter_by_name(self, name: str) -> list[Event]:
        """Filter events by name (like filtering by event topic)."""
        return [e for e in self.events if e.name == name]


# --- Address generation -----------------------------------------------------

def make_address(name: str) -> str:
    """Generate a deterministic Ethereum-style address from a name.

    Real addresses come from public keys. We use a hash for simplicity,
    keeping the 0x + 40 hex char format.
    """
    h = hashlib.sha256(name.encode()).hexdigest()
    return "0x" + h[:40]  # 20 bytes = 40 hex chars


def short_addr(address: str) -> str:
    """Shorten an address for display: 0x1234...abcd."""
    return address[:6] + "..." + address[-4:]


# --- ERC-20 Token Contract --------------------------------------------------

class ERC20Token:
    """A complete ERC-20 token implementation.

    Storage layout (mirrors Solidity):
    - _balances: mapping(address => uint256)
    - _allowances: mapping(address => mapping(address => uint256))
    - _total_supply: uint256
    """

    def __init__(self, name: str, symbol: str, decimals: int = DEFAULT_DECIMALS):
        # --- Token metadata (immutable after deployment) ---
        self._name = name
        self._symbol = symbol
        self._decimals = decimals

        # --- Storage (mutable state) ---
        self._balances: dict[str, int] = {}     # address → raw balance
        self._allowances: dict[str, dict[str, int]] = {}  # owner → (spender → amount)
        self._total_supply: int = 0

        # --- Event log ---
        self.events = EventLog()

        # --- Deployer address (for access control) ---
        self._owner: str | None = None

    # --- ERC-20 View Functions (read-only, no state changes) ----------------

    def name(self) -> str:
        """Returns the token name (e.g., 'USD Coin')."""
        return self._name

    def symbol(self) -> str:
        """Returns the token symbol (e.g., 'USDC')."""
        return self._symbol

    def decimals(self) -> int:
        """Returns the number of decimal places.

        A decimals value of 18 means that 1 token = 10^18 smallest units.
        UIs divide the raw balance by 10^decimals for human display.
        """
        return self._decimals

    def total_supply(self) -> int:
        """Returns the total number of tokens in existence (raw units)."""
        return self._total_supply

    def balance_of(self, account: str) -> int:
        """Returns the token balance of an account (raw units).

        Returns 0 for any address that has never held tokens — this matches
        Solidity's default mapping behavior (unset keys return zero).
        """
        return self._balances.get(account, 0)

    def allowance(self, owner: str, spender: str) -> int:
        """Returns how many tokens `spender` can still transfer from `owner`.

        The allowance mechanism enables two-step transfers:
        1. Owner calls approve(spender, amount)
        2. Spender calls transferFrom(owner, recipient, amount)
        This is how DEXes and lending protocols move your tokens.
        """
        return self._allowances.get(owner, {}).get(spender, 0)

    # --- ERC-20 State-Changing Functions ------------------------------------

    def transfer(self, sender: str, recipient: str, amount: int) -> bool:
        """Transfer tokens from sender to recipient.

        Requirements:
        - sender must have sufficient balance
        - recipient cannot be the zero address
        - amount must be non-negative

        Emits: Transfer(from, to, value)
        """
        self._require(recipient != ZERO_ADDRESS, "transfer to zero address")
        self._require(amount >= 0, "transfer amount must be non-negative")
        self._require(self.balance_of(sender) >= amount, "insufficient balance")

        # Debit sender, credit recipient
        self._balances[sender] = self.balance_of(sender) - amount
        self._balances[recipient] = self.balance_of(recipient) + amount

        # Emit Transfer event
        self.events.emit("Transfer", {
            "from": short_addr(sender),
            "to": short_addr(recipient),
            "value": amount,
        })
        return True

    def approve(self, owner: str, spender: str, amount: int) -> bool:
        """Set the allowance that `spender` can transfer from `owner`.

        IMPORTANT: This REPLACES the current allowance (not incremental).
        The approve-then-transferFrom pattern has a known race condition:
        if the owner changes the allowance from N to M, the spender could
        potentially spend N+M. The mitigation is to set allowance to 0 first.

        Emits: Approval(owner, spender, value)
        """
        self._require(spender != ZERO_ADDRESS, "approve to zero address")
        self._require(amount >= 0, "approval amount must be non-negative")

        # Set the allowance (overwrites any existing value)
        if owner not in self._allowances:
            self._allowances[owner] = {}
        self._allowances[owner][spender] = amount

        # Emit Approval event
        self.events.emit("Approval", {
            "owner": short_addr(owner),
            "spender": short_addr(spender),
            "value": amount,
        })
        return True

    def transfer_from(self, spender: str, owner: str, recipient: str, amount: int) -> bool:
        """Transfer tokens from `owner` to `recipient`, called by `spender`.

        The spender must have sufficient allowance from the owner.
        After the transfer, the allowance is decreased by the transferred amount.

        This is the core mechanism that enables DeFi:
        - User approves a DEX contract to spend their tokens
        - DEX calls transferFrom to execute the swap

        Emits: Transfer(from, to, value) and Approval(owner, spender, new_allowance)
        """
        current_allowance = self.allowance(owner, spender)
        self._require(current_allowance >= amount, "transfer amount exceeds allowance")

        # Execute the transfer (this checks balance too)
        self.transfer(owner, recipient, amount)

        # Decrease the allowance by the amount transferred
        self.approve(owner, spender, current_allowance - amount)

        return True

    # --- Minting and burning (not part of ERC-20 spec, but standard extensions) ---

    def mint(self, to: str, amount: int):
        """Create new tokens and assign them to `to`.

        Minting increases total supply. In real contracts, this is usually
        restricted to the contract owner or a minter role.

        Emits: Transfer(ZERO_ADDRESS, to, value)
        """
        self._require(to != ZERO_ADDRESS, "mint to zero address")
        self._require(amount > 0, "mint amount must be positive")

        self._total_supply += amount
        self._balances[to] = self.balance_of(to) + amount

        # Mint events use zero address as the sender (tokens come from nowhere)
        self.events.emit("Transfer", {
            "from": "0x0000...0000",
            "to": short_addr(to),
            "value": amount,
        })

    def burn(self, owner: str, amount: int):
        """Destroy tokens from `owner`, reducing total supply.

        Emits: Transfer(owner, ZERO_ADDRESS, value)
        """
        self._require(self.balance_of(owner) >= amount, "burn exceeds balance")
        self._require(amount > 0, "burn amount must be positive")

        self._balances[owner] = self.balance_of(owner) - amount
        self._total_supply -= amount

        # Burn events use zero address as the recipient (tokens go nowhere)
        self.events.emit("Transfer", {
            "from": short_addr(owner),
            "to": "0x0000...0000",
            "value": amount,
        })

    # --- Internal helpers ---------------------------------------------------

    @staticmethod
    def _require(condition: bool, message: str):
        """Revert if condition is False (like Solidity's require()).

        In real EVM execution, a failed require reverts all state changes
        and refunds remaining gas. We simulate this with an exception.
        """
        if not condition:
            raise ValueError(f"ERC20: {message}")

    def format_amount(self, raw: int) -> str:
        """Convert raw token units to human-readable format."""
        scale = 10 ** self._decimals
        whole = raw // scale
        frac = raw % scale
        if frac == 0:
            return f"{whole:,}"
        # Show up to 4 decimal places
        frac_str = str(frac).zfill(self._decimals)[:4].rstrip('0')
        return f"{whole:,}.{frac_str}"


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of an ERC-20 token."""

    print("=" * 70)
    print("ERC-20 TOKEN STANDARD — Fungible Token Implementation")
    print("=" * 70)
    print()

    # --- Deploy the token ---------------------------------------------------
    print("--- Step 1: Deploy Token Contract ---")
    print()

    token = ERC20Token("NoMagic Coin", "NMC", decimals=18)
    deployer = make_address("deployer")
    token._owner = deployer

    print(f"  Token Name:    {token.name()}")
    print(f"  Symbol:        {token.symbol()}")
    print(f"  Decimals:      {token.decimals()}")
    print(f"  Total Supply:  {token.total_supply()}")
    print(f"  Deployer:      {short_addr(deployer)}")
    print()

    # --- Mint initial supply ------------------------------------------------
    print("--- Step 2: Mint Initial Supply ---")
    print()

    alice = make_address("alice")
    bob = make_address("bob")
    charlie = make_address("charlie")
    dex_contract = make_address("uniswap_v3_router")

    # Mint 1,000,000 tokens to deployer (in raw units: 1M * 10^18)
    mint_amount = 1_000_000 * SCALE
    token.mint(deployer, mint_amount)

    print(f"  Minted {token.format_amount(mint_amount)} {token.symbol()} to deployer")
    print(f"  Total Supply: {token.format_amount(token.total_supply())} {token.symbol()}")
    print()

    # --- Transfer tokens ----------------------------------------------------
    print("--- Step 3: Direct Transfers ---")
    print()

    transfers = [
        (deployer, alice, 50_000 * SCALE, "deployer → Alice"),
        (deployer, bob, 30_000 * SCALE, "deployer → Bob"),
        (alice, charlie, 5_000 * SCALE, "Alice → Charlie"),
    ]

    print("  ┌──────────────────────────────────────────────────────────┐")
    print(f"  │ {'Transfer':<20} {'Amount':>15} {'Status':>10}      │")
    print("  ├──────────────────────────────────────────────────────────┤")

    for sender, recipient, amount, label in transfers:
        try:
            token.transfer(sender, recipient, amount)
            formatted = token.format_amount(amount)
            print(f"  │ {label:<20} {formatted:>15} {'OK':>10}      │")
        except ValueError as e:
            print(f"  │ {label:<20} {'':>15} {'REVERT':>10}      │")

    print("  └──────────────────────────────────────────────────────────┘")
    print()

    # Show balances
    print("  Balances after transfers:")
    accounts = [
        ("deployer", deployer),
        ("Alice", alice),
        ("Bob", bob),
        ("Charlie", charlie),
    ]
    print("  ┌──────────────────────────────────────────────────┐")
    for name, addr in accounts:
        bal = token.balance_of(addr)
        formatted = token.format_amount(bal)
        print(f"  │  {name:<12} {short_addr(addr):<16} {formatted:>12} NMC │")
    print("  └──────────────────────────────────────────────────┘")
    print()

    # --- Approve + TransferFrom pattern ------------------------------------
    print("--- Step 4: Approve + TransferFrom (DEX pattern) ---")
    print()

    approve_amount = 10_000 * SCALE

    print(f"  Scenario: Alice approves a DEX to spend {token.format_amount(approve_amount)} NMC")
    print(f"  Then the DEX transfers tokens from Alice to Bob (simulating a swap)")
    print()

    # Step 1: Alice approves the DEX
    token.approve(alice, dex_contract, approve_amount)
    print(f"  1. Alice approves DEX: allowance = {token.format_amount(token.allowance(alice, dex_contract))} NMC")

    # Step 2: DEX calls transferFrom (Alice → Bob, 3000 tokens)
    swap_amount = 3_000 * SCALE
    token.transfer_from(dex_contract, alice, bob, swap_amount)
    print(f"  2. DEX transfers {token.format_amount(swap_amount)} NMC from Alice to Bob")
    print(f"     Remaining allowance: {token.format_amount(token.allowance(alice, dex_contract))} NMC")

    # Step 3: DEX transfers more
    swap_amount_2 = 2_000 * SCALE
    token.transfer_from(dex_contract, alice, bob, swap_amount_2)
    print(f"  3. DEX transfers {token.format_amount(swap_amount_2)} NMC from Alice to Bob")
    print(f"     Remaining allowance: {token.format_amount(token.allowance(alice, dex_contract))} NMC")
    print()

    # Show updated balances
    print("  Balances after approve/transferFrom:")
    print("  ┌──────────────────────────────────────────────────┐")
    for name, addr in accounts:
        bal = token.balance_of(addr)
        formatted = token.format_amount(bal)
        print(f"  │  {name:<12} {short_addr(addr):<16} {formatted:>12} NMC │")
    print("  └──────────────────────────────────────────────────┘")
    print()

    # --- Failure cases (reverts) -------------------------------------------
    print("--- Step 5: Revert Cases ---")
    print()

    test_cases = [
        ("Overdraft transfer",
         lambda: token.transfer(charlie, alice, 999_999 * SCALE)),
        ("Transfer to zero addr",
         lambda: token.transfer(alice, ZERO_ADDRESS, 100)),
        ("TransferFrom over allowance",
         lambda: token.transfer_from(dex_contract, alice, bob, 999_999 * SCALE)),
    ]

    for label, fn in test_cases:
        try:
            fn()
            print(f"  {label}: OK (unexpected)")
        except ValueError as e:
            print(f"  {label}:")
            print(f"    REVERT: {e}")
    print()

    # --- Burn tokens -------------------------------------------------------
    print("--- Step 6: Burn Tokens ---")
    print()

    burn_amount = 10_000 * SCALE
    print(f"  Before burn: Bob has {token.format_amount(token.balance_of(bob))} NMC")
    print(f"  Total supply: {token.format_amount(token.total_supply())} NMC")

    token.burn(bob, burn_amount)

    print(f"  Burned {token.format_amount(burn_amount)} NMC from Bob")
    print(f"  After burn:  Bob has {token.format_amount(token.balance_of(bob))} NMC")
    print(f"  Total supply: {token.format_amount(token.total_supply())} NMC")
    print()

    # --- Event log ----------------------------------------------------------
    print("--- Step 7: Event Log ---")
    print()
    print("  All emitted events (like querying eth_getLogs):")
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print(f"  │ {'#':<3} {'Event':<10} {'Details':<47}│")
    print("  ├─────────────────────────────────────────────────────────────┤")

    for i, event in enumerate(token.events.events):
        args_str = ", ".join(f"{k}={v}" for k, v in event.args.items()
                            if k != "value")
        value = event.args.get("value", "")
        if isinstance(value, int):
            value = token.format_amount(value)
        detail = f"{args_str} | {value}"
        if len(detail) > 47:
            detail = detail[:44] + "..."
        print(f"  │ {i:<3} {event.name:<10} {detail:<47}│")

    print("  └─────────────────────────────────────────────────────────────┘")
    print()

    transfer_count = len(token.events.filter_by_name("Transfer"))
    approval_count = len(token.events.filter_by_name("Approval"))
    print(f"  Transfer events: {transfer_count}")
    print(f"  Approval events: {approval_count}")
    print()

    # --- Summary ------------------------------------------------------------
    print("--- ERC-20 Interface Summary ---")
    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ View Functions (no gas, read-only):                     │")
    print("  │   name()                → string                       │")
    print("  │   symbol()              → string                       │")
    print("  │   decimals()            → uint8                        │")
    print("  │   totalSupply()         → uint256                      │")
    print("  │   balanceOf(account)    → uint256                      │")
    print("  │   allowance(owner, sp)  → uint256                      │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │ State-Changing Functions (require gas):                 │")
    print("  │   transfer(to, amount)                → bool           │")
    print("  │   approve(spender, amount)            → bool           │")
    print("  │   transferFrom(from, to, amount)      → bool           │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │ Events:                                                 │")
    print("  │   Transfer(from, to, value)                            │")
    print("  │   Approval(owner, spender, value)                      │")
    print("  └─────────────────────────────────────────────────────────┘")


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
