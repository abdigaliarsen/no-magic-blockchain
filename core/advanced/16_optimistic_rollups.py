"""
TITLE: Optimistic Rollups
CATEGORY: core

WHAT THIS IMPLEMENTS:
    A simplified optimistic rollup system with an L1 chain, L2 sequencer,
    challenge window, and fraud proof mechanism. The L2 sequencer batches
    transactions and posts state roots to L1. During the challenge window,
    anyone can submit a fraud proof by re-executing the batch and proving
    the posted state root is incorrect, causing the sequencer to be slashed.

KEY CONCEPTS:
    - L1/L2 architecture: L1 stores state roots, L2 processes transactions
    - Sequencer: batches L2 transactions and posts commitments to L1
    - Challenge window: period during which fraud proofs can be submitted
    - Fraud proof: re-execution proof that a posted state root is invalid
    - Slashing: sequencer loses their bond for posting invalid state roots

PREREQUISITE SCRIPTS:
    - core/fundamentals/05_blockchain.py (block/chain structure)
    - core/fundamentals/01_hashing.py (state root hashing)

REAL-WORLD RELEVANCE:
    Optimistic rollups are used by Optimism and Arbitrum, two of the largest
    Ethereum L2 scaling solutions. They process thousands of transactions per
    second off-chain while inheriting Ethereum's security through fraud proofs.
"""

import hashlib

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Challenge window: number of L1 blocks a batch must wait before finalization.
# In production Optimism/Arbitrum, this is ~7 days (~50,400 blocks).
# We use 7 blocks for a quick demo.
CHALLENGE_WINDOW = 7

# Sequencer bond amount (in wei-like units). Slashed on fraud.
SEQUENCER_BOND = 1000

# Initial balances for demo accounts on L2
INITIAL_BALANCE = 1000

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# Hashing utilities
# ----------------------------------------------------------------------------

def compute_hash(*args) -> str:
    """Hash arbitrary arguments into a hex digest."""
    data = "|".join(str(a) for a in args)
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def compute_state_root(state: dict) -> str:
    """Compute a deterministic hash of the L2 state (account balances).

    In production, this would be a Merkle Patricia Trie root.
    We simplify to a hash of sorted (account, balance) pairs.
    """
    # Sort for determinism — dict ordering shouldn't affect the root
    items = sorted(state.items())
    return compute_hash(str(items))


# ----------------------------------------------------------------------------
# L2 State Machine
# ----------------------------------------------------------------------------

class L2State:
    """The L2 state: a mapping of account addresses to balances.

    This is the state that the sequencer maintains and transitions
    by executing transactions. Think of it as a simplified EVM state.
    """

    def __init__(self, initial_balances: dict[str, int] = None):
        self.balances = dict(initial_balances or {})

    def copy(self) -> "L2State":
        """Create a deep copy of the state (for fraud proof re-execution)."""
        return L2State(dict(self.balances))

    def apply_tx(self, tx: dict) -> bool:
        """Apply a single transaction to the state.

        Returns True if the transaction is valid and applied, False otherwise.
        A transaction is: {"from": addr, "to": addr, "amount": int}
        """
        sender = tx["from"]
        receiver = tx["to"]
        amount = tx["amount"]

        # Validate: sender must have sufficient balance
        if self.balances.get(sender, 0) < amount:
            return False  # Insufficient funds — tx rejected

        # Execute the transfer
        self.balances[sender] -= amount
        self.balances[receiver] = self.balances.get(receiver, 0) + amount
        return True

    def apply_batch(self, transactions: list[dict]) -> str:
        """Apply a batch of transactions and return the new state root.

        This is what the sequencer does: execute txs in order, then
        commit the resulting state root to L1.
        """
        for tx in transactions:
            self.apply_tx(tx)  # Invalid txs are silently skipped
        return compute_state_root(self.balances)

    @property
    def root(self) -> str:
        """Current state root."""
        return compute_state_root(self.balances)


# ----------------------------------------------------------------------------
# L1 Chain (simplified)
# ----------------------------------------------------------------------------

class L1Block:
    """A block on the L1 chain. Stores state root submissions from L2."""

    def __init__(self, number: int, prev_hash: str):
        self.number = number
        self.prev_hash = prev_hash
        self.submissions = []        # L2 state root submissions in this block
        self.challenges = []         # Fraud proof challenges in this block
        self.hash = ""

    def finalize(self):
        """Compute this block's hash."""
        data = f"{self.number}|{self.prev_hash}|{self.submissions}|{self.challenges}"
        self.hash = compute_hash(data)


class L1Chain:
    """Simplified L1 chain that stores L2 state root submissions."""

    def __init__(self):
        # Genesis block
        genesis = L1Block(0, "0" * 16)
        genesis.finalize()
        self.blocks = [genesis]
        self.pending_submissions = []  # Submissions waiting to be finalized
        self.finalized_roots = []      # State roots that survived the challenge window
        self.sequencer_bonds = {}      # sequencer_id -> bond amount

    @property
    def height(self) -> int:
        return len(self.blocks) - 1

    def deposit_bond(self, sequencer_id: str, amount: int):
        """Sequencer deposits a bond to L1 (required to submit batches)."""
        self.sequencer_bonds[sequencer_id] = (
            self.sequencer_bonds.get(sequencer_id, 0) + amount
        )

    def submit_state_root(self, sequencer_id: str, batch_id: int,
                          state_root: str, transactions: list[dict],
                          pre_state_root: str):
        """Sequencer submits a state root to L1.

        The submission enters a challenge window. If no fraud proof is
        submitted within CHALLENGE_WINDOW blocks, it is finalized.
        """
        submission = {
            "batch_id": batch_id,
            "sequencer": sequencer_id,
            "state_root": state_root,
            "pre_state_root": pre_state_root,
            "transactions": transactions,  # Stored for fraud proof re-execution
            "submitted_at": self.height + 1,  # Next block
            "challenged": False,
            "finalized": False,
        }
        self.pending_submissions.append(submission)
        return submission

    def submit_fraud_proof(self, challenger: str, batch_id: int,
                           correct_root: str) -> dict:
        """Submit a fraud proof against a pending submission.

        The challenger re-executes the batch and provides the correct state root.
        If the posted root differs from the correct root, the fraud proof succeeds.
        """
        # Find the submission
        submission = None
        for s in self.pending_submissions:
            if s["batch_id"] == batch_id and not s["finalized"]:
                submission = s
                break

        if submission is None:
            return {"success": False, "reason": "Submission not found"}

        if submission["challenged"]:
            return {"success": False, "reason": "Already challenged"}

        # Check if within challenge window
        blocks_elapsed = self.height - submission["submitted_at"] + 1
        if blocks_elapsed > CHALLENGE_WINDOW:
            return {"success": False, "reason": "Challenge window expired"}

        # Verify the fraud proof: re-execute the batch
        if submission["state_root"] == correct_root:
            return {"success": False, "reason": "State root is correct, no fraud"}

        # Fraud confirmed! Slash the sequencer
        submission["challenged"] = True
        sequencer = submission["sequencer"]
        slashed = self.sequencer_bonds.get(sequencer, 0)
        self.sequencer_bonds[sequencer] = 0  # Slash entire bond

        # Reward the challenger (half the bond in production)
        reward = slashed // 2

        return {
            "success": True,
            "reason": "Fraud proof accepted",
            "slashed_amount": slashed,
            "challenger_reward": reward,
            "posted_root": submission["state_root"],
            "correct_root": correct_root,
        }

    def produce_block(self):
        """Produce a new L1 block and check for finalizations."""
        prev = self.blocks[-1]
        block = L1Block(prev.number + 1, prev.hash)

        # Check which submissions can be finalized (challenge window passed)
        for s in self.pending_submissions:
            if s["finalized"] or s["challenged"]:
                continue
            blocks_elapsed = block.number - s["submitted_at"]
            if blocks_elapsed >= CHALLENGE_WINDOW:
                s["finalized"] = True
                self.finalized_roots.append(s["state_root"])
                block.submissions.append(s)

        block.finalize()
        self.blocks.append(block)
        return block


# ----------------------------------------------------------------------------
# L2 Sequencer
# ----------------------------------------------------------------------------

class Sequencer:
    """L2 sequencer that batches transactions and posts state roots to L1.

    The sequencer is a centralized operator (in current rollup designs)
    that processes transactions quickly on L2, then posts commitments to L1.
    """

    def __init__(self, sequencer_id: str, l1: L1Chain,
                 initial_state: dict[str, int]):
        self.id = sequencer_id
        self.l1 = l1
        self.state = L2State(initial_state)
        self.batch_count = 0
        self.batches = []  # History of all batches
        self.is_malicious = False  # Can be set to True for fraud demo

    def process_batch(self, transactions: list[dict]) -> dict:
        """Process a batch of L2 transactions and submit the state root to L1.

        Returns a dict describing the batch.
        """
        pre_state_root = self.state.root
        pre_state = self.state.copy()  # Save for fraud proof comparison

        # Execute all transactions
        results = []
        for tx in transactions:
            ok = self.state.apply_tx(tx)
            results.append({"tx": tx, "success": ok})

        # Compute the post-state root
        post_state_root = self.state.root

        # If malicious, tamper with the state root
        if self.is_malicious:
            # Post a wrong state root (e.g., hash of garbage)
            post_state_root = compute_hash("malicious", str(self.batch_count))

        self.batch_count += 1
        batch = {
            "batch_id": self.batch_count,
            "transactions": transactions,
            "tx_results": results,
            "pre_state_root": pre_state_root,
            "post_state_root": post_state_root,
            "pre_state": pre_state,
            "honest_root": self.state.root,  # The actual correct root
        }
        self.batches.append(batch)

        # Submit to L1
        self.l1.submit_state_root(
            self.id, self.batch_count, post_state_root,
            transactions, pre_state_root
        )

        return batch


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of optimistic rollups."""

    print("=" * 70)
    print("  Optimistic Rollups — L2 Scaling with Fraud Proofs")
    print("=" * 70)

    # --- Explain the architecture ---
    print("\n--- Architecture Overview ---\n")
    print("  ┌──────────────────────────────────────────────────────────┐")
    print("  │                        L1 (Ethereum)                    │")
    print("  │  ┌────────────────────────────────────────────────────┐ │")
    print("  │  │  State Root Storage    Challenge Contract          │ │")
    print("  │  │  [root_1] [root_2]     [fraud proofs here]        │ │")
    print("  │  └────────────────────────────────────────────────────┘ │")
    print("  │                        ^                                │")
    print("  │                        | posts state roots              │")
    print("  │                        |                                │")
    print("  │  ┌────────────────────────────────────────────────────┐ │")
    print("  │  │                    L2 (Rollup)                     │ │")
    print("  │  │  Sequencer processes txs off-chain, batches them,  │ │")
    print("  │  │  and posts state roots to L1. If a root is wrong,  │ │")
    print("  │  │  anyone can challenge it with a fraud proof.       │ │")
    print("  │  └────────────────────────────────────────────────────┘ │")
    print("  └──────────────────────────────────────────────────────────┘")

    print(f"\n  Challenge window:  {CHALLENGE_WINDOW} L1 blocks")
    print(f"  Sequencer bond:    {SEQUENCER_BOND} units")

    # === Setup ===
    print("\n" + "-" * 70)
    print("  Setup: Initialize L1, L2, and Sequencer")
    print("-" * 70)

    initial_balances = {
        "Alice": INITIAL_BALANCE,
        "Bob": INITIAL_BALANCE,
        "Charlie": INITIAL_BALANCE,
    }

    l1 = L1Chain()
    sequencer = Sequencer("Sequencer_1", l1, initial_balances)

    # Sequencer deposits bond
    l1.deposit_bond("Sequencer_1", SEQUENCER_BOND)

    print(f"\n  L2 initial state:")
    for acct, bal in initial_balances.items():
        print(f"    {acct:10s}: {bal} units")
    print(f"  State root: {sequencer.state.root}")
    print(f"  Sequencer bond: {SEQUENCER_BOND} units")

    # === Batch 1: Honest batch ===
    print("\n" + "-" * 70)
    print("  Batch 1: Honest Transactions")
    print("-" * 70)

    batch1_txs = [
        {"from": "Alice", "to": "Bob", "amount": 100},
        {"from": "Bob", "to": "Charlie", "amount": 50},
        {"from": "Charlie", "to": "Alice", "amount": 25},
    ]

    print(f"\n  Transactions:")
    for i, tx in enumerate(batch1_txs):
        print(f"    {i+1}. {tx['from']} -> {tx['to']}: {tx['amount']} units")

    batch1 = sequencer.process_batch(batch1_txs)
    print(f"\n  Pre-state root:  {batch1['pre_state_root']}")
    print(f"  Post-state root: {batch1['post_state_root']}")

    print(f"\n  L2 state after batch 1:")
    for acct in sorted(sequencer.state.balances):
        print(f"    {acct:10s}: {sequencer.state.balances[acct]} units")

    print(f"\n  Submitted to L1 at block {l1.height + 1}")
    print(f"  Challenge window: blocks {l1.height + 1} to "
          f"{l1.height + 1 + CHALLENGE_WINDOW}")

    # Produce L1 blocks to advance past challenge window
    print(f"\n  Advancing L1 by {CHALLENGE_WINDOW + 1} blocks...")
    for _ in range(CHALLENGE_WINDOW + 1):
        l1.produce_block()

    finalized_count = len(l1.finalized_roots)
    print(f"  L1 height: {l1.height}")
    print(f"  Finalized roots: {finalized_count}")
    if finalized_count > 0:
        print(f"  Batch 1 state root FINALIZED (no challenge received)")

    # === Batch 2: Another honest batch ===
    print("\n" + "-" * 70)
    print("  Batch 2: More Honest Transactions")
    print("-" * 70)

    batch2_txs = [
        {"from": "Alice", "to": "Charlie", "amount": 200},
        {"from": "Bob", "to": "Alice", "amount": 150},
    ]

    print(f"\n  Transactions:")
    for i, tx in enumerate(batch2_txs):
        print(f"    {i+1}. {tx['from']} -> {tx['to']}: {tx['amount']} units")

    batch2 = sequencer.process_batch(batch2_txs)
    print(f"\n  Pre-state root:  {batch2['pre_state_root']}")
    print(f"  Post-state root: {batch2['post_state_root']}")

    print(f"\n  L2 state after batch 2:")
    for acct in sorted(sequencer.state.balances):
        print(f"    {acct:10s}: {sequencer.state.balances[acct]} units")

    # Advance past challenge window
    for _ in range(CHALLENGE_WINDOW + 1):
        l1.produce_block()
    print(f"\n  Batch 2 FINALIZED after challenge window.")

    # === Batch 3: FRAUDULENT batch ===
    print("\n" + "=" * 70)
    print("  Batch 3: FRAUDULENT Batch (Sequencer Goes Rogue)")
    print("=" * 70)

    # Make the sequencer malicious
    sequencer.is_malicious = True

    batch3_txs = [
        {"from": "Bob", "to": "Alice", "amount": 75},
        {"from": "Charlie", "to": "Bob", "amount": 100},
    ]

    print(f"\n  Transactions:")
    for i, tx in enumerate(batch3_txs):
        print(f"    {i+1}. {tx['from']} -> {tx['to']}: {tx['amount']} units")

    batch3 = sequencer.process_batch(batch3_txs)

    print(f"\n  Pre-state root:       {batch3['pre_state_root']}")
    print(f"  Posted state root:    {batch3['post_state_root']}  <-- WRONG!")
    print(f"  Correct state root:   {batch3['honest_root']}")
    print(f"\n  The sequencer posted a FAKE state root!")
    print(f"  (Maybe trying to steal funds by altering balances)")

    # --- Challenge phase ---
    print(f"\n  --- Challenge Phase ---")
    print(f"\n  A verifier (watcher) detects the fraud:")
    print(f"  1. Downloads the batch transactions from L1 calldata")
    print(f"  2. Re-executes them starting from pre_state_root")
    print(f"  3. Computes the CORRECT post-state root")
    print(f"  4. Sees it differs from the posted root")
    print(f"  5. Submits a fraud proof to L1")

    # Advance 3 blocks (still within challenge window)
    for _ in range(3):
        l1.produce_block()

    # Challenger re-executes the batch to get the correct root
    challenger_state = batch3["pre_state"].copy()
    correct_root = challenger_state.apply_batch(batch3_txs)

    print(f"\n  Challenger re-execution:")
    print(f"    Computed root: {correct_root}")
    print(f"    Posted root:   {batch3['post_state_root']}")
    print(f"    Match: {'YES' if correct_root == batch3['post_state_root'] else 'NO -- FRAUD DETECTED'}")

    # Submit fraud proof
    proof_result = l1.submit_fraud_proof(
        "Verifier_1", batch3["batch_id"], correct_root
    )

    print(f"\n  Fraud proof result:")
    print(f"    Success:           {proof_result['success']}")
    print(f"    Reason:            {proof_result['reason']}")
    if proof_result['success']:
        print(f"    Posted root:       {proof_result['posted_root']}")
        print(f"    Correct root:      {proof_result['correct_root']}")
        print(f"    Sequencer slashed: {proof_result['slashed_amount']} units")
        print(f"    Challenger reward: {proof_result['challenger_reward']} units")

    print(f"\n  Sequencer bond after slash: "
          f"{l1.sequencer_bonds.get('Sequencer_1', 0)} units")

    # === Show the full L1 state ===
    print("\n" + "-" * 70)
    print("  L1 Chain Summary")
    print("-" * 70)

    print(f"\n  L1 height: {l1.height}")
    print(f"  Finalized state roots: {len(l1.finalized_roots)}")
    for i, root in enumerate(l1.finalized_roots):
        print(f"    Batch {i+1}: {root}")

    print(f"\n  Pending submissions:")
    pending = [s for s in l1.pending_submissions
               if not s["finalized"] and not s["challenged"]]
    challenged = [s for s in l1.pending_submissions if s["challenged"]]

    if pending:
        for s in pending:
            print(f"    Batch {s['batch_id']}: {s['state_root']} (pending)")
    else:
        print(f"    (none)")

    if challenged:
        print(f"\n  Challenged (invalidated) submissions:")
        for s in challenged:
            print(f"    Batch {s['batch_id']}: {s['state_root']} (FRAUD)")

    # === Summary diagram ===
    print("\n" + "-" * 70)
    print("  Timeline")
    print("-" * 70)
    print()
    print("  L1 blocks:  [0]─[1]─[2]─...─[8]─[9]─...─[16]─[17]─[18]─[19]")
    print("               │                │                 │")
    print("               │    Batch 1      │    Batch 2      │    Batch 3")
    print("               │    submitted    │    submitted    │    submitted")
    print("               │                │                 │")
    print("               │  ...7 blocks... │  ...7 blocks... │")
    print("               │                │                 │")
    print("               │    FINALIZED    │    FINALIZED    │    CHALLENGED!")
    print("               │    (no fraud)   │    (no fraud)   │    (fraud proof")
    print("               │                │                 │     accepted)")

    # === Key properties ===
    print("\n" + "-" * 70)
    print("  Key Properties of Optimistic Rollups")
    print("-" * 70)
    print()
    print("  ┌──────────────────────────────────────────────────────────┐")
    print("  │  1. OPTIMISTIC: Assume batches are valid unless proven  │")
    print("  │     otherwise. No expensive computation on L1.          │")
    print("  │                                                         │")
    print("  │  2. FRAUD PROOFS: Anyone can challenge invalid batches  │")
    print("  │     by re-executing transactions and showing the        │")
    print("  │     correct state root differs from the posted one.     │")
    print("  │                                                         │")
    print("  │  3. CHALLENGE WINDOW: Batches are not final for ~7 days │")
    print("  │     This is the withdrawal delay users experience.      │")
    print("  │                                                         │")
    print("  │  4. ECONOMIC SECURITY: Sequencers post bonds that get   │")
    print("  │     slashed on fraud. Challengers are rewarded.         │")
    print("  │                                                         │")
    print("  │  5. DATA AVAILABILITY: Transaction data is posted to    │")
    print("  │     L1 (calldata/blobs) so anyone can re-execute.       │")
    print("  │                                                         │")
    print("  │  vs ZK-Rollups: No challenge window needed (proofs are  │")
    print("  │  verified immediately), but proving is more expensive.  │")
    print("  └──────────────────────────────────────────────────────────┘")

    print()
    print("=" * 70)
    print("  Optimistic Rollups complete.")
    print("=" * 70)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
