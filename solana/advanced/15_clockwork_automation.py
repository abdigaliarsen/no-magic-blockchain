"""
TITLE: Clockwork On-Chain Automation
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    Clockwork-style on-chain automation for Solana — the equivalent of cron jobs
    for smart contracts. Threads are scheduled tasks with trigger conditions
    (time-based, account-change, epoch-change). External "crankers" execute
    threads when conditions are met, receiving reimbursement for compute costs.

KEY CONCEPTS:
    - Thread: a scheduled task with trigger conditions and an instruction payload
    - Trigger types: cron schedule, account data change, epoch boundary, slot interval
    - Crank: external caller that executes a thread when its trigger fires
    - Thread authority: the account that created and controls the thread
    - Rate limiting: threads have a max executions-per-slot to prevent spam

PREREQUISITE SCRIPTS:
    - solana/fundamentals/01_accounts_model.py (account structure)
    - solana/fundamentals/03_programs.py (instruction processing)
    - solana/advanced/14_pdas_cpis_deep.py (PDAs for thread accounts)

REAL-WORLD RELEVANCE:
    On-chain automation enables DCA (Dollar Cost Averaging), auto-compounding
    yield farms, liquidation bots, and recurring payments — all without
    off-chain infrastructure. Clockwork was the leading automation protocol
    on Solana before sunsetting; similar systems (Geyser plugins, custom
    cranks) continue to power DeFi automation.
"""

import hashlib
import time as time_module
import random
import math

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Thread configuration limits
MAX_EXECUTIONS_PER_SLOT = 5        # Prevent a single thread from hogging resources
DEFAULT_THREAD_FEE = 5_000         # Lamports charged per thread execution
CRANK_REIMBURSEMENT = 1_000        # Lamports paid to the cranker per execution
MIN_THREAD_BALANCE = 100_000       # Minimum lamports to keep thread alive

# Simulation parameters
NUM_SLOTS = 40                     # Number of slots to simulate
SLOT_DURATION_MS = 400             # Real Solana: ~400ms per slot
SLOTS_PER_EPOCH = 20               # Simplified (real: 432,000)
RANDOM_SEED = 42                   # Reproducible results
LAMPORTS_PER_SOL = 1_000_000_000   # For display conversion

# Trigger type constants
TRIGGER_CRON = "cron"              # Execute on a cron-like schedule
TRIGGER_ACCOUNT = "account"        # Execute when an account's data changes
TRIGGER_EPOCH = "epoch"            # Execute at epoch boundaries
TRIGGER_SLOT = "slot"              # Execute every N slots


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: Trigger — defines when a thread should execute
# ----------------------------------------------------------------------------

class CronTrigger:
    """Cron-style trigger: fires every N slots (simplified from real cron syntax).

    Real Clockwork used cron expressions like "*/10 * * * *".
    We simplify to "every N slots" for clarity.
    """

    def __init__(self, every_n_slots):
        self.every_n_slots = every_n_slots  # Fire every N slots
        self.trigger_type = TRIGGER_CRON
        self.last_fired_slot = -every_n_slots  # Ensure first slot can fire

    def should_fire(self, current_slot, **kwargs):
        """Check if enough slots have passed since last firing."""
        elapsed = current_slot - self.last_fired_slot
        return elapsed >= self.every_n_slots

    def record_fire(self, slot):
        """Record that this trigger fired at the given slot."""
        self.last_fired_slot = slot

    def __repr__(self):
        return f"CronTrigger(every {self.every_n_slots} slots)"


class AccountTrigger:
    """Account-change trigger: fires when a monitored account's data changes.

    Useful for reactive automation — e.g., execute a liquidation when a
    borrower's collateral ratio drops below threshold.
    """

    def __init__(self, account_address, data_hash=None):
        self.account_address = account_address
        self.trigger_type = TRIGGER_ACCOUNT
        # Track the last known hash of the account data
        self.last_data_hash = data_hash or ""

    def should_fire(self, current_slot, accounts=None, **kwargs):
        """Check if the monitored account's data has changed."""
        if accounts is None:
            return False
        account = accounts.get(self.account_address)
        if account is None:
            return False
        # Hash the current account data to detect changes
        current_hash = hashlib.sha256(
            str(account.get("data", "")).encode()).hexdigest()[:16]
        return current_hash != self.last_data_hash

    def record_fire(self, slot, accounts=None):
        """Update the stored data hash after firing."""
        if accounts:
            account = accounts.get(self.account_address)
            if account:
                self.last_data_hash = hashlib.sha256(
                    str(account.get("data", "")).encode()).hexdigest()[:16]

    def __repr__(self):
        return f"AccountTrigger(watch={self.account_address[:12]}...)"


class EpochTrigger:
    """Epoch-boundary trigger: fires at the start of each new epoch.

    Useful for periodic rebalancing, reward distribution, or state cleanup.
    """

    def __init__(self):
        self.trigger_type = TRIGGER_EPOCH
        self.last_epoch = -1  # Track which epoch we last fired in

    def should_fire(self, current_slot, **kwargs):
        """Check if we've entered a new epoch."""
        current_epoch = current_slot // SLOTS_PER_EPOCH
        return current_epoch > self.last_epoch

    def record_fire(self, slot):
        """Record the epoch we fired in."""
        self.last_epoch = slot // SLOTS_PER_EPOCH

    def __repr__(self):
        return f"EpochTrigger(every {SLOTS_PER_EPOCH} slots)"


# ----------------------------------------------------------------------------
# 2b: Thread — a scheduled automation task
# ----------------------------------------------------------------------------

class Thread:
    """A Clockwork thread: a scheduled task stored as an on-chain account.

    Threads contain:
    - A trigger condition (when to execute)
    - An instruction payload (what to execute)
    - A balance (pays for execution fees)
    - An authority (who controls the thread)
    """

    def __init__(self, thread_id, authority, trigger, instruction,
                 balance_lamports=1_000_000):
        self.thread_id = thread_id
        self.authority = authority          # Who created this thread
        self.trigger = trigger              # When to execute
        self.instruction = instruction      # What to execute (dict)
        self.balance = balance_lamports     # Funds to pay for executions
        self.is_active = True               # Can be paused by authority
        self.execution_count = 0           # Total times executed
        self.executions_this_slot = 0      # Rate limiting counter
        self.created_at_slot = 0           # Slot when thread was created
        self.last_executed_slot = -1       # Last slot this thread ran
        self.execution_log = []            # History of executions

        # Derive a PDA-like address for this thread account
        address_data = f"thread:{thread_id}:{authority}"
        self.address = hashlib.sha256(address_data.encode()).hexdigest()[:24]

    @property
    def is_funded(self):
        """Check if thread has enough balance to execute."""
        return self.balance >= (DEFAULT_THREAD_FEE + CRANK_REIMBURSEMENT)

    def deduct_fee(self):
        """Deduct execution fee from thread balance."""
        total_fee = DEFAULT_THREAD_FEE + CRANK_REIMBURSEMENT
        self.balance -= total_fee
        return total_fee

    def __repr__(self):
        status = "active" if self.is_active else "paused"
        return (f"Thread({self.thread_id}, {status}, "
                f"balance={self.balance}, execs={self.execution_count})")


# ----------------------------------------------------------------------------
# 2c: Cranker — external service that triggers thread execution
# ----------------------------------------------------------------------------

class Cranker:
    """A cranker: an off-chain service that monitors threads and triggers execution.

    Crankers scan for threads whose trigger conditions are met, then submit
    transactions to execute them. They receive a small reimbursement for gas.
    Multiple crankers can compete to execute a thread — first one wins.
    """

    def __init__(self, name):
        self.name = name
        self.earnings = 0              # Total lamports earned from cranking
        self.cranks_performed = 0      # Number of successful cranks
        self.failed_cranks = 0         # Failed attempts

    def try_crank(self, thread, current_slot, accounts=None):
        """Attempt to execute a thread if its trigger condition is met.

        Returns: (success, execution_result)
        """
        # Check if thread is eligible for execution
        if not thread.is_active:
            return False, "Thread is paused"

        if not thread.is_funded:
            thread.is_active = False  # Auto-pause underfunded threads
            return False, "Thread underfunded — auto-paused"

        if thread.executions_this_slot >= MAX_EXECUTIONS_PER_SLOT:
            return False, "Rate limit exceeded for this slot"

        # Check trigger condition
        if not thread.trigger.should_fire(current_slot, accounts=accounts):
            return False, "Trigger condition not met"

        # Execute the thread
        fee = thread.deduct_fee()
        thread.execution_count += 1
        thread.executions_this_slot += 1
        thread.last_executed_slot = current_slot

        # Record trigger state
        if hasattr(thread.trigger, 'record_fire'):
            if isinstance(thread.trigger, AccountTrigger):
                thread.trigger.record_fire(current_slot, accounts=accounts)
            else:
                thread.trigger.record_fire(current_slot)

        # Execute the instruction (simulated)
        result = self._execute_instruction(thread.instruction, current_slot)

        # Cranker earns reimbursement
        self.earnings += CRANK_REIMBURSEMENT
        self.cranks_performed += 1

        # Log the execution
        execution_record = {
            "slot": current_slot,
            "cranker": self.name,
            "fee": fee,
            "result": result,
        }
        thread.execution_log.append(execution_record)

        return True, result

    def _execute_instruction(self, instruction, slot):
        """Simulate instruction execution. Returns a result dict."""
        instr_type = instruction.get("type", "unknown")

        if instr_type == "dca_swap":
            # Simulate a DCA swap with slight price variation
            base_price = instruction.get("base_price", 150.0)
            # Price varies by +/- 5% randomly
            price_variation = (random.random() - 0.5) * 0.10
            actual_price = base_price * (1 + price_variation)
            amount_usd = instruction.get("amount_usd", 10)
            tokens_bought = amount_usd / actual_price

            return {
                "type": "dca_swap",
                "price": actual_price,
                "spent": amount_usd,
                "received": tokens_bought,
                "token": instruction.get("token", "SOL"),
            }

        elif instr_type == "auto_compound":
            # Simulate yield compounding
            principal = instruction.get("principal", 1000)
            apy = instruction.get("apy", 0.08)
            # Each compound adds a fraction of the annual yield
            compound_fraction = 1 / (365 * 24)  # Hourly compounding equivalent
            interest = principal * apy * compound_fraction

            return {
                "type": "auto_compound",
                "principal": principal,
                "interest_added": interest,
                "new_balance": principal + interest,
            }

        elif instr_type == "liquidation_check":
            # Simulate checking a loan position for liquidation
            collateral = instruction.get("collateral", 100)
            debt = instruction.get("debt", 70)
            threshold = instruction.get("threshold", 0.75)
            ratio = debt / collateral if collateral > 0 else float("inf")

            return {
                "type": "liquidation_check",
                "collateral": collateral,
                "debt": debt,
                "ratio": ratio,
                "liquidatable": ratio >= threshold,
            }

        return {"type": instr_type, "status": "executed"}


# ----------------------------------------------------------------------------
# 2d: Scheduler — manages all threads and coordinates cranking
# ----------------------------------------------------------------------------

class AutomationScheduler:
    """The Clockwork scheduler: manages threads and processes triggers each slot.

    In reality this runs as part of the Solana validator or as a Geyser plugin.
    We simulate it as a central coordinator that checks all threads each slot.
    """

    def __init__(self):
        self.threads = {}              # thread_id → Thread
        self.crankers = []             # List of active crankers
        self.slot_log = {}             # slot → list of events
        self.accounts = {}             # Simulated account states for triggers

    def register_thread(self, thread):
        """Register a new automation thread."""
        self.threads[thread.thread_id] = thread

    def add_cranker(self, cranker):
        """Add a cranker to the pool."""
        self.crankers.append(cranker)

    def update_account(self, address, data):
        """Update an account's data — may trigger account-change threads."""
        self.accounts[address] = {"data": data, "address": address}

    def process_slot(self, slot):
        """Process all threads for a given slot.

        Resets per-slot rate limits, checks each thread's trigger,
        and assigns crankers to execute eligible threads.
        """
        events = []

        # Reset per-slot execution counters
        for thread in self.threads.values():
            thread.executions_this_slot = 0

        # Check each thread against its trigger
        for thread_id, thread in self.threads.items():
            if not thread.is_active:
                continue

            # Round-robin cranker assignment (simplified)
            cranker_idx = slot % len(self.crankers) if self.crankers else 0
            cranker = self.crankers[cranker_idx] if self.crankers else None

            if cranker is None:
                continue

            success, result = cranker.try_crank(
                thread, slot, accounts=self.accounts)

            if success:
                events.append({
                    "thread_id": thread_id,
                    "cranker": cranker.name,
                    "result": result,
                    "slot": slot,
                })

        self.slot_log[slot] = events
        return events


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Clockwork-style automation."""
    random.seed(RANDOM_SEED)

    print("=" * 72)
    print("  CLOCKWORK ON-CHAIN AUTOMATION — Cron Jobs for Solana")
    print("=" * 72)

    # --- Step 1: Create automation threads ---
    print("\n─── Step 1: Thread Creation ─────────────────────────────────────────")
    print("Creating scheduled automation threads with different triggers...\n")

    scheduler = AutomationScheduler()

    # Thread 1: DCA — buy SOL every 5 slots
    dca_thread = Thread(
        thread_id="dca-sol-daily",
        authority="Alice",
        trigger=CronTrigger(every_n_slots=5),
        instruction={
            "type": "dca_swap",
            "token": "SOL",
            "amount_usd": 50,
            "base_price": 150.0,
        },
        balance_lamports=500_000,
    )

    # Thread 2: Auto-compound — compound yield every 8 slots
    compound_thread = Thread(
        thread_id="compound-yield",
        authority="Bob",
        trigger=CronTrigger(every_n_slots=8),
        instruction={
            "type": "auto_compound",
            "principal": 10_000,
            "apy": 0.12,
        },
        balance_lamports=400_000,
    )

    # Thread 3: Liquidation monitor — triggers on account data change
    price_account = "oracle-sol-usd-0000"
    liquidation_thread = Thread(
        thread_id="liquidation-bot",
        authority="LiqBot",
        trigger=AccountTrigger(price_account),
        instruction={
            "type": "liquidation_check",
            "collateral": 100,
            "debt": 70,
            "threshold": 0.75,
        },
        balance_lamports=600_000,
    )

    # Thread 4: Epoch rebalancer — executes at epoch boundaries
    rebalance_thread = Thread(
        thread_id="epoch-rebalance",
        authority="VaultProtocol",
        trigger=EpochTrigger(),
        instruction={
            "type": "rebalance",
            "strategy": "equal-weight",
        },
        balance_lamports=300_000,
    )

    threads = [dca_thread, compound_thread, liquidation_thread, rebalance_thread]
    for t in threads:
        scheduler.register_thread(t)

    for t in threads:
        print(f"  ┌─────────────────────────────────────────────────────┐")
        print(f"  │  Thread: {t.thread_id:<42}│")
        print(f"  │  Authority: {t.authority:<39}│")
        print(f"  │  Trigger:   {str(t.trigger):<39}│")
        print(f"  │  Balance:   {t.balance:>10,} lamports"
              f"                    │")
        print(f"  │  Address:   {t.address:<39}│")
        print(f"  └─────────────────────────────────────────────────────┘")

    # --- Step 2: Register crankers ---
    print("\n─── Step 2: Cranker Registration ────────────────────────────────────")
    print("Crankers monitor threads and trigger execution for reimbursement...\n")

    crankers = [Cranker("CrankBot-A"), Cranker("CrankBot-B")]
    for c in crankers:
        scheduler.add_cranker(c)
        print(f"  Registered: {c.name}")

    # --- Step 3: Run the simulation ---
    print(f"\n─── Step 3: Simulation ({NUM_SLOTS} slots) "
          "────────────────────────────────────")
    print("Processing threads each slot, executing when triggers fire...\n")

    # Track DCA purchases for summary
    dca_purchases = []
    compound_balance = 10_000  # Track compounding balance

    print(f"  {'Slot':>4} │ {'Epoch':>5} │ {'Thread Executed':<20} │ "
          f"{'Cranker':<12} │ Details")
    print(f"  {'─' * 4}─┼─{'─' * 5}─┼─{'─' * 20}─┼─{'─' * 12}─┼─{'─' * 24}")

    for slot in range(NUM_SLOTS):
        epoch = slot // SLOTS_PER_EPOCH

        # Simulate oracle price updates at random slots (triggers account change)
        if slot % 3 == 0:  # Oracle updates every ~3 slots
            new_price = 150 + random.uniform(-10, 10)
            scheduler.update_account(price_account, {"price": new_price})

        events = scheduler.process_slot(slot)

        for event in events:
            result = event["result"]
            thread_id = event["thread_id"]
            cranker_name = event["cranker"]

            # Format details based on instruction type
            if result.get("type") == "dca_swap":
                detail = (f"Buy {result['received']:.4f} SOL "
                          f"@ ${result['price']:.2f}")
                dca_purchases.append(result)
            elif result.get("type") == "auto_compound":
                compound_balance = result["new_balance"]
                # Update instruction for next compound
                compound_thread.instruction["principal"] = compound_balance
                detail = f"+{result['interest_added']:.4f} → {compound_balance:.2f}"
            elif result.get("type") == "liquidation_check":
                liq = "LIQUIDATE!" if result["liquidatable"] else "safe"
                detail = f"ratio={result['ratio']:.2f} [{liq}]"
            elif result.get("type") == "rebalance":
                detail = "Rebalanced portfolio"
            else:
                detail = str(result.get("type", ""))

            print(f"  {slot:>4} │ {epoch:>5} │ {thread_id:<20} │ "
                  f"{cranker_name:<12} │ {detail}")

    # --- Step 4: DCA Summary ---
    print(f"\n─── Step 4: DCA Thread Summary ──────────────────────────────────────")
    print("Dollar Cost Averaging results across all executions:\n")

    if dca_purchases:
        total_sol = sum(p["received"] for p in dca_purchases)
        total_spent = sum(p["spent"] for p in dca_purchases)
        avg_price = total_spent / total_sol if total_sol > 0 else 0
        prices = [p["price"] for p in dca_purchases]

        print(f"  Executions:       {len(dca_purchases)}")
        print(f"  Total spent:      ${total_spent:.2f}")
        print(f"  Total SOL bought: {total_sol:.4f}")
        print(f"  Average price:    ${avg_price:.2f}")
        print(f"  Price range:      ${min(prices):.2f} — ${max(prices):.2f}")
        print()

        # Visual price chart
        print(f"  DCA Purchase Prices:")
        min_p, max_p = min(prices), max(prices)
        price_range = max_p - min_p if max_p > min_p else 1
        for i, p in enumerate(prices):
            bar_len = int(((p - min_p) / price_range) * 30) + 1
            bar = "█" * bar_len
            print(f"    #{i + 1:>2} ${p:>7.2f} │{bar}")

    # --- Step 5: Thread state summary ---
    print(f"\n─── Step 5: Thread State Summary ────────────────────────────────────")
    print("Final state of all automation threads:\n")

    print(f"  {'Thread':<20} │ {'Status':<8} │ {'Execs':>5} │ "
          f"{'Balance':>12} │ {'Funded':>6}")
    print(f"  {'─' * 20}─┼─{'─' * 8}─┼─{'─' * 5}─┼─{'─' * 12}─┼─{'─' * 6}")

    for t in threads:
        status = "active" if t.is_active else "PAUSED"
        funded = "yes" if t.is_funded else "NO"
        print(f"  {t.thread_id:<20} │ {status:<8} │ {t.execution_count:>5} │ "
              f"{t.balance:>12,} │ {funded:>6}")

    # --- Step 6: Cranker earnings ---
    print(f"\n─── Step 6: Cranker Earnings ────────────────────────────────────────")
    print("Crankers earn reimbursement for each successful execution:\n")

    for c in crankers:
        sol_earned = c.earnings / LAMPORTS_PER_SOL
        print(f"  {c.name}:")
        print(f"    Cranks performed: {c.cranks_performed}")
        print(f"    Earnings:        {c.earnings:,} lamports ({sol_earned:.9f} SOL)")

    # --- Step 7: Execution timeline ---
    print(f"\n─── Step 7: Execution Timeline ──────────────────────────────────────")
    print("Visual timeline showing when each thread executed:\n")

    # Create a compact timeline view
    symbols = {
        "dca-sol-daily": "D",
        "compound-yield": "C",
        "liquidation-bot": "L",
        "epoch-rebalance": "E",
    }

    print(f"  Legend: D=DCA  C=Compound  L=Liquidation  E=Epoch-rebalance\n")

    # Print in rows of 20 slots
    for row_start in range(0, NUM_SLOTS, 20):
        row_end = min(row_start + 20, NUM_SLOTS)

        # Slot numbers
        header = "  Slot: "
        for s in range(row_start, row_end):
            header += f"{s:>3}"
        print(header)

        # Execution markers
        line = "        "
        for s in range(row_start, row_end):
            events = scheduler.slot_log.get(s, [])
            if events:
                chars = "".join(symbols.get(e["thread_id"], "?")
                                for e in events)
                line += f"{chars:>3}"
            else:
                line += "  ."
        print(line)

        # Epoch boundaries
        epoch_line = "  Epoch:"
        for s in range(row_start, row_end):
            if s % SLOTS_PER_EPOCH == 0:
                epoch_line += f" E{s // SLOTS_PER_EPOCH}"
            else:
                epoch_line += "   "
        print(epoch_line)
        print()

    print("=" * 72)
    print("  KEY TAKEAWAYS")
    print("=" * 72)
    print("  1. Threads are on-chain cron jobs with configurable triggers")
    print("  2. Trigger types: cron (time), account-change, epoch, slot")
    print("  3. Crankers execute threads and earn reimbursement")
    print("  4. Threads auto-pause when balance runs out (no free execution)")
    print("  5. Rate limits prevent threads from consuming too many resources")
    print("  6. Use cases: DCA, auto-compound, liquidations, rebalancing")
    print("=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
