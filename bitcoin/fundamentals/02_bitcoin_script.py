"""
TITLE: Bitcoin Script VM
CATEGORY: bitcoin

WHAT THIS IMPLEMENTS:
    A stack-based virtual machine that executes Bitcoin Script, the simple
    programming language used to lock and unlock bitcoins. Implements core
    opcodes (OP_DUP, OP_HASH160, OP_CHECKSIG, flow control, arithmetic)
    and evaluates Pay-to-Public-Key-Hash (P2PKH) scripts step by step.

KEY CONCEPTS:
    - Stack-based execution: opcodes push/pop values from a LIFO stack
    - ScriptSig (unlocking) + ScriptPubKey (locking) concatenation model
    - P2PKH: the most common Bitcoin transaction type, checks signature + pubkey hash
    - Intentionally limited: no loops, no Turing-completeness (by design)

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (SHA-256 hashing)
    - core/02_public_key_crypto.py (elliptic curve keypairs)
    - core/03_digital_signatures.py (ECDSA sign/verify)

REAL-WORLD RELEVANCE:
    Every Bitcoin transaction contains a Script that must evaluate to true
    for the coins to be spent. P2PKH scripts protect the vast majority of
    bitcoin UTXOs, requiring proof of key ownership via signature verification.
"""

import hashlib
import secrets

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# secp256k1 curve parameters — Bitcoin's elliptic curve
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F  # field prime
A = 0   # curve coefficient a
B = 7   # curve coefficient b
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141  # group order
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (GX, GY)  # generator point — everyone starts from here
INFINITY = None  # the "zero element" on the curve

# Opcode constants — numeric identifiers matching Bitcoin Core's definitions
OP_0 = 0x00          # push empty byte string (falsy)
OP_FALSE = 0x00      # alias for OP_0
OP_TRUE = 0x51       # push the number 1 (truthy)
OP_DUP = 0x76        # duplicate top stack item
OP_HASH160 = 0xA9    # SHA-256 then RIPEMD-160 (Bitcoin address hash)
OP_EQUAL = 0x87      # check if top two items are equal, push result
OP_EQUALVERIFY = 0x88  # OP_EQUAL + OP_VERIFY combined
OP_CHECKSIG = 0xAC   # verify ECDSA signature against pubkey
OP_VERIFY = 0x69     # fail if top stack item is falsy
OP_IF = 0x63         # conditional branch: execute next block if top is truthy
OP_ELSE = 0x67       # alternative branch for OP_IF
OP_ENDIF = 0x68      # end conditional block
OP_ADD = 0x93        # pop two items, push their sum
OP_SUB = 0x94        # pop two items, push (second - first)
OP_DATA = 0xFF       # pseudo-opcode: push raw data onto stack (not a real Bitcoin opcode)

# Human-readable opcode names for display
OPCODE_NAMES = {
    OP_0: "OP_FALSE",
    OP_TRUE: "OP_TRUE",
    OP_DUP: "OP_DUP",
    OP_HASH160: "OP_HASH160",
    OP_EQUAL: "OP_EQUAL",
    OP_EQUALVERIFY: "OP_EQUALVERIFY",
    OP_CHECKSIG: "OP_CHECKSIG",
    OP_VERIFY: "OP_VERIFY",
    OP_IF: "OP_IF",
    OP_ELSE: "OP_ELSE",
    OP_ENDIF: "OP_ENDIF",
    OP_ADD: "OP_ADD",
    OP_SUB: "OP_SUB",
    OP_DATA: "OP_DATA",
}

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# ----------------------------------------------------------------------------
# 2a: Elliptic curve arithmetic (self-contained, no imports from other scripts)
# ----------------------------------------------------------------------------

def mod_inv(a, m):
    """Modular inverse via Fermat's little theorem: a^(m-2) mod m."""
    return pow(a, m - 2, m)


def point_add(p1, p2):
    """Add two points on secp256k1. Handles identity and doubling cases."""
    if p1 is INFINITY:
        return p2
    if p2 is INFINITY:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and y1 != y2:
        return INFINITY  # point + its inverse = identity

    if x1 == x2 and y1 == y2:
        # Point doubling: tangent slope = (3x^2 + a) / (2y)
        lam = (3 * x1 * x1 + A) * mod_inv(2 * y1, P) % P
    else:
        # Point addition: secant slope = (y2 - y1) / (x2 - x1)
        lam = (y2 - y1) * mod_inv(x2 - x1, P) % P

    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def scalar_mult(k, point):
    """Multiply a curve point by integer k using double-and-add algorithm."""
    result = INFINITY
    addend = point
    while k > 0:
        if k & 1:  # if the lowest bit is set, add current point
            result = point_add(result, addend)
        addend = point_add(addend, addend)  # double the point each step
        k >>= 1  # shift to next bit
    return result

# ----------------------------------------------------------------------------
# 2b: ECDSA signing and verification (needed for OP_CHECKSIG)
# ----------------------------------------------------------------------------

def ecdsa_sign(private_key, message_bytes):
    """Sign a message hash using ECDSA on secp256k1. Returns (r, s)."""
    z = int.from_bytes(hashlib.sha256(message_bytes).digest(), "big")  # hash the message
    while True:
        k = secrets.randbelow(N - 1) + 1  # random nonce, must be [1, N-1]
        r_point = scalar_mult(k, G)
        r = r_point[0] % N  # r = x-coordinate of k*G mod N
        if r == 0:
            continue  # vanishingly rare, try again
        k_inv = mod_inv(k, N)
        s = (k_inv * (z + r * private_key)) % N  # s = k^-1 * (hash + r * privkey)
        if s == 0:
            continue
        return (r, s)


def ecdsa_verify(public_key, message_bytes, signature):
    """Verify an ECDSA signature. Returns True if valid."""
    r, s = signature
    if not (1 <= r < N and 1 <= s < N):
        return False  # signature values out of range
    z = int.from_bytes(hashlib.sha256(message_bytes).digest(), "big")
    s_inv = mod_inv(s, N)
    u1 = (z * s_inv) % N       # weight for generator point
    u2 = (r * s_inv) % N       # weight for public key point
    point = point_add(scalar_mult(u1, G), scalar_mult(u2, public_key))
    if point is INFINITY:
        return False
    return point[0] % N == r   # valid if recovered x-coordinate matches r

# ----------------------------------------------------------------------------
# 2c: Hash functions used by Bitcoin Script
# ----------------------------------------------------------------------------

def hash160(data):
    """HASH160 = RIPEMD-160(SHA-256(data)). Used to create Bitcoin addresses."""
    sha = hashlib.sha256(data).digest()
    ripemd = hashlib.new("ripemd160", sha).digest()
    return ripemd


def serialize_pubkey(pub):
    """Serialize a public key point as 65-byte uncompressed format (04 || x || y)."""
    return b'\x04' + pub[0].to_bytes(32, "big") + pub[1].to_bytes(32, "big")


def serialize_signature(sig):
    """Serialize an ECDSA signature as r || s (64 bytes)."""
    r, s = sig
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def deserialize_pubkey(data):
    """Deserialize 65-byte uncompressed public key back to (x, y) tuple."""
    # Skip the 0x04 prefix byte
    x = int.from_bytes(data[1:33], "big")
    y = int.from_bytes(data[33:65], "big")
    return (x, y)


def deserialize_signature(data):
    """Deserialize 64-byte signature back to (r, s) tuple."""
    r = int.from_bytes(data[:32], "big")
    s = int.from_bytes(data[32:64], "big")
    return (r, s)

# ----------------------------------------------------------------------------
# 2d: Script instruction representation
# ----------------------------------------------------------------------------

class ScriptOp:
    """Represents a single instruction in a Bitcoin Script program.
    An instruction is either an opcode (like OP_DUP) or a data push."""

    def __init__(self, opcode, data=None):
        self.opcode = opcode  # the opcode number
        self.data = data      # raw bytes if this is a data push, else None

    def name(self):
        """Human-readable name for display."""
        if self.opcode == OP_DATA:
            # Show truncated hex for data pushes to keep output readable
            hex_str = self.data.hex()
            if len(hex_str) > 16:
                return f"<{hex_str[:16]}...>"
            return f"<{hex_str}>"
        return OPCODE_NAMES.get(self.opcode, f"UNKNOWN(0x{self.opcode:02x})")


def data_op(data):
    """Helper to create a data-push instruction."""
    return ScriptOp(OP_DATA, data)

# ----------------------------------------------------------------------------
# 2e: Script VM — the execution engine
# ----------------------------------------------------------------------------

class ScriptError(Exception):
    """Raised when script execution fails (e.g., stack underflow, verify failure)."""
    pass


class ScriptVM:
    """Stack-based virtual machine that executes Bitcoin Script programs.

    Bitcoin Script is intentionally NOT Turing-complete — no loops, no recursion.
    This prevents denial-of-service attacks on the network. Scripts either
    succeed (non-empty, truthy top-of-stack) or fail."""

    def __init__(self, script, message=b"", trace=False):
        self.script = script        # list of ScriptOp instructions
        self.stack = []             # the main data stack (list of bytes)
        self.message = message      # the "transaction" being validated (for CHECKSIG)
        self.trace = trace          # if True, record execution trace for display
        self.trace_log = []         # list of (op_name, stack_snapshot) tuples
        self.pc = 0                 # program counter (current instruction index)

    def _push(self, data):
        """Push bytes onto the stack."""
        self.stack.append(data)

    def _pop(self):
        """Pop bytes from the stack. Raises ScriptError if empty."""
        if not self.stack:
            raise ScriptError("Stack underflow — tried to pop from empty stack")
        return self.stack.pop()

    def _peek(self):
        """Look at the top item without removing it."""
        if not self.stack:
            raise ScriptError("Stack underflow — tried to peek at empty stack")
        return self.stack[-1]

    def _is_truthy(self, data):
        """Check if a stack value is truthy (non-zero bytes).
        Bitcoin defines false as empty bytes or all-zero bytes."""
        return data != b'' and data != b'\x00' and any(b != 0 for b in data)

    def _int_to_bytes(self, n):
        """Encode a Python int as Bitcoin Script's little-endian signed format."""
        if n == 0:
            return b'\x00'
        negative = n < 0
        n = abs(n)
        result = []
        while n > 0:
            result.append(n & 0xFF)
            n >>= 8
        # If the high bit is set, add a sign byte
        if result[-1] & 0x80:
            result.append(0x80 if negative else 0x00)
        elif negative:
            result[-1] |= 0x80
        return bytes(result)

    def _bytes_to_int(self, data):
        """Decode Bitcoin Script's little-endian signed format to Python int."""
        if not data:
            return 0
        # Check sign bit of the last byte
        negative = data[-1] & 0x80
        result = 0
        for i, b in enumerate(data):
            if i == len(data) - 1:
                b &= 0x7F  # strip sign bit from last byte
            result |= b << (8 * i)
        return -result if negative else result

    def _snapshot_stack(self):
        """Create a human-readable snapshot of the current stack for tracing."""
        items = []
        for item in self.stack:
            hex_str = item.hex()
            if len(hex_str) <= 16:
                items.append(hex_str)
            else:
                items.append(hex_str[:16] + "...")
        return items

    def _record_trace(self, op_name):
        """Record the current state after executing an opcode."""
        if self.trace:
            self.trace_log.append((op_name, self._snapshot_stack()))

    def _find_matching_else_or_endif(self, start_pc):
        """Find the OP_ELSE or OP_ENDIF matching the OP_IF at start_pc.
        Handles nested IF/ELSE/ENDIF blocks by tracking nesting depth."""
        depth = 1  # we're inside one IF block
        pc = start_pc + 1
        while pc < len(self.script):
            op = self.script[pc].opcode
            if op == OP_IF:
                depth += 1  # entering a nested IF
            elif op == OP_ELSE and depth == 1:
                return pc  # found matching ELSE at our level
            elif op == OP_ENDIF:
                depth -= 1
                if depth == 0:
                    return pc  # found matching ENDIF
            pc += 1
        raise ScriptError("OP_IF without matching OP_ENDIF")

    def execute(self):
        """Execute the script. Returns True if the script succeeds
        (stack is non-empty and top element is truthy), False otherwise."""
        self.pc = 0
        while self.pc < len(self.script):
            op = self.script[self.pc]
            self._execute_op(op)
            self.pc += 1

        # Script succeeds if stack is non-empty and top is truthy
        if not self.stack:
            return False
        return self._is_truthy(self.stack[-1])

    def _execute_op(self, op):
        """Execute a single opcode. This is the heart of the VM."""
        if op.opcode == OP_DATA:
            # Push raw data onto the stack
            self._push(op.data)
            self._record_trace(op.name())

        elif op.opcode == OP_FALSE:
            # Push an empty byte string (falsy value)
            self._push(b'')
            self._record_trace("OP_FALSE")

        elif op.opcode == OP_TRUE:
            # Push the number 1 (truthy value)
            self._push(b'\x01')
            self._record_trace("OP_TRUE")

        elif op.opcode == OP_DUP:
            # Duplicate the top stack item — needed so we can hash the pubkey
            # while keeping the original for signature checking later
            top = self._peek()
            self._push(top)
            self._record_trace("OP_DUP")

        elif op.opcode == OP_HASH160:
            # Pop value, push HASH160(value) — creates the "address" hash
            value = self._pop()
            self._push(hash160(value))
            self._record_trace("OP_HASH160")

        elif op.opcode == OP_EQUAL:
            # Pop two items, push 1 if equal, 0 if not
            a = self._pop()
            b = self._pop()
            result = b'\x01' if a == b else b'\x00'
            self._push(result)
            self._record_trace("OP_EQUAL")

        elif op.opcode == OP_EQUALVERIFY:
            # Like OP_EQUAL + OP_VERIFY: check equality, fail immediately if not
            # This is used in P2PKH to confirm the pubkey hashes to the right address
            a = self._pop()
            b = self._pop()
            if a != b:
                self._record_trace("OP_EQUALVERIFY")
                raise ScriptError("OP_EQUALVERIFY failed — values not equal")
            self._record_trace("OP_EQUALVERIFY")

        elif op.opcode == OP_CHECKSIG:
            # The critical opcode: verify that the signature matches the pubkey
            # Pop pubkey, pop signature, verify ECDSA signature over the message
            pubkey_bytes = self._pop()     # serialized public key (65 bytes)
            sig_bytes = self._pop()        # serialized signature (64 bytes)
            pubkey = deserialize_pubkey(pubkey_bytes)
            sig = deserialize_signature(sig_bytes)
            valid = ecdsa_verify(pubkey, self.message, sig)
            self._push(b'\x01' if valid else b'\x00')
            self._record_trace("OP_CHECKSIG")

        elif op.opcode == OP_VERIFY:
            # Pop top item, fail if it's falsy — acts as an assertion
            top = self._pop()
            if not self._is_truthy(top):
                self._record_trace("OP_VERIFY")
                raise ScriptError("OP_VERIFY failed — top of stack was falsy")
            self._record_trace("OP_VERIFY")

        elif op.opcode == OP_IF:
            # Conditional execution: pop condition, skip to ELSE/ENDIF if false
            condition = self._pop()
            self._record_trace("OP_IF")
            if not self._is_truthy(condition):
                # Skip ahead to matching OP_ELSE or OP_ENDIF
                target_pc = self._find_matching_else_or_endif(self.pc)
                self.pc = target_pc  # jump past the false branch

        elif op.opcode == OP_ELSE:
            # If we reach OP_ELSE during normal execution, the IF-branch ran,
            # so skip ahead to the matching OP_ENDIF
            self._record_trace("OP_ELSE")
            depth = 1
            pc = self.pc + 1
            while pc < len(self.script):
                if self.script[pc].opcode == OP_IF:
                    depth += 1
                elif self.script[pc].opcode == OP_ENDIF:
                    depth -= 1
                    if depth == 0:
                        self.pc = pc  # jump to ENDIF (main loop will advance past it)
                        break
                pc += 1

        elif op.opcode == OP_ENDIF:
            # Marks end of a conditional block — nothing to do at execution time
            self._record_trace("OP_ENDIF")

        elif op.opcode == OP_ADD:
            # Pop two numbers, push their sum — used in time-lock scripts
            a = self._bytes_to_int(self._pop())
            b = self._bytes_to_int(self._pop())
            self._push(self._int_to_bytes(a + b))
            self._record_trace("OP_ADD")

        elif op.opcode == OP_SUB:
            # Pop two numbers, push (second - first)
            a = self._bytes_to_int(self._pop())
            b = self._bytes_to_int(self._pop())
            self._push(self._int_to_bytes(b - a))
            self._record_trace("OP_SUB")

        else:
            raise ScriptError(f"Unknown opcode: 0x{op.opcode:02x}")

# ----------------------------------------------------------------------------
# 2f: P2PKH script builder — the standard Bitcoin transaction type
# ----------------------------------------------------------------------------

def build_p2pkh_script_pubkey(pubkey_hash):
    """Build the locking script (scriptPubKey) for P2PKH.
    Pattern: OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG

    This says: "To spend these coins, provide a public key that hashes
    to this address AND a valid signature for that key." """
    return [
        ScriptOp(OP_DUP),
        ScriptOp(OP_HASH160),
        data_op(pubkey_hash),        # the expected hash of the recipient's pubkey
        ScriptOp(OP_EQUALVERIFY),
        ScriptOp(OP_CHECKSIG),
    ]


def build_p2pkh_script_sig(signature_bytes, pubkey_bytes):
    """Build the unlocking script (scriptSig) for P2PKH.
    Pattern: <signature> <pubkey>

    The spender proves ownership by providing their signature and pubkey."""
    return [
        data_op(signature_bytes),    # ECDSA signature over the transaction
        data_op(pubkey_bytes),       # public key (must hash to the address)
    ]

# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def format_stack_display(stack_items):
    """Format a stack snapshot as a visual column for display."""
    if not stack_items:
        return "  (empty)"
    lines = []
    for i, item in enumerate(reversed(stack_items)):
        prefix = "  TOP → " if i == 0 else "        "
        lines.append(f"{prefix}│ {item} │")
    return "\n".join(lines)


def demo():
    """Run visual demonstrations of Bitcoin Script execution."""

    print("=" * 72)
    print("  BITCOIN SCRIPT VM — Stack-Based Transaction Validation")
    print("=" * 72)

    # ------------------------------------------------------------------
    # Demo 1: Simple arithmetic script
    # ------------------------------------------------------------------
    print("\n─── Demo 1: Arithmetic Script ─────────────────────────────────────")
    print("  Script: OP_TRUE OP_TRUE OP_ADD OP_TRUE OP_TRUE OP_ADD OP_EQUAL")
    print("  Purpose: Verify that 1+1 == 1+1 (basic stack arithmetic)\n")

    arith_script = [
        ScriptOp(OP_TRUE),
        ScriptOp(OP_TRUE),
        ScriptOp(OP_ADD),
        ScriptOp(OP_TRUE),
        ScriptOp(OP_TRUE),
        ScriptOp(OP_ADD),
        ScriptOp(OP_EQUAL),
    ]

    vm = ScriptVM(arith_script, trace=True)
    result = vm.execute()

    print("  Step-by-step execution:")
    print("  ┌──────────────────┬──────────────────────────────────┐")
    print("  │     Opcode       │           Stack After            │")
    print("  ├──────────────────┼──────────────────────────────────┤")
    for op_name, stack in vm.trace_log:
        stack_str = ", ".join(stack) if stack else "(empty)"
        print(f"  │ {op_name:<16} │ {stack_str:<32} │")
    print("  └──────────────────┴──────────────────────────────────┘")
    print(f"  Result: {'PASS' if result else 'FAIL'}")

    # ------------------------------------------------------------------
    # Demo 2: OP_IF / OP_ELSE / OP_ENDIF conditional logic
    # ------------------------------------------------------------------
    print("\n─── Demo 2: Conditional Script (IF/ELSE) ───────────────────────────")
    print("  Script: OP_TRUE OP_IF OP_TRUE OP_ELSE OP_FALSE OP_ENDIF")
    print("  Purpose: If condition is true, push 1; else push 0\n")

    cond_script = [
        ScriptOp(OP_TRUE),     # push condition (true)
        ScriptOp(OP_IF),       # evaluate condition
        ScriptOp(OP_TRUE),     # true branch: push 1
        ScriptOp(OP_ELSE),
        ScriptOp(OP_FALSE),    # false branch: push 0
        ScriptOp(OP_ENDIF),
    ]

    vm = ScriptVM(cond_script, trace=True)
    result = vm.execute()

    print("  Step-by-step execution:")
    print("  ┌──────────────────┬──────────────────────────────────┐")
    print("  │     Opcode       │           Stack After            │")
    print("  ├──────────────────┼──────────────────────────────────┤")
    for op_name, stack in vm.trace_log:
        stack_str = ", ".join(stack) if stack else "(empty)"
        print(f"  │ {op_name:<16} │ {stack_str:<32} │")
    print("  └──────────────────┴──────────────────────────────────┘")
    print(f"  Result: {'PASS' if result else 'FAIL'}")

    # ------------------------------------------------------------------
    # Demo 3: Full P2PKH — the main event
    # ------------------------------------------------------------------
    print("\n─── Demo 3: P2PKH (Pay-to-Public-Key-Hash) ─────────────────────────")
    print("  The most common Bitcoin transaction type.")
    print("  Alice locks coins to Bob's address. Bob proves he can spend them.\n")

    # Step 1: Generate Bob's keypair
    print("  Step 1: Bob generates a keypair")
    bob_private = secrets.randbelow(N - 1) + 1       # Bob's secret key
    bob_public = scalar_mult(bob_private, G)          # Bob's public key (on the curve)
    bob_pubkey_bytes = serialize_pubkey(bob_public)    # 65-byte serialized form
    bob_pubkey_hash = hash160(bob_pubkey_bytes)        # HASH160 = the "address"
    print(f"    Private key: {bob_private:#066x}")
    print(f"    Public key:  {bob_pubkey_bytes[:8].hex()}...{bob_pubkey_bytes[-4:].hex()}")
    print(f"    HASH160:     {bob_pubkey_hash.hex()}")

    # Step 2: Alice creates the locking script (scriptPubKey)
    print("\n  Step 2: Alice creates locking script (scriptPubKey)")
    script_pubkey = build_p2pkh_script_pubkey(bob_pubkey_hash)
    print("    OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG")
    print("    Meaning: 'Only the owner of this address can spend'")

    # Step 3: Bob creates the unlocking script (scriptSig)
    print("\n  Step 3: Bob signs the transaction and creates unlocking script")
    tx_message = b"Bob sends 0.5 BTC to Carol"  # simplified "transaction"
    bob_signature = ecdsa_sign(bob_private, tx_message)
    bob_sig_bytes = serialize_signature(bob_signature)
    script_sig = build_p2pkh_script_sig(bob_sig_bytes, bob_pubkey_bytes)
    print(f"    Signature:   {bob_sig_bytes[:8].hex()}...{bob_sig_bytes[-4:].hex()}")
    print("    ScriptSig:   <sig> <pubkey>")

    # Step 4: Concatenate and execute: scriptSig + scriptPubKey
    full_script = script_sig + script_pubkey
    print("\n  Step 4: Execute combined script (scriptSig + scriptPubKey)")
    print("    Full script: <sig> <pubkey> OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG\n")

    vm = ScriptVM(full_script, message=tx_message, trace=True)
    try:
        result = vm.execute()
    except ScriptError as e:
        result = False
        print(f"    Script error: {e}")

    # Display step-by-step execution
    print("  ┌─────────────────────┬────────────────────────────────────────────┐")
    print("  │       Opcode        │              Stack After                   │")
    print("  ├─────────────────────┼────────────────────────────────────────────┤")
    for op_name, stack in vm.trace_log:
        stack_str = ", ".join(stack) if stack else "(empty)"
        # Truncate long stack displays
        if len(stack_str) > 40:
            stack_str = stack_str[:37] + "..."
        print(f"  │ {op_name:<19} │ {stack_str:<42} │")
    print("  └─────────────────────┴────────────────────────────────────────────┘")

    status = "PASS ✓" if result else "FAIL ✗"
    print(f"\n  Transaction validation: {status}")
    print(f"  Bob successfully proved he owns the coins!")

    # ------------------------------------------------------------------
    # Demo 4: Failed P2PKH — wrong key tries to spend
    # ------------------------------------------------------------------
    print("\n─── Demo 4: Failed P2PKH — Attacker Uses Wrong Key ─────────────────")
    print("  Eve tries to spend Bob's coins with her own key.\n")

    # Eve generates her own keypair
    eve_private = secrets.randbelow(N - 1) + 1
    eve_public = scalar_mult(eve_private, G)
    eve_pubkey_bytes = serialize_pubkey(eve_public)
    eve_signature = ecdsa_sign(eve_private, tx_message)
    eve_sig_bytes = serialize_signature(eve_signature)
    print(f"    Eve's pubkey hash: {hash160(eve_pubkey_bytes).hex()}")
    print(f"    Bob's pubkey hash: {bob_pubkey_hash.hex()}")
    print(f"    Hashes match? NO — Eve can't impersonate Bob\n")

    # Eve's scriptSig with Bob's locking script
    eve_script_sig = build_p2pkh_script_sig(eve_sig_bytes, eve_pubkey_bytes)
    eve_full_script = eve_script_sig + script_pubkey

    vm = ScriptVM(eve_full_script, message=tx_message, trace=True)
    try:
        result = vm.execute()
    except ScriptError as e:
        result = False
        print(f"  Script error: {e}")

    print("  ┌─────────────────────┬────────────────────────────────────────────┐")
    print("  │       Opcode        │              Stack After                   │")
    print("  ├─────────────────────┼────────────────────────────────────────────┤")
    for op_name, stack in vm.trace_log:
        stack_str = ", ".join(stack) if stack else "(empty)"
        if len(stack_str) > 40:
            stack_str = stack_str[:37] + "..."
        print(f"  │ {op_name:<19} │ {stack_str:<42} │")
    print("  └─────────────────────┴────────────────────────────────────────────┘")

    status = "PASS ✓" if result else "FAIL ✗"
    print(f"\n  Transaction validation: {status}")
    print(f"  Eve's attempt was REJECTED — the hash of her pubkey doesn't match!")

    print("\n" + "=" * 72)
    print("  KEY TAKEAWAY: Bitcoin Script is intentionally simple — no loops,")
    print("  no Turing-completeness. Every transaction must satisfy a script")
    print("  that proves ownership, making the system secure by design.")
    print("=" * 72)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
