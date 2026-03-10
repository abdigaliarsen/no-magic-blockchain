"""
TITLE: Solana Banking Stage
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    Solana's banking stage — the core transaction processing pipeline within a
    validator. Incoming transactions flow through fetch, signature verification,
    banking (execution), and broadcast stages. The banking stage uses multiple
    threads to process non-conflicting transactions in parallel, with priority
    fee-based scheduling to maximize validator revenue.

KEY CONCEPTS:
    - Pipeline stages: fetch → sigverify → banking → broadcast (TPU pipeline)
    - Multi-threaded banking: 4 threads process non-conflicting txs in parallel
    - Transaction scheduling: prioritize by compute unit price (priority fees)
    - Account locking: transactions that touch same accounts cannot run in parallel
    - Leader forwarding: non-leaders forward transactions to the current leader
    - Block packing: fit highest-value transactions within compute budget

PREREQUISITE SCRIPTS:
    - solana/fundamentals/01_accounts_model.py (account structure)
    - solana/fundamentals/04_transactions.py (transaction format)
    - solana/intermediate/10_sealevel_parallel.py (Sealevel parallel execution)

REAL-WORLD RELEVANCE:
    The banking stage is where Solana's high throughput comes from — processing
    thousands of transactions per second across parallel threads. Understanding
    the pipeline explains why Solana can achieve ~400ms block times and why
    priority fees matter for transaction inclusion during congestion.
"""

import hashlib
import random
import time as time_module
from collections import defaultdict
from enum import Enum

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Pipeline stage configuration
NUM_FETCH_THREADS = 2          # Threads receiving packets from the network
NUM_SIGVERIFY_THREADS = 2      # Threads verifying transaction signatures
NUM_BANKING_THREADS = 4        # Threads executing transactions (real: 4-6)
NUM_BROADCAST_THREADS = 1      # Thread broadcasting completed block

# Block limits — a Solana block has a compute unit (CU) budget
MAX_BLOCK_COMPUTE_UNITS = 48_000_000  # Real: 48M CU per block
DEFAULT_CU_PER_TX = 200_000           # Default compute units per transaction
MAX_TXS_PER_BLOCK = 200               # Simplified max transactions per block

# Priority fee configuration
MIN_PRIORITY_FEE = 0           # Base priority (lamports per CU)
BASE_FEE_LAMPORTS = 5_000      # Mandatory base fee per transaction

# Simulation parameters
NUM_INCOMING_TXS = 100         # Total transactions to process
NUM_SLOTS = 5                  # Slots to simulate
RANDOM_SEED = 42               # Reproducible results
LAMPORTS_PER_SOL = 1_000_000_000

# Simulated latency (microseconds) for each pipeline stage
FETCH_LATENCY_US = 50          # Network packet receive
SIGVERIFY_LATENCY_US = 100     # Ed25519 signature verification
BANKING_LATENCY_US = 200       # Transaction execution
BROADCAST_LATENCY_US = 50      # Shred and broadcast


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: Transaction — represents an incoming transaction to the banking stage
# ----------------------------------------------------------------------------

class TxStatus(Enum):
    """Transaction lifecycle stages within the banking pipeline."""
    RECEIVED = "received"          # Arrived at fetch stage
    SIG_VERIFIED = "sig_verified"  # Signature verified
    SCHEDULED = "scheduled"        # Queued for banking thread
    EXECUTING = "executing"        # Currently being processed
    EXECUTED = "executed"          # Successfully executed
    FAILED = "failed"              # Execution failed
    DROPPED = "dropped"            # Dropped (over capacity or conflict)


class BankingTransaction:
    """A transaction flowing through the banking stage pipeline.

    Each transaction declares which accounts it reads and writes.
    This information drives parallel scheduling — transactions touching
    different accounts can execute simultaneously.
    """

    def __init__(self, tx_id, sender, read_accounts, write_accounts,
                 compute_units=None, priority_fee=0, will_fail=False):
        self.tx_id = tx_id
        self.sender = sender
        self.read_accounts = set(read_accounts)    # Accounts read (shared lock)
        self.write_accounts = set(write_accounts)  # Accounts written (exclusive lock)
        self.compute_units = compute_units or DEFAULT_CU_PER_TX
        self.priority_fee = priority_fee           # Lamports per compute unit
        self.base_fee = BASE_FEE_LAMPORTS
        self.will_fail = will_fail                 # Simulate execution failure
        self.status = TxStatus.RECEIVED
        self.assigned_thread = None                # Banking thread assigned to
        self.pipeline_timestamps = {}              # Stage → simulated timestamp

        # Compute a short signature for display
        sig_data = f"{tx_id}:{sender}:{sorted(write_accounts)}"
        self.signature = hashlib.sha256(sig_data.encode()).hexdigest()[:12]

    @property
    def total_fee(self):
        """Total fee = base fee + (priority fee per CU * CU used)."""
        return self.base_fee + (self.priority_fee * self.compute_units)

    @property
    def all_accounts(self):
        """All accounts this transaction touches (for conflict detection)."""
        return self.read_accounts | self.write_accounts

    def conflicts_with(self, other):
        """Check if this transaction conflicts with another.

        Conflict occurs when:
        - Both write to the same account (write-write conflict)
        - One writes to an account the other reads (read-write conflict)
        Read-read access to the same account is safe (no conflict).
        """
        # Write-write conflict
        if self.write_accounts & other.write_accounts:
            return True
        # This writes what other reads
        if self.write_accounts & other.read_accounts:
            return True
        # Other writes what this reads
        if self.read_accounts & other.write_accounts:
            return True
        return False

    def __repr__(self):
        return (f"Tx({self.tx_id}, prio={self.priority_fee}, "
                f"CU={self.compute_units}, {self.status.value})")


# ----------------------------------------------------------------------------
# 2b: Pipeline stages — fetch, sigverify, banking, broadcast
# ----------------------------------------------------------------------------

class FetchStage:
    """Fetch stage: receives raw transaction packets from the network.

    In real Solana, this uses QUIC protocol to receive UDP packets from
    clients. Rate limiting and deduplication happen here.
    """

    def __init__(self, num_threads):
        self.num_threads = num_threads
        self.received = []             # Transactions received
        self.total_bytes = 0

    def receive(self, transactions):
        """Receive a batch of transactions from the network."""
        for tx in transactions:
            tx.status = TxStatus.RECEIVED
            tx.pipeline_timestamps["fetch"] = FETCH_LATENCY_US
            self.received.append(tx)

        self.total_bytes += len(transactions) * 1232  # ~1232 bytes per tx packet
        return self.received


class SigVerifyStage:
    """Signature verification stage: verify Ed25519 signatures in parallel.

    GPU-accelerated in real Solana. Invalid signatures are dropped here
    before they waste compute resources in the banking stage.
    """

    def __init__(self, num_threads):
        self.num_threads = num_threads
        self.verified = []
        self.dropped = []

    def verify(self, transactions):
        """Verify signatures — we simulate ~5% invalid signature rate."""
        for tx in transactions:
            # Simulate: 95% of transactions have valid signatures
            sig_valid = random.random() > 0.05

            if sig_valid:
                tx.status = TxStatus.SIG_VERIFIED
                tx.pipeline_timestamps["sigverify"] = SIGVERIFY_LATENCY_US
                self.verified.append(tx)
            else:
                tx.status = TxStatus.DROPPED
                tx.pipeline_timestamps["sigverify_drop"] = SIGVERIFY_LATENCY_US
                self.dropped.append(tx)

        return self.verified, self.dropped


class BankingStage:
    """Banking stage: the core execution engine with multi-threaded processing.

    Transactions are sorted by priority fee, then scheduled across threads.
    Each thread processes non-conflicting transactions. The scheduler ensures
    transactions touching the same accounts don't execute simultaneously.
    """

    def __init__(self, num_threads):
        self.num_threads = num_threads
        # Each thread has its own queue and locked accounts
        self.threads = {i: BankingThread(i) for i in range(num_threads)}
        self.executed = []
        self.failed = []
        self.dropped = []

    def schedule_and_execute(self, transactions, block_cu_budget):
        """Schedule transactions across threads and execute them.

        Algorithm:
        1. Sort by priority fee (highest first) — greedy fee maximization
        2. For each transaction, find a thread with no account conflicts
        3. If no thread is available, queue for later or drop
        4. Execute all threads, collecting results
        """
        # Step 1: Sort by priority fee (descending) — higher fee = higher priority
        sorted_txs = sorted(transactions, key=lambda t: t.priority_fee,
                            reverse=True)

        remaining_cu = block_cu_budget
        scheduled_count = 0
        dropped_count = 0

        # Step 2: Schedule each transaction to a compatible thread
        for tx in sorted_txs:
            # Check if block has capacity for this transaction
            if remaining_cu < tx.compute_units:
                tx.status = TxStatus.DROPPED
                self.dropped.append(tx)
                dropped_count += 1
                continue

            if scheduled_count >= MAX_TXS_PER_BLOCK:
                tx.status = TxStatus.DROPPED
                self.dropped.append(tx)
                dropped_count += 1
                continue

            # Find a thread with no conflicting locks
            assigned = False
            for thread_id in range(self.num_threads):
                thread = self.threads[thread_id]
                if thread.can_accept(tx):
                    thread.assign(tx)
                    tx.assigned_thread = thread_id
                    tx.status = TxStatus.SCHEDULED
                    remaining_cu -= tx.compute_units
                    scheduled_count += 1
                    assigned = True
                    break

            if not assigned:
                # Try the thread with the least load (even if there's a conflict
                # — it will wait for the conflicting tx to finish)
                least_loaded = min(self.threads.values(),
                                   key=lambda t: len(t.queue))
                least_loaded.assign(tx)
                tx.assigned_thread = least_loaded.thread_id
                tx.status = TxStatus.SCHEDULED
                remaining_cu -= tx.compute_units
                scheduled_count += 1

        # Step 3: Execute all threads
        for thread in self.threads.values():
            executed, failed = thread.execute_all()
            self.executed.extend(executed)
            self.failed.extend(failed)

        return self.executed, self.failed, self.dropped


class BankingThread:
    """A single banking thread that processes a queue of transactions.

    Each thread maintains a set of locked accounts. Transactions that
    conflict with currently-locked accounts wait until the lock is released.
    """

    def __init__(self, thread_id):
        self.thread_id = thread_id
        self.queue = []                    # Transactions assigned to this thread
        self.locked_write_accounts = set()  # Currently write-locked accounts
        self.locked_read_accounts = defaultdict(int)  # Read lock reference counts
        self.executed_count = 0
        self.total_cu_processed = 0
        self.total_fees_collected = 0

    def can_accept(self, tx):
        """Check if this thread can accept a transaction without conflicts.

        A transaction can be accepted if none of its write accounts are
        currently locked for writing, and none of its read accounts are
        currently locked for writing by another transaction.
        """
        # Check write-write conflicts
        if tx.write_accounts & self.locked_write_accounts:
            return False
        # Check if tx reads an account that's write-locked
        if tx.read_accounts & self.locked_write_accounts:
            return False
        # Check if tx writes an account that's read-locked
        for acc in tx.write_accounts:
            if self.locked_read_accounts.get(acc, 0) > 0:
                return False
        return True

    def assign(self, tx):
        """Assign a transaction to this thread and lock its accounts."""
        self.queue.append(tx)
        # Lock write accounts exclusively
        self.locked_write_accounts |= tx.write_accounts
        # Lock read accounts with reference counting (multiple readers OK)
        for acc in tx.read_accounts:
            self.locked_read_accounts[acc] += 1

    def execute_all(self):
        """Execute all queued transactions, releasing locks after each."""
        executed = []
        failed = []

        for tx in self.queue:
            tx.status = TxStatus.EXECUTING
            tx.pipeline_timestamps["banking"] = BANKING_LATENCY_US

            if tx.will_fail:
                tx.status = TxStatus.FAILED
                failed.append(tx)
            else:
                tx.status = TxStatus.EXECUTED
                self.executed_count += 1
                self.total_cu_processed += tx.compute_units
                self.total_fees_collected += tx.total_fee
                executed.append(tx)

            # Release locks after execution
            self.locked_write_accounts -= tx.write_accounts
            for acc in tx.read_accounts:
                self.locked_read_accounts[acc] -= 1

        return executed, failed


class BroadcastStage:
    """Broadcast stage: shred the completed block and send to the network.

    After the banking stage produces a block, it's broken into shreds
    (erasure-coded packets) and broadcast via Turbine protocol.
    """

    def __init__(self):
        self.blocks_broadcast = 0

    def broadcast(self, executed_txs, slot):
        """Broadcast the block — returns block summary."""
        total_cu = sum(tx.compute_units for tx in executed_txs)
        total_fees = sum(tx.total_fee for tx in executed_txs)

        for tx in executed_txs:
            tx.pipeline_timestamps["broadcast"] = BROADCAST_LATENCY_US

        self.blocks_broadcast += 1

        return {
            "slot": slot,
            "tx_count": len(executed_txs),
            "compute_units": total_cu,
            "total_fees": total_fees,
            "cu_utilization": total_cu / MAX_BLOCK_COMPUTE_UNITS * 100,
        }


# ----------------------------------------------------------------------------
# 2c: Leader scheduler — determines which validator produces each block
# ----------------------------------------------------------------------------

class LeaderSchedule:
    """Simplified leader schedule: assigns validators to slots.

    In real Solana, the leader schedule is derived from stake weights
    and a random seed. Non-leaders forward transactions to the current leader.
    """

    def __init__(self, validators):
        self.validators = validators
        # Pre-compute a simple round-robin schedule
        self.schedule = {
            slot: validators[slot % len(validators)]
            for slot in range(NUM_SLOTS * 2)
        }

    def get_leader(self, slot):
        """Get the leader validator for a given slot."""
        return self.schedule.get(slot, self.validators[0])

    def is_leader(self, validator, slot):
        """Check if a validator is the leader for a given slot."""
        return self.get_leader(slot) == validator


# ----------------------------------------------------------------------------
# 2d: Full TPU pipeline — orchestrates all stages
# ----------------------------------------------------------------------------

class TPUPipeline:
    """Transaction Processing Unit — the full pipeline from receive to broadcast.

    This is the core of a Solana validator. Transactions flow through four
    stages in a pipelined fashion: while one batch is in banking, the next
    batch is being signature-verified, and the next is being fetched.
    """

    def __init__(self):
        self.fetch = FetchStage(NUM_FETCH_THREADS)
        self.sigverify = SigVerifyStage(NUM_SIGVERIFY_THREADS)
        self.banking = BankingStage(NUM_BANKING_THREADS)
        self.broadcast = BroadcastStage()
        self.pipeline_stats = []

    def process_slot(self, transactions, slot):
        """Process a batch of transactions through the full pipeline.

        Returns detailed stats about each stage's performance.
        """
        stats = {"slot": slot}

        # Stage 1: Fetch — receive from network
        received = self.fetch.receive(transactions)
        stats["fetched"] = len(received)

        # Stage 2: SigVerify — verify signatures
        verified, sig_dropped = self.sigverify.verify(received)
        stats["sig_verified"] = len(verified)
        stats["sig_dropped"] = len(sig_dropped)

        # Stage 3: Banking — schedule and execute
        executed, failed, capacity_dropped = self.banking.schedule_and_execute(
            verified, MAX_BLOCK_COMPUTE_UNITS)
        stats["executed"] = len(executed)
        stats["failed"] = len(failed)
        stats["capacity_dropped"] = len(capacity_dropped)

        # Stage 4: Broadcast — shred and send
        block_info = self.broadcast.broadcast(executed, slot)
        stats["block"] = block_info

        self.pipeline_stats.append(stats)
        return stats


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def _generate_transactions(count):
    """Generate a realistic mix of transactions for simulation."""
    random.seed(RANDOM_SEED)

    # Simulate different types of Solana transactions
    account_pools = {
        "system": [f"sys-{i}" for i in range(5)],
        "token": [f"tok-{i}" for i in range(10)],
        "defi": [f"defi-{i}" for i in range(8)],
        "nft": [f"nft-{i}" for i in range(6)],
    }

    transactions = []
    for i in range(count):
        # Randomly choose transaction type
        tx_type = random.choice(["transfer", "swap", "mint", "stake"])

        if tx_type == "transfer":
            # Simple SOL transfer — touches 2 accounts
            accs = random.sample(account_pools["system"], 2)
            read_accs = [accs[0]]
            write_accs = accs
            cu = 150_000
            prio = random.choice([0, 0, 0, 100, 500, 1000])  # Most pay no priority

        elif tx_type == "swap":
            # DEX swap — touches pool + user accounts
            pool_acc = random.choice(account_pools["defi"])
            user_accs = random.sample(account_pools["token"], 2)
            read_accs = [pool_acc]
            write_accs = user_accs + [pool_acc]
            cu = 300_000
            # DEX swaps often have higher priority (MEV, arbitrage)
            prio = random.choice([0, 200, 500, 1000, 5000, 10000])

        elif tx_type == "mint":
            # NFT mint — touches mint + metadata accounts
            nft_acc = random.choice(account_pools["nft"])
            user_acc = random.choice(account_pools["token"])
            read_accs = []
            write_accs = [nft_acc, user_acc]
            cu = 250_000
            prio = random.choice([0, 0, 100, 2000, 5000])

        else:  # stake
            sys_acc = random.choice(account_pools["system"])
            read_accs = [sys_acc]
            write_accs = [sys_acc, f"stake-{i}"]
            cu = 200_000
            prio = 0  # Staking usually no priority fee

        # ~3% of transactions will fail execution
        will_fail = random.random() < 0.03

        tx = BankingTransaction(
            tx_id=f"tx-{i:04d}",
            sender=f"user-{random.randint(0, 20)}",
            read_accounts=read_accs,
            write_accounts=write_accs,
            compute_units=cu,
            priority_fee=prio,
            will_fail=will_fail,
        )
        transactions.append(tx)

    return transactions


def demo():
    """Run a visual demonstration of the Solana banking stage."""
    random.seed(RANDOM_SEED)

    print("=" * 72)
    print("  SOLANA BANKING STAGE — Transaction Processing Pipeline")
    print("=" * 72)

    # --- Step 1: Pipeline overview ---
    print("\n─── Step 1: TPU Pipeline Architecture ───────────────────────────────")
    print("Transactions flow through 4 stages in the Transaction Processing Unit:\n")

    print("  ┌──────────┐   ┌────────────┐   ┌──────────┐   ┌───────────┐")
    print("  │  FETCH   │──>│  SIGVERIFY  │──>│ BANKING  │──>│ BROADCAST │")
    print("  │ (2 thds) │   │  (2 thds)   │   │ (4 thds) │   │  (1 thd)  │")
    print("  └──────────┘   └────────────┘   └──────────┘   └───────────┘")
    print("    Receive       Verify Ed25519    Execute txs    Shred &")
    print("    packets       signatures        in parallel    broadcast")
    print()
    print(f"  Block compute budget: {MAX_BLOCK_COMPUTE_UNITS:>14,} CU")
    print(f"  Default CU per tx:    {DEFAULT_CU_PER_TX:>14,} CU")
    print(f"  Max txs per block:    {MAX_TXS_PER_BLOCK:>14,}")

    # --- Step 2: Generate and inspect transactions ---
    print("\n─── Step 2: Incoming Transaction Pool ──────────────────────────────")
    print(f"Generating {NUM_INCOMING_TXS} transactions with varying priorities...\n")

    all_txs = _generate_transactions(NUM_INCOMING_TXS)

    # Priority fee distribution
    prio_buckets = defaultdict(int)
    for tx in all_txs:
        if tx.priority_fee == 0:
            prio_buckets["0 (base)"] += 1
        elif tx.priority_fee <= 500:
            prio_buckets["1-500"] += 1
        elif tx.priority_fee <= 2000:
            prio_buckets["501-2000"] += 1
        else:
            prio_buckets["2001+"] += 1

    print("  Priority fee distribution:")
    for bucket, count in sorted(prio_buckets.items()):
        bar = "█" * (count // 2)
        print(f"    {bucket:>12} lamports/CU: {count:>3} txs │{bar}")

    total_cu_requested = sum(tx.compute_units for tx in all_txs)
    print(f"\n  Total CU requested: {total_cu_requested:>14,}")
    print(f"  Block CU capacity:  {MAX_BLOCK_COMPUTE_UNITS:>14,}")
    load_pct = total_cu_requested / MAX_BLOCK_COMPUTE_UNITS * 100
    print(f"  Load factor:        {load_pct:>13.1f}%")

    # --- Step 3: Process through the pipeline ---
    print("\n─── Step 3: Pipeline Execution ──────────────────────────────────────")
    print("Processing transactions through fetch → sigverify → banking → broadcast\n")

    pipeline = TPUPipeline()
    stats = pipeline.process_slot(all_txs, slot=0)

    # Show pipeline stage results
    stages = [
        ("Fetch", stats["fetched"], "Packets received from network"),
        ("SigVerify", stats["sig_verified"],
         f"Signatures valid ({stats['sig_dropped']} dropped)"),
        ("Banking", stats["executed"],
         f"Executed ({stats['failed']} failed, "
         f"{stats['capacity_dropped']} over capacity)"),
        ("Broadcast", stats["executed"], "Shredded and broadcast"),
    ]

    for stage_name, count, detail in stages:
        bar = "█" * (count // 3)
        print(f"  {stage_name:>10} │ {count:>3} txs │ {detail}")
        print(f"  {'':>10} │ {bar}")

    # --- Step 4: Thread assignment analysis ---
    print("\n─── Step 4: Banking Thread Assignment ──────────────────────────────")
    print(f"How transactions were distributed across {NUM_BANKING_THREADS} threads:\n")

    banking = pipeline.banking
    print(f"  {'Thread':>8} │ {'Queued':>6} │ {'Executed':>8} │ "
          f"{'CU Used':>12} │ {'Fees':>14} │ Load")
    print(f"  {'─' * 8}─┼─{'─' * 6}─┼─{'─' * 8}─┼─"
          f"{'─' * 12}─┼─{'─' * 14}─┼─{'─' * 20}")

    for tid, thread in banking.threads.items():
        queued = len(thread.queue)
        executed = thread.executed_count
        cu = thread.total_cu_processed
        fees = thread.total_fees_collected
        load_bar = "█" * (queued // 2) if queued > 0 else ""
        fees_sol = fees / LAMPORTS_PER_SOL
        print(f"  Thread {tid} │ {queued:>6} │ {executed:>8} │ "
              f"{cu:>12,} │ {fees:>10,} lam │ {load_bar}")

    # --- Step 5: Priority fee impact ---
    print("\n─── Step 5: Priority Fee Impact on Inclusion ─────────────────────────")
    print("Higher priority fee = better chance of inclusion in the block:\n")

    # Analyze which transactions made it in vs got dropped
    executed_txs = banking.executed
    dropped_txs = banking.dropped + banking.failed

    # Priority fee comparison
    exec_prios = [tx.priority_fee for tx in executed_txs] or [0]
    drop_prios = [tx.priority_fee for tx in dropped_txs] or [0]

    exec_avg = sum(exec_prios) / len(exec_prios)
    drop_avg = sum(drop_prios) / len(drop_prios) if drop_prios else 0

    print(f"  Executed transactions ({len(executed_txs)}):")
    print(f"    Avg priority fee: {exec_avg:>8.1f} lamports/CU")
    print(f"    Max priority fee: {max(exec_prios):>8} lamports/CU")
    print(f"    Min priority fee: {min(exec_prios):>8} lamports/CU")

    if dropped_txs:
        print(f"\n  Dropped/failed transactions ({len(dropped_txs)}):")
        print(f"    Avg priority fee: {drop_avg:>8.1f} lamports/CU")
        print(f"    Max priority fee: {max(drop_prios):>8} lamports/CU")
        print(f"    Min priority fee: {min(drop_prios):>8} lamports/CU")

    # --- Step 6: Account conflict analysis ---
    print("\n─── Step 6: Account Conflict Analysis ──────────────────────────────")
    print("Transactions touching the same accounts cannot run in parallel:\n")

    # Count how many txs touch each account
    account_usage = defaultdict(int)
    for tx in all_txs:
        for acc in tx.all_accounts:
            account_usage[acc] += 1

    # Show the most contended accounts
    hot_accounts = sorted(account_usage.items(), key=lambda x: x[1],
                          reverse=True)[:10]

    print(f"  {'Account':<15} │ {'Txs Touching':>12} │ Contention")
    print(f"  {'─' * 15}─┼─{'─' * 12}─┼─{'─' * 30}")

    for acc, count in hot_accounts:
        bar = "█" * count
        heat = "HOT" if count > 10 else "warm" if count > 5 else "cold"
        print(f"  {acc:<15} │ {count:>12} │ {bar} ({heat})")

    print(f"\n  Hot accounts create serialization points — transactions")
    print(f"  touching them must wait, reducing parallelism.")

    # --- Step 7: Leader forwarding ---
    print("\n─── Step 7: Leader Forwarding ───────────────────────────────────────")
    print("Non-leader validators forward transactions to the current leader:\n")

    validators = ["ValidatorA", "ValidatorB", "ValidatorC", "ValidatorD"]
    leader_schedule = LeaderSchedule(validators)

    print(f"  {'Slot':>4} │ {'Leader':<12} │ Forwarding Path")
    print(f"  {'─' * 4}─┼─{'─' * 12}─┼─{'─' * 45}")

    for slot in range(NUM_SLOTS):
        leader = leader_schedule.get_leader(slot)
        # Non-leaders forward to current leader
        forwarders = [v for v in validators if v != leader]
        fwd_arrows = " → ".join(forwarders[:2]) + f" → [{leader}]"
        print(f"  {slot:>4} │ {leader:<12} │ {fwd_arrows}")

    # Also show upcoming leader lookahead
    print(f"\n  Gulf Stream optimization: clients send txs to upcoming leaders")
    print(f"  Leader lookahead: {NUM_SLOTS} slots ahead")
    for slot in range(NUM_SLOTS):
        next_leader = leader_schedule.get_leader(slot + 1)
        print(f"    Slot {slot}: Leader={leader_schedule.get_leader(slot)}, "
              f"Next={next_leader} (clients pre-send)")

    # --- Step 8: Block summary ---
    print("\n─── Step 8: Block Production Summary ────────────────────────────────")

    block = stats["block"]
    total_fees = block["total_fees"]
    fees_sol = total_fees / LAMPORTS_PER_SOL

    print(f"  ┌─────────────────────────────────────────────────────┐")
    print(f"  │  BLOCK #{block['slot']}                                        │")
    print(f"  │  ───────────────────────────────────────────────    │")
    print(f"  │  Transactions:    {block['tx_count']:>6}                          │")
    print(f"  │  Compute units:   {block['compute_units']:>12,}                  │")
    print(f"  │  CU utilization:  {block['cu_utilization']:>9.1f}%                     │")
    print(f"  │  Total fees:      {total_fees:>12,} lamports              │")
    print(f"  │                   ({fees_sol:.6f} SOL)                  │")
    print(f"  │  Banking threads: {NUM_BANKING_THREADS}                               │")
    print(f"  └─────────────────────────────────────────────────────┘")

    # Pipeline latency breakdown
    print(f"\n  Pipeline latency per transaction (simulated):")
    print(f"    Fetch:     {FETCH_LATENCY_US:>6} us")
    print(f"    SigVerify: {SIGVERIFY_LATENCY_US:>6} us")
    print(f"    Banking:   {BANKING_LATENCY_US:>6} us")
    print(f"    Broadcast: {BROADCAST_LATENCY_US:>6} us")
    total_latency = (FETCH_LATENCY_US + SIGVERIFY_LATENCY_US +
                     BANKING_LATENCY_US + BROADCAST_LATENCY_US)
    print(f"    ─────────────────")
    print(f"    Total:     {total_latency:>6} us ({total_latency / 1000:.1f} ms)")

    print("\n" + "=" * 72)
    print("  KEY TAKEAWAYS")
    print("=" * 72)
    print("  1. TPU pipeline: fetch → sigverify → banking → broadcast")
    print("  2. Banking stage uses 4 threads for parallel execution")
    print("  3. Account locking prevents conflicting txs from running together")
    print("  4. Priority fees determine transaction ordering during congestion")
    print("  5. Hot accounts (e.g., popular DEX pools) create bottlenecks")
    print("  6. Non-leaders forward txs to the current leader (Gulf Stream)")
    print("=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
