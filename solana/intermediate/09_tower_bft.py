"""
TITLE: Tower BFT Consensus
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    Tower BFT — Solana's PBFT-inspired consensus optimized with Proof of History.
    Validators vote on slots, building a "lockout tower" where each successive vote
    doubles the lockout period on older votes. Fork switching becomes exponentially
    expensive, enabling fast finality without traditional PBFT message passing.

KEY CONCEPTS:
    - Vote lockouts: each vote doubles the lockout period for the vote below it
    - Lockout tower: a stack of votes with exponentially increasing lockout durations
    - Fork choice: stake-weighted vote counting to pick the heaviest fork
    - Exponential backoff: switching forks costs 2^(tower_depth) slots of progress
    - PoH integration: no need for synchronous message rounds — PoH provides ordering

PREREQUISITE SCRIPTS:
    - solana/fundamentals/02_proof_of_history.py (PoH as the clock)
    - solana/fundamentals/04_transactions.py (transaction structure)
    - core/fundamentals/07_consensus_pos.py (proof-of-stake basics)

REAL-WORLD RELEVANCE:
    Tower BFT is how Solana achieves ~400ms block times with finality in ~12 seconds.
    Validators run Tower BFT to decide which fork of the chain is canonical, and
    the exponential lockout prevents long-range attacks without requiring slashing.
"""

import hashlib
import random
import time

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Maximum depth of the vote lockout tower — once a vote reaches this depth
# it is "rooted" (finalized). Real Solana uses MAX_LOCKOUT_HISTORY = 31.
MAX_LOCKOUT_HISTORY = 8

# Base lockout period — the minimum number of slots a vote locks out
# Real Solana uses 2. A vote at depth d has lockout = BASE_LOCKOUT * 2^d.
BASE_LOCKOUT = 2

# Number of validators in our simulation
NUM_VALIDATORS = 4

# Number of slots to simulate
NUM_SLOTS = 30

# Seed for reproducible results
RANDOM_SEED = 42


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: Vote — a single vote in the lockout tower
# ----------------------------------------------------------------------------

class Vote:
    """A single vote in a validator's lockout tower.

    Each vote records the slot number being voted on and a confirmation count.
    The confirmation count increases each time a new vote is stacked on top,
    doubling the lockout period: lockout = BASE_LOCKOUT * 2^confirmation_count.
    """

    def __init__(self, slot, confirmation_count=0):
        self.slot = slot                            # Slot number this vote is for
        self.confirmation_count = confirmation_count  # Times confirmed by newer votes

    @property
    def lockout(self):
        """Lockout period in slots — exponentially increases with confirmations."""
        return BASE_LOCKOUT * (2 ** self.confirmation_count)

    @property
    def expiration_slot(self):
        """The slot at which this vote's lockout expires."""
        return self.slot + self.lockout

    def __repr__(self):
        return f"Vote(slot={self.slot}, conf={self.confirmation_count}, lockout={self.lockout})"


# ----------------------------------------------------------------------------
# 2b: Lockout Tower — a validator's vote stack
# ----------------------------------------------------------------------------

class LockoutTower:
    """A validator's Tower BFT vote stack.

    The tower is a stack of votes. When a new vote is pushed:
    1. Pop any expired votes (lockout period has passed)
    2. Push the new vote on top
    3. Increment confirmation_count for votes below IF they are on the same fork
    4. If a vote reaches MAX_LOCKOUT_HISTORY confirmations, it becomes "rooted" (finalized)
    """

    def __init__(self, validator_id):
        self.validator_id = validator_id
        self.votes = []          # Stack of Vote objects (newest on top)
        self.root_slot = 0       # Latest finalized slot
        self.vote_history = []   # Full history of (slot, fork_id) for analysis

    def can_vote(self, slot, fork_id, fork_ancestry):
        """Check if voting on this slot/fork would violate any lockout.

        A validator CANNOT vote on a fork that conflicts with a locked-out vote.
        The vote is allowed only if the new slot is on the same fork as all
        locked-out votes, or those lockouts have expired.
        """
        for vote in self.votes:
            if slot < vote.expiration_slot:
                # This vote is still locked out — new vote must be on same fork
                # Check if the voted-on slot is an ancestor of our new slot
                if vote.slot not in fork_ancestry:
                    return False  # Would switch forks while locked out
        return True

    def push_vote(self, slot, fork_id, fork_ancestry):
        """Push a new vote onto the tower.

        Returns (voted, newly_rooted_slot) — whether the vote succeeded and
        any slot that became finalized.
        """
        if not self.can_vote(slot, fork_id, fork_ancestry):
            return False, None  # Cannot vote — lockout violation

        # Remove expired votes (lockout period has passed for the new slot)
        self.votes = [v for v in self.votes if slot < v.expiration_slot]

        # Push the new vote
        new_vote = Vote(slot=slot, confirmation_count=0)
        self.votes.append(new_vote)
        self.vote_history.append((slot, fork_id))

        # Increment confirmation count for all votes below the new one
        # (they're on the same fork since we passed the can_vote check)
        newly_rooted = None
        for i in range(len(self.votes) - 2, -1, -1):
            self.votes[i].confirmation_count += 1
            # If a vote reaches max confirmations, it is rooted (finalized)
            if self.votes[i].confirmation_count >= MAX_LOCKOUT_HISTORY:
                newly_rooted = self.votes[i].slot
                self.root_slot = max(self.root_slot, newly_rooted)
                # Remove rooted vote and all below it
                self.votes = self.votes[i + 1:]
                break

        return True, newly_rooted

    def tower_depth(self):
        """Current depth of the tower (number of active votes)."""
        return len(self.votes)

    def switching_cost(self):
        """Cost of switching forks — measured in slots of lockout to burn.

        Higher tower = exponentially harder to switch.
        """
        if not self.votes:
            return 0
        # The deepest vote has the longest lockout
        return self.votes[0].lockout if self.votes else 0


# ----------------------------------------------------------------------------
# 2c: Fork — a chain of slots on one branch
# ----------------------------------------------------------------------------

class Fork:
    """Represents a fork (branch) of the slot chain.

    Each fork has a parent fork (except the root) and a list of slots.
    """

    def __init__(self, fork_id, parent_id=None, start_slot=0):
        self.fork_id = fork_id
        self.parent_id = parent_id    # Fork we branched from (None for root)
        self.start_slot = start_slot  # Slot where this fork diverged
        self.slots = []               # Slots produced on this fork
        self.stake_votes = {}         # slot → total stake that voted

    def add_slot(self, slot):
        """Add a new slot to this fork."""
        self.slots.append(slot)

    def latest_slot(self):
        """Most recent slot on this fork."""
        return self.slots[-1] if self.slots else self.start_slot


# ----------------------------------------------------------------------------
# 2d: Tower BFT simulator — orchestrates validators, forks, and voting
# ----------------------------------------------------------------------------

class TowerBFTSimulator:
    """Simulates Tower BFT consensus across multiple validators and forks."""

    def __init__(self, num_validators, seed=RANDOM_SEED):
        self.rng = random.Random(seed)

        # Create validators with random stake
        self.validators = {}
        self.stakes = {}
        for i in range(num_validators):
            vid = f"V{i}"
            self.validators[vid] = LockoutTower(vid)
            # Stake between 1000 and 10000 SOL
            self.stakes[vid] = self.rng.randint(1000, 10000)

        self.total_stake = sum(self.stakes.values())

        # Fork tracking
        self.forks = {"main": Fork("main", parent_id=None, start_slot=0)}
        self.slot_to_fork = {}    # slot_number → fork_id
        self.fork_ancestry = {}   # For each fork, the set of ancestor slots

        # Event log for visualization
        self.events = []

    def _get_fork_ancestry(self, fork_id):
        """Get all ancestor slots for a fork (includes parent forks' slots)."""
        ancestry = set()
        current = fork_id
        while current is not None:
            fork = self.forks[current]
            ancestry.update(fork.slots)
            ancestry.add(fork.start_slot)
            current = fork.parent_id
        return ancestry

    def create_fork(self, fork_id, parent_fork_id, branch_slot):
        """Create a new fork branching from parent at the given slot."""
        self.forks[fork_id] = Fork(fork_id, parent_fork_id, branch_slot)
        self.events.append(("FORK", branch_slot, fork_id, parent_fork_id))

    def produce_slot(self, slot, fork_id):
        """A leader produces a new slot on the given fork."""
        self.forks[fork_id].add_slot(slot)
        self.slot_to_fork[slot] = fork_id

    def process_votes(self, slot, fork_id):
        """All validators attempt to vote on the given slot.

        Returns dict of {validator_id: (voted, newly_rooted)}.
        """
        ancestry = self._get_fork_ancestry(fork_id)
        results = {}
        total_voted_stake = 0

        for vid, tower in self.validators.items():
            voted, rooted = tower.push_vote(slot, fork_id, ancestry)
            results[vid] = (voted, rooted)
            if voted:
                total_voted_stake += self.stakes[vid]
                self.events.append(("VOTE", slot, vid, fork_id, tower.tower_depth()))
            if rooted:
                self.events.append(("ROOT", slot, vid, rooted))

        # Track stake-weighted votes on this fork
        self.forks[fork_id].stake_votes[slot] = total_voted_stake
        return results

    def fork_weight(self, fork_id):
        """Calculate the total stake-weighted vote count for a fork.

        This is how validators decide which fork is canonical — the one
        with the most stake voting on it.
        """
        total = sum(self.forks[fork_id].stake_votes.values())
        # Include parent fork weight
        parent = self.forks[fork_id].parent_id
        if parent and parent in self.forks:
            total += self.fork_weight(parent)
        return total


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Tower BFT consensus."""

    print("=" * 70)
    print("  TOWER BFT — Solana's PoH-Optimized Consensus")
    print("=" * 70)

    # --- Lockout Tower Mechanics ---------------------------------------------
    print("\n--- 1. Lockout Tower Mechanics ---\n")
    print("  Each vote doubles the lockout for older votes:")
    print(f"  Base lockout = {BASE_LOCKOUT} slots")
    print(f"  Max tower depth = {MAX_LOCKOUT_HISTORY}\n")

    print(f"  {'Depth':>5s}  {'Confirmations':>14s}  {'Lockout (slots)':>16s}  {'Visualization'}")
    print(f"  {'─'*5}  {'─'*14}  {'─'*16}  {'─'*30}")
    for depth in range(MAX_LOCKOUT_HISTORY):
        lockout = BASE_LOCKOUT * (2 ** depth)
        bar = "█" * min(lockout // 2, 30)
        print(f"  {depth:>5d}  {depth:>14d}  {lockout:>16d}  {bar}")

    print(f"\n  At depth {MAX_LOCKOUT_HISTORY - 1}, lockout = "
          f"{BASE_LOCKOUT * 2**(MAX_LOCKOUT_HISTORY-1)} slots.")
    print(f"  Switching forks at that depth means wasting that many slots!")

    # --- Single Validator Tower Growth ----------------------------------------
    print("\n--- 2. Single Validator Tower Growth ---\n")

    tower = LockoutTower("demo")
    # Simulate voting on consecutive slots (same fork)
    ancestry = set(range(20))  # All slots on same fork

    print(f"  Voting on consecutive slots (same fork):\n")
    print(f"  {'Slot':>4s}  {'Tower Depth':>11s}  {'Root':>4s}  {'Tower State'}")
    print(f"  {'─'*4}  {'─'*11}  {'─'*4}  {'─'*45}")

    for slot in range(1, 16):
        voted, rooted = tower.push_vote(slot, "main", ancestry)
        # Format tower state showing each vote's lockout
        tower_str = " ".join(
            f"[s{v.slot}:L{v.lockout}]" for v in reversed(tower.votes)
        )
        root_str = str(rooted) if rooted else "-"
        print(f"  {slot:>4d}  {tower.tower_depth():>11d}  {root_str:>4s}  {tower_str}")

    # --- Multi-Validator Fork Choice ------------------------------------------
    print("\n--- 3. Multi-Validator Fork Choice Simulation ---\n")

    sim = TowerBFTSimulator(NUM_VALIDATORS)

    # Display validator stakes
    print("  Validator stakes:")
    print(f"  ┌─{'─'*6}─┬─{'─'*8}─┬─{'─'*12}─┐")
    print(f"  │ {'ID':>6s} │ {'Stake':>8s} │ {'% of Total':>12s} │")
    print(f"  ├─{'─'*6}─┼─{'─'*8}─┼─{'─'*12}─┤")
    for vid in sorted(sim.validators.keys()):
        pct = sim.stakes[vid] / sim.total_stake * 100
        print(f"  │ {vid:>6s} │ {sim.stakes[vid]:>8d} │ {pct:>11.1f}% │")
    print(f"  └─{'─'*6}─┴─{'─'*8}─┴─{'─'*12}─┘")
    print(f"  Total stake: {sim.total_stake:,}\n")

    # Phase 1: Normal consensus on main fork (slots 1-10)
    print("  Phase 1: Normal consensus (slots 1-10, all on main fork)")
    print(f"  {'─'*60}")

    for slot in range(1, 11):
        sim.produce_slot(slot, "main")
        results = sim.process_votes(slot, "main")
        voted = [vid for vid, (v, _) in results.items() if v]
        rooted = [(vid, r) for vid, (_, r) in results.items() if r]
        root_str = f" ROOT:{rooted[0][1]}" if rooted else ""
        print(f"  Slot {slot:>2d}: votes=[{','.join(voted)}]{root_str}")

    # Phase 2: Fork occurs at slot 10
    print(f"\n  Phase 2: Fork at slot 10!")
    print(f"  {'─'*60}")
    print("  main:    ...─[10]─[11]─[12]─[13]─[14]─[15]")
    print("                  └─[11']─[12']─[13']─[14']─[15']  (fork_b)")

    sim.create_fork("fork_b", "main", branch_slot=10)

    # Validators split: V0,V1 stay on main; V2,V3 try fork_b
    main_voters = ["V0", "V1"]
    fork_b_voters = ["V2", "V3"]

    print(f"\n  main voters:   {main_voters} "
          f"(stake: {sum(sim.stakes[v] for v in main_voters):,})")
    print(f"  fork_b voters: {fork_b_voters} "
          f"(stake: {sum(sim.stakes[v] for v in fork_b_voters):,})")

    # Simulate both forks advancing
    fork_events = []
    for slot in range(11, 16):
        # Main fork slot
        sim.produce_slot(slot, "main")
        main_ancestry = sim._get_fork_ancestry("main")
        # Fork B slot (use slot + 100 to avoid collision)
        fork_b_slot = slot + 100
        sim.produce_slot(fork_b_slot, "fork_b")
        fork_b_ancestry = sim._get_fork_ancestry("fork_b")

        main_voted = []
        fork_b_voted = []
        main_rooted = []
        fork_b_rooted = []

        for vid in main_voters:
            voted, rooted = sim.validators[vid].push_vote(slot, "main", main_ancestry)
            if voted:
                main_voted.append(vid)
                sim.forks["main"].stake_votes[slot] = (
                    sim.forks["main"].stake_votes.get(slot, 0) + sim.stakes[vid]
                )
            if rooted:
                main_rooted.append((vid, rooted))

        for vid in fork_b_voters:
            voted, rooted = sim.validators[vid].push_vote(
                fork_b_slot, "fork_b", fork_b_ancestry
            )
            if voted:
                fork_b_voted.append(vid)
                sim.forks["fork_b"].stake_votes[fork_b_slot] = (
                    sim.forks["fork_b"].stake_votes.get(fork_b_slot, 0) + sim.stakes[vid]
                )
            if rooted:
                fork_b_rooted.append((vid, rooted))

        main_root = f" ROOT:{main_rooted[0][1]}" if main_rooted else ""
        fork_root = f" ROOT:{fork_b_rooted[0][1]}" if fork_b_rooted else ""

        fork_events.append({
            "slot": slot,
            "main_voted": main_voted,
            "fork_b_voted": fork_b_voted,
            "main_root": main_root,
            "fork_root": fork_root,
        })

    print(f"\n  {'Slot':>4s}  {'Main Fork':>20s}  {'Fork B':>20s}")
    print(f"  {'─'*4}  {'─'*20}  {'─'*20}")
    for ev in fork_events:
        m_str = f"[{','.join(ev['main_voted'])}]{ev['main_root']}"
        f_str = f"[{','.join(ev['fork_b_voted'])}]{ev['fork_root']}"
        print(f"  {ev['slot']:>4d}  {m_str:>20s}  {f_str:>20s}")

    # --- Fork Weight Comparison -----------------------------------------------
    print("\n--- 4. Fork Weight (Stake-Weighted Votes) ---\n")

    main_weight = sim.fork_weight("main")
    fork_b_weight = sim.fork_weight("fork_b")
    total_weight = main_weight + fork_b_weight

    print(f"  Main fork weight:   {main_weight:>10,} "
          f"({'█' * int(main_weight / max(total_weight, 1) * 30)})")
    print(f"  Fork B weight:      {fork_b_weight:>10,} "
          f"({'█' * int(fork_b_weight / max(total_weight, 1) * 30)})")
    print(f"\n  Winner: {'Main Fork' if main_weight >= fork_b_weight else 'Fork B'} "
          f"(canonical chain)")

    # --- Lockout Tower Comparison ---------------------------------------------
    print("\n--- 5. Validator Lockout Towers ---\n")

    for vid in sorted(sim.validators.keys()):
        tower = sim.validators[vid]
        fork_label = "main" if vid in main_voters else "fork_b"
        cost = tower.switching_cost()

        print(f"  {vid} (fork: {fork_label}, root: {tower.root_slot}, "
              f"switch cost: {cost} slots):")

        if tower.votes:
            for i, vote in enumerate(reversed(tower.votes)):
                depth = len(tower.votes) - 1 - i
                bar = "░" * min(vote.lockout, 40)
                print(f"    [{depth}] slot={vote.slot:>3d}  "
                      f"conf={vote.confirmation_count}  "
                      f"lockout={vote.lockout:>4d}  {bar}")
        else:
            print(f"    (empty tower)")
        print()

    # --- Exponential Backoff Visualization ------------------------------------
    print("--- 6. Exponential Backoff: Why Fork Switching is Expensive ---\n")

    print("  Once a validator has voted deeply on a fork, switching requires")
    print("  waiting for lockouts to expire. The cost grows exponentially:\n")

    print(f"  {'Votes Deep':>10s}  {'Switch Cost':>12s}  {'Visualization'}")
    print(f"  {'─'*10}  {'─'*12}  {'─'*40}")
    for depth in range(1, MAX_LOCKOUT_HISTORY + 1):
        cost = BASE_LOCKOUT * (2 ** (depth - 1))
        bar = "▓" * min(cost, 40)
        print(f"  {depth:>10d}  {cost:>12d}  {bar}")

    print(f"\n  This exponential cost is what makes Tower BFT secure:")
    print(f"  an attacker would need to outpace the honest chain by")
    print(f"  an exponentially growing margin to revert finalized slots.")

    # --- PoH Advantage --------------------------------------------------------
    print("\n--- 7. PoH Advantage: No Message Passing ---\n")

    print("  Traditional PBFT (3-phase):")
    print("  ┌──────────┐   ┌──────────┐   ┌──────────┐")
    print("  │ Pre-Prepare│──▸│  Prepare  │──▸│  Commit   │")
    print("  │  O(n)     │   │  O(n²)   │   │  O(n²)   │")
    print("  └──────────┘   └──────────┘   └──────────┘")
    print(f"  Messages for {NUM_VALIDATORS} validators: "
          f"~{NUM_VALIDATORS + NUM_VALIDATORS**2 + NUM_VALIDATORS**2}")
    print()
    print("  Tower BFT with PoH:")
    print("  ┌──────────┐   ┌──────────┐")
    print("  │ PoH Slot  │──▸│   Vote    │")
    print("  │  (clock)  │   │  O(n)    │")
    print("  └──────────┘   └──────────┘")
    print(f"  Messages for {NUM_VALIDATORS} validators: ~{NUM_VALIDATORS}")
    print()
    print("  PoH eliminates the need for pre-prepare and prepare phases")
    print("  because the PoH sequence already provides a global ordering.")
    print("  Validators just vote on the PoH-ordered slots — no negotiation.")

    # --- Summary --------------------------------------------------------------
    print("\n--- Summary ---\n")
    print("  Tower BFT key properties:")
    print("  • Votes stack in a tower with exponentially increasing lockouts")
    print(f"  • Base lockout: {BASE_LOCKOUT} slots, doubling per confirmation")
    print(f"  • After {MAX_LOCKOUT_HISTORY} confirmations, a vote is rooted (finalized)")
    print("  • Fork choice: heaviest fork by stake-weighted votes wins")
    print("  • Switching forks costs exponentially more slots of progress")
    print("  • PoH removes PBFT message overhead: O(n) instead of O(n²)")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
