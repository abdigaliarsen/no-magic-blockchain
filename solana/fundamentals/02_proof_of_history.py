"""
TITLE: Proof of History (PoH)
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    Solana's Proof of History — a verifiable delay function built from sequential
    SHA-256 hashing. Each hash depends on the previous one, creating a
    cryptographic clock that proves the passage of time without relying on
    timestamps or consensus.

KEY CONCEPTS:
    - Sequential SHA-256 chain: hash_n = SHA256(hash_{n-1})
    - Ticks: periodic checkpoints in the hash sequence
    - Event insertion: mixing external data (e.g., transaction hashes) into the chain
    - Verification: re-computing the sequence to prove ordering and elapsed time

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 fundamentals)
    - solana/01_accounts_model.py (Solana account model basics)

REAL-WORLD RELEVANCE:
    Proof of History is Solana's key innovation for achieving high throughput.
    By providing a global clock, validators don't need to negotiate timestamps
    via consensus, enabling parallel transaction processing and 400ms block times.
"""

import hashlib
import time

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Number of hashes between ticks — in real Solana this is tuned so that
# ticks occur regularly (64 ticks per slot)
HASHES_PER_TICK = 50

# Number of ticks per slot — real Solana uses 64 ticks per slot
TICKS_PER_SLOT = 20

# Initial hash — the "genesis" starting point for the PoH chain
GENESIS_HASH = hashlib.sha256(b"solana-genesis-poh-seed").hexdigest()


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: PoH entry — a single record in the hash chain
# ----------------------------------------------------------------------------

class PoHEntry:
    """One entry in the Proof of History sequence.

    Each entry records:
    - The hash at this point in the sequence
    - How many hashes were computed since the last entry
    - Optional event data (transaction hash mixed in)
    """

    def __init__(self, hash_value, num_hashes, event_data=None):
        self.hash = hash_value       # The SHA-256 hash at this point
        self.num_hashes = num_hashes  # Hashes since previous entry
        self.event_data = event_data  # External data mixed in (or None for ticks)

    @property
    def is_tick(self):
        """Ticks are entries with no event data — just periodic checkpoints."""
        return self.event_data is None

    def __repr__(self):
        kind = "TICK" if self.is_tick else "EVENT"
        return f"PoHEntry({kind}, hashes={self.num_hashes}, hash={self.hash[:16]}...)"


# ----------------------------------------------------------------------------
# 2b: PoH generator — produces the sequential hash chain
# ----------------------------------------------------------------------------

class ProofOfHistory:
    """Generates a Proof of History chain via sequential SHA-256 hashing.

    The core insight: SHA-256 cannot be parallelized — each hash requires
    the previous hash as input. This creates a verifiable "clock" that
    proves real time has passed between events.
    """

    def __init__(self, initial_hash=GENESIS_HASH):
        self.current_hash = initial_hash   # Rolling hash state
        self.entries = []                   # Recorded entries (ticks + events)
        self.total_hashes = 0              # Total hashes computed
        self.hash_count_since_entry = 0    # Hashes since last recorded entry

    def _hash_once(self):
        """Compute one step of the sequential hash chain.

        This is the fundamental PoH operation: hash_{n+1} = SHA256(hash_n).
        Because SHA-256 is sequential, you MUST compute each intermediate
        hash — there's no shortcut to jump ahead.
        """
        self.current_hash = hashlib.sha256(
            self.current_hash.encode("utf-8")
        ).hexdigest()
        self.total_hashes += 1
        self.hash_count_since_entry += 1

    def tick(self):
        """Record a tick — a periodic checkpoint in the hash sequence.

        Ticks happen at regular intervals (every HASHES_PER_TICK hashes).
        They prove that real time passed between entries without needing
        an external clock.
        """
        # Advance the hash chain by HASHES_PER_TICK steps
        for _ in range(HASHES_PER_TICK):
            self._hash_once()

        # Record the tick entry
        entry = PoHEntry(
            hash_value=self.current_hash,
            num_hashes=self.hash_count_since_entry,
        )
        self.entries.append(entry)
        self.hash_count_since_entry = 0  # Reset counter for next entry
        return entry

    def record_event(self, event_data):
        """Mix external event data into the PoH sequence.

        When a transaction arrives, its hash is mixed into the PoH chain.
        This proves the event occurred AFTER the previous entry and BEFORE
        the next one — establishing a total ordering of events.

        The mixing is: hash_{n+1} = SHA256(hash_n || event_data)
        """
        # Mix the event data into the current hash
        combined = self.current_hash + event_data
        self.current_hash = hashlib.sha256(
            combined.encode("utf-8")
        ).hexdigest()
        self.total_hashes += 1
        self.hash_count_since_entry += 1

        # Record the event entry
        entry = PoHEntry(
            hash_value=self.current_hash,
            num_hashes=self.hash_count_since_entry,
            event_data=event_data,
        )
        self.entries.append(entry)
        self.hash_count_since_entry = 0
        return entry

    def generate_slot(self, events=None):
        """Generate a full slot of PoH entries with optional events mixed in.

        A slot consists of TICKS_PER_SLOT ticks. Events are inserted at
        specified tick positions, simulating transactions arriving during
        the slot.

        Args:
            events: List of (tick_index, event_data) tuples — which tick
                    to insert each event before
        """
        if events is None:
            events = []

        # Build a lookup: tick_number → list of events to insert before it
        event_schedule = {}
        for tick_idx, data in events:
            event_schedule.setdefault(tick_idx, []).append(data)

        for tick_num in range(TICKS_PER_SLOT):
            # Insert any events scheduled before this tick
            for event_data in event_schedule.get(tick_num, []):
                self.record_event(event_data)

            # Record the tick
            self.tick()


# ----------------------------------------------------------------------------
# 2c: PoH verifier — re-computes the chain to validate it
# ----------------------------------------------------------------------------

class PoHVerifier:
    """Verifies a Proof of History sequence by re-computing every hash.

    Verification is the same cost as generation — you must recompute
    every intermediate hash. However, verification CAN be parallelized
    by splitting the chain into segments and verifying each independently.
    """

    @staticmethod
    def verify_sequence(entries, initial_hash=GENESIS_HASH):
        """Verify an entire PoH sequence starting from a known initial hash.

        Returns (is_valid, steps_verified, failure_index).
        """
        current_hash = initial_hash
        total_verified = 0

        for i, entry in enumerate(entries):
            if entry.event_data is not None:
                # This is an event entry — reproduce the event mixing
                # First, hash (num_hashes - 1) times sequentially
                for _ in range(entry.num_hashes - 1):
                    current_hash = hashlib.sha256(
                        current_hash.encode("utf-8")
                    ).hexdigest()
                    total_verified += 1

                # Then mix in the event data
                combined = current_hash + entry.event_data
                current_hash = hashlib.sha256(
                    combined.encode("utf-8")
                ).hexdigest()
                total_verified += 1
            else:
                # This is a tick — just sequential hashing
                for _ in range(entry.num_hashes):
                    current_hash = hashlib.sha256(
                        current_hash.encode("utf-8")
                    ).hexdigest()
                    total_verified += 1

            # Check that our recomputed hash matches the recorded hash
            if current_hash != entry.hash:
                return False, total_verified, i  # Mismatch at entry i

        return True, total_verified, -1  # All entries verified

    @staticmethod
    def verify_segment(entries, start_hash):
        """Verify a segment of the PoH chain (for parallel verification).

        In production Solana, the chain is split into segments and each
        segment is verified by a different CPU core. This is how verification
        can be parallelized even though generation cannot.
        """
        return PoHVerifier.verify_sequence(entries, initial_hash=start_hash)


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Proof of History."""

    print("=" * 70)
    print("  PROOF OF HISTORY — Solana's Cryptographic Clock")
    print("=" * 70)

    # --- Basic sequential hashing --------------------------------------------
    print("\n--- 1. Sequential Hash Chain ---\n")
    print("  Each hash depends on the previous one:")
    print("  hash_0 → SHA256(hash_0) = hash_1 → SHA256(hash_1) = hash_2 → ...\n")

    h = GENESIS_HASH
    print(f"  Genesis:  {h[:32]}...")
    for i in range(5):
        h = hashlib.sha256(h.encode("utf-8")).hexdigest()
        print(f"  Step {i+1}:   {h[:32]}...")
    print(f"\n  Key insight: you CANNOT compute hash_5 without computing")
    print(f"  hashes 1-4 first. This proves time has passed.")

    # --- Generate PoH with events --------------------------------------------
    print("\n--- 2. Generate PoH Slot with Events ---\n")

    poh = ProofOfHistory()

    # Create some fake transaction hashes to embed
    tx_events = [
        (3,  "tx:alice_sends_5_sol_to_bob"),     # Insert before tick 3
        (7,  "tx:bob_creates_token_account"),     # Insert before tick 7
        (12, "tx:carol_mints_1000_tokens"),       # Insert before tick 12
    ]

    print(f"  Configuration:")
    print(f"    Hashes per tick:  {HASHES_PER_TICK}")
    print(f"    Ticks per slot:   {TICKS_PER_SLOT}")
    print(f"    Events to embed:  {len(tx_events)}")
    print()

    # Measure generation time
    start_time = time.perf_counter()
    poh.generate_slot(events=tx_events)
    gen_time = time.perf_counter() - start_time

    print(f"  Generated slot: {len(poh.entries)} entries "
          f"({poh.total_hashes:,} total hashes)")
    print(f"  Generation time: {gen_time*1000:.1f}ms")

    # Display the entries
    print(f"\n  {'#':>3s}  {'Type':>5s}  {'Hashes':>7s}  {'Hash':>20s}  Event")
    print(f"  {'─'*3}  {'─'*5}  {'─'*7}  {'─'*20}  {'─'*30}")

    for i, entry in enumerate(poh.entries):
        kind = "TICK" if entry.is_tick else "EVENT"
        event_str = entry.event_data[:30] if entry.event_data else ""
        marker = "│" if entry.is_tick else "◆"
        print(f"  {i:>3d}  {kind:>5s}  {entry.num_hashes:>7d}  "
              f"{entry.hash[:20]}  {marker} {event_str}")

    # --- Verify the sequence -------------------------------------------------
    print("\n--- 3. Verify PoH Sequence ---\n")

    start_time = time.perf_counter()
    valid, steps, fail_idx = PoHVerifier.verify_sequence(poh.entries)
    verify_time = time.perf_counter() - start_time

    print(f"  Recomputed {steps:,} hashes to verify")
    print(f"  Verification time: {verify_time*1000:.1f}ms")
    print(f"  Result: {'✓ VALID' if valid else '✗ INVALID'}")

    # --- Tamper with the sequence and re-verify ------------------------------
    print("\n--- 4. Tamper Detection ---\n")

    # Save original hash
    tamper_idx = 5
    original_hash = poh.entries[tamper_idx].hash

    # Tamper: modify a hash in the middle of the sequence
    print(f"  Tampering with entry #{tamper_idx}...")
    print(f"  Original hash: {original_hash[:32]}...")
    poh.entries[tamper_idx].hash = hashlib.sha256(b"tampered").hexdigest()
    tampered_hash = poh.entries[tamper_idx].hash
    print(f"  Tampered hash: {tampered_hash[:32]}...")

    # Re-verify — should fail
    valid, steps, fail_idx = PoHVerifier.verify_sequence(poh.entries)
    print(f"\n  Verification after tampering:")
    print(f"  Result: {'✓ VALID' if valid else '✗ INVALID'}")
    if not valid:
        print(f"  Failed at entry #{fail_idx} after {steps:,} hash recomputations")

    # Restore for next demo
    poh.entries[tamper_idx].hash = original_hash

    # --- Event ordering proof ------------------------------------------------
    print("\n--- 5. Event Ordering Proof ---\n")

    print("  PoH proves the ORDER of events without consensus:")
    print()
    event_entries = [(i, e) for i, e in enumerate(poh.entries) if not e.is_tick]

    print("  Timeline:")
    print("  ─────────────────────────────────────────────────────────")

    prev_tick = 0
    for idx, entry in event_entries:
        # Count ticks before this event
        ticks_before = sum(
            1 for j in range(idx)
            if poh.entries[j].is_tick
        )
        total_hashes_before = sum(
            poh.entries[j].num_hashes for j in range(idx + 1)
        )
        print(f"  Hash #{total_hashes_before:>5,}  ◆ {entry.event_data}")
        print(f"  {'':>13s}   └─ after {ticks_before} ticks, "
              f"hash: {entry.hash[:20]}...")

    print("  ─────────────────────────────────────────────────────────")
    print()
    print("  Because each event is mixed into the hash chain, we can")
    print("  prove Event A happened before Event B without timestamps.")

    # --- Parallelizable verification -----------------------------------------
    print("\n--- 6. Parallel Verification ---\n")

    # Split entries into segments and verify each independently
    num_segments = 4
    entries = poh.entries
    segment_size = len(entries) // num_segments

    print(f"  Splitting {len(entries)} entries into {num_segments} segments")
    print(f"  (In production, each segment runs on a separate CPU core)\n")

    # Get the starting hash for each segment
    segment_results = []
    overall_start = time.perf_counter()

    for seg_idx in range(num_segments):
        start_idx = seg_idx * segment_size
        end_idx = start_idx + segment_size if seg_idx < num_segments - 1 else len(entries)
        segment = entries[start_idx:end_idx]

        # Starting hash is the genesis hash for segment 0,
        # or the last hash of the previous segment for others
        if seg_idx == 0:
            start_hash = GENESIS_HASH
        else:
            start_hash = entries[start_idx - 1].hash

        seg_start = time.perf_counter()
        valid, steps, fail = PoHVerifier.verify_segment(segment, start_hash)
        seg_time = time.perf_counter() - seg_start

        status = "✓" if valid else "✗"
        print(f"  Segment {seg_idx}: entries [{start_idx:>2d}..{end_idx-1:>2d}] "
              f"— {steps:>4d} hashes — {seg_time*1000:.1f}ms — {status}")
        segment_results.append(valid)

    overall_time = time.perf_counter() - overall_start
    all_valid = all(segment_results)
    print(f"\n  Overall result: {'✓ ALL VALID' if all_valid else '✗ INVALID'}")
    print(f"  Total time (sequential): {overall_time*1000:.1f}ms")
    print(f"  With {num_segments} cores, would be ~{overall_time*1000/num_segments:.1f}ms")

    # --- Summary -------------------------------------------------------------
    print("\n--- Summary ---\n")
    print("  Key properties of Proof of History:")
    print("  • Sequential: hash_n requires hash_{n-1} (cannot skip ahead)")
    print("  • Verifiable: anyone can recompute to validate")
    print("  • Parallelizable verification: split chain into segments")
    print("  • Event ordering: mix data in to prove sequence of events")
    print("  • No consensus needed for time: the hash chain IS the clock")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
