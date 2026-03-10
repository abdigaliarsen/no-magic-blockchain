"""
TITLE: MEV & Flashbots (Maximal Extractable Value)
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    A simulation of Maximal Extractable Value (MEV) extraction on Ethereum — the
    profit miners/validators can capture by reordering, inserting, or censoring
    transactions. Implements a mempool, sandwich attacks on DEX swaps, a multi-builder
    block auction, and Proposer-Builder Separation (PBS).

KEY CONCEPTS:
    - MEV: profit from transaction ordering within a block
    - Sandwich attack: frontrun + backrun a large swap to extract price impact
    - Block builder auction: builders compete to produce the most valuable block
    - Proposer-Builder Separation (PBS): proposer selects sealed block by bid

PREREQUISITE SCRIPTS:
    - core/fundamentals/05_blockchain.py (block structure)
    - ethereum/fundamentals/01_accounts_state.py (accounts and state)
    - ethereum/fundamentals/03_gas_execution.py (gas and EIP-1559)

REAL-WORLD RELEVANCE:
    MEV is one of Ethereum's most critical economic forces — over $600M has been
    extracted since 2020. Flashbots and PBS (enshrined in the roadmap via ePBS)
    aim to democratize MEV extraction, reduce harmful MEV (sandwich attacks), and
    prevent validator centralization.
"""

import hashlib
import random
import time

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Simulated token prices for a simple constant-product AMM (x * y = k)
INITIAL_ETH_RESERVE = 10_000   # ETH in the liquidity pool
INITIAL_TOKEN_RESERVE = 20_000_000  # TOKEN in the pool

# Gas costs for different transaction types
BASE_GAS = 21_000        # Simple transfer
SWAP_GAS = 150_000        # DEX swap
BUNDLE_OVERHEAD_GAS = 5_000  # Extra gas for bundle coordination

# Block gas limit
BLOCK_GAS_LIMIT = 30_000_000

# Base fee parameters (simplified EIP-1559)
BASE_FEE_GWEI = 20  # Current base fee in Gwei
GWEI = 10**9         # 1 Gwei in Wei

# Seed for reproducibility
random.seed(42)


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# Constant-Product AMM (simplified Uniswap v2)
# ----------------------------------------------------------------------------

class AMM:
    """A constant-product automated market maker: x * y = k.

    This is the simplest DEX model — the product of reserves stays constant,
    meaning large trades create price impact (slippage).
    """

    def __init__(self, eth_reserve: int, token_reserve: int):
        self.eth_reserve = eth_reserve
        self.token_reserve = token_reserve
        self.k = eth_reserve * token_reserve  # Invariant: must stay constant

    def price(self) -> float:
        """Current marginal price: how many tokens per 1 ETH."""
        return self.token_reserve / self.eth_reserve

    def quote_buy_tokens(self, eth_in: int) -> int:
        """Calculate tokens received for `eth_in` ETH (before fees).

        Uses the constant-product formula: new_token_reserve = k / new_eth_reserve
        The difference is how many tokens the buyer gets.
        """
        new_eth = self.eth_reserve + eth_in
        new_token = self.k // new_eth  # Integer division — rounds down
        tokens_out = self.token_reserve - new_token
        return tokens_out

    def quote_sell_tokens(self, tokens_in: int) -> int:
        """Calculate ETH received for selling `tokens_in` tokens."""
        new_token = self.token_reserve + tokens_in
        new_eth = self.k // new_token
        eth_out = self.eth_reserve - new_eth
        return eth_out

    def execute_buy(self, eth_in: int) -> int:
        """Buy tokens with ETH — mutates reserves."""
        tokens_out = self.quote_buy_tokens(eth_in)
        self.eth_reserve += eth_in
        self.token_reserve -= tokens_out
        self.k = self.eth_reserve * self.token_reserve  # Recompute k (rounding)
        return tokens_out

    def execute_sell(self, tokens_in: int) -> int:
        """Sell tokens for ETH — mutates reserves."""
        eth_out = self.quote_sell_tokens(tokens_in)
        self.token_reserve += tokens_in
        self.eth_reserve -= eth_out
        self.k = self.eth_reserve * self.token_reserve
        return eth_out

    def snapshot(self) -> dict:
        """Capture current state for later comparison."""
        return {
            "eth_reserve": self.eth_reserve,
            "token_reserve": self.token_reserve,
            "price": self.price(),
        }


# ----------------------------------------------------------------------------
# Transaction types
# ----------------------------------------------------------------------------

class Transaction:
    """A pending transaction in the mempool."""

    def __init__(self, sender: str, tx_type: str, params: dict,
                 max_priority_fee: int = 2, max_fee: int = 50,
                 gas_limit: int = BASE_GAS):
        self.sender = sender
        self.tx_type = tx_type          # "transfer", "swap_buy", "swap_sell"
        self.params = params            # Type-specific parameters
        self.max_priority_fee = max_priority_fee  # Gwei — tip to validator
        self.max_fee = max_fee          # Gwei — max total fee
        self.gas_limit = gas_limit
        self.nonce = random.randint(0, 1000)
        # Compute a deterministic hash for this transaction
        self.tx_hash = hashlib.sha256(
            f"{sender}{tx_type}{params}{self.nonce}{time.time_ns()}".encode()
        ).hexdigest()[:16]

    def effective_priority_fee(self, base_fee: int) -> int:
        """Actual priority fee paid: min(max_priority, max_fee - base_fee)."""
        return min(self.max_priority_fee, self.max_fee - base_fee)

    def __repr__(self) -> str:
        return f"Tx({self.tx_hash}: {self.sender} {self.tx_type})"


# ----------------------------------------------------------------------------
# Mempool
# ----------------------------------------------------------------------------

class Mempool:
    """Public mempool — all pending transactions are visible to everyone.

    This visibility is what makes MEV possible: searchers can see pending swaps
    and craft transactions that exploit the ordering.
    """

    def __init__(self):
        self.pending: list[Transaction] = []

    def submit(self, tx: Transaction):
        """Add a transaction to the mempool."""
        self.pending.append(tx)

    def get_all(self) -> list[Transaction]:
        """Return all pending transactions (public visibility)."""
        return list(self.pending)

    def remove(self, tx_hashes: set[str]):
        """Remove transactions that were included in a block."""
        self.pending = [tx for tx in self.pending if tx.tx_hash not in tx_hashes]


# ----------------------------------------------------------------------------
# MEV Searcher — sandwich attack
# ----------------------------------------------------------------------------

class Searcher:
    """An MEV searcher that monitors the mempool for profitable opportunities.

    A sandwich attack works by:
    1. FRONTRUN: Buy tokens before the victim's large buy (pushing price up)
    2. VICTIM: The victim's buy executes at a worse price
    3. BACKRUN: Sell the tokens bought in step 1 at the now-higher price
    """

    def __init__(self, name: str, capital_eth: int):
        self.name = name
        self.capital_eth = capital_eth  # ETH available for MEV extraction

    def find_sandwich_opportunities(self, mempool: Mempool,
                                     amm: AMM) -> list[dict]:
        """Scan mempool for large swaps that can be sandwiched profitably."""
        opportunities = []
        for tx in mempool.get_all():
            if tx.tx_type != "swap_buy":
                continue  # Only sandwich buy orders

            eth_amount = tx.params.get("eth_amount", 0)
            # Only target swaps large enough to create meaningful price impact
            if eth_amount < amm.eth_reserve * 0.005:  # >0.5% of pool
                continue

            # Simulate the sandwich to estimate profit
            profit = self._simulate_sandwich(amm, eth_amount)
            if profit > 0:
                opportunities.append({
                    "victim_tx": tx,
                    "victim_eth": eth_amount,
                    "estimated_profit_eth": profit,
                })
        return opportunities

    def _simulate_sandwich(self, amm: AMM, victim_eth: int) -> int:
        """Simulate a sandwich attack without mutating the real AMM.

        Returns estimated profit in ETH.
        """
        # Save state
        saved = (amm.eth_reserve, amm.token_reserve, amm.k)

        # Step 1: Frontrun — buy tokens with our capital
        frontrun_eth = min(self.capital_eth, victim_eth // 2)
        tokens_bought = amm.execute_buy(frontrun_eth)

        # Step 2: Victim's trade executes at the now-worse price
        amm.execute_buy(victim_eth)

        # Step 3: Backrun — sell our tokens at the inflated price
        eth_received = amm.execute_sell(tokens_bought)

        # Profit = ETH received - ETH spent
        profit = eth_received - frontrun_eth

        # Restore AMM state
        amm.eth_reserve, amm.token_reserve, amm.k = saved
        return profit

    def build_sandwich_bundle(self, victim_tx: Transaction,
                               amm: AMM) -> list[Transaction]:
        """Create a bundle of 3 transactions: frontrun + victim + backrun.

        Bundles are submitted atomically — all execute or none do.
        """
        victim_eth = victim_tx.params["eth_amount"]
        frontrun_eth = min(self.capital_eth, victim_eth // 2)

        # Frontrun transaction — high priority to get in first
        frontrun = Transaction(
            sender=f"searcher:{self.name}",
            tx_type="swap_buy",
            params={"eth_amount": frontrun_eth},
            max_priority_fee=100,  # Very high tip to guarantee ordering
            gas_limit=SWAP_GAS,
        )

        # Backrun transaction — must execute right after victim
        backrun = Transaction(
            sender=f"searcher:{self.name}",
            tx_type="swap_sell",
            params={"sell_after_frontrun": True, "frontrun_eth": frontrun_eth},
            max_priority_fee=100,
            gas_limit=SWAP_GAS,
        )

        # Bundle: frontrun → victim → backrun (strict ordering)
        return [frontrun, victim_tx, backrun]


# ----------------------------------------------------------------------------
# Block Builder
# ----------------------------------------------------------------------------

class BlockBuilder:
    """A block builder that orders transactions to maximize value.

    In PBS, builders compete to produce the most valuable block. They include
    MEV bundles, order by priority fee, and submit a bid to the proposer.
    """

    def __init__(self, name: str):
        self.name = name

    def build_block(self, mempool: Mempool, bundles: list[list[Transaction]],
                    base_fee: int) -> dict:
        """Build a block by ordering transactions to maximize total fees + MEV.

        Returns a sealed block with a bid amount.
        """
        block_txs: list[Transaction] = []
        gas_used = 0
        total_priority_fees = 0
        included_hashes: set[str] = set()

        # Step 1: Include bundles first (they pay high tips and contain MEV)
        for bundle in bundles:
            bundle_gas = sum(tx.gas_limit for tx in bundle)
            if gas_used + bundle_gas <= BLOCK_GAS_LIMIT:
                for tx in bundle:
                    block_txs.append(tx)
                    included_hashes.add(tx.tx_hash)
                    fee = tx.effective_priority_fee(base_fee)
                    total_priority_fees += fee * tx.gas_limit
                gas_used += bundle_gas

        # Step 2: Fill remaining space with highest-priority mempool txs
        remaining = [tx for tx in mempool.get_all()
                     if tx.tx_hash not in included_hashes]
        # Sort by effective priority fee (highest first)
        remaining.sort(
            key=lambda tx: tx.effective_priority_fee(base_fee),
            reverse=True,
        )
        for tx in remaining:
            if gas_used + tx.gas_limit <= BLOCK_GAS_LIMIT:
                block_txs.append(tx)
                included_hashes.add(tx.tx_hash)
                fee = tx.effective_priority_fee(base_fee)
                total_priority_fees += fee * tx.gas_limit
                gas_used += tx.gas_limit

        # Builder's bid to the proposer — a share of total value extracted
        # In practice, builders bid most of their profit to stay competitive
        bid = total_priority_fees * 9 // 10  # Keep 10% margin

        return {
            "builder": self.name,
            "transactions": block_txs,
            "gas_used": gas_used,
            "total_priority_fees_gwei": total_priority_fees,
            "bid_gwei": bid,
            "tx_count": len(block_txs),
        }


# ----------------------------------------------------------------------------
# Proposer (Validator)
# ----------------------------------------------------------------------------

class Proposer:
    """A block proposer in PBS — selects the highest-bid block.

    The proposer does NOT see transaction contents — only the bid amount.
    This separation prevents proposers from stealing MEV.
    """

    def __init__(self, name: str):
        self.name = name

    def select_block(self, builder_blocks: list[dict]) -> dict:
        """Select the block with the highest bid (sealed — contents hidden)."""
        # Sort by bid descending, pick the winner
        builder_blocks.sort(key=lambda b: b["bid_gwei"], reverse=True)
        winner = builder_blocks[0]
        return winner


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of MEV extraction and PBS."""

    print("=" * 72)
    print("  MEV & FLASHBOTS — Maximal Extractable Value on Ethereum")
    print("=" * 72)

    # --- Part 1: Mempool and AMM Setup ---
    print("\n--- Part 1: DEX Pool & Mempool ---\n")

    amm = AMM(INITIAL_ETH_RESERVE, INITIAL_TOKEN_RESERVE)
    mempool = Mempool()

    print(f"  Constant-Product AMM (x * y = k)")
    print(f"  ┌──────────────────────────────────────────┐")
    print(f"  │ ETH Reserve:   {amm.eth_reserve:>12,} ETH          │")
    print(f"  │ TOKEN Reserve: {amm.token_reserve:>12,} TOKEN        │")
    print(f"  │ Price:         {amm.price():>12,.2f} TOKEN/ETH    │")
    print(f"  │ k (invariant): {amm.k:>12,}              │")
    print(f"  └──────────────────────────────────────────┘")

    # Simulate users submitting transactions to the public mempool
    user_txs = [
        Transaction("alice", "transfer", {"to": "bob", "amount": 1},
                    max_priority_fee=2, gas_limit=BASE_GAS),
        Transaction("bob", "swap_buy", {"eth_amount": 200},   # Large swap!
                    max_priority_fee=3, gas_limit=SWAP_GAS),
        Transaction("carol", "swap_buy", {"eth_amount": 10},  # Small swap
                    max_priority_fee=5, gas_limit=SWAP_GAS),
        Transaction("dave", "transfer", {"to": "eve", "amount": 5},
                    max_priority_fee=1, gas_limit=BASE_GAS),
        Transaction("eve", "swap_buy", {"eth_amount": 500},   # Very large!
                    max_priority_fee=4, gas_limit=SWAP_GAS),
    ]

    for tx in user_txs:
        mempool.submit(tx)

    print(f"\n  Public Mempool ({len(mempool.pending)} pending transactions):")
    print(f"  {'Hash':<18} {'Sender':<10} {'Type':<12} {'Tip':>6} {'Details'}")
    print(f"  {'─' * 18} {'─' * 10} {'─' * 12} {'─' * 6} {'─' * 20}")
    for tx in mempool.get_all():
        detail = ""
        if tx.tx_type == "swap_buy":
            detail = f"{tx.params['eth_amount']} ETH -> TOKEN"
        elif tx.tx_type == "transfer":
            detail = f"{tx.params['amount']} ETH to {tx.params['to']}"
        print(f"  {tx.tx_hash:<18} {tx.sender:<10} {tx.tx_type:<12} "
              f"{tx.max_priority_fee:>4}  {detail}")

    # --- Part 2: Sandwich Attack ---
    print("\n\n--- Part 2: Sandwich Attack ---\n")

    searcher = Searcher("MEVBot", capital_eth=300)

    opps = searcher.find_sandwich_opportunities(mempool, amm)
    print(f"  Searcher '{searcher.name}' scanning mempool...")
    print(f"  Found {len(opps)} sandwich opportunity(ies):\n")

    for i, opp in enumerate(opps):
        vtx = opp["victim_tx"]
        print(f"  Opportunity #{i + 1}:")
        print(f"  ┌─────────────────────────────────────────────────────┐")
        print(f"  │ Victim: {vtx.sender:<10} buying with "
              f"{opp['victim_eth']:>6} ETH              │")
        print(f"  │ Est. profit: {opp['estimated_profit_eth']:>6} ETH"
              f"                              │")
        print(f"  └─────────────────────────────────────────────────────┘")

    # Execute the most profitable sandwich
    if opps:
        best = max(opps, key=lambda o: o["estimated_profit_eth"])
        victim_tx = best["victim_tx"]

        print(f"\n  Executing sandwich on {victim_tx.sender}'s "
              f"{best['victim_eth']} ETH swap:\n")

        # Show step-by-step execution
        pre_price = amm.price()
        frontrun_eth = min(searcher.capital_eth, best["victim_eth"] // 2)

        # Step 1: Frontrun
        tokens_from_frontrun = amm.execute_buy(frontrun_eth)
        post_frontrun_price = amm.price()
        print(f"  Step 1 ─ FRONTRUN (searcher buys before victim)")
        print(f"    Spend: {frontrun_eth} ETH  ->  "
              f"Get: {tokens_from_frontrun:,} TOKEN")
        print(f"    Price: {pre_price:,.2f} -> {post_frontrun_price:,.2f} "
              f"TOKEN/ETH (+{(post_frontrun_price/pre_price - 1)*100:.2f}%)")

        # Step 2: Victim trade
        victim_eth = best["victim_eth"]
        tokens_victim = amm.execute_buy(victim_eth)
        post_victim_price = amm.price()
        # What victim WOULD have gotten without the sandwich
        fair_tokens = AMM(INITIAL_ETH_RESERVE, INITIAL_TOKEN_RESERVE).quote_buy_tokens(victim_eth)
        print(f"\n  Step 2 ─ VICTIM ({victim_tx.sender}'s swap executes)")
        print(f"    Spend: {victim_eth} ETH  ->  "
              f"Get: {tokens_victim:,} TOKEN")
        print(f"    Fair price would have given: {fair_tokens:,} TOKEN")
        print(f"    Victim lost: {fair_tokens - tokens_victim:,} TOKEN "
              f"({(1 - tokens_victim/fair_tokens)*100:.2f}% worse)")

        # Step 3: Backrun
        eth_from_backrun = amm.execute_sell(tokens_from_frontrun)
        post_backrun_price = amm.price()
        profit = eth_from_backrun - frontrun_eth
        print(f"\n  Step 3 ─ BACKRUN (searcher sells at inflated price)")
        print(f"    Sell: {tokens_from_frontrun:,} TOKEN  ->  "
              f"Get: {eth_from_backrun} ETH")
        print(f"    Price: {post_victim_price:,.2f} -> "
              f"{post_backrun_price:,.2f} TOKEN/ETH")

        print(f"\n  ┌─────────────────────────────────────────────────────┐")
        print(f"  │ SANDWICH RESULT                                     │")
        print(f"  │ Searcher profit: {profit:>8} ETH                    │")
        print(f"  │ Victim loss:     {fair_tokens - tokens_victim:>8,} TOKEN "
              f"(extra slippage)  │")
        print(f"  └─────────────────────────────────────────────────────┘")

    # --- Part 3: Block Builder Auction ---
    print("\n\n--- Part 3: Block Builder Auction (PBS) ---\n")

    # Reset AMM for clean builder comparison
    amm = AMM(INITIAL_ETH_RESERVE, INITIAL_TOKEN_RESERVE)

    # Create multiple builders with different strategies
    builders = [
        BlockBuilder("Flashbots"),
        BlockBuilder("BloXroute"),
        BlockBuilder("BuilderAI"),
    ]

    # Searcher creates bundles for each builder
    searcher2 = Searcher("Searcher1", capital_eth=200)
    bundles_for_builders: list[list[list[Transaction]]] = []

    # Each builder gets slightly different bundles (simulating exclusive order flow)
    for builder in builders:
        opp = searcher2.find_sandwich_opportunities(mempool, amm)
        builder_bundles = []
        for o in opp[:2]:  # Max 2 bundles per builder
            bundle = searcher2.build_sandwich_bundle(o["victim_tx"], amm)
            builder_bundles.append(bundle)
        # Add some randomness — not all builders get all bundles
        if random.random() > 0.3:
            bundles_for_builders.append(builder_bundles)
        else:
            bundles_for_builders.append(builder_bundles[:1])

    # Each builder constructs their best block
    builder_blocks = []
    for builder, bundles in zip(builders, bundles_for_builders):
        block = builder.build_block(mempool, bundles, BASE_FEE_GWEI)
        builder_blocks.append(block)

    print(f"  {len(builders)} builders competing to build the next block:\n")
    print(f"  {'Builder':<15} {'Txs':>5} {'Gas Used':>12} "
          f"{'Fees (Gwei)':>14} {'Bid (Gwei)':>14}")
    print(f"  {'─' * 15} {'─' * 5} {'─' * 12} {'─' * 14} {'─' * 14}")
    for block in builder_blocks:
        print(f"  {block['builder']:<15} {block['tx_count']:>5} "
              f"{block['gas_used']:>12,} {block['total_priority_fees_gwei']:>14,} "
              f"{block['bid_gwei']:>14,}")

    # --- Part 4: Proposer-Builder Separation ---
    print("\n\n--- Part 4: Proposer-Builder Separation (PBS) ---\n")

    proposer = Proposer("Validator_42")
    winning_block = proposer.select_block(builder_blocks)

    print(f"  Proposer '{proposer.name}' receives sealed bids:")
    print()
    for block in sorted(builder_blocks, key=lambda b: b["bid_gwei"], reverse=True):
        marker = " <-- WINNER" if block["builder"] == winning_block["builder"] else ""
        print(f"    [{block['builder']:<12}] bid: {block['bid_gwei']:>12,} Gwei{marker}")

    print(f"\n  PBS Flow:")
    print(f"  ┌────────────┐    sealed bids    ┌────────────┐")
    print(f"  │  Builder 1 │───────────────────>│            │")
    print(f"  └────────────┘                    │            │")
    print(f"  ┌────────────┐    sealed bids    │  Proposer  │")
    print(f"  │  Builder 2 │───────────────────>│  (picks    │")
    print(f"  └────────────┘                    │   highest  │")
    print(f"  ┌────────────┐    sealed bids    │   bid)     │")
    print(f"  │  Builder 3 │───────────────────>│            │")
    print(f"  └────────────┘                    └─────┬──────┘")
    print(f"                                          │")
    print(f"                                          ▼")
    print(f"                                   ┌────────────┐")
    print(f"                                   │  Winning   │")
    print(f"                                   │  Block     │")
    print(f"                                   │  (sealed)  │")
    print(f"                                   └────────────┘")

    print(f"\n  Winner: {winning_block['builder']} "
          f"(bid {winning_block['bid_gwei']:,} Gwei)")
    print(f"  The proposer CANNOT see or reorder transactions inside the block.")
    print(f"  This prevents proposers from stealing MEV from searchers/builders.")

    # --- Part 5: Fair Ordering Comparison ---
    print("\n\n--- Part 5: MEV Extraction vs Fair Ordering ---\n")

    amm_fair = AMM(INITIAL_ETH_RESERVE, INITIAL_TOKEN_RESERVE)
    amm_mev = AMM(INITIAL_ETH_RESERVE, INITIAL_TOKEN_RESERVE)

    # Fair ordering: process swaps in arrival order (FIFO)
    swap_txs = [tx for tx in user_txs if tx.tx_type == "swap_buy"]
    fair_results = []
    for tx in swap_txs:
        eth = tx.params["eth_amount"]
        tokens = amm_fair.execute_buy(eth)
        fair_results.append((tx.sender, eth, tokens))

    # MEV ordering: searcher sandwiches the largest swap
    mev_results = []
    largest_swap = max(swap_txs, key=lambda t: t.params["eth_amount"])
    for tx in swap_txs:
        eth = tx.params["eth_amount"]
        if tx is largest_swap:
            # Frontrun
            front_tokens = amm_mev.execute_buy(200)  # Searcher frontruns
            # Victim executes
            tokens = amm_mev.execute_buy(eth)
            # Backrun
            amm_mev.execute_sell(front_tokens)
            mev_results.append((tx.sender, eth, tokens, "SANDWICHED"))
        else:
            tokens = amm_mev.execute_buy(eth)
            mev_results.append((tx.sender, eth, tokens, "normal"))

    print(f"  {'User':<10} {'ETH In':>8} {'Fair Tokens':>14} "
          f"{'MEV Tokens':>13} {'Diff':>8} {'Status'}")
    print(f"  {'─' * 10} {'─' * 8} {'─' * 14} {'─' * 13} {'─' * 8} {'─' * 12}")
    for fair, mev in zip(fair_results, mev_results):
        diff = mev[2] - fair[2]
        sign = "+" if diff >= 0 else ""
        status = mev[3] if len(mev) > 3 else "normal"
        marker = " <--" if status == "SANDWICHED" else ""
        print(f"  {fair[0]:<10} {fair[1]:>8} {fair[2]:>14,} "
              f"{mev[2]:>13,} {sign}{diff:>7,} {status}{marker}")

    print(f"\n  Key takeaway: sandwich attacks extract value from regular users")
    print(f"  by manipulating the order of transactions within a block.")
    print(f"  PBS and Flashbots aim to make this process transparent and fair.")

    print("\n" + "=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
