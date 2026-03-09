"""
TITLE: P2P Gossip Network Simulation
CATEGORY: core

WHAT THIS IMPLEMENTS:
    A fully in-memory simulation of a peer-to-peer gossip network where nodes
    discover each other, propagate blocks via gossip, and resolve forks using
    the longest-chain rule. No actual networking — everything is simulated with
    Python data structures.

KEY CONCEPTS:
    - Gossip protocol (epidemic-style block propagation)
    - Peer discovery (bootstrap nodes, random peer exchange)
    - Fork resolution (longest-chain rule)

PREREQUISITE SCRIPTS:
    - core/05_blockchain.py (block structure and chain validation concepts)

REAL-WORLD RELEVANCE:
    Every public blockchain uses gossip-based P2P networking to propagate
    transactions and blocks. Bitcoin uses a gossip protocol where each node
    relays new blocks to its peers, and forks are resolved by the longest
    (most proof-of-work) chain rule.
"""

import hashlib   # For block hashing
import random    # For peer selection and network topology
import time      # For block timestamps

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Number of nodes in the simulated network
NUM_NODES = 10

# How many peers each node tries to maintain — real Bitcoin nodes target ~8
# outbound connections; we use fewer for clearer demo output
MAX_PEERS = 3

# Number of bootstrap nodes that new nodes connect to first —
# in Bitcoin, these are hardcoded DNS seeds
NUM_BOOTSTRAP_NODES = 2

# Fixed seed so the demo output is reproducible across runs
RANDOM_SEED = 42

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# Block — simplified block structure (just enough for P2P simulation)
# ----------------------------------------------------------------------------

class Block:
    """A minimal block: hash, parent hash, height, creator, and payload."""

    def __init__(self, height: int, prev_hash: str, data: str, creator_id: int):
        self.height = height                    # Position in the chain (0 = genesis)
        self.prev_hash = prev_hash              # Hash of the parent block
        self.data = data                        # Arbitrary payload string
        self.creator_id = creator_id            # Which node mined/created this block
        self.timestamp = time.time()            # Creation time (used in hash)
        self.hash = self._compute_hash()        # This block's unique identifier

    def _compute_hash(self) -> str:
        """Hash the block header fields to produce a unique fingerprint."""
        header = f"{self.height}|{self.prev_hash}|{self.data}|{self.creator_id}|{self.timestamp}"
        return hashlib.sha256(header.encode()).hexdigest()[:16]  # Truncate for readability

    def __repr__(self) -> str:
        return f"Block(#{self.height}, hash={self.hash[:8]}…, creator=Node {self.creator_id})"


# ----------------------------------------------------------------------------
# Node — a single participant in the P2P network
# ----------------------------------------------------------------------------

class Node:
    """
    A network node that maintains a blockchain, a set of peers, and
    participates in gossip-based block propagation.
    """

    def __init__(self, node_id: int):
        self.id = node_id                       # Unique identifier for this node
        self.peers: list[int] = []              # IDs of nodes we're connected to
        self.chain: list[Block] = []            # Our local copy of the blockchain
        self.known_block_hashes: set[str] = set()  # Hashes we've already seen (dedup)
        self.pending_relay: list[Block] = []    # Blocks to forward on the next tick

        # Create the genesis block — every node starts with the same one
        genesis = Block(height=0, prev_hash="0" * 16, data="Genesis", creator_id=-1)
        # Override timestamp so all nodes produce identical genesis hashes
        genesis.timestamp = 0
        genesis.hash = genesis._compute_hash()
        self.chain.append(genesis)
        self.known_block_hashes.add(genesis.hash)

    @property
    def tip(self) -> Block:
        """The block at the top of our current best chain."""
        return self.chain[-1]

    def add_peer(self, peer_id: int) -> None:
        """Establish a bidirectional awareness of another node."""
        if peer_id != self.id and peer_id not in self.peers:
            self.peers.append(peer_id)

    def create_block(self, data: str) -> Block:
        """Mine a new block on top of our current chain tip."""
        block = Block(
            height=self.tip.height + 1,
            prev_hash=self.tip.hash,
            data=data,
            creator_id=self.id,
        )
        self.chain.append(block)
        self.known_block_hashes.add(block.hash)
        # Queue this block to be gossiped to peers on the next tick
        self.pending_relay.append(block)
        return block

    def receive_block(self, block: Block, all_nodes: dict[int, "Node"]) -> bool:
        """
        Process an incoming block from a peer.

        Returns True if the block was new and accepted, False if already known
        or invalid.
        """
        # --- Deduplication: skip blocks we've already seen ---
        if block.hash in self.known_block_hashes:
            return False  # Already have it, don't relay again

        self.known_block_hashes.add(block.hash)

        # --- Check if this block extends our current chain ---
        if block.prev_hash == self.tip.hash and block.height == self.tip.height + 1:
            # Happy path: block fits right on top of our chain
            self.chain.append(block)
            self.pending_relay.append(block)  # Relay to our peers
            return True

        # --- Fork handling: check if the incoming block is part of a longer chain ---
        # Ask the sender's node for their full chain and adopt it if it's longer
        sender_node = all_nodes.get(block.creator_id)
        if sender_node and len(sender_node.chain) > len(self.chain):
            # The sender has a longer chain — adopt it (longest-chain rule)
            if self._validate_chain(sender_node.chain):
                old_height = self.tip.height
                self.chain = list(sender_node.chain)  # Copy the longer chain
                # Record all block hashes from the new chain
                for b in self.chain:
                    self.known_block_hashes.add(b.hash)
                self.pending_relay.append(block)  # Continue relaying
                return True

        return False  # Block doesn't fit and no longer chain found

    def _validate_chain(self, chain: list[Block]) -> bool:
        """Verify that a chain is internally consistent (hash links intact)."""
        for i in range(1, len(chain)):
            if chain[i].prev_hash != chain[i - 1].hash:
                return False  # Broken link in the chain
            if chain[i].height != chain[i - 1].height + 1:
                return False  # Height gap
        return True

    def get_relay_targets(self) -> list[int]:
        """Return the list of peers we'll gossip to on this tick."""
        return list(self.peers)  # In real networks, nodes might select a subset


# ----------------------------------------------------------------------------
# Network — orchestrates all nodes and simulates the passage of time
# ----------------------------------------------------------------------------

class Network:
    """
    Manages the set of nodes, handles peer discovery, and runs the
    tick-by-tick gossip simulation.
    """

    def __init__(self, num_nodes: int, max_peers: int, num_bootstrap: int):
        self.nodes: dict[int, Node] = {}
        self.max_peers = max_peers
        self.num_bootstrap = num_bootstrap
        self.propagation_log: list[str] = []  # Human-readable log of each tick

        # --- Create all nodes ---
        for i in range(num_nodes):
            self.nodes[i] = Node(node_id=i)

        # --- Peer discovery ---
        self._bootstrap_peers()
        self._random_peer_exchange()
        self._enforce_max_peers()  # Trim over-connected nodes

    # ---- Peer discovery: bootstrap ----

    def _bootstrap_peers(self) -> None:
        """
        Connect every node to ONE randomly chosen bootstrap node (not all of them).
        In Bitcoin, nodes query DNS seeds and connect to a small subset.
        We limit this to keep the topology sparse so gossip takes multiple hops.
        """
        bootstrap_ids = list(range(self.num_bootstrap))  # Node 0, 1 are bootstraps

        # Connect bootstrap nodes to each other first
        for i, boot_id in enumerate(bootstrap_ids):
            for other_boot in bootstrap_ids:
                if boot_id != other_boot:
                    self.nodes[boot_id].add_peer(other_boot)

        # Each non-bootstrap node connects to one random bootstrap node
        for node_id, node in self.nodes.items():
            if node_id in bootstrap_ids:
                continue  # Already connected above
            chosen_boot = random.choice(bootstrap_ids)
            node.add_peer(chosen_boot)
            self.nodes[chosen_boot].add_peer(node_id)

    # ---- Peer discovery: random peer exchange ----

    def _random_peer_exchange(self) -> None:
        """
        Each node asks its existing peers for THEIR peer lists, then
        randomly connects to some of those. This builds a more connected
        and resilient topology — similar to Bitcoin's addr message exchange.
        """
        for node_id, node in self.nodes.items():
            # Gather candidates from our peers' peer lists
            candidates: set[int] = set()
            for peer_id in node.peers:
                peer_node = self.nodes[peer_id]
                for second_hop in peer_node.peers:
                    if second_hop != node_id and second_hop not in node.peers:
                        candidates.add(second_hop)

            # Connect to random candidates up to our max peer limit
            candidates_list = sorted(candidates)  # Sort for reproducibility
            random.shuffle(candidates_list)
            for candidate in candidates_list:
                if len(node.peers) >= self.max_peers:
                    break  # We have enough peers
                node.add_peer(candidate)
                self.nodes[candidate].add_peer(node_id)  # Bidirectional

    def _enforce_max_peers(self) -> None:
        """
        Trim each node's peer list down to max_peers.
        Bootstrap nodes often accumulate many connections during discovery;
        this simulates real-world connection limits (Bitcoin caps at ~125 total).
        """
        for node_id, node in self.nodes.items():
            if len(node.peers) > self.max_peers:
                # Keep a random subset; sort first for reproducibility
                peers_sorted = sorted(node.peers)
                random.shuffle(peers_sorted)
                kept = set(peers_sorted[:self.max_peers])
                dropped = set(peers_sorted[self.max_peers:])
                node.peers = list(kept)
                # Remove reverse links from dropped peers
                for dropped_id in dropped:
                    peer_node = self.nodes[dropped_id]
                    if node_id in peer_node.peers:
                        peer_node.peers.remove(node_id)

    # ---- Gossip propagation engine ----

    def propagate(self) -> list[dict]:
        """
        Run tick-by-tick gossip until all nodes have received all pending blocks.

        Returns a list of per-tick records for display.
        """
        ticks = []
        tick = 0

        while True:
            # Collect which nodes have blocks to relay this tick
            relays: list[tuple[int, int, Block]] = []  # (sender, receiver, block)

            for node_id, node in self.nodes.items():
                if not node.pending_relay:
                    continue  # Nothing to send

                targets = node.get_relay_targets()
                for block in node.pending_relay:
                    for peer_id in targets:
                        relays.append((node_id, peer_id, block))

                node.pending_relay.clear()  # We've handed off our blocks

            if not relays:
                break  # No more gossip activity — propagation complete

            # Process all relays for this tick
            tick_record = {"tick": tick, "deliveries": []}
            newly_received: dict[int, list[int]] = {}  # receiver → [senders]

            for sender_id, receiver_id, block in relays:
                receiver = self.nodes[receiver_id]
                accepted = receiver.receive_block(block, self.nodes)
                if accepted:
                    if sender_id not in newly_received:
                        newly_received[sender_id] = []
                    newly_received[sender_id].append(receiver_id)

            tick_record["deliveries"] = newly_received
            ticks.append(tick_record)
            tick += 1

            # Safety: prevent infinite loops in case of bugs
            if tick > 50:
                break

        return ticks

    # ---- Fork simulation ----

    def simulate_fork(self, node_a_id: int, node_b_id: int) -> tuple[Block, Block]:
        """
        Create a fork: two different nodes each create a block at the same height.
        This simulates what happens when two miners find a block at nearly the
        same time.
        """
        node_a = self.nodes[node_a_id]
        node_b = self.nodes[node_b_id]

        block_a = node_a.create_block(f"Fork-A by Node {node_a_id}")
        block_b = node_b.create_block(f"Fork-B by Node {node_b_id}")

        return block_a, block_b

    def get_chain_tips(self) -> dict[str, list[int]]:
        """Return a mapping of tip hash → list of node IDs that have that tip."""
        tips: dict[str, list[int]] = {}
        for node_id, node in self.nodes.items():
            tip_hash = node.tip.hash
            if tip_hash not in tips:
                tips[tip_hash] = []
            tips[tip_hash].append(node_id)
        return tips


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of P2P gossip propagation and fork resolution."""

    random.seed(RANDOM_SEED)  # Reproducible output

    # ---- Part 1: Network topology ----

    print("=" * 60)
    print("  P2P GOSSIP NETWORK SIMULATION")
    print("=" * 60)
    print()

    net = Network(num_nodes=NUM_NODES, max_peers=MAX_PEERS, num_bootstrap=NUM_BOOTSTRAP_NODES)

    print(f"Network: {NUM_NODES} nodes, {NUM_BOOTSTRAP_NODES} bootstrap nodes, "
          f"max {MAX_PEERS} peers each")
    print()
    print("--- Network Topology ---")
    print()
    for node_id in sorted(net.nodes):
        node = net.nodes[node_id]
        peer_str = ", ".join(f"Node {p}" for p in sorted(node.peers))
        label = " (bootstrap)" if node_id < NUM_BOOTSTRAP_NODES else ""
        print(f"  Node {node_id}{label}: peers = [{peer_str}]")
    print()

    # ---- Part 2: Block propagation via gossip ----

    print("=" * 60)
    print("  BLOCK PROPAGATION VIA GOSSIP")
    print("=" * 60)
    print()

    # Node 0 creates a new block
    block = net.nodes[0].create_block("Alice pays Bob 5 BTC")
    print(f"Tick 0: Node 0 creates {block}")
    print(f"        hash={block.hash}")
    print()

    # Count how many nodes have the block after creation (just node 0)
    nodes_with_block = {0}

    # Run gossip propagation tick by tick
    ticks = net.propagate()

    for record in ticks:
        tick = record["tick"] + 1  # +1 because tick 0 was the creation
        deliveries = record["deliveries"]

        # Build a readable description of this tick's gossip
        parts = []
        for sender_id in sorted(deliveries):
            receivers = sorted(deliveries[sender_id])
            receiver_str = ", ".join(f"Node {r}" for r in receivers)
            parts.append(f"Node {sender_id} → [{receiver_str}]")
            nodes_with_block.update(receivers)

        nodes_with_block.update(deliveries.keys())  # Senders also have it
        delivery_str = ", ".join(parts) if parts else "(no new deliveries)"

        print(f"Tick {tick}: {delivery_str}")
        print(f"        ({len(nodes_with_block)}/{NUM_NODES} nodes have the block)")
        print()

    if len(nodes_with_block) == NUM_NODES:
        print(f"✓ All {NUM_NODES} nodes received Block #{block.height} "
              f"in {len(ticks)} ticks")
    print()

    # ---- Part 3: Fork creation and resolution ----

    print("=" * 60)
    print("  FORK CREATION AND RESOLUTION")
    print("=" * 60)
    print()

    # Reset the network for a clean fork demo
    random.seed(RANDOM_SEED + 1)
    net2 = Network(num_nodes=NUM_NODES, max_peers=MAX_PEERS, num_bootstrap=NUM_BOOTSTRAP_NODES)

    # Two nodes create competing blocks at the same height
    node_a_id, node_b_id = 3, 7
    block_a, block_b = net2.simulate_fork(node_a_id, node_b_id)

    print(f"Two nodes create blocks at the same height (fork!):")
    print()
    print(f"  Node {node_a_id} creates: {block_a}")
    print(f"    hash = {block_a.hash}")
    print(f"  Node {node_b_id} creates: {block_b}")
    print(f"    hash = {block_b.hash}")
    print()

    # Show the fork visually
    genesis_hash = net2.nodes[0].chain[0].hash[:8]
    print(f"         Genesis ({genesis_hash}…)")
    print(f"              │")
    print(f"       ┌──────┴──────┐")
    print(f"       │             │")
    print(f"  Block A         Block B")
    print(f"  ({block_a.hash[:8]}…)   ({block_b.hash[:8]}…)")
    print(f"  by Node {node_a_id}       by Node {node_b_id}")
    print()

    # Propagate both competing blocks
    ticks = net2.propagate()
    print(f"Propagating both blocks through the network...")
    print()

    # Show which chain each node ended up on
    tips = net2.get_chain_tips()
    print("--- Chain tips after fork propagation ---")
    print()
    for tip_hash, node_ids in sorted(tips.items(), key=lambda x: -len(x[1])):
        node_list = ", ".join(f"Node {n}" for n in sorted(node_ids))
        # Determine which fork this tip belongs to
        if tip_hash == block_a.hash:
            label = f"Block A (by Node {node_a_id})"
        elif tip_hash == block_b.hash:
            label = f"Block B (by Node {node_b_id})"
        else:
            label = "Genesis (no fork block received yet)"
        print(f"  Tip {tip_hash[:8]}… ({label}):")
        print(f"    Nodes: [{node_list}]")
        print()

    # Now resolve the fork: node_a_id mines another block, making chain A longer
    print("--- Resolving the fork (longest-chain rule) ---")
    print()

    resolver = net2.nodes[node_a_id]
    resolve_block = resolver.create_block(f"Node {node_a_id} extends chain A")
    print(f"Node {node_a_id} mines Block #{resolve_block.height} on top of Block A")
    print(f"  Chain A is now length {len(resolver.chain)} (longer than chain B)")
    print()

    print(f"         Genesis ({genesis_hash}…)")
    print(f"              │")
    print(f"       ┌──────┴──────┐")
    print(f"       │             │")
    print(f"  Block A         Block B")
    print(f"  ({block_a.hash[:8]}…)   ({block_b.hash[:8]}…)")
    print(f"       │          (orphaned)")
    print(f"  Block #{resolve_block.height}")
    print(f"  ({resolve_block.hash[:8]}…)")
    print(f"  by Node {node_a_id}")
    print()

    # Propagate the longer chain
    ticks = net2.propagate()
    print(f"Propagating the longer chain...")
    print()

    # Check final state
    tips_after = net2.get_chain_tips()
    print("--- Chain tips after fork resolution ---")
    print()
    for tip_hash, node_ids in sorted(tips_after.items(), key=lambda x: -len(x[1])):
        node_list = ", ".join(f"Node {n}" for n in sorted(node_ids))
        print(f"  Tip {tip_hash[:8]}… : [{node_list}]")

    if len(tips_after) == 1:
        print()
        print(f"✓ Fork resolved! All nodes converged to the longest chain")
    else:
        # Some nodes may still have the shorter chain if they weren't
        # directly connected to the resolver — show this honestly
        longest_tip = max(tips_after.items(), key=lambda x: len(x[1]))
        print()
        print(f"  {len(longest_tip[1])}/{NUM_NODES} nodes on the longest chain")
        print(f"  (remaining nodes will converge in subsequent ticks)")

    print()

    # ---- Part 4: Network statistics ----

    print("=" * 60)
    print("  NETWORK STATISTICS")
    print("=" * 60)
    print()

    # Show connectivity stats
    peer_counts = [len(net2.nodes[i].peers) for i in range(NUM_NODES)]
    avg_peers = sum(peer_counts) / len(peer_counts)
    print(f"  Average peers per node:  {avg_peers:.1f}")
    print(f"  Min peers:               {min(peer_counts)}")
    print(f"  Max peers:               {max(peer_counts)}")
    print()

    # Show chain lengths
    chain_lengths = [len(net2.nodes[i].chain) for i in range(NUM_NODES)]
    print(f"  Chain lengths across nodes: {chain_lengths}")
    print(f"  All nodes agree on chain:   {'Yes' if len(set(chain_lengths)) == 1 else 'No'}")
    print()

    print("KEY TAKEAWAYS:")
    print("  • Gossip ensures blocks reach all nodes in O(log N) ticks")
    print("  • Forks are natural — they happen when two nodes mine simultaneously")
    print("  • Longest-chain rule provides eventual consistency")
    print("  • More peers = faster propagation, but more bandwidth")


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
