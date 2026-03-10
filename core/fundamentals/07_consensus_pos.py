"""
TITLE: Proof of Stake Consensus
CATEGORY: core

WHAT THIS IMPLEMENTS:
    A proof-of-stake consensus mechanism where validators are selected to propose
    blocks with probability proportional to their staked amount. Includes slashing
    logic that penalizes validators caught double-signing (proposing two different
    blocks for the same slot).

KEY CONCEPTS:
    - Validator selection weighted by stake
    - Slashing for misbehavior (double-signing)
    - Epoch-based rotation and finality

PREREQUISITE SCRIPTS:
    - core/05_blockchain.py

REAL-WORLD RELEVANCE:
    Ethereum switched from proof-of-work to proof-of-stake in "The Merge" (Sep 2022).
    Validators lock up 32 ETH and are randomly selected to propose/attest blocks,
    with misbehavior punished by slashing their stake.
"""

import hashlib
import random
import time

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

NUM_VALIDATORS = 5                  # Number of validators in the network
SLOTS_PER_EPOCH = 20                # How many block slots make up one epoch
NUM_EPOCHS = 5                      # Total epochs to simulate (100 slots total)
SLASH_PENALTY_FRACTION = 0.5        # Fraction of stake burned when slashed
MIN_STAKE = 1                       # Minimum stake to remain an active validator
SEED = 42                           # Fixed seed for reproducible demos

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --------------------------------------------------------------------------
# Validator
# --------------------------------------------------------------------------

class Validator:
    """Represents a PoS validator with a stake and tracking state."""

    def __init__(self, address: str, stake: int):
        self.address = address        # Human-readable identifier
        self.stake = stake            # Amount of tokens staked (voting power)
        self.active = True            # Whether this validator can be selected
        self.slashed = False          # Whether this validator has been penalized
        self.blocks_proposed = 0      # Counter for demo statistics
        self.proposals: dict[int, str] = {}  # slot -> block_hash, to detect double-signing

    def __repr__(self) -> str:
        status = "SLASHED" if self.slashed else ("active" if self.active else "inactive")
        return f"Validator({self.address}, stake={self.stake}, {status})"


# --------------------------------------------------------------------------
# Block (minimal, just enough for consensus demonstration)
# --------------------------------------------------------------------------

class Block:
    """A simplified block used to demonstrate proposer selection and signing."""

    def __init__(self, slot: int, epoch: int, proposer: str, data: str):
        self.slot = slot
        self.epoch = epoch
        self.proposer = proposer
        self.data = data
        self.timestamp = time.time()
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Hash the block contents to get a unique fingerprint."""
        content = f"{self.slot}:{self.epoch}:{self.proposer}:{self.data}:{self.timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()


# --------------------------------------------------------------------------
# Proof-of-Stake Engine
# --------------------------------------------------------------------------

class ProofOfStake:
    """Manages validator set, selection, and slashing for PoS consensus."""

    def __init__(self, validators: list[Validator], rng: random.Random | None = None):
        self.validators = {v.address: v for v in validators}
        self.rng = rng or random.Random()  # Pluggable RNG for reproducibility
        self.chain: list[Block] = []       # Finalized chain of blocks
        self.slash_log: list[dict] = []    # Record of slashing events

    # ---- Validator selection ------------------------------------------------

    def _active_validators(self) -> list[Validator]:
        """Return only validators that are active and above minimum stake."""
        return [
            v for v in self.validators.values()
            if v.active and not v.slashed and v.stake >= MIN_STAKE
        ]

    def select_proposer(self, slot: int, epoch: int) -> Validator | None:
        """
        Select a block proposer weighted by stake.

        The selection uses a deterministic seed derived from slot + epoch so that
        every honest node agrees on who the proposer is for each slot.
        """
        active = self._active_validators()
        if not active:
            return None  # No validators available — chain halts

        # Build weighted list: higher stake = more chances of selection
        stakes = [v.stake for v in active]
        total_stake = sum(stakes)

        # Use slot and epoch to seed selection — deterministic but unpredictable
        # In real PoS (e.g., Ethereum) a RANDAO or VDF provides this randomness
        seed_material = f"{slot}:{epoch}".encode()
        slot_seed = int(hashlib.sha256(seed_material).hexdigest(), 16)
        self.rng.seed(slot_seed)

        # Weighted random choice: probability proportional to stake fraction
        cumulative = 0.0
        pick = self.rng.random() * total_stake
        for validator, stake in zip(active, stakes):
            cumulative += stake
            if pick <= cumulative:
                return validator

        return active[-1]  # Fallback (shouldn't reach here due to float precision)

    # ---- Block proposal -----------------------------------------------------

    def propose_block(self, slot: int, epoch: int, data: str) -> Block | None:
        """Select a proposer and have them create a block for this slot."""
        proposer = self.select_proposer(slot, epoch)
        if proposer is None:
            return None

        block = Block(slot=slot, epoch=epoch, proposer=proposer.address, data=data)

        # Record this proposal so we can detect double-signing later
        proposer.proposals[slot] = block.hash
        proposer.blocks_proposed += 1

        self.chain.append(block)
        return block

    # ---- Slashing -----------------------------------------------------------

    def detect_double_sign(self, validator_addr: str, slot: int,
                           second_block_hash: str) -> bool:
        """
        Check if a validator proposed two different blocks for the same slot.

        Double-signing is the cardinal sin of PoS — it means the validator tried
        to create a fork, which undermines consensus. Real networks (Ethereum,
        Cosmos) slash heavily for this.
        """
        validator = self.validators.get(validator_addr)
        if validator is None:
            return False

        # If the validator already proposed a *different* block for this slot,
        # that's a double-sign
        if slot in validator.proposals and validator.proposals[slot] != second_block_hash:
            return True
        return False

    def slash_validator(self, validator_addr: str, reason: str) -> dict | None:
        """
        Slash a misbehaving validator: burn part of their stake, deactivate them.

        Returns a record of the slashing event for the log.
        """
        validator = self.validators.get(validator_addr)
        if validator is None or validator.slashed:
            return None  # Already slashed or doesn't exist

        old_stake = validator.stake
        # Burn a fraction of their stake as punishment
        penalty = int(old_stake * SLASH_PENALTY_FRACTION)
        validator.stake -= penalty
        validator.slashed = True
        validator.active = False  # Remove from active set immediately

        event = {
            "validator": validator_addr,
            "reason": reason,
            "old_stake": old_stake,
            "penalty": penalty,
            "remaining_stake": validator.stake,
        }
        self.slash_log.append(event)
        return event

    # ---- Epoch processing ---------------------------------------------------

    def run_epoch(self, epoch: int, slots_per_epoch: int) -> list[Block]:
        """
        Process all slots in an epoch: select proposers and produce blocks.

        In real PoS, an epoch boundary is where finality checkpoints happen
        and the validator set can be reshuffled.
        """
        blocks = []
        for slot_in_epoch in range(slots_per_epoch):
            global_slot = epoch * slots_per_epoch + slot_in_epoch
            data = f"Transactions for slot {global_slot}"
            block = self.propose_block(global_slot, epoch, data)
            if block:
                blocks.append(block)
        return blocks


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of the concept."""

    print("=" * 65)
    print("  PROOF OF STAKE CONSENSUS — From Scratch")
    print("=" * 65)

    # ---- Set up validators with varying stakes ------------------------------
    validators = [
        Validator("Alice",   100),   # Largest stake — should win most often
        Validator("Bob",      60),
        Validator("Charlie",  30),
        Validator("Diana",    8),
        Validator("Eve",      2),    # Smallest stake — rare selections
    ]

    total_stake = sum(v.stake for v in validators)

    print("\n--- Validator Set ---\n")
    print(f"  {'Validator':<12} {'Stake':>8} {'Weight':>10}")
    print(f"  {'─' * 12} {'─' * 8} {'─' * 10}")
    for v in validators:
        weight = v.stake / total_stake * 100
        print(f"  {v.address:<12} {v.stake:>8} {weight:>9.1f}%")
    print(f"\n  Total staked: {total_stake}")

    # ---- Run epochs ---------------------------------------------------------
    pos = ProofOfStake(validators)

    print(f"\n{'=' * 65}")
    print(f"  Simulating {NUM_EPOCHS} epochs × {SLOTS_PER_EPOCH} slots = "
          f"{NUM_EPOCHS * SLOTS_PER_EPOCH} blocks")
    print(f"{'=' * 65}\n")

    for epoch in range(NUM_EPOCHS):
        blocks = pos.run_epoch(epoch, SLOTS_PER_EPOCH)
        proposers = [b.proposer for b in blocks]
        # Show a compact summary of who proposed in this epoch
        print(f"  Epoch {epoch}: ", end="")
        # Show first letter of each proposer for a quick visual
        initials = [p[0] for p in proposers]
        print(" ".join(initials))

    print(f"\n  Legend: A=Alice  B=Bob  C=Charlie  D=Diana  E=Eve")

    # ---- Show selection distribution ----------------------------------------
    print(f"\n{'=' * 65}")
    print("  Selection Distribution (actual vs expected)")
    print(f"{'=' * 65}\n")

    total_blocks = NUM_EPOCHS * SLOTS_PER_EPOCH
    print(f"  {'Validator':<12} {'Proposed':>10} {'Actual %':>10} {'Expected %':>12} {'Delta':>8}")
    print(f"  {'─' * 12} {'─' * 10} {'─' * 10} {'─' * 12} {'─' * 8}")

    for v in validators:
        actual_pct = v.blocks_proposed / total_blocks * 100
        expected_pct = v.stake / total_stake * 100
        delta = actual_pct - expected_pct
        # Show a bar proportional to actual selections
        print(f"  {v.address:<12} {v.blocks_proposed:>10} {actual_pct:>9.1f}% {expected_pct:>11.1f}% {delta:>+7.1f}%")

    print(f"\n  Total blocks: {total_blocks}")
    print(f"  (With more slots the distribution converges to expected weights)")

    # ---- Demonstrate slashing for double-signing ----------------------------
    print(f"\n{'=' * 65}")
    print("  SLASHING DEMONSTRATION — Double-Signing Attack")
    print(f"{'=' * 65}\n")

    # Find a slot Bob actually proposed during the simulation
    bob = pos.validators["Bob"]
    target_slot = next(iter(bob.proposals))  # Pick Bob's first proposed slot

    print(f"  Bob already proposed block for slot {target_slot}:")
    original_hash = bob.proposals[target_slot]
    print(f"    Block hash: {original_hash[:32]}...")

    # Create a conflicting block (different data → different hash)
    conflicting_block = Block(
        slot=target_slot, epoch=target_slot // SLOTS_PER_EPOCH,
        proposer="Bob", data="FRAUDULENT: double-spend attempt"
    )
    print(f"\n  Bob creates a SECOND block for the same slot:")
    print(f"    Block hash: {conflicting_block.hash[:32]}...")

    # Detect the double-sign
    is_double = pos.detect_double_sign("Bob", target_slot, conflicting_block.hash)

    if is_double:
        print(f"\n  ✗ DOUBLE-SIGNING DETECTED!")
        print(f"    Two different blocks for slot {target_slot} by Bob")
        print()

        # Slash Bob
        event = pos.slash_validator("Bob", f"double-sign slot {target_slot}")

        print(f"  ┌─────────────────────────────────────┐")
        print(f"  │         SLASHING EVENT               │")
        print(f"  ├─────────────────────────────────────┤")
        print(f"  │ Validator:  {event['validator']:<24}│")
        print(f"  │ Reason:     {event['reason']:<24}│")
        print(f"  │ Old stake:  {event['old_stake']:<24}│")
        print(f"  │ Penalty:    {event['penalty']:<24}│")
        print(f"  │ Remaining:  {event['remaining_stake']:<24}│")
        print(f"  └─────────────────────────────────────┘")
    else:
        print("  No double-signing detected.")

    # ---- Show updated validator set after slashing --------------------------
    print(f"\n--- Validator Set After Slashing ---\n")
    print(f"  {'Validator':<12} {'Stake':>8} {'Status':>10}")
    print(f"  {'─' * 12} {'─' * 8} {'─' * 10}")
    for addr in ["Alice", "Bob", "Charlie", "Diana", "Eve"]:
        v = pos.validators[addr]
        status = "SLASHED" if v.slashed else "active"
        print(f"  {v.address:<12} {v.stake:>8} {status:>10}")

    # ---- Run one more epoch without Bob -------------------------------------
    print(f"\n--- Post-Slashing Epoch (Bob excluded) ---\n")

    # Reset counters for this mini-epoch
    for v in pos.validators.values():
        v.blocks_proposed = 0

    blocks = pos.run_epoch(NUM_EPOCHS, SLOTS_PER_EPOCH)
    proposers = [b.proposer for b in blocks]
    print(f"  Epoch {NUM_EPOCHS}: ", end="")
    print(" ".join(p[0] for p in proposers))
    print()

    # Verify Bob got zero blocks
    bob_blocks = pos.validators["Bob"].blocks_proposed
    print(f"  Bob proposed {bob_blocks} blocks (expected 0 — slashed validators can't propose)")

    remaining_active = [v for v in pos.validators.values() if v.active and not v.slashed]
    print(f"  Active validators: {', '.join(v.address for v in remaining_active)}")

    print(f"\n{'=' * 65}")
    print("  ✓ Proof-of-Stake demo complete")
    print(f"{'=' * 65}")


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
