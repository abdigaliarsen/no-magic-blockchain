"""
TITLE: Sealevel Parallel Transaction Runtime
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    Sealevel — Solana's parallel transaction execution engine. Transactions declare
    which accounts they read from and write to upfront, enabling the runtime to
    identify non-conflicting transactions and execute them simultaneously. This
    script builds a dependency graph, detects conflicts, and schedules parallel batches.

KEY CONCEPTS:
    - Account-level parallelism: transactions touching disjoint accounts run concurrently
    - Read/write conflict detection: two transactions writing the same account must serialize
    - Dependency graph construction from declared account access lists
    - Batch scheduling: group non-conflicting transactions into parallel execution batches
    - Comparison of sequential vs parallel execution performance

PREREQUISITE SCRIPTS:
    - solana/fundamentals/01_accounts_model.py (account structure and ownership)
    - solana/fundamentals/03_programs.py (instruction processing)
    - solana/fundamentals/04_transactions.py (transaction format)

REAL-WORLD RELEVANCE:
    Sealevel is what gives Solana its high throughput — processing thousands of
    transactions per second by running them in parallel across available CPU cores.
    Every Solana validator runs Sealevel to maximize hardware utilization.
"""

import hashlib
import random
import time

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Number of simulated accounts in the system
NUM_ACCOUNTS = 12

# Number of transactions to schedule
NUM_TRANSACTIONS = 10

# Simulated per-transaction execution time in milliseconds
TX_EXEC_TIME_MS = 50

# Number of available CPU cores for parallel execution
NUM_CORES = 4

# Seed for reproducibility
RANDOM_SEED = 42


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: Account — simplified Solana account for tracking access
# ----------------------------------------------------------------------------

class Account:
    """A simplified Solana account for demonstrating access patterns."""

    def __init__(self, address, lamports=0, data=""):
        self.address = address      # Unique account identifier
        self.lamports = lamports    # Balance in lamports
        self.data = data            # Account data (simplified as string)

    def __repr__(self):
        return f"Account({self.address}, {self.lamports} lamports)"


# ----------------------------------------------------------------------------
# 2b: Transaction — declares account access upfront
# ----------------------------------------------------------------------------

class Transaction:
    """A transaction that declares its account access pattern.

    In Solana, every transaction MUST declare which accounts it reads from
    and which it writes to BEFORE execution. This is the key enabler for
    parallel execution — the runtime can analyze conflicts without running code.
    """

    def __init__(self, tx_id, read_accounts, write_accounts, description=""):
        self.tx_id = tx_id
        self.read_accounts = set(read_accounts)    # Accounts read (shared access OK)
        self.write_accounts = set(write_accounts)   # Accounts written (exclusive access)
        self.description = description
        # All accounts this transaction touches
        self.all_accounts = self.read_accounts | self.write_accounts

    def conflicts_with(self, other):
        """Check if this transaction conflicts with another.

        Conflict rules:
        - Write-Write: two txs writing the same account MUST serialize
        - Read-Write: if one reads and another writes same account, MUST serialize
        - Read-Read: two txs both reading the same account can run in parallel
        """
        # Write-write conflict: both write to the same account
        write_write = self.write_accounts & other.write_accounts
        if write_write:
            return True, "write-write", write_write

        # Read-write conflict: one reads what the other writes
        read_write_1 = self.read_accounts & other.write_accounts
        read_write_2 = self.write_accounts & other.read_accounts
        if read_write_1:
            return True, "read-write", read_write_1
        if read_write_2:
            return True, "write-read", read_write_2

        return False, None, set()  # No conflict — safe to parallelize

    def __repr__(self):
        return f"TX({self.tx_id})"


# ----------------------------------------------------------------------------
# 2c: Dependency Graph — tracks which transactions conflict
# ----------------------------------------------------------------------------

class DependencyGraph:
    """Builds a conflict graph from transaction access declarations.

    Nodes are transactions. An edge between two transactions means they
    conflict (share a writable account) and MUST be serialized.
    """

    def __init__(self):
        self.nodes = []            # List of transactions
        self.edges = []            # List of (tx_a, tx_b, conflict_type, accounts)
        self.adjacency = {}        # tx_id → set of conflicting tx_ids

    def add_transaction(self, tx):
        """Add a transaction to the graph."""
        self.nodes.append(tx)
        self.adjacency[tx.tx_id] = set()

    def build(self):
        """Build the conflict graph by checking all pairs of transactions.

        This is O(n²) in the number of transactions — but n is bounded
        by the number of transactions per block (typically a few thousand).
        """
        self.edges = []
        for i, tx_a in enumerate(self.nodes):
            for tx_b in self.nodes[i + 1:]:
                conflicts, conflict_type, accounts = tx_a.conflicts_with(tx_b)
                if conflicts:
                    self.edges.append((tx_a, tx_b, conflict_type, accounts))
                    self.adjacency[tx_a.tx_id].add(tx_b.tx_id)
                    self.adjacency[tx_b.tx_id].add(tx_a.tx_id)


# ----------------------------------------------------------------------------
# 2d: Batch Scheduler — groups non-conflicting transactions
# ----------------------------------------------------------------------------

class BatchScheduler:
    """Schedules transactions into parallel execution batches.

    Uses a greedy graph coloring approach: transactions in the same batch
    (color) have no conflicts and can run in parallel. Transactions in
    different batches are executed sequentially between batches.
    """

    @staticmethod
    def schedule(graph):
        """Assign transactions to parallel batches using greedy coloring.

        Returns list of batches, where each batch is a list of transactions
        that can run simultaneously.
        """
        # Greedy coloring: process transactions in order, assign the
        # smallest batch number that doesn't conflict with neighbors
        tx_to_batch = {}
        batches = []

        for tx in graph.nodes:
            # Find batch numbers used by conflicting transactions
            neighbor_batches = set()
            for neighbor_id in graph.adjacency[tx.tx_id]:
                if neighbor_id in tx_to_batch:
                    neighbor_batches.add(tx_to_batch[neighbor_id])

            # Assign the smallest available batch number
            batch_num = 0
            while batch_num in neighbor_batches:
                batch_num += 1

            tx_to_batch[tx.tx_id] = batch_num

            # Extend batches list if needed
            while len(batches) <= batch_num:
                batches.append([])
            batches[batch_num].append(tx)

        return batches

    @staticmethod
    def estimate_parallel_time(batches, tx_time_ms, num_cores):
        """Estimate execution time with parallel processing.

        Each batch runs its transactions in parallel (up to num_cores at a time).
        Batches run sequentially relative to each other.
        """
        total_ms = 0
        for batch in batches:
            # Within a batch, transactions run in parallel across cores
            # If more txs than cores, need multiple waves
            import math
            waves = math.ceil(len(batch) / num_cores)
            total_ms += waves * tx_time_ms
        return total_ms

    @staticmethod
    def estimate_sequential_time(num_txs, tx_time_ms):
        """Estimate execution time with purely sequential processing."""
        return num_txs * tx_time_ms


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Sealevel parallel execution."""

    print("=" * 70)
    print("  SEALEVEL — Solana's Parallel Transaction Runtime")
    print("=" * 70)

    rng = random.Random(RANDOM_SEED)

    # --- Create accounts ------------------------------------------------------
    print("\n--- 1. Account Setup ---\n")

    accounts = {}
    account_names = [
        "Alice", "Bob", "Carol", "Dave", "Eve", "Frank",
        "TokenMint", "Pool_AB", "Pool_CD", "Config",
        "ProgramX", "ProgramY",
    ]
    for name in account_names:
        addr = hashlib.sha256(name.encode()).hexdigest()[:16]
        accounts[name] = Account(addr, lamports=rng.randint(1000, 50000))

    print(f"  {'Account':>12s}  {'Address':>18s}  {'Lamports':>10s}")
    print(f"  {'─'*12}  {'─'*18}  {'─'*10}")
    for name, acct in accounts.items():
        print(f"  {name:>12s}  {acct.address:>18s}  {acct.lamports:>10,}")

    # --- Create transactions with declared access patterns --------------------
    print("\n--- 2. Transaction Access Declarations ---\n")

    # Build realistic-looking transactions with varying conflict patterns
    transactions = [
        Transaction("TX0", read_accounts=["ProgramX"],
                    write_accounts=["Alice", "Bob"],
                    description="Alice → Bob transfer"),
        Transaction("TX1", read_accounts=["ProgramX"],
                    write_accounts=["Carol", "Dave"],
                    description="Carol → Dave transfer"),
        Transaction("TX2", read_accounts=["ProgramX"],
                    write_accounts=["Eve", "Frank"],
                    description="Eve → Frank transfer"),
        Transaction("TX3", read_accounts=["ProgramY", "TokenMint"],
                    write_accounts=["Alice"],
                    description="Mint tokens to Alice"),
        Transaction("TX4", read_accounts=["ProgramY"],
                    write_accounts=["Pool_AB", "Alice", "Bob"],
                    description="Alice+Bob → Pool swap"),
        Transaction("TX5", read_accounts=["ProgramY"],
                    write_accounts=["Pool_CD", "Carol", "Dave"],
                    description="Carol+Dave → Pool swap"),
        Transaction("TX6", read_accounts=["Config", "ProgramX"],
                    write_accounts=["Eve"],
                    description="Update Eve's config"),
        Transaction("TX7", read_accounts=["ProgramX"],
                    write_accounts=["Frank", "Bob"],
                    description="Frank → Bob transfer"),
        Transaction("TX8", read_accounts=["Config"],
                    write_accounts=["TokenMint"],
                    description="Update token mint"),
        Transaction("TX9", read_accounts=["ProgramY", "Config"],
                    write_accounts=["Pool_AB"],
                    description="Rebalance Pool_AB"),
    ]

    print("  Each transaction declares its reads and writes UPFRONT:\n")
    print(f"  {'TX':>4s}  {'Description':>24s}  {'Reads':>20s}  {'Writes':>20s}")
    print(f"  {'─'*4}  {'─'*24}  {'─'*20}  {'─'*20}")
    for tx in transactions:
        reads = ",".join(sorted(tx.read_accounts))
        writes = ",".join(sorted(tx.write_accounts))
        print(f"  {tx.tx_id:>4s}  {tx.description:>24s}  {reads:>20s}  {writes:>20s}")

    # --- Build dependency graph -----------------------------------------------
    print("\n--- 3. Conflict Detection ---\n")

    graph = DependencyGraph()
    for tx in transactions:
        graph.add_transaction(tx)
    graph.build()

    print("  Checking all transaction pairs for conflicts:\n")
    if graph.edges:
        print(f"  {'TX A':>5s}  {'TX B':>5s}  {'Type':>12s}  {'Conflicting Accounts'}")
        print(f"  {'─'*5}  {'─'*5}  {'─'*12}  {'─'*30}")
        for tx_a, tx_b, ctype, accts in graph.edges:
            acct_str = ", ".join(sorted(accts))
            print(f"  {tx_a.tx_id:>5s}  {tx_b.tx_id:>5s}  {ctype:>12s}  {acct_str}")
    else:
        print("  No conflicts found — all transactions can run in parallel!")

    print(f"\n  Total conflicts: {len(graph.edges)}")
    print(f"  Total pairs checked: {len(transactions) * (len(transactions)-1) // 2}")

    # --- Visualize conflict graph ---------------------------------------------
    print("\n--- 4. Conflict Graph ---\n")

    print("  Nodes = transactions, edges = conflicts (must serialize)\n")
    # Show adjacency for each transaction
    for tx in transactions:
        neighbors = graph.adjacency[tx.tx_id]
        if neighbors:
            neighbor_str = ", ".join(sorted(neighbors))
            print(f"  {tx.tx_id} ── conflicts with ── [{neighbor_str}]")
        else:
            print(f"  {tx.tx_id} ── (no conflicts, fully parallel)")

    # --- Schedule into parallel batches ---------------------------------------
    print("\n--- 5. Parallel Batch Scheduling ---\n")

    batches = BatchScheduler.schedule(graph)

    print(f"  Scheduled {len(transactions)} transactions into "
          f"{len(batches)} parallel batches:\n")

    for i, batch in enumerate(batches):
        tx_ids = [tx.tx_id for tx in batch]
        bar_width = len(batch) * 8
        print(f"  Batch {i}: ┌{'─' * bar_width}┐")
        print(f"           │{'  '.join(f' {tid} ' for tid in tx_ids)}"
              f"{'':>{bar_width - sum(len(tid)+3 for tid in tx_ids)}}│")
        descs = [tx.description for tx in batch]
        # Verify no conflicts within batch
        ok = True
        for j, tx_a in enumerate(batch):
            for tx_b in batch[j+1:]:
                conflict, _, _ = tx_a.conflicts_with(tx_b)
                if conflict:
                    ok = False
        status = "✓ no conflicts" if ok else "✗ HAS CONFLICTS"
        print(f"           └{'─' * bar_width}┘  {status}")

    # --- Execution time comparison --------------------------------------------
    print("\n--- 6. Sequential vs Parallel Execution ---\n")

    seq_time = BatchScheduler.estimate_sequential_time(len(transactions), TX_EXEC_TIME_MS)
    par_time = BatchScheduler.estimate_parallel_time(batches, TX_EXEC_TIME_MS, NUM_CORES)

    print(f"  Configuration:")
    print(f"    Transactions:       {len(transactions)}")
    print(f"    CPU cores:          {NUM_CORES}")
    print(f"    Per-TX time:        {TX_EXEC_TIME_MS}ms")
    print(f"    Parallel batches:   {len(batches)}")
    print()

    # Sequential timeline
    print(f"  Sequential execution ({seq_time}ms total):")
    seq_bar = "".join(f"[{tx.tx_id}]" for tx in transactions)
    print(f"    {seq_bar}")
    print(f"    {'─' * len(seq_bar)}▸ time")
    print()

    # Parallel timeline
    print(f"  Parallel execution ({par_time}ms total):")
    for i, batch in enumerate(batches):
        import math
        waves = math.ceil(len(batch) / NUM_CORES)
        for w in range(waves):
            start = w * NUM_CORES
            end = min(start + NUM_CORES, len(batch))
            wave_txs = batch[start:end]
            core_bars = "  ".join(f"[{tx.tx_id}]" for tx in wave_txs)
            label = f"B{i}W{w}" if waves > 1 else f"B{i}  "
            print(f"    {label}: {core_bars}")
    print(f"    {'─' * 40}▸ time")
    print()

    speedup = seq_time / par_time if par_time > 0 else float('inf')
    print(f"  Speedup: {speedup:.1f}x "
          f"({seq_time}ms → {par_time}ms)")
    print(f"  Core utilization: {len(transactions) * TX_EXEC_TIME_MS / (par_time * NUM_CORES) * 100:.0f}%")

    # --- Read-Read Sharing Demo -----------------------------------------------
    print("\n--- 7. Read-Read Sharing (No Conflict) ---\n")

    print("  Key insight: READS don't conflict with each other!")
    print("  Multiple transactions can read the same account simultaneously.\n")

    # Show Config and ProgramX being read by multiple txs
    read_shared = {}
    for tx in transactions:
        for acct in tx.read_accounts:
            read_shared.setdefault(acct, []).append(tx.tx_id)

    print(f"  {'Account':>12s}  {'Read By'}")
    print(f"  {'─'*12}  {'─'*40}")
    for acct, readers in sorted(read_shared.items()):
        if len(readers) > 1:
            print(f"  {acct:>12s}  {', '.join(readers)}  "
                  f"(shared read — no conflict)")

    # --- Summary --------------------------------------------------------------
    print("\n--- Summary ---\n")
    print("  Sealevel parallel execution key properties:")
    print("  • Transactions MUST declare all account reads/writes upfront")
    print("  • Write-write and read-write on same account = conflict (serialize)")
    print("  • Read-read on same account = no conflict (parallelize)")
    print("  • Dependency graph groups non-conflicting txs into parallel batches")
    print(f"  • {len(transactions)} transactions scheduled into {len(batches)} batches "
          f"= {speedup:.1f}x speedup")
    print("  • This is why Solana can process thousands of TPS on commodity hardware")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
