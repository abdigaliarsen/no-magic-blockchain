"""
TITLE: Bloom Filters
CATEGORY: core

WHAT THIS IMPLEMENTS:
    A Bloom filter — a space-efficient probabilistic data structure that tests
    whether an element is a member of a set. It can produce false positives
    (saying "maybe in set" when it isn't) but never false negatives (if it says
    "definitely not in set", it's correct).

KEY CONCEPTS:
    - Bit array as compact set representation
    - Multiple independent hash functions (via salted SHA-256)
    - Insert: set k bit positions to 1
    - Query: check if all k bit positions are 1
    - False positive rate: controlled by array size and hash count

PREREQUISITE SCRIPTS:
    - core/fundamentals/01_hashing.py (SHA-256 for hash functions)

REAL-WORLD RELEVANCE:
    Bitcoin SPV nodes use Bloom filters (BIP 37) to request only relevant
    transactions from full nodes without revealing their exact addresses.
    Ethereum uses Bloom filters in transaction receipt logs to quickly check
    if a block might contain a specific event.
"""

import hashlib
import math

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Default parameters for demonstration
DEFAULT_SIZE = 1000        # Number of bits in the filter (m)
DEFAULT_HASH_COUNT = 7     # Number of hash functions (k)

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================


class BloomFilter:
    """A Bloom filter backed by a bit array with multiple hash functions.

    The filter uses k independent hash functions, each mapping an element to
    a position in an m-bit array. An element is "inserted" by setting all k
    positions to 1. A query returns True if all k positions are 1.
    """

    def __init__(self, size: int = DEFAULT_SIZE, hash_count: int = DEFAULT_HASH_COUNT):
        """Initialize the Bloom filter.

        Args:
            size: Number of bits in the bit array (m). Larger = fewer false positives.
            hash_count: Number of hash functions (k). Optimal k = (m/n) * ln(2).
        """
        self.size = size            # Total bits in the array (m)
        self.hash_count = hash_count  # Number of hash functions (k)
        # Use a bytearray as our bit array — each byte holds 8 bits
        # We need ceil(size / 8) bytes to store 'size' bits
        self._bits = bytearray((size + 7) // 8)
        self.item_count = 0         # Track how many items have been inserted

    def _hash(self, item: str, seed: int) -> int:
        """Compute a hash position for the given item and seed.

        We create k independent hash functions by prepending a different seed
        byte to the input before hashing. Each seed produces a completely
        different SHA-256 output (avalanche effect), giving us independent
        hash functions from a single hash algorithm.
        """
        # Prepend the seed as bytes to make each hash function independent
        data = seed.to_bytes(4, "big") + item.encode("utf-8")
        # SHA-256 produces 32 bytes; interpret as integer, mod by filter size
        digest = hashlib.sha256(data).digest()
        # Use first 8 bytes (64 bits) — more than enough for any practical filter size
        value = int.from_bytes(digest[:8], "big")
        return value % self.size

    def _set_bit(self, position: int) -> None:
        """Set a single bit in the bit array to 1."""
        byte_index = position // 8   # Which byte contains this bit
        bit_offset = position % 8    # Which bit within that byte
        self._bits[byte_index] |= (1 << bit_offset)  # OR to set without clearing others

    def _get_bit(self, position: int) -> bool:
        """Check if a single bit in the bit array is set to 1."""
        byte_index = position // 8
        bit_offset = position % 8
        return bool(self._bits[byte_index] & (1 << bit_offset))

    def insert(self, item: str) -> list[int]:
        """Insert an item into the Bloom filter.

        Sets k bit positions (one per hash function) to 1.
        Returns the list of positions that were set (useful for visualization).
        """
        positions = []
        for i in range(self.hash_count):
            pos = self._hash(item, seed=i)
            self._set_bit(pos)
            positions.append(pos)
        self.item_count += 1
        return positions

    def query(self, item: str) -> bool:
        """Query whether an item might be in the set.

        Returns True if all k hash positions are set to 1 (item MAY be present).
        Returns False if any position is 0 (item is DEFINITELY NOT present).
        """
        for i in range(self.hash_count):
            pos = self._hash(item, seed=i)
            if not self._get_bit(pos):
                # Found a 0 bit — this item was never inserted
                return False
        # All bits set — item is probably in the set (could be false positive)
        return True

    def bits_set(self) -> int:
        """Count how many bits are currently set to 1."""
        count = 0
        for byte in self._bits:
            # Count set bits in each byte using Brian Kernighan's method
            while byte:
                byte &= byte - 1  # Clear lowest set bit
                count += 1
        return count

    @staticmethod
    def optimal_size(n: int, fp_rate: float) -> int:
        """Calculate optimal bit array size for n items and desired FP rate.

        Formula: m = -(n * ln(p)) / (ln(2)^2)
        This minimizes space while achieving the target false positive rate.
        """
        m = -(n * math.log(fp_rate)) / (math.log(2) ** 2)
        return int(math.ceil(m))

    @staticmethod
    def optimal_hash_count(m: int, n: int) -> int:
        """Calculate optimal number of hash functions.

        Formula: k = (m / n) * ln(2)
        Too few hash functions → more false positives from insufficient coverage.
        Too many → bit array fills up too fast, also increasing false positives.
        """
        k = (m / n) * math.log(2)
        return max(1, int(round(k)))

    def theoretical_fp_rate(self) -> float:
        """Calculate the theoretical false positive rate given current parameters.

        Formula: (1 - e^(-kn/m))^k
        where k = hash_count, n = items inserted, m = filter size.
        """
        if self.item_count == 0:
            return 0.0
        exponent = -self.hash_count * self.item_count / self.size
        return (1 - math.exp(exponent)) ** self.hash_count


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Bloom filters."""

    print("=" * 70)
    print("  Bloom Filters — Probabilistic Set Membership")
    print("=" * 70)

    # --- Basic operation ---
    print("\n--- Basic Bloom Filter Operation ---\n")

    bf = BloomFilter(size=64, hash_count=3)  # Small for visualization
    print(f"  Filter: {bf.size} bits, {bf.hash_count} hash functions\n")

    # Insert some items and show bit positions
    items = ["alice", "bob", "charlie"]
    for item in items:
        positions = bf.insert(item)
        # Show which bits were set
        bit_str = ""
        for b in range(bf.size):
            if b in positions:
                bit_str += "#"  # This bit was just set by this item
            elif bf._get_bit(b):
                bit_str += "."  # This bit was set by a previous item
            else:
                bit_str += "_"  # This bit is still 0
        print(f'  Insert "{item}":')
        print(f"    Positions: {positions}")
        print(f"    Bits: [{bit_str}]")
        print()

    # Query for present and absent items
    print("  --- Queries ---\n")
    queries = ["alice", "bob", "charlie", "dave", "eve", "frank"]
    for item in queries:
        result = bf.query(item)
        known = item in items
        status = ""
        if result and known:
            status = "TRUE POSITIVE (correctly found)"
        elif result and not known:
            status = "FALSE POSITIVE (not actually in set!)"
        elif not result and not known:
            status = "TRUE NEGATIVE (correctly rejected)"
        else:
            status = "FALSE NEGATIVE (BUG — should never happen!)"
        symbol = "+" if result else "-"
        print(f'    [{symbol}] "{item}": {status}')

    # --- False positive rate measurement ---
    print("\n\n--- False Positive Rate Experiment ---\n")

    # Create a properly-sized filter
    n_items = 100           # Number of items to insert
    target_fp = 0.01        # Target 1% false positive rate
    m = BloomFilter.optimal_size(n_items, target_fp)
    k = BloomFilter.optimal_hash_count(m, n_items)

    print(f"  Target: store {n_items} items with {target_fp*100:.1f}% FP rate")
    print(f"  Optimal filter size:  {m} bits ({m/8:.0f} bytes)")
    print(f"  Optimal hash count:   {k}")
    print()

    bf2 = BloomFilter(size=m, hash_count=k)

    # Insert n_items unique strings
    inserted = set()
    for i in range(n_items):
        item = f"item_{i:04d}"
        bf2.insert(item)
        inserted.add(item)

    # Test all inserted items — should all return True
    false_negatives = 0
    for item in inserted:
        if not bf2.query(item):
            false_negatives += 1

    print(f"  Inserted items found:    {n_items - false_negatives}/{n_items}")
    print(f"  False negatives:         {false_negatives} (must be 0)")

    # Test many non-inserted items to measure FP rate empirically
    n_test = 10000
    false_positives = 0
    for i in range(n_test):
        test_item = f"test_{i:06d}"  # Different prefix, guaranteed not inserted
        if bf2.query(test_item):
            false_positives += 1

    empirical_fp = false_positives / n_test
    theoretical_fp = bf2.theoretical_fp_rate()

    print()
    print(f"  Non-member queries:      {n_test}")
    print(f"  False positives:         {false_positives}")
    print(f"  Empirical FP rate:       {empirical_fp*100:.2f}%")
    print(f"  Theoretical FP rate:     {theoretical_fp*100:.2f}%")
    print(f"  Target FP rate:          {target_fp*100:.2f}%")
    print()

    # Visual comparison bar
    max_bar = 40
    emp_bar = int(empirical_fp / target_fp * max_bar / 2)
    theo_bar = int(theoretical_fp / target_fp * max_bar / 2)
    tgt_bar = max_bar // 2

    print(f"  Empirical:    [{'#' * min(emp_bar, max_bar):.<{max_bar}s}] {empirical_fp*100:.2f}%")
    print(f"  Theoretical:  [{'#' * min(theo_bar, max_bar):.<{max_bar}s}] {theoretical_fp*100:.2f}%")
    print(f"  Target:       [{'#' * min(tgt_bar, max_bar):.<{max_bar}s}] {target_fp*100:.2f}%")

    # --- Space efficiency ---
    print("\n\n--- Space Efficiency ---\n")

    print(f"  Storing {n_items} items:")
    print(f"    Bloom filter:  {m // 8} bytes ({m} bits)")
    # A Python set of 100 strings would be much larger
    avg_item_len = 9  # "item_0000" = 9 chars
    set_size = n_items * (avg_item_len + 50)  # rough estimate with Python overhead
    print(f"    Python set:    ~{set_size} bytes (estimated)")
    ratio = set_size / (m // 8) if m > 0 else 0
    print(f"    Space savings: ~{ratio:.0f}x smaller with Bloom filter")
    print(f"    Trade-off:     {empirical_fp*100:.2f}% false positive rate")

    # --- How it works diagram ---
    print("\n--- How Bloom Filters Work ---\n")
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │                                                        │")
    print("  │  INSERT \"alice\":                                       │")
    print("  │    h1(\"alice\") = 5   h2(\"alice\") = 12  h3(\"alice\") = 7 │")
    print("  │                                                        │")
    print("  │    Bit array:  [0 0 0 0 0 1 0 1 0 0 0 0 1 0 0 0]      │")
    print("  │                          ^   ^           ^             │")
    print("  │                                                        │")
    print("  │  QUERY \"alice\":  positions 5,12,7 all = 1 -> MAYBE     │")
    print("  │  QUERY \"dave\":   position 3 = 0          -> DEFINITELY │")
    print("  │                                              NOT       │")
    print("  │                                                        │")
    print("  │  Key property: no false negatives, but false positives │")
    print("  │  are possible when different items' bits overlap.       │")
    print("  └─────────────────────────────────────────────────────────┘")

    # --- Blockchain usage ---
    print("\n--- Blockchain Applications ---\n")
    print("  Bitcoin BIP 37:  SPV nodes send Bloom filters to full nodes")
    print("                   to request only matching transactions,")
    print("                   reducing bandwidth while preserving some privacy.")
    print()
    print("  Ethereum logs:   Each block contains a 2048-bit Bloom filter")
    print("                   over all log topics, enabling fast scanning")
    print("                   for specific events without checking every tx.")

    print()
    print("=" * 70)
    print("  Bloom filter demonstration complete.")
    print("=" * 70)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
