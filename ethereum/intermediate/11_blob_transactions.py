"""
TITLE: Blob Transactions (EIP-4844)
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    EIP-4844 (Proto-Danksharding) blob transactions from scratch. Covers the
    Type-3 transaction format, blob structure (4096 field elements), simplified
    KZG polynomial commitments, the separate blob fee market with exponential
    pricing, and the target/max blob-per-block mechanism.

KEY CONCEPTS:
    - Type-3 transactions: new tx envelope carrying blob sidecar data
    - Blobs: 4096 field elements, each 32 bytes (128 KB per blob)
    - KZG commitments: polynomial commitment to blob data (simplified here)
    - Blob fee market: separate from execution gas, exponential pricing
    - Target of 3 blobs/block, max 6: elastic capacity with price feedback

PREREQUISITE SCRIPTS:
    - core/fundamentals/01_hashing.py (hashing fundamentals)
    - ethereum/fundamentals/03_gas_execution.py (EIP-1559 gas model)
    - ethereum/fundamentals/04_rlp_encoding.py (transaction encoding)

REAL-WORLD RELEVANCE:
    EIP-4844 went live in the Dencun upgrade (March 2024) and reduced L2
    data costs by ~10-100x. Rollups like Optimism, Arbitrum, and Base post
    their transaction data in blobs instead of calldata, making Ethereum
    scalable as a data availability layer for Layer 2s.
"""

import hashlib  # SHA-256 for hashing (stand-in for keccak256)
import struct   # For packing integers
import math     # For exponential fee calculations
import os       # For random blob data generation

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# --- Blob parameters (from EIP-4844 spec) ---

# Each blob contains 4096 field elements (BLS12-381 scalar field)
FIELD_ELEMENTS_PER_BLOB = 4096

# Each field element is 32 bytes
BYTES_PER_FIELD_ELEMENT = 32

# Total blob size: 4096 * 32 = 131,072 bytes (128 KB)
BLOB_SIZE = FIELD_ELEMENTS_PER_BLOB * BYTES_PER_FIELD_ELEMENT

# Target number of blobs per block (the "equilibrium" point)
TARGET_BLOBS_PER_BLOCK = 3

# Maximum blobs allowed in a single block
MAX_BLOBS_PER_BLOCK = 6

# Maximum blobs a single transaction can carry
MAX_BLOBS_PER_TX = 6

# --- Fee market parameters ---

# Minimum blob base fee (1 wei in real Ethereum)
MIN_BLOB_BASE_FEE = 1

# The blob base fee update fraction — controls how fast fees adjust
# Real value: 3338477 (makes fee change ~12.5% per excess blob)
BLOB_BASE_FEE_UPDATE_FRACTION = 3338477

# Simplified fraction for demo (exaggerated so changes are visible)
DEMO_UPDATE_FRACTION = 200000

# --- BLS12-381 field prime (modulus for field elements) ---
# Simplified — we use a smaller prime for demo purposes
BLS_MODULUS = 0x73eda753299d7d483339d80809a1d80553bda402fffe5bfeffffffff00000001


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Hashing ---------------------------------------------------------------

def sha256(data: bytes) -> bytes:
    """SHA-256 hash. Stand-in for keccak256 where needed."""
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes) -> str:
    """SHA-256 hash as hex string."""
    return hashlib.sha256(data).hexdigest()


# --- Blob data structure ---------------------------------------------------

class Blob:
    """A blob is 4096 field elements, each 32 bytes.

    In practice, rollups encode their compressed transaction batches into
    blobs. Each field element must be less than the BLS12-381 scalar field
    modulus to be a valid polynomial evaluation point.
    """

    def __init__(self, data: bytes | None = None):
        if data is not None:
            if len(data) > BLOB_SIZE:
                raise ValueError(f"Blob data exceeds {BLOB_SIZE} bytes")
            # Pad to full blob size
            self.data = data + b'\x00' * (BLOB_SIZE - len(data))
        else:
            self.data = b'\x00' * BLOB_SIZE

    @classmethod
    def from_random(cls, seed: int = 0) -> 'Blob':
        """Create a blob with deterministic pseudo-random data.

        We use a seeded hash chain instead of os.urandom for reproducibility.
        """
        chunks = []
        current = seed.to_bytes(32, 'big')
        for _ in range(FIELD_ELEMENTS_PER_BLOB):
            current = sha256(current)
            # Ensure the field element is less than the BLS modulus
            # by masking the top byte (simplified approach)
            element = bytearray(current)
            element[0] &= 0x73  # Keep under BLS modulus (very rough)
            chunks.append(bytes(element))
        return cls(b''.join(chunks))

    def field_element(self, index: int) -> int:
        """Get a single field element as an integer."""
        start = index * BYTES_PER_FIELD_ELEMENT
        return int.from_bytes(self.data[start:start + BYTES_PER_FIELD_ELEMENT], 'big')

    def commitment(self) -> bytes:
        """Compute a simplified KZG commitment to this blob.

        REAL KZG: Evaluate the blob as a polynomial at a trusted setup point
        using elliptic curve operations (BLS12-381 pairings).

        SIMPLIFIED: We hash the blob data to produce a 48-byte commitment.
        This preserves the binding property (can't find two blobs with the
        same commitment) but not the polynomial evaluation property.
        """
        # Real KZG commitments are 48 bytes (compressed BLS12-381 G1 point)
        h1 = sha256(b"blob_commitment_v1" + self.data[:BLOB_SIZE // 2])
        h2 = sha256(b"blob_commitment_v2" + self.data[BLOB_SIZE // 2:])
        # Combine two hashes to get 48 bytes (simulating a G1 point)
        return (h1 + h2)[:48]

    def versioned_hash(self) -> bytes:
        """Compute the versioned hash (used in the transaction body).

        The versioned hash is what actually appears in the Type-3 transaction.
        It's SHA-256 of the KZG commitment, with the first byte replaced by
        the version number (0x01 for KZG).
        """
        commitment = self.commitment()
        h = sha256(commitment)
        # Replace first byte with version prefix 0x01
        return b'\x01' + h[1:]  # Version 1 = KZG commitment scheme

    def proof_for_element(self, index: int) -> bytes:
        """Generate a simplified KZG proof for a specific field element.

        REAL KZG: Compute a quotient polynomial evaluation proof that
        proves the polynomial evaluates to a specific value at index.

        SIMPLIFIED: Hash of commitment + index (preserves the concept).
        """
        commitment = self.commitment()
        return sha256(commitment + index.to_bytes(4, 'big'))


# --- Type-3 transaction format ----------------------------------------------

class BlobTransaction:
    """A Type-3 (EIP-4844) blob-carrying transaction.

    Type-3 transactions are like EIP-1559 transactions but with additional
    blob-related fields and a separate fee market for blob data.
    """

    def __init__(
        self,
        chain_id: int,
        nonce: int,
        max_priority_fee: int,    # Tip to validator (execution layer)
        max_fee_per_gas: int,     # Max execution gas price willing to pay
        gas_limit: int,           # Execution gas limit
        to: str,                  # Destination address
        value: int,               # ETH value in wei
        data: bytes,              # Calldata (e.g., rollup batch submission)
        max_fee_per_blob_gas: int,  # Max blob gas price willing to pay
        blobs: list[Blob] | None = None,
    ):
        if blobs and len(blobs) > MAX_BLOBS_PER_TX:
            raise ValueError(f"Max {MAX_BLOBS_PER_TX} blobs per transaction")

        self.tx_type = 3  # EIP-4844 type identifier
        self.chain_id = chain_id
        self.nonce = nonce
        self.max_priority_fee = max_priority_fee
        self.max_fee_per_gas = max_fee_per_gas
        self.gas_limit = gas_limit
        self.to = to
        self.value = value
        self.data = data
        self.max_fee_per_blob_gas = max_fee_per_blob_gas

        # Blob sidecar — travels with the tx but stored separately
        self.blobs = blobs or []
        self.blob_commitments = [b.commitment() for b in self.blobs]
        self.blob_versioned_hashes = [b.versioned_hash() for b in self.blobs]

    def blob_gas_used(self) -> int:
        """Calculate the blob gas consumed by this transaction.

        Each blob costs a fixed 131,072 gas in the blob gas dimension.
        This is separate from execution gas.
        """
        return len(self.blobs) * BLOB_SIZE  # 131072 gas per blob

    def tx_hash(self) -> bytes:
        """Compute a simplified transaction hash."""
        # Hash the core fields (simplified — real encoding uses SSZ/RLP)
        parts = [
            self.tx_type.to_bytes(1, 'big'),
            self.chain_id.to_bytes(8, 'big'),
            self.nonce.to_bytes(8, 'big'),
            self.to.encode(),
            self.value.to_bytes(32, 'big'),
        ]
        for vh in self.blob_versioned_hashes:
            parts.append(vh)
        return sha256(b''.join(parts))


# --- Blob fee market --------------------------------------------------------

def fake_exponential(factor: int, numerator: int, denominator: int) -> int:
    """Compute factor * e^(numerator / denominator) using integer arithmetic.

    This is the core of the blob fee market — an exponential function that
    increases fees rapidly when demand exceeds the target. The implementation
    uses a Taylor series approximation: e^x = 1 + x + x^2/2! + x^3/3! + ...

    This function is defined in EIP-4844 and must be computed identically
    by all clients.
    """
    # Taylor series: sum of (factor * numerator^i) / (denominator^i * i!)
    # We iterate until the terms become negligibly small
    output = 0
    numerator_accumulator = factor * denominator  # Start with factor * denom (the "1" term)

    for i in range(1, 100):  # 100 terms is more than enough for convergence
        output += numerator_accumulator
        # Next term: multiply by numerator, divide by (denominator * i)
        numerator_accumulator = (numerator_accumulator * numerator) // (denominator * i)
        if numerator_accumulator == 0:
            break  # Converged — remaining terms are zero

    return output // denominator


def calc_blob_base_fee(excess_blob_gas: int, update_fraction: int = DEMO_UPDATE_FRACTION) -> int:
    """Calculate the current blob base fee from excess blob gas.

    The blob base fee follows an exponential curve:
    blob_base_fee = MIN_BLOB_BASE_FEE * e^(excess_blob_gas / UPDATE_FRACTION)

    When blocks consistently use more than TARGET blobs, the excess
    accumulates and fees rise exponentially. When usage drops below
    target, excess decreases and fees fall.
    """
    return fake_exponential(MIN_BLOB_BASE_FEE, excess_blob_gas, update_fraction)


def update_excess_blob_gas(parent_excess: int, parent_blobs_used: int) -> int:
    """Update the excess blob gas counter after a block.

    excess_new = max(0, parent_excess + blobs_used - target_blobs) * gas_per_blob

    If a block uses more than TARGET blobs, excess increases.
    If it uses fewer, excess decreases (but never below 0).
    This creates a negative feedback loop that stabilizes blob usage
    around the target.
    """
    target_gas = TARGET_BLOBS_PER_BLOCK * BLOB_SIZE
    parent_used_gas = parent_blobs_used * BLOB_SIZE

    total = parent_excess + parent_used_gas
    if total <= target_gas:
        return 0  # Below target — no excess
    return total - target_gas


# --- Block with blob support ------------------------------------------------

class BlobBlock:
    """A block that can contain blob transactions.

    In EIP-4844, the block body carries blob transactions but the actual
    blob data is propagated separately (sidecar). The block header includes
    excess_blob_gas and blob_gas_used for fee calculation.
    """

    def __init__(self, number: int, parent_excess_blob_gas: int):
        self.number = number
        self.transactions: list[BlobTransaction] = []
        self.excess_blob_gas = parent_excess_blob_gas
        self.blob_gas_used = 0
        self.blob_base_fee = calc_blob_base_fee(parent_excess_blob_gas)

    def add_transaction(self, tx: BlobTransaction) -> bool:
        """Add a blob transaction to this block.

        Checks that the block doesn't exceed MAX_BLOBS_PER_BLOCK and that
        the transaction's max_fee_per_blob_gas covers the current blob base fee.
        """
        total_blobs = sum(len(t.blobs) for t in self.transactions) + len(tx.blobs)
        if total_blobs > MAX_BLOBS_PER_BLOCK:
            return False  # Block is full (blob capacity)

        if tx.max_fee_per_blob_gas < self.blob_base_fee:
            return False  # Transaction underbid the blob fee market

        self.transactions.append(tx)
        self.blob_gas_used += tx.blob_gas_used()
        return True

    def total_blobs(self) -> int:
        """Count total blobs in this block."""
        return sum(len(tx.blobs) for tx in self.transactions)

    def next_excess_blob_gas(self) -> int:
        """Compute excess_blob_gas for the next block."""
        return update_excess_blob_gas(self.excess_blob_gas, self.total_blobs())


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def _hex(data: bytes, n: int = 16) -> str:
    """Truncated hex display."""
    h = data.hex()
    return h[:n] + "..." if len(h) > n else h


def _format_wei(wei: int) -> str:
    """Format wei amount in a human-readable way."""
    if wei >= 10**9:
        return f"{wei / 10**9:.2f} Gwei"
    elif wei >= 10**3:
        return f"{wei / 10**3:.1f} Kwei"
    else:
        return f"{wei} wei"


def demo():
    """Run a visual demonstration of EIP-4844 blob transactions."""

    print("=" * 70)
    print("EIP-4844 BLOB TRANSACTIONS — Proto-Danksharding")
    print("=" * 70)
    print()

    # --- Part 1: Blob structure ---------------------------------------------
    print("--- Part 1: Blob Structure ---")
    print()

    blob = Blob.from_random(seed=42)

    print(f"  Blob size: {BLOB_SIZE:,} bytes ({BLOB_SIZE // 1024} KB)")
    print(f"  Field elements: {FIELD_ELEMENTS_PER_BLOB}")
    print(f"  Bytes per element: {BYTES_PER_FIELD_ELEMENT}")
    print()

    # Show a few field elements
    print("  Sample field elements (first 4 of 4096):")
    for i in range(4):
        fe = blob.field_element(i)
        print(f"    [{i:4d}] 0x{fe:064x}"[:60] + "...")
    print(f"    ... ({FIELD_ELEMENTS_PER_BLOB - 4} more elements)")
    print()

    # Show commitment and versioned hash
    commitment = blob.commitment()
    versioned_hash = blob.versioned_hash()

    print("  KZG Commitment (48 bytes, BLS12-381 G1 point):")
    print(f"    {_hex(commitment, 48)}")
    print()
    print("  Versioned Hash (in tx body, version=0x01):")
    print(f"    {_hex(versioned_hash, 48)}")
    print(f"    Version byte: 0x{versioned_hash[0]:02x}")
    print()

    # --- Part 2: Type-3 transaction format ----------------------------------
    print("--- Part 2: Type-3 Transaction Format ---")
    print()

    # Simulate a rollup posting batch data
    rollup_address = "0x" + sha256(b"optimism_batcher").hex()[:40]
    blob1 = Blob.from_random(seed=100)
    blob2 = Blob.from_random(seed=200)

    tx = BlobTransaction(
        chain_id=1,          # Ethereum mainnet
        nonce=42,
        max_priority_fee=2 * 10**9,    # 2 Gwei tip
        max_fee_per_gas=30 * 10**9,    # 30 Gwei max
        gas_limit=21000,
        to=rollup_address,
        value=0,             # No ETH transfer — just data posting
        data=b'\x00' * 32,  # Minimal calldata
        max_fee_per_blob_gas=50 * 10**9,  # 50 Gwei max for blob gas
        blobs=[blob1, blob2],
    )

    print("  Type-3 Transaction (Rollup Batch Submission):")
    print("  ┌─────────────────────────────────────────────────────────┐")
    print(f"  │ tx_type:              {tx.tx_type} (EIP-4844 blob tx)            │")
    print(f"  │ chain_id:             {tx.chain_id} (mainnet)                     │")
    print(f"  │ nonce:                {tx.nonce}                                 │")
    print(f"  │ max_priority_fee:     {_format_wei(tx.max_priority_fee):<28}│")
    print(f"  │ max_fee_per_gas:      {_format_wei(tx.max_fee_per_gas):<28}│")
    print(f"  │ gas_limit:            {tx.gas_limit:<28}│")
    print(f"  │ to:                   {tx.to[:18]}...              │")
    print(f"  │ value:                {tx.value} wei                           │")
    print(f"  │ max_fee_per_blob_gas: {_format_wei(tx.max_fee_per_blob_gas):<28}│")
    print(f"  │ blob_versioned_hashes: [{len(tx.blob_versioned_hashes)} hashes]                │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print(f"  │ SIDECAR (propagated separately):                       │")
    print(f"  │   blobs:       {len(tx.blobs)} x {BLOB_SIZE // 1024} KB = "
          f"{len(tx.blobs) * BLOB_SIZE // 1024} KB               │")
    print(f"  │   commitments: {len(tx.blob_commitments)} x 48 bytes                      │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()

    for i, vh in enumerate(tx.blob_versioned_hashes):
        print(f"  Versioned hash [{i}]: {_hex(vh, 40)}")
    print()

    # --- Part 3: KZG verification (simplified) ------------------------------
    print("--- Part 3: KZG Commitment Verification (Simplified) ---")
    print()

    element_idx = 1000
    element_value = blob1.field_element(element_idx)
    proof = blob1.proof_for_element(element_idx)

    print(f"  Proving: blob[{element_idx}] = 0x{element_value:064x}"[:55] + "...")
    print(f"  Commitment: {_hex(blob1.commitment(), 32)}")
    print(f"  Proof:      {_hex(proof, 32)}")
    print()
    print("  In real KZG:")
    print("    verify(commitment, index, value, proof) → True/False")
    print("    Uses elliptic curve pairings on BLS12-381")
    print("    Requires a trusted setup (the 'ceremony')")
    print()

    # --- Part 4: Blob fee market simulation ---------------------------------
    print("--- Part 4: Blob Fee Market (Exponential Pricing) ---")
    print()
    print(f"  Target: {TARGET_BLOBS_PER_BLOCK} blobs/block")
    print(f"  Maximum: {MAX_BLOBS_PER_BLOCK} blobs/block")
    print(f"  Blob gas per blob: {BLOB_SIZE:,}")
    print()

    # Simulate 12 blocks with varying demand
    # Pattern: low → high → above target → back to target → below
    demand_pattern = [1, 2, 3, 5, 6, 6, 6, 4, 3, 2, 1, 3]

    print("  Simulating 12 blocks with varying blob demand:")
    print()
    print("  ┌───────┬───────┬────────────────┬──────────────┬──────────────────┐")
    print("  │ Block │ Blobs │ Blob Base Fee  │ Excess Gas   │ Status           │")
    print("  ├───────┼───────┼────────────────┼──────────────┼──────────────────┤")

    excess = 0  # Start with no excess

    for i, demand in enumerate(demand_pattern):
        base_fee = calc_blob_base_fee(excess)
        blobs_used = min(demand, MAX_BLOBS_PER_BLOCK)

        # Status indicator
        if blobs_used > TARGET_BLOBS_PER_BLOCK:
            status = "ABOVE target"
            marker = ">>>"
        elif blobs_used == TARGET_BLOBS_PER_BLOCK:
            status = "AT target"
            marker = "==="
        else:
            status = "below target"
            marker = "<<<"

        # Visual blob bar
        bar = "#" * blobs_used + "." * (MAX_BLOBS_PER_BLOCK - blobs_used)

        print(f"  │  {i:>3}  │ [{bar}] │ {_format_wei(base_fee):>14} │ {excess:>12,} │ {marker} {status:<11}│")

        # Update excess for next block
        excess = update_excess_blob_gas(excess, blobs_used)

    print("  └───────┴───────┴────────────────┴──────────────┬──────────────────┘")
    print()
    print("  Key insight: fees rise exponentially when demand > target (3 blobs)")
    print("  and fall when demand < target. This creates economic pressure to")
    print("  keep blob usage near the target — similar to EIP-1559 for exec gas.")

    # --- Part 5: Cost comparison --------------------------------------------
    print()
    print("--- Part 5: Blobs vs Calldata Cost Comparison ---")
    print()

    # Approximate costs for posting 128 KB of rollup data
    data_size = BLOB_SIZE  # 128 KB
    calldata_gas_per_byte = 16  # Non-zero calldata byte costs 16 gas
    calldata_gas = data_size * calldata_gas_per_byte
    exec_gas_price = 30  # 30 Gwei
    blob_gas_price = 1   # 1 wei (typical low blob fee)

    calldata_cost_gwei = calldata_gas * exec_gas_price
    blob_cost_gwei = BLOB_SIZE * blob_gas_price / 10**9  # Convert wei to Gwei

    print(f"  Posting {data_size // 1024} KB of rollup data:")
    print()
    print("  ┌──────────────────────────────────────────────────────┐")
    print(f"  │ Method      │ Gas Used     │ Price     │ Cost       │")
    print("  ├──────────────────────────────────────────────────────┤")
    print(f"  │ Calldata    │ {calldata_gas:>10,}  │ {exec_gas_price} Gwei  │ {calldata_cost_gwei:>10,} Gwei │")
    print(f"  │ Blob (4844) │ {BLOB_SIZE:>10,}  │ {blob_gas_price} wei   │ {blob_cost_gwei:>10.4f} Gwei │")
    print("  └──────────────────────────────────────────────────────┘")
    print()

    if blob_cost_gwei > 0:
        ratio = calldata_cost_gwei / blob_cost_gwei
        print(f"  Blob is ~{ratio:,.0f}x cheaper than calldata at these prices!")
    print()
    print("  Note: Blob data is pruned after ~18 days (4096 epochs).")
    print("  Calldata is stored forever. Blobs are for temporary DA only.")


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
