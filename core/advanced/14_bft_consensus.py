"""
TITLE: Practical Byzantine Fault Tolerance (PBFT)
CATEGORY: core

WHAT THIS IMPLEMENTS:
    A simulation of the PBFT consensus protocol with 4 nodes (tolerating f=1
    Byzantine fault). Implements the full 3-phase protocol: pre-prepare, prepare,
    and commit. Demonstrates how honest nodes reach agreement even when one node
    is actively malicious and sends conflicting messages.

KEY CONCEPTS:
    - Byzantine fault tolerance: consensus despite arbitrary (malicious) failures
    - 3f+1 minimum nodes to tolerate f Byzantine faults
    - Three-phase protocol: pre-prepare, prepare, commit
    - View changes when the primary (leader) is faulty
    - Quorum requirement: 2f+1 matching messages needed for progress

PREREQUISITE SCRIPTS:
    - core/fundamentals/07_consensus_pos.py (validator-based consensus basics)
    - core/fundamentals/08_p2p_network.py (message passing between nodes)

REAL-WORLD RELEVANCE:
    PBFT is the foundation of permissioned blockchain consensus (Hyperledger Fabric),
    and its ideas underpin Tendermint (Cosmos), HotStuff (Diem/Libra), and the
    finality gadgets in Ethereum's Casper FFG.
"""

import hashlib
import random

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Total nodes in the network. PBFT requires n >= 3f+1 to tolerate f faults.
# With n=4, we can tolerate f=1 Byzantine (malicious) node.
NUM_NODES = 4
MAX_FAULTS = 1  # f = (n-1) // 3

# Quorum size: 2f+1 matching messages needed for agreement
QUORUM = 2 * MAX_FAULTS + 1  # = 3 out of 4

# Message types in PBFT
PRE_PREPARE = "PRE-PREPARE"
PREPARE = "PREPARE"
COMMIT = "COMMIT"
REPLY = "REPLY"

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================


def hash_request(data: str) -> str:
    """Hash a client request to create a unique digest."""
    return hashlib.sha256(data.encode()).hexdigest()[:16]


class Message:
    """A PBFT protocol message sent between nodes."""

    def __init__(self, msg_type: str, view: int, seq: int, digest: str,
                 sender: int, data: str = ""):
        self.type = msg_type      # PRE-PREPARE, PREPARE, COMMIT, or REPLY
        self.view = view          # Current view number (identifies the primary)
        self.seq = seq            # Sequence number for ordering
        self.digest = digest      # Hash of the client request
        self.sender = sender      # Node ID that sent this message
        self.data = data          # Original request data (only in PRE-PREPARE)

    def __repr__(self):
        return f"<{self.type} v={self.view} seq={self.seq} from={self.sender}>"


class PBFTNode:
    """A node participating in PBFT consensus.

    Each node maintains a message log and tracks its state through the
    three phases. The primary (leader) initiates consensus; backups validate.
    """

    def __init__(self, node_id: int, total_nodes: int, is_byzantine: bool = False):
        self.id = node_id
        self.total = total_nodes
        self.is_byzantine = is_byzantine  # Whether this node acts maliciously
        self.view = 0                     # Current view (primary = view mod n)
        self.seq = 0                      # Latest sequence number
        self.message_log = []             # All received messages
        self.prepared = {}                # seq -> True when PREPARED state reached
        self.committed = {}               # seq -> True when COMMITTED state reached
        self.executed = []                # List of executed requests

    @property
    def is_primary(self) -> bool:
        """The primary (leader) is determined by: view mod num_nodes."""
        return self.id == self.view % self.total

    def receive_request(self, request: str) -> list[Message]:
        """Primary receives a client request and broadcasts PRE-PREPARE.

        Only the primary node creates PRE-PREPARE messages. If this node
        is Byzantine, it may send conflicting digests to different nodes.
        """
        if not self.is_primary:
            return []

        self.seq += 1
        digest = hash_request(request)

        if self.is_byzantine:
            # Byzantine primary sends a DIFFERENT digest to confuse nodes
            fake_digest = hash_request(request + "_tampered")
            # Return both real and fake messages — we'll route them separately
            real_msg = Message(PRE_PREPARE, self.view, self.seq, digest,
                               self.id, request)
            fake_msg = Message(PRE_PREPARE, self.view, self.seq, fake_digest,
                               self.id, request + "_tampered")
            self.message_log.append(real_msg)
            return [real_msg, fake_msg]  # Two conflicting pre-prepares
        else:
            msg = Message(PRE_PREPARE, self.view, self.seq, digest,
                          self.id, request)
            self.message_log.append(msg)
            return [msg]

    def handle_pre_prepare(self, msg: Message) -> Message | None:
        """Backup receives PRE-PREPARE, validates it, and broadcasts PREPARE.

        A backup accepts the PRE-PREPARE if:
        1. The view number matches its current view
        2. It hasn't accepted a different PRE-PREPARE for this seq number
        3. The digest matches the hash of the data
        """
        if msg.type != PRE_PREPARE:
            return None

        # Validate: digest must match the data
        expected_digest = hash_request(msg.data)
        if msg.digest != expected_digest:
            # Byzantine primary sent inconsistent digest — reject silently
            return None

        self.message_log.append(msg)

        # Broadcast PREPARE to all other nodes
        prepare = Message(PREPARE, self.view, msg.seq, msg.digest, self.id)
        self.message_log.append(prepare)
        return prepare

    def handle_prepare(self, msg: Message) -> Message | None:
        """Receive a PREPARE message. Once 2f+1 matching PREPAREs are collected,
        the node enters PREPARED state and broadcasts COMMIT.

        The PREPARED state means: enough honest nodes agree on the request's
        digest, so the request will eventually be committed.
        """
        if msg.type != PREPARE:
            return None

        self.message_log.append(msg)

        # Count matching PREPARE messages for this (view, seq, digest)
        matching = [m for m in self.message_log
                    if m.type == PREPARE
                    and m.view == msg.view
                    and m.seq == msg.seq
                    and m.digest == msg.digest]

        # Need 2f+1 matching PREPAREs (including our own) to enter PREPARED
        if len(matching) >= QUORUM and msg.seq not in self.prepared:
            self.prepared[msg.seq] = True
            # Broadcast COMMIT
            commit = Message(COMMIT, self.view, msg.seq, msg.digest, self.id)
            self.message_log.append(commit)
            return commit

        return None

    def handle_commit(self, msg: Message) -> Message | None:
        """Receive a COMMIT message. Once 2f+1 matching COMMITs are collected,
        the node enters COMMITTED state and executes the request.

        COMMITTED means: enough nodes are PREPARED, so the request is final.
        """
        if msg.type != COMMIT:
            return None

        self.message_log.append(msg)

        # Count matching COMMIT messages
        matching = [m for m in self.message_log
                    if m.type == COMMIT
                    and m.view == msg.view
                    and m.seq == msg.seq
                    and m.digest == msg.digest]

        # Need 2f+1 matching COMMITs to execute
        if len(matching) >= QUORUM and msg.seq not in self.committed:
            self.committed[msg.seq] = True
            # Execute the request (find original data from PRE-PREPARE)
            for m in self.message_log:
                if (m.type == PRE_PREPARE and m.seq == msg.seq
                        and m.digest == msg.digest):
                    self.executed.append(m.data)
                    break
            # Send REPLY to client
            reply = Message(REPLY, self.view, msg.seq, msg.digest, self.id)
            return reply

        return None


# ----------------------------------------------------------------------------
# PBFT Network Simulation
# ----------------------------------------------------------------------------

class PBFTNetwork:
    """Simulates a PBFT network with message passing between nodes."""

    def __init__(self, num_nodes: int, byzantine_ids: list[int] = None):
        self.nodes = []
        byzantine_ids = byzantine_ids or []
        for i in range(num_nodes):
            is_byz = i in byzantine_ids
            self.nodes.append(PBFTNode(i, num_nodes, is_byz))
        self.log = []  # Human-readable log of all events

    def _log(self, msg: str):
        """Record an event for display."""
        self.log.append(msg)

    def run_consensus(self, request: str) -> dict:
        """Run full PBFT consensus for a single client request.

        Returns a dict with the results of each phase.
        """
        self.log = []
        primary_id = 0  # View 0 → node 0 is primary

        primary = self.nodes[primary_id]
        self._log(f"Client sends request: '{request}'")
        self._log(f"Primary is Node {primary_id}" +
                  (" (BYZANTINE)" if primary.is_byzantine else ""))

        # === Phase 1: PRE-PREPARE ===
        self._log("\n  --- Phase 1: PRE-PREPARE ---")
        pre_prepares = primary.receive_request(request)

        if not pre_prepares:
            self._log("  ERROR: Primary failed to create PRE-PREPARE")
            return {"success": False, "log": self.log}

        for pp in pre_prepares:
            self._log(f"  Node {primary_id} broadcasts {pp}")

        # === Phase 2: PREPARE ===
        self._log("\n  --- Phase 2: PREPARE ---")
        prepare_msgs = []

        for node in self.nodes:
            if node.id == primary_id:
                continue  # Primary doesn't send PREPARE

            if primary.is_byzantine:
                # Byzantine primary: send real msg to some, fake to others
                # First backup gets real, second gets fake, etc.
                pp = pre_prepares[node.id % len(pre_prepares)]
            else:
                pp = pre_prepares[0]

            prepare = node.handle_pre_prepare(pp)
            if prepare:
                self._log(f"  Node {node.id} accepts PRE-PREPARE, "
                          f"broadcasts {prepare}")
                prepare_msgs.append(prepare)
            else:
                self._log(f"  Node {node.id} REJECTS PRE-PREPARE "
                          f"(invalid digest)")

        # === Deliver PREPARE messages to all nodes ===
        self._log("\n  --- Delivering PREPARE messages ---")
        commit_msgs = []

        for node in self.nodes:
            for prep in prepare_msgs:
                if prep.sender == node.id:
                    continue  # Don't deliver to sender
                commit = node.handle_prepare(prep)
                if commit:
                    self._log(f"  Node {node.id} reaches PREPARED state, "
                              f"broadcasts {commit}")
                    commit_msgs.append(commit)

        # === Phase 3: COMMIT ===
        self._log("\n  --- Phase 3: COMMIT ---")
        replies = []

        for node in self.nodes:
            for cm in commit_msgs:
                if cm.sender == node.id:
                    continue
                reply = node.handle_commit(cm)
                if reply:
                    self._log(f"  Node {node.id} reaches COMMITTED state, "
                              f"executes request")
                    replies.append(reply)

        # === Check results ===
        executed_nodes = [n.id for n in self.nodes if n.executed]
        success = len(executed_nodes) >= QUORUM

        self._log(f"\n  --- Result ---")
        self._log(f"  Nodes that executed: {executed_nodes}")
        self._log(f"  Consensus {'REACHED' if success else 'FAILED'} "
                  f"({len(executed_nodes)}/{len(self.nodes)} nodes agreed)")

        return {
            "success": success,
            "executed_nodes": executed_nodes,
            "replies": replies,
            "log": self.log,
        }


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of PBFT consensus."""

    print("=" * 70)
    print("  Practical Byzantine Fault Tolerance (PBFT)")
    print("=" * 70)

    # --- Explain the setup ---
    print("\n--- PBFT Configuration ---\n")
    print(f"  Total nodes (n):        {NUM_NODES}")
    print(f"  Max faults (f):         {MAX_FAULTS}")
    print(f"  Minimum nodes: 3f+1 =   {3 * MAX_FAULTS + 1}")
    print(f"  Quorum (2f+1):          {QUORUM}")
    print()
    print("  ┌──────────────────────────────────────────────────────────┐")
    print("  │  PBFT guarantees consensus if at most f nodes are       │")
    print("  │  Byzantine (arbitrarily malicious). With n=4, f=1:      │")
    print("  │                                                         │")
    print("  │  Node 0: PRIMARY (proposes values)                      │")
    print("  │  Node 1: Backup                                         │")
    print("  │  Node 2: Backup                                         │")
    print("  │  Node 3: Backup                                         │")
    print("  │                                                         │")
    print("  │  Agreement requires 2f+1 = 3 matching messages.         │")
    print("  └──────────────────────────────────────────────────────────┘")

    # === Scenario 1: Normal consensus (no faults) ===
    print("\n" + "=" * 70)
    print("  Scenario 1: Normal Consensus (All Honest)")
    print("=" * 70)

    network = PBFTNetwork(NUM_NODES, byzantine_ids=[])
    result = network.run_consensus("Transfer 10 BTC from Alice to Bob")

    for line in result["log"]:
        print(f"  {line}")

    print()
    print("  ┌──────────────────────────────────────────────────────────┐")
    print("  │  All 4 nodes agreed on the same request.                │")
    print("  │  The 3-phase protocol ensures total order of requests.  │")
    print("  └──────────────────────────────────────────────────────────┘")

    # === Scenario 2: One Byzantine backup ===
    print("\n" + "=" * 70)
    print("  Scenario 2: Byzantine Backup (Node 3 is malicious)")
    print("=" * 70)

    print("\n  Node 3 will refuse to participate (crash fault).")
    print("  With 3 honest nodes, quorum of 3 is still achievable.\n")

    # Simulate by just ignoring node 3's messages
    network2 = PBFTNetwork(NUM_NODES, byzantine_ids=[])
    # Manually mark node 3 as non-participating
    network2.nodes[3].is_byzantine = True

    # Run manually to show the crash fault scenario
    request = "Deploy smart contract v2"
    print(f"  Client sends request: '{request}'")
    print(f"  Primary is Node 0 (honest)")
    print(f"  Node 3 is BYZANTINE (will not respond)")

    primary = network2.nodes[0]
    pre_prepares = primary.receive_request(request)
    pp = pre_prepares[0]
    print(f"\n  --- Phase 1: PRE-PREPARE ---")
    print(f"  Node 0 broadcasts {pp}")

    print(f"\n  --- Phase 2: PREPARE ---")
    prepare_msgs = []
    for node in network2.nodes:
        if node.id == 0:
            continue
        if node.is_byzantine:
            print(f"  Node {node.id} is Byzantine — does NOT send PREPARE")
            continue
        prepare = node.handle_pre_prepare(pp)
        if prepare:
            print(f"  Node {node.id} broadcasts {prepare}")
            prepare_msgs.append(prepare)

    print(f"\n  --- Delivering PREPARE messages ---")
    commit_msgs = []
    # The primary also implicitly agrees — add its own PREPARE to its log
    # so it can reach quorum along with backups' PREPAREs.
    primary_prep = Message(PREPARE, 0, pp.seq, pp.digest, 0)
    primary.message_log.append(primary_prep)
    # Include it in the broadcast so other nodes see it
    all_prepares = [primary_prep] + prepare_msgs

    for node in network2.nodes:
        if node.is_byzantine:
            continue
        for prep in all_prepares:
            if prep.sender == node.id:
                continue  # Already in their own log
            commit = node.handle_prepare(prep)
            if commit:
                print(f"  Node {node.id} reaches PREPARED (2f+1 prepares), "
                      f"broadcasts {commit}")
                commit_msgs.append(commit)

    print(f"\n  --- Phase 3: COMMIT ---")
    executed = []
    for node in network2.nodes:
        if node.is_byzantine:
            continue
        for cm in commit_msgs:
            if cm.sender == node.id:
                continue
            reply = node.handle_commit(cm)
            if reply:
                print(f"  Node {node.id} reaches COMMITTED, executes request")
                executed.append(node.id)

    print(f"\n  --- Result ---")
    print(f"  Nodes that executed: {executed}")
    print(f"  Consensus REACHED despite Node 3 being Byzantine")

    print()
    print("  ┌──────────────────────────────────────────────────────────┐")
    print("  │  Even with 1 Byzantine node, the remaining 3 honest     │")
    print("  │  nodes form a quorum (2f+1 = 3) and reach agreement.    │")
    print("  └──────────────────────────────────────────────────────────┘")

    # === Scenario 3: Byzantine Primary (equivocation) ===
    print("\n" + "=" * 70)
    print("  Scenario 3: Byzantine Primary (Sends Conflicting Messages)")
    print("=" * 70)

    print("\n  Node 0 (primary) sends DIFFERENT requests to different nodes.")
    print("  This is called equivocation — the worst Byzantine behavior.\n")

    network3 = PBFTNetwork(NUM_NODES, byzantine_ids=[0])
    result3 = network3.run_consensus("Transfer 100 ETH to Charlie")

    for line in result3["log"]:
        print(f"  {line}")

    print()
    print("  ┌──────────────────────────────────────────────────────────┐")
    print("  │  Byzantine primary sent conflicting PRE-PREPAREs.       │")
    print("  │  Honest nodes detect the inconsistency in PREPARE       │")
    print("  │  phase — they never get 2f+1 matching digests.          │")
    print("  │                                                         │")
    print("  │  In real PBFT, this triggers a VIEW CHANGE:             │")
    print("  │  nodes elect a new primary and retry the request.       │")
    print("  └──────────────────────────────────────────────────────────┘")

    # === Summary: PBFT message flow ===
    print("\n" + "=" * 70)
    print("  PBFT Message Flow Summary")
    print("=" * 70)

    print()
    print("  Client ──request──> Primary")
    print("  ")
    print("  Phase 1: PRE-PREPARE")
    print("  ┌────────┐  PRE-PREPARE  ┌────────┐ ┌────────┐ ┌────────┐")
    print("  │Primary │──────────────>│Backup 1│ │Backup 2│ │Backup 3│")
    print("  │(Node 0)│               │(Node 1)│ │(Node 2)│ │(Node 3)│")
    print("  └────────┘               └────────┘ └────────┘ └────────┘")
    print()
    print("  Phase 2: PREPARE (all-to-all)")
    print("  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐")
    print("  │Node 0  │<>│Node 1  │<>│Node 2  │<>│Node 3  │")
    print("  └────────┘  └────────┘  └────────┘  └────────┘")
    print("  Each node waits for 2f+1 = 3 matching PREPARE messages")
    print()
    print("  Phase 3: COMMIT (all-to-all)")
    print("  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐")
    print("  │Node 0  │<>│Node 1  │<>│Node 2  │<>│Node 3  │")
    print("  └────────┘  └────────┘  └────────┘  └────────┘")
    print("  Each node waits for 2f+1 = 3 matching COMMIT messages")
    print("  Then executes the request and sends REPLY to client")

    print()
    print("  Total messages per request: O(n^2)")
    print(f"  With n={NUM_NODES}: ~{NUM_NODES * NUM_NODES} messages")
    print("  This quadratic cost is why PBFT is used in permissioned chains")
    print("  (tens of nodes), not public chains (thousands of nodes).")

    print()
    print("=" * 70)
    print("  PBFT Consensus complete.")
    print("=" * 70)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
