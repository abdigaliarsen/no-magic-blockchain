"""
TITLE: BitVM (Simplified)
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    A simplified BitVM protocol demonstrating how arbitrary computation can be
    verified on Bitcoin using bit commitments, NAND gate verification, and a
    bisection-based fraud proof. The prover commits to inputs/outputs of a
    circuit, and the verifier can challenge any incorrect gate.

KEY CONCEPTS:
    - Bit commitments: prover locks each bit using hash pairs (H0, H1)
    - NAND gates: universal gate — any boolean circuit can be built from NANDs
    - Circuit execution: connect committed bits through a NAND gate graph
    - Bisection fraud proof: verifier narrows down to a single wrong gate
    - On-chain verification: one gate check proves fraud

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - bitcoin/fundamentals/02_bitcoin_script.py (Script opcodes)
    - bitcoin/intermediate/12_timelocks_htlcs.py (challenge-response)

REAL-WORLD RELEVANCE:
    BitVM (proposed by Robin Linus in 2023) enables optimistic computation
    verification on Bitcoin without soft forks. It's used for trust-minimized
    Bitcoin bridges and could enable general smart contract functionality.
    The key insight: computation is done off-chain, but any incorrect result
    can be disproven on-chain by revealing a single faulty gate.
"""

import hashlib  # For SHA-256 bit commitments
import os       # For random preimage generation

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Number of bits in our simplified circuit inputs/outputs
NUM_BITS = 4                          # 4-bit numbers for demo clarity

# Challenge-response parameters
MAX_BISECTION_ROUNDS = 5             # Maximum rounds to narrow down to one gate
CHALLENGE_TIMEOUT_BLOCKS = 144       # ~24 hours to respond to a challenge

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Hashing utility ---

def sha256(data: bytes) -> bytes:
    """Compute SHA-256 hash."""
    return hashlib.sha256(data).digest()


# --- Bit Commitments ---

class BitCommitment:
    """
    A commitment to a single bit using a hash pair.

    The prover generates two random preimages (preimage0, preimage1) and
    publishes their hashes (hash0, hash1). To reveal the bit value, the
    prover reveals the corresponding preimage:
    - Reveal preimage0 → bit is 0
    - Reveal preimage1 → bit is 1

    Crucially, the prover CANNOT reveal both — doing so would let the
    verifier claim a penalty (equivocation proof).
    """
    def __init__(self, label: str):
        self.label = label
        # Two random preimages — one for each possible bit value
        self.preimage0 = os.urandom(32)  # Preimage for bit=0
        self.preimage1 = os.urandom(32)  # Preimage for bit=1
        # Published commitments (hashes) — these go on-chain
        self.hash0 = sha256(self.preimage0)
        self.hash1 = sha256(self.preimage1)
        # The actual bit value (set when the commitment is opened)
        self.value = None
        self.revealed_preimage = None

    def commit_to(self, bit: int):
        """Set the bit value this commitment represents."""
        assert bit in (0, 1), "Bit must be 0 or 1"
        self.value = bit
        # The preimage that will be revealed to open this commitment
        self.revealed_preimage = self.preimage1 if bit == 1 else self.preimage0

    def verify_opening(self, preimage: bytes) -> tuple:
        """
        Verify a commitment opening.
        Returns (is_valid, bit_value).
        """
        h = sha256(preimage)
        if h == self.hash0:
            return True, 0
        elif h == self.hash1:
            return True, 1
        else:
            return False, None  # Preimage doesn't match either hash

    def script_asm(self) -> str:
        """
        The on-chain script that verifies this bit commitment.
        Spender provides a preimage; script checks it matches hash0 or hash1.
        """
        return (f"OP_DUP OP_SHA256 <{self.hash0.hex()[:12]}...> OP_EQUAL\n"
                f"  OP_IF OP_DROP 0  # bit = 0\n"
                f"  OP_ELSE OP_SHA256 <{self.hash1.hex()[:12]}...> OP_EQUALVERIFY 1  # bit = 1\n"
                f"  OP_ENDIF")


# --- NAND Gate ---

class NANDGate:
    """
    A NAND gate operating on committed bits.

    NAND truth table:
      A  B  | NAND(A,B)
      0  0  |    1
      0  1  |    1
      1  0  |    1
      1  1  |    0

    NAND is a universal gate — any boolean function can be built from NANDs:
    - NOT(A) = NAND(A, A)
    - AND(A, B) = NAND(NAND(A, B), NAND(A, B))
    - OR(A, B) = NAND(NAND(A, A), NAND(B, B))
    - XOR(A, B) = NAND(NAND(NAND(A,A), NAND(B,B)), NAND(A,B))
    """
    def __init__(self, gate_id: int, input_a: BitCommitment,
                 input_b: BitCommitment, output: BitCommitment):
        self.gate_id = gate_id
        self.input_a = input_a
        self.input_b = input_b
        self.output = output

    def expected_output(self) -> int:
        """Compute the correct NAND output from committed input values."""
        a = self.input_a.value
        b = self.input_b.value
        return 1 - (a & b)  # NAND = NOT AND

    def is_consistent(self) -> bool:
        """Check if the committed output matches the expected NAND result."""
        if self.output.value is None:
            return False  # Output not yet committed
        return self.output.value == self.expected_output()

    def verify_on_chain(self) -> tuple:
        """
        Simulate on-chain verification of this gate.

        The verifier reveals all three preimages (input_a, input_b, output).
        The script checks:
        1. Each preimage matches its commitment hash
        2. output == NAND(input_a, input_b)

        If step 2 fails, the prover is caught cheating.
        """
        # Verify input A commitment
        ok_a, val_a = self.input_a.verify_opening(self.input_a.revealed_preimage)
        if not ok_a:
            return False, "Input A commitment invalid"

        # Verify input B commitment
        ok_b, val_b = self.input_b.verify_opening(self.input_b.revealed_preimage)
        if not ok_b:
            return False, "Input B commitment invalid"

        # Verify output commitment
        ok_out, val_out = self.output.verify_opening(self.output.revealed_preimage)
        if not ok_out:
            return False, "Output commitment invalid"

        # Check NAND consistency
        expected = 1 - (val_a & val_b)
        if val_out != expected:
            return False, (f"FRAUD: NAND({val_a},{val_b}) should be {expected}, "
                          f"but prover claimed {val_out}")

        return True, f"Gate {self.gate_id} verified: NAND({val_a},{val_b}) = {val_out}"


# --- Boolean Circuit ---

class Circuit:
    """
    A boolean circuit built from NAND gates with committed bit wires.

    Each wire in the circuit has a BitCommitment. Gates connect input wires
    to output wires via NAND operations.
    """
    def __init__(self, name: str):
        self.name = name
        self.wires = {}           # wire_name -> BitCommitment
        self.gates = []           # List of NANDGate objects
        self.input_wires = []     # Names of input wires
        self.output_wires = []    # Names of output wires

    def add_wire(self, name: str) -> BitCommitment:
        """Create a new committed wire."""
        commitment = BitCommitment(name)
        self.wires[name] = commitment
        return commitment

    def add_input(self, name: str) -> BitCommitment:
        """Add an input wire to the circuit."""
        wire = self.add_wire(name)
        self.input_wires.append(name)
        return wire

    def add_output(self, name: str) -> BitCommitment:
        """Add an output wire to the circuit."""
        wire = self.add_wire(name)
        self.output_wires.append(name)
        return wire

    def add_nand(self, gate_id: int, wire_a: str, wire_b: str, wire_out: str):
        """Add a NAND gate connecting two input wires to an output wire."""
        gate = NANDGate(
            gate_id,
            self.wires[wire_a],
            self.wires[wire_b],
            self.wires[wire_out]
        )
        self.gates.append(gate)
        return gate

    def set_inputs(self, values: dict):
        """Set input wire values and propagate through the circuit."""
        for name, value in values.items():
            self.wires[name].commit_to(value)

    def propagate(self):
        """Propagate values through all gates in order."""
        for gate in self.gates:
            output_val = gate.expected_output()
            gate.output.commit_to(output_val)

    def find_inconsistent_gate(self) -> int:
        """Find the first gate with an inconsistent output (for fraud proof)."""
        for gate in self.gates:
            if not gate.is_consistent():
                return gate.gate_id
        return -1  # All gates consistent


def build_addition_circuit() -> Circuit:
    """
    Build a 2-bit addition circuit using NAND gates.

    Adds two 2-bit numbers: A (a1,a0) + B (b1,b0) = S (s2,s1,s0)

    Uses the half-adder identity:
      sum = XOR(a, b) = NAND(NAND(NAND(a,a), NAND(b,b)), NAND(a,b))
      carry = AND(a, b) = NAND(NAND(a,b), NAND(a,b))
    """
    circuit = Circuit("2-bit Adder")

    # Input wires: two 2-bit numbers
    circuit.add_input("a0")  # LSB of A
    circuit.add_input("a1")  # MSB of A
    circuit.add_input("b0")  # LSB of B
    circuit.add_input("b1")  # MSB of B

    # Output wires: 3-bit sum
    circuit.add_output("s0")  # LSB of sum
    circuit.add_output("s1")  # Middle bit of sum
    circuit.add_output("s2")  # MSB of sum (carry out)

    # Intermediate wires for half-adder 0 (a0 + b0)
    # XOR from NAND: t1=NAND(a,b), t2=NAND(a,t1), t3=NAND(b,t1), XOR=NAND(t2,t3)
    circuit.add_wire("nand_00")   # NAND(a0, b0)
    circuit.add_wire("na0_t2")    # NAND(a0, nand_00)
    circuit.add_wire("nb0_t3")    # NAND(b0, nand_00)
    circuit.add_wire("carry0")    # Carry from bit 0

    # Half-adder 0: sum0 = XOR(a0, b0), carry0 = AND(a0, b0)
    gate_id = 0
    circuit.add_nand(gate_id, "a0", "b0", "nand_00");     gate_id += 1  # t1 = NAND(a0,b0)
    circuit.add_nand(gate_id, "a0", "nand_00", "na0_t2"); gate_id += 1  # t2 = NAND(a0,t1)
    circuit.add_nand(gate_id, "b0", "nand_00", "nb0_t3"); gate_id += 1  # t3 = NAND(b0,t1)
    circuit.add_nand(gate_id, "na0_t2", "nb0_t3", "s0");  gate_id += 1  # XOR = NAND(t2,t3)
    # carry0 = AND(a0, b0) = NOT(NAND(a0,b0)) = NAND(nand_00, nand_00)
    circuit.add_nand(gate_id, "nand_00", "nand_00", "carry0"); gate_id += 1

    # Intermediate wires for half-adder 1 (a1 XOR b1)
    circuit.add_wire("nand_11")
    circuit.add_wire("na1_t2")
    circuit.add_wire("nb1_t3")
    circuit.add_wire("xor_11")    # a1 XOR b1

    # Half-adder 1a: xor_11 = XOR(a1, b1)
    circuit.add_nand(gate_id, "a1", "b1", "nand_11");      gate_id += 1
    circuit.add_nand(gate_id, "a1", "nand_11", "na1_t2");   gate_id += 1
    circuit.add_nand(gate_id, "b1", "nand_11", "nb1_t3");   gate_id += 1
    circuit.add_nand(gate_id, "na1_t2", "nb1_t3", "xor_11"); gate_id += 1

    # Half-adder 1b: s1 = XOR(xor_11, carry0), carry_out for s2
    circuit.add_wire("nand_xc")    # NAND(xor_11, carry0)
    circuit.add_wire("nxc_t2")     # NAND(xor_11, nand_xc)
    circuit.add_wire("nxc_t3")     # NAND(carry0, nand_xc)
    circuit.add_wire("carry1a")    # AND(xor_11, carry0) via NAND
    circuit.add_wire("carry1b")    # AND(a1, b1) via NAND
    circuit.add_wire("not_c1a")    # NOT carry1a
    circuit.add_wire("not_c1b")    # NOT carry1b

    circuit.add_nand(gate_id, "xor_11", "carry0", "nand_xc"); gate_id += 1
    circuit.add_nand(gate_id, "xor_11", "nand_xc", "nxc_t2"); gate_id += 1
    circuit.add_nand(gate_id, "carry0", "nand_xc", "nxc_t3"); gate_id += 1
    circuit.add_nand(gate_id, "nxc_t2", "nxc_t3", "s1"); gate_id += 1

    # carry_out = OR(AND(xor_11, carry0), AND(a1, b1))
    # AND(x,c) = NOT(NAND(x,c))
    circuit.add_nand(gate_id, "nand_xc", "nand_xc", "carry1a"); gate_id += 1  # AND(xor_11, carry0)
    circuit.add_nand(gate_id, "nand_11", "nand_11", "carry1b"); gate_id += 1  # AND(a1, b1)
    # OR(carry1a, carry1b) = NAND(NOT(carry1a), NOT(carry1b))
    circuit.add_nand(gate_id, "carry1a", "carry1a", "not_c1a"); gate_id += 1
    circuit.add_nand(gate_id, "carry1b", "carry1b", "not_c1b"); gate_id += 1
    circuit.add_nand(gate_id, "not_c1a", "not_c1b", "s2"); gate_id += 1

    return circuit


# --- Bisection Protocol ---

class BisectionChallenge:
    """
    The bisection protocol for narrowing down a fraud to a single gate.

    If the prover claims f(x) = y but the correct answer is y', the verifier
    re-executes the circuit honestly. Then:
    1. Compare prover's trace vs honest trace at the midpoint gate's output
    2. If they differ: the error is at or before the midpoint → search left
    3. If they agree: the error is after the midpoint → search right
    4. Repeat until a single gate is identified
    5. Verify that one gate on-chain — fraud proven!
    """
    def __init__(self, prover_circuit: Circuit, honest_circuit: Circuit):
        self.prover_circuit = prover_circuit
        self.honest_circuit = honest_circuit
        self.rounds = []           # Log of bisection rounds
        self.disputed_range = (0, len(prover_circuit.gates) - 1)

    def bisect(self) -> int:
        """
        Run the bisection protocol to find the faulty gate.
        Returns the gate_id of the first gate where prover's output differs
        from the honest computation.
        """
        lo, hi = self.disputed_range

        while lo < hi:
            mid = (lo + hi) // 2

            # Compare the output wire of gate[mid] between prover and honest traces
            prover_gate = self.prover_circuit.gates[mid]
            honest_gate = self.honest_circuit.gates[mid]

            # Do the prover's values match the honest values at this gate's output?
            outputs_match = (prover_gate.output.value == honest_gate.output.value)

            self.rounds.append({
                "range": (lo, hi),
                "midpoint": mid,
                "outputs_match": outputs_match,
                "prover_val": prover_gate.output.value,
                "honest_val": honest_gate.output.value,
                "wire": prover_gate.output.label,
                "narrowed_to": "left" if not outputs_match else "right"
            })

            if not outputs_match:
                hi = mid      # Divergence at or before midpoint
            else:
                lo = mid + 1  # Divergence is after midpoint

        # lo == hi: we've found the faulty gate
        return lo


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Demonstrate BitVM concepts: bit commitments, circuits, and fraud proofs."""

    print("=" * 70)
    print("        SIMPLIFIED BitVM")
    print("=" * 70)

    # --- Part 1: Bit Commitments ---
    print("\n--- Part 1: Bit Commitments ---\n")

    print("  A bit commitment locks a single bit using two hashes:")
    print("  - hash0 = SHA256(preimage0) → commits to bit=0")
    print("  - hash1 = SHA256(preimage1) → commits to bit=1")
    print("  Revealing the preimage opens the commitment.\n")

    bit = BitCommitment("example_bit")
    bit.commit_to(1)  # Commit to bit value 1

    print(f"  Commitment for '{bit.label}':")
    print(f"  ┌────────────────────────────────────────────────────────┐")
    print(f"  │ hash0: {bit.hash0.hex()[:40]}...  │")
    print(f"  │ hash1: {bit.hash1.hex()[:40]}...  │")
    print(f"  │ committed value: {bit.value}                                   │")
    print(f"  └────────────────────────────────────────────────────────┘")

    # Verify opening
    ok, val = bit.verify_opening(bit.revealed_preimage)
    print(f"\n  Opening verification:")
    print(f"  Preimage: {bit.revealed_preimage.hex()[:32]}...")
    print(f"  SHA256 =  {sha256(bit.revealed_preimage).hex()[:32]}...")
    print(f"  Matches hash{val}: {ok}")
    print(f"  Revealed bit: {val}")

    # Show script
    print(f"\n  On-chain verification script:")
    for line in bit.script_asm().split("\n"):
        print(f"    {line}")

    # --- Part 2: NAND Gates ---
    print(f"\n--- Part 2: NAND Gates (Universal Gate) ---\n")

    print(f"  NAND truth table:")
    print(f"  ┌─────┬─────┬──────────┐")
    print(f"  │  A  │  B  │ NAND(A,B)│")
    print(f"  ├─────┼─────┼──────────┤")
    for a in (0, 1):
        for b in (0, 1):
            result = 1 - (a & b)
            print(f"  │  {a}  │  {b}  │    {result}     │")
    print(f"  └─────┴─────┴──────────┘")

    print(f"\n  Building other gates from NAND:")
    print(f"  NOT(A)    = NAND(A, A)")
    print(f"  AND(A, B) = NAND(NAND(A,B), NAND(A,B))")
    print(f"  OR(A, B)  = NAND(NAND(A,A), NAND(B,B))")
    print(f"  XOR(A, B) = NAND(NAND(NAND(A,A),NAND(B,B)), NAND(A,B))")

    # Verify a single NAND gate
    print(f"\n  Single gate verification:")
    in_a = BitCommitment("gate_in_a")
    in_b = BitCommitment("gate_in_b")
    out = BitCommitment("gate_out")
    in_a.commit_to(1)
    in_b.commit_to(1)
    out.commit_to(0)  # NAND(1,1) = 0

    gate = NANDGate(0, in_a, in_b, out)
    ok, msg = gate.verify_on_chain()
    print(f"  NAND(1, 1) = 0 → {msg}")

    # --- Part 3: Circuit — Correct Execution ---
    print(f"\n--- Part 3: 2-Bit Addition Circuit (Correct) ---\n")

    circuit = build_addition_circuit()

    # Compute 2 + 3 = 5 (binary: 10 + 11 = 101)
    a_val = 2   # binary: 10
    b_val = 3   # binary: 11
    expected_sum = a_val + b_val

    circuit.set_inputs({
        "a0": (a_val >> 0) & 1,  # LSB of A
        "a1": (a_val >> 1) & 1,  # MSB of A
        "b0": (b_val >> 0) & 1,  # LSB of B
        "b1": (b_val >> 1) & 1,  # MSB of B
    })
    circuit.propagate()  # Compute all gate outputs

    # Read result
    s0 = circuit.wires["s0"].value
    s1 = circuit.wires["s1"].value
    s2 = circuit.wires["s2"].value
    result = s0 | (s1 << 1) | (s2 << 2)

    print(f"  Computing: {a_val} + {b_val} = ?")
    print(f"  Binary:    {a_val:02b} + {b_val:02b}")
    print()
    print(f"  Circuit: {len(circuit.gates)} NAND gates, "
          f"{len(circuit.wires)} wires")
    print()
    print(f"  ┌─────────────────────────────────────────────────┐")
    print(f"  │ Input A:  a1={circuit.wires['a1'].value}  "
          f"a0={circuit.wires['a0'].value}  "
          f"(decimal {a_val}){' ' * 19}│")
    print(f"  │ Input B:  b1={circuit.wires['b1'].value}  "
          f"b0={circuit.wires['b0'].value}  "
          f"(decimal {b_val}){' ' * 19}│")
    print(f"  │ Output S: s2={s2}  s1={s1}  s0={s0}  "
          f"(decimal {result}){' ' * 14}│")
    print(f"  └─────────────────────────────────────────────────┘")
    print(f"\n  Result: {a_val} + {b_val} = {result} "
          f"{'(correct)' if result == expected_sum else '(WRONG!)'}")

    # Verify all gates are consistent
    inconsistent = circuit.find_inconsistent_gate()
    print(f"  All {len(circuit.gates)} gates consistent: "
          f"{'YES' if inconsistent == -1 else 'NO (gate ' + str(inconsistent) + ')'}")

    # --- Part 4: Fraud Proof ---
    print(f"\n--- Part 4: Fraud Proof (Incorrect Execution) ---\n")

    print(f"  Scenario: Prover claims 2 + 3 = 4 (should be 5)")
    print(f"  The prover tampers with the s0 output bit...\n")

    # Build the prover's (fraudulent) circuit
    fraud_circuit = build_addition_circuit()
    fraud_circuit.set_inputs({"a0": 0, "a1": 1, "b0": 1, "b1": 1})
    fraud_circuit.propagate()  # Compute honestly first

    # Now tamper: change s0 from 1 to 0 (making result 4 instead of 5)
    fraud_circuit.wires["s0"].commit_to(0)  # Lie: should be 1

    fraud_s0 = fraud_circuit.wires["s0"].value
    fraud_s1 = fraud_circuit.wires["s1"].value
    fraud_s2 = fraud_circuit.wires["s2"].value
    fraud_result = fraud_s0 | (fraud_s1 << 1) | (fraud_s2 << 2)

    print(f"  Prover's claimed output: s2={fraud_s2} s1={fraud_s1} s0={fraud_s0} "
          f"(decimal {fraud_result})")
    print(f"  Correct output:          s2={s2} s1={s1} s0={s0} (decimal {result})")

    # Find the inconsistent gate — gate #3 outputs s0
    bad_gate_id = fraud_circuit.find_inconsistent_gate()
    bad_gate = fraud_circuit.gates[bad_gate_id]
    print(f"\n  Locating fraud: scanning {len(fraud_circuit.gates)} gates...")
    print(f"  Found inconsistent gate: #{bad_gate_id} "
          f"(output wire: {bad_gate.output.label})")

    print(f"\n  In real BitVM, the bisection protocol narrows N gates to 1")
    print(f"  in log2(N) rounds. For {len(fraud_circuit.gates)} gates: "
          f"{len(fraud_circuit.gates).bit_length()} rounds max.")
    print(f"  Each round, verifier challenges prover to reveal midpoint values.")

    # Show the bisection concept
    num_gates = len(fraud_circuit.gates)
    print(f"\n  Bisection illustration (conceptual):")
    print(f"  ┌{'─' * 50}┐")
    print(f"  │ Full circuit: gates [0, {num_gates-1}]"
          f"{' ' * (50 - 28 - len(str(num_gates-1)))}│")
    lo, hi = 0, num_gates - 1
    rnd = 1
    while lo < hi:
        mid = (lo + hi) // 2
        if mid >= bad_gate_id:
            direction = "left"
            hi = mid
        else:
            direction = "right"
            lo = mid + 1
        print(f"  │ Round {rnd}: mid={mid:>2} → error is {direction}"
              f" → [{lo:>2}, {hi:>2}]"
              f"{' ' * (50 - 38 - len(str(lo)) - len(str(hi)))}│")
        rnd += 1
    print(f"  │ Found: gate #{lo}"
          f"{' ' * (50 - 14 - len(str(lo)))}│")
    print(f"  └{'─' * 50}┘")

    # On-chain verification of the faulty gate
    found_gate = bad_gate_id
    ok, msg = bad_gate.verify_on_chain()

    print(f"\n  On-chain verification of gate #{found_gate}:")
    print(f"  ┌────────────────────────────────────────────────────────┐")
    print(f"  │ Input A ({bad_gate.input_a.label}): "
          f"bit = {bad_gate.input_a.value}"
          f"{' ' * (40 - len(bad_gate.input_a.label))}│")
    print(f"  │ Input B ({bad_gate.input_b.label}): "
          f"bit = {bad_gate.input_b.value}"
          f"{' ' * (40 - len(bad_gate.input_b.label))}│")
    print(f"  │ Output  ({bad_gate.output.label}):  "
          f"bit = {bad_gate.output.value} "
          f"(expected {bad_gate.expected_output()})"
          f"{' ' * (30 - len(bad_gate.output.label))}│")
    print(f"  │ Verdict: {msg:<48}│")
    print(f"  └────────────────────────────────────────────────────────┘")

    # --- Part 5: Protocol Summary ---
    print(f"\n--- Part 5: BitVM Protocol Overview ---\n")

    print(f"  ┌────────────────────────────────────────────────────────┐")
    print(f"  │              BitVM Protocol Steps                      │")
    print(f"  ├────────────────────────────────────────────────────────┤")
    print(f"  │ 1. SETUP                                               │")
    print(f"  │    Prover commits to all wire values (hash pairs)      │")
    print(f"  │    Published on-chain: hash0, hash1 for every wire     │")
    print(f"  │                                                        │")
    print(f"  │ 2. CLAIM                                               │")
    print(f"  │    Prover asserts: f(x) = y                            │")
    print(f"  │    (off-chain computation, on-chain commitment)        │")
    print(f"  │                                                        │")
    print(f"  │ 3. CHALLENGE (if verifier disagrees)                   │")
    print(f"  │    Bisection: narrow N gates to 1 in log2(N) rounds    │")
    print(f"  │    Each round: prover reveals midpoint wire values     │")
    print(f"  │                                                        │")
    print(f"  │ 4. FRAUD PROOF (on-chain, single gate)                 │")
    print(f"  │    Reveal 3 preimages (2 inputs + 1 output)            │")
    print(f"  │    Script verifies: output != NAND(input_a, input_b)   │")
    print(f"  │    Prover loses their bond                             │")
    print(f"  ├────────────────────────────────────────────────────────┤")
    print(f"  │ Key properties:                                        │")
    print(f"  │ - Computation is off-chain (scales to any program)     │")
    print(f"  │ - Verification is on-chain (1 gate = ~100 bytes)       │")
    print(f"  │ - Optimistic: if prover is honest, no challenge needed │")
    print(f"  │ - log2(N) rounds to find fraud in N-gate circuit       │")
    bisection_rounds = len(circuit.gates).bit_length()
    print(f"  │ - This {len(circuit.gates)}-gate circuit: "
          f"{bisection_rounds} bisection rounds max{' ' * 13}│")
    print(f"  └────────────────────────────────────────────────────────┘")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
