"""
TITLE: Covenants (OP_CTV / CheckTemplateVerify)
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    Bitcoin covenants using BIP 119's CheckTemplateVerify (CTV) opcode, which
    restricts HOW coins can be spent rather than just WHO can spend them.
    Implements a vault construct with 2-step withdrawal and cancel path.

KEY CONCEPTS:
    - OP_CTV: commits to a transaction template (outputs, locktime, etc.)
    - Template hash: SHA-256 of version, locktime, outputs hash, etc.
    - Vault: deposit → cold storage, withdrawal requires initiate + wait + complete
    - Cancel path: during the timelock delay, owner can claw back to vault

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - bitcoin/fundamentals/02_bitcoin_script.py (Script opcodes)
    - bitcoin/intermediate/12_timelocks_htlcs.py (timelocks)

REAL-WORLD RELEVANCE:
    CTV (BIP 119) enables non-interactive payment pools, vaults, and congestion
    control. Vaults are the most practical covenant use case — they add a time
    delay to withdrawals so stolen keys can't instantly drain funds.
"""

import hashlib  # For SHA-256 hashing
import struct   # For serializing integers into bytes
import os       # For generating random transaction IDs
import time     # For timestamp display

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Simulated block height and timing
CURRENT_BLOCK_HEIGHT = 850_000         # Approximate current Bitcoin block height
VAULT_TIMELOCK_BLOCKS = 144            # 24-hour delay (~10 min/block * 144 = 1 day)
BLOCKS_PER_HOUR = 6                    # ~10 minute block interval

# Transaction version used in template hashing
TX_VERSION = 2

# Vault states
VAULT_STATE_LOCKED = "LOCKED"          # Funds sitting in vault (cold storage)
VAULT_STATE_UNVAULTING = "UNVAULTING"  # Withdrawal initiated, waiting for timelock
VAULT_STATE_COMPLETED = "COMPLETED"    # Withdrawal finalized
VAULT_STATE_CANCELLED = "CANCELLED"   # Withdrawal cancelled, funds back in vault

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Template Hash (CTV commitment) ---

def sha256(data: bytes) -> bytes:
    """Compute SHA-256 hash of data."""
    return hashlib.sha256(data).digest()


def double_sha256(data: bytes) -> bytes:
    """Compute double SHA-256 (standard Bitcoin hash)."""
    return sha256(sha256(data))


def serialize_uint32(value: int) -> bytes:
    """Serialize a 32-bit unsigned integer in little-endian."""
    return struct.pack("<I", value)


def serialize_uint64(value: int) -> bytes:
    """Serialize a 64-bit unsigned integer in little-endian."""
    return struct.pack("<Q", value)


class TxOutput:
    """
    Simplified transaction output.
    In real Bitcoin: value (satoshis) + scriptPubKey (locking script).
    """
    def __init__(self, value_sats: int, script_pubkey: bytes, label: str = ""):
        self.value_sats = value_sats          # Amount in satoshis
        self.script_pubkey = script_pubkey    # Locking script (simplified)
        self.label = label                     # Human-readable label for demo

    def serialize(self) -> bytes:
        """Serialize output for hashing (value + script length + script)."""
        script_len = len(self.script_pubkey).to_bytes(1, "little")
        return serialize_uint64(self.value_sats) + script_len + self.script_pubkey


class TxInput:
    """
    Simplified transaction input referencing a previous output.
    """
    def __init__(self, txid: bytes, vout: int, sequence: int = 0xFFFFFFFF):
        self.txid = txid          # Previous transaction hash (32 bytes)
        self.vout = vout          # Output index in previous transaction
        self.sequence = sequence  # Sequence number (used for timelocks)

    def serialize_outpoint(self) -> bytes:
        """Serialize the outpoint (txid + vout) this input spends."""
        return self.txid + serialize_uint32(self.vout)


def compute_template_hash(
    version: int,
    locktime: int,
    scriptsigs_hash: bytes,
    num_inputs: int,
    sequences_hash: bytes,
    num_outputs: int,
    outputs_hash: bytes,
    input_index: int
) -> bytes:
    """
    Compute the CTV template hash per BIP 119.

    This hash commits to the STRUCTURE of the spending transaction without
    committing to the input txids. This is what makes CTV powerful — it
    constrains WHERE coins can go without knowing WHERE they come from.

    Fields:
    - version: transaction version (usually 2)
    - locktime: transaction locktime
    - scriptsigs_hash: hash of all scriptSigs (usually empty for segwit)
    - num_inputs: number of inputs
    - sequences_hash: hash of all input sequence numbers
    - num_outputs: number of outputs
    - outputs_hash: hash of all serialized outputs
    - input_index: which input this CTV is evaluated for
    """
    # Concatenate all fields in BIP 119 order
    preimage = b""
    preimage += serialize_uint32(version)
    preimage += serialize_uint32(locktime)
    preimage += scriptsigs_hash                     # 32 bytes
    preimage += serialize_uint32(num_inputs)
    preimage += sequences_hash                      # 32 bytes
    preimage += serialize_uint32(num_outputs)
    preimage += outputs_hash                        # 32 bytes
    preimage += serialize_uint32(input_index)

    return sha256(preimage)  # Single SHA-256 per BIP 119


def compute_outputs_hash(outputs: list) -> bytes:
    """Hash all serialized outputs together."""
    all_outputs = b""
    for out in outputs:
        all_outputs += out.serialize()
    return sha256(all_outputs)


def compute_sequences_hash(sequences: list) -> bytes:
    """Hash all input sequence numbers together."""
    data = b""
    for seq in sequences:
        data += serialize_uint32(seq)
    return sha256(data)


# --- CTV Script ---

class CTVScript:
    """
    A script that enforces spending via CheckTemplateVerify.

    The script is simply: <template_hash> OP_CTV
    This means the spending transaction MUST match the committed template.
    """
    def __init__(self, template_hash: bytes):
        self.template_hash = template_hash

    def verify(self, spending_tx_template_hash: bytes) -> bool:
        """
        Verify that the spending transaction matches the committed template.
        In real Bitcoin, OP_CTV pops the hash from the stack and checks it
        against the computed hash of the spending transaction.
        """
        return self.template_hash == spending_tx_template_hash

    def to_script_asm(self) -> str:
        """Return human-readable script representation."""
        return f"<{self.template_hash.hex()[:16]}...> OP_CHECKTEMPLATEVERIFY"


# --- Vault ---

class Vault:
    """
    A CTV-based vault with 2-step withdrawal.

    Flow:
    1. DEPOSIT: Coins are locked in the vault CTV script
    2. INITIATE WITHDRAWAL: Spend vault UTXO → creates a timelocked output
       (this tx must match the CTV template exactly)
    3. WAIT: Timelock period (e.g., 144 blocks / ~24 hours)
    4. COMPLETE: After timelock, spend to final destination
       OR
    4. CANCEL: During timelock, owner can send back to vault (re-vault)

    The key insight: step 2 is constrained by CTV to only create outputs
    matching the pre-committed template. An attacker with the vault key
    can only trigger a withdrawal to the pre-defined intermediate address,
    giving the owner time to cancel.
    """
    def __init__(self, owner: str, amount_sats: int, hot_key: bytes, cold_key: bytes):
        self.owner = owner
        self.amount_sats = amount_sats
        self.hot_key = hot_key                  # Key for initiating withdrawal
        self.cold_key = cold_key                # Key for cancellation (recovery)
        self.state = VAULT_STATE_LOCKED
        self.unvault_height = None              # Block when unvaulting was initiated
        self.withdrawal_address = None          # Final destination
        self.vault_txid = os.urandom(32)        # Simulated vault UTXO txid
        self.log = []                           # Event log for demo output

        # Pre-compute the CTV template for the unvaulting transaction
        # This is done at vault creation time — it commits to the withdrawal
        # structure before the coins are even deposited
        self._build_templates()

    def _build_templates(self):
        """
        Build the CTV templates that constrain how vault funds can move.

        The unvault template commits to:
        - One output: the timelocked intermediate address
        - Locktime: 0 (no absolute timelock on the unvault tx itself)
        - The relative timelock is enforced by CSV in the intermediate script
        """
        # The intermediate output uses CSV to enforce the waiting period
        # After VAULT_TIMELOCK_BLOCKS, funds can move to the final destination
        intermediate_script = self._make_intermediate_script()
        self.intermediate_output = TxOutput(
            self.amount_sats,
            intermediate_script,
            label="Intermediate (timelocked)"
        )

        # Compute what the unvault transaction must look like
        outputs_hash = compute_outputs_hash([self.intermediate_output])
        sequences_hash = compute_sequences_hash([0xFFFFFFFF])  # Default sequence
        scriptsigs_hash = sha256(b"")  # Empty for segwit

        self.unvault_template_hash = compute_template_hash(
            version=TX_VERSION,
            locktime=0,
            scriptsigs_hash=scriptsigs_hash,
            num_inputs=1,
            sequences_hash=sequences_hash,
            num_outputs=1,
            outputs_hash=outputs_hash,
            input_index=0
        )

        # The vault script itself: <template_hash> OP_CTV
        self.vault_ctv = CTVScript(self.unvault_template_hash)

    def _make_intermediate_script(self) -> bytes:
        """
        Create the intermediate script that enforces the timelock.
        In real Bitcoin this would be:
            <timelock> OP_CSV OP_DROP <hot_key> OP_CHECKSIG
            OR
            <cold_key> OP_CHECKSIG  (cancel path, no timelock)
        """
        # Simplified: encode the timelock and keys into bytes for hashing
        script = b"CSV:" + serialize_uint32(VAULT_TIMELOCK_BLOCKS)
        script += b"|HOT:" + self.hot_key
        script += b"|COLD:" + self.cold_key
        return script

    def _record(self, event: str, detail: str):
        """Record an event for demo display."""
        self.log.append((event, detail))

    def initiate_withdrawal(self, destination: str, current_height: int) -> tuple:
        """
        Step 2: Initiate a withdrawal from the vault.

        This creates a transaction spending the vault UTXO. The transaction
        MUST match the CTV template — it can ONLY create the pre-committed
        intermediate output with a timelock.
        """
        if self.state != VAULT_STATE_LOCKED:
            return False, f"Vault is {self.state}, cannot initiate withdrawal"

        # Simulate building the unvault transaction
        # Compute its template hash and verify it matches the CTV commitment
        outputs_hash = compute_outputs_hash([self.intermediate_output])
        sequences_hash = compute_sequences_hash([0xFFFFFFFF])
        scriptsigs_hash = sha256(b"")

        spending_template_hash = compute_template_hash(
            version=TX_VERSION,
            locktime=0,
            scriptsigs_hash=scriptsigs_hash,
            num_inputs=1,
            sequences_hash=sequences_hash,
            num_outputs=1,
            outputs_hash=outputs_hash,
            input_index=0
        )

        # CTV verification — the spending tx must match the committed template
        if not self.vault_ctv.verify(spending_template_hash):
            return False, "CTV verification failed — transaction doesn't match template"

        self.state = VAULT_STATE_UNVAULTING
        self.unvault_height = current_height
        self.withdrawal_address = destination

        self._record("UNVAULT", f"Withdrawal initiated at block #{current_height:,}")
        self._record("UNVAULT", f"Destination: {destination}")
        self._record("UNVAULT", f"CTV template verified: {spending_template_hash.hex()[:24]}...")
        self._record("UNVAULT", f"Timelock: {VAULT_TIMELOCK_BLOCKS} blocks "
                     f"(~{VAULT_TIMELOCK_BLOCKS // BLOCKS_PER_HOUR} hours)")
        complete_height = current_height + VAULT_TIMELOCK_BLOCKS
        self._record("UNVAULT", f"Earliest completion: block #{complete_height:,}")

        return True, "Withdrawal initiated, timelock started"

    def complete_withdrawal(self, current_height: int) -> tuple:
        """
        Step 4a: Complete the withdrawal after the timelock has expired.

        This spends the intermediate UTXO using the hot key, only possible
        after VAULT_TIMELOCK_BLOCKS have elapsed since initiation.
        """
        if self.state != VAULT_STATE_UNVAULTING:
            return False, f"Vault is {self.state}, nothing to complete"

        # Check if timelock has expired
        blocks_elapsed = current_height - self.unvault_height
        if blocks_elapsed < VAULT_TIMELOCK_BLOCKS:
            remaining = VAULT_TIMELOCK_BLOCKS - blocks_elapsed
            self._record("BLOCKED", f"Timelock not expired! "
                        f"{blocks_elapsed}/{VAULT_TIMELOCK_BLOCKS} blocks elapsed, "
                        f"{remaining} remaining")
            return False, f"Timelock not expired — {remaining} blocks remaining"

        self.state = VAULT_STATE_COMPLETED
        self._record("COMPLETE", f"Withdrawal completed at block #{current_height:,}")
        self._record("COMPLETE", f"{self.amount_sats:,} sats sent to {self.withdrawal_address}")
        return True, f"Withdrawal completed — {self.amount_sats:,} sats to {self.withdrawal_address}"

    def cancel_withdrawal(self, current_height: int) -> tuple:
        """
        Step 4b: Cancel the withdrawal and re-vault the funds.

        This uses the cold key to spend the intermediate UTXO back to a
        new vault address. The cancel path has NO timelock — it can be
        executed immediately, which is what makes vaults secure: if you
        detect unauthorized unvaulting, you can cancel before the timelock
        expires.
        """
        if self.state != VAULT_STATE_UNVAULTING:
            return False, f"Vault is {self.state}, nothing to cancel"

        blocks_elapsed = current_height - self.unvault_height
        if blocks_elapsed >= VAULT_TIMELOCK_BLOCKS:
            # The timelock has already expired — too late to cancel
            self._record("CANCEL_FAIL", "Timelock already expired — too late to cancel")
            return False, "Cannot cancel — timelock already expired"

        self.state = VAULT_STATE_CANCELLED
        self._record("CANCEL", f"Withdrawal CANCELLED at block #{current_height:,}")
        self._record("CANCEL", f"Funds re-vaulted using cold key (no timelock needed)")
        self._record("CANCEL", f"{self.amount_sats:,} sats safe in new vault")
        return True, "Withdrawal cancelled — funds re-vaulted"

    def try_malicious_withdrawal(self) -> tuple:
        """
        Demonstrate that an attacker cannot create arbitrary outputs.

        Even with the hot key, the attacker can only create a transaction
        matching the CTV template. They cannot redirect funds elsewhere.
        """
        # Attacker tries to spend vault to their own address
        attacker_output = TxOutput(
            self.amount_sats,
            b"ATTACKER_ADDRESS_DEADBEEF",  # Not the committed intermediate script
            label="Attacker's address"
        )

        outputs_hash = compute_outputs_hash([attacker_output])
        sequences_hash = compute_sequences_hash([0xFFFFFFFF])
        scriptsigs_hash = sha256(b"")

        malicious_template_hash = compute_template_hash(
            version=TX_VERSION,
            locktime=0,
            scriptsigs_hash=scriptsigs_hash,
            num_inputs=1,
            sequences_hash=sequences_hash,
            num_outputs=1,
            outputs_hash=outputs_hash,
            input_index=0
        )

        # CTV check will fail — the template doesn't match
        verified = self.vault_ctv.verify(malicious_template_hash)
        return verified, malicious_template_hash


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Demonstrate CTV covenants and vault construct."""

    print("=" * 70)
    print("        COVENANTS (OP_CTV / CheckTemplateVerify)")
    print("=" * 70)

    # --- Part 1: Template Hash ---
    print("\n--- Part 1: CTV Template Hash ---\n")

    print("  CTV restricts HOW coins can be spent, not just WHO.")
    print("  It commits to the exact structure of the spending transaction.\n")

    # Show what goes into a template hash
    example_output = TxOutput(50_000_000, b"recipient_script", label="Pay Bob")
    outputs_hash = compute_outputs_hash([example_output])
    sequences_hash = compute_sequences_hash([0xFFFFFFFF])
    scriptsigs_hash = sha256(b"")

    template_hash = compute_template_hash(
        version=TX_VERSION, locktime=0,
        scriptsigs_hash=scriptsigs_hash,
        num_inputs=1,
        sequences_hash=sequences_hash,
        num_outputs=1,
        outputs_hash=outputs_hash,
        input_index=0
    )

    print("  Template hash components:")
    print(f"  ┌────────────────────────────────────────────────────────┐")
    print(f"  │ version:        {TX_VERSION:<40} │")
    print(f"  │ locktime:       {0:<40} │")
    print(f"  │ scriptsigs:     {scriptsigs_hash.hex()[:32]}... │")
    print(f"  │ num_inputs:     {1:<40} │")
    print(f"  │ sequences:      {sequences_hash.hex()[:32]}... │")
    print(f"  │ num_outputs:    {1:<40} │")
    print(f"  │ outputs:        {outputs_hash.hex()[:32]}... │")
    print(f"  │ input_index:    {0:<40} │")
    print(f"  ├────────────────────────────────────────────────────────┤")
    print(f"  │ template_hash:  {template_hash.hex()[:32]}... │")
    print(f"  └────────────────────────────────────────────────────────┘")

    print(f"\n  Script: <template_hash> OP_CHECKTEMPLATEVERIFY")
    print(f"  Meaning: spending tx MUST produce exactly these outputs")

    # --- Part 2: Vault Construction ---
    print(f"\n--- Part 2: Vault Construction ---\n")

    hot_key = os.urandom(32)   # Key for normal operations
    cold_key = os.urandom(32)  # Key stored offline for emergencies

    vault = Vault("Alice", 100_000_000, hot_key, cold_key)  # 1 BTC = 100M sats

    print(f"  Vault created for {vault.owner}:")
    print(f"  ┌────────────────────────────────────────────────────────┐")
    print(f"  │ Owner:          {vault.owner:<40} │")
    print(f"  │ Amount:         {vault.amount_sats:>12,} sats (1.0 BTC)         │")
    print(f"  │ State:          {vault.state:<40} │")
    print(f"  │ Timelock:       {VAULT_TIMELOCK_BLOCKS} blocks (~24 hours)"
          f"{' ' * 20} │")
    print(f"  │ CTV hash:       {vault.unvault_template_hash.hex()[:32]}... │")
    print(f"  └────────────────────────────────────────────────────────┘")

    print(f"\n  Vault flow:")
    print(f"  ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐")
    print(f"  │  DEPOSIT     │───>│  VAULT (CTV)     │───>│ INTERMEDIATE │")
    print(f"  │  (any input) │    │  locked by       │    │ (timelocked) │")
    print(f"  └──────────────┘    │  template hash   │    └──────┬───────┘")
    print(f"                      └──────────────────┘      wait │ {VAULT_TIMELOCK_BLOCKS} blocks")
    print(f"                                                     │")
    print(f"                      ┌──────────────────┐    ┌──────▼───────┐")
    print(f"                      │  RE-VAULT        │<───│  COMPLETE or │")
    print(f"                      │  (cancel path)   │    │  CANCEL      │")
    print(f"                      └──────────────────┘    └──────────────┘")

    # --- Part 3: Malicious Withdrawal Attempt ---
    print(f"\n--- Part 3: Attacker Tries to Steal Funds ---\n")

    print(f"  Attacker has Alice's hot key. Tries to redirect funds...")
    verified, bad_hash = vault.try_malicious_withdrawal()

    print(f"  ┌────────────────────────────────────────────────────────┐")
    print(f"  │ Attacker's template:  {bad_hash.hex()[:28]}...     │")
    print(f"  │ Vault's template:     {vault.unvault_template_hash.hex()[:28]}...     │")
    print(f"  │ Match:                {'YES' if verified else 'NO':<36} │")
    print(f"  │ Result:               {'ACCEPTED' if verified else 'REJECTED by OP_CTV':<36} │")
    print(f"  └────────────────────────────────────────────────────────┘")

    if not verified:
        print(f"\n  The attacker CANNOT redirect funds to a different address.")
        print(f"  CTV enforces that the spending tx matches the committed template.")
        print(f"  The ONLY thing the attacker can do is trigger the normal unvault")
        print(f"  process, which gives the owner time to cancel.")

    # --- Part 4: Normal Withdrawal (Happy Path) ---
    print(f"\n--- Part 4: Normal 2-Step Withdrawal ---\n")

    height = CURRENT_BLOCK_HEIGHT
    print(f"  Step 1: Initiate withdrawal at block #{height:,}")
    ok, msg = vault.initiate_withdrawal("bc1q_bob_final_address", height)
    print(f"  Result: {msg}")

    for event, detail in vault.log:
        print(f"    [{event:12s}] {detail}")
    vault.log.clear()

    # Try to complete too early
    early_height = height + 10
    print(f"\n  Step 2a: Try to complete at block #{early_height:,} (too early)")
    ok, msg = vault.complete_withdrawal(early_height)
    print(f"  Result: {msg}")
    for event, detail in vault.log:
        print(f"    [{event:12s}] {detail}")
    vault.log.clear()

    # Complete after timelock
    final_height = height + VAULT_TIMELOCK_BLOCKS + 1
    print(f"\n  Step 2b: Complete at block #{final_height:,} (after timelock)")
    ok, msg = vault.complete_withdrawal(final_height)
    print(f"  Result: {msg}")
    for event, detail in vault.log:
        print(f"    [{event:12s}] {detail}")

    # --- Part 5: Cancellation Path ---
    print(f"\n--- Part 5: Withdrawal Cancellation ---\n")

    vault2 = Vault("Alice", 100_000_000, hot_key, cold_key)

    height = CURRENT_BLOCK_HEIGHT
    print(f"  Step 1: Attacker initiates withdrawal at block #{height:,}")
    ok, msg = vault2.initiate_withdrawal("bc1q_attacker_address", height)
    print(f"  Result: {msg}")
    for event, detail in vault2.log:
        print(f"    [{event:12s}] {detail}")
    vault2.log.clear()

    # Alice detects and cancels
    cancel_height = height + 50  # 50 blocks later (~8 hours)
    print(f"\n  Step 2: Alice detects attack, cancels at block #{cancel_height:,}")
    ok, msg = vault2.cancel_withdrawal(cancel_height)
    print(f"  Result: {msg}")
    for event, detail in vault2.log:
        print(f"    [{event:12s}] {detail}")

    # --- Summary ---
    print(f"\n--- Summary: CTV Covenant Properties ---\n")
    print(f"  ┌──────────────────────────────────────────────────────────┐")
    print(f"  │ Property            │ How CTV achieves it               │")
    print(f"  ├─────────────────────┼───────────────────────────────────┤")
    print(f"  │ Restrict outputs    │ Template hash commits to outputs  │")
    print(f"  │ Non-interactive     │ Template computed at deposit time │")
    print(f"  │ No key custody      │ CTV is script-level, not key-lvl │")
    print(f"  │ Composable          │ CTV outputs can contain more CTV │")
    print(f"  │ Vault security      │ Attacker triggers timelock,      │")
    print(f"  │                     │ owner cancels with cold key      │")
    print(f"  └─────────────────────┴───────────────────────────────────┘")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
