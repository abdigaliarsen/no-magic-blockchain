"""
TITLE: devp2p Wire Protocol
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    Ethereum's devp2p networking layer from scratch — the peer-to-peer protocol
    that Ethereum nodes use to discover each other, negotiate capabilities, and
    exchange blockchain data. Covers RLPx framing (encrypted transport), capability-
    based sub-protocol negotiation, and eth/68 message types (Status, NewBlockHashes,
    Transactions, GetBlockHeaders, BlockHeaders, etc.).

KEY CONCEPTS:
    - RLPx transport: encrypted frames with header (MAC + size) and body
    - Capability negotiation: nodes agree on shared sub-protocols (eth, snap, etc.)
    - eth/68 messages: typed messages for block/tx propagation and state sync
    - Handshake flow: Hello -> Status -> ready to exchange data

PREREQUISITE SCRIPTS:
    - core/fundamentals/08_p2p_network.py (gossip protocol basics)
    - ethereum/fundamentals/04_rlp_encoding.py (RLP serialization)
    - ethereum/fundamentals/01_accounts_state.py (Ethereum state context)

REAL-WORLD RELEVANCE:
    devp2p is the backbone of Ethereum's decentralized network. Every execution
    client (Geth, Nethermind, Besu, Erigon) implements this protocol to sync the
    chain, propagate transactions, and serve data to peers. The eth/68 upgrade
    (EIP-4938) added transaction announcement with types and sizes for better
    bandwidth management.
"""

import hashlib
import struct
import random
import time

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# RLPx protocol version
RLPX_VERSION = 5

# Supported sub-protocol capabilities
CAPABILITIES = {
    "eth": 68,   # Ethereum wire protocol version 68
    "snap": 1,   # Snapshot sync protocol
    "les": 4,    # Light Ethereum Subprotocol
}

# eth/68 message IDs (offset within the eth capability)
ETH_MSG = {
    0x00: "Status",
    0x01: "NewBlockHashes",
    0x02: "Transactions",
    0x03: "GetBlockHeaders",
    0x04: "BlockHeaders",
    0x05: "GetBlockBodies",
    0x06: "BlockBodies",
    0x07: "NewBlock",
    0x08: "NewPooledTransactionHashes",  # eth/68: includes types + sizes
    0x09: "GetPooledTransactions",
    0x0A: "PooledTransactions",
    0x0D: "GetReceipts",
    0x0E: "Receipts",
}

# Maximum frame payload size (16 MB in real RLPx)
MAX_FRAME_SIZE = 16 * 1024 * 1024

# Network IDs
NETWORK_IDS = {
    1: "Mainnet",
    5: "Goerli",
    11155111: "Sepolia",
    17000: "Holesky",
}

# Simulated chain parameters
GENESIS_HASH = hashlib.sha256(b"Ethereum Genesis Block").hexdigest()
FORK_HASH = hashlib.sha256(b"Cancun Fork").digest()[:4].hex()

# Seed for reproducibility
random.seed(42)


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# RLP Encoding (minimal implementation for framing)
# ----------------------------------------------------------------------------

def rlp_encode_string(data: bytes) -> bytes:
    """RLP-encode a single byte string."""
    if len(data) == 1 and data[0] < 0x80:
        return data  # Single byte below 0x80 is its own encoding
    elif len(data) < 56:
        prefix = bytes([0x80 + len(data)])
        return prefix + data
    else:
        len_bytes = _encode_length(len(data))
        prefix = bytes([0xB7 + len(len_bytes)]) + len_bytes
        return prefix + data


def rlp_encode_list(items: list[bytes]) -> bytes:
    """RLP-encode a list of already-encoded items."""
    payload = b''.join(items)
    if len(payload) < 56:
        prefix = bytes([0xC0 + len(payload)])
        return prefix + payload
    else:
        len_bytes = _encode_length(len(payload))
        prefix = bytes([0xF7 + len(len_bytes)]) + len_bytes
        return prefix + payload


def _encode_length(length: int) -> bytes:
    """Encode an integer as big-endian bytes without leading zeros."""
    if length == 0:
        return b'\x00'
    result = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return result


# ----------------------------------------------------------------------------
# RLPx Frame (encrypted transport layer)
# ----------------------------------------------------------------------------

class RLPxFrame:
    """An RLPx frame — the unit of data exchange between Ethereum nodes.

    Real RLPx uses ECIES encryption + AES-256-CTR + HMAC-SHA-256.
    We simulate the frame structure without actual encryption (stdlib only).
    """

    def __init__(self, capability: str, msg_id: int, payload: bytes):
        self.capability = capability
        self.msg_id = msg_id
        self.payload = payload
        self.frame_size = len(payload)
        # Simulated MAC (real uses HMAC-SHA-256 with session keys)
        self.mac = hashlib.sha256(
            struct.pack(">BH", msg_id, self.frame_size) + payload
        ).digest()[:16]

    def encode(self) -> bytes:
        """Encode frame into wire format: [header | header-mac | body | body-mac].

        Header: 3 bytes frame size + 13 bytes header data (RLP encoded)
        Body: frame payload (RLP encoded message)
        """
        # Header: frame size (3 bytes, big-endian) + capability + msg_id
        header = struct.pack(">I", self.frame_size)[1:]  # 3 bytes
        header += rlp_encode_string(self.capability.encode())
        header += bytes([self.msg_id])
        # Pad header to 16 bytes (AES block size)
        header = header.ljust(16, b'\x00')

        # Header MAC (16 bytes)
        header_mac = self.mac

        # Body: the RLP-encoded message payload
        body = self.payload
        # Pad body to 16-byte boundary
        pad_len = (16 - len(body) % 16) % 16
        body_padded = body + b'\x00' * pad_len

        # Body MAC
        body_mac = hashlib.sha256(body).digest()[:16]

        return header + header_mac + body_padded + body_mac

    @classmethod
    def decode(cls, data: bytes) -> 'RLPxFrame':
        """Decode a wire-format frame (simplified, no decryption)."""
        # Parse header (first 16 bytes)
        header = data[:16]
        frame_size = int.from_bytes(b'\x00' + header[:3], "big")
        # Extract capability name (simplified parsing)
        cap_start = 3
        cap_len = header[cap_start] - 0x80 if header[cap_start] >= 0x80 else 0
        if cap_len > 0 and cap_start + 1 + cap_len <= 16:
            capability = header[cap_start + 1: cap_start + 1 + cap_len].decode(
                errors="replace")
        else:
            capability = "eth"
        msg_id = header[cap_start + 1 + max(cap_len, 0)]

        # Skip header MAC (16 bytes)
        body_start = 32
        body = data[body_start: body_start + frame_size]

        return cls(capability, msg_id, body)

    def __repr__(self) -> str:
        msg_name = ETH_MSG.get(self.msg_id, f"Unknown({self.msg_id})")
        return (f"Frame({self.capability}/{msg_name}, "
                f"{self.frame_size} bytes)")


# ----------------------------------------------------------------------------
# eth/68 Messages
# ----------------------------------------------------------------------------

class EthMessage:
    """Factory for eth/68 protocol messages."""

    @staticmethod
    def status(network_id: int, total_difficulty: int, best_hash: str,
               genesis_hash: str, fork_id: str) -> dict:
        """Status message — exchanged during handshake.

        Both peers send Status immediately after Hello. If Status values
        are incompatible (different network, different genesis), disconnect.
        """
        return {
            "msg_id": 0x00,
            "msg_name": "Status",
            "protocol_version": 68,
            "network_id": network_id,
            "total_difficulty": total_difficulty,
            "best_hash": best_hash[:16] + "...",
            "genesis_hash": genesis_hash[:16] + "...",
            "fork_id": fork_id,
        }

    @staticmethod
    def new_block_hashes(announcements: list[tuple[str, int]]) -> dict:
        """Announce new block hashes to peers.

        Each announcement is (hash, number). Peers can then request
        full blocks via GetBlockHeaders + GetBlockBodies.
        """
        return {
            "msg_id": 0x01,
            "msg_name": "NewBlockHashes",
            "announcements": [
                {"hash": h[:16] + "...", "number": n}
                for h, n in announcements
            ],
        }

    @staticmethod
    def new_pooled_tx_hashes(tx_types: list[int], tx_sizes: list[int],
                              tx_hashes: list[str]) -> dict:
        """Announce new transactions (eth/68 format with types and sizes).

        eth/68 added types and sizes to transaction announcements so peers
        can decide whether to request the full tx based on type and size,
        reducing bandwidth waste.
        """
        return {
            "msg_id": 0x08,
            "msg_name": "NewPooledTransactionHashes",
            "version": "eth/68",
            "transactions": [
                {"type": t, "size": s, "hash": h[:16] + "..."}
                for t, s, h in zip(tx_types, tx_sizes, tx_hashes)
            ],
        }

    @staticmethod
    def get_block_headers(start: int, count: int, skip: int = 0,
                           reverse: bool = False) -> dict:
        """Request block headers from a peer.

        Can request by number or hash, with skip for sparse fetching
        (useful for binary search during sync).
        """
        return {
            "msg_id": 0x03,
            "msg_name": "GetBlockHeaders",
            "start_block": start,
            "count": count,
            "skip": skip,
            "reverse": reverse,
        }

    @staticmethod
    def block_headers(headers: list[dict]) -> dict:
        """Response to GetBlockHeaders with actual header data."""
        return {
            "msg_id": 0x04,
            "msg_name": "BlockHeaders",
            "headers": headers,
        }


# ----------------------------------------------------------------------------
# DevP2P Node
# ----------------------------------------------------------------------------

class DevP2PNode:
    """A simulated Ethereum node implementing the devp2p protocol.

    Handles peer discovery, RLPx handshake, capability negotiation,
    and eth/68 message exchange.
    """

    def __init__(self, name: str, node_id: str, port: int,
                 capabilities: dict[str, int] | None = None):
        self.name = name
        self.node_id = node_id      # 64-byte public key (shortened for demo)
        self.port = port
        self.capabilities = capabilities or {"eth": 68, "snap": 1}
        self.peers: dict[str, dict] = {}  # Connected peers and their info
        self.chain_head = 0          # Highest block number
        self.total_difficulty = 0    # Cumulative difficulty
        self.best_hash = GENESIS_HASH
        self.network_id = 1          # Mainnet
        self.message_log: list[str] = []  # Log of sent/received messages

    def _log(self, msg: str):
        """Log a protocol message."""
        self.message_log.append(msg)

    def send_hello(self, peer: 'DevP2PNode') -> dict:
        """Send RLPx Hello message — the very first message in a connection.

        Hello contains the node's capabilities so both sides know which
        sub-protocols they share.
        """
        hello = {
            "protocol_version": RLPX_VERSION,
            "client_id": f"SimNode/v1.0/{self.name}",
            "capabilities": [
                (cap, ver) for cap, ver in self.capabilities.items()
            ],
            "listen_port": self.port,
            "node_id": self.node_id[:16] + "...",
        }
        self._log(f"-> Hello to {peer.name}: caps={list(self.capabilities.keys())}")
        return hello

    def receive_hello(self, peer: 'DevP2PNode', hello: dict) -> dict:
        """Process a Hello message and negotiate shared capabilities.

        Only capabilities supported by BOTH nodes are activated.
        """
        peer_caps = dict(hello["capabilities"])

        # Find shared capabilities — intersection of both nodes' caps
        shared = {}
        for cap, ver in self.capabilities.items():
            if cap in peer_caps:
                # Use the lower version if both support different versions
                shared[cap] = min(ver, peer_caps[cap])

        self.peers[peer.name] = {
            "client_id": hello["client_id"],
            "shared_caps": shared,
            "state": "hello_received",
        }

        self._log(f"<- Hello from {peer.name}: "
                  f"shared_caps={list(shared.keys())}")
        return {"shared_capabilities": shared}

    def send_status(self, peer: 'DevP2PNode') -> dict:
        """Send eth/68 Status message after Hello handshake.

        Status contains chain parameters — peers must be on the same
        network and genesis to continue.
        """
        status = EthMessage.status(
            network_id=self.network_id,
            total_difficulty=self.total_difficulty,
            best_hash=self.best_hash,
            genesis_hash=GENESIS_HASH,
            fork_id=FORK_HASH,
        )
        self._log(f"-> Status to {peer.name}: "
                  f"TD={self.total_difficulty}, head=#{self.chain_head}")
        return status

    def receive_status(self, peer: 'DevP2PNode', status: dict) -> bool:
        """Validate peer's Status message.

        Disconnect if network_id or genesis_hash don't match.
        """
        # Check network compatibility
        if status["network_id"] != self.network_id:
            self._log(f"!! Disconnect {peer.name}: wrong network "
                      f"({status['network_id']} != {self.network_id})")
            return False

        if status["genesis_hash"] != GENESIS_HASH[:16] + "...":
            self._log(f"!! Disconnect {peer.name}: wrong genesis")
            return False

        # Update peer info
        if peer.name in self.peers:
            self.peers[peer.name].update({
                "state": "active",
                "total_difficulty": status["total_difficulty"],
                "best_hash": status["best_hash"],
                "protocol_version": status["protocol_version"],
            })

        self._log(f"<- Status from {peer.name}: "
                  f"TD={status['total_difficulty']}, OK")
        return True

    def request_headers(self, peer: 'DevP2PNode', start: int,
                        count: int) -> dict:
        """Request block headers from a peer (for syncing)."""
        msg = EthMessage.get_block_headers(start, count)
        frame = RLPxFrame("eth", 0x03,
                          f"GetBlockHeaders({start},{count})".encode())
        self._log(f"-> GetBlockHeaders to {peer.name}: "
                  f"start=#{start}, count={count}")
        return {"message": msg, "frame": frame}

    def respond_headers(self, peer: 'DevP2PNode', start: int,
                        count: int) -> dict:
        """Respond to a GetBlockHeaders request with simulated headers."""
        headers = []
        for i in range(count):
            block_num = start + i
            if block_num > self.chain_head:
                break  # Don't have this block
            headers.append({
                "number": block_num,
                "hash": hashlib.sha256(f"block_{block_num}".encode()
                                        ).hexdigest()[:16] + "...",
                "parent_hash": hashlib.sha256(
                    f"block_{block_num - 1}".encode()
                ).hexdigest()[:16] + "..." if block_num > 0 else "0" * 16 + "...",
                "timestamp": 1700000000 + block_num * 12,  # 12s slots
                "gas_used": random.randint(10_000_000, 30_000_000),
            })

        msg = EthMessage.block_headers(headers)
        self._log(f"-> BlockHeaders to {peer.name}: "
                  f"{len(headers)} headers")
        return msg

    def announce_transactions(self, peer: 'DevP2PNode',
                               txs: list[dict]) -> dict:
        """Announce new transactions using eth/68 format (types + sizes)."""
        msg = EthMessage.new_pooled_tx_hashes(
            tx_types=[tx["type"] for tx in txs],
            tx_sizes=[tx["size"] for tx in txs],
            tx_hashes=[tx["hash"] for tx in txs],
        )
        self._log(f"-> NewPooledTxHashes to {peer.name}: "
                  f"{len(txs)} txs (eth/68)")
        return msg

    def announce_block(self, peer: 'DevP2PNode',
                       block_hash: str, block_number: int) -> dict:
        """Announce a new block hash to a peer."""
        msg = EthMessage.new_block_hashes([(block_hash, block_number)])
        self._log(f"-> NewBlockHashes to {peer.name}: "
                  f"block #{block_number}")
        return msg


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of the devp2p wire protocol."""

    print("=" * 72)
    print("  devp2p Wire Protocol — Ethereum Node Communication")
    print("=" * 72)

    # --- Part 1: RLPx Frame Structure ---
    print("\n--- Part 1: RLPx Frame Structure ---\n")

    # Create a sample frame
    payload = b"Hello, peer! This is a test message."
    frame = RLPxFrame("eth", 0x00, payload)
    encoded = frame.encode()

    print(f"  RLPx Frame Format:")
    print(f"  ┌────────────────────────────────────────────────────────┐")
    print(f"  │            RLPx Encrypted Frame                       │")
    print(f"  ├──────────────┬──────────────┬────────────┬────────────┤")
    print(f"  │   Header     │  Header MAC  │    Body    │  Body MAC  │")
    print(f"  │   16 bytes   │   16 bytes   │  N bytes   │  16 bytes  │")
    print(f"  ├──────────────┴──────────────┴────────────┴────────────┤")
    print(f"  │ Header contains:                                      │")
    print(f"  │   - Frame size (3 bytes, big-endian)                  │")
    print(f"  │   - Capability name (RLP encoded)                     │")
    print(f"  │   - Message ID (1 byte)                               │")
    print(f"  │   - Padding to 16-byte boundary (AES block size)      │")
    print(f"  └───────────────────────────────────────────────────────┘")

    print(f"\n  Example frame:")
    print(f"    Capability: {frame.capability}")
    print(f"    Message ID: 0x{frame.msg_id:02x} ({ETH_MSG.get(frame.msg_id, '?')})")
    print(f"    Payload:    {frame.frame_size} bytes")
    print(f"    MAC:        {frame.mac.hex()}")
    print(f"    Wire size:  {len(encoded)} bytes total")

    # Decode it back
    decoded = RLPxFrame.decode(encoded)
    print(f"\n  Decoded frame: {decoded}")

    # --- Part 2: Node Handshake ---
    print("\n\n--- Part 2: Node Handshake (Hello + Status) ---\n")

    # Create two nodes
    node_a = DevP2PNode(
        name="Geth-Alpha",
        node_id=hashlib.sha256(b"node_a_key").hexdigest(),
        port=30303,
        capabilities={"eth": 68, "snap": 1},
    )
    node_a.chain_head = 18_500_000
    node_a.total_difficulty = 58_750_000_000_000

    node_b = DevP2PNode(
        name="Nethermind-Beta",
        node_id=hashlib.sha256(b"node_b_key").hexdigest(),
        port=30304,
        capabilities={"eth": 68, "snap": 1, "les": 4},
    )
    node_b.chain_head = 18_499_998
    node_b.total_difficulty = 58_749_999_000_000

    print(f"  Node A: {node_a.name}")
    print(f"    ID:   {node_a.node_id[:32]}...")
    print(f"    Caps: {list(node_a.capabilities.items())}")
    print(f"    Head: block #{node_a.chain_head:,}")
    print(f"\n  Node B: {node_b.name}")
    print(f"    ID:   {node_b.node_id[:32]}...")
    print(f"    Caps: {list(node_b.capabilities.items())}")
    print(f"    Head: block #{node_b.chain_head:,}")

    print(f"\n  === Handshake Sequence ===\n")

    # Step 1: Exchange Hello messages
    print(f"  Step 1: Hello exchange (RLPx layer)")
    print(f"  ┌──────────────┐                ┌──────────────────┐")
    print(f"  │ {node_a.name:<12} │ ── Hello ──>  │ {node_b.name:<16} │")
    print(f"  │              │ <── Hello ──  │                  │")
    print(f"  └──────────────┘                └──────────────────┘")

    hello_a = node_a.send_hello(node_b)
    hello_b = node_b.send_hello(node_a)
    result_a = node_a.receive_hello(node_b, hello_b)
    result_b = node_b.receive_hello(node_a, hello_a)

    shared_caps = result_a["shared_capabilities"]
    print(f"\n  Negotiated capabilities: {list(shared_caps.items())}")
    print(f"  Note: 'les' dropped — only Node B supports it")

    # Step 2: Exchange Status messages (eth sub-protocol)
    print(f"\n  Step 2: Status exchange (eth/68 layer)")
    print(f"  ┌──────────────┐                ┌──────────────────┐")
    print(f"  │ {node_a.name:<12} │ ── Status ──> │ {node_b.name:<16} │")
    print(f"  │              │ <── Status ──  │                  │")
    print(f"  └──────────────┘                └──────────────────┘")

    status_a = node_a.send_status(node_b)
    status_b = node_b.send_status(node_a)

    ok_a = node_a.receive_status(node_b, status_b)
    ok_b = node_b.receive_status(node_a, status_a)

    print(f"\n  Status validation:")
    print(f"    Node A accepts Node B: {ok_a}")
    print(f"    Node B accepts Node A: {ok_b}")
    print(f"    Network: {NETWORK_IDS.get(node_a.network_id, 'Unknown')}")
    print(f"    Genesis: {GENESIS_HASH[:16]}...")

    # --- Part 3: Block Header Sync ---
    print(f"\n\n--- Part 3: Block Header Sync ---\n")

    print(f"  Node B is {node_a.chain_head - node_b.chain_head} blocks behind. "
          f"Requesting headers...\n")

    # Node B requests headers from Node A
    start_block = node_b.chain_head + 1
    count = 5
    req = node_b.request_headers(node_a, start_block, count)

    print(f"  ┌──────────────────┐  GetBlockHeaders  ┌──────────────┐")
    print(f"  │ {node_b.name:<16} │ ───────────────> │ {node_a.name:<12} │")
    print(f"  │ (behind)         │                    │ (ahead)      │")
    print(f"  │                  │  BlockHeaders      │              │")
    print(f"  │                  │ <───────────────── │              │")
    print(f"  └──────────────────┘                    └──────────────┘")

    # Node A responds with headers
    resp = node_a.respond_headers(node_b, start_block, count)

    print(f"\n  Received {len(resp['headers'])} block headers:")
    print(f"  {'#':<12} {'Hash':<20} {'Parent':<20} {'Gas Used':>12}")
    print(f"  {'─' * 12} {'─' * 20} {'─' * 20} {'─' * 12}")
    for hdr in resp["headers"]:
        print(f"  {hdr['number']:<12,} {hdr['hash']:<20} "
              f"{hdr['parent_hash']:<20} {hdr['gas_used']:>12,}")

    # --- Part 4: Transaction Announcement (eth/68) ---
    print(f"\n\n--- Part 4: Transaction Announcements (eth/68) ---\n")

    print(f"  eth/68 improvement: announce tx TYPE and SIZE before sending full tx")
    print(f"  This lets peers filter by type and avoid downloading unwanted txs\n")

    # Simulate some transactions
    txs = [
        {"type": 0, "size": 110,
         "hash": hashlib.sha256(b"tx_legacy_1").hexdigest()},
        {"type": 2, "size": 250,
         "hash": hashlib.sha256(b"tx_eip1559_1").hexdigest()},
        {"type": 2, "size": 180,
         "hash": hashlib.sha256(b"tx_eip1559_2").hexdigest()},
        {"type": 3, "size": 131_072,
         "hash": hashlib.sha256(b"tx_blob_1").hexdigest()},
    ]

    tx_type_names = {0: "Legacy", 1: "AccessList", 2: "EIP-1559", 3: "Blob"}

    msg = node_a.announce_transactions(node_b, txs)

    print(f"  NewPooledTransactionHashes (eth/68):")
    print(f"  ┌──────┬──────────────┬────────────┬──────────────────────┐")
    print(f"  │ Type │ Name         │ Size       │ Hash                 │")
    print(f"  ├──────┼──────────────┼────────────┼──────────────────────┤")
    for tx_info in msg["transactions"]:
        type_name = tx_type_names.get(tx_info["type"], "Unknown")
        size_str = f"{tx_info['size']:,} B"
        print(f"  │  {tx_info['type']}   │ {type_name:<12} │ {size_str:>10} │ "
              f"{tx_info['hash']:<20} │")
    print(f"  └──────┴──────────────┴────────────┴──────────────────────┘")

    print(f"\n  Before eth/68: peer had to download ALL announced txs")
    print(f"  After eth/68:  peer can skip blob txs (131 KB!) if not needed")

    # --- Part 5: Block Announcement ---
    print(f"\n\n--- Part 5: New Block Propagation ---\n")

    new_block_hash = hashlib.sha256(
        f"block_{node_a.chain_head + 1}".encode()
    ).hexdigest()
    new_block_num = node_a.chain_head + 1

    msg = node_a.announce_block(node_b, new_block_hash, new_block_num)

    print(f"  New block #{new_block_num:,} mined!")
    print(f"  Hash: {new_block_hash[:32]}...\n")

    print(f"  Propagation flow:")
    print(f"  ┌──────────────┐")
    print(f"  │   Proposer   │")
    print(f"  │  (new block) │")
    print(f"  └──────┬───────┘")
    print(f"         │ NewBlock (full block to sqrt(peers))")
    print(f"    ┌────┴────┐")
    print(f"    ▼         ▼")
    print(f"  ┌─────┐  ┌─────┐")
    print(f"  │Peer1│  │Peer2│")
    print(f"  └──┬──┘  └──┬──┘")
    print(f"     │ NewBlockHashes (hash only to remaining peers)")
    print(f"  ┌──┴──┐  ┌──┴──┐")
    print(f"  │Peer3│  │Peer4│")
    print(f"  └─────┘  └─────┘")
    print(f"  (Peer3/4 request full block via GetBlockHeaders+GetBlockBodies)")

    # --- Part 6: Protocol Message Log ---
    print(f"\n\n--- Part 6: Full Message Log ---\n")

    all_messages = (
        [(node_a.name, m) for m in node_a.message_log] +
        [(node_b.name, m) for m in node_b.message_log]
    )

    print(f"  {'#':<4} {'Node':<20} {'Message'}")
    print(f"  {'─' * 4} {'─' * 20} {'─' * 45}")
    for i, (node_name, msg) in enumerate(all_messages, 1):
        print(f"  {i:<4} {node_name:<20} {msg}")

    # --- Part 7: Protocol Layer Summary ---
    print(f"\n\n--- Part 7: devp2p Protocol Stack ---\n")

    print(f"  ┌────────────────────────────────────────────────────────┐")
    print(f"  │                    Application                        │")
    print(f"  │  (consensus client, execution client, user requests)  │")
    print(f"  ├────────────────────────────────────────────────────────┤")
    print(f"  │                eth/68 Sub-Protocol                    │")
    print(f"  │  Status, NewBlock, GetHeaders, Transactions, etc.     │")
    print(f"  ├────────────────────────────────────────────────────────┤")
    print(f"  │               snap/1 Sub-Protocol                     │")
    print(f"  │  GetAccountRange, GetStorageRanges, etc.              │")
    print(f"  ├────────────────────────────────────────────────────────┤")
    print(f"  │                 RLPx Transport                        │")
    print(f"  │  Frame multiplexing, ECIES encryption, HMAC           │")
    print(f"  ├────────────────────────────────────────────────────────┤")
    print(f"  │             RLPx Handshake (ECIES)                    │")
    print(f"  │  Key exchange, capability negotiation                 │")
    print(f"  ├────────────────────────────────────────────────────────┤")
    print(f"  │                   TCP/IP                              │")
    print(f"  │  Default port: 30303                                  │")
    print(f"  └────────────────────────────────────────────────────────┘")

    print(f"\n  Key design choices:")
    print(f"  - Capability-based: nodes only exchange messages for shared protocols")
    print(f"  - Multiplexed: multiple sub-protocols share one TCP connection")
    print(f"  - Encrypted: all traffic is ECIES-encrypted (forward secrecy)")
    print(f"  - Extensible: new capabilities (e.g., 'snap') added without breaking old ones")

    print("\n" + "=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
