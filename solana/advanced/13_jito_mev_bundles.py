"""
TITLE: Jito MEV Bundles
CATEGORY: solana

WHAT THIS IMPLEMENTS:
    Jito's MEV extraction infrastructure for Solana — the equivalent of Flashbots
    on Ethereum. Searchers detect profitable opportunities (arbitrage, liquidations),
    construct atomic bundles of ordered transactions, and compete in a tip auction
    where the highest bidder wins inclusion by the block-producing validator.

KEY CONCEPTS:
    - MEV (Maximal Extractable Value): profit from transaction ordering/inclusion
    - Bundle: ordered list of transactions executed atomically (all-or-nothing)
    - Tip auction: searchers compete by tipping validators via Jito tip accounts
    - Backrun opportunities: detect a profitable tx and append a follow-up tx
    - Validator revenue: tips flow to the leader who includes the winning bundle

PREREQUISITE SCRIPTS:
    - solana/fundamentals/01_accounts_model.py (account structure)
    - solana/fundamentals/04_transactions.py (transaction format)
    - solana/intermediate/10_sealevel_parallel.py (parallel execution)

REAL-WORLD RELEVANCE:
    Jito processes the majority of Solana transactions, generating millions in
    MEV revenue. Searchers use Jito bundles for DEX arbitrage, liquidations, and
    NFT sniping. Understanding MEV is critical for DeFi protocol design, as
    unprotected protocols leak value to searchers at users' expense.
"""

import hashlib
import random
import time

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Number of Jito tip accounts — real Jito uses 8 rotating tip accounts
# to distribute load and prevent contention on a single account
NUM_TIP_ACCOUNTS = 8

# Minimum tip to be considered in the auction (in lamports)
# Real Jito has dynamic minimums based on demand
MIN_TIP_LAMPORTS = 10_000  # 0.00001 SOL

# Maximum transactions per bundle — Jito enforces a limit to prevent
# oversized bundles from hogging block space
MAX_BUNDLE_SIZE = 5

# Simulation parameters
NUM_SEARCHERS = 5          # Number of competing searchers
NUM_DEX_POOLS = 3          # Number of simulated DEX liquidity pools
RANDOM_SEED = 42           # Reproducible results
BLOCK_CAPACITY = 20        # Max transactions the leader can fit in a block

# Lamports per SOL for display conversion
LAMPORTS_PER_SOL = 1_000_000_000


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: DEX pool — simulates an AMM liquidity pool for arbitrage detection
# ----------------------------------------------------------------------------

class DEXPool:
    """A simplified constant-product AMM pool (x * y = k).

    Two tokens trade against each other. Price moves when trades occur,
    creating arbitrage opportunities between pools with the same pair.
    """

    def __init__(self, name, token_a, token_b, reserve_a, reserve_b):
        self.name = name
        self.token_a = token_a
        self.token_b = token_b
        self.reserve_a = reserve_a    # Amount of token A in the pool
        self.reserve_b = reserve_b    # Amount of token B in the pool

    @property
    def price_a_in_b(self):
        """Price of token A denominated in token B."""
        return self.reserve_b / self.reserve_a

    @property
    def price_b_in_a(self):
        """Price of token B denominated in token A."""
        return self.reserve_a / self.reserve_b

    def get_amount_out(self, amount_in, token_in):
        """Calculate output amount using constant-product formula: x * y = k.

        Uses the standard AMM formula: amount_out = (amount_in * reserve_out) /
        (reserve_in + amount_in). No fees for simplicity.
        """
        if token_in == self.token_a:
            reserve_in, reserve_out = self.reserve_a, self.reserve_b
        else:
            reserve_in, reserve_out = self.reserve_b, self.reserve_a

        # Constant-product swap formula — ensures k never decreases
        amount_out = (amount_in * reserve_out) / (reserve_in + amount_in)
        return amount_out

    def execute_swap(self, amount_in, token_in):
        """Execute a swap, updating reserves. Returns amount received."""
        amount_out = self.get_amount_out(amount_in, token_in)

        if token_in == self.token_a:
            self.reserve_a += amount_in      # Pool receives token A
            self.reserve_b -= amount_out     # Pool gives out token B
        else:
            self.reserve_b += amount_in      # Pool receives token B
            self.reserve_a -= amount_out     # Pool gives out token A

        return amount_out

    def __repr__(self):
        return (f"DEXPool({self.name}: {self.reserve_a:.2f} {self.token_a} / "
                f"{self.reserve_b:.2f} {self.token_b})")


# ----------------------------------------------------------------------------
# 2b: Transaction — represents a single Solana transaction in a bundle
# ----------------------------------------------------------------------------

class Transaction:
    """A simplified Solana transaction for MEV simulation."""

    def __init__(self, sender, tx_type, details, fee_lamports=5000):
        self.sender = sender
        self.tx_type = tx_type          # "swap", "backrun", "tip", etc.
        self.details = details          # Dict with transaction-specific data
        self.fee_lamports = fee_lamports  # Base transaction fee
        # Hash serves as the transaction signature
        self.signature = self._compute_signature()

    def _compute_signature(self):
        """Compute a deterministic 'signature' for this transaction."""
        data = f"{self.sender}:{self.tx_type}:{self.details}:{self.fee_lamports}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def __repr__(self):
        return f"Tx({self.tx_type} by {self.sender} [{self.signature}])"


# ----------------------------------------------------------------------------
# 2c: Bundle — an atomic group of ordered transactions
# ----------------------------------------------------------------------------

class Bundle:
    """A Jito bundle: ordered transactions executed atomically.

    If ANY transaction in the bundle fails, the ENTIRE bundle is reverted.
    This guarantees searchers only pay tips when their strategy succeeds.
    """

    def __init__(self, searcher, transactions, tip_lamports):
        if len(transactions) > MAX_BUNDLE_SIZE:
            raise ValueError(f"Bundle exceeds max size of {MAX_BUNDLE_SIZE}")
        if tip_lamports < MIN_TIP_LAMPORTS:
            raise ValueError(f"Tip {tip_lamports} below minimum {MIN_TIP_LAMPORTS}")

        self.searcher = searcher
        self.transactions = transactions  # Ordered list — execution order matters
        self.tip_lamports = tip_lamports  # Tip paid to validator for inclusion
        self.bundle_id = self._compute_id()
        self.status = "pending"           # pending → won/lost → executed/reverted

    def _compute_id(self):
        """Bundle ID is a hash of all transaction signatures."""
        sigs = ":".join(tx.signature for tx in self.transactions)
        return hashlib.sha256(sigs.encode()).hexdigest()[:12]

    @property
    def total_cost(self):
        """Total cost = sum of base fees + tip."""
        base_fees = sum(tx.fee_lamports for tx in self.transactions)
        return base_fees + self.tip_lamports

    def __repr__(self):
        return (f"Bundle({self.bundle_id} by {self.searcher}, "
                f"{len(self.transactions)} txs, tip={self.tip_lamports})")


# ----------------------------------------------------------------------------
# 2d: Tip account — one of Jito's 8 rotating tip accounts
# ----------------------------------------------------------------------------

class TipAccount:
    """A Jito tip account that collects tips from winning bundles.

    Tips accumulate here and are distributed to the validator at epoch end.
    Multiple tip accounts prevent contention — searchers pick one at random.
    """

    def __init__(self, index):
        # Generate a deterministic "address" for this tip account
        seed = f"jito-tip-account-{index}"
        self.address = hashlib.sha256(seed.encode()).hexdigest()[:12]
        self.balance_lamports = 0    # Accumulated tips
        self.index = index

    def deposit(self, amount_lamports):
        """Deposit a tip into this account."""
        self.balance_lamports += amount_lamports

    def drain(self):
        """Drain all tips — called when distributing to the validator."""
        amount = self.balance_lamports
        self.balance_lamports = 0
        return amount


# ----------------------------------------------------------------------------
# 2e: MEV opportunity detector — finds arbitrage between DEX pools
# ----------------------------------------------------------------------------

class MEVDetector:
    """Detects MEV opportunities by scanning DEX pool states.

    Looks for price discrepancies between pools trading the same pair.
    A discrepancy means buying cheap on one pool and selling high on another.
    """

    @staticmethod
    def find_arbitrage(pools):
        """Find arbitrage opportunities across pools with overlapping pairs.

        Returns a list of (pool_buy, pool_sell, token_path, profit_estimate).
        """
        opportunities = []

        # Compare every pair of pools for price discrepancies
        for i, pool_a in enumerate(pools):
            for pool_b in pools[i + 1:]:
                # Check if pools share the same token pair
                if (pool_a.token_a == pool_b.token_a and
                        pool_a.token_b == pool_b.token_b):
                    # Compare prices — buy where cheap, sell where expensive
                    price_a = pool_a.price_a_in_b  # Price of token A on pool A
                    price_b = pool_b.price_a_in_b  # Price of token A on pool B

                    if price_a < price_b:
                        # Token A is cheaper on pool A — buy there, sell on pool B
                        spread = (price_b - price_a) / price_a
                        if spread > 0.005:  # Only worth it if spread > 0.5%
                            opportunities.append({
                                "buy_pool": pool_a,
                                "sell_pool": pool_b,
                                "buy_token": pool_a.token_a,
                                "sell_token": pool_a.token_b,
                                "spread_pct": spread * 100,
                                "direction": f"Buy {pool_a.token_a} on {pool_a.name}, "
                                             f"sell on {pool_b.name}",
                            })
                    elif price_b < price_a:
                        spread = (price_a - price_b) / price_b
                        if spread > 0.005:
                            opportunities.append({
                                "buy_pool": pool_b,
                                "sell_pool": pool_a,
                                "buy_token": pool_b.token_a,
                                "sell_token": pool_b.token_b,
                                "spread_pct": spread * 100,
                                "direction": f"Buy {pool_b.token_a} on {pool_b.name}, "
                                             f"sell on {pool_a.name}",
                            })

        return opportunities


# ----------------------------------------------------------------------------
# 2f: Bundle auction — selects winning bundle per opportunity
# ----------------------------------------------------------------------------

class BundleAuction:
    """Jito's bundle auction: highest tip wins inclusion.

    When multiple searchers target the same opportunity, only the bundle
    with the highest tip gets included. Losers pay nothing (atomic bundles).
    """

    def __init__(self):
        self.pending_bundles = []    # All submitted bundles
        self.winning_bundles = []    # Bundles selected for inclusion

    def submit(self, bundle):
        """Submit a bundle to the auction."""
        self.pending_bundles.append(bundle)

    def run_auction(self):
        """Run the auction: group bundles by opportunity, pick highest tip.

        In reality, Jito groups bundles that touch the same accounts
        (conflicting bundles). Here we group by the opportunity they target.
        """
        # Group bundles by the opportunity they target (using the first tx details)
        groups = {}
        for bundle in self.pending_bundles:
            # Use the first transaction's details as the opportunity key
            opp_key = bundle.transactions[0].details.get("opportunity", "unknown")
            if opp_key not in groups:
                groups[opp_key] = []
            groups[opp_key].append(bundle)

        results = []
        for opp_key, bundles in groups.items():
            # Sort by tip — highest tip wins
            bundles.sort(key=lambda b: b.tip_lamports, reverse=True)
            winner = bundles[0]
            winner.status = "won"
            self.winning_bundles.append(winner)

            # Mark losers — they pay nothing since bundles are atomic
            for loser in bundles[1:]:
                loser.status = "lost"

            results.append({
                "opportunity": opp_key,
                "winner": winner,
                "losers": bundles[1:],
                "competing_tips": [b.tip_lamports for b in bundles],
            })

        return results


# ----------------------------------------------------------------------------
# 2g: Jito validator — processes bundles and normal transactions
# ----------------------------------------------------------------------------

class JitoValidator:
    """A Solana validator running Jito's modified client.

    Processes both normal transactions and Jito bundles, inserting winning
    bundles into the block at optimal positions. Tips flow to the validator
    as additional revenue beyond normal block rewards.
    """

    def __init__(self, name):
        self.name = name
        self.tip_accounts = [TipAccount(i) for i in range(NUM_TIP_ACCOUNTS)]
        self.blocks_produced = []
        self.total_tips_earned = 0

    def select_tip_account(self):
        """Pick a random tip account — distributes load across accounts."""
        return random.choice(self.tip_accounts)

    def produce_block(self, normal_txs, winning_bundles):
        """Produce a block containing normal txs and winning bundles.

        Bundles are placed first (they have priority due to tips),
        then remaining block space is filled with normal transactions.
        """
        block_txs = []
        capacity_remaining = BLOCK_CAPACITY

        # Insert winning bundles first — they paid for priority
        for bundle in winning_bundles:
            bundle_size = len(bundle.transactions)
            if bundle_size <= capacity_remaining:
                # Add all bundle transactions in order (atomicity)
                for tx in bundle.transactions:
                    block_txs.append(tx)
                capacity_remaining -= bundle_size

                # Record the tip — deposit into a tip account
                tip_account = self.select_tip_account()
                tip_account.deposit(bundle.tip_lamports)
                self.total_tips_earned += bundle.tip_lamports
                bundle.status = "executed"

        # Fill remaining space with normal transactions
        for tx in normal_txs:
            if capacity_remaining <= 0:
                break
            block_txs.append(tx)
            capacity_remaining -= 1

        block = {
            "slot": len(self.blocks_produced),
            "transactions": block_txs,
            "bundle_count": len(winning_bundles),
            "total_txs": len(block_txs),
            "tips_earned": sum(b.tip_lamports for b in winning_bundles),
        }
        self.blocks_produced.append(block)
        return block

    def collect_all_tips(self):
        """Drain all tip accounts — called at epoch end."""
        total = sum(account.drain() for account in self.tip_accounts)
        return total


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Jito MEV bundles."""
    random.seed(RANDOM_SEED)

    print("=" * 72)
    print("  JITO MEV BUNDLES — Solana's MEV Extraction Infrastructure")
    print("=" * 72)

    # --- Step 1: Set up DEX pools with a price discrepancy ---
    print("\n─── Step 1: DEX Pool Setup ─────────────────────────────────────────")
    print("Creating AMM pools with price discrepancies for arbitrage...\n")

    pools = [
        DEXPool("Raydium", "SOL", "USDC", 10_000, 1_500_000),   # 150 USDC/SOL
        DEXPool("Orca", "SOL", "USDC", 10_000, 1_580_000),      # 158 USDC/SOL
        DEXPool("Jupiter", "SOL", "USDC", 10_000, 1_520_000),   # 152 USDC/SOL
    ]

    for pool in pools:
        price = pool.price_a_in_b
        print(f"  ┌─────────────────────────────────────────┐")
        print(f"  │ {pool.name:>10}  │  {pool.token_a}/{pool.token_b}  "
              f"│  Price: ${price:.2f}  │")
        print(f"  │  Reserves: {pool.reserve_a:,.0f} {pool.token_a} / "
              f"{pool.reserve_b:,.0f} {pool.token_b}     │")
        print(f"  └─────────────────────────────────────────┘")

    # --- Step 2: Detect arbitrage opportunities ---
    print("\n─── Step 2: MEV Opportunity Detection ──────────────────────────────")
    print("Scanning for price discrepancies across DEX pools...\n")

    opportunities = MEVDetector.find_arbitrage(pools)

    for i, opp in enumerate(opportunities):
        print(f"  Opportunity #{i + 1}:")
        print(f"    Direction: {opp['direction']}")
        print(f"    Spread:    {opp['spread_pct']:.2f}%")
        print(f"    Buy pool:  {opp['buy_pool'].name} "
              f"(${opp['buy_pool'].price_a_in_b:.2f})")
        print(f"    Sell pool: {opp['sell_pool'].name} "
              f"(${opp['sell_pool'].price_a_in_b:.2f})")
        print()

    # --- Step 3: Searchers construct bundles ---
    print("─── Step 3: Searcher Bundle Construction ────────────────────────────")
    print(f"{NUM_SEARCHERS} searchers spotted the same opportunity and compete...\n")

    auction = BundleAuction()

    # Use the best opportunity (largest spread)
    best_opp = max(opportunities, key=lambda o: o["spread_pct"])

    # Each searcher constructs a bundle with different trade size and tip
    searcher_configs = [
        ("AlphaBot", 100, 500_000),      # Trades 100 SOL, tips 0.0005 SOL
        ("FlashArb", 200, 1_200_000),    # Trades 200 SOL, tips 0.0012 SOL
        ("MEVKing", 150, 2_500_000),     # Trades 150 SOL, tips 0.0025 SOL
        ("SpeedBot", 80, 800_000),       # Trades 80 SOL, tips 0.0008 SOL
        ("DarkPool", 300, 1_800_000),    # Trades 300 SOL, tips 0.0018 SOL
    ]

    for name, trade_size, tip in searcher_configs:
        # Transaction 1: Buy on the cheaper pool
        buy_tx = Transaction(
            sender=name,
            tx_type="swap",
            details={
                "opportunity": "SOL-USDC-arb",
                "pool": best_opp["buy_pool"].name,
                "action": "buy",
                "amount": trade_size,
                "token": "SOL",
            }
        )

        # Transaction 2: Sell on the more expensive pool
        sell_tx = Transaction(
            sender=name,
            tx_type="swap",
            details={
                "opportunity": "SOL-USDC-arb",
                "pool": best_opp["sell_pool"].name,
                "action": "sell",
                "amount": trade_size,
                "token": "SOL",
            }
        )

        # Transaction 3: Tip the validator via Jito tip account
        tip_tx = Transaction(
            sender=name,
            tx_type="tip",
            details={
                "opportunity": "SOL-USDC-arb",
                "tip_lamports": tip,
            }
        )

        bundle = Bundle(name, [buy_tx, sell_tx, tip_tx], tip)
        auction.submit(bundle)

        tip_sol = tip / LAMPORTS_PER_SOL
        print(f"  {name:>10} → Bundle {bundle.bundle_id}")
        print(f"              Trade: {trade_size} SOL arb, "
              f"Tip: {tip:>12,} lamports ({tip_sol:.6f} SOL)")

    # --- Step 4: Run the auction ---
    print("\n─── Step 4: Bundle Auction ──────────────────────────────────────────")
    print("Jito engine selects the highest-tipping bundle per opportunity...\n")

    results = auction.run_auction()

    for result in results:
        winner = result["winner"]
        tips = result["competing_tips"]
        winner_tip_sol = winner.tip_lamports / LAMPORTS_PER_SOL

        print(f"  Opportunity: {result['opportunity']}")
        print(f"  ┌─────────────────────────────────────────────────────┐")
        print(f"  │  WINNER: {winner.searcher:<12}                       │")
        print(f"  │  Tip:    {winner.tip_lamports:>12,} lamports "
              f"({winner_tip_sol:.6f} SOL)  │")
        print(f"  │  Txs:    {len(winner.transactions)} transactions "
              f"(atomic bundle)          │")
        print(f"  └─────────────────────────────────────────────────────┘")

        print(f"\n  Auction results (sorted by tip, descending):")
        for i, (bundle_tip, bundle) in enumerate(
                sorted(zip(tips, auction.pending_bundles),
                       key=lambda x: x[0], reverse=True)):
            status_icon = "★" if bundle.status == "won" else " "
            tip_sol = bundle_tip / LAMPORTS_PER_SOL
            print(f"    {status_icon} {bundle.searcher:>10}: "
                  f"{bundle_tip:>12,} lamports ({tip_sol:.6f} SOL) "
                  f"[{bundle.status}]")

    # --- Step 5: Validator produces block with winning bundle ---
    print("\n─── Step 5: Block Production ────────────────────────────────────────")
    print("Leader validator includes winning bundle in the block...\n")

    validator = JitoValidator("ValidatorA")

    # Create some normal transactions
    normal_txs = [
        Transaction(f"User{i}", "transfer",
                    {"from": f"User{i}", "to": f"User{i + 1}", "amount": 1.0})
        for i in range(10)
    ]

    block = validator.produce_block(normal_txs, auction.winning_bundles)

    print(f"  Block #{block['slot']}:")
    print(f"  ┌─────────────────────────────────────────────────────┐")
    print(f"  │  Total transactions:   {block['total_txs']:>3}                         │")
    print(f"  │  Bundle transactions:  {block['bundle_count'] * 3:>3} "
          f"({block['bundle_count']} bundle{'s' if block['bundle_count'] > 1 else ''})     "
          f"             │")
    print(f"  │  Normal transactions:  "
          f"{block['total_txs'] - block['bundle_count'] * 3:>3}                         │")
    tip_sol = block['tips_earned'] / LAMPORTS_PER_SOL
    print(f"  │  Tips earned:          {block['tips_earned']:>12,} lamports     │")
    print(f"  │                        ({tip_sol:.6f} SOL)             │")
    print(f"  └─────────────────────────────────────────────────────┘")

    print(f"\n  Transaction order in block:")
    for i, tx in enumerate(block["transactions"]):
        marker = "BUNDLE" if tx.tx_type in ("swap", "tip") else "normal"
        print(f"    [{i:>2}] {marker:>6} │ {tx.tx_type:>8} │ {tx.sender:>10} │ "
              f"{tx.signature}")

    # --- Step 6: Tip distribution summary ---
    print("\n─── Step 6: Validator Revenue Summary ──────────────────────────────")
    print("Tips collected across all tip accounts:\n")

    for account in validator.tip_accounts:
        bar_len = account.balance_lamports // 100_000
        bar = "█" * bar_len if bar_len > 0 else ""
        if account.balance_lamports > 0:
            print(f"  Tip Account {account.index} [{account.address}]: "
                  f"{account.balance_lamports:>12,} lamports {bar}")

    total_tips = validator.total_tips_earned
    total_sol = total_tips / LAMPORTS_PER_SOL
    print(f"\n  Total validator MEV revenue: {total_tips:,} lamports "
          f"({total_sol:.6f} SOL)")

    # --- Step 7: Backrun opportunity demonstration ---
    print("\n─── Step 7: Backrun Opportunity ─────────────────────────────────────")
    print("A large user swap creates a backrun opportunity...\n")

    # Simulate a large user swap that moves the price
    user_pool = DEXPool("Raydium-v2", "SOL", "USDC", 10_000, 1_500_000)
    price_before = user_pool.price_a_in_b

    print(f"  Pool price before user swap: ${price_before:.2f}")

    # User buys 500 SOL — this moves the price significantly
    user_amount = 500
    usdc_cost = user_pool.get_amount_out(user_amount, "SOL")
    user_pool.execute_swap(user_amount, "SOL")  # This is a buy of SOL with USDC direction

    # Actually let's simulate: user sells 500 SOL for USDC
    user_pool2 = DEXPool("Raydium-v2", "SOL", "USDC", 10_000, 1_500_000)
    user_sells_sol = 500
    usdc_received = user_pool2.execute_swap(user_sells_sol, "SOL")
    price_after = user_pool2.price_a_in_b

    print(f"  User sells {user_sells_sol} SOL → receives {usdc_received:,.2f} USDC")
    print(f"  Pool price after user swap:  ${price_after:.2f}")
    print(f"  Price impact: {((price_after - price_before) / price_before) * 100:.2f}%")

    # Searcher backruns — buys SOL cheap after the price dropped
    arb_pool = DEXPool("Orca-v2", "SOL", "USDC", 10_000, 1_500_000)
    arb_price = arb_pool.price_a_in_b

    print(f"\n  Arbitrage pool (Orca-v2) price: ${arb_price:.2f}")
    print(f"  Spread after user trade: "
          f"{((arb_price - price_after) / price_after) * 100:.2f}%")

    # Searcher buys on Raydium (cheaper after user's sell), sells on Orca
    backrun_amount = 100  # SOL
    # Buy SOL on Raydium-v2 (now cheaper) using USDC
    cost_usdc = user_pool2.get_amount_out(backrun_amount * price_after, "USDC")
    # Sell SOL on Orca (still at original price) for USDC
    revenue_usdc = arb_pool.get_amount_out(backrun_amount, "SOL")
    profit_usdc = revenue_usdc - (backrun_amount * price_after)

    print(f"\n  Backrun strategy:")
    print(f"    Buy  {backrun_amount} SOL on Raydium-v2 at ~${price_after:.2f}")
    print(f"    Sell {backrun_amount} SOL on Orca-v2    at ~${arb_price:.2f}")
    print(f"    Estimated profit: ~${profit_usdc:.2f} USDC")

    bundle_txs = [
        Transaction("BackrunBot", "swap",
                    {"opportunity": "backrun", "action": "buy",
                     "pool": "Raydium-v2"}),
        Transaction("BackrunBot", "swap",
                    {"opportunity": "backrun", "action": "sell",
                     "pool": "Orca-v2"}),
        Transaction("BackrunBot", "tip",
                    {"opportunity": "backrun", "tip_lamports": 500_000}),
    ]
    backrun_bundle = Bundle("BackrunBot", bundle_txs, 500_000)

    print(f"\n  Backrun bundle: {backrun_bundle.bundle_id}")
    print(f"    Transactions: {len(backrun_bundle.transactions)}")
    print(f"    Tip:          {backrun_bundle.tip_lamports:,} lamports")
    print(f"    Status:       Atomic — if arb fails, tip is NOT paid")

    print("\n" + "=" * 72)
    print("  KEY TAKEAWAYS")
    print("=" * 72)
    print("  1. Bundles are atomic: all-or-nothing execution protects searchers")
    print("  2. Highest tip wins: fair auction mechanism for MEV extraction")
    print("  3. Validators earn extra: tips supplement normal block rewards")
    print("  4. Backruns are common: large swaps create predictable arb")
    print("  5. MEV is a feature: Jito channels it through a structured system")
    print("=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
