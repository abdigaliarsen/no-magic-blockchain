"""
TITLE: UTXO Model
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    A complete Unspent Transaction Output (UTXO) model from scratch. Transactions
    consume existing UTXOs as inputs and produce new UTXOs as outputs. The UTXO set
    tracks all spendable outputs and prevents double-spending.

KEY CONCEPTS:
    - Unspent transaction outputs (UTXOs) as the fundamental unit of value
    - Transaction inputs reference previous outputs by (txid, output_index)
    - Change addresses — leftover value returned to the sender

PREREQUISITE SCRIPTS:
    - core/01_hashing.py
    - core/05_blockchain.py

REAL-WORLD RELEVANCE:
    Bitcoin and many other cryptocurrencies use the UTXO model for tracking
    ownership. Every bitcoin you "own" is really a set of unspent outputs
    locked to your address, waiting to be consumed by a future transaction.
"""

import hashlib
import json
from dataclasses import dataclass, field

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Coinbase reward — new coins minted per block (in satoshi-like units)
COINBASE_REWARD = 50

# Special "null" reference for coinbase inputs (no previous tx to reference)
COINBASE_TXID = "0" * 64
COINBASE_VOUT = 0xFFFFFFFF  # Max uint32 signals "this is a coinbase input"

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2.1: Transaction Output — a "coin" locked to a recipient
# ----------------------------------------------------------------------------

@dataclass
class TxOutput:
    """A single transaction output: an amount locked to a recipient address."""
    amount: int          # Value in smallest units (like satoshis)
    recipient: str       # Address that can spend this output

    def to_dict(self) -> dict:
        """Serialize for hashing."""
        return {"amount": self.amount, "recipient": self.recipient}


# ----------------------------------------------------------------------------
# 2.2: Transaction Input — a reference to a previous output being spent
# ----------------------------------------------------------------------------

@dataclass
class TxInput:
    """A reference to a specific output from a previous transaction."""
    txid: str            # Hash of the transaction containing the output we're spending
    vout: int            # Index of the output within that transaction (0, 1, 2...)
    spender: str         # Address claiming to own this UTXO (simplified — real Bitcoin uses scripts)

    def to_dict(self) -> dict:
        """Serialize for hashing."""
        return {"txid": self.txid, "vout": self.vout, "spender": self.spender}


# ----------------------------------------------------------------------------
# 2.3: Transaction — consumes inputs, produces outputs
# ----------------------------------------------------------------------------

@dataclass
class Transaction:
    """
    A transaction that spends existing UTXOs (inputs) and creates new ones (outputs).

    Think of it like breaking a $20 bill: you hand over the $20 (input),
    receive your purchase (output 1), and get change back (output 2).
    """
    inputs: list[TxInput]
    outputs: list[TxOutput]
    txid: str = ""       # Computed after construction

    def __post_init__(self):
        """Compute the transaction ID as the hash of its contents."""
        self.txid = self._compute_txid()

    def _compute_txid(self) -> str:
        """Hash all inputs and outputs to produce a unique transaction ID."""
        data = json.dumps({
            "inputs": [inp.to_dict() for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs],
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    @property
    def is_coinbase(self) -> bool:
        """Coinbase transactions have a single input referencing the null txid."""
        return (
            len(self.inputs) == 1
            and self.inputs[0].txid == COINBASE_TXID
            and self.inputs[0].vout == COINBASE_VOUT
        )

    @property
    def total_input_value(self) -> int:
        """Sum is only meaningful after validation resolves input amounts."""
        # This is set externally during validation, since inputs don't carry amounts
        return getattr(self, "_resolved_input_value", 0)

    @property
    def total_output_value(self) -> int:
        """Sum of all output amounts."""
        return sum(out.amount for out in self.outputs)


# ----------------------------------------------------------------------------
# 2.4: UTXO Set — the global ledger of all spendable outputs
# ----------------------------------------------------------------------------

class UTXOSet:
    """
    Tracks every unspent transaction output in the system.

    The key insight: Bitcoin doesn't track "balances." It tracks individual
    unspent coins (UTXOs). Your balance is just the sum of all UTXOs locked
    to your address.
    """

    def __init__(self):
        # Map from (txid, vout) → TxOutput
        # This is the heart of Bitcoin's state — the set of all spendable coins
        self._utxos: dict[tuple[str, int], TxOutput] = {}
        # Log of all processed transactions for history
        self._tx_history: list[Transaction] = []

    def get_utxo(self, txid: str, vout: int) -> TxOutput | None:
        """Look up a specific UTXO by its transaction ID and output index."""
        return self._utxos.get((txid, vout))

    def add_utxo(self, txid: str, vout: int, output: TxOutput) -> None:
        """Register a new unspent output in the set."""
        self._utxos[(txid, vout)] = output

    def remove_utxo(self, txid: str, vout: int) -> None:
        """Mark an output as spent by removing it from the unspent set."""
        del self._utxos[(txid, vout)]

    def get_balance(self, address: str) -> int:
        """Sum all UTXOs belonging to an address — this IS their balance."""
        return sum(
            utxo.amount
            for utxo in self._utxos.values()
            if utxo.recipient == address
        )

    def get_utxos_for(self, address: str) -> list[tuple[str, int, TxOutput]]:
        """Find all UTXOs belonging to an address, returned as (txid, vout, output)."""
        return [
            (txid, vout, utxo)
            for (txid, vout), utxo in self._utxos.items()
            if utxo.recipient == address
        ]

    @property
    def size(self) -> int:
        """Number of unspent outputs currently in the set."""
        return len(self._utxos)

    def validate_and_apply(self, tx: Transaction) -> tuple[bool, str]:
        """
        Validate a transaction and, if valid, update the UTXO set.

        Returns (success, message).

        Validation rules:
        1. Coinbase tx: no inputs to validate, just add outputs
        2. Regular tx: all inputs must reference existing UTXOs
        3. No double-spending: each input UTXO must still be unspent
        4. Input value >= output value (difference is the fee)
        5. Spender must match the UTXO's recipient (ownership check)
        """
        if tx.is_coinbase:
            # Coinbase creates new coins — no inputs to validate
            for idx, output in enumerate(tx.outputs):
                self.add_utxo(tx.txid, idx, output)
            self._tx_history.append(tx)
            return True, "Coinbase transaction accepted"

        # --- Validate each input ---
        total_input = 0
        inputs_to_consume = []  # Collect valid inputs before modifying state

        for inp in tx.inputs:
            # Check 1: Does this UTXO exist?
            utxo = self.get_utxo(inp.txid, inp.vout)
            if utxo is None:
                return False, (
                    f"Input references non-existent UTXO: "
                    f"txid={inp.txid[:16]}..., vout={inp.vout}"
                )

            # Check 2: Does the spender own this UTXO?
            if utxo.recipient != inp.spender:
                return False, (
                    f"Spender '{inp.spender}' does not own UTXO "
                    f"(owned by '{utxo.recipient}')"
                )

            total_input += utxo.amount
            inputs_to_consume.append((inp.txid, inp.vout))

        # Check 3: Outputs must not exceed inputs (remainder is fee)
        total_output = tx.total_output_value
        if total_output > total_input:
            return False, (
                f"Output value ({total_output}) exceeds input value ({total_input})"
            )

        # Store resolved input value for reference
        tx._resolved_input_value = total_input

        # --- Apply: remove spent UTXOs, add new ones ---
        for txid, vout in inputs_to_consume:
            self.remove_utxo(txid, vout)  # These coins are now spent

        for idx, output in enumerate(tx.outputs):
            self.add_utxo(tx.txid, idx, output)  # New coins enter the set

        self._tx_history.append(tx)
        fee = total_input - total_output
        return True, f"Transaction accepted (fee: {fee})"


# ----------------------------------------------------------------------------
# 2.5: Helper — create common transaction types
# ----------------------------------------------------------------------------

def create_coinbase_tx(recipient: str, reward: int = COINBASE_REWARD) -> Transaction:
    """Create a coinbase transaction that mints new coins to a recipient."""
    return Transaction(
        inputs=[TxInput(txid=COINBASE_TXID, vout=COINBASE_VOUT, spender="COINBASE")],
        outputs=[TxOutput(amount=reward, recipient=recipient)],
    )


def create_payment_tx(
    utxo_set: UTXOSet,
    sender: str,
    recipient: str,
    amount: int,
    fee: int = 0,
) -> Transaction | None:
    """
    Build a transaction that pays `amount` from sender to recipient.

    Automatically selects UTXOs and creates a change output if needed.
    Returns None if the sender has insufficient funds.
    """
    # Gather sender's UTXOs (simple greedy coin selection)
    available = utxo_set.get_utxos_for(sender)
    selected_inputs = []
    selected_value = 0
    needed = amount + fee

    for txid, vout, utxo in available:
        selected_inputs.append(TxInput(txid=txid, vout=vout, spender=sender))
        selected_value += utxo.amount
        if selected_value >= needed:
            break  # We have enough coins

    if selected_value < needed:
        return None  # Insufficient funds

    # Build outputs
    outputs = [TxOutput(amount=amount, recipient=recipient)]

    # Change output — return leftover to sender (minus fee)
    change = selected_value - amount - fee
    if change > 0:
        outputs.append(TxOutput(amount=change, recipient=sender))

    return Transaction(inputs=selected_inputs, outputs=outputs)


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def _print_header(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _print_tx(tx: Transaction, label: str = "") -> None:
    """Print a transaction in a visual box format."""
    tag = f" ({label})" if label else ""
    print(f"\n  Transaction{tag}")
    print(f"  ┌─{'─' * 54}─┐")
    print(f"  │ {'txid:':<8} {tx.txid[:40]}... │")

    # Show inputs
    print(f"  │ {'INPUTS:':<54} │")
    for i, inp in enumerate(tx.inputs):
        if inp.txid == COINBASE_TXID:
            print(f"  │   [{i}] COINBASE (new coins minted)                   │")
        else:
            line = f"[{i}] {inp.txid[:16]}...:{inp.vout} (by {inp.spender})"
            print(f"  │   {line:<52} │")

    # Show outputs
    print(f"  │ {'OUTPUTS:':<54} │")
    for i, out in enumerate(tx.outputs):
        line = f"[{i}] {out.amount:>6} → {out.recipient}"
        print(f"  │   {line:<52} │")

    print(f"  └─{'─' * 54}─┘")


def _print_utxo_set(utxo_set: UTXOSet, addresses: list[str]) -> None:
    """Print the current state of the UTXO set."""
    print(f"\n  UTXO Set ({utxo_set.size} unspent output(s)):")
    print(f"  ┌─{'─' * 54}─┐")

    for (txid, vout), utxo in utxo_set._utxos.items():
        line = f"{txid[:12]}...:{vout}  →  {utxo.amount:>4} to {utxo.recipient}"
        print(f"  │ {line:<54} │")

    print(f"  ├─{'─' * 54}─┤")

    # Show balances
    for addr in addresses:
        balance = utxo_set.get_balance(addr)
        line = f"Balance({addr}): {balance}"
        print(f"  │ {line:<54} │")

    print(f"  └─{'─' * 54}─┘")


def demo():
    """Run a visual demonstration of the UTXO model."""

    _print_header("UTXO (Unspent Transaction Output) Model")
    print("\n  In Bitcoin, there are no 'accounts' or 'balances.'")
    print("  Instead, value exists as discrete 'coins' (UTXOs) that")
    print("  are created and consumed by transactions.")

    utxo_set = UTXOSet()
    addresses = ["Alice", "Bob", "Charlie"]

    # ---- Step 1: Coinbase transaction — mint coins for Alice ----
    _print_header("Step 1: Coinbase → Alice gets 50 coins (mining reward)")

    coinbase_tx = create_coinbase_tx("Alice", COINBASE_REWARD)
    _print_tx(coinbase_tx, "Coinbase")

    ok, msg = utxo_set.validate_and_apply(coinbase_tx)
    print(f"\n  ✓ {msg}")
    _print_utxo_set(utxo_set, addresses)

    # ---- Step 2: Alice pays Bob 30, gets 18 change (2 fee) ----
    _print_header("Step 2: Alice → Bob 30 coins (fee: 2, change: 18)")

    tx_alice_bob = create_payment_tx(utxo_set, "Alice", "Bob", 30, fee=2)
    if tx_alice_bob is None:
        print("  ✗ Insufficient funds!")
        return

    _print_tx(tx_alice_bob, "Alice → Bob")

    ok, msg = utxo_set.validate_and_apply(tx_alice_bob)
    print(f"\n  ✓ {msg}")
    print("\n  Notice: Alice's original 50-coin UTXO was consumed entirely.")
    print("  She received 18 coins back as a new 'change' UTXO.")
    _print_utxo_set(utxo_set, addresses)

    # ---- Step 3: Bob pays Charlie 10, gets 19 change (1 fee) ----
    _print_header("Step 3: Bob → Charlie 10 coins (fee: 1, change: 19)")

    tx_bob_charlie = create_payment_tx(utxo_set, "Bob", "Charlie", 10, fee=1)
    if tx_bob_charlie is None:
        print("  ✗ Insufficient funds!")
        return

    _print_tx(tx_bob_charlie, "Bob → Charlie")

    ok, msg = utxo_set.validate_and_apply(tx_bob_charlie)
    print(f"\n  ✓ {msg}")
    _print_utxo_set(utxo_set, addresses)

    # ---- Step 4: Show double-spend prevention ----
    _print_header("Step 4: Double-Spend Attempt")
    print("\n  Bob tries to spend his original 30-coin output again...")

    # Manually craft a double-spend: reuse the same input Bob already spent
    double_spend_tx = Transaction(
        inputs=[TxInput(
            txid=tx_alice_bob.txid,   # Reference the Alice→Bob tx
            vout=0,                    # Output index 0 was the 30 to Bob
            spender="Bob",
        )],
        outputs=[TxOutput(amount=30, recipient="Bob")],
    )
    _print_tx(double_spend_tx, "DOUBLE SPEND")

    ok, msg = utxo_set.validate_and_apply(double_spend_tx)
    print(f"\n  ✗ REJECTED: {msg}")
    print("  The UTXO was already consumed — double-spending is impossible!")

    # ---- Step 5: Show ownership check ----
    _print_header("Step 5: Theft Attempt")
    print("\n  Charlie tries to spend Alice's UTXO...")

    theft_tx = Transaction(
        inputs=[TxInput(
            txid=tx_alice_bob.txid,   # Alice's change output
            vout=1,                    # Output index 1 was Alice's change
            spender="Charlie",         # Charlie claims to be the spender
        )],
        outputs=[TxOutput(amount=18, recipient="Charlie")],
    )
    _print_tx(theft_tx, "THEFT ATTEMPT")

    ok, msg = utxo_set.validate_and_apply(theft_tx)
    print(f"\n  ✗ REJECTED: {msg}")

    # ---- Final state ----
    _print_header("Final UTXO Set")
    _print_utxo_set(utxo_set, addresses)

    # Show the chain of value flow
    print("\n  Value Flow:")
    print("  ┌──────────┐    ┌──────────┐    ┌──────────┐")
    print("  │ Coinbase │───▶│  Alice   │───▶│   Bob    │───▶ Charlie: 10")
    print("  │  (50)    │    │  (18)    │    │  (19)    │")
    print("  └──────────┘    └──────────┘    └──────────┘")
    print(f"\n  Total fees collected: {50 - 18 - 30 + 30 - 19 - 10} coins")
    print("  (Fees = sum of inputs − sum of outputs, per transaction)\n")


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
