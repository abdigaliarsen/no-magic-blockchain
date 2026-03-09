"""
TITLE: Ethereum Account State Model
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    A complete Ethereum world-state model from scratch, including Externally Owned
    Accounts (EOAs) and contract accounts. Processes transfer transactions by
    updating nonces and balances, demonstrating how Ethereum's state machine works.

KEY CONCEPTS:
    - Account structure: nonce, balance, code_hash, storage_root
    - EOA vs contract accounts
    - World state as address → account mapping
    - State transitions via transaction processing

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (hash functions for code_hash / storage_root)

REAL-WORLD RELEVANCE:
    Ethereum's entire execution model revolves around state transitions. Every
    transaction transforms the world state from one snapshot to the next. Full
    nodes store and verify this state to validate the chain.
"""

import hashlib  # For computing code_hash and storage_root placeholders
import json     # For pretty-printing state snapshots
from dataclasses import dataclass, field
from typing import Optional

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# The hash of empty bytecode — every EOA has this as its code_hash because
# EOAs have no deployed code. This is keccak256("") in real Ethereum, but
# we use sha256("") here since keccak isn't in stdlib.
EMPTY_CODE_HASH = hashlib.sha256(b"").hexdigest()

# The root hash of an empty Merkle Patricia Trie — represents an account
# with no storage slots written. Contract accounts get a real root once
# they store data.
EMPTY_STORAGE_ROOT = hashlib.sha256(b"empty_storage").hexdigest()

# 1 Ether = 10^18 Wei in real Ethereum; we use the same scale
WEI_PER_ETHER = 10 ** 18

# Gas cost for a simple transfer (21,000 in real Ethereum)
TRANSFER_GAS = 21_000

# Gas price in Wei (simplified — real Ethereum uses EIP-1559 dynamic fees)
GAS_PRICE = 20 * (10 ** 9)  # 20 Gwei


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Account representation --------------------------------------------------

@dataclass
class Account:
    """Represents a single Ethereum account (EOA or contract).

    Fields mirror the real Ethereum account structure stored in the world state
    trie. Every account, whether owned by a human or a smart contract, has
    exactly these four fields.
    """
    nonce: int = 0               # Number of txs sent (EOA) or contracts created (contract)
    balance: int = 0             # Wei held by this account
    code_hash: str = ""          # SHA-256 of the account's bytecode (empty for EOAs)
    storage_root: str = ""       # Root of the account's storage trie (empty for EOAs)
    code: bytes = b""            # The actual bytecode (not stored in state, kept separately)

    def __post_init__(self):
        """Set default hashes if not provided."""
        if not self.code_hash:
            self.code_hash = EMPTY_CODE_HASH
        if not self.storage_root:
            self.storage_root = EMPTY_STORAGE_ROOT

    @property
    def is_contract(self) -> bool:
        """A contract account has non-empty code (code_hash differs from empty)."""
        return self.code_hash != EMPTY_CODE_HASH

    @property
    def account_type(self) -> str:
        """Human-readable label for the account type."""
        return "Contract" if self.is_contract else "EOA"

    def to_dict(self) -> dict:
        """Serialize to a dictionary for display (omits raw code bytes)."""
        return {
            "type": self.account_type,
            "nonce": self.nonce,
            "balance_wei": self.balance,
            "balance_eth": f"{self.balance / WEI_PER_ETHER:.4f}",
            "code_hash": self.code_hash[:16] + "...",      # Truncate for readability
            "storage_root": self.storage_root[:16] + "...",
        }


# --- Transaction representation ----------------------------------------------

@dataclass
class Transaction:
    """A simple value-transfer transaction (type 0 — no contract interaction).

    In real Ethereum, transactions also carry data (for contract calls),
    gas limit, max fee, etc. We keep only what's needed for transfers.
    """
    sender: str         # Address of the sender (hex string)
    recipient: str      # Address of the recipient (hex string)
    value: int          # Amount in Wei to transfer
    nonce: int          # Must match sender's current nonce (replay protection)
    gas_limit: int = TRANSFER_GAS   # Gas units the sender is willing to pay
    gas_price: int = GAS_PRICE      # Price per gas unit in Wei

    @property
    def total_cost(self) -> int:
        """Total Wei deducted from sender: value + gas fees."""
        return self.value + (self.gas_limit * self.gas_price)


# --- World State --------------------------------------------------------------

class WorldState:
    """The world state maps every known address to its account object.

    In real Ethereum, this is stored as a Merkle Patricia Trie so that
    any state snapshot can be summarized by a single root hash. Here we
    use a simple dictionary for clarity.
    """

    def __init__(self):
        self.accounts: dict[str, Account] = {}  # address → Account
        self.tx_log: list[str] = []              # Human-readable log of processed txs

    def get_account(self, address: str) -> Account:
        """Return the account for an address, creating it on first access.

        In real Ethereum, reading a non-existent account returns an "empty"
        account (nonce=0, balance=0). We do the same.
        """
        if address not in self.accounts:
            self.accounts[address] = Account()
        return self.accounts[address]

    def create_eoa(self, address: str, balance: int = 0) -> Account:
        """Create an Externally Owned Account (controlled by a private key)."""
        account = Account(balance=balance)
        self.accounts[address] = account
        return account

    def create_contract(self, address: str, code: bytes, balance: int = 0) -> Account:
        """Create a contract account with deployed bytecode."""
        code_hash = hashlib.sha256(code).hexdigest()     # Hash of the contract code
        storage_root = EMPTY_STORAGE_ROOT                 # No storage written yet
        account = Account(
            balance=balance,
            code_hash=code_hash,
            storage_root=storage_root,
            code=code,
        )
        self.accounts[address] = account
        return account

    def process_transaction(self, tx: Transaction) -> tuple[bool, str]:
        """Apply a transfer transaction to the world state.

        This is the core state-transition function. It mirrors what the EVM
        does for simple transfers (no contract execution).

        Returns (success: bool, message: str).
        """
        sender = self.get_account(tx.sender)
        recipient = self.get_account(tx.recipient)

        # --- Validation checks (order matches go-ethereum) --------------------

        # 1. Nonce must match — prevents replay attacks
        if tx.nonce != sender.nonce:
            msg = (f"REJECTED: nonce mismatch for {tx.sender[:10]}... "
                   f"(expected {sender.nonce}, got {tx.nonce})")
            self.tx_log.append(msg)
            return False, msg

        # 2. Sender must have enough balance for value + gas
        if sender.balance < tx.total_cost:
            msg = (f"REJECTED: insufficient balance for {tx.sender[:10]}... "
                   f"(has {sender.balance}, needs {tx.total_cost})")
            self.tx_log.append(msg)
            return False, msg

        # --- Apply state changes -----------------------------------------------

        gas_fee = tx.gas_limit * tx.gas_price  # Fee paid regardless of outcome

        # Deduct value + gas from sender
        sender.balance -= tx.total_cost
        # Increment sender's nonce (this tx is now "used")
        sender.nonce += 1
        # Credit value to recipient (gas fee goes to miner, not modeled here)
        recipient.balance += tx.value

        msg = (f"OK: {tx.sender[:10]}... → {tx.recipient[:10]}... "
               f"| {tx.value / WEI_PER_ETHER:.4f} ETH "
               f"| gas fee: {gas_fee / WEI_PER_ETHER:.6f} ETH")
        self.tx_log.append(msg)
        return True, msg

    def state_root(self) -> str:
        """Compute a summary hash of the entire world state.

        Real Ethereum uses the Merkle Patricia Trie root. We concatenate
        all account data in sorted-address order and hash it.
        """
        parts = []
        for addr in sorted(self.accounts.keys()):
            acct = self.accounts[addr]
            # Deterministic serialization: address + nonce + balance + hashes
            parts.append(f"{addr}:{acct.nonce}:{acct.balance}:{acct.code_hash}:{acct.storage_root}")
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()

    def print_state(self, title: str = "World State"):
        """Print a formatted snapshot of all accounts."""
        print(f"\n{'=' * 64}")
        print(f"  {title}")
        print(f"  State Root: {self.state_root()[:32]}...")
        print(f"{'=' * 64}")
        for addr in sorted(self.accounts.keys()):
            acct = self.accounts[addr]
            info = acct.to_dict()
            print(f"\n  Address: {addr}")
            print(f"  ┌{'─' * 44}┐")
            print(f"  │ {'Type':<14} {info['type']:<28} │")
            print(f"  │ {'Nonce':<14} {info['nonce']:<28} │")
            print(f"  │ {'Balance':<14} {info['balance_eth'] + ' ETH':<28} │")
            print(f"  │ {'Balance (Wei)':<14} {info['balance_wei']:<28} │")
            print(f"  │ {'Code Hash':<14} {info['code_hash']:<28} │")
            print(f"  │ {'Storage Root':<14} {info['storage_root']:<28} │")
            print(f"  └{'─' * 44}┘")
        print()


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Ethereum's account state model."""

    print("=" * 64)
    print("  ETHEREUM ACCOUNT STATE MODEL")
    print("  Demonstrating world state transitions via transfers")
    print("=" * 64)

    # --- Setup: create accounts -----------------------------------------------

    world = WorldState()

    # Alice: an EOA with 10 ETH (like a user with a MetaMask wallet)
    world.create_eoa("0xAlice_1234567890abcdef", balance=10 * WEI_PER_ETHER)
    # Bob: an EOA with 5 ETH
    world.create_eoa("0xBob___1234567890abcdef", balance=5 * WEI_PER_ETHER)
    # Charlie: a new EOA with 0 ETH (has never received funds)
    world.create_eoa("0xCharl_1234567890abcdef", balance=0)
    # A simple contract account (e.g., a deployed token contract)
    world.create_contract(
        "0xContr_1234567890abcdef",
        code=b"\x60\x01\x60\x02\x01",  # Dummy bytecode: PUSH1 1 PUSH1 2 ADD
        balance=2 * WEI_PER_ETHER,
    )

    world.print_state("Initial World State")

    # --- Transaction 1: Alice sends 2 ETH to Bob -----------------------------

    print("\n" + "─" * 64)
    print("  Transaction #1: Alice → Bob (2 ETH)")
    print("─" * 64)

    tx1 = Transaction(
        sender="0xAlice_1234567890abcdef",
        recipient="0xBob___1234567890abcdef",
        value=2 * WEI_PER_ETHER,
        nonce=0,  # Alice's first tx
    )
    success, msg = world.process_transaction(tx1)
    print(f"  Result: {msg}")
    world.print_state("After Transaction #1")

    # --- Transaction 2: Bob sends 1 ETH to Charlie ---------------------------

    print("\n" + "─" * 64)
    print("  Transaction #2: Bob → Charlie (1 ETH)")
    print("─" * 64)

    tx2 = Transaction(
        sender="0xBob___1234567890abcdef",
        recipient="0xCharl_1234567890abcdef",
        value=1 * WEI_PER_ETHER,
        nonce=0,  # Bob's first tx
    )
    success, msg = world.process_transaction(tx2)
    print(f"  Result: {msg}")
    world.print_state("After Transaction #2")

    # --- Transaction 3: Alice sends 3 ETH to the contract --------------------

    print("\n" + "─" * 64)
    print("  Transaction #3: Alice → Contract (3 ETH)")
    print("─" * 64)

    tx3 = Transaction(
        sender="0xAlice_1234567890abcdef",
        recipient="0xContr_1234567890abcdef",
        value=3 * WEI_PER_ETHER,
        nonce=1,  # Alice's second tx (nonce incremented after tx1)
    )
    success, msg = world.process_transaction(tx3)
    print(f"  Result: {msg}")
    world.print_state("After Transaction #3")

    # --- Show failure cases ---------------------------------------------------

    print("\n" + "─" * 64)
    print("  Transaction #4: Alice → Bob (100 ETH) — SHOULD FAIL (insufficient)")
    print("─" * 64)

    tx4 = Transaction(
        sender="0xAlice_1234567890abcdef",
        recipient="0xBob___1234567890abcdef",
        value=100 * WEI_PER_ETHER,
        nonce=2,
    )
    success, msg = world.process_transaction(tx4)
    print(f"  Result: {msg}")

    print("\n" + "─" * 64)
    print("  Transaction #5: Alice → Bob (0.5 ETH) — SHOULD FAIL (wrong nonce)")
    print("─" * 64)

    tx5 = Transaction(
        sender="0xAlice_1234567890abcdef",
        recipient="0xBob___1234567890abcdef",
        value=int(0.5 * WEI_PER_ETHER),
        nonce=999,  # Wrong nonce — replay protection kicks in
    )
    success, msg = world.process_transaction(tx5)
    print(f"  Result: {msg}")

    # --- Summary of all state roots -------------------------------------------

    print("\n" + "=" * 64)
    print("  TRANSACTION LOG")
    print("=" * 64)
    for i, entry in enumerate(world.tx_log):
        print(f"  [{i + 1}] {entry}")

    print("\n" + "=" * 64)
    print("  KEY TAKEAWAYS")
    print("=" * 64)
    print("  1. Each account has nonce, balance, code_hash, storage_root")
    print("  2. EOAs have empty code_hash; contracts have real code")
    print("  3. Nonces prevent replay attacks (each tx must use the next nonce)")
    print("  4. Balance checks prevent overdrafts")
    print("  5. Gas fees are deducted even for simple transfers")
    print("  6. The state root changes after every valid transaction")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
