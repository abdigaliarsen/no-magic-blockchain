"""
TITLE: Timelocks & HTLCs (Hash Time-Locked Contracts)
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    Bitcoin timelock mechanisms (CLTV and CSV opcodes) and Hash Time-Locked
    Contracts (HTLCs). Demonstrates how these primitives combine to enable
    trustless cross-chain atomic swaps between two blockchains.

KEY CONCEPTS:
    - CLTV (CheckLockTimeVerify): absolute timelock — funds locked until block height/time
    - CSV (CheckSequenceVerify): relative timelock — locked for N blocks after confirmation
    - HTLC: payment locked by both a hash preimage AND a timeout
    - Atomic swaps: trustless cross-chain exchange using paired HTLCs

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - bitcoin/fundamentals/02_bitcoin_script.py (Script opcodes)
    - bitcoin/fundamentals/08_simplified_lightning.py (payment channels)

REAL-WORLD RELEVANCE:
    CLTV (BIP 65) and CSV (BIP 112) are essential for Lightning Network payment
    channels and atomic swaps. HTLCs enable trustless multi-hop payments across
    Lightning and cross-chain exchanges without centralized intermediaries.
"""

import hashlib  # For SHA-256 and RIPEMD-160 hashing
import os       # For random preimage generation
import time     # For timestamp simulation

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Timelock types
LOCKTIME_BLOCK_HEIGHT = "block_height"  # Lock until a specific block number
LOCKTIME_TIMESTAMP = "timestamp"        # Lock until a specific Unix timestamp
LOCKTIME_THRESHOLD = 500_000_000        # Below = block height, above = timestamp

# Simulated blockchain state
CURRENT_BLOCK_HEIGHT = 800_000          # Current Bitcoin block height (approx)
CURRENT_TIMESTAMP = int(time.time())    # Current Unix timestamp
BLOCKS_PER_HOUR = 6                     # ~10 minute block interval

# HTLC timeout windows (in blocks)
HTLC_TIMEOUT_ALICE = 144               # Alice's HTLC: 24 hours (on chain A)
HTLC_TIMEOUT_BOB = 72                  # Bob's HTLC: 12 hours (on chain B) — shorter!

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Simplified Script VM (for timelock opcodes) ---

class ScriptVM:
    """
    Minimal Script virtual machine supporting timelock opcodes.
    Stack-based: operations push/pop values from a LIFO stack.
    """
    def __init__(self):
        self.stack = []
        self.log = []      # Execution trace for demo output
        self.failed = False # Set to True when a verify-type opcode fails

    def _log(self, op, detail=""):
        """Record an operation for the execution trace."""
        stack_view = [self._fmt(v) for v in self.stack]
        self.log.append((op, detail, stack_view[:]))

    def _fmt(self, value):
        """Format a stack value for display."""
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, bytes):
            return value.hex()[:16] + "..."
        return str(value)

    def push(self, value):
        """Push a value onto the stack."""
        self.stack.append(value)
        self._log("PUSH", self._fmt(value))

    def execute(self, script, context):
        """
        Execute a script with a spending context.
        context = {
            'block_height': current block height,
            'block_time': current block timestamp,
            'sequence': input's sequence number (for CSV),
            'tx_locktime': transaction's nLockTime (for CLTV),
            'preimage': hash preimage (for HTLC),
        }
        """
        self.stack = []
        self.log = []
        self.failed = False

        for op in script:
            if self.failed:
                break  # Stop executing after a failure
            if op == "OP_CHECKLOCKTIMEVERIFY":
                self._op_cltv(context)
            elif op == "OP_CHECKSEQUENCEVERIFY":
                self._op_csv(context)
            elif op == "OP_HASH256":
                self._op_hash256()
            elif op == "OP_EQUAL":
                self._op_equal()
            elif op == "OP_EQUALVERIFY":
                self._op_equalverify()
            elif op == "OP_IF":
                self._log("OP_IF", "")
            elif op == "OP_ELSE":
                self._log("OP_ELSE", "")
            elif op == "OP_ENDIF":
                self._log("OP_ENDIF", "")
            elif op == "OP_DROP":
                self._op_drop()
            elif op == "OP_DUP":
                self._op_dup()
            elif op == "OP_CHECKSIG":
                self._op_checksig(context)
            elif op == "OP_TRUE":
                self.push(True)
            elif op == "OP_VERIFY":
                self._op_verify()
            elif isinstance(op, (int, bytes)):
                self.push(op)
            else:
                self._log(f"UNKNOWN: {op}", "SKIP")

        # Script succeeds if no failure flag and top of stack is truthy
        if self.failed:
            return False
        result = len(self.stack) > 0 and bool(self.stack[-1])
        return result

    def _op_cltv(self, ctx):
        """
        OP_CHECKLOCKTIMEVERIFY: verify that the transaction's nLockTime
        is >= the value on top of stack. This is an ABSOLUTE timelock.
        The locktime value stays on the stack (like OP_NOP behavior).
        """
        if not self.stack:
            self._log("OP_CLTV", "FAIL: empty stack")
            self.stack.append(False)
            return
        locktime = self.stack[-1]  # Peek, don't pop (BIP 65 behavior)
        tx_locktime = ctx.get("tx_locktime", 0)

        if tx_locktime >= locktime:
            self._log("OP_CLTV", f"PASS: tx_locktime {tx_locktime} >= {locktime}")
        else:
            self._log("OP_CLTV", f"FAIL: tx_locktime {tx_locktime} < {locktime}")
            # In real Bitcoin, script fails immediately
            self.failed = True

    def _op_csv(self, ctx):
        """
        OP_CHECKSEQUENCEVERIFY: verify that the input's sequence number
        encodes a relative timelock that has been satisfied. This is a
        RELATIVE timelock (N blocks/time since the UTXO was confirmed).
        """
        if not self.stack:
            self._log("OP_CSV", "FAIL: empty stack")
            self.stack.append(False)
            return
        required_seq = self.stack[-1]  # Peek
        actual_seq = ctx.get("sequence", 0)

        if actual_seq >= required_seq:
            self._log("OP_CSV", f"PASS: sequence {actual_seq} >= {required_seq}")
        else:
            self._log("OP_CSV", f"FAIL: sequence {actual_seq} < {required_seq}")
            self.failed = True

    def _op_hash256(self):
        """Double-SHA256 of top stack element."""
        if not self.stack:
            return
        value = self.stack.pop()
        if isinstance(value, int):
            value = value.to_bytes(32, "big")
        h = hashlib.sha256(hashlib.sha256(value).digest()).digest()
        self.stack.append(h)
        self._log("OP_HASH256", f"hash = {h.hex()[:16]}...")

    def _op_equal(self):
        """Check if top two stack elements are equal."""
        if len(self.stack) < 2:
            self.stack.append(False)
            return
        a = self.stack.pop()
        b = self.stack.pop()
        result = a == b
        self.stack.append(result)
        self._log("OP_EQUAL", "TRUE" if result else "FALSE")

    def _op_equalverify(self):
        """OP_EQUAL + OP_VERIFY: equal check that fails the script if false."""
        self._op_equal()
        if not self.stack or not self.stack[-1]:
            self._log("OP_EQUALVERIFY", "FAIL")
            self.stack.clear()
            self.stack.append(False)
        else:
            self.stack.pop()  # Remove the True, continue
            self._log("OP_EQUALVERIFY", "PASS")

    def _op_drop(self):
        """Remove top stack element."""
        if self.stack:
            self.stack.pop()
            self._log("OP_DROP", "")

    def _op_dup(self):
        """Duplicate top stack element."""
        if self.stack:
            self.stack.append(self.stack[-1])
            self._log("OP_DUP", "")

    def _op_checksig(self, ctx):
        """Simplified signature check (always passes in our simulation)."""
        if len(self.stack) >= 2:
            self.stack.pop()  # pubkey
            self.stack.pop()  # signature
            self.stack.append(True)
            self._log("OP_CHECKSIG", "PASS (simulated)")
        else:
            self.stack.append(False)
            self._log("OP_CHECKSIG", "FAIL: missing args")

    def _op_verify(self):
        """Fail script if top is not true."""
        if not self.stack or not self.stack[-1]:
            self._log("OP_VERIFY", "FAIL")
            self.stack.clear()
            self.stack.append(False)
        else:
            self.stack.pop()
            self._log("OP_VERIFY", "PASS")


# --- HTLC Contract ---

class HTLC:
    """
    Hash Time-Locked Contract.

    Funds can be claimed in two ways:
    1. HASH PATH: provide the preimage of a hash (before timeout)
    2. TIMEOUT PATH: wait until the timelock expires, then reclaim

    This is the core building block of Lightning Network and atomic swaps.
    """
    def __init__(self, sender, receiver, amount, hash_lock, timeout_blocks, chain="Bitcoin"):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.hash_lock = hash_lock          # SHA-256 hash that must be revealed
        self.timeout_blocks = timeout_blocks # Blocks until sender can reclaim
        self.chain = chain
        self.claimed = False
        self.claim_type = None              # "preimage" or "timeout"
        self.creation_height = CURRENT_BLOCK_HEIGHT

    def timeout_height(self):
        """Block height when the timeout path becomes available."""
        return self.creation_height + self.timeout_blocks

    def can_claim_with_preimage(self, preimage, current_height):
        """
        Check if receiver can claim with the hash preimage.
        Must be before the timeout and preimage must hash correctly.
        """
        if current_height >= self.timeout_height():
            return False, "Timeout expired — sender can reclaim"
        h = hashlib.sha256(preimage).digest()
        if h != self.hash_lock:
            return False, "Invalid preimage — hash mismatch"
        return True, "Valid preimage"

    def can_claim_timeout(self, current_height):
        """Check if sender can reclaim via timeout."""
        if current_height < self.timeout_height():
            blocks_left = self.timeout_height() - current_height
            return False, f"{blocks_left} blocks until timeout"
        return True, "Timeout reached — sender can reclaim"

    def claim(self, preimage=None, current_height=None):
        """Attempt to claim the HTLC."""
        if self.claimed:
            return False, "Already claimed"

        if current_height is None:
            current_height = CURRENT_BLOCK_HEIGHT

        if preimage is not None:
            ok, msg = self.can_claim_with_preimage(preimage, current_height)
            if ok:
                self.claimed = True
                self.claim_type = "preimage"
                return True, f"Claimed by {self.receiver} with preimage"
            return False, msg
        else:
            ok, msg = self.can_claim_timeout(current_height)
            if ok:
                self.claimed = True
                self.claim_type = "timeout"
                return True, f"Reclaimed by {self.sender} via timeout"
            return False, msg


# --- Atomic Swap ---

class AtomicSwap:
    """
    Cross-chain atomic swap using paired HTLCs.

    Protocol:
    1. Alice generates secret preimage, computes hash
    2. Alice locks BTC in HTLC on Bitcoin (longer timeout)
    3. Bob sees the hash, locks LTC in HTLC on Litecoin (shorter timeout)
    4. Alice claims Bob's LTC by revealing the preimage
    5. Bob sees the preimage on-chain, claims Alice's BTC

    Key insight: Bob's timeout MUST be shorter than Alice's, otherwise
    Alice could claim Bob's LTC and then wait for her own HTLC to timeout.
    """
    def __init__(self, alice, bob, btc_amount, ltc_amount):
        self.alice = alice
        self.bob = bob
        self.btc_amount = btc_amount
        self.ltc_amount = ltc_amount

        # Step 1: Alice generates the secret
        self.preimage = os.urandom(32)
        self.hash_lock = hashlib.sha256(self.preimage).digest()

        # Step 2: Create HTLCs
        self.htlc_btc = HTLC(alice, bob, btc_amount, self.hash_lock,
                              HTLC_TIMEOUT_ALICE, chain="Bitcoin")
        self.htlc_ltc = HTLC(bob, alice, ltc_amount, self.hash_lock,
                              HTLC_TIMEOUT_BOB, chain="Litecoin")

        self.steps = []

    def record(self, step, detail):
        """Record a swap step for the demo."""
        self.steps.append((step, detail))

    def execute_happy_path(self):
        """Execute the swap where both parties cooperate."""
        self.record("SETUP", f"{self.alice} generates secret preimage")
        self.record("SETUP", f"Hash lock: {self.hash_lock.hex()[:24]}...")

        self.record("LOCK", f"{self.alice} locks {self.btc_amount} BTC on Bitcoin "
                    f"(timeout: {HTLC_TIMEOUT_ALICE} blocks)")
        self.record("LOCK", f"{self.bob} locks {self.ltc_amount} LTC on Litecoin "
                    f"(timeout: {HTLC_TIMEOUT_BOB} blocks)")

        # Alice claims LTC by revealing preimage
        ok, msg = self.htlc_ltc.claim(preimage=self.preimage)
        self.record("CLAIM", f"{self.alice} reveals preimage, claims {self.ltc_amount} LTC — {msg}")
        self.record("CLAIM", f"Preimage now visible on Litecoin chain!")

        # Bob sees preimage on-chain, claims BTC
        ok, msg = self.htlc_btc.claim(preimage=self.preimage)
        self.record("CLAIM", f"{self.bob} uses preimage, claims {self.btc_amount} BTC — {msg}")

        self.record("DONE", "Swap complete! Both parties received their coins.")

    def execute_abort_path(self):
        """Execute the swap where Bob never locks funds (Alice reclaims)."""
        self.record("SETUP", f"{self.alice} generates secret preimage")
        self.record("LOCK", f"{self.alice} locks {self.btc_amount} BTC on Bitcoin")
        self.record("ABORT", f"{self.bob} goes offline / refuses to lock LTC")

        # Time passes...
        future_height = CURRENT_BLOCK_HEIGHT + HTLC_TIMEOUT_ALICE + 1
        ok, msg = self.htlc_btc.claim(current_height=future_height)
        self.record("REFUND", f"After {HTLC_TIMEOUT_ALICE} blocks: {self.alice} reclaims BTC — {msg}")
        self.record("DONE", "No swap occurred. Alice's funds are safe.")


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Demonstrate timelocks and atomic swaps."""

    print("=" * 70)
    print("        TIMELOCKS & HTLCs")
    print("=" * 70)

    # --- Part 1: CLTV (Absolute Timelock) ---
    print("\n--- Part 1: CLTV (CheckLockTimeVerify) — Absolute Timelock ---\n")

    vm = ScriptVM()
    lock_height = CURRENT_BLOCK_HEIGHT + 100  # Lock until 100 blocks from now

    print(f"  Scenario: Funds locked until block #{lock_height:,}")
    print(f"  Current block: #{CURRENT_BLOCK_HEIGHT:,}")

    # Attempt 1: Too early
    print(f"\n  Attempt 1: Spend at block #{CURRENT_BLOCK_HEIGHT:,} (too early)")
    script = [lock_height, "OP_CHECKLOCKTIMEVERIFY", "OP_DROP", b"sig", b"pubkey", "OP_CHECKSIG"]
    ctx_early = {"tx_locktime": CURRENT_BLOCK_HEIGHT, "block_height": CURRENT_BLOCK_HEIGHT}
    result = vm.execute(script, ctx_early)
    print(f"  Result: {'PASS' if result else 'FAIL (expected)'}")
    for op, detail, stack in vm.log:
        if detail:
            print(f"    {op:25s} {detail}")

    # Attempt 2: After lock expires
    print(f"\n  Attempt 2: Spend at block #{lock_height:,} (lock expired)")
    ctx_later = {"tx_locktime": lock_height, "block_height": lock_height}
    result = vm.execute(script, ctx_later)
    print(f"  Result: {'PASS' if result else 'FAIL'}")
    for op, detail, stack in vm.log:
        if detail:
            print(f"    {op:25s} {detail}")

    # --- Part 2: CSV (Relative Timelock) ---
    print(f"\n--- Part 2: CSV (CheckSequenceVerify) — Relative Timelock ---\n")

    relative_lock = 6  # Lock for 6 blocks after UTXO confirmation

    print(f"  Scenario: Funds locked for {relative_lock} blocks after confirmation")

    # Attempt 1: Too early (only 2 blocks since confirmation)
    print(f"\n  Attempt 1: Spend 2 blocks after confirmation")
    csv_script = [relative_lock, "OP_CHECKSEQUENCEVERIFY", "OP_DROP",
                  b"sig", b"pubkey", "OP_CHECKSIG"]
    ctx_early = {"sequence": 2}  # Only 2 blocks have passed
    result = vm.execute(csv_script, ctx_early)
    print(f"  Result: {'PASS' if result else 'FAIL (expected)'}")
    for op, detail, stack in vm.log:
        if detail:
            print(f"    {op:25s} {detail}")

    # Attempt 2: After relative lock
    print(f"\n  Attempt 2: Spend 10 blocks after confirmation")
    ctx_later = {"sequence": 10}  # 10 blocks have passed
    result = vm.execute(csv_script, ctx_later)
    print(f"  Result: {'PASS' if result else 'FAIL'}")
    for op, detail, stack in vm.log:
        if detail:
            print(f"    {op:25s} {detail}")

    # --- Comparison ---
    print(f"\n  ┌──────────────────────────────────────────────────┐")
    print(f"  │         CLTV vs CSV Comparison                   │")
    print(f"  ├────────────┬──────────────────┬──────────────────┤")
    print(f"  │            │ CLTV (BIP 65)    │ CSV (BIP 112)    │")
    print(f"  ├────────────┼──────────────────┼──────────────────┤")
    print(f"  │ Lock type  │ Absolute         │ Relative         │")
    print(f"  │ Reference  │ Block height     │ Blocks since     │")
    print(f"  │            │ or timestamp     │ confirmation     │")
    print(f"  │ Use case   │ \"After Jan 2025\" │ \"Wait 2 weeks\"   │")
    print(f"  │ Field      │ nLockTime        │ nSequence        │")
    print(f"  └────────────┴──────────────────┴──────────────────┘")

    # --- Part 3: HTLC ---
    print(f"\n--- Part 3: Hash Time-Locked Contract (HTLC) ---\n")

    preimage = os.urandom(32)
    hash_lock = hashlib.sha256(preimage).digest()

    htlc = HTLC("Alice", "Bob", 1.0, hash_lock, timeout_blocks=144)

    print(f"  HTLC created:")
    print(f"  ┌─────────────────────────────────────────────┐")
    print(f"  │ Sender:    {htlc.sender:33s} │")
    print(f"  │ Receiver:  {htlc.receiver:33s} │")
    print(f"  │ Amount:    {htlc.amount} BTC{' ' * 27} │")
    print(f"  │ Hash lock: {hash_lock.hex()[:24]}...       │")
    print(f"  │ Timeout:   block #{htlc.timeout_height():,}{' ' * 18} │")
    print(f"  └─────────────────────────────────────────────┘")

    print(f"\n  Spending conditions:")
    print(f"  ┌─────────────────────────────────────────────┐")
    print(f"  │ PATH A (hash path):                        │")
    print(f"  │   Bob provides preimage where              │")
    print(f"  │   SHA256(preimage) == hash_lock             │")
    print(f"  │   (must be before timeout)                  │")
    print(f"  ├─────────────────────────────────────────────┤")
    print(f"  │ PATH B (timeout path):                     │")
    print(f"  │   After block #{htlc.timeout_height():,}, Alice can    │")
    print(f"  │   reclaim the funds                         │")
    print(f"  └─────────────────────────────────────────────┘")

    # Claim with correct preimage
    ok, msg = htlc.claim(preimage=preimage)
    print(f"\n  Bob claims with preimage: {msg}")

    # --- Part 4: Atomic Swap ---
    print(f"\n--- Part 4: Cross-Chain Atomic Swap ---\n")

    print(f"  Alice has BTC, wants LTC")
    print(f"  Bob has LTC, wants BTC")
    print(f"  They don't trust each other.\n")

    swap = AtomicSwap("Alice", "Bob", btc_amount=1.0, ltc_amount=50.0)
    swap.execute_happy_path()

    print(f"  Swap timeline:")
    print(f"  ┌{'─' * 60}┐")
    for i, (step, detail) in enumerate(swap.steps):
        marker = {"SETUP": " ", "LOCK": " ", "CLAIM": " ", "DONE": " ", "ABORT": "!", "REFUND": " "}
        icon = marker.get(step, " ")
        print(f"  │{icon} [{step:6s}] {detail:<50s}│")
    print(f"  └{'─' * 60}┘")

    # --- Safety: why Bob's timeout must be shorter ---
    print(f"\n  Why Bob's timeout MUST be shorter than Alice's:")
    print(f"  ┌{'─' * 60}┐")
    print(f"  │ Alice's HTLC (Bitcoin):  {HTLC_TIMEOUT_ALICE:>3} blocks (~24 hours)        │")
    print(f"  │ Bob's HTLC (Litecoin):   {HTLC_TIMEOUT_BOB:>3} blocks (~12 hours)        │")
    print(f"  │                                                            │")
    print(f"  │ If Bob's timeout >= Alice's timeout:                       │")
    print(f"  │   Alice claims LTC (reveals preimage)                      │")
    print(f"  │   Alice ALSO waits for BTC timeout and reclaims            │")
    print(f"  │   => Alice gets BOTH coins! (Bob loses)                    │")
    print(f"  │                                                            │")
    print(f"  │ With shorter timeout for Bob:                              │")
    print(f"  │   Alice MUST claim LTC before Bob's timeout                │")
    print(f"  │   Once preimage is revealed, Bob can claim BTC             │")
    print(f"  │   Bob always has time because his deadline is later        │")
    print(f"  └{'─' * 60}┘")

    # --- Part 5: Abort path ---
    print(f"\n--- Part 5: Swap Abort (Safety Net) ---\n")

    swap2 = AtomicSwap("Alice", "Bob", btc_amount=1.0, ltc_amount=50.0)
    swap2.execute_abort_path()

    for step, detail in swap2.steps:
        print(f"  [{step:6s}] {detail}")

    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
