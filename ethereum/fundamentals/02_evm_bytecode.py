"""
TITLE: EVM Bytecode Interpreter
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    A simplified Ethereum Virtual Machine (EVM) that executes raw bytecode.
    Implements a 256-bit stack machine with memory, storage, and control flow.
    Each opcode is executed step-by-step with full visibility into machine state.

KEY CONCEPTS:
    - Stack-based virtual machine architecture (LIFO, max 1024 depth)
    - 256-bit word size (all stack items are 0..2^256-1)
    - Byte-addressable memory (expands dynamically, word-aligned reads/writes)
    - Persistent storage (key-value mapping of 256-bit words)
    - Control flow with JUMP / JUMPI / JUMPDEST

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (understanding of hash functions)
    - ethereum/01_accounts_state.py (account model context)

REAL-WORLD RELEVANCE:
    Every smart contract on Ethereum compiles down to EVM bytecode. When you
    call a function on a contract, the EVM executes these exact opcodes.
    Understanding the EVM is essential for security auditing, gas optimization,
    and debugging Solidity/Vyper contracts.
"""

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# All EVM values are 256-bit unsigned integers (uint256).
# Python ints are arbitrary precision, so we mask to 256 bits after operations.
UINT256_MAX = (1 << 256) - 1

# Maximum stack depth — the real EVM enforces this limit
MAX_STACK_DEPTH = 1024

# --- Opcode definitions (hex value → mnemonic) --------------------------------
# We define only the subset needed for meaningful programs.

# Arithmetic / comparison
STOP      = 0x00  # Halts execution
ADD       = 0x01  # a + b
MUL       = 0x02  # a * b
SUB       = 0x03  # a - b
DIV       = 0x04  # a // b (integer division, 0 if b==0)
MOD       = 0x06  # a % b (0 if b==0)
LT        = 0x10  # 1 if a < b, else 0
GT        = 0x11  # 1 if a > b, else 0
EQ        = 0x14  # 1 if a == b, else 0
ISZERO    = 0x15  # 1 if a == 0, else 0

# Bitwise
AND       = 0x16  # a & b
OR        = 0x17  # a | b
NOT       = 0x19  # bitwise NOT (complement in 256-bit field)

# Stack / memory / storage
POP       = 0x50  # Remove top of stack
MLOAD     = 0x51  # Load 32-byte word from memory at offset
MSTORE    = 0x52  # Store 32-byte word to memory at offset
SLOAD     = 0x54  # Load word from storage at key
SSTORE    = 0x55  # Store word to storage at key

# Control flow
JUMP      = 0x56  # Unconditional jump to destination
JUMPI     = 0x57  # Conditional jump (if condition != 0)
JUMPDEST  = 0x5B  # Mark valid jump destination (no-op otherwise)

# Push operations: PUSH1 (0x60) through PUSH32 (0x7f)
# PUSH<n> reads the next n bytes from code and pushes them as a uint256
PUSH1     = 0x60  # Push 1 byte
PUSH32    = 0x7F  # Push 32 bytes

# Duplication and swap (we implement DUP1 and SWAP1 as examples)
DUP1      = 0x80  # Duplicate top of stack
SWAP1     = 0x90  # Swap top two stack items

# Return
RETURN    = 0xF3  # Return data from memory

# Human-readable name lookup for trace output
OPCODE_NAMES = {
    0x00: "STOP",   0x01: "ADD",    0x02: "MUL",    0x03: "SUB",
    0x04: "DIV",    0x06: "MOD",    0x10: "LT",     0x11: "GT",
    0x14: "EQ",     0x15: "ISZERO", 0x16: "AND",    0x17: "OR",
    0x19: "NOT",    0x50: "POP",    0x51: "MLOAD",  0x52: "MSTORE",
    0x54: "SLOAD",  0x55: "SSTORE", 0x56: "JUMP",   0x57: "JUMPI",
    0x5B: "JUMPDEST", 0x80: "DUP1", 0x90: "SWAP1", 0xF3: "RETURN",
}
# Add PUSH1..PUSH32 names dynamically
for i in range(32):
    OPCODE_NAMES[0x60 + i] = f"PUSH{i + 1}"


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

class EVMError(Exception):
    """Base exception for EVM execution errors."""
    pass


class StackUnderflow(EVMError):
    """Raised when an opcode tries to pop from an empty stack."""
    pass


class StackOverflow(EVMError):
    """Raised when stack exceeds MAX_STACK_DEPTH."""
    pass


class InvalidJump(EVMError):
    """Raised when JUMP/JUMPI targets a non-JUMPDEST location."""
    pass


class OutOfGas(EVMError):
    """Raised when gas is exhausted (used in script 03)."""
    pass


class EVM:
    """A minimal Ethereum Virtual Machine implementation.

    Executes raw bytecode one opcode at a time, maintaining:
      - stack:   list of uint256 values (index -1 is the top)
      - memory:  bytearray that grows on demand
      - storage: dict mapping uint256 keys to uint256 values
      - pc:      program counter (byte offset into code)
    """

    def __init__(self, code: bytes, trace: bool = True):
        self.code = code              # The raw bytecode to execute
        self.pc = 0                   # Program counter — index of next opcode
        self.stack: list[int] = []    # The operand stack (LIFO)
        self.memory = bytearray()     # Byte-addressable, grows as needed
        self.storage: dict[int, int] = {}  # Persistent key → value store
        self.running = True           # Set to False by STOP or RETURN
        self.trace = trace            # Whether to print execution trace
        self.return_data = b""        # Data returned by RETURN opcode
        self.steps = 0                # Total opcodes executed

    # --- Stack helpers --------------------------------------------------------

    def _push(self, value: int):
        """Push a uint256 onto the stack, checking for overflow."""
        if len(self.stack) >= MAX_STACK_DEPTH:
            raise StackOverflow(f"Stack overflow at pc={self.pc}")
        self.stack.append(value & UINT256_MAX)  # Mask to 256 bits

    def _pop(self) -> int:
        """Pop and return the top stack value, checking for underflow."""
        if not self.stack:
            raise StackUnderflow(f"Stack underflow at pc={self.pc}")
        return self.stack.pop()

    # --- Memory helpers -------------------------------------------------------

    def _memory_extend(self, offset: int, size: int):
        """Extend memory if the access would go out of bounds."""
        needed = offset + size
        if needed > len(self.memory):
            # Extend with zero bytes — memory is zero-initialized
            self.memory.extend(b"\x00" * (needed - len(self.memory)))

    def _mstore(self, offset: int, value: int):
        """Store a 32-byte (256-bit) word at the given byte offset."""
        self._memory_extend(offset, 32)
        # Convert uint256 to 32 bytes big-endian
        word_bytes = value.to_bytes(32, "big")
        self.memory[offset:offset + 32] = word_bytes

    def _mload(self, offset: int) -> int:
        """Load a 32-byte word from memory at the given byte offset."""
        self._memory_extend(offset, 32)
        word_bytes = bytes(self.memory[offset:offset + 32])
        return int.from_bytes(word_bytes, "big")

    # --- Valid jump destinations -----------------------------------------------

    def _valid_jumpdests(self) -> set[int]:
        """Scan the code to find all positions marked with JUMPDEST (0x5B).

        This prevents jumping into the middle of PUSH data or arbitrary code.
        """
        dests = set()
        i = 0
        while i < len(self.code):
            op = self.code[i]
            if op == JUMPDEST:
                dests.add(i)
            # Skip over PUSH<n> immediate bytes
            if PUSH1 <= op <= PUSH32:
                n = op - PUSH1 + 1  # Number of bytes to skip
                i += n
            i += 1
        return dests

    # --- Trace printing -------------------------------------------------------

    def _print_trace(self, pc: int, opcode: int, name: str):
        """Print the current opcode and machine state."""
        stack_str = [f"0x{v:X}" if v > 255 else str(v) for v in self.stack]
        # Show at most 6 stack items for readability
        if len(stack_str) > 6:
            stack_str = stack_str[-6:] + ["..."]
        stack_display = ", ".join(reversed(stack_str))  # Top of stack first

        mem_size = len(self.memory)
        storage_count = len(self.storage)

        print(f"  pc={pc:04d}  {name:<10}  "
              f"stack=[{stack_display}]  "
              f"mem={mem_size}B  store={storage_count}")

    # --- Main execution loop --------------------------------------------------

    def run(self) -> bytes:
        """Execute bytecode until STOP, RETURN, or end of code.

        Returns the return data (empty bytes if STOP).
        """
        jumpdests = self._valid_jumpdests()  # Pre-scan valid jump targets

        if self.trace:
            print(f"\n  {'─' * 60}")
            print(f"  Executing {len(self.code)} bytes of bytecode")
            print(f"  Code: {self.code.hex()}")
            print(f"  {'─' * 60}")

        while self.running and self.pc < len(self.code):
            pc_before = self.pc
            opcode = self.code[self.pc]          # Fetch current opcode
            name = OPCODE_NAMES.get(opcode, f"0x{opcode:02X}")

            self.pc += 1  # Advance past the opcode byte
            self.steps += 1

            # --- Dispatch opcode -----------------------------------------------

            if opcode == STOP:
                self.running = False

            elif opcode == ADD:
                a, b = self._pop(), self._pop()
                self._push(a + b)                # Mask applied in _push

            elif opcode == MUL:
                a, b = self._pop(), self._pop()
                self._push(a * b)

            elif opcode == SUB:
                a, b = self._pop(), self._pop()
                self._push(a - b)                # Wraps to uint256 via mask

            elif opcode == DIV:
                a, b = self._pop(), self._pop()
                self._push(a // b if b != 0 else 0)  # EVM: div by 0 returns 0

            elif opcode == MOD:
                a, b = self._pop(), self._pop()
                self._push(a % b if b != 0 else 0)

            elif opcode == LT:
                a, b = self._pop(), self._pop()
                self._push(1 if a < b else 0)

            elif opcode == GT:
                a, b = self._pop(), self._pop()
                self._push(1 if a > b else 0)

            elif opcode == EQ:
                a, b = self._pop(), self._pop()
                self._push(1 if a == b else 0)

            elif opcode == ISZERO:
                a = self._pop()
                self._push(1 if a == 0 else 0)

            elif opcode == AND:
                a, b = self._pop(), self._pop()
                self._push(a & b)

            elif opcode == OR:
                a, b = self._pop(), self._pop()
                self._push(a | b)

            elif opcode == NOT:
                a = self._pop()
                self._push(UINT256_MAX ^ a)      # Bitwise complement in 256-bit

            elif opcode == POP:
                self._pop()                       # Discard top value

            elif opcode == MLOAD:
                offset = self._pop()
                self._push(self._mload(offset))

            elif opcode == MSTORE:
                offset = self._pop()
                value = self._pop()
                self._mstore(offset, value)

            elif opcode == SLOAD:
                key = self._pop()
                value = self.storage.get(key, 0)  # Default: 0 (uninitialized)
                self._push(value)

            elif opcode == SSTORE:
                key = self._pop()
                value = self._pop()
                self.storage[key] = value

            elif opcode == JUMP:
                dest = self._pop()
                if dest not in jumpdests:
                    raise InvalidJump(f"Invalid JUMP to {dest} at pc={pc_before}")
                self.pc = dest                    # Jump to destination

            elif opcode == JUMPI:
                dest = self._pop()
                cond = self._pop()
                if cond != 0:                     # Jump only if condition is truthy
                    if dest not in jumpdests:
                        raise InvalidJump(f"Invalid JUMPI to {dest} at pc={pc_before}")
                    self.pc = dest

            elif opcode == JUMPDEST:
                pass                              # No-op: just marks a valid target

            elif PUSH1 <= opcode <= PUSH32:
                n = opcode - PUSH1 + 1            # Number of bytes to read
                # Read n bytes from code starting at current pc
                raw = self.code[self.pc:self.pc + n]
                value = int.from_bytes(raw, "big")  # Big-endian, like the EVM
                self._push(value)
                self.pc += n                      # Skip past the immediate bytes
                name = f"PUSH{n} 0x{value:X}" if value > 255 else f"PUSH{n} {value}"

            elif opcode == DUP1:
                if not self.stack:
                    raise StackUnderflow(f"Stack underflow at DUP1, pc={pc_before}")
                self._push(self.stack[-1])        # Copy top without removing

            elif opcode == SWAP1:
                if len(self.stack) < 2:
                    raise StackUnderflow(f"Stack underflow at SWAP1, pc={pc_before}")
                # Swap top two elements
                self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]

            elif opcode == RETURN:
                offset = self._pop()
                size = self._pop()
                self._memory_extend(offset, size)
                self.return_data = bytes(self.memory[offset:offset + size])
                self.running = False

            else:
                raise EVMError(f"Unknown opcode 0x{opcode:02X} at pc={pc_before}")

            if self.trace:
                self._print_trace(pc_before, opcode, name)

        return self.return_data


# --- Helper: assemble bytecode from opcode list --------------------------------

def assemble(*ops) -> bytes:
    """Convert a list of opcode ints/bytes into a bytecode bytes object.

    Convenience function so we don't have to write raw hex everywhere.
    """
    result = bytearray()
    for op in ops:
        if isinstance(op, int):
            result.append(op & 0xFF)
        elif isinstance(op, bytes):
            result.extend(op)
        else:
            raise ValueError(f"Invalid operand: {op}")
    return bytes(result)


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run several EVM programs to demonstrate how the stack machine works."""

    print("=" * 64)
    print("  EVM BYTECODE INTERPRETER")
    print("  A 256-bit stack machine executing raw opcodes")
    print("=" * 64)

    # --- Program 1: Simple arithmetic (2 + 3) * 7 = 35 -----------------------

    print("\n" + "=" * 64)
    print("  Program 1: (2 + 3) * 7 = 35")
    print("=" * 64)
    print("  Bytecode: PUSH1 2, PUSH1 3, ADD, PUSH1 7, MUL, STOP")

    code1 = assemble(
        PUSH1, 0x02,   # Push 2
        PUSH1, 0x03,   # Push 3
        ADD,           # 2 + 3 = 5
        PUSH1, 0x07,   # Push 7
        MUL,           # 5 * 7 = 35
        STOP,
    )
    evm1 = EVM(code1)
    evm1.run()
    print(f"\n  Final stack top: {evm1.stack[-1]}")
    assert evm1.stack[-1] == 35, "Arithmetic check failed"
    print("  [PASS] Result is 35")

    # --- Program 2: Store and load from memory --------------------------------

    print("\n" + "=" * 64)
    print("  Program 2: Memory store and load")
    print("=" * 64)
    print("  Store 0xCAFE at memory[0], load it back")

    code2 = assemble(
        PUSH1, 0x00,          # Memory offset 0
        PUSH1, 0x00,          # Placeholder (will be overwritten by MSTORE's value)
        POP,                  # Clean up
        PUSH32,               # Push a 32-byte value: 0xCAFE
        *b"\x00" * 30,        # 30 zero bytes
        b"\xCA\xFE",          # Last 2 bytes = 0xCAFE
        PUSH1, 0x00,          # Memory offset 0
        MSTORE,               # Store the 32-byte word at memory[0]
        PUSH1, 0x00,          # Memory offset 0
        MLOAD,                # Load 32-byte word from memory[0]
        STOP,
    )
    evm2 = EVM(code2)
    evm2.run()
    print(f"\n  Final stack top: 0x{evm2.stack[-1]:X}")
    assert evm2.stack[-1] == 0xCAFE, "Memory round-trip failed"
    print("  [PASS] Memory round-trip: 0xCAFE")

    # --- Program 3: Persistent storage (SSTORE / SLOAD) -----------------------

    print("\n" + "=" * 64)
    print("  Program 3: Storage write and read")
    print("=" * 64)
    print("  SSTORE key=1 value=42, then SLOAD key=1")

    code3 = assemble(
        PUSH1, 42,     # Value to store
        PUSH1, 1,      # Storage key
        SSTORE,        # storage[1] = 42
        PUSH1, 1,      # Storage key
        SLOAD,         # Push storage[1] onto stack
        STOP,
    )
    evm3 = EVM(code3)
    evm3.run()
    print(f"\n  Final stack top: {evm3.stack[-1]}")
    print(f"  Storage: {evm3.storage}")
    assert evm3.stack[-1] == 42, "Storage round-trip failed"
    print("  [PASS] Storage round-trip: key=1 → 42")

    # --- Program 4: Conditional jump (simple if/else) -------------------------

    print("\n" + "=" * 64)
    print("  Program 4: Conditional jump (loop with JUMPI)")
    print("=" * 64)
    print("  Count from 3 down to 0 using a loop")
    print("  Equivalent to: x=3; while(x>0) x=x-1;")

    # Layout:
    #   0: PUSH1 3          — initial counter = 3
    #   2: JUMPDEST         — loop target (pc=2)
    #   3: DUP1             — copy counter for comparison
    #   4: PUSH1 0          — push 0
    #   6: EQ               — counter == 0?
    #   7: PUSH1 17         — push exit address (pc=17)
    #   9: JUMPI            — if counter==0, jump to exit
    #  10: PUSH1 1          — push 1
    #  12: SWAP1            — swap so counter is on top
    #  13: SUB              — counter - 1
    #  14: PUSH1 2          — push loop address
    #  16: JUMP             — jump back to JUMPDEST
    #  17: JUMPDEST         — exit point
    #  18: STOP

    code4 = assemble(
        PUSH1, 3,       # pc=0: counter = 3
        JUMPDEST,       # pc=2: loop start
        DUP1,           # pc=3: duplicate counter
        PUSH1, 0,       # pc=4: push 0
        EQ,             # pc=6: counter == 0?
        PUSH1, 17,      # pc=7: exit address (pc=17, where JUMPDEST is)
        JUMPI,          # pc=9: conditional jump
        PUSH1, 1,       # pc=10: push 1
        SWAP1,          # pc=12: swap so counter is on top for SUB
        SUB,            # pc=13: counter - 1
        PUSH1, 2,       # pc=14: loop address (pc=2)
        JUMP,           # pc=16: jump back
        JUMPDEST,       # pc=17: exit point
        STOP,           # pc=18: halt
    )
    evm4 = EVM(code4)
    evm4.run()
    print(f"\n  Final stack top: {evm4.stack[-1]}")
    print(f"  Total steps: {evm4.steps}")
    assert evm4.stack[-1] == 0, "Loop should end with counter=0"
    print("  [PASS] Loop terminated with counter = 0")

    # --- Program 5: RETURN data from memory -----------------------------------

    print("\n" + "=" * 64)
    print("  Program 5: RETURN data from memory")
    print("=" * 64)
    print("  Compute 10 + 20 = 30, store in memory, return 32 bytes")

    code5 = assemble(
        PUSH1, 10,      # Push 10
        PUSH1, 20,      # Push 20
        ADD,            # 10 + 20 = 30
        PUSH1, 0,       # Memory offset 0
        MSTORE,         # Store result at memory[0]
        PUSH1, 32,      # Return size: 32 bytes
        PUSH1, 0,       # Return offset: 0
        RETURN,         # Return memory[0:32]
    )
    evm5 = EVM(code5)
    ret = evm5.run()
    result = int.from_bytes(ret, "big")
    print(f"\n  Return data (hex): {ret.hex()}")
    print(f"  Return data (int): {result}")
    assert result == 30, "Return value should be 30"
    print("  [PASS] Returned value 30")

    # --- Summary --------------------------------------------------------------

    print("\n" + "=" * 64)
    print("  KEY TAKEAWAYS")
    print("=" * 64)
    print("  1. The EVM is a stack machine — operands are pushed/popped, not in registers")
    print("  2. All values are 256-bit unsigned integers (uint256)")
    print("  3. Memory is volatile (cleared per call), storage is persistent")
    print("  4. JUMP/JUMPI can only target JUMPDEST opcodes (security measure)")
    print("  5. RETURN copies memory to the caller — this is how functions return data")
    print("  6. Every Solidity function compiles to sequences of these basic opcodes")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
