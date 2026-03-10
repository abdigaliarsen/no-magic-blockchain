"""
TITLE: Account Abstraction (ERC-4337)
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    ERC-4337 account abstraction from scratch — smart contract wallets with
    programmable validation logic without protocol-level changes. Covers
    UserOperations, the EntryPoint contract, Paymasters for sponsored
    transactions, and social recovery with multi-guardian schemes.

KEY CONCEPTS:
    - UserOperation: a pseudo-transaction describing what a smart account wants to do
    - EntryPoint: a singleton contract that validates and executes UserOps
    - Paymaster: a contract that pays gas on behalf of users (sponsored txs)
    - Social recovery: guardians can change the account owner via threshold vote
    - Validation vs execution: two-phase processing for DoS resistance

PREREQUISITE SCRIPTS:
    - core/fundamentals/03_digital_signatures.py (signature verification)
    - ethereum/fundamentals/01_accounts_state.py (account model)
    - ethereum/fundamentals/06_smart_contracts.py (contract interactions)

REAL-WORLD RELEVANCE:
    ERC-4337 is live on Ethereum mainnet and L2s. It enables gas sponsorship
    (onboarding without ETH), batch transactions, session keys, social recovery,
    and arbitrary signature schemes (passkeys, multisig). Used by Safe, Biconomy,
    ZeroDev, Alchemy's Account Kit, and many wallet-as-a-service providers.
"""

import hashlib  # SHA-256 for hashing (stand-in for keccak256)
import time     # For nonce and timestamp simulation

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Gas costs for various operations
VERIFICATION_GAS_LIMIT = 100_000   # Max gas for validation phase
CALL_GAS_LIMIT = 200_000           # Max gas for execution phase
PRE_VERIFICATION_GAS = 21_000      # Overhead gas (calldata cost, etc.)

# EntryPoint address (singleton — same on all chains in real ERC-4337)
ENTRYPOINT_ADDRESS = "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789"

# Minimum stake for a paymaster to be accepted (in wei)
MIN_PAYMASTER_STAKE = 10**18  # 1 ETH

# Social recovery: minimum delay before recovery executes (blocks)
RECOVERY_DELAY_BLOCKS = 100

# How many hex chars to show for addresses/hashes
ADDR_DISPLAY = 10
HASH_DISPLAY = 16


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Utility functions ------------------------------------------------------

def sha256_hex(data: bytes) -> str:
    """SHA-256 hash as hex. Stand-in for keccak256."""
    return hashlib.sha256(data).hexdigest()


def make_address(name: str) -> str:
    """Generate a deterministic Ethereum-style address."""
    h = hashlib.sha256(name.encode()).hexdigest()
    return "0x" + h[:40]


def short_addr(addr: str) -> str:
    """Shorten address for display."""
    if len(addr) <= 12:
        return addr
    return addr[:6] + "..." + addr[-4:]


def sign_message(private_key: str, message: bytes) -> str:
    """Simulate signing a message with a private key.

    Real ECDSA signatures are 65 bytes (r, s, v). We simulate with
    a hash of (key + message) to demonstrate the concept.
    """
    return hashlib.sha256(private_key.encode() + message).hexdigest()


def verify_signature(address: str, message: bytes, signature: str, private_key: str) -> bool:
    """Verify a simulated signature.

    In reality, ecrecover(hash, v, r, s) → address. We check that
    the signature matches what signing with the expected key produces.
    """
    expected = hashlib.sha256(private_key.encode() + message).hexdigest()
    return signature == expected


# --- UserOperation ----------------------------------------------------------

class UserOperation:
    """A UserOperation is a pseudo-transaction for smart account wallets.

    Instead of sending a regular transaction (which requires an EOA with ETH),
    users submit UserOperations to a separate mempool. Bundlers package these
    into regular transactions that call the EntryPoint contract.

    Fields mirror the ERC-4337 spec.
    """

    def __init__(
        self,
        sender: str,              # The smart account address
        nonce: int,               # Anti-replay nonce (managed by account)
        call_data: bytes,         # What the account should execute
        call_gas_limit: int = CALL_GAS_LIMIT,
        verification_gas_limit: int = VERIFICATION_GAS_LIMIT,
        pre_verification_gas: int = PRE_VERIFICATION_GAS,
        max_fee_per_gas: int = 30 * 10**9,       # 30 Gwei
        max_priority_fee: int = 2 * 10**9,        # 2 Gwei
        paymaster: str | None = None,              # Paymaster address (or None)
        paymaster_data: bytes = b'',               # Data for paymaster validation
        signature: str = '',                        # Account signature
    ):
        self.sender = sender
        self.nonce = nonce
        self.call_data = call_data
        self.call_gas_limit = call_gas_limit
        self.verification_gas_limit = verification_gas_limit
        self.pre_verification_gas = pre_verification_gas
        self.max_fee_per_gas = max_fee_per_gas
        self.max_priority_fee = max_priority_fee
        self.paymaster = paymaster
        self.paymaster_data = paymaster_data
        self.signature = signature

    def hash(self) -> bytes:
        """Compute the UserOperation hash (used for signing).

        The hash covers all fields except the signature itself.
        This is what the account owner signs to authorize the operation.
        """
        data = (
            self.sender.encode() +
            self.nonce.to_bytes(32, 'big') +
            self.call_data +
            self.call_gas_limit.to_bytes(32, 'big') +
            self.max_fee_per_gas.to_bytes(32, 'big') +
            (self.paymaster or "").encode()
        )
        return hashlib.sha256(data).digest()

    def total_gas(self) -> int:
        """Total gas this operation could consume."""
        return self.call_gas_limit + self.verification_gas_limit + self.pre_verification_gas


# --- Smart Account (Contract Wallet) ----------------------------------------

class SmartAccount:
    """A smart contract wallet with programmable validation.

    Unlike EOAs (externally owned accounts), smart accounts can:
    - Use any signature scheme (ECDSA, multisig, passkeys, etc.)
    - Batch multiple calls in one transaction
    - Have social recovery mechanisms
    - Delegate gas payment to paymasters
    """

    def __init__(self, address: str, owner_key: str):
        self.address = address
        self.owner_key = owner_key  # The key authorized to sign operations
        self.owner_address = make_address(owner_key)
        self.nonce = 0
        self.balance = 0  # ETH balance for gas (in wei)

        # --- Social recovery state ---
        self.guardians: list[str] = []  # Guardian addresses
        self.recovery_threshold = 0     # How many guardians needed
        self.pending_recovery: dict | None = None  # Pending recovery request
        self.recovery_approvals: set[str] = set()  # Which guardians approved

    def validate_user_op(self, user_op: UserOperation) -> bool:
        """Validate a UserOperation's signature.

        This is the core of account abstraction — the ACCOUNT decides
        if an operation is authorized, not the protocol. Different accounts
        can implement different validation logic:
        - Single ECDSA signature (like this example)
        - Multisig (require N-of-M signatures)
        - Passkey (WebAuthn/FIDO2)
        - Session keys (time/scope-limited authorization)
        """
        # Check nonce to prevent replay attacks
        if user_op.nonce != self.nonce:
            return False

        # Verify the signature against the account owner
        op_hash = user_op.hash()
        return verify_signature(
            self.owner_address, op_hash, user_op.signature, self.owner_key
        )

    def execute(self, call_data: bytes) -> tuple[bool, str]:
        """Execute a call from this account.

        In real EVM, this would be a CALL opcode. We simulate by
        parsing the call_data as a simple command string.
        """
        # Increment nonce after successful execution
        self.nonce += 1

        # Parse the call data as a UTF-8 command (simplified)
        try:
            command = call_data.decode('utf-8')
            return True, f"Executed: {command}"
        except UnicodeDecodeError:
            return True, f"Executed: {len(call_data)} bytes of calldata"

    # --- Social recovery ----------------------------------------------------

    def setup_recovery(self, guardians: list[str], threshold: int):
        """Configure social recovery with a set of guardians.

        Guardians are trusted addresses (friends, family, other devices)
        who can collectively change the account owner if the key is lost.
        The threshold determines how many guardians must agree.
        """
        if threshold > len(guardians):
            raise ValueError("Threshold cannot exceed number of guardians")
        if threshold < 1:
            raise ValueError("Threshold must be at least 1")
        self.guardians = guardians
        self.recovery_threshold = threshold
        self.recovery_approvals = set()
        self.pending_recovery = None

    def initiate_recovery(self, new_owner_key: str, guardian: str) -> bool:
        """A guardian initiates recovery to a new owner.

        Any guardian can start the process. Once threshold approvals
        are reached, the owner key is changed.
        """
        if guardian not in self.guardians:
            return False  # Not a guardian

        new_owner_address = make_address(new_owner_key)
        self.pending_recovery = {
            "new_owner_key": new_owner_key,
            "new_owner_address": new_owner_address,
            "initiated_by": guardian,
        }
        self.recovery_approvals = {guardian}  # First guardian auto-approves
        return True

    def approve_recovery(self, guardian: str) -> bool:
        """A guardian approves the pending recovery.

        Once enough guardians approve, the recovery executes automatically.
        """
        if self.pending_recovery is None:
            return False
        if guardian not in self.guardians:
            return False
        if guardian in self.recovery_approvals:
            return False  # Already approved

        self.recovery_approvals.add(guardian)
        return True

    def execute_recovery(self) -> bool:
        """Execute recovery if threshold is met.

        Changes the account owner to the new key specified in the
        pending recovery. Resets recovery state afterward.
        """
        if self.pending_recovery is None:
            return False
        if len(self.recovery_approvals) < self.recovery_threshold:
            return False  # Not enough approvals yet

        # Change owner
        old_key = self.owner_key
        self.owner_key = self.pending_recovery["new_owner_key"]
        self.owner_address = self.pending_recovery["new_owner_address"]

        # Reset recovery state
        self.pending_recovery = None
        self.recovery_approvals = set()

        return True


# --- Paymaster --------------------------------------------------------------

class Paymaster:
    """A Paymaster sponsors gas for UserOperations.

    Paymasters enable gasless transactions — users don't need ETH to
    interact with the blockchain. Common use cases:
    - Onboarding: new users get free transactions
    - Token payments: pay gas in ERC-20 tokens instead of ETH
    - Subscriptions: app pays gas for its users
    """

    def __init__(self, address: str, balance: int = 0):
        self.address = address
        self.balance = balance  # Staked ETH for paying gas
        self.sponsored_ops: list[str] = []  # Track sponsored operations
        self.policy = "allow_all"  # Sponsorship policy

        # Rate limiting per sender
        self.sponsor_count: dict[str, int] = {}
        self.max_sponsors_per_sender = 5  # Max free txs per user

    def validate_paymaster_op(self, user_op: UserOperation) -> tuple[bool, str]:
        """Validate whether this paymaster will sponsor the UserOperation.

        The paymaster can implement arbitrary sponsorship logic:
        - Whitelist check
        - Rate limiting
        - Token balance check (for token paymasters)
        - Signature verification (for verifying paymasters)

        Returns (approved, reason).
        """
        # Check if paymaster has enough balance to cover gas
        max_cost = user_op.total_gas() * user_op.max_fee_per_gas
        if self.balance < max_cost:
            return False, "Paymaster underfunded"

        # Rate limit: max N sponsored txs per sender
        sender_count = self.sponsor_count.get(user_op.sender, 0)
        if sender_count >= self.max_sponsors_per_sender:
            return False, f"Rate limit exceeded ({self.max_sponsors_per_sender} free txs)"

        return True, "Approved"

    def post_op(self, user_op: UserOperation, actual_gas_used: int, gas_price: int):
        """Called after UserOp execution to settle payment.

        The paymaster's balance is debited for the actual gas used.
        In token paymasters, this is where the user's ERC-20 tokens
        would be collected as payment.
        """
        cost = actual_gas_used * gas_price
        self.balance -= cost
        self.sponsored_ops.append(user_op.sender)
        self.sponsor_count[user_op.sender] = self.sponsor_count.get(user_op.sender, 0) + 1


# --- EntryPoint Contract ---------------------------------------------------

class EntryPoint:
    """The singleton EntryPoint contract that processes UserOperations.

    All ERC-4337 operations flow through the EntryPoint:
    1. Bundler submits a batch of UserOps via handleOps()
    2. EntryPoint validates each op (calls account.validateUserOp)
    3. If a paymaster is specified, validates with paymaster too
    4. Executes the operation (calls account.execute)
    5. Settles gas payments

    The two-phase (validate then execute) design prevents DoS attacks:
    validation is cheap and deterministic, so invalid ops are rejected early.
    """

    def __init__(self):
        self.address = ENTRYPOINT_ADDRESS
        self.accounts: dict[str, SmartAccount] = {}  # Registered accounts
        self.paymasters: dict[str, Paymaster] = {}    # Registered paymasters
        self.execution_log: list[dict] = []           # Record of processed ops

    def register_account(self, account: SmartAccount):
        """Register a smart account with the EntryPoint."""
        self.accounts[account.address] = account

    def register_paymaster(self, paymaster: Paymaster):
        """Register a paymaster with the EntryPoint."""
        self.paymasters[paymaster.address] = paymaster

    def handle_ops(self, user_ops: list[UserOperation]) -> list[dict]:
        """Process a batch of UserOperations (called by bundler).

        This is the main entry point for ERC-4337. Each op goes through:
        1. Validation loop (all ops validated before any execution)
        2. Execution loop (execute validated ops, collect gas payments)

        Separating validation from execution prevents one failed op from
        affecting the validation of subsequent ops in the batch.
        """
        results = []

        for user_op in user_ops:
            result = self._handle_single_op(user_op)
            results.append(result)
            self.execution_log.append(result)

        return results

    def _handle_single_op(self, user_op: UserOperation) -> dict:
        """Process a single UserOperation through both phases."""
        result = {
            "sender": user_op.sender,
            "nonce": user_op.nonce,
            "success": False,
            "phase": "unknown",
            "reason": "",
            "gas_used": 0,
            "paymaster_used": user_op.paymaster is not None,
        }

        # --- Phase 1: Validation ---
        # Look up the sender account
        account = self.accounts.get(user_op.sender)
        if account is None:
            result["phase"] = "validation"
            result["reason"] = "Account not found"
            return result

        # Validate the UserOp signature with the account
        if not account.validate_user_op(user_op):
            result["phase"] = "validation"
            result["reason"] = "Signature validation failed"
            return result

        # If paymaster specified, validate with paymaster too
        paymaster = None
        if user_op.paymaster:
            paymaster = self.paymasters.get(user_op.paymaster)
            if paymaster is None:
                result["phase"] = "validation"
                result["reason"] = "Paymaster not found"
                return result

            approved, reason = paymaster.validate_paymaster_op(user_op)
            if not approved:
                result["phase"] = "validation"
                result["reason"] = f"Paymaster rejected: {reason}"
                return result

        # --- Phase 2: Execution ---
        success, exec_result = account.execute(user_op.call_data)
        gas_used = PRE_VERIFICATION_GAS + VERIFICATION_GAS_LIMIT // 2  # Simulated

        result["success"] = success
        result["phase"] = "execution"
        result["reason"] = exec_result
        result["gas_used"] = gas_used

        # Settle gas payment
        gas_price = user_op.max_fee_per_gas
        if paymaster:
            # Paymaster pays for gas
            paymaster.post_op(user_op, gas_used, gas_price)
            result["gas_paid_by"] = "paymaster"
        else:
            # Account pays for gas from its own balance
            cost = gas_used * gas_price
            account.balance -= cost
            result["gas_paid_by"] = "account"

        return result


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of ERC-4337 account abstraction."""

    print("=" * 70)
    print("ERC-4337 ACCOUNT ABSTRACTION — Smart Contract Wallets")
    print("=" * 70)
    print()

    # --- Setup: Create accounts, paymaster, entrypoint ---------------------
    entrypoint = EntryPoint()

    # Create smart account for Alice
    alice_key = "alice_private_key_001"
    alice_account = SmartAccount(make_address("alice_smart_account"), alice_key)
    alice_account.balance = 10 * 10**18  # 10 ETH for gas
    entrypoint.register_account(alice_account)

    # Create smart account for Bob
    bob_key = "bob_private_key_002"
    bob_account = SmartAccount(make_address("bob_smart_account"), bob_key)
    bob_account.balance = 5 * 10**18
    entrypoint.register_account(bob_account)

    # Create a paymaster (gas sponsor)
    paymaster = Paymaster(make_address("app_paymaster"), balance=100 * 10**18)
    entrypoint.register_paymaster(paymaster)

    print("--- Step 1: Setup ---")
    print()
    print("  Smart Accounts:")
    print(f"    Alice: {short_addr(alice_account.address)} (balance: 10 ETH)")
    print(f"    Bob:   {short_addr(bob_account.address)} (balance: 5 ETH)")
    print()
    print(f"  Paymaster: {short_addr(paymaster.address)} (staked: 100 ETH)")
    print(f"  EntryPoint: {short_addr(entrypoint.address)}")
    print()

    # --- Part 1: Basic UserOperation ----------------------------------------
    print("--- Step 2: Send a UserOperation (Self-Paid) ---")
    print()

    # Alice sends a UserOp to transfer tokens
    call_data = b"transfer(bob, 100 USDC)"
    user_op = UserOperation(
        sender=alice_account.address,
        nonce=0,
        call_data=call_data,
    )
    # Sign the UserOp
    user_op.signature = sign_message(alice_key, user_op.hash())

    print("  UserOperation:")
    print("  ┌──────────────────────────────────────────────────────────┐")
    print(f"  │ sender:           {short_addr(user_op.sender):<40}│")
    print(f"  │ nonce:            {user_op.nonce:<40}│")
    print(f"  │ callData:         {call_data.decode():<40}│")
    print(f"  │ callGasLimit:     {user_op.call_gas_limit:>10,} gas{'':<25}│")
    print(f"  │ verificationGas:  {user_op.verification_gas_limit:>10,} gas{'':<25}│")
    print(f"  │ maxFeePerGas:     {user_op.max_fee_per_gas // 10**9} Gwei{'':<34}│")
    print(f"  │ paymaster:        {'(none — self-paid)':<40}│")
    print(f"  │ signature:        {user_op.signature[:32]}...│")
    print("  └──────────────────────────────────────────────────────────┘")
    print()

    # Process through EntryPoint
    results = entrypoint.handle_ops([user_op])
    r = results[0]

    print("  EntryPoint Processing:")
    print(f"    Phase 1 (Validation): account.validateUserOp() → PASS")
    print(f"    Phase 2 (Execution):  account.execute() → {r['reason']}")
    print(f"    Gas used: {r['gas_used']:,}")
    print(f"    Gas paid by: {r['gas_paid_by']}")
    print(f"    Result: {'SUCCESS' if r['success'] else 'FAILED'}")
    print()

    # --- Part 2: Paymaster-sponsored transaction ----------------------------
    print("--- Step 3: Paymaster-Sponsored Transaction (Gasless) ---")
    print()

    print("  Scenario: Bob has a smart account but the app pays his gas.")
    print("  This is how gasless onboarding works — users don't need ETH!")
    print()

    call_data_2 = b"mint(nft_collection, token_id=42)"
    user_op_2 = UserOperation(
        sender=bob_account.address,
        nonce=0,
        call_data=call_data_2,
        paymaster=paymaster.address,  # App's paymaster pays
        paymaster_data=b"sponsored",
    )
    user_op_2.signature = sign_message(bob_key, user_op_2.hash())

    paymaster_balance_before = paymaster.balance

    results_2 = entrypoint.handle_ops([user_op_2])
    r2 = results_2[0]

    paymaster_cost = paymaster_balance_before - paymaster.balance

    print("  ┌──────────────────────────────────────────────────────────┐")
    print(f"  │ User (Bob):     signs the UserOp with his key           │")
    print(f"  │ Paymaster:      validates and agrees to sponsor         │")
    print(f"  │ EntryPoint:     executes and debits paymaster           │")
    print("  └──────────────────────────────────────────────────────────┘")
    print()
    print(f"  Result: {'SUCCESS' if r2['success'] else 'FAILED'}")
    print(f"  Gas paid by: PAYMASTER (not Bob!)")
    print(f"  Paymaster cost: {paymaster_cost / 10**18:.6f} ETH")
    print(f"  Bob's balance unchanged: {bob_account.balance / 10**18:.0f} ETH")
    print()

    # --- Part 3: Batch UserOps (bundler) ------------------------------------
    print("--- Step 4: Bundler Batches Multiple UserOps ---")
    print()
    print("  Bundlers collect UserOps from a separate mempool and package")
    print("  them into a single transaction that calls EntryPoint.handleOps().")
    print()

    # Create multiple ops
    batch_ops = []
    op_descriptions = [
        (alice_account, alice_key, b"swap(1 ETH -> USDC)", None),
        (bob_account, bob_key, b"approve(dex, 1000 USDC)", paymaster.address),
        (alice_account, alice_key, b"stake(100 USDC, vault)", None),
    ]

    for account, key, call_data_b, pm in op_descriptions:
        op = UserOperation(
            sender=account.address,
            nonce=account.nonce,  # Use current nonce
            call_data=call_data_b,
            paymaster=pm,
        )
        op.signature = sign_message(key, op.hash())
        batch_ops.append(op)

    batch_results = entrypoint.handle_ops(batch_ops)

    print("  Batch of 3 UserOps:")
    print("  ┌────┬──────────┬────────────────────────────┬──────────┬───────────┐")
    print("  │ #  │ Sender   │ Action                     │ Paymaster│ Result    │")
    print("  ├────┼──────────┼────────────────────────────┼──────────┼───────────┤")
    for i, (op, res) in enumerate(zip(batch_ops, batch_results)):
        sender = "Alice" if op.sender == alice_account.address else "Bob"
        action = op.call_data.decode()[:26]
        pm = "Yes" if op.paymaster else "No"
        status = "OK" if res["success"] else "FAIL"
        print(f"  │ {i+1}  │ {sender:<8} │ {action:<26} │ {pm:<8} │ {status:<9} │")
    print("  └────┴──────────┴────────────────────────────┴──────────┴───────────┘")
    print()

    # --- Part 4: Validation failure cases -----------------------------------
    print("--- Step 5: Validation Failures ---")
    print()

    failure_cases = []

    # Case 1: Wrong signature
    bad_op = UserOperation(sender=alice_account.address, nonce=alice_account.nonce, call_data=b"steal_funds()")
    bad_op.signature = "definitely_not_a_valid_signature"
    failure_cases.append(("Wrong signature", bad_op))

    # Case 2: Wrong nonce (replay attack)
    replay_op = UserOperation(sender=alice_account.address, nonce=0, call_data=b"replay_old_tx()")
    replay_op.signature = sign_message(alice_key, replay_op.hash())
    failure_cases.append(("Replay (old nonce)", replay_op))

    # Case 3: Unknown account
    ghost_op = UserOperation(sender=make_address("ghost"), nonce=0, call_data=b"haunt()")
    ghost_op.signature = "ghost_sig"
    failure_cases.append(("Unknown account", ghost_op))

    print("  ┌─────────────────────┬────────────────────────────────────┐")
    print("  │ Attack              │ Result                             │")
    print("  ├─────────────────────┼────────────────────────────────────┤")

    for label, op in failure_cases:
        result_f = entrypoint._handle_single_op(op)
        reason = result_f["reason"]
        if len(reason) > 34:
            reason = reason[:31] + "..."
        print(f"  │ {label:<19} │ REVERT: {reason:<26}│")

    print("  └─────────────────────┴────────────────────────────────────┘")
    print()
    print("  All failures caught in validation phase (Phase 1).")
    print("  Invalid ops never reach execution — saves gas and prevents DoS.")
    print()

    # --- Part 5: Social Recovery --------------------------------------------
    print("--- Step 6: Social Recovery (2-of-3 Guardians) ---")
    print()

    # Setup guardians for Alice's account
    guardian1 = make_address("alice_friend_dave")
    guardian2 = make_address("alice_sister_eve")
    guardian3 = make_address("alice_hardware_wallet")

    alice_account.setup_recovery(
        guardians=[guardian1, guardian2, guardian3],
        threshold=2  # 2 of 3 guardians needed
    )

    print("  Scenario: Alice loses her private key!")
    print()
    print(f"  Account: {short_addr(alice_account.address)}")
    print(f"  Old owner: {short_addr(alice_account.owner_address)}")
    print()
    print("  Guardians (2-of-3 required):")
    print(f"    [1] Dave (friend):     {short_addr(guardian1)}")
    print(f"    [2] Eve (sister):      {short_addr(guardian2)}")
    print(f"    [3] Hardware wallet:   {short_addr(guardian3)}")
    print()

    # Step 1: Dave initiates recovery
    new_key = "alice_new_key_after_recovery"
    alice_account.initiate_recovery(new_key, guardian1)
    print(f"  Step 1: Dave initiates recovery to new key")
    print(f"    Approvals: {len(alice_account.recovery_approvals)}/{alice_account.recovery_threshold}"
          f" (need {alice_account.recovery_threshold})")

    # Step 2: Eve approves
    alice_account.approve_recovery(guardian2)
    print(f"  Step 2: Eve approves recovery")
    print(f"    Approvals: {len(alice_account.recovery_approvals)}/{alice_account.recovery_threshold}"
          f" (threshold met!)")

    # Step 3: Execute recovery
    old_owner = alice_account.owner_address
    success = alice_account.execute_recovery()
    print(f"  Step 3: Recovery executed: {'SUCCESS' if success else 'FAILED'}")
    print()

    print(f"  Owner changed:")
    print(f"    Before: {short_addr(old_owner)}")
    print(f"    After:  {short_addr(alice_account.owner_address)}")
    print()

    # Verify old key no longer works
    old_op = UserOperation(sender=alice_account.address, nonce=alice_account.nonce, call_data=b"test()")
    old_op.signature = sign_message(alice_key, old_op.hash())  # Old key!
    old_valid = alice_account.validate_user_op(old_op)

    new_op = UserOperation(sender=alice_account.address, nonce=alice_account.nonce, call_data=b"test()")
    new_op.signature = sign_message(new_key, new_op.hash())  # New key
    new_valid = alice_account.validate_user_op(new_op)

    print(f"  Verification:")
    print(f"    Old key signs UserOp → valid? {'YES' if old_valid else 'NO (rejected)'}")
    print(f"    New key signs UserOp → valid? {'YES' if new_valid else 'NO'}")
    print()

    # --- Summary: EOA vs Smart Account -------------------------------------
    print("--- Summary: EOA vs Smart Account (ERC-4337) ---")
    print()
    print("  ┌────────────────────┬──────────────────┬──────────────────────┐")
    print("  │ Feature            │ EOA              │ Smart Account (4337) │")
    print("  ├────────────────────┼──────────────────┼──────────────────────┤")
    print("  │ Key management     │ Single ECDSA key │ Any scheme           │")
    print("  │ Gas payment        │ Must hold ETH    │ Paymaster can pay    │")
    print("  │ Batch transactions │ One tx at a time │ Multiple in one op   │")
    print("  │ Recovery           │ Lose key = lost  │ Social recovery      │")
    print("  │ Upgrade logic      │ Impossible       │ Upgradeable proxy    │")
    print("  │ Session keys       │ No               │ Time-limited access  │")
    print("  │ Protocol changes   │ N/A              │ None needed (4337)   │")
    print("  └────────────────────┴──────────────────┴──────────────────────┘")
    print()

    # --- Processing summary -------------------------------------------------
    print(f"  Total UserOps processed: {len(entrypoint.execution_log)}")
    successful = sum(1 for r in entrypoint.execution_log if r["success"])
    print(f"  Successful: {successful}")
    print(f"  Failed: {len(entrypoint.execution_log) - successful}")
    print(f"  Paymaster-sponsored: {sum(1 for r in entrypoint.execution_log if r['paymaster_used'])}")


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
