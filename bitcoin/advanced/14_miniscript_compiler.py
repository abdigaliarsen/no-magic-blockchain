"""
TITLE: Miniscript Compiler
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    A simplified Miniscript policy language compiler that translates human-readable
    spending policies into Bitcoin Script opcodes. Includes witness cost analysis
    to compare the weight of different spending paths.

KEY CONCEPTS:
    - Policy language: and(), or(), thresh(), pk(), after(), hash() combinators
    - AST (Abstract Syntax Tree): policies parsed into a tree structure
    - Script compilation: AST nodes emit corresponding Bitcoin Script opcodes
    - Witness cost: weight units per spending path (signatures, preimages, etc.)

PREREQUISITE SCRIPTS:
    - bitcoin/fundamentals/02_bitcoin_script.py (Script opcodes)
    - bitcoin/intermediate/10_taproot_mast.py (script trees)
    - bitcoin/intermediate/12_timelocks_htlcs.py (timelocks)

REAL-WORLD RELEVANCE:
    Miniscript (developed by Pieter Wuille, Andrew Poelstra, and Sanket Kanjalkar)
    is used in production Bitcoin wallets (e.g., Liana) to safely compose complex
    spending conditions. It enables automated analysis of spending costs, security
    properties, and compatibility with hardware signing devices.
"""

import hashlib  # For SHA-256 and HASH160 simulation

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Witness weight costs (in weight units, 1 vbyte = 4 weight units)
WEIGHT_SIGNATURE = 73       # DER-encoded ECDSA signature (~72-73 bytes)
WEIGHT_SCHNORR_SIG = 65     # Schnorr signature (64 bytes + sighash flag)
WEIGHT_PUBKEY = 34           # Compressed public key (33 bytes + push opcode)
WEIGHT_HASH_PREIMAGE = 33   # SHA-256 preimage (32 bytes + push opcode)
WEIGHT_EMPTY = 1             # Empty witness element (OP_0)
WEIGHT_PUSH_INT = 2          # Small integer push

# Script opcode mnemonics
OP_DUP = "OP_DUP"
OP_HASH160 = "OP_HASH160"
OP_EQUALVERIFY = "OP_EQUALVERIFY"
OP_CHECKSIG = "OP_CHECKSIG"
OP_CHECKMULTISIG = "OP_CHECKMULTISIG"
OP_IF = "OP_IF"
OP_ELSE = "OP_ELSE"
OP_ENDIF = "OP_ENDIF"
OP_CHECKLOCKTIMEVERIFY = "OP_CHECKLOCKTIMEVERIFY"
OP_CHECKSEQUENCEVERIFY = "OP_CHECKSEQUENCEVERIFY"
OP_DROP = "OP_DROP"
OP_SHA256 = "OP_SHA256"
OP_EQUAL = "OP_EQUAL"
OP_VERIFY = "OP_VERIFY"
OP_SWAP = "OP_SWAP"
OP_ADD = "OP_ADD"
OP_GREATERTHANOREQUAL = "OP_GREATERTHANOREQUAL"
OP_TRUE = "OP_1"
OP_FALSE = "OP_0"
OP_BOOLOR = "OP_BOOLOR"
OP_BOOLAND = "OP_BOOLAND"
OP_IFDUP = "OP_IFDUP"
OP_NOTIF = "OP_NOTIF"
OP_SIZE = "OP_SIZE"
OP_TOALTSTACK = "OP_TOALTSTACK"
OP_FROMALTSTACK = "OP_FROMALTSTACK"
OP_CHECKMULTISIGVERIFY = "OP_CHECKMULTISIGVERIFY"
OP_CHECKSIGVERIFY = "OP_CHECKSIGVERIFY"

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Policy AST Nodes ---

class PolicyNode:
    """Base class for all policy AST nodes."""

    def compile(self) -> list:
        """Compile this policy node to a list of Script opcodes."""
        raise NotImplementedError

    def witness_cost(self, satisfaction: dict = None) -> int:
        """Estimate witness weight in weight units for satisfying this policy."""
        raise NotImplementedError

    def describe(self, indent: int = 0) -> str:
        """Return a human-readable description of this policy."""
        raise NotImplementedError


class PkPolicy(PolicyNode):
    """
    pk(KEY) — require a signature from KEY.
    Compiles to: <KEY> OP_CHECKSIG
    """
    def __init__(self, key_name: str):
        self.key_name = key_name

    def compile(self) -> list:
        return [f"<{self.key_name}>", OP_CHECKSIG]

    def witness_cost(self, satisfaction: dict = None) -> int:
        # Witness: one signature
        return WEIGHT_SIGNATURE

    def describe(self, indent: int = 0) -> str:
        return " " * indent + f"pk({self.key_name})"

    def __repr__(self):
        return f"pk({self.key_name})"


class AfterPolicy(PolicyNode):
    """
    after(N) — require absolute timelock of N blocks.
    Compiles to: <N> OP_CHECKLOCKTIMEVERIFY OP_DROP
    Always true once the timelock expires (returns 1).
    """
    def __init__(self, block_height: int):
        self.block_height = block_height

    def compile(self) -> list:
        return [self.block_height, OP_CHECKLOCKTIMEVERIFY, OP_DROP, OP_TRUE]

    def witness_cost(self, satisfaction: dict = None) -> int:
        # Timelocks add no witness data — they're checked against tx fields
        return 0

    def describe(self, indent: int = 0) -> str:
        return " " * indent + f"after({self.block_height})"

    def __repr__(self):
        return f"after({self.block_height})"


class OlderPolicy(PolicyNode):
    """
    older(N) — require relative timelock of N blocks since UTXO confirmation.
    Compiles to: <N> OP_CHECKSEQUENCEVERIFY OP_DROP
    """
    def __init__(self, blocks: int):
        self.blocks = blocks

    def compile(self) -> list:
        return [self.blocks, OP_CHECKSEQUENCEVERIFY, OP_DROP, OP_TRUE]

    def witness_cost(self, satisfaction: dict = None) -> int:
        return 0

    def describe(self, indent: int = 0) -> str:
        return " " * indent + f"older({self.blocks})"

    def __repr__(self):
        return f"older({self.blocks})"


class HashPolicy(PolicyNode):
    """
    sha256(H) — require a SHA-256 preimage that hashes to H.
    Compiles to: OP_SHA256 <H> OP_EQUAL
    """
    def __init__(self, hash_hex: str):
        self.hash_hex = hash_hex

    def compile(self) -> list:
        return [OP_SIZE, 32, OP_EQUALVERIFY, OP_SHA256, f"<{self.hash_hex[:16]}...>", OP_EQUAL]

    def witness_cost(self, satisfaction: dict = None) -> int:
        return WEIGHT_HASH_PREIMAGE

    def describe(self, indent: int = 0) -> str:
        return " " * indent + f"sha256({self.hash_hex[:16]}...)"

    def __repr__(self):
        return f"sha256({self.hash_hex[:16]}...)"


class AndPolicy(PolicyNode):
    """
    and(A, B) — both conditions must be satisfied.
    Compiles by combining both sub-scripts with OP_BOOLAND.
    """
    def __init__(self, left: PolicyNode, right: PolicyNode):
        self.left = left
        self.right = right

    def compile(self) -> list:
        # Compile both sub-policies, combine with BOOLAND
        left_script = self.left.compile()
        right_script = self.right.compile()
        # Use VERIFY on the first, so stack has just the second result
        # Pattern: <left_script> OP_VERIFY <right_script>
        return left_script + [OP_VERIFY] + right_script

    def witness_cost(self, satisfaction: dict = None) -> int:
        # Both branches must be satisfied
        return self.left.witness_cost(satisfaction) + self.right.witness_cost(satisfaction)

    def describe(self, indent: int = 0) -> str:
        prefix = " " * indent
        return (f"{prefix}and(\n"
                f"{self.left.describe(indent + 2)},\n"
                f"{self.right.describe(indent + 2)}\n"
                f"{prefix})")

    def __repr__(self):
        return f"and({self.left}, {self.right})"


class OrPolicy(PolicyNode):
    """
    or(A, B) — either condition can be satisfied.
    Compiles to an IF/ELSE branch, spender chooses which path.

    The spender provides a selector (1 for left branch, 0 for right) in
    the witness to choose which branch to execute.
    """
    def __init__(self, left: PolicyNode, right: PolicyNode,
                 left_prob: float = 0.5, right_prob: float = 0.5):
        self.left = left
        self.right = right
        self.left_prob = left_prob    # Probability of using left path
        self.right_prob = right_prob  # Probability of using right path

    def compile(self) -> list:
        left_script = self.left.compile()
        right_script = self.right.compile()
        # IF <left> ELSE <right> ENDIF
        return [OP_IF] + left_script + [OP_ELSE] + right_script + [OP_ENDIF]

    def witness_cost(self, satisfaction: dict = None) -> int:
        # Return the cost of the cheaper path (optimal spending)
        left_cost = self.left.witness_cost(satisfaction) + WEIGHT_PUSH_INT  # +1 for selector
        right_cost = self.right.witness_cost(satisfaction) + WEIGHT_PUSH_INT
        return min(left_cost, right_cost)

    def spending_paths(self) -> list:
        """Return all spending paths with their costs."""
        return [
            ("left", self.left, self.left.witness_cost() + WEIGHT_PUSH_INT, self.left_prob),
            ("right", self.right, self.right.witness_cost() + WEIGHT_PUSH_INT, self.right_prob),
        ]

    def describe(self, indent: int = 0) -> str:
        prefix = " " * indent
        return (f"{prefix}or(\n"
                f"{self.left.describe(indent + 2)},\n"
                f"{self.right.describe(indent + 2)}\n"
                f"{prefix})")

    def __repr__(self):
        return f"or({self.left}, {self.right})"


class ThreshPolicy(PolicyNode):
    """
    thresh(K, sub1, sub2, ..., subN) — at least K of N sub-policies must be satisfied.

    For K=N: equivalent to and(sub1, and(sub2, ... subN))
    For K=1: equivalent to or(sub1, or(sub2, ... subN))
    For pure pk() sub-policies: compiles to OP_CHECKMULTISIG
    """
    def __init__(self, threshold: int, sub_policies: list):
        self.threshold = threshold
        self.sub_policies = sub_policies
        self.n = len(sub_policies)

    def _is_pure_multisig(self) -> bool:
        """Check if all sub-policies are simple pk() — can use CHECKMULTISIG."""
        return all(isinstance(p, PkPolicy) for p in self.sub_policies)

    def compile(self) -> list:
        if self._is_pure_multisig():
            # Use native CHECKMULTISIG for pure key thresholds
            script = [self.threshold]  # OP_K
            for policy in self.sub_policies:
                script.append(f"<{policy.key_name}>")  # Push each pubkey
            script.append(self.n)  # OP_N
            script.append(OP_CHECKMULTISIG)
            return script
        else:
            # General threshold: compile each sub-policy, count successes
            # Pattern: <sub1> <sub2> OP_ADD <sub3> OP_ADD ... <K> OP_GREATERTHANOREQUAL
            script = self.sub_policies[0].compile()
            for sub in self.sub_policies[1:]:
                script += [OP_TOALTSTACK]  # Stash running total
                script += sub.compile()
                script += [OP_FROMALTSTACK, OP_ADD]  # Retrieve and add
            script += [self.threshold, OP_GREATERTHANOREQUAL]
            return script

    def witness_cost(self, satisfaction: dict = None) -> int:
        if self._is_pure_multisig():
            # CHECKMULTISIG witness: OP_0 + K signatures
            return WEIGHT_EMPTY + self.threshold * WEIGHT_SIGNATURE
        else:
            # Sort sub-policies by cost, take cheapest K
            costs = sorted(p.witness_cost(satisfaction) for p in self.sub_policies)
            return sum(costs[:self.threshold])

    def describe(self, indent: int = 0) -> str:
        prefix = " " * indent
        subs = ",\n".join(p.describe(indent + 2) for p in self.sub_policies)
        return f"{prefix}thresh({self.threshold},\n{subs}\n{prefix})"

    def __repr__(self):
        subs = ", ".join(str(p) for p in self.sub_policies)
        return f"thresh({self.threshold}, {subs})"


# --- Script Compiler ---

class MiniscriptCompiler:
    """
    Compiles policy AST into Bitcoin Script and analyzes spending paths.
    """
    def __init__(self, policy: PolicyNode):
        self.policy = policy
        self.compiled_script = None

    def compile(self) -> list:
        """Compile the policy AST into a list of Script opcodes."""
        self.compiled_script = self.policy.compile()
        return self.compiled_script

    def script_size(self) -> int:
        """Estimate the script size in bytes."""
        size = 0
        for op in self.compiled_script:
            if isinstance(op, str) and op.startswith("OP_"):
                size += 1  # Each opcode is 1 byte
            elif isinstance(op, str) and op.startswith("<"):
                # Push data — estimate based on content
                if "key" in op.lower() or "pk" in op.lower():
                    size += 34  # 33-byte compressed pubkey + 1-byte push
                else:
                    size += 33  # Generic 32-byte push
            elif isinstance(op, int):
                if 0 <= op <= 16:
                    size += 1   # OP_0 through OP_16
                elif op < 256:
                    size += 2   # 1-byte push
                elif op < 65536:
                    size += 3   # 2-byte push
                else:
                    size += 5   # 4-byte push
        return size

    def format_script(self) -> str:
        """Format the compiled script for display."""
        return " ".join(str(op) for op in self.compiled_script)

    def analyze_paths(self) -> list:
        """
        Analyze all spending paths and their costs.
        Returns list of (description, witness_weight, script) tuples.
        """
        paths = []
        self._collect_paths(self.policy, [], paths)
        return paths

    def _collect_paths(self, node: PolicyNode, path: list, results: list):
        """Recursively collect all possible spending paths."""
        if isinstance(node, OrPolicy):
            # Two paths: left and right
            self._collect_paths(node.left, path + [f"or:left"], results)
            self._collect_paths(node.right, path + [f"or:right"], results)
        elif isinstance(node, AndPolicy):
            # Both must be satisfied — combine descriptions
            self._collect_paths_and(node, path, results)
        elif isinstance(node, ThreshPolicy):
            # For simplicity, show the cheapest K-of-N combination
            desc = " -> ".join(path + [str(node)])
            cost = node.witness_cost()
            results.append((desc, cost, node.compile()))
        else:
            # Leaf node
            desc = " -> ".join(path + [str(node)])
            cost = node.witness_cost()
            results.append((desc, cost, node.compile()))

    def _collect_paths_and(self, node: AndPolicy, path: list, results: list):
        """Handle AND nodes: both children contribute to the same path."""
        if isinstance(node.left, OrPolicy):
            # Left is OR — fork here
            self._collect_paths(node.left, path + [f"and:left"], results)
        elif isinstance(node.right, OrPolicy):
            # Right is OR — fork here
            self._collect_paths(node.right, path + [f"and:right"], results)
        else:
            desc = " -> ".join(path + [f"and({node.left}, {node.right})"])
            cost = node.witness_cost()
            results.append((desc, cost, node.compile()))


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Demonstrate the Miniscript policy compiler."""

    print("=" * 70)
    print("        MINISCRIPT COMPILER")
    print("=" * 70)

    # --- Part 1: Simple Policies ---
    print("\n--- Part 1: Simple Policy Compilation ---\n")

    # pk(Alice)
    p1 = PkPolicy("Alice")
    c1 = MiniscriptCompiler(p1)
    script1 = c1.compile()

    print(f"  Policy:  {p1}")
    print(f"  Script:  {c1.format_script()}")
    print(f"  Size:    {c1.script_size()} bytes")
    print(f"  Witness: {p1.witness_cost()} weight units (1 signature)")

    # after(850144) — absolute timelock
    print()
    p2 = AfterPolicy(850_144)
    c2 = MiniscriptCompiler(p2)
    script2 = c2.compile()

    print(f"  Policy:  {p2}")
    print(f"  Script:  {c2.format_script()}")
    print(f"  Size:    {c2.script_size()} bytes")
    print(f"  Witness: {p2.witness_cost()} weight units (no witness data)")

    # sha256(H)
    print()
    h = hashlib.sha256(b"secret preimage").hexdigest()
    p3 = HashPolicy(h)
    c3 = MiniscriptCompiler(p3)
    script3 = c3.compile()

    print(f"  Policy:  {p3}")
    print(f"  Script:  {c3.format_script()}")
    print(f"  Size:    {c3.script_size()} bytes")
    print(f"  Witness: {p3.witness_cost()} weight units (1 preimage)")

    # --- Part 2: 2-of-3 Multisig ---
    print(f"\n--- Part 2: Multisig (thresh) ---\n")

    p4 = ThreshPolicy(2, [
        PkPolicy("Alice"),
        PkPolicy("Bob"),
        PkPolicy("Carol"),
    ])
    c4 = MiniscriptCompiler(p4)
    script4 = c4.compile()

    print(f"  Policy:  thresh(2, pk(Alice), pk(Bob), pk(Carol))")
    print(f"  Script:  {c4.format_script()}")
    print(f"  Size:    {c4.script_size()} bytes")
    print(f"  Witness: {p4.witness_cost()} weight units")
    print(f"           (OP_0 + 2 signatures = {WEIGHT_EMPTY} + 2 * {WEIGHT_SIGNATURE})")

    # --- Part 3: Complex Policy with OR ---
    print(f"\n--- Part 3: Complex Policy — Recovery Wallet ---\n")

    # Policy: "Alice can spend anytime, OR (Bob AND Carol) after 144 blocks"
    # This is a typical recovery setup:
    # - Normal use: Alice signs with her key
    # - Recovery: if Alice loses access, Bob+Carol can recover after 1 day

    alice_key = PkPolicy("Alice")
    bob_key = PkPolicy("Bob")
    carol_key = PkPolicy("Carol")
    timelock = OlderPolicy(144)

    recovery = AndPolicy(
        ThreshPolicy(2, [bob_key, carol_key]),  # Bob AND Carol
        timelock                                  # after 144 blocks
    )

    wallet_policy = OrPolicy(alice_key, recovery)

    compiler = MiniscriptCompiler(wallet_policy)
    script = compiler.compile()

    print(f"  Policy:")
    print(wallet_policy.describe(4))
    print()

    # Show compiled script
    print(f"  Compiled Script:")
    print(f"  ┌{'─' * 60}┐")
    # Break script into lines of ~4 opcodes for readability
    ops = script
    line = "  │ "
    for i, op in enumerate(ops):
        token = str(op)
        if len(line) + len(token) > 60:
            print(f"{line:<62}│")
            line = "  │   "
        line += token + " "
    if line.strip():
        print(f"{line:<62}│")
    print(f"  └{'─' * 60}┘")

    print(f"\n  Script size: {compiler.script_size()} bytes")

    # --- Part 4: Spending Path Analysis ---
    print(f"\n--- Part 4: Spending Path Analysis ---\n")

    print(f"  ┌{'─' * 62}┐")
    print(f"  │ {'Path':<35} {'Witness Cost':>12} {'vbytes':>10} │")
    print(f"  ├{'─' * 62}┤")

    # Path 1: Alice spends (just her signature + IF selector)
    alice_cost = alice_key.witness_cost() + WEIGHT_PUSH_INT  # sig + selector
    alice_vb = (alice_cost + 3) // 4  # Convert WU to vbytes (round up)
    print(f"  │ {'Alice signs (normal path)':<35} {alice_cost:>8} WU {alice_vb:>7} vB │")

    # Path 2: Bob + Carol recovery (2 sigs + timelock + selector)
    recovery_cost = recovery.witness_cost() + WEIGHT_PUSH_INT
    recovery_vb = (recovery_cost + 3) // 4
    print(f"  │ {'Bob+Carol after 144 blocks':<35} {recovery_cost:>8} WU {recovery_vb:>7} vB │")

    savings = recovery_cost - alice_cost
    print(f"  ├{'─' * 62}┤")
    print(f"  │ {'Alice path saves':<35} {savings:>8} WU {savings // 4:>7} vB │")
    print(f"  └{'─' * 62}┘")

    print(f"\n  Key insight: the normal spending path (Alice) is ~{savings} WU")
    print(f"  cheaper than recovery. This is by design — frequent spends are")
    print(f"  optimized for cost, recovery is rare and can afford higher fees.")

    # --- Part 5: Real-World Example — Liana-style Wallet ---
    print(f"\n--- Part 5: Liana-Style Degrading Multisig ---\n")

    # Liana wallet pattern: primary key with time-degrading fallbacks
    # - Immediately: 2-of-3 (Alice, Bob, Carol)
    # - After 6 months (~26,000 blocks): any 1 of 3
    # - After 1 year (~52,000 blocks): recovery key

    primary = ThreshPolicy(2, [
        PkPolicy("Alice"),
        PkPolicy("Bob"),
        PkPolicy("Carol"),
    ])

    degraded = AndPolicy(
        OrPolicy(
            PkPolicy("Alice"),
            OrPolicy(PkPolicy("Bob"), PkPolicy("Carol"))
        ),
        OlderPolicy(26_000)  # ~6 months
    )

    recovery_final = AndPolicy(
        PkPolicy("Recovery_Key"),
        OlderPolicy(52_000)  # ~1 year
    )

    liana_policy = OrPolicy(primary, OrPolicy(degraded, recovery_final))

    liana_compiler = MiniscriptCompiler(liana_policy)
    liana_script = liana_compiler.compile()

    print(f"  Policy (degrading over time):")
    print(f"  ┌{'─' * 60}┐")
    print(f"  │ Time 0:        2-of-3 (Alice, Bob, Carol)               │")
    print(f"  │ After ~6 mo:   any 1-of-3                               │")
    print(f"  │ After ~1 yr:   Recovery_Key alone                       │")
    print(f"  └{'─' * 60}┘")

    print(f"\n  Compiled script size: {liana_compiler.script_size()} bytes")

    # Analyze costs for each tier
    print(f"\n  Spending cost by tier:")
    print(f"  ┌{'─' * 58}┐")
    print(f"  │ {'Tier':<30} {'Cost':>10} {'Wait':>14} │")
    print(f"  ├{'─' * 58}┤")

    tier1_cost = primary.witness_cost()
    tier2_cost = WEIGHT_SIGNATURE  # 1 signature
    tier3_cost = WEIGHT_SIGNATURE  # Recovery key signature

    print(f"  │ {'2-of-3 multisig':<30} {tier1_cost:>7} WU {'none':>14} │")
    print(f"  │ {'1-of-3 degraded':<30} {tier2_cost:>7} WU {'~26,000 blks':>14} │")
    print(f"  │ {'Recovery key':<30} {tier3_cost:>7} WU {'~52,000 blks':>14} │")
    print(f"  └{'─' * 58}┘")

    # --- Part 6: Compilation Comparison ---
    print(f"\n--- Part 6: Policy vs Script Comparison ---\n")

    examples = [
        ("pk(A)", PkPolicy("A")),
        ("and(pk(A), pk(B))", AndPolicy(PkPolicy("A"), PkPolicy("B"))),
        ("or(pk(A), pk(B))", OrPolicy(PkPolicy("A"), PkPolicy("B"))),
        ("thresh(2, pk(A), pk(B), pk(C))", ThreshPolicy(2, [PkPolicy("A"), PkPolicy("B"), PkPolicy("C")])),
        ("and(pk(A), older(144))", AndPolicy(PkPolicy("A"), OlderPolicy(144))),
    ]

    print(f"  ┌{'─' * 66}┐")
    print(f"  │ {'Policy':<30} {'Compiled Script':<34}│")
    print(f"  ├{'─' * 66}┤")
    for desc, policy in examples:
        comp = MiniscriptCompiler(policy)
        s = comp.compile()
        script_str = " ".join(str(op) for op in s)
        if len(script_str) > 32:
            script_str = script_str[:29] + "..."
        print(f"  │ {desc:<30} {script_str:<34}│")
    print(f"  └{'─' * 66}┘")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
