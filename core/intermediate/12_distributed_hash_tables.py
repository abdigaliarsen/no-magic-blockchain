"""
TITLE: Distributed Hash Tables (Kademlia)
CATEGORY: core

WHAT THIS IMPLEMENTS:
    A Kademlia-style Distributed Hash Table (DHT) simulated in-memory. Implements
    XOR-based distance metric, k-bucket routing tables, iterative node lookup,
    and key-value store/retrieve operations across a network of 50+ simulated nodes.

KEY CONCEPTS:
    - XOR distance metric (symmetric, satisfies triangle inequality)
    - K-buckets: routing table organized by distance ranges
    - Iterative lookup: find closest nodes to a target ID
    - Distributed storage: key-value pairs stored at nodes closest to the key hash

PREREQUISITE SCRIPTS:
    - core/fundamentals/01_hashing.py (hashing for node/key IDs)
    - core/fundamentals/08_p2p_network.py (peer-to-peer networking concepts)

REAL-WORLD RELEVANCE:
    Kademlia is the foundation of peer discovery in Ethereum's devp2p,
    BitTorrent's DHT for trackerless torrents, and IPFS content routing.
    It enables decentralized networks to locate data without central servers.
"""

import hashlib
import random

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Number of bits in node/key IDs — determines the address space size (2^ID_BITS)
# Real Kademlia uses 160 bits (SHA-1); we use 16 bits for readable demos
ID_BITS = 16
ID_SPACE = 1 << ID_BITS  # Total address space: 2^16 = 65536

# K parameter: max contacts per k-bucket and replication factor
# Larger k → more robust routing but more storage. Real networks use k=20.
K = 3

# Alpha: number of parallel lookups in each iteration
# Real Kademlia uses alpha=3 for concurrent RPCs; we simulate sequentially
ALPHA = 3

# Number of nodes in the simulated network
NUM_NODES = 50

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

def xor_distance(a: int, b: int) -> int:
    """Compute XOR distance between two node IDs.

    XOR distance is the core of Kademlia's metric:
    - d(a, b) = a XOR b
    - It's symmetric: d(a,b) = d(b,a)
    - It satisfies triangle inequality: d(a,c) <= d(a,b) + d(b,c)
    - d(a,a) = 0 (identity)
    - For any point a and distance d, there is exactly one point b with d(a,b) = d

    The last property is unique to XOR and makes routing efficient.
    """
    return a ^ b


def key_to_id(key: str) -> int:
    """Hash a string key to a node ID in our address space.

    We use SHA-256 and take the first ID_BITS bits.
    """
    h = hashlib.sha256(key.encode("utf-8")).digest()
    # Convert first 2 bytes to integer, mask to ID_BITS bits
    return int.from_bytes(h[:2], "big") % ID_SPACE


def bucket_index(node_id: int, target_id: int) -> int:
    """Determine which k-bucket a target falls into relative to a node.

    The bucket index is the position of the highest set bit in the XOR distance.
    Bucket i contains nodes whose distance is in [2^i, 2^(i+1)).
    This means bucket 0 holds the closest nodes, bucket (ID_BITS-1) the farthest.

    Returns -1 if the IDs are identical (shouldn't store self in routing table).
    """
    dist = xor_distance(node_id, target_id)
    if dist == 0:
        return -1  # Same node — no bucket
    # Find the position of the highest bit: this determines the bucket
    return dist.bit_length() - 1


# ----------------------------------------------------------------------------
# K-Bucket: a bounded list of contacts at a specific distance range
# ----------------------------------------------------------------------------

class KBucket:
    """A k-bucket stores up to K contacts for a specific distance range.

    Contacts are ordered by most-recently-seen: the tail is the most recently
    contacted node. When the bucket is full and a new node is discovered:
    - If the least-recently-seen (head) node is still alive, keep it (Kademlia
      prefers long-lived nodes, which are statistically more reliable)
    - Otherwise, evict the head and add the new node
    """

    def __init__(self):
        self.contacts: list[int] = []  # List of node IDs, tail = most recent

    def add(self, node_id: int) -> bool:
        """Add a node to this bucket, or move it to the tail if already present.

        Returns True if the node was added/updated, False if bucket is full
        and the node couldn't be added.
        """
        if node_id in self.contacts:
            # Already known — move to tail (most recently seen)
            self.contacts.remove(node_id)
            self.contacts.append(node_id)
            return True

        if len(self.contacts) < K:
            # Bucket has room — just add
            self.contacts.append(node_id)
            return True

        # Bucket full — in real Kademlia, we'd ping the head node.
        # For simulation, we just reject (stable nodes are preferred).
        return False

    def closest(self, target_id: int, count: int) -> list[int]:
        """Return up to 'count' contacts sorted by XOR distance to target."""
        return sorted(self.contacts, key=lambda nid: xor_distance(nid, target_id))[:count]


# ----------------------------------------------------------------------------
# DHT Node: a participant in the Kademlia network
# ----------------------------------------------------------------------------

class DHTNode:
    """A single node in the Kademlia DHT network.

    Each node has:
    - A unique ID (random or hash-derived)
    - A routing table of ID_BITS k-buckets
    - A local key-value store for data it's responsible for
    """

    def __init__(self, node_id: int):
        self.node_id = node_id
        # One k-bucket for each bit position (0 to ID_BITS-1)
        self.buckets: list[KBucket] = [KBucket() for _ in range(ID_BITS)]
        # Local storage: maps key_id -> (key_name, value)
        self.storage: dict[int, tuple[str, str]] = {}

    def update_routing_table(self, other_id: int) -> None:
        """Add or update a node in our routing table.

        Called whenever we learn about another node (through lookup, store, etc.).
        """
        idx = bucket_index(self.node_id, other_id)
        if idx >= 0:  # Don't add ourselves
            self.buckets[idx].add(other_id)

    def find_closest(self, target_id: int, count: int = K) -> list[int]:
        """Find the closest nodes to target_id from our routing table.

        Searches all buckets and returns the overall closest 'count' nodes.
        """
        all_contacts = []
        for bucket in self.buckets:
            all_contacts.extend(bucket.contacts)
        # Sort by XOR distance to target
        all_contacts.sort(key=lambda nid: xor_distance(nid, target_id))
        return all_contacts[:count]

    def store_value(self, key_id: int, key_name: str, value: str) -> None:
        """Store a key-value pair locally."""
        self.storage[key_id] = (key_name, value)

    def get_value(self, key_id: int) -> tuple[str, str] | None:
        """Retrieve a value from local storage, or None if not found."""
        return self.storage.get(key_id)


# ----------------------------------------------------------------------------
# DHT Network: the full simulated Kademlia network
# ----------------------------------------------------------------------------

class DHTNetwork:
    """A simulated Kademlia DHT network with multiple nodes.

    In reality, nodes communicate via UDP RPCs (PING, STORE, FIND_NODE,
    FIND_VALUE). Here we simulate the protocol by directly calling methods
    on node objects, tracking message counts for visualization.
    """

    def __init__(self):
        self.nodes: dict[int, DHTNode] = {}  # node_id -> DHTNode
        self.message_count = 0  # Track simulated RPCs

    def add_node(self, node_id: int) -> DHTNode:
        """Add a new node to the network."""
        node = DHTNode(node_id)
        self.nodes[node_id] = node
        return node

    def bootstrap(self) -> None:
        """Bootstrap the network: every node learns about some initial peers.

        In real Kademlia, a new node contacts a bootstrap node and does an
        iterative FIND_NODE for its own ID to populate its routing table.
        Here we simulate by having each node learn about a random subset of peers.
        """
        node_ids = list(self.nodes.keys())
        for nid in node_ids:
            node = self.nodes[nid]
            # Each node learns about ~log2(N) random peers (simulating bootstrap)
            num_bootstrap = min(8, len(node_ids) - 1)
            peers = random.sample([x for x in node_ids if x != nid], num_bootstrap)
            for peer_id in peers:
                node.update_routing_table(peer_id)
                # The peer also learns about us (bidirectional)
                self.nodes[peer_id].update_routing_table(nid)

    def iterative_find_node(self, source_id: int, target_id: int,
                            trace: bool = False) -> list[tuple[int, int]]:
        """Perform iterative FIND_NODE lookup from source toward target.

        This is the core Kademlia lookup algorithm:
        1. Start with the ALPHA closest nodes from our routing table
        2. Ask each for their closest nodes to the target
        3. Add newly discovered nodes to our candidate set
        4. Repeat until no closer nodes are found

        Returns list of (node_id, distance) sorted by distance to target.
        """
        source = self.nodes[source_id]
        hops = 0

        # Initialize with our own closest known nodes
        closest = source.find_closest(target_id, count=K)
        queried = {source_id}  # Track which nodes we've already asked
        hop_log = []  # For tracing the lookup path

        while True:
            hops += 1
            # Pick ALPHA closest unqueried nodes to ask
            to_query = [nid for nid in closest if nid not in queried][:ALPHA]

            if not to_query:
                break  # No more unqueried nodes — lookup complete

            new_nodes_found = False
            for nid in to_query:
                queried.add(nid)
                self.message_count += 1

                if nid not in self.nodes:
                    continue  # Node not in network (shouldn't happen in sim)

                # Ask this node for its closest to target (simulated FIND_NODE RPC)
                peer = self.nodes[nid]
                peer_closest = peer.find_closest(target_id, count=K)

                if trace:
                    dist = xor_distance(nid, target_id)
                    hop_log.append((hops, nid, dist, len(peer_closest)))

                # Update source's routing table with discovered nodes
                for discovered_id in peer_closest:
                    source.update_routing_table(discovered_id)
                    if discovered_id not in [c for c in closest]:
                        new_nodes_found = True

                # Merge into our candidate set
                for new_id in peer_closest:
                    if new_id not in closest:
                        closest.append(new_id)

            # Re-sort by distance to target
            closest.sort(key=lambda nid: xor_distance(nid, target_id))
            closest = closest[:K]  # Keep only K closest

            if not new_nodes_found:
                break  # Converged — no new closer nodes found

        if trace:
            return closest, hops, hop_log

        return [(nid, xor_distance(nid, target_id)) for nid in closest]

    def store(self, key: str, value: str, source_id: int,
              trace: bool = False) -> list[int]:
        """Store a key-value pair in the DHT.

        1. Hash the key to get a key_id
        2. Find the K closest nodes to key_id
        3. Store the value on each of those nodes (replication)

        Returns list of node IDs that stored the value.
        """
        key_id = key_to_id(key)

        # Find K closest nodes to the key
        if trace:
            closest, hops, hop_log = self.iterative_find_node(
                source_id, key_id, trace=True
            )
            stored_at = []
            for nid in [c for c in closest]:
                self.nodes[nid].store_value(key_id, key, value)
                stored_at.append(nid)
                self.message_count += 1
            return stored_at, key_id, hops, hop_log
        else:
            result = self.iterative_find_node(source_id, key_id)
            stored_at = []
            for nid, dist in result:
                self.nodes[nid].store_value(key_id, key, value)
                stored_at.append(nid)
                self.message_count += 1
            return stored_at

    def retrieve(self, key: str, source_id: int,
                 trace: bool = False) -> str | None:
        """Retrieve a value from the DHT.

        1. Hash the key to get key_id
        2. Find the K closest nodes to key_id
        3. Check each for the value

        Returns the value if found, None otherwise.
        """
        key_id = key_to_id(key)

        if trace:
            closest, hops, hop_log = self.iterative_find_node(
                source_id, key_id, trace=True
            )
            for nid in closest:
                result = self.nodes[nid].get_value(key_id)
                if result is not None:
                    return result[1], key_id, hops, hop_log
            return None, key_id, hops, hop_log
        else:
            result = self.iterative_find_node(source_id, key_id)
            for nid, dist in result:
                val = self.nodes[nid].get_value(key_id)
                if val is not None:
                    return val[1]
            return None


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of Kademlia DHT."""

    print("=" * 70)
    print("  Distributed Hash Tables (Kademlia DHT)")
    print("=" * 70)

    # --- XOR Distance ---
    print("\n--- XOR Distance Metric ---\n")

    examples = [(0b1010, 0b1100), (0b0001, 0b1000), (0b1111, 0b1111)]
    for a, b in examples:
        d = xor_distance(a, b)
        print(f"  d({a:04b}, {b:04b}) = {a:04b} XOR {b:04b} = {d:04b} = {d}")
    print()
    print("  Properties:")
    a, b, c = 5, 12, 9
    print(f"    Symmetric:  d({a},{b}) = {xor_distance(a,b)}, d({b},{a}) = {xor_distance(b,a)}")
    print(f"    Identity:   d({a},{a}) = {xor_distance(a,a)}")
    d_ab = xor_distance(a, b)
    d_bc = xor_distance(b, c)
    d_ac = xor_distance(a, c)
    print(f"    Triangle:   d({a},{c})={d_ac} <= d({a},{b})+d({b},{c})={d_ab}+{d_bc}={d_ab+d_bc}")

    # --- Build the network ---
    print("\n\n--- Building {}-Node Network ---\n".format(NUM_NODES))

    random.seed(42)  # Reproducible demo
    network = DHTNetwork()

    # Create nodes with random IDs
    for _ in range(NUM_NODES):
        nid = random.randint(0, ID_SPACE - 1)
        while nid in network.nodes:  # Ensure unique IDs
            nid = random.randint(0, ID_SPACE - 1)
        network.add_node(nid)

    # Bootstrap the network
    network.bootstrap()

    node_ids = sorted(network.nodes.keys())
    print(f"  Created {len(node_ids)} nodes with {ID_BITS}-bit IDs")
    print(f"  ID range: 0 to {ID_SPACE - 1} ({ID_SPACE} possible IDs)")
    print(f"  Sample node IDs: {node_ids[:6]}...")

    # Show one node's routing table
    sample_node = network.nodes[node_ids[0]]
    print(f"\n  Routing table for node {sample_node.node_id}:")
    print(f"  {'Bucket':>8s}  {'Distance Range':>20s}  {'Contacts':>10s}")
    print("  " + "-" * 45)
    for i in range(ID_BITS):
        contacts = sample_node.buckets[i].contacts
        if contacts:
            lo = 1 << i
            hi = (1 << (i + 1)) - 1
            print(f"  {i:>8d}  {lo:>8d} - {hi:<8d}    {len(contacts):>3d}  {contacts[:3]}{'...' if len(contacts) > 3 else ''}")

    # --- Store values ---
    print("\n\n--- Storing Key-Value Pairs ---\n")

    # Use the first node as our entry point
    source = node_ids[0]
    test_data = [
        ("tx:abc123", "Alice -> Bob: 5 BTC"),
        ("block:100", "hash=0xdeadbeef..."),
        ("peer:node42", "192.168.1.42:30303"),
    ]

    for key, value in test_data:
        stored_at, key_id, hops, hop_log = network.store(
            key, value, source, trace=True
        )
        print(f'  STORE "{key}" (id={key_id})')
        print(f'    Value: "{value}"')
        print(f"    Lookup hops: {hops}")
        print(f"    Stored at nodes: {stored_at}")

        # Show routing trace
        if hop_log:
            print(f"    Routing trace:")
            for hop_num, nid, dist, n_resp in hop_log[:5]:
                print(f"      Hop {hop_num}: node {nid:>5d} (dist={dist:>5d}, returned {n_resp} contacts)")
        print()

    # --- Retrieve values ---
    print("--- Retrieving Values ---\n")

    # Retrieve from a DIFFERENT node to show distributed routing
    retriever = node_ids[-1]  # Use the last node
    print(f"  Retrieving from node {retriever} (different from storer {source})\n")

    for key, expected_value in test_data:
        network.message_count = 0
        result, key_id, hops, hop_log = network.retrieve(key, retriever, trace=True)

        found = result is not None
        correct = result == expected_value if found else False
        status = "FOUND" if correct else ("WRONG VALUE" if found else "NOT FOUND")

        print(f'  GET "{key}" (id={key_id})')
        print(f"    Status: {status}")
        if found:
            print(f'    Value: "{result}"')
        print(f"    Lookup hops: {hops}")
        print(f"    Messages sent: {network.message_count}")

        # Show routing
        if hop_log:
            print(f"    Route: ", end="")
            route_nodes = [retriever] + [nid for _, nid, _, _ in hop_log[:4]]
            print(" -> ".join(str(n) for n in route_nodes))
        print()

    # --- Key not found ---
    print("--- Key Not Found ---\n")

    network.message_count = 0
    result, key_id, hops, _ = network.retrieve("nonexistent:key", source, trace=True)
    print(f'  GET "nonexistent:key" (id={key_id})')
    print(f"  Status: {'FOUND' if result else 'NOT FOUND (correct)'}")
    print(f"  Hops: {hops}")

    # --- How it works ---
    print("\n\n--- How Kademlia Works ---\n")
    print("  ┌──────────────────────────────────────────────────────────┐")
    print("  │  1. Each node has a {}-bit ID and a routing table      │".format(ID_BITS))
    print("  │     of {} k-buckets (one per bit position).             │".format(ID_BITS))
    print("  │                                                         │")
    print("  │  2. Bucket i holds nodes at XOR distance [2^i, 2^(i+1))│")
    print("  │     Each bucket holds at most K={} contacts.            │".format(K))
    print("  │                                                         │")
    print("  │  3. To find a key, iteratively query closest known      │")
    print("  │     nodes, each returning their closest contacts.       │")
    print("  │     Converges in O(log N) hops.                         │")
    print("  │                                                         │")
    print("  │  4. Values are stored at the K nodes closest to the     │")
    print("  │     key's hash (replication for fault tolerance).       │")
    print("  │                                                         │")
    print("  │  XOR distance is unique because for any point and any   │")
    print("  │  distance, exactly ONE other point exists at that       │")
    print("  │  distance — making routing unambiguous.                 │")
    print("  └──────────────────────────────────────────────────────────┘")

    # --- Blockchain context ---
    print("\n--- Blockchain Applications ---\n")
    print("  Ethereum devp2p:  Uses Kademlia for peer discovery.")
    print("                    Nodes find each other by looking up")
    print("                    node IDs in the DHT.")
    print()
    print("  IPFS:             Content-addressed storage uses a DHT")
    print("                    to map content hashes to provider nodes.")
    print()
    print("  BitTorrent:       DHT enables trackerless torrents by")
    print("                    mapping info_hash to peer lists.")

    print()
    print("=" * 70)
    print("  Kademlia DHT demonstration complete.")
    print("=" * 70)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
