"""
TITLE: Stratum V2 Mining Protocol
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    A simplified Stratum V2 mining protocol simulation including job negotiation
    between pool and miners, template selection, share submission with per-miner
    difficulty, and PPLNS (Pay Per Last N Shares) reward distribution.

KEY CONCEPTS:
    - Job negotiation: miners can propose block templates (transaction selection)
    - Template distribution: pool sends work units to miners with unique extranonces
    - Share validation: miners submit partial proofs-of-work at reduced difficulty
    - Per-miner difficulty: pool adjusts target per miner based on hash rate
    - PPLNS: reward distribution weighted by recent share contributions

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - core/06_consensus_pow.py (proof-of-work mining)
    - bitcoin/fundamentals/03_mining.py (Bitcoin mining specifics)
    - bitcoin/fundamentals/07_difficulty_adjustment.py (difficulty targets)

REAL-WORLD RELEVANCE:
    Stratum V2 (SV2) is the successor to the widely-used Stratum V1 protocol.
    It adds encryption, enables miners to select transactions (improving
    decentralization), and reduces bandwidth. Major pools (e.g., DEMAND,
    Braiins) and firmware support SV2 in production.
"""

import hashlib  # For SHA-256 hashing (proof-of-work)
import struct   # For serializing block header fields
import os       # For random nonces and extranonces
import time     # For timestamps

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Network difficulty (simplified — real Bitcoin uses 256-bit targets)
NETWORK_DIFFICULTY_BITS = 24         # Leading zero bits required for a valid block
NETWORK_TARGET = (1 << (256 - NETWORK_DIFFICULTY_BITS)) - 1

# Share difficulty (much easier than block difficulty)
DEFAULT_SHARE_DIFFICULTY_BITS = 8    # Leading zero bits for a share
MIN_SHARE_DIFFICULTY_BITS = 4        # Minimum share difficulty
MAX_SHARE_DIFFICULTY_BITS = 20       # Maximum share difficulty

# PPLNS window size
PPLNS_WINDOW = 20                    # Number of recent shares for reward calculation

# Block reward
BLOCK_REWARD_SATS = 312_500_000      # 3.125 BTC (post-2024 halving)
POOL_FEE_PERCENT = 2.0               # Pool operator fee

# Target share rate (shares per simulated round per miner)
TARGET_SHARE_RATE = 3                # Aim for ~3 shares per round per miner

# Simulation parameters
NUM_MINERS = 5
SIMULATION_ROUNDS = 4                # Number of job rounds to simulate

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Hashing ---

def sha256d(data: bytes) -> bytes:
    """Double SHA-256 hash (standard Bitcoin block hash)."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def hash_to_int(h: bytes) -> int:
    """Convert a 32-byte hash to an integer (little-endian, like Bitcoin)."""
    return int.from_bytes(h, "little")


def meets_target(hash_bytes: bytes, difficulty_bits: int) -> bool:
    """Check if a hash meets the difficulty target (has enough leading zeros)."""
    hash_int = int.from_bytes(hash_bytes, "big")  # Big-endian for bit comparison
    target = (1 << (256 - difficulty_bits)) - 1
    return hash_int <= target


# --- Block Template ---

class Transaction:
    """A simplified transaction for block template construction."""
    def __init__(self, txid: str, fee_sats: int, weight: int):
        self.txid = txid            # Transaction identifier
        self.fee_sats = fee_sats    # Fee in satoshis
        self.weight = weight        # Weight units (max 4M per block)

    def serialize(self) -> bytes:
        """Serialize for inclusion in block header hash."""
        return self.txid.encode() + struct.pack("<Q", self.fee_sats)


class BlockTemplate:
    """
    A block template containing selected transactions.

    In Stratum V2, miners can propose their own templates (transaction
    selection), unlike V1 where the pool dictates everything.
    """
    def __init__(self, height: int, prev_hash: bytes, transactions: list,
                 coinbase_value: int, creator: str = "pool"):
        self.height = height
        self.prev_hash = prev_hash
        self.transactions = transactions
        self.coinbase_value = coinbase_value  # Block reward + total fees
        self.creator = creator                 # Who selected the transactions
        self.timestamp = int(time.time())
        self.version = 0x20000000              # BIP 9 version bits
        self.merkle_root = self._compute_merkle_root()

        # Total fees from selected transactions
        self.total_fees = sum(tx.fee_sats for tx in transactions)
        self.total_weight = sum(tx.weight for tx in transactions)

    def _compute_merkle_root(self) -> bytes:
        """Compute a simplified merkle root from transaction data."""
        if not self.transactions:
            return sha256d(b"empty_block")
        data = b""
        for tx in self.transactions:
            data += tx.serialize()
        return sha256d(data)

    def header_bytes(self, nonce: int, extranonce: bytes) -> bytes:
        """
        Serialize the block header for hashing.
        Includes the extranonce so each miner searches a unique nonce space.
        """
        header = b""
        header += struct.pack("<I", self.version)
        header += self.prev_hash
        # Mix extranonce into merkle root (simplified — real Bitcoin puts it in coinbase)
        modified_merkle = sha256d(self.merkle_root + extranonce)
        header += modified_merkle
        header += struct.pack("<I", self.timestamp)
        header += struct.pack("<I", NETWORK_DIFFICULTY_BITS)
        header += struct.pack("<I", nonce)
        return header


# --- Miner ---

class Miner:
    """
    A mining worker connected to the pool.

    Each miner has a unique extranonce to avoid duplicate work,
    and a per-miner difficulty target for share submission.
    """
    def __init__(self, name: str, hash_rate_relative: float):
        self.name = name
        self.hash_rate = hash_rate_relative   # Relative hash power (e.g., 1.0, 2.5)
        self.extranonce = os.urandom(8)       # Unique nonce space partition
        self.share_difficulty = DEFAULT_SHARE_DIFFICULTY_BITS
        self.shares_submitted = 0
        self.shares_accepted = 0
        self.shares_rejected = 0
        self.blocks_found = 0
        self.proposed_templates = 0           # Templates this miner proposed (SV2 feature)

    def mine(self, template: BlockTemplate, max_attempts: int = 10000) -> list:
        """
        Attempt to mine shares (and possibly a block) on the given template.

        Returns a list of Share objects for valid shares found.
        """
        shares = []
        attempts = int(max_attempts * self.hash_rate)  # More hash rate = more attempts

        for nonce in range(attempts):
            header = template.header_bytes(nonce, self.extranonce)
            hash_result = sha256d(header)

            # Check if this meets share difficulty (much easier than block)
            if meets_target(hash_result, self.share_difficulty):
                is_block = meets_target(hash_result, NETWORK_DIFFICULTY_BITS)
                share = Share(
                    miner_name=self.name,
                    nonce=nonce,
                    hash_result=hash_result,
                    difficulty=self.share_difficulty,
                    is_block=is_block,
                    template_creator=template.creator
                )
                shares.append(share)
                self.shares_submitted += 1

                if is_block:
                    self.blocks_found += 1
                    break  # Stop mining once a block is found

        return shares


class Share:
    """
    A proof-of-work share submitted by a miner to the pool.
    A share proves the miner is doing work, even if it doesn't meet
    full network difficulty.
    """
    def __init__(self, miner_name: str, nonce: int, hash_result: bytes,
                 difficulty: int, is_block: bool, template_creator: str):
        self.miner_name = miner_name
        self.nonce = nonce
        self.hash_result = hash_result
        self.difficulty = difficulty
        self.is_block = is_block              # True if this share is also a valid block
        self.template_creator = template_creator
        self.timestamp = time.time()
        self.accepted = False                  # Set by pool during validation

    def weight(self) -> float:
        """
        Share weight based on difficulty.
        Higher difficulty shares count for more in PPLNS.
        A share at difficulty D is worth 2^D relative to difficulty 1.
        """
        return 2 ** self.difficulty


# --- Mining Pool ---

class MiningPool:
    """
    A Stratum V2 mining pool that coordinates miners, validates shares,
    adjusts per-miner difficulty, and distributes rewards via PPLNS.
    """
    def __init__(self, name: str):
        self.name = name
        self.miners = {}                    # name -> Miner
        self.share_log = []                 # All accepted shares (PPLNS window)
        self.blocks_found = []              # Blocks mined by the pool
        self.mempool = []                   # Available transactions
        self.current_height = 850_000
        self.prev_hash = os.urandom(32)     # Previous block hash
        self.job_log = []                   # Log of job distributions

    def register_miner(self, miner: Miner):
        """Register a miner with the pool."""
        self.miners[miner.name] = miner

    def populate_mempool(self, num_txs: int = 20):
        """Create simulated transactions in the mempool."""
        self.mempool = []
        for i in range(num_txs):
            fee = 1000 + (i * 500) + int.from_bytes(os.urandom(2), "big") % 5000
            weight = 200 + int.from_bytes(os.urandom(2), "big") % 800
            tx = Transaction(f"tx_{i:04d}_{os.urandom(4).hex()}", fee, weight)
            self.mempool.append(tx)
        # Sort by fee rate (fee/weight) descending — rational miners pick highest fee rate
        self.mempool.sort(key=lambda t: t.fee_sats / t.weight, reverse=True)

    def create_template(self, creator: str = "pool") -> BlockTemplate:
        """
        Create a block template from mempool transactions.

        In SV2, either the pool or a miner can create the template.
        The creator selects which transactions to include.
        """
        selected = []
        total_weight = 0
        max_weight = 4_000_000  # 4M weight units per block

        for tx in self.mempool:
            if total_weight + tx.weight <= max_weight:
                selected.append(tx)
                total_weight += tx.weight

        total_fees = sum(tx.fee_sats for tx in selected)
        coinbase_value = BLOCK_REWARD_SATS + total_fees

        return BlockTemplate(
            self.current_height, self.prev_hash, selected,
            coinbase_value, creator=creator
        )

    def negotiate_template(self, miner: Miner) -> BlockTemplate:
        """
        SV2 job negotiation: miner proposes a template, pool validates.

        This is the key SV2 improvement — miners can choose which
        transactions to include, improving censorship resistance.
        """
        # Miner creates their own template (possibly different tx selection)
        template = self.create_template(creator=miner.name)
        miner.proposed_templates += 1

        # Pool validates: check that coinbase pays the pool correctly
        # In a real implementation, pool checks:
        # 1. Coinbase output pays pool's address
        # 2. No invalid transactions
        # 3. Template meets consensus rules
        return template

    def distribute_jobs(self) -> dict:
        """
        Send mining jobs to all registered miners.
        Returns mapping of miner_name -> template.
        """
        jobs = {}
        for name, miner in self.miners.items():
            # Every other round, let one miner propose their template (SV2 feature)
            if miner.proposed_templates == 0 and miner.hash_rate >= 2.0:
                # Higher hashrate miners negotiate templates
                template = self.negotiate_template(miner)
                self.job_log.append((name, "negotiated", template.total_fees))
            else:
                template = self.create_template(creator="pool")
                self.job_log.append((name, "pool-assigned", template.total_fees))
            jobs[name] = template
        return jobs

    def validate_share(self, share: Share) -> bool:
        """
        Validate a submitted share.
        Check that the hash actually meets the claimed difficulty.
        """
        if meets_target(share.hash_result, share.difficulty):
            share.accepted = True
            self.share_log.append(share)
            self.miners[share.miner_name].shares_accepted += 1

            if share.is_block:
                self.blocks_found.append(share)
                self._advance_block()

            return True
        else:
            self.miners[share.miner_name].shares_rejected += 1
            return False

    def _advance_block(self):
        """Advance to the next block after finding one."""
        self.prev_hash = os.urandom(32)
        self.current_height += 1

    def adjust_difficulty(self, miner: Miner, shares_this_round: int):
        """
        Adjust per-miner share difficulty based on submission rate.

        Goal: each miner should submit ~TARGET_SHARE_RATE shares per round.
        Too many shares → increase difficulty (reduce pool bandwidth)
        Too few shares → decrease difficulty (ensure miner gets credit)
        """
        if shares_this_round == 0:
            # Miner found nothing — make it easier
            miner.share_difficulty = max(MIN_SHARE_DIFFICULTY_BITS,
                                         miner.share_difficulty - 2)
        elif shares_this_round > TARGET_SHARE_RATE * 2:
            # Too many shares — make it harder
            miner.share_difficulty = min(MAX_SHARE_DIFFICULTY_BITS,
                                         miner.share_difficulty + 1)
        elif shares_this_round < TARGET_SHARE_RATE // 2:
            # Too few shares — make it easier
            miner.share_difficulty = max(MIN_SHARE_DIFFICULTY_BITS,
                                         miner.share_difficulty - 1)
        # Otherwise: difficulty is about right, keep it

    def compute_pplns_rewards(self) -> dict:
        """
        Compute PPLNS (Pay Per Last N Shares) reward distribution.

        PPLNS uses a sliding window of the last N shares to determine
        each miner's payout. This discourages pool-hopping because
        miners must contribute consistently to earn rewards.

        Share weight is proportional to difficulty — a share at difficulty
        D counts as 2^D times a share at difficulty 1.
        """
        # Take the last PPLNS_WINDOW shares
        window = self.share_log[-PPLNS_WINDOW:] if len(self.share_log) > PPLNS_WINDOW \
            else self.share_log

        if not window:
            return {}

        # Sum weighted shares per miner
        miner_weights = {}
        total_weight = 0.0
        for share in window:
            w = share.weight()
            miner_weights[share.miner_name] = miner_weights.get(share.miner_name, 0) + w
            total_weight += w

        # Distribute block reward proportionally
        pool_fee = int(BLOCK_REWARD_SATS * POOL_FEE_PERCENT / 100)
        distributable = BLOCK_REWARD_SATS - pool_fee

        rewards = {}
        for name, weight in miner_weights.items():
            fraction = weight / total_weight if total_weight > 0 else 0
            rewards[name] = int(distributable * fraction)

        return rewards


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def fmt_sats(sats: int) -> str:
    """Format satoshis as BTC string."""
    btc = sats / 100_000_000
    return f"{btc:.4f} BTC"


def demo():
    """Demonstrate Stratum V2 mining protocol."""

    print("=" * 70)
    print("        STRATUM V2 MINING PROTOCOL")
    print("=" * 70)

    # --- Part 1: Pool Setup ---
    print("\n--- Part 1: Pool and Miner Registration ---\n")

    pool = MiningPool("DemoPool")
    pool.populate_mempool(20)

    # Create miners with varying hash rates
    miner_configs = [
        ("Miner_A", 3.0),   # Large miner — high hash rate
        ("Miner_B", 2.0),   # Medium miner
        ("Miner_C", 1.5),   # Medium-small miner
        ("Miner_D", 1.0),   # Small miner
        ("Miner_E", 0.5),   # Very small miner
    ]

    for name, rate in miner_configs:
        miner = Miner(name, rate)
        pool.register_miner(miner)

    total_rate = sum(m.hash_rate for m in pool.miners.values())

    print(f"  Pool: {pool.name}")
    print(f"  Block height: #{pool.current_height:,}")
    print(f"  Block reward: {fmt_sats(BLOCK_REWARD_SATS)}")
    print(f"  Pool fee: {POOL_FEE_PERCENT}%")
    print(f"  PPLNS window: {PPLNS_WINDOW} shares\n")

    print(f"  ┌{'─' * 50}┐")
    print(f"  │ {'Miner':<12} {'Hash Rate':>10} {'Share %':>10} {'Difficulty':>14} │")
    print(f"  ├{'─' * 50}┤")
    for name, miner in pool.miners.items():
        pct = (miner.hash_rate / total_rate) * 100
        print(f"  │ {name:<12} {miner.hash_rate:>9.1f}x {pct:>9.1f}% "
              f"{miner.share_difficulty:>11} bits │")
    print(f"  └{'─' * 50}┘")

    # --- Part 2: Mempool and Template ---
    print(f"\n--- Part 2: Block Template Construction ---\n")

    template = pool.create_template()
    top_txs = template.transactions[:5]  # Show top 5 by fee rate

    print(f"  Mempool: {len(pool.mempool)} transactions")
    print(f"  Template: {len(template.transactions)} txs selected")
    print(f"  Total weight: {template.total_weight:,} / 4,000,000 WU")
    print(f"  Total fees: {fmt_sats(template.total_fees)}")
    print(f"  Coinbase: {fmt_sats(template.coinbase_value)}\n")

    print(f"  Top transactions by fee rate:")
    print(f"  ┌{'─' * 56}┐")
    print(f"  │ {'TxID':<20} {'Fee (sats)':>10} {'Weight':>8} {'sat/WU':>8} │")
    print(f"  ├{'─' * 56}┤")
    for tx in top_txs:
        rate = tx.fee_sats / tx.weight
        print(f"  │ {tx.txid[:20]:<20} {tx.fee_sats:>10,} {tx.weight:>8,} {rate:>8.2f} │")
    print(f"  │ {'...':<20} {'':>10} {'':>8} {'':>8} │")
    print(f"  └{'─' * 56}┘")

    # --- Part 3: Job Negotiation (SV2 Feature) ---
    print(f"\n--- Part 3: Job Negotiation (SV2 Feature) ---\n")

    print(f"  Stratum V1: pool dictates ALL transaction selection")
    print(f"  Stratum V2: miners can PROPOSE their own templates\n")

    pool.job_log.clear()
    jobs = pool.distribute_jobs()

    print(f"  Job distribution:")
    print(f"  ┌{'─' * 58}┐")
    print(f"  │ {'Miner':<12} {'Type':<18} {'Template Fees':>14} {'Creator':>10} │")
    print(f"  ├{'─' * 58}┤")
    for name, job_type, fees in pool.job_log:
        creator = name if job_type == "negotiated" else "pool"
        type_label = "NEGOTIATED" if job_type == "negotiated" else "pool-assigned"
        print(f"  │ {name:<12} {type_label:<18} {fmt_sats(fees):>14} {creator:>10} │")
    print(f"  └{'─' * 58}┘")

    print(f"\n  Miners with higher hash rate (>= 2x) negotiate their own")
    print(f"  templates — they choose which transactions to include.")

    # --- Part 4: Mining Simulation ---
    print(f"\n--- Part 4: Mining Simulation ({SIMULATION_ROUNDS} rounds) ---\n")

    for round_num in range(1, SIMULATION_ROUNDS + 1):
        pool.populate_mempool(20)  # Refresh mempool each round
        jobs = pool.distribute_jobs()

        round_shares = {}
        block_found_by = None

        for name, miner in pool.miners.items():
            shares = miner.mine(jobs[name], max_attempts=5000)
            valid_count = 0
            for share in shares:
                if pool.validate_share(share):
                    valid_count += 1
                    if share.is_block:
                        block_found_by = name
            round_shares[name] = valid_count

            # Adjust difficulty based on share rate
            pool.adjust_difficulty(miner, valid_count)

        print(f"  Round {round_num}:")
        print(f"  ┌{'─' * 46}┐")
        print(f"  │ {'Miner':<12} {'Shares':>8} {'New Diff':>10} {'Block?':>12} │")
        print(f"  ├{'─' * 46}┤")
        for name, miner in pool.miners.items():
            found = "BLOCK!" if name == block_found_by else ""
            print(f"  │ {name:<12} {round_shares[name]:>8} "
                  f"{miner.share_difficulty:>7} bits {found:>12} │")
        print(f"  └{'─' * 46}┘")

        if block_found_by:
            print(f"  >>> Block found by {block_found_by}! "
                  f"Height: #{pool.current_height - 1:,}")
        print()

    # --- Part 5: PPLNS Reward Distribution ---
    print(f"--- Part 5: PPLNS Reward Distribution ---\n")

    print(f"  PPLNS window: last {PPLNS_WINDOW} shares")
    print(f"  Total shares in log: {len(pool.share_log)}")

    window_shares = pool.share_log[-PPLNS_WINDOW:] if len(pool.share_log) > PPLNS_WINDOW \
        else pool.share_log

    # Count shares per miner in window
    share_counts = {}
    for share in window_shares:
        share_counts[share.miner_name] = share_counts.get(share.miner_name, 0) + 1

    rewards = pool.compute_pplns_rewards()
    pool_fee_sats = int(BLOCK_REWARD_SATS * POOL_FEE_PERCENT / 100)

    print(f"\n  ┌{'─' * 62}┐")
    print(f"  │ {'Miner':<12} {'Shares':>8} {'Weight':>10} {'Reward':>16} {'% of Total':>12} │")
    print(f"  ├{'─' * 62}┤")

    total_reward = sum(rewards.values())
    for name in sorted(rewards.keys()):
        count = share_counts.get(name, 0)
        # Compute weight in window
        miner_weight = sum(s.weight() for s in window_shares if s.miner_name == name)
        pct = (rewards[name] / total_reward * 100) if total_reward > 0 else 0
        print(f"  │ {name:<12} {count:>8} {miner_weight:>10.0f} "
              f"{fmt_sats(rewards[name]):>16} {pct:>11.1f}% │")

    print(f"  ├{'─' * 62}┤")
    print(f"  │ {'Pool fee':<12} {'':>8} {'':>10} "
          f"{fmt_sats(pool_fee_sats):>16} {POOL_FEE_PERCENT:>11.1f}% │")
    print(f"  │ {'Block reward':<12} {'':>8} {'':>10} "
          f"{fmt_sats(BLOCK_REWARD_SATS):>16} {'100.0%':>12} │")
    print(f"  └{'─' * 62}┘")

    # --- Part 6: V1 vs V2 Comparison ---
    print(f"\n--- Part 6: Stratum V1 vs V2 Comparison ---\n")

    print(f"  ┌{'─' * 60}┐")
    print(f"  │ {'Feature':<24} {'V1':^16} {'V2':^16} │")
    print(f"  ├{'─' * 60}┤")
    comparisons = [
        ("Encryption",        "None (plain)",   "AEAD encrypted"),
        ("Tx selection",      "Pool only",      "Miner can propose"),
        ("Bandwidth",         "High (JSON)",    "Low (binary)"),
        ("Header-only mining","No",             "Yes"),
        ("Man-in-middle",     "Vulnerable",     "Prevented"),
        ("Share aggregation", "No",             "Yes"),
        ("Template negot.",   "No",             "Yes (job decl.)"),
    ]
    for feature, v1, v2 in comparisons:
        print(f"  │ {feature:<24} {v1:^16} {v2:^16} │")
    print(f"  └{'─' * 60}┘")

    # --- Summary Statistics ---
    print(f"\n--- Summary ---\n")

    print(f"  ┌{'─' * 54}┐")
    print(f"  │ {'Miner':<12} {'Accepted':>8} {'Rejected':>8} {'Blocks':>8} {'Templates':>10} │")
    print(f"  ├{'─' * 54}┤")
    for name, miner in pool.miners.items():
        print(f"  │ {name:<12} {miner.shares_accepted:>8} "
              f"{miner.shares_rejected:>8} {miner.blocks_found:>8} "
              f"{miner.proposed_templates:>10} │")
    print(f"  └{'─' * 54}┘")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
