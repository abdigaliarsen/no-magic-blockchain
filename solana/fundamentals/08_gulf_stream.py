"""
TITLE: Gulf Stream — Mempool-less Transaction Forwarding
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    Solana's Gulf Stream protocol eliminates the traditional mempool by forwarding
    transactions directly to the current and upcoming leaders. Clients know the
    leader schedule in advance and send transactions to the right validator,
    reducing confirmation latency. Transactions include a recent blockhash that
    expires after ~60 seconds, preventing stale replays.

KEY CONCEPTS:
    - Deterministic leader schedule based on stake and epoch
    - Transaction forwarding to current and next leaders (no mempool)
    - Recent blockhash as transaction expiry mechanism
    - Reduced latency by skipping gossip-based mempool propagation

PREREQUISITE SCRIPTS:
    - solana/01_accounts_model.py
    - solana/02_proof_of_history.py

REAL-WORLD RELEVANCE:
    Gulf Stream is one of Solana's key innovations for achieving high throughput
    and low latency (~400ms). By eliminating the mempool and forwarding transactions
    directly to leaders, Solana avoids the gossip overhead that slows down networks
    like Bitcoin and Ethereum.
"""

import hashlib
import random
import time

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

SLOTS_PER_EPOCH = 432_000           # Real Solana: ~432k slots per epoch (~2 days)
SIMULATED_SLOTS = 10                # We simulate 10 slots for demo brevity
SLOT_DURATION_MS = 400              # Each slot is ~400ms on Solana
BLOCKHASH_EXPIRY_SLOTS = 150        # Transactions expire after ~150 slots (~60 seconds)
NUM_VALIDATORS = 8                  # Validators in our simulated network
NUM_CLIENTS = 5                     # Clients submitting transactions
SEED = 42                           # Reproducible randomness

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --------------------------------------------------------------------------
# Validator — a node that can be a leader
# --------------------------------------------------------------------------

class Validator:
    """A validator in the Solana network with a stake that determines leader frequency."""

    def __init__(self, name: str, stake: int):
        self.name = name          # Human-readable identifier
        self.stake = stake        # Staked lamports (affects leader selection probability)
        self.received_txs: list["Transaction"] = []  # Transactions received while leader
        self.blocks_produced: list[dict] = []         # Blocks produced during leadership

    def __repr__(self) -> str:
        return f"Validator({self.name}, stake={self.stake:,})"


# --------------------------------------------------------------------------
# Transaction — a client-submitted transaction
# --------------------------------------------------------------------------

class Transaction:
    """A Solana transaction with a recent blockhash for expiry."""

    def __init__(self, tx_id: str, sender: str, payload: str,
                 recent_blockhash: str, created_at_slot: int):
        self.tx_id = tx_id                        # Unique transaction identifier
        self.sender = sender                      # Which client sent this
        self.payload = payload                    # What the transaction does
        self.recent_blockhash = recent_blockhash  # Links to a recent block (for expiry)
        self.created_at_slot = created_at_slot    # Slot when the transaction was created
        self.status = "pending"                   # pending → confirmed | expired
        self.forwarded_to: list[str] = []         # Which validators received this tx
        self.confirmed_in_slot: int | None = None # Slot where it was included (if any)

    def is_expired(self, current_slot: int) -> bool:
        """Check if this transaction has expired based on slot age."""
        return (current_slot - self.created_at_slot) > BLOCKHASH_EXPIRY_SLOTS

    def __repr__(self) -> str:
        return f"Tx({self.tx_id}, {self.sender}, {self.status})"


# --------------------------------------------------------------------------
# Leader Schedule — deterministic rotation
# --------------------------------------------------------------------------

class LeaderSchedule:
    """Generates a deterministic leader schedule based on validator stakes.

    In real Solana, the schedule is computed per-epoch using a seed derived
    from the previous epoch's final blockhash. Leaders are selected with
    probability proportional to their stake.
    """

    def __init__(self, validators: list[Validator], epoch_seed: str):
        self.validators = validators
        self.epoch_seed = epoch_seed       # Seed for deterministic randomness
        self.schedule: list[str] = []      # slot_index -> leader name
        self._generate_schedule()

    def _generate_schedule(self):
        """Build the leader schedule for the epoch using stake-weighted selection.

        Higher-stake validators appear more frequently as leaders.
        The schedule is deterministic given the same seed and stakes.
        """
        # Create a weighted pool: each validator appears proportional to their stake
        total_stake = sum(v.stake for v in self.validators)
        rng = random.Random(self.epoch_seed)  # Deterministic RNG from epoch seed

        for slot in range(SIMULATED_SLOTS):
            # Weighted random selection: probability proportional to stake
            pick = rng.randint(0, total_stake - 1)
            cumulative = 0
            for v in self.validators:
                cumulative += v.stake
                if pick < cumulative:
                    self.schedule.append(v.name)
                    break

    def get_leader(self, slot: int) -> str:
        """Get the leader for a specific slot."""
        return self.schedule[slot % len(self.schedule)]

    def get_upcoming_leaders(self, current_slot: int, lookahead: int = 2) -> list[str]:
        """Get the leaders for the next few slots (for tx forwarding).

        Clients use this to know WHERE to send their transactions.
        """
        leaders = []
        for offset in range(lookahead + 1):  # Include current + next slots
            slot = current_slot + offset
            if slot < len(self.schedule):
                leader = self.schedule[slot]
                if leader not in leaders:  # Avoid duplicates
                    leaders.append(leader)
        return leaders


# --------------------------------------------------------------------------
# Blockhash Registry — tracks recent block hashes for expiry
# --------------------------------------------------------------------------

class BlockhashRegistry:
    """Tracks recent blockhashes that transactions can reference.

    In Solana, a transaction must include a recent blockhash. If the
    blockhash is too old (>150 slots), the transaction is rejected.
    """

    def __init__(self):
        self.hashes: dict[int, str] = {}  # slot -> blockhash

    def produce_blockhash(self, slot: int) -> str:
        """Generate a blockhash for a slot (simulates block production)."""
        h = hashlib.sha256(f"block:{slot}:{time.time()}".encode()).hexdigest()[:16]
        self.hashes[slot] = h
        return h

    def get_recent_hash(self, current_slot: int) -> str | None:
        """Get the most recent blockhash available to clients."""
        # Walk backwards to find the latest produced block
        for s in range(current_slot, max(-1, current_slot - 10), -1):
            if s in self.hashes:
                return self.hashes[s]
        return None

    def is_valid_blockhash(self, blockhash: str, current_slot: int) -> bool:
        """Check if a blockhash is still valid (not too old)."""
        for slot, h in self.hashes.items():
            if h == blockhash:
                return (current_slot - slot) <= BLOCKHASH_EXPIRY_SLOTS
        return False


# --------------------------------------------------------------------------
# Gulf Stream Network — ties everything together
# --------------------------------------------------------------------------

class GulfStreamNetwork:
    """Simulates the Gulf Stream protocol: direct tx forwarding to leaders."""

    def __init__(self, validators: list[Validator], epoch_seed: str):
        self.validators = {v.name: v for v in validators}
        self.schedule = LeaderSchedule(validators, epoch_seed)
        self.blockhash_registry = BlockhashRegistry()
        self.all_transactions: list[Transaction] = []
        self.event_log: list[str] = []  # Human-readable event log

    def submit_transaction(self, tx: Transaction, current_slot: int) -> None:
        """Client submits a transaction — it's forwarded directly to leaders.

        Gulf Stream's key insight: clients know the leader schedule, so they
        send transactions directly to the current + upcoming leaders instead
        of broadcasting to the whole network's mempool.
        """
        self.all_transactions.append(tx)

        # Determine where to forward: current leader + next leaders
        targets = self.schedule.get_upcoming_leaders(current_slot, lookahead=2)
        tx.forwarded_to = list(targets)

        for target in targets:
            if target in self.validators:
                self.validators[target].received_txs.append(tx)

        self.event_log.append(
            f"  Slot {current_slot}: {tx.sender} submits {tx.tx_id} "
            f"→ forwarded to [{', '.join(targets)}]"
        )

    def process_slot(self, slot: int) -> dict:
        """Process one slot: the leader produces a block from received transactions."""
        leader_name = self.schedule.get_leader(slot)
        leader = self.validators[leader_name]

        # Produce a blockhash for this slot
        blockhash = self.blockhash_registry.produce_blockhash(slot)

        # Leader processes pending transactions it has received
        included_txs = []
        expired_txs = []

        for tx in leader.received_txs:
            if tx.status != "pending":
                continue  # Already processed

            if tx.is_expired(slot):
                tx.status = "expired"
                expired_txs.append(tx)
            elif self.blockhash_registry.is_valid_blockhash(tx.recent_blockhash, slot):
                tx.status = "confirmed"
                tx.confirmed_in_slot = slot
                included_txs.append(tx)
            else:
                # Blockhash invalid (too old or unknown) — reject
                tx.status = "expired"
                expired_txs.append(tx)

        block = {
            "slot": slot,
            "leader": leader_name,
            "blockhash": blockhash,
            "transactions": [tx.tx_id for tx in included_txs],
            "expired": [tx.tx_id for tx in expired_txs],
        }
        leader.blocks_produced.append(block)

        return block


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Gulf Stream transaction forwarding."""

    random.seed(SEED)

    print("=" * 70)
    print("  GULF STREAM — Mempool-less Transaction Forwarding")
    print("=" * 70)
    print()

    # --- Setup validators with varying stakes ---
    validators = [
        Validator("Figment", 5_000_000),     # High stake → more leader slots
        Validator("Chorus", 3_000_000),
        Validator("Everstake", 2_500_000),
        Validator("P2P", 2_000_000),
        Validator("Coinbase", 4_000_000),     # High stake
        Validator("Kraken", 1_500_000),
        Validator("Lido", 3_500_000),
        Validator("Marinade", 1_000_000),     # Low stake → fewer leader slots
    ]

    network = GulfStreamNetwork(validators, epoch_seed="epoch-42-seed")

    # --- Part 1: Leader Schedule ---
    print("-" * 70)
    print("  PART 1: Leader Schedule (Stake-Weighted)")
    print("-" * 70)
    print()

    total_stake = sum(v.stake for v in validators)
    print("  Validator stakes:")
    for v in validators:
        pct = v.stake / total_stake * 100
        bar = "#" * int(pct / 2)  # Visual bar
        print(f"    {v.name:<12} {v.stake:>10,} lam ({pct:5.1f}%) {bar}")
    print()

    print("  Leader schedule for 10 slots:")
    print()
    print("  ┌──────┬──────────────┬─────────────────────────────────┐")
    print("  │ Slot │ Leader       │ Upcoming Leaders (for clients)  │")
    print("  ├──────┼──────────────┼─────────────────────────────────┤")

    for slot in range(SIMULATED_SLOTS):
        leader = network.schedule.get_leader(slot)
        upcoming = network.schedule.get_upcoming_leaders(slot, lookahead=2)
        upcoming_str = " → ".join(upcoming)
        print(f"  │  {slot:<3} │ {leader:<12} │ {upcoming_str:<31} │")

    print("  └──────┴──────────────┴─────────────────────────────────┘")
    print()

    # --- Part 2: Transaction Forwarding ---
    print("-" * 70)
    print("  PART 2: Transaction Forwarding (No Mempool)")
    print("-" * 70)
    print()

    # Produce initial blockhash so transactions can reference it
    initial_hash = network.blockhash_registry.produce_blockhash(0)

    # Create transactions from 5 clients at various slots
    client_txs = [
        # (client, payload, submit_at_slot)
        ("Client-A", "Transfer 5 SOL to Bob", 1),
        ("Client-B", "Stake 100 SOL", 2),
        ("Client-C", "Swap USDC→SOL on Jupiter", 3),
        ("Client-D", "Mint NFT #42", 4),
        ("Client-E", "Close token account", 5),
    ]

    print("  How Gulf Stream works:")
    print("    1. Client checks the leader schedule")
    print("    2. Client sends tx directly to current + upcoming leaders")
    print("    3. No gossip needed — leader gets the tx immediately")
    print()

    # Submit transactions
    tx_objects = []
    for client, payload, submit_slot in client_txs:
        recent_hash = network.blockhash_registry.get_recent_hash(submit_slot)
        if recent_hash is None:
            recent_hash = initial_hash  # Use initial hash if no block produced yet

        tx = Transaction(
            tx_id=f"tx-{len(tx_objects) + 1}",
            sender=client,
            payload=payload,
            recent_blockhash=recent_hash,
            created_at_slot=submit_slot,
        )
        tx_objects.append(tx)
        network.submit_transaction(tx, submit_slot)

    # Print forwarding events
    for event in network.event_log:
        print(event)
    print()

    print("  Comparison with traditional mempool:")
    print("  ┌──────────────────────┬──────────────────────────────────┐")
    print("  │ Traditional Mempool  │ Gulf Stream                      │")
    print("  ├──────────────────────┼──────────────────────────────────┤")
    print("  │ Tx → gossip to ALL   │ Tx → direct to leader           │")
    print("  │ O(n) propagation     │ O(1) forwarding                  │")
    print("  │ Leader picks from    │ Leader already has tx            │")
    print("  │   pooled txs         │   before its slot                │")
    print("  │ ~seconds latency     │ ~400ms latency                   │")
    print("  └──────────────────────┴──────────────────────────────────┘")
    print()

    # --- Part 3: Block Production ---
    print("-" * 70)
    print("  PART 3: Block Production Across Slots")
    print("-" * 70)
    print()

    for slot in range(1, SIMULATED_SLOTS):
        block = network.process_slot(slot)
        leader = block["leader"]
        txs = block["transactions"]
        expired = block["expired"]

        tx_display = ", ".join(txs) if txs else "(empty)"
        exp_display = f"  expired: {', '.join(expired)}" if expired else ""

        print(f"  Slot {slot}: Leader={leader:<12} blockhash={block['blockhash']}")
        print(f"          included: [{tx_display}]{exp_display}")
        print()

    # --- Part 4: Transaction Expiry ---
    print("-" * 70)
    print("  PART 4: Transaction Expiry (Recent Blockhash)")
    print("-" * 70)
    print()

    print(f"  Blockhash expiry window: {BLOCKHASH_EXPIRY_SLOTS} slots (~60 seconds)")
    print()
    print("  How expiry prevents replay attacks:")
    print("    1. Each tx includes a recent blockhash")
    print("    2. Validators reject txs with blockhash older than 150 slots")
    print("    3. This prevents old transactions from being re-submitted")
    print()

    # Create an already-expired transaction to demonstrate
    stale_hash = hashlib.sha256(b"very-old-block").hexdigest()[:16]
    expired_tx = Transaction(
        tx_id="tx-stale",
        sender="Client-Z",
        payload="Transfer 1000 SOL (replay attempt)",
        recent_blockhash=stale_hash,
        created_at_slot=0,     # Created at slot 0
    )

    # Try to process it at a much later slot
    late_slot = BLOCKHASH_EXPIRY_SLOTS + 10
    is_expired = expired_tx.is_expired(late_slot)
    is_valid_hash = network.blockhash_registry.is_valid_blockhash(stale_hash, late_slot)

    print(f"  Expired tx demo:")
    print(f"    tx_id:            {expired_tx.tx_id}")
    print(f"    recent_blockhash: {stale_hash}")
    print(f"    created_at_slot:  {expired_tx.created_at_slot}")
    print(f"    current_slot:     {late_slot}")
    print(f"    age (slots):      {late_slot - expired_tx.created_at_slot}")
    print(f"    max age:          {BLOCKHASH_EXPIRY_SLOTS}")
    print(f"    expired?          {'✗ YES — REJECTED' if is_expired else '✓ valid'}")
    print(f"    blockhash valid?  {'✓ yes' if is_valid_hash else '✗ NO — unknown/expired'}")
    print()

    # --- Part 5: Final Summary ---
    print("-" * 70)
    print("  PART 5: Transaction Results Summary")
    print("-" * 70)
    print()

    print("  ┌──────────┬────────────┬──────────────────────────────────┬───────────┐")
    print("  │ Tx ID    │ Sender     │ Payload                          │ Status    │")
    print("  ├──────────┼────────────┼──────────────────────────────────┼───────────┤")

    for tx in tx_objects:
        status_marker = "✓" if tx.status == "confirmed" else "✗"
        slot_info = f"slot {tx.confirmed_in_slot}" if tx.confirmed_in_slot else tx.status
        print(f"  │ {tx.tx_id:<8} │ {tx.sender:<10} │ {tx.payload:<32} │ {status_marker} {slot_info:<7} │")

    print("  └──────────┴────────────┴──────────────────────────────────┴───────────┘")
    print()

    confirmed = sum(1 for tx in tx_objects if tx.status == "confirmed")
    pending = sum(1 for tx in tx_objects if tx.status == "pending")
    expired = sum(1 for tx in tx_objects if tx.status == "expired")

    print(f"  Confirmed: {confirmed}/{len(tx_objects)}")
    print(f"  Pending:   {pending}/{len(tx_objects)}")
    print(f"  Expired:   {expired}/{len(tx_objects)}")
    print()
    print("  Gulf Stream eliminates the mempool bottleneck by letting clients")
    print("  send transactions directly to the right leader, cutting latency")
    print("  from seconds (gossip) to milliseconds (direct forwarding).")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
