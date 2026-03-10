"""
TITLE: Beacon Chain (Proof of Stake)
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    A simplified Ethereum Beacon Chain with validator registration, slot/epoch
    structure, RANDAO-based proposer selection, attestations, and Casper FFG
    finality (justified → finalized after 2 epochs of supermajority votes).

KEY CONCEPTS:
    - Validator lifecycle: deposit 32 ETH → activation queue → active → exit
    - Slot/epoch timing: 32 slots per epoch, one proposer per slot
    - RANDAO: on-chain randomness accumulated from validator reveals
    - Casper FFG: checkpoint voting with 2/3 supermajority for finality

PREREQUISITE SCRIPTS:
    - core/07_consensus_pos.py (basic proof-of-stake concepts)
    - core/01_hashing.py (hashing fundamentals)

REAL-WORLD RELEVANCE:
    Ethereum switched from proof-of-work to proof-of-stake on Sep 15, 2022
    ("The Merge"). The Beacon Chain coordinates ~900,000+ validators, finalizing
    blocks every ~13 minutes (2 epochs). Finalized blocks are irreversible.
"""

import hashlib  # SHA-256 for hashing — stdlib only
import random   # For simulating network behavior (not for consensus randomness)
import time     # For timestamps in block headers

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Number of slots in one epoch (real Ethereum uses 32)
SLOTS_PER_EPOCH = 32

# Minimum stake to become a validator (in ETH, real value is 32 ETH)
MIN_DEPOSIT = 32

# Target committee size per slot (simplified; real Ethereum targets ~128)
TARGET_COMMITTEE_SIZE = 4

# Supermajority threshold for Casper FFG finality (2/3 of total stake)
SUPERMAJORITY_FRACTION = 2 / 3

# How many hex chars to show for truncated hashes
HASH_DISPLAY_LEN = 8

# Seed for reproducible demo results
RANDOM_SEED = 42

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 as hex string."""
    return hashlib.sha256(data).hexdigest()


def sha256_bytes(data: bytes) -> bytes:
    """Compute SHA-256 as raw bytes."""
    return hashlib.sha256(data).digest()


# --- Validator ------------------------------------------------------------

class Validator:
    """Represents a Beacon Chain validator.

    Each validator stakes exactly MIN_DEPOSIT ETH and participates in
    proposing blocks and attesting to checkpoints.
    """

    def __init__(self, index: int, pubkey: str, deposit: int):
        self.index = index          # Unique validator index
        self.pubkey = pubkey        # Public key (simplified as a hex string)
        self.deposit = deposit      # Amount staked (must be >= MIN_DEPOSIT)
        self.balance = deposit      # Effective balance (can change with rewards/penalties)
        self.active = False         # Whether this validator is in the active set
        self.slashed = False        # Whether this validator has been slashed
        self.activation_epoch = -1  # Epoch when this validator becomes active
        self.exit_epoch = -1        # Epoch when this validator exits (or -1)

    def __repr__(self):
        status = "ACTIVE" if self.active else "PENDING"
        if self.slashed:
            status = "SLASHED"
        return f"V{self.index}({status}, {self.balance}ETH)"


# --- Attestation -----------------------------------------------------------

class Attestation:
    """A validator's vote on the current head and checkpoint.

    In real Ethereum, attestations include:
    - source checkpoint (last justified)
    - target checkpoint (current epoch boundary)
    - head vote (specific block in the current slot)
    """

    def __init__(self, validator_index: int, slot: int,
                 source_epoch: int, target_epoch: int,
                 head_root: str):
        self.validator_index = validator_index
        self.slot = slot
        self.source_epoch = source_epoch    # The last justified checkpoint
        self.target_epoch = target_epoch    # The checkpoint being voted for
        self.head_root = head_root          # Hash of the block at head of chain


# --- Beacon Block ----------------------------------------------------------

class BeaconBlock:
    """A block in the Beacon Chain.

    Contains the proposer's identity, parent link, state root, RANDAO reveal,
    and a list of attestations from other validators.
    """

    def __init__(self, slot: int, proposer_index: int, parent_root: str,
                 randao_reveal: str):
        self.slot = slot
        self.proposer_index = proposer_index
        self.parent_root = parent_root
        self.state_root = ""               # Computed after processing
        self.randao_reveal = randao_reveal  # Proposer's RANDAO contribution
        self.attestations: list[Attestation] = []
        self.block_root = ""               # Hash of this block (computed later)

    def compute_root(self) -> str:
        """Compute a deterministic hash for this block."""
        data = f"{self.slot}:{self.proposer_index}:{self.parent_root}:{self.randao_reveal}"
        self.block_root = sha256_hex(data.encode("utf-8"))
        return self.block_root


# --- Checkpoint (for Casper FFG) -------------------------------------------

class Checkpoint:
    """A checkpoint is an epoch boundary block used for finality.

    Casper FFG operates on checkpoints, not individual blocks.
    A checkpoint becomes:
    - JUSTIFIED when 2/3+ of validators vote for it as target
    - FINALIZED when the next checkpoint is also justified
    """

    def __init__(self, epoch: int, block_root: str):
        self.epoch = epoch
        self.block_root = block_root
        self.justified = False     # Has received 2/3+ supermajority votes
        self.finalized = False     # Is permanently irreversible
        self.vote_count = 0        # Number of validators who voted for it
        self.total_weight = 0      # Sum of voting validators' balances


# --- Beacon Chain State Machine --------------------------------------------

class BeaconState:
    """The full state of the Beacon Chain.

    Tracks validators, RANDAO, checkpoints, and finality status.
    """

    def __init__(self):
        self.validators: list[Validator] = []
        self.slot = 0                      # Current slot number
        self.epoch = 0                     # Current epoch number
        self.randao_mix = b"\x00" * 32     # Accumulated randomness
        self.blocks: list[BeaconBlock] = []  # All produced blocks
        self.checkpoints: dict[int, Checkpoint] = {}  # epoch → Checkpoint
        self.justified_epoch = 0           # Most recent justified epoch
        self.finalized_epoch = 0           # Most recent finalized epoch
        self.genesis_root = sha256_hex(b"genesis")  # Root of the genesis block

    # --- Validator management ----------------------------------------------

    def register_validator(self, pubkey: str, deposit: int) -> Validator:
        """Register a new validator with the given deposit.

        The validator enters a pending state and activates at the next epoch.
        """
        if deposit < MIN_DEPOSIT:
            raise ValueError(f"Deposit {deposit} ETH < minimum {MIN_DEPOSIT} ETH")

        index = len(self.validators)
        validator = Validator(index, pubkey, deposit)
        # In real Ethereum, there's an activation queue with a churn limit.
        # We simplify: activate at the next epoch transition.
        validator.activation_epoch = self.epoch + 1
        self.validators.append(validator)
        return validator

    def get_active_validators(self, epoch: int) -> list[Validator]:
        """Return all validators active at the given epoch."""
        return [
            v for v in self.validators
            if v.active and not v.slashed
            and (v.exit_epoch == -1 or v.exit_epoch > epoch)
        ]

    def activate_pending_validators(self):
        """Activate validators whose activation epoch has arrived."""
        for v in self.validators:
            if not v.active and v.activation_epoch <= self.epoch:
                v.active = True

    # --- RANDAO (randomness) -----------------------------------------------

    def mix_randao(self, reveal: bytes):
        """Mix a validator's RANDAO reveal into the accumulated randomness.

        RANDAO works by XOR-ing each proposer's reveal with the existing mix.
        This is simple but effective: no single validator can predict the future
        mix without knowing all future reveals.
        """
        # XOR the reveal with the current mix (both are 32 bytes)
        new_mix = bytes(a ^ b for a, b in zip(self.randao_mix, reveal))
        self.randao_mix = new_mix

    # --- Proposer selection ------------------------------------------------

    def select_proposer(self, slot: int) -> int:
        """Select a block proposer for the given slot.

        Uses RANDAO mix + slot number to deterministically pick a validator.
        Real Ethereum uses a more sophisticated shuffling algorithm (swap-or-not).
        """
        active = self.get_active_validators(self.epoch)
        if not active:
            raise RuntimeError("No active validators")

        # Hash the RANDAO mix with the slot to get a pseudo-random seed
        seed = sha256_bytes(self.randao_mix + slot.to_bytes(8, "big"))
        # Use the seed to select a validator index
        idx = int.from_bytes(seed[:8], "big") % len(active)
        return active[idx].index

    # --- Committee selection -----------------------------------------------

    def select_committee(self, slot: int) -> list[int]:
        """Select a committee of validators to attest during this slot.

        In real Ethereum, each slot has one or more committees.
        We simplify: one committee per slot with TARGET_COMMITTEE_SIZE members.
        """
        active = self.get_active_validators(self.epoch)
        if not active:
            return []

        # Derive a seed specific to this slot's committee
        seed = sha256_bytes(self.randao_mix + b"committee" + slot.to_bytes(8, "big"))

        # Shuffle and take the first TARGET_COMMITTEE_SIZE validators
        # Use a simple deterministic shuffle based on the seed
        indices = [v.index for v in active]
        # Fisher-Yates shuffle using seed-derived values
        for i in range(len(indices) - 1, 0, -1):
            # Derive a deterministic random value for each swap
            h = sha256_bytes(seed + i.to_bytes(4, "big"))
            j = int.from_bytes(h[:4], "big") % (i + 1)
            indices[i], indices[j] = indices[j], indices[i]

        committee_size = min(TARGET_COMMITTEE_SIZE, len(indices))
        return indices[:committee_size]

    # --- Block processing --------------------------------------------------

    def process_slot(self, slot: int, verbose: bool = False) -> BeaconBlock | None:
        """Process a single slot: select proposer, create block, collect attestations.

        Returns the produced block, or None if the slot is skipped.
        """
        self.slot = slot
        self.epoch = slot // SLOTS_PER_EPOCH

        # Get the parent block root
        parent_root = self.blocks[-1].block_root if self.blocks else self.genesis_root

        # Select the proposer for this slot
        proposer_idx = self.select_proposer(slot)
        proposer = self.validators[proposer_idx]

        # Generate the proposer's RANDAO reveal (hash of their secret + slot)
        # In real Ethereum, this is a BLS signature of the epoch number
        reveal = sha256_bytes(f"{proposer.pubkey}:{slot}".encode("utf-8"))

        # Create the block
        block = BeaconBlock(
            slot=slot,
            proposer_index=proposer_idx,
            parent_root=parent_root,
            randao_reveal=reveal.hex(),
        )

        # Mix RANDAO
        self.mix_randao(reveal)

        # Select committee and collect attestations
        committee = self.select_committee(slot)
        current_epoch = slot // SLOTS_PER_EPOCH

        for v_idx in committee:
            if v_idx == proposer_idx:
                continue  # Proposer doesn't attest in their own slot (simplification)
            attestation = Attestation(
                validator_index=v_idx,
                slot=slot,
                source_epoch=self.justified_epoch,    # Vote for last justified
                target_epoch=current_epoch,            # Vote for current epoch checkpoint
                head_root=parent_root,
            )
            block.attestations.append(attestation)

        # Compute block root
        block.compute_root()
        self.blocks.append(block)

        if verbose:
            print(f"    Slot {slot:>3} │ Proposer: V{proposer_idx:<3} │ "
                  f"Attestations: {len(block.attestations):<2} │ "
                  f"Root: {block.block_root[:HASH_DISPLAY_LEN]}...")

        return block

    # --- Epoch transition --------------------------------------------------

    def process_epoch_transition(self, epoch: int, verbose: bool = False):
        """Process an epoch boundary: activate validators, evaluate finality.

        This is where Casper FFG operates:
        1. Count attestations for the current epoch's checkpoint
        2. If 2/3+ voted: JUSTIFY the checkpoint
        3. If the previous checkpoint was also justified: FINALIZE it
        """
        self.epoch = epoch
        self.activate_pending_validators()

        active = self.get_active_validators(epoch)
        total_balance = sum(v.balance for v in active)

        if not active:
            return

        # --- Count votes for this epoch's checkpoint ---
        # The checkpoint block is the first block of this epoch (or genesis)
        epoch_start_slot = epoch * SLOTS_PER_EPOCH
        checkpoint_root = self.genesis_root
        for b in self.blocks:
            if b.slot >= epoch_start_slot:
                checkpoint_root = b.block_root
                break

        checkpoint = Checkpoint(epoch, checkpoint_root)

        # Tally attestations from this epoch's blocks
        vote_weight = 0
        voters = set()
        for block in self.blocks:
            block_epoch = block.slot // SLOTS_PER_EPOCH
            if block_epoch == epoch:
                for att in block.attestations:
                    if att.target_epoch == epoch and att.validator_index not in voters:
                        voters.add(att.validator_index)
                        vote_weight += self.validators[att.validator_index].balance

        checkpoint.vote_count = len(voters)
        checkpoint.total_weight = vote_weight

        # --- Check for justification (2/3 supermajority) ---
        if total_balance > 0 and vote_weight / total_balance >= SUPERMAJORITY_FRACTION:
            checkpoint.justified = True
            self.justified_epoch = epoch

            if verbose:
                pct = vote_weight / total_balance * 100
                print(f"  ✓ Epoch {epoch} JUSTIFIED ({checkpoint.vote_count} votes, "
                      f"{pct:.0f}% stake)")

            # --- Check for finalization ---
            # If the previous epoch was also justified, it becomes finalized
            prev_epoch = epoch - 1
            if prev_epoch in self.checkpoints and self.checkpoints[prev_epoch].justified:
                self.checkpoints[prev_epoch].finalized = True
                self.finalized_epoch = prev_epoch
                if verbose:
                    print(f"  ★ Epoch {prev_epoch} FINALIZED (two consecutive justified)")
        else:
            if verbose:
                pct = vote_weight / total_balance * 100 if total_balance > 0 else 0
                print(f"  ✗ Epoch {epoch} not justified ({checkpoint.vote_count} votes, "
                      f"{pct:.0f}% stake, need {SUPERMAJORITY_FRACTION * 100:.0f}%)")

        self.checkpoints[epoch] = checkpoint

    # --- Slashing -----------------------------------------------------------

    def slash_validator(self, index: int, verbose: bool = False):
        """Slash a validator for misbehavior (e.g., double-voting).

        The validator loses a portion of their stake and is forcibly exited.
        """
        v = self.validators[index]
        if v.slashed:
            return  # Already slashed

        penalty = v.balance // 32  # Lose ~3.125% of balance (initial penalty per Ethereum spec)
        v.balance -= penalty
        v.slashed = True
        v.exit_epoch = self.epoch + 1  # Force exit at next epoch

        if verbose:
            print(f"  ⚡ Validator V{index} SLASHED: -{penalty} ETH "
                  f"(balance: {v.balance} ETH)")


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of the Beacon Chain."""

    # Use a fixed seed for reproducible output
    random.seed(RANDOM_SEED)

    print("=" * 70)
    print("  BEACON CHAIN — Ethereum's Proof of Stake Consensus")
    print("=" * 70)

    # --- Part 1: Validator registration ------------------------------------
    print("\n--- Part 1: Validator Registration ---\n")

    state = BeaconState()

    # Register 10 validators, each depositing 32 ETH
    validator_names = [
        "Alice", "Bob", "Charlie", "Diana", "Eve",
        "Frank", "Grace", "Heidi", "Ivan", "Judy",
    ]

    print("  Registering 10 validators (32 ETH deposit each):\n")
    print(f"  {'Index':<7} {'Name':<10} {'Pubkey':<18} {'Deposit':<10} {'Status'}")
    print(f"  {'─' * 7} {'─' * 10} {'─' * 18} {'─' * 10} {'─' * 10}")

    for i, name in enumerate(validator_names):
        pubkey = sha256_hex(name.encode("utf-8"))[:16]
        v = state.register_validator(pubkey, deposit=32)
        print(f"  V{v.index:<5} {name:<10} {pubkey}.. {v.deposit:<10} PENDING")

    # Activate validators (simulate epoch 1 transition)
    state.epoch = 1
    state.activate_pending_validators()
    active = state.get_active_validators(1)
    print(f"\n  Activated {len(active)} validators at epoch 1")

    # --- Part 2: Slot/Epoch structure --------------------------------------
    print("\n--- Part 2: Slot/Epoch Structure ---\n")
    print(f"  Slots per epoch: {SLOTS_PER_EPOCH}")
    print(f"  Real Ethereum: 1 slot = 12 seconds, 1 epoch = 6.4 minutes")
    print(f"  For demo: simulating 3 epochs ({3 * SLOTS_PER_EPOCH} slots total)")

    print()
    print("  Epoch structure:")
    print("  ┌────────────────────────────────────────────────────────┐")
    print("  │ Epoch 1: [Slot 32, Slot 33, ... Slot 63]              │")
    print("  │ Epoch 2: [Slot 64, Slot 65, ... Slot 95]              │")
    print("  │ Epoch 3: [Slot 96, Slot 97, ... Slot 127]             │")
    print("  └────────────────────────────────────────────────────────┘")

    # --- Part 3: Simulating block production -------------------------------
    print("\n--- Part 3: Block Production (3 Epochs) ---\n")

    # We'll simulate 3 epochs, showing a subset of slots for readability
    num_epochs = 3
    start_epoch = 1

    for epoch_num in range(start_epoch, start_epoch + num_epochs):
        epoch_start = epoch_num * SLOTS_PER_EPOCH
        epoch_end = epoch_start + SLOTS_PER_EPOCH

        print(f"  ┌── Epoch {epoch_num} (slots {epoch_start}-{epoch_end - 1}) "
              f"{'─' * 30}┐")

        # Process each slot in the epoch (show first 4 and last 1)
        for slot in range(epoch_start, epoch_end):
            # For readability, only print details for a few slots per epoch
            show_detail = (slot < epoch_start + 4 or slot == epoch_end - 1)
            block = state.process_slot(slot, verbose=show_detail)

            if slot == epoch_start + 4 and epoch_end - 1 > epoch_start + 4:
                remaining = epoch_end - 1 - (epoch_start + 4)
                print(f"    ... ({remaining} more slots processed silently) ...")

        # Process epoch transition (finality check)
        print(f"  └── Epoch {epoch_num} boundary {'─' * 37}┘")
        state.process_epoch_transition(epoch_num, verbose=True)
        print()

    # --- Part 4: Proposer distribution -------------------------------------
    print("--- Part 4: Proposer Selection Distribution ---\n")

    # Count how many times each validator was selected as proposer
    proposer_counts: dict[int, int] = {}
    for block in state.blocks:
        proposer_counts[block.proposer_index] = proposer_counts.get(
            block.proposer_index, 0
        ) + 1

    print(f"  {'Validator':<12} {'Proposals':<12} {'Bar'}")
    print(f"  {'─' * 12} {'─' * 12} {'─' * 30}")
    for i in range(len(state.validators)):
        count = proposer_counts.get(i, 0)
        bar = "█" * count
        name = validator_names[i]
        print(f"  V{i} ({name[:6]:<6}) {count:<12} {bar}")

    print(f"\n  Total blocks produced: {len(state.blocks)}")
    print("  (Selection is deterministic based on RANDAO + slot number)")

    # --- Part 5: Attestation summary ---------------------------------------
    print("\n--- Part 5: Attestation Summary ---\n")

    total_attestations = sum(len(b.attestations) for b in state.blocks)
    print(f"  Total attestations collected: {total_attestations}")
    print(f"  Average attestations per block: "
          f"{total_attestations / len(state.blocks):.1f}")

    # --- Part 6: Casper FFG finality ---------------------------------------
    print("\n--- Part 6: Casper FFG Finality Status ---\n")

    print(f"  {'Epoch':<8} {'Justified':<12} {'Finalized':<12} {'Votes':<8} {'Weight'}")
    print(f"  {'─' * 8} {'─' * 12} {'─' * 12} {'─' * 8} {'─' * 10}")

    for epoch_num in sorted(state.checkpoints.keys()):
        cp = state.checkpoints[epoch_num]
        j_mark = "✓ YES" if cp.justified else "✗ no"
        f_mark = "★ YES" if cp.finalized else "  no"
        print(f"  {epoch_num:<8} {j_mark:<12} {f_mark:<12} "
              f"{cp.vote_count:<8} {cp.total_weight} ETH")

    print(f"\n  Latest justified epoch: {state.justified_epoch}")
    print(f"  Latest finalized epoch: {state.finalized_epoch}")

    if state.finalized_epoch > 0:
        print(f"\n  Finalization means epoch {state.finalized_epoch}'s checkpoint is")
        print(f"  IRREVERSIBLE — no honest reorganization can undo it.")

    # --- Part 7: Slashing demonstration ------------------------------------
    print("\n--- Part 7: Slashing a Misbehaving Validator ---\n")

    print("  Scenario: Validator V7 (Heidi) double-votes on two conflicting blocks")
    print()

    v7_before = state.validators[7].balance
    state.slash_validator(7, verbose=True)
    v7_after = state.validators[7].balance

    print(f"\n  Before: V7 balance = {v7_before} ETH")
    print(f"  After:  V7 balance = {v7_after} ETH")
    print(f"  Status: {state.validators[7]}")
    print(f"  Exit epoch: {state.validators[7].exit_epoch}")
    print()
    print("  Slashing serves two purposes:")
    print("  1. Punish the misbehaving validator financially")
    print("  2. Remove them from the active set to protect the network")

    print("\n" + "=" * 70)
    print("  KEY TAKEAWAY: The Beacon Chain coordinates validators through")
    print("  slots, epochs, and committees. Casper FFG achieves finality when")
    print("  two consecutive checkpoints receive 2/3+ supermajority votes.")
    print("  Finalized blocks are cryptoeconomically irreversible — reverting")
    print("  them would require slashing 1/3 of all staked ETH.")
    print("=" * 70)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
