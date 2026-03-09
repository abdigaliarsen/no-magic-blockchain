"""
TITLE: Solana Rent Model
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    Solana's rent system that charges accounts for storing data on-chain.
    Accounts must maintain a minimum balance (2 years of rent) to become
    rent-exempt, otherwise rent is deducted each epoch until the account
    is purged.

KEY CONCEPTS:
    - Rent rate: lamports charged per byte per epoch
    - Rent exemption: accounts with balance >= 2 years of rent are exempt
    - Rent collection: non-exempt accounts lose rent each epoch
    - Account purging: accounts drained to zero are removed

PREREQUISITE SCRIPTS:
    - solana/01_accounts_model.py

REAL-WORLD RELEVANCE:
    Solana charges rent to prevent state bloat. In practice, almost all
    accounts are rent-exempt (hold >= minimum balance). Since Solana v1.17,
    new accounts are required to be rent-exempt at creation.
"""

import math

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

LAMPORTS_PER_SOL = 1_000_000_000          # 1 SOL = 1 billion lamports
LAMPORTS_PER_BYTE_PER_EPOCH = 3_480       # Approximate rent rate on Solana mainnet
ACCOUNT_HEADER_SIZE = 128                  # Every account has 128 bytes of fixed overhead
EXEMPTION_YEARS = 2                        # Must hold enough for 2 years of rent to be exempt
EPOCHS_PER_YEAR = 182                      # Roughly 2 days per epoch → ~182 epochs/year
SLOTS_PER_EPOCH = 432_000                  # Number of slots in one Solana epoch (~2 days)

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --------------------------------------------------------------------------
# Account
# --------------------------------------------------------------------------

class Account:
    """Represents a Solana account that may owe rent."""

    def __init__(self, address: str, data_size: int, balance: int):
        self.address = address                            # Human-readable label
        self.data_size = data_size                        # Bytes of data stored on-chain
        self.balance = balance                            # Current lamport balance
        self.total_size = data_size + ACCOUNT_HEADER_SIZE # Total space = data + fixed header
        self.alive = True                                 # Account is still on-chain
        self.rent_collected = 0                           # Running total of rent paid
        self.epochs_survived = 0                          # How many epochs the account lasted

    def __repr__(self) -> str:
        status = "alive" if self.alive else "PURGED"
        return f"Account({self.address}, {self.data_size}B, {self.balance} lamports, {status})"


# --------------------------------------------------------------------------
# Rent Calculator
# --------------------------------------------------------------------------

def calculate_rent_per_epoch(total_size: int) -> int:
    """Calculate how many lamports an account owes per epoch.

    Rent = total_size_in_bytes * lamports_per_byte_per_epoch.
    """
    return total_size * LAMPORTS_PER_BYTE_PER_EPOCH


def calculate_minimum_balance(data_size: int) -> int:
    """Calculate the minimum lamport balance for rent exemption.

    The account must hold enough to pay 2 years of rent.
    total_size includes the 128-byte header that every account has.
    """
    total_size = data_size + ACCOUNT_HEADER_SIZE
    rent_per_epoch = calculate_rent_per_epoch(total_size)
    epochs_in_exemption_period = EXEMPTION_YEARS * EPOCHS_PER_YEAR  # 2 * 182 = 364 epochs
    return rent_per_epoch * epochs_in_exemption_period


def is_rent_exempt(account: Account) -> bool:
    """Check whether an account's balance meets the rent-exemption threshold."""
    min_balance = calculate_minimum_balance(account.data_size)
    return account.balance >= min_balance


# --------------------------------------------------------------------------
# Rent Collector
# --------------------------------------------------------------------------

class RentCollector:
    """Simulates epoch-based rent collection across all accounts."""

    def __init__(self):
        self.current_epoch = 0        # Tracks the current epoch number
        self.total_collected = 0       # Total lamports collected as rent
        self.purged_accounts: list[str] = []  # Addresses of accounts removed

    def collect_rent(self, accounts: list[Account]) -> list[dict]:
        """Collect rent from all non-exempt, living accounts for one epoch.

        Returns a log of actions taken for display purposes.
        """
        self.current_epoch += 1
        actions = []

        for acct in accounts:
            if not acct.alive:
                continue  # Skip accounts that were already purged

            if is_rent_exempt(acct):
                # Rent-exempt accounts are never charged
                acct.epochs_survived += 1
                actions.append({
                    "account": acct.address,
                    "action": "exempt",
                    "rent_due": 0,
                    "balance_after": acct.balance,
                })
                continue

            # Calculate rent owed this epoch
            rent_due = calculate_rent_per_epoch(acct.total_size)

            if acct.balance >= rent_due:
                # Deduct rent from balance
                acct.balance -= rent_due
                acct.rent_collected += rent_due
                acct.epochs_survived += 1
                self.total_collected += rent_due
                actions.append({
                    "account": acct.address,
                    "action": "collected",
                    "rent_due": rent_due,
                    "balance_after": acct.balance,
                })
            else:
                # Insufficient balance → purge the account
                remainder = acct.balance
                acct.balance = 0
                acct.alive = False
                self.total_collected += remainder
                self.purged_accounts.append(acct.address)
                actions.append({
                    "account": acct.address,
                    "action": "purged",
                    "rent_due": rent_due,
                    "balance_after": 0,
                })

        return actions


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def format_lamports(lamports: int) -> str:
    """Format lamports with SOL equivalent for readability."""
    sol = lamports / LAMPORTS_PER_SOL
    if sol >= 0.01:
        return f"{lamports:>15,} lamports ({sol:.4f} SOL)"
    return f"{lamports:>15,} lamports"


def demo():
    """Run a visual demonstration of Solana's rent model."""

    # --- Part 1: Show rent-exempt minimums for various account sizes ---
    print("=" * 70)
    print("  SOLANA RENT MODEL")
    print("=" * 70)
    print()
    print("Rent rate:", LAMPORTS_PER_BYTE_PER_EPOCH, "lamports/byte/epoch")
    print("Exemption requirement: hold enough for", EXEMPTION_YEARS, "years of rent")
    print("Epochs per year:", EPOCHS_PER_YEAR)
    print()

    print("-" * 70)
    print("  PART 1: Rent-Exempt Minimum Balances")
    print("-" * 70)
    print()
    print(f"  {'Data Size':>12}  {'Total Size':>12}  {'Rent/Epoch':>16}  {'Min Balance (Exempt)':>24}")
    print(f"  {'─' * 12}  {'─' * 12}  {'─' * 16}  {'─' * 24}")

    test_sizes = [0, 100, 1_000, 10_000]  # The four sizes requested in the spec

    for data_size in test_sizes:
        total = data_size + ACCOUNT_HEADER_SIZE
        rent_epoch = calculate_rent_per_epoch(total)
        min_bal = calculate_minimum_balance(data_size)
        sol_equiv = min_bal / LAMPORTS_PER_SOL
        print(f"  {data_size:>10} B  {total:>10} B  {rent_epoch:>14,} lam  {min_bal:>16,} lam ({sol_equiv:.4f} SOL)")

    print()
    print("  Insight: Even a 0-byte account needs the 128-byte header,")
    print("  so no account is truly free to store on-chain.")
    print()

    # --- Part 2: Create accounts and check exemption status ---
    print("-" * 70)
    print("  PART 2: Account Exemption Status")
    print("-" * 70)
    print()

    accounts = [
        # Exempt: balance exactly at minimum
        Account("Alice-0B", 0, calculate_minimum_balance(0)),
        # Exempt: generous balance
        Account("Bob-100B", 100, calculate_minimum_balance(100) + 500_000),
        # NOT exempt: half the required balance → will pay rent
        Account("Carol-1000B", 1_000, calculate_minimum_balance(1_000) // 2),
        # NOT exempt: tiny balance → will be purged quickly
        Account("Dave-10000B", 10_000, 5_000_000),
    ]

    for acct in accounts:
        exempt = is_rent_exempt(acct)
        min_bal = calculate_minimum_balance(acct.data_size)
        status = "✓ EXEMPT" if exempt else "✗ NOT EXEMPT"
        print(f"  ┌─────────────────────────────────────────────────────────┐")
        print(f"  │ {acct.address:<20}  data: {acct.data_size:>6} bytes               │")
        print(f"  │ balance:  {acct.balance:>14,} lamports                    │")
        print(f"  │ minimum:  {min_bal:>14,} lamports                    │")
        print(f"  │ status:   {status:<30}              │")
        print(f"  └─────────────────────────────────────────────────────────┘")
    print()

    # --- Part 3: Simulate rent collection over multiple epochs ---
    print("-" * 70)
    print("  PART 3: Rent Collection Simulation (20 epochs)")
    print("-" * 70)
    print()

    collector = RentCollector()
    num_epochs = 20
    # Track balance history for non-exempt accounts
    non_exempt = [a for a in accounts if not is_rent_exempt(a)]

    print(f"  Tracking non-exempt accounts: {', '.join(a.address for a in non_exempt)}")
    print()
    print(f"  {'Epoch':>5}  ", end="")
    for a in non_exempt:
        print(f"{'[' + a.address + ']':>22}  ", end="")
    print()
    print(f"  {'─' * 5}  ", end="")
    for _ in non_exempt:
        print(f"{'─' * 22}  ", end="")
    print()

    for epoch in range(1, num_epochs + 1):
        actions = collector.collect_rent(accounts)

        # Build a lookup of this epoch's results
        action_map = {a["account"]: a for a in actions}

        print(f"  {epoch:>5}  ", end="")
        for a in non_exempt:
            info = action_map.get(a.address)
            if info is None or info["action"] == "exempt":
                print(f"{'— exempt —':>22}  ", end="")
            elif info["action"] == "collected":
                print(f"{info['balance_after']:>14,} lam -R  ", end="")
            elif info["action"] == "purged":
                print(f"{'☠ PURGED':>22}  ", end="")
            else:
                print(f"{'—':>22}  ", end="")
        print()

    print()
    print(f"  Total rent collected: {collector.total_collected:,} lamports")
    print(f"  Accounts purged:     {len(collector.purged_accounts)}")
    if collector.purged_accounts:
        print(f"  Purged addresses:    {', '.join(collector.purged_accounts)}")
    print()

    # --- Part 4: Summary ---
    print("-" * 70)
    print("  PART 4: Final Account States")
    print("-" * 70)
    print()

    for acct in accounts:
        alive = "alive" if acct.alive else "PURGED"
        print(f"  {acct.address:<16}  balance: {acct.balance:>14,} lam  "
              f"rent_paid: {acct.rent_collected:>12,} lam  "
              f"epochs: {acct.epochs_survived:>3}  [{alive}]")

    print()
    print("  Key takeaway: rent-exempt accounts live forever at no ongoing cost.")
    print("  Non-exempt accounts slowly drain and eventually get purged.")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
