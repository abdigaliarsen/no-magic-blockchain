"""
TITLE: Simplified Lightning Network
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    A simplified Lightning Network showing payment channels, commitment
    transactions, Hash Time-Locked Contracts (HTLCs), multi-hop payment
    routing, and cooperative/force channel closes.

KEY CONCEPTS:
    - Payment channels: fund once on-chain, transact unlimited off-chain
    - Commitment transactions: track the latest balance between two parties
    - HTLCs: hash-locked payments that enable trustless multi-hop routing
    - Channel close: cooperative (instant) vs force close (timelock delay)

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - core/03_digital_signatures.py (digital signatures)
    - bitcoin/01_utxo_model.py (UTXO transaction model)

REAL-WORLD RELEVANCE:
    The Lightning Network processes millions of Bitcoin payments per month
    with near-instant settlement and negligible fees. It solves Bitcoin's
    scalability limitation (~7 tx/sec on-chain) by moving most transactions
    off-chain while preserving trustless security guarantees.
"""

import hashlib  # For SHA-256 used in HTLCs and transaction hashing
import os       # For generating random preimages
import time     # For timestamps in commitment transactions

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Timelock for force-close: how many blocks the closer must wait
# This gives the counterparty time to dispute with a newer commitment
FORCE_CLOSE_TIMELOCK = 144  # ~1 day worth of blocks (144 × 10 min)

# HTLC timeout: blocks until the sender can reclaim locked funds
# if the receiver never reveals the preimage
HTLC_TIMEOUT_BLOCKS = 40

# Minimum channel capacity in satoshis
MIN_CHANNEL_CAPACITY = 20_000  # 20,000 sat minimum

# Fee for on-chain transactions (in satoshis)
ONCHAIN_FEE = 500  # Simplified fixed fee

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

def sha256(data):
    """Compute SHA-256 hash of data."""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).digest()


def double_sha256(data):
    """Double SHA-256, used for Bitcoin transaction IDs."""
    return sha256(sha256(data))


def generate_preimage():
    """Generate a random 32-byte preimage for HTLC."""
    return os.urandom(32)


def hash_preimage(preimage):
    """Hash a preimage to get the payment hash used in HTLCs."""
    return sha256(preimage)


class CommitmentTransaction:
    """
    A commitment transaction represents the current balance state of a channel.

    Each party holds their own version. When the channel closes, the latest
    commitment tx is broadcast. Old (revoked) commitments can be penalized.
    """

    def __init__(self, channel_id, seq_num, balance_a, balance_b, htlcs=None):
        self.channel_id = channel_id     # Identifies which channel this belongs to
        self.seq_num = seq_num           # Sequence number — higher = newer state
        self.balance_a = balance_a       # How much party A gets (satoshis)
        self.balance_b = balance_b       # How much party B gets (satoshis)
        self.htlcs = htlcs or []         # List of active HTLCs
        self.timestamp = time.time()     # When this commitment was created
        self.revoked = False             # True if a newer commitment exists
        self.signed_by_a = False         # Whether party A signed this
        self.signed_by_b = False         # Whether party B signed this

    @property
    def txid(self):
        """Compute a simplified transaction ID from the commitment data."""
        data = f"{self.channel_id}:{self.seq_num}:{self.balance_a}:{self.balance_b}"
        for htlc in self.htlcs:
            data += f":{htlc['hash'].hex()}:{htlc['amount']}"
        return double_sha256(data.encode()).hex()[:16]

    def sign(self, party):
        """Record that a party has signed this commitment."""
        if party == 'A':
            self.signed_by_a = True
        elif party == 'B':
            self.signed_by_b = True

    @property
    def fully_signed(self):
        """Both parties must sign for the commitment to be valid."""
        return self.signed_by_a and self.signed_by_b

    def total(self):
        """Total value locked in this commitment (should equal channel capacity)."""
        htlc_total = sum(h['amount'] for h in self.htlcs)
        return self.balance_a + self.balance_b + htlc_total


class HTLC:
    """
    Hash Time-Locked Contract: a conditional payment.

    The payment completes if the receiver reveals the preimage (hash → preimage).
    If not revealed before the timeout, the sender reclaims the funds.
    This enables trustless multi-hop routing.
    """

    def __init__(self, payment_hash, amount, timeout_blocks, sender, receiver):
        self.payment_hash = payment_hash    # SHA-256 hash that must be revealed
        self.amount = amount                # Payment amount in satoshis
        self.timeout_blocks = timeout_blocks  # Blocks until sender can reclaim
        self.sender = sender                # Who locked the funds
        self.receiver = receiver            # Who can claim with preimage
        self.settled = False                # True when preimage is revealed
        self.expired = False                # True when timeout passes without reveal
        self.preimage = None                # Set when the receiver reveals it

    def try_settle(self, preimage):
        """Attempt to settle the HTLC by revealing the preimage."""
        if self.settled or self.expired:
            return False

        # Verify: SHA-256(preimage) must equal the payment hash
        if sha256(preimage) == self.payment_hash:
            self.preimage = preimage
            self.settled = True
            return True
        return False

    def to_dict(self):
        """Convert to dict for embedding in commitment transactions."""
        return {
            'hash': self.payment_hash,
            'amount': self.amount,
            'timeout': self.timeout_blocks,
            'sender': self.sender,
            'receiver': self.receiver,
        }


class PaymentChannel:
    """
    A bidirectional payment channel between two parties.

    Lifecycle:
    1. Open: funding transaction locks funds on-chain
    2. Use: parties exchange signed commitment transactions off-chain
    3. Close: broadcast the latest commitment (cooperative or force)
    """

    def __init__(self, party_a, party_b, capacity, funding_a, funding_b):
        self.party_a = party_a          # Name of party A
        self.party_b = party_b          # Name of party B
        self.capacity = capacity        # Total satoshis locked in channel
        self.balance_a = funding_a      # A's current balance
        self.balance_b = funding_b      # B's current balance
        self.channel_id = double_sha256(f"{party_a}:{party_b}:{capacity}".encode()).hex()[:12]
        self.commitments = []           # History of all commitment transactions
        self.active_htlcs = []          # Currently pending HTLCs
        self.state = "OPEN"             # OPEN, CLOSED, FORCE_CLOSED
        self.seq_num = 0                # Current commitment sequence number
        self.events = []                # Log of channel events

        # Create the initial commitment (state 0)
        self._create_commitment()
        self._log(f"Channel opened: {party_a} ({funding_a} sat) ↔ {party_b} ({funding_b} sat)")

    def _log(self, message):
        """Record a channel event."""
        self.events.append(message)

    def _create_commitment(self):
        """Create a new commitment transaction reflecting current balances."""
        htlc_dicts = [h.to_dict() for h in self.active_htlcs]
        commitment = CommitmentTransaction(
            channel_id=self.channel_id,
            seq_num=self.seq_num,
            balance_a=self.balance_a,
            balance_b=self.balance_b,
            htlcs=htlc_dicts,
        )
        # Both parties sign the new commitment
        commitment.sign('A')
        commitment.sign('B')

        # Revoke all previous commitments — they're now outdated
        for old in self.commitments:
            old.revoked = True

        self.commitments.append(commitment)
        self.seq_num += 1
        return commitment

    def pay(self, sender, amount):
        """
        Make a direct payment within the channel (no HTLC needed for direct peers).

        Updates balances and creates a new commitment transaction.
        """
        if self.state != "OPEN":
            raise ValueError("Channel is closed")

        # Determine direction
        if sender == self.party_a:
            if amount > self.balance_a:
                raise ValueError(f"{sender} has insufficient balance ({self.balance_a} < {amount})")
            self.balance_a -= amount
            self.balance_b += amount
            receiver = self.party_b
        elif sender == self.party_b:
            if amount > self.balance_b:
                raise ValueError(f"{sender} has insufficient balance ({self.balance_b} < {amount})")
            self.balance_b -= amount
            self.balance_a += amount
            receiver = self.party_a
        else:
            raise ValueError(f"Unknown party: {sender}")

        commitment = self._create_commitment()
        self._log(f"Payment: {sender} → {receiver}: {amount} sat (commitment #{commitment.seq_num - 1})")
        return commitment

    def add_htlc(self, payment_hash, amount, sender, timeout=HTLC_TIMEOUT_BLOCKS):
        """
        Add an HTLC to the channel. Locks funds from sender until the
        preimage is revealed or the timeout expires.
        """
        if self.state != "OPEN":
            raise ValueError("Channel is closed")

        # Determine receiver
        if sender == self.party_a:
            if amount > self.balance_a:
                raise ValueError(f"{sender} has insufficient balance")
            self.balance_a -= amount  # Lock funds away from sender's balance
            receiver = self.party_b
        else:
            if amount > self.balance_b:
                raise ValueError(f"{sender} has insufficient balance")
            self.balance_b -= amount
            receiver = self.party_a

        htlc = HTLC(payment_hash, amount, timeout, sender, receiver)
        self.active_htlcs.append(htlc)

        commitment = self._create_commitment()
        self._log(f"HTLC added: {sender} → {receiver}: {amount} sat "
                  f"(hash: {payment_hash.hex()[:8]}...)")
        return htlc

    def settle_htlc(self, payment_hash, preimage):
        """
        Settle an HTLC by revealing the preimage.
        Funds move from locked state to the receiver's balance.
        """
        for htlc in self.active_htlcs:
            if htlc.payment_hash == payment_hash and not htlc.settled:
                if htlc.try_settle(preimage):
                    # Move locked funds to receiver's balance
                    if htlc.receiver == self.party_a:
                        self.balance_a += htlc.amount
                    else:
                        self.balance_b += htlc.amount

                    self.active_htlcs.remove(htlc)
                    commitment = self._create_commitment()
                    self._log(f"HTLC settled: {htlc.receiver} claimed {htlc.amount} sat "
                              f"(preimage: {preimage.hex()[:8]}...)")
                    return True
        return False

    def close_cooperative(self):
        """
        Cooperative close: both parties agree to the final state.
        The latest commitment is broadcast immediately — no timelock needed.
        """
        if self.state != "OPEN":
            raise ValueError("Channel is already closed")

        # Settle any remaining HTLCs (in practice, they'd be resolved first)
        self.state = "CLOSED"
        latest = self.commitments[-1]
        self._log(f"Cooperative close: {self.party_a}={self.balance_a} sat, "
                  f"{self.party_b}={self.balance_b} sat")
        return latest

    def close_force(self, closer):
        """
        Force close: one party broadcasts their latest commitment unilaterally.
        The closer's funds are timelocked; the other party can claim immediately.
        This is used when the counterparty is unresponsive.
        """
        if self.state != "OPEN":
            raise ValueError("Channel is already closed")

        self.state = "FORCE_CLOSED"
        latest = self.commitments[-1]
        self._log(f"Force close by {closer}! Funds timelocked for {FORCE_CLOSE_TIMELOCK} blocks.")
        self._log(f"  {closer}'s funds available after timelock.")

        other = self.party_b if closer == self.party_a else self.party_a
        self._log(f"  {other}'s funds available immediately.")
        return latest


class LightningNetwork:
    """
    A simplified Lightning Network managing multiple payment channels
    and routing payments through intermediaries.
    """

    def __init__(self):
        self.channels = {}   # channel_id → PaymentChannel
        self.nodes = {}      # node_name → list of channel_ids

    def open_channel(self, party_a, party_b, funding_a, funding_b):
        """Open a new payment channel between two parties."""
        capacity = funding_a + funding_b
        channel = PaymentChannel(party_a, party_b, capacity, funding_a, funding_b)

        self.channels[channel.channel_id] = channel

        # Register both parties as nodes
        for party in [party_a, party_b]:
            if party not in self.nodes:
                self.nodes[party] = []
            self.nodes[party].append(channel.channel_id)

        return channel

    def find_route(self, sender, receiver):
        """
        Find a path from sender to receiver through the channel graph.
        Uses simple BFS (breadth-first search) for shortest path.
        """
        if sender == receiver:
            return []

        # BFS to find shortest path
        visited = {sender}
        queue = [(sender, [])]  # (current_node, path_of_channel_ids)

        while queue:
            current, path = queue.pop(0)

            # Check all channels this node participates in
            for ch_id in self.nodes.get(current, []):
                channel = self.channels[ch_id]
                if channel.state != "OPEN":
                    continue

                # Determine the peer on the other end of this channel
                if channel.party_a == current:
                    peer = channel.party_b
                elif channel.party_b == current:
                    peer = channel.party_a
                else:
                    continue

                if peer in visited:
                    continue

                new_path = path + [ch_id]
                if peer == receiver:
                    return new_path  # Found the route!

                visited.add(peer)
                queue.append((peer, new_path))

        return None  # No route found

    def route_payment(self, sender, receiver, amount):
        """
        Route a payment from sender to receiver via HTLC chain.

        1. Receiver generates preimage and payment hash
        2. Sender locks funds via HTLC on each hop
        3. Receiver reveals preimage, settling each hop backwards
        """
        route = self.find_route(sender, receiver)
        if route is None:
            raise ValueError(f"No route from {sender} to {receiver}")

        # Step 1: Receiver generates the secret preimage
        preimage = generate_preimage()
        payment_hash = hash_preimage(preimage)

        # Build the hop list (pairs of nodes along the route)
        hops = []
        current = sender
        for ch_id in route:
            channel = self.channels[ch_id]
            if channel.party_a == current:
                next_node = channel.party_b
            else:
                next_node = channel.party_a
            hops.append((current, next_node, ch_id))
            current = next_node

        # Step 2: Add HTLCs along the route (forward direction)
        # Each hop gets a decreasing timeout so earlier hops expire later
        # This ensures the sender can always reclaim if routing fails
        htlcs = []
        for i, (hop_sender, hop_receiver, ch_id) in enumerate(hops):
            channel = self.channels[ch_id]
            timeout = HTLC_TIMEOUT_BLOCKS - (i * 10)  # Decreasing timeouts
            htlc = channel.add_htlc(payment_hash, amount, hop_sender, timeout)
            htlcs.append((channel, htlc))

        # Step 3: Settle HTLCs in reverse (backward direction)
        # The receiver reveals the preimage first, then each hop settles
        for channel, htlc in reversed(htlcs):
            channel.settle_htlc(payment_hash, preimage)

        return preimage, payment_hash, hops


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Demonstrate the Lightning Network with channels, payments, and routing."""
    print("=" * 72)
    print("  SIMPLIFIED LIGHTNING NETWORK")
    print("=" * 72)

    print(f"""
  The Lightning Network enables instant, low-fee Bitcoin payments by
  creating off-chain payment channels. Instead of recording every
  transaction on the blockchain, parties exchange signed commitments
  and only go on-chain to open/close channels.
    """)

    # ===================================================================
    # PART 1: Opening a Payment Channel
    # ===================================================================
    print("─" * 72)
    print("  PART 1: Opening a Payment Channel")
    print("─" * 72)

    ln = LightningNetwork()

    # Alice and Bob open a channel
    ch_ab = ln.open_channel("Alice", "Bob", 100_000, 50_000)

    print(f"""
  Alice and Bob open a payment channel:

  ┌─── Funding Transaction (on-chain) ───────────────────────────┐
  │                                                               │
  │  Alice deposits: 100,000 sat                                  │
  │  Bob deposits:    50,000 sat                                  │
  │  Total capacity: 150,000 sat                                  │
  │                                                               │
  │  This is a 2-of-2 multisig — both must sign to spend.        │
  │  Channel ID: {ch_ab.channel_id}                                    │
  └───────────────────────────────────────────────────────────────┘

  Initial commitment (state #0):
  ┌──────────────────────────────────────────┐
  │  Alice: 100,000 sat  │  Bob: 50,000 sat  │
  └──────────────────────────────────────────┘

  From now on, payments happen OFF-CHAIN (no miners needed)!
    """)

    # ===================================================================
    # PART 2: Making Payments Within the Channel
    # ===================================================================
    print("─" * 72)
    print("  PART 2: Off-Chain Payments (3 Payments)")
    print("─" * 72)

    payments = [
        ("Alice", 10_000, "coffee"),
        ("Alice", 25_000, "dinner"),
        ("Bob", 5_000, "refund"),
    ]

    for sender, amount, desc in payments:
        ch_ab.pay(sender, amount)

    # Show the state progression
    print(f"\n  Three payments, zero on-chain transactions:\n")
    for i, commit in enumerate(ch_ab.commitments):
        status = "CURRENT" if i == len(ch_ab.commitments) - 1 else "REVOKED"
        marker = "→" if status == "CURRENT" else " "
        revoke = " [REVOKED]" if commit.revoked else ""

        desc = ""
        if i == 0:
            desc = "(channel open)"
        elif i <= len(payments):
            s, a, d = payments[i - 1]
            desc = f"({s} pays {a:,} sat for {d})"

        print(f"  {marker} State #{i}: Alice={commit.balance_a:>7,} sat  "
              f"Bob={commit.balance_b:>6,} sat  {desc}{revoke}")

    print(f"""
  Each payment creates a new commitment transaction:
  • Old commitments are REVOKED (publishing one = penalty!)
  • Only the latest commitment reflects true balances
  • No miners, no fees, no confirmation wait — instant!
    """)

    # ===================================================================
    # PART 3: Multi-Hop Routing with HTLCs
    # ===================================================================
    print("─" * 72)
    print("  PART 3: Multi-Hop Routing (Alice → Bob → Carol)")
    print("─" * 72)

    # Open a channel between Bob and Carol
    ch_bc = ln.open_channel("Bob", "Carol", 80_000, 30_000)

    print(f"""
  Network topology:
    Alice ←──────────→ Bob ←──────────→ Carol
          ch: {ch_ab.channel_id}       ch: {ch_bc.channel_id}

  Alice wants to pay Carol 15,000 sat, but has no direct channel.
  Solution: route through Bob using Hash Time-Locked Contracts (HTLCs).
    """)

    # Save balances before routing
    before_alice = ch_ab.balance_a
    before_bob_ab = ch_ab.balance_b
    before_bob_bc = ch_bc.balance_a
    before_carol = ch_bc.balance_b

    print(f"  Balances BEFORE routing:")
    print(f"    Alice:     {before_alice:>7,} sat (in Alice↔Bob channel)")
    print(f"    Bob (A↔B): {before_bob_ab:>7,} sat")
    print(f"    Bob (B↔C): {before_bob_bc:>7,} sat")
    print(f"    Carol:     {before_carol:>7,} sat (in Bob↔Carol channel)")

    # Route the payment
    preimage, payment_hash, hops = ln.route_payment("Alice", "Carol", 15_000)

    print(f"""
  HTLC Routing Steps:

  Step 1: Carol generates secret preimage
    Preimage:     {preimage.hex()[:24]}...
    Payment Hash: {payment_hash.hex()[:24]}...
    Carol sends the hash to Alice (preimage stays secret).

  Step 2: Lock funds forward (Alice → Bob → Carol)
    ┌─────────┐  HTLC: 15k sat  ┌─────────┐  HTLC: 15k sat  ┌─────────┐
    │  Alice  │ ──────────────→ │   Bob   │ ──────────────→ │  Carol  │
    └─────────┘  timeout: {HTLC_TIMEOUT_BLOCKS} blk  └─────────┘  timeout: {HTLC_TIMEOUT_BLOCKS - 10} blk  └─────────┘

    Note: timeouts DECREASE along the route. This ensures:
    • Carol must claim before Bob's HTLC expires
    • Bob can claim from Alice after getting preimage from Carol

  Step 3: Settle backward (Carol reveals preimage)
    ┌─────────┐   preimage     ┌─────────┐   preimage     ┌─────────┐
    │  Alice  │ ←────────────── │   Bob   │ ←────────────── │  Carol  │
    └─────────┘                └─────────┘                └─────────┘
    Carol reveals preimage → Bob learns it → Bob settles with Alice
    """)

    print(f"  Balances AFTER routing:")
    print(f"    Alice:     {ch_ab.balance_a:>7,} sat ({ch_ab.balance_a - before_alice:+,})")
    print(f"    Bob (A↔B): {ch_ab.balance_b:>7,} sat ({ch_ab.balance_b - before_bob_ab:+,})")
    print(f"    Bob (B↔C): {ch_bc.balance_a:>7,} sat ({ch_bc.balance_a - before_bob_bc:+,})")
    print(f"    Carol:     {ch_bc.balance_b:>7,} sat ({ch_bc.balance_b - before_carol:+,})")
    print(f"\n    Bob's NET change: {(ch_ab.balance_b - before_bob_ab) + (ch_bc.balance_a - before_bob_bc):+,} sat")
    print(f"    → Bob forwarded the payment — his total balance is unchanged.")
    print(f"      (In practice, Bob would charge a small routing fee.)")

    # ===================================================================
    # PART 4: Channel Close
    # ===================================================================
    print("\n" + "─" * 72)
    print("  PART 4: Channel Close — Cooperative vs Force")
    print("─" * 72)

    # --- Cooperative close ---
    print(f"\n  A) Cooperative Close (Alice ↔ Bob channel)")
    print(f"     Both parties agree to the final state.\n")

    final = ch_ab.close_cooperative()

    print(f"  ┌─── Closing Transaction (on-chain) ──────────────────────────┐")
    print(f"  │                                                             │")
    print(f"  │  Spends the original funding transaction                    │")
    print(f"  │                                                             │")
    print(f"  │  Output 1: Alice → {final.balance_a:>7,} sat                        │")
    print(f"  │  Output 2: Bob   → {final.balance_b:>7,} sat                        │")
    print(f"  │                                                             │")
    print(f"  │  ✓ No timelock — both signed, funds available immediately   │")
    print(f"  │  ✓ Only 2 on-chain transactions total (open + close)        │")
    print(f"  │    despite {len(ch_ab.commitments) - 1} off-chain payments!                          │")
    print(f"  └─────────────────────────────────────────────────────────────┘")

    # --- Force close (simulate on the other channel) ---
    print(f"\n  B) Force Close (Bob ↔ Carol channel)")
    print(f"     Bob is unresponsive — Carol broadcasts unilaterally.\n")

    force_final = ch_bc.close_force("Carol")

    print(f"  ┌─── Force Close Transaction (on-chain) ─────────────────────┐")
    print(f"  │                                                             │")
    print(f"  │  Carol broadcasts HER latest commitment                     │")
    print(f"  │                                                             │")
    print(f"  │  Output 1: Bob   → {force_final.balance_a:>7,} sat (available NOW)       │")
    print(f"  │  Output 2: Carol → {force_final.balance_b:>7,} sat (TIMELOCKED)          │")
    print(f"  │                                                             │")
    print(f"  │  ⏱  Carol must wait {FORCE_CLOSE_TIMELOCK} blocks (~1 day) for her funds │")
    print(f"  │  ⚠  If Carol broadcast an OLD state, Bob can take ALL funds │")
    print(f"  │     using the revocation key (penalty for cheating!)        │")
    print(f"  └─────────────────────────────────────────────────────────────┘")

    # ===================================================================
    # PART 5: Channel Event Log
    # ===================================================================
    print(f"\n" + "─" * 72)
    print(f"  CHANNEL EVENT LOGS")
    print(f"─" * 72)

    print(f"\n  Alice ↔ Bob channel ({ch_ab.channel_id}):")
    for i, event in enumerate(ch_ab.events):
        print(f"    {i+1}. {event}")

    print(f"\n  Bob ↔ Carol channel ({ch_bc.channel_id}):")
    for i, event in enumerate(ch_bc.events):
        print(f"    {i+1}. {event}")

    # ===================================================================
    # Summary
    # ===================================================================
    print(f"\n" + "─" * 72)
    print(f"  WHY LIGHTNING MATTERS")
    print(f"─" * 72)
    print(f"""
  On-chain Bitcoin:
    • ~7 transactions per second
    • 10-minute confirmation time
    • Fee per transaction: ~$1-50 (varies with demand)

  Lightning Network:
    • Millions of transactions per second (theoretically)
    • Instant settlement (milliseconds)
    • Fee per transaction: < 1 satoshi
    • Only 2 on-chain transactions needed (open + close)

  Security guarantees:
    • Funds are secured by Bitcoin's blockchain
    • Cheating is punishable (old state = lose everything)
    • HTLCs are atomic: either the entire payment succeeds or fails
    • No trusted third party — trustless routing through strangers
    """)

    print("=" * 72)
    print("  Lightning: Bitcoin's layer-2 scaling solution.")
    print("=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
