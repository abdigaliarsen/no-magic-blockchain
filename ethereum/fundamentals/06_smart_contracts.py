"""
TITLE: Smart Contracts
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    A simplified smart contract lifecycle: deploying bytecode to a contract
    address, calling functions via ABI-style selectors, and reading/writing
    persistent storage. Includes a minimal stack-based EVM to execute bytecodes.

KEY CONCEPTS:
    - Contract deployment: address = hash(deployer + nonce)
    - Contract calls: load bytecode, set up execution context, run EVM
    - Persistent storage: per-contract key-value store surviving across calls
    - Function dispatch via 4-byte selectors

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (hashing fundamentals)
    - ethereum/01_accounts_state.py (account model and state)
    - ethereum/02_evm_bytecode.py (EVM instruction set)

REAL-WORLD RELEVANCE:
    Smart contracts are the foundation of DeFi, NFTs, DAOs, and all
    programmable blockchain applications. Ethereum's EVM executes contract
    bytecodes in a sandboxed environment with metered gas consumption.
"""

import hashlib  # SHA-256 for hashing — stdlib only (stand-in for keccak256)
import struct   # For encoding/decoding 256-bit integers

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Maximum stack depth for our simplified EVM
MAX_STACK_DEPTH = 1024

# Gas costs for different operations (simplified from actual EVM costs)
GAS_COSTS = {
    "STOP": 0,
    "PUSH": 3,       # PUSH1..PUSH32 all cost 3 gas (Gverylow)
    "POP": 2,
    "ADD": 3,
    "SUB": 3,
    "MUL": 5,
    "DUP": 3,
    "SWAP": 3,
    "SLOAD": 100,    # Reading storage is expensive (cold access)
    "SSTORE": 20000, # Writing storage is the most expensive operation (zero → non-zero, per EIP-2200)
    "MLOAD": 3,
    "MSTORE": 3,
    "JUMP": 8,
    "JUMPI": 10,
    "CALLDATALOAD": 3,
    "EQ": 3,
    "LT": 3,
    "GT": 3,
    "ISZERO": 3,
    "RETURN": 0,
    "REVERT": 0,
    "JUMPDEST": 1,   # Marker opcode — nearly free
    "CALLER": 2,
    "CALLVALUE": 2,
}

# Opcodes: a simplified subset of the real EVM instruction set
# Each opcode is a single byte; we use readable names mapped to byte values
OPCODES = {
    0x00: "STOP",
    0x01: "ADD",
    0x02: "MUL",
    0x03: "SUB",
    0x10: "LT",
    0x11: "GT",
    0x14: "EQ",
    0x15: "ISZERO",
    0x33: "CALLER",
    0x34: "CALLVALUE",
    0x35: "CALLDATALOAD",
    0x50: "POP",
    0x51: "MLOAD",
    0x52: "MSTORE",
    0x54: "SLOAD",
    0x55: "SSTORE",
    0x56: "JUMP",
    0x57: "JUMPI",
    0x5B: "JUMPDEST",
    0x60: "PUSH1",
    0x61: "PUSH2",
    0x7F: "PUSH32",
    0x80: "DUP1",
    0x81: "DUP2",
    0x90: "SWAP1",
    0x91: "SWAP2",
    0xF3: "RETURN",
    0xFD: "REVERT",
}

# 2^256 - 1: maximum value for a 256-bit EVM word
MAX_UINT256 = (1 << 256) - 1

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

def sha256_hex(data: bytes) -> str:
    """SHA-256 hash as hex string. Stand-in for keccak256.

    NOTE: Real Ethereum uses keccak256 everywhere. We use SHA-256 here
    because keccak256 is not in Python's stdlib. The logic is identical —
    only the hash function differs.
    """
    return hashlib.sha256(data).hexdigest()


def compute_contract_address(deployer: str, nonce: int) -> str:
    """Compute a contract's address from the deployer's address and nonce.

    In real Ethereum: address = keccak256(RLP([sender, nonce]))[12:]
    We simplify: address = sha256(deployer + nonce)[:40] (20 bytes = 40 hex chars)
    """
    raw = f"{deployer}{nonce}".encode("utf-8")
    return sha256_hex(raw)[:40]  # Take first 20 bytes (40 hex chars) as address


def function_selector(signature: str) -> bytes:
    """Compute the 4-byte function selector from a function signature.

    Example: "transfer(address,uint256)" → first 4 bytes of hash.
    Real Ethereum uses keccak256; we use SHA-256 as a stand-in.
    """
    return bytes.fromhex(sha256_hex(signature.encode("utf-8"))[:8])


def encode_uint256(value: int) -> bytes:
    """Encode an integer as a 32-byte big-endian uint256."""
    return value.to_bytes(32, "big")


def decode_uint256(data: bytes) -> int:
    """Decode a 32-byte big-endian uint256 to an integer."""
    return int.from_bytes(data, "big")


# --- Execution context (msg.sender, msg.value, calldata) -------------------

class ExecutionContext:
    """Holds the context for a single contract call.

    Mirrors Ethereum's concept of msg.sender, msg.value, and calldata.
    """

    def __init__(self, caller: str, value: int, calldata: bytes):
        self.caller = caller      # msg.sender — who initiated this call
        self.value = value        # msg.value — ETH sent with the call (in wei)
        self.calldata = calldata  # The ABI-encoded function call data


# --- Simplified EVM --------------------------------------------------------

class MiniEVM:
    """A minimal EVM that executes bytecodes with a stack, memory, and storage.

    This is a teaching implementation covering the core execution loop:
    fetch opcode → decode → execute → update state.
    """

    def __init__(self, bytecode: bytes, context: ExecutionContext,
                 storage: dict[int, int]):
        self.code = bytecode            # The contract's bytecodes to execute
        self.pc = 0                      # Program counter (current instruction)
        self.stack: list[int] = []       # The EVM is a stack machine
        self.memory = bytearray(4096)    # Linear memory (byte-addressable)
        self.storage = storage           # Persistent storage (slot → value)
        self.context = context           # Call context (caller, value, calldata)
        self.gas_used = 0                # Total gas consumed
        self.return_data = b""           # Data returned by RETURN opcode
        self.reverted = False            # True if execution REVERTed
        self.halted = False              # True when execution is finished
        self.trace: list[str] = []       # Execution trace for debugging/display

    def _use_gas(self, opname: str):
        """Deduct gas for an operation."""
        cost = GAS_COSTS.get(opname, 3)  # Default cost of 3 for unknown ops
        self.gas_used += cost

    def _push(self, value: int):
        """Push a value onto the stack, enforcing the max depth."""
        if len(self.stack) >= MAX_STACK_DEPTH:
            raise RuntimeError("Stack overflow")
        self.stack.append(value & MAX_UINT256)  # Mask to 256 bits

    def _pop(self) -> int:
        """Pop a value from the stack."""
        if not self.stack:
            raise RuntimeError("Stack underflow")
        return self.stack.pop()

    def execute(self) -> bytes:
        """Run the bytecode until STOP, RETURN, REVERT, or end of code.

        Returns the data from RETURN (if any), or empty bytes.
        """
        while self.pc < len(self.code) and not self.halted:
            opcode = self.code[self.pc]
            self._execute_opcode(opcode)

        return self.return_data

    def _execute_opcode(self, opcode: int):
        """Decode and execute a single opcode."""
        opname = OPCODES.get(opcode, f"UNKNOWN(0x{opcode:02x})")

        # Handle PUSH1 through PUSH32 (opcodes 0x60-0x7F)
        if 0x60 <= opcode <= 0x7F:
            n_bytes = opcode - 0x5F  # PUSH1 = 1 byte, PUSH2 = 2 bytes, etc.
            self._use_gas("PUSH")
            # Read the next n_bytes from the code as the value to push
            value_bytes = self.code[self.pc + 1: self.pc + 1 + n_bytes]
            value = int.from_bytes(value_bytes, "big")
            self._push(value)
            self.trace.append(f"  PUSH{n_bytes} {value}")
            self.pc += 1 + n_bytes  # Skip past the opcode + immediate data
            return

        # Handle DUP1, DUP2 (opcodes 0x80, 0x81)
        if opcode in (0x80, 0x81):
            depth = opcode - 0x7F  # DUP1 = 1, DUP2 = 2
            self._use_gas("DUP")
            if len(self.stack) < depth:
                raise RuntimeError(f"DUP{depth}: not enough stack items")
            value = self.stack[-depth]  # Peek at the nth item from the top
            self._push(value)
            self.trace.append(f"  DUP{depth} → {value}")
            self.pc += 1
            return

        # Handle SWAP1, SWAP2 (opcodes 0x90, 0x91)
        if opcode in (0x90, 0x91):
            depth = opcode - 0x8F  # SWAP1 = 1, SWAP2 = 2
            self._use_gas("SWAP")
            if len(self.stack) < depth + 1:
                raise RuntimeError(f"SWAP{depth}: not enough stack items")
            # Swap top of stack with the (depth+1)th item
            self.stack[-1], self.stack[-(depth + 1)] = (
                self.stack[-(depth + 1)], self.stack[-1]
            )
            self.trace.append(f"  SWAP{depth}")
            self.pc += 1
            return

        self._use_gas(opname)

        if opcode == 0x00:  # STOP
            self.trace.append("  STOP")
            self.halted = True

        elif opcode == 0x01:  # ADD
            a, b = self._pop(), self._pop()
            self._push(a + b)
            self.trace.append(f"  ADD {a} + {b} = {(a + b) & MAX_UINT256}")

        elif opcode == 0x02:  # MUL
            a, b = self._pop(), self._pop()
            self._push(a * b)
            self.trace.append(f"  MUL {a} * {b}")

        elif opcode == 0x03:  # SUB
            a, b = self._pop(), self._pop()
            self._push(a - b)
            self.trace.append(f"  SUB {a} - {b} = {(a - b) & MAX_UINT256}")

        elif opcode == 0x10:  # LT
            a, b = self._pop(), self._pop()
            self._push(1 if a < b else 0)
            self.trace.append(f"  LT {a} < {b} → {1 if a < b else 0}")

        elif opcode == 0x11:  # GT
            a, b = self._pop(), self._pop()
            self._push(1 if a > b else 0)
            self.trace.append(f"  GT {a} > {b}")

        elif opcode == 0x14:  # EQ
            a, b = self._pop(), self._pop()
            result = 1 if a == b else 0
            self._push(result)
            self.trace.append(f"  EQ {a} == {b} → {result}")

        elif opcode == 0x15:  # ISZERO
            a = self._pop()
            self._push(1 if a == 0 else 0)
            self.trace.append(f"  ISZERO {a} → {1 if a == 0 else 0}")

        elif opcode == 0x33:  # CALLER
            # Push msg.sender onto the stack as an integer
            caller_int = int(self.context.caller, 16) & MAX_UINT256
            self._push(caller_int)
            self.trace.append(f"  CALLER → 0x{self.context.caller[:12]}...")

        elif opcode == 0x34:  # CALLVALUE
            self._push(self.context.value)
            self.trace.append(f"  CALLVALUE → {self.context.value}")

        elif opcode == 0x35:  # CALLDATALOAD
            offset = self._pop()
            # Read 32 bytes from calldata starting at offset
            data = self.context.calldata[offset:offset + 32]
            # Pad with zeros if calldata is shorter than offset + 32
            data = data.ljust(32, b"\x00")
            value = int.from_bytes(data, "big")
            self._push(value)
            self.trace.append(f"  CALLDATALOAD offset={offset} → 0x{value:064x}"[:60])

        elif opcode == 0x50:  # POP
            val = self._pop()
            self.trace.append(f"  POP {val}")

        elif opcode == 0x51:  # MLOAD
            offset = self._pop()
            # Read 32 bytes from memory at the given offset
            value = int.from_bytes(self.memory[offset:offset + 32], "big")
            self._push(value)
            self.trace.append(f"  MLOAD [{offset}] → {value}")

        elif opcode == 0x52:  # MSTORE
            offset = self._pop()
            value = self._pop()
            # Write 32 bytes to memory at the given offset
            data = (value & MAX_UINT256).to_bytes(32, "big")
            self.memory[offset:offset + 32] = data
            self.trace.append(f"  MSTORE [{offset}] ← {value}")

        elif opcode == 0x54:  # SLOAD
            slot = self._pop()
            value = self.storage.get(slot, 0)  # Default to 0 if never written
            self._push(value)
            self.trace.append(f"  SLOAD slot[{slot}] → {value}")

        elif opcode == 0x55:  # SSTORE
            slot = self._pop()
            value = self._pop()
            self.storage[slot] = value  # Persist in contract storage
            self.trace.append(f"  SSTORE slot[{slot}] ← {value}")

        elif opcode == 0x56:  # JUMP
            dest = self._pop()
            if dest < len(self.code) and self.code[dest] == 0x5B:  # Must land on JUMPDEST
                self.pc = dest
                self.trace.append(f"  JUMP → {dest}")
                return  # Don't increment PC
            else:
                raise RuntimeError(f"Invalid JUMP destination: {dest}")

        elif opcode == 0x57:  # JUMPI
            dest = self._pop()
            cond = self._pop()
            if cond != 0:
                if dest < len(self.code) and self.code[dest] == 0x5B:
                    self.pc = dest
                    self.trace.append(f"  JUMPI → {dest} (condition={cond})")
                    return
                else:
                    raise RuntimeError(f"Invalid JUMPI destination: {dest}")
            self.trace.append(f"  JUMPI skipped (condition=0)")

        elif opcode == 0x5B:  # JUMPDEST
            self.trace.append("  JUMPDEST")
            pass  # Just a valid jump target marker

        elif opcode == 0xF3:  # RETURN
            offset = self._pop()
            length = self._pop()
            self.return_data = bytes(self.memory[offset:offset + length])
            self.trace.append(f"  RETURN offset={offset} len={length}")
            self.halted = True

        elif opcode == 0xFD:  # REVERT
            offset = self._pop()
            length = self._pop()
            self.return_data = bytes(self.memory[offset:offset + length])
            self.reverted = True
            self.halted = True
            self.trace.append("  REVERT")

        else:
            self.trace.append(f"  UNKNOWN opcode 0x{opcode:02x}")
            self.halted = True

        self.pc += 1  # Advance to the next instruction


# --- Smart Contract State Machine ------------------------------------------

class ContractAccount:
    """Represents a deployed smart contract on the blockchain.

    Stores the contract's bytecodes and its persistent storage.
    """

    def __init__(self, address: str, bytecode: bytes, deployer: str):
        self.address = address        # The contract's address
        self.bytecode = bytecode      # The deployed bytecodes
        self.storage: dict[int, int] = {}  # Persistent storage (slot → value)
        self.deployer = deployer      # Who deployed this contract
        self.balance = 0              # ETH balance in wei


class WorldState:
    """The blockchain's world state: all accounts and their storage.

    In real Ethereum, this is stored in the state MPT (see script 05).
    Here we use a simple dict for clarity.
    """

    def __init__(self):
        self.accounts: dict[str, dict] = {}     # address → {balance, nonce}
        self.contracts: dict[str, ContractAccount] = {}  # address → ContractAccount
        self.deploy_nonces: dict[str, int] = {}  # deployer address → next nonce

    def create_eoa(self, address: str, balance: int = 1000000):
        """Create an Externally Owned Account (a regular user account)."""
        self.accounts[address] = {"balance": balance, "nonce": 0}
        self.deploy_nonces[address] = 0

    def deploy_contract(self, deployer: str, bytecode: bytes,
                        verbose: bool = False) -> str:
        """Deploy a contract: store bytecodes at a deterministic address.

        Returns the new contract's address.
        """
        if deployer not in self.accounts:
            raise ValueError(f"Deployer {deployer[:12]}... not found")

        # Get and increment the deployer's nonce
        nonce = self.deploy_nonces[deployer]
        self.deploy_nonces[deployer] = nonce + 1

        # Compute the contract address deterministically
        contract_addr = compute_contract_address(deployer, nonce)

        # Create the contract account
        contract = ContractAccount(contract_addr, bytecode, deployer)
        self.contracts[contract_addr] = contract

        if verbose:
            print(f"  Contract deployed at: 0x{contract_addr[:16]}...")
            print(f"  Bytecode size: {len(bytecode)} bytes")
            print(f"  Deployer: 0x{deployer[:12]}...")
            print(f"  Nonce: {nonce}")

        return contract_addr

    def call_contract(self, caller: str, contract_addr: str,
                      calldata: bytes, value: int = 0,
                      verbose: bool = False) -> bytes:
        """Call a deployed contract with the given calldata.

        Loads the contract's bytecodes, creates an execution context,
        runs the EVM, and returns the result.
        """
        if contract_addr not in self.contracts:
            raise ValueError(f"No contract at {contract_addr[:12]}...")

        contract = self.contracts[contract_addr]
        context = ExecutionContext(caller=caller, value=value, calldata=calldata)

        # Create a fresh EVM instance with the contract's code and storage
        evm = MiniEVM(contract.bytecode, context, contract.storage)
        result = evm.execute()

        if verbose:
            print(f"\n  --- EVM Execution Trace ---")
            for line in evm.trace:
                print(f"  {line}")
            print(f"  Gas used: {evm.gas_used}")
            if evm.reverted:
                print(f"  ✗ REVERTED")
            else:
                print(f"  ✓ Success")

        return result


# --- Contract Bytecode Builder (helper for demo) --------------------------

class BytecodeBuilder:
    """Helper to construct EVM bytecodes from high-level operations.

    Instead of writing raw hex, we build bytecodes with named methods.
    This is similar to what a Solidity compiler would output.
    """

    def __init__(self):
        self.code = bytearray()

    def push1(self, value: int) -> "BytecodeBuilder":
        """PUSH1: push a 1-byte value onto the stack."""
        self.code.append(0x60)
        self.code.append(value & 0xFF)
        return self

    def push2(self, value: int) -> "BytecodeBuilder":
        """PUSH2: push a 2-byte value onto the stack."""
        self.code.append(0x61)
        self.code.extend(value.to_bytes(2, "big"))
        return self

    def push4(self, value: int) -> "BytecodeBuilder":
        """PUSH4: push a 4-byte value (used for function selectors)."""
        # We'll encode as PUSH1 repeated if needed, or use a different approach
        # Actually use PUSH32 approach but with 4 bytes via custom logic
        # For simplicity, push the 4-byte value using PUSH1 shifts
        self.code.append(0x60)
        self.code.append((value >> 24) & 0xFF)
        # Shift left by 8
        self.push1(8)
        self.code.append(0x02)  # MUL (stand-in for SHL which we didn't implement)
        # ... this gets complex. Let's use a different approach.
        # We'll just push the full 4-byte value as a 32-byte value via PUSH32
        return self

    def push32(self, value: int) -> "BytecodeBuilder":
        """PUSH32: push a 32-byte value onto the stack."""
        self.code.append(0x7F)
        self.code.extend(value.to_bytes(32, "big"))
        return self

    def op(self, opcode: int) -> "BytecodeBuilder":
        """Append a raw opcode byte."""
        self.code.append(opcode)
        return self

    def stop(self) -> "BytecodeBuilder":
        return self.op(0x00)

    def add(self) -> "BytecodeBuilder":
        return self.op(0x01)

    def sub(self) -> "BytecodeBuilder":
        return self.op(0x03)

    def eq(self) -> "BytecodeBuilder":
        return self.op(0x14)

    def iszero(self) -> "BytecodeBuilder":
        return self.op(0x15)

    def pop(self) -> "BytecodeBuilder":
        return self.op(0x50)

    def sload(self) -> "BytecodeBuilder":
        return self.op(0x54)

    def sstore(self) -> "BytecodeBuilder":
        return self.op(0x55)

    def mload(self) -> "BytecodeBuilder":
        return self.op(0x51)

    def mstore(self) -> "BytecodeBuilder":
        return self.op(0x52)

    def jump(self) -> "BytecodeBuilder":
        return self.op(0x56)

    def jumpi(self) -> "BytecodeBuilder":
        return self.op(0x57)

    def jumpdest(self) -> "BytecodeBuilder":
        return self.op(0x5B)

    def calldataload(self) -> "BytecodeBuilder":
        return self.op(0x35)

    def dup1(self) -> "BytecodeBuilder":
        return self.op(0x80)

    def dup2(self) -> "BytecodeBuilder":
        return self.op(0x81)

    def swap1(self) -> "BytecodeBuilder":
        return self.op(0x90)

    def ret(self) -> "BytecodeBuilder":
        """RETURN opcode (named 'ret' to avoid Python keyword)."""
        return self.op(0xF3)

    def build(self) -> bytes:
        """Return the assembled bytecodes."""
        return bytes(self.code)

    def current_offset(self) -> int:
        """Return the current bytecodes offset (for jump targets)."""
        return len(self.code)


def build_counter_contract() -> bytes:
    """Build bytecodes for a simple Counter contract.

    Equivalent Solidity:
        contract Counter {
            uint256 count;  // storage slot 0
            function increment() public { count += 1; }
            function get() public view returns (uint256) { return count; }
        }

    Bytecodes layout:
        1. Load first 4 bytes of calldata (function selector)
        2. Compare against increment() selector → jump to increment code
        3. Compare against get() selector → jump to get code
        4. STOP (fallback)
        5. increment code: SLOAD slot 0, add 1, SSTORE slot 0, STOP
        6. get code: SLOAD slot 0, MSTORE, RETURN
    """
    b = BytecodeBuilder()

    # Compute function selectors (first 4 bytes of hash of signature)
    inc_selector = int.from_bytes(function_selector("increment()"), "big")
    get_selector = int.from_bytes(function_selector("get()"), "big")

    # --- Function dispatcher ---
    # Load calldata[0:32] to get the function selector
    # We only care about the first 4 bytes, shifted right by 224 bits
    # But our simple EVM doesn't have SHR, so we'll compare the full 32-byte value
    # where the selector is left-aligned (occupies the high 4 bytes)
    inc_selector_full = inc_selector << 224  # Left-align to match calldata format
    get_selector_full = get_selector << 224

    # Push 0 for CALLDATALOAD offset, load calldata
    b.push1(0)          # offset 0
    b.calldataload()    # Load first 32 bytes of calldata → stack

    # Check for increment() selector
    b.dup1()                          # Duplicate the selector for comparison
    b.push32(inc_selector_full)       # Push the increment selector
    b.eq()                            # Compare
    # We'll fill in the jump target later
    inc_jump_offset = b.current_offset()
    b.push1(0)                        # Placeholder for jump target
    b.jumpi()                         # Jump if selectors match

    # Check for get() selector
    b.push32(get_selector_full)
    b.eq()
    get_jump_offset = b.current_offset()
    b.push1(0)                        # Placeholder for jump target
    b.jumpi()

    # Fallback: no matching function — STOP
    b.stop()

    # --- increment() implementation ---
    inc_target = b.current_offset()
    b.jumpdest()
    b.push1(0)       # Storage slot 0 (where 'count' lives)
    b.sload()        # Load current count
    b.push1(1)       # Push 1
    b.add()          # count + 1
    b.push1(0)       # Storage slot 0
    b.sstore()       # Store new count
    b.stop()         # End execution

    # --- get() implementation ---
    get_target = b.current_offset()
    b.jumpdest()
    b.push1(0)       # Storage slot 0
    b.sload()        # Load count
    b.push1(0)       # Memory offset 0
    b.mstore()       # Store in memory[0:32]
    b.push1(32)      # Return 32 bytes
    b.push1(0)       # From memory offset 0
    b.ret()          # RETURN

    # --- Patch jump targets ---
    # Now that we know the actual offsets, write them into the placeholders
    code = bytearray(b.build())
    code[inc_jump_offset + 1] = inc_target   # Fix increment jump target
    code[get_jump_offset + 1] = get_target   # Fix get jump target

    return bytes(code)


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of smart contract deployment and execution."""

    print("=" * 70)
    print("  SMART CONTRACTS — Deploy, Call, and Storage on the EVM")
    print("=" * 70)

    # --- Part 1: Setup world state -----------------------------------------
    print("\n--- Part 1: World State Setup ---\n")

    world = WorldState()
    alice_addr = "a]" + "0" * 38  # Simplified address for readability
    alice_addr = sha256_hex(b"alice")[:40]  # Deterministic address for Alice

    world.create_eoa(alice_addr, balance=100_000_000)
    print(f"  Created EOA for Alice: 0x{alice_addr[:16]}...")
    print(f"  Balance: 100,000,000 wei")

    # --- Part 2: Contract deployment ---------------------------------------
    print("\n--- Part 2: Contract Deployment ---\n")

    print("  Building Counter contract bytecodes...")
    print("  Equivalent Solidity:")
    print("    contract Counter {")
    print("        uint256 count;")
    print("        function increment() public { count += 1; }")
    print("        function get() public view returns (uint256) { return count; }")
    print("    }")
    print()

    counter_bytecode = build_counter_contract()
    print(f"  Compiled bytecodes: {len(counter_bytecode)} bytes")
    print(f"  Hex: {counter_bytecode[:32].hex()}...")

    contract_addr = world.deploy_contract(alice_addr, counter_bytecode, verbose=True)

    # --- Part 3: Function selectors ----------------------------------------
    print("\n--- Part 3: Function Selectors ---\n")

    inc_sel = function_selector("increment()")
    get_sel = function_selector("get()")

    print("  Function selectors (first 4 bytes of hash of signature):")
    print(f"  ┌────────────────────────────────────────────┐")
    print(f"  │ increment()  →  0x{inc_sel.hex():<30s}│")
    print(f"  │ get()        →  0x{get_sel.hex():<30s}│")
    print(f"  └────────────────────────────────────────────┘")
    print()
    print("  NOTE: Real Ethereum uses keccak256 for selectors.")
    print("  We use SHA-256 as a stand-in (same concept, different hash).")

    # --- Part 4: Call increment() three times ------------------------------
    print("\n--- Part 4: Calling increment() 3 Times ---\n")

    for i in range(1, 4):
        # Build calldata: 4-byte selector, left-padded into 32 bytes
        calldata = inc_sel + b"\x00" * 28  # Pad to 32 bytes

        print(f"  Call #{i}: increment()")
        print(f"    Calldata: 0x{calldata[:4].hex()} (+ 28 zero bytes)")

        result = world.call_contract(
            caller=alice_addr,
            contract_addr=contract_addr,
            calldata=calldata,
            verbose=True,
        )

        # Show storage state after the call
        contract = world.contracts[contract_addr]
        count = contract.storage.get(0, 0)
        print(f"    Storage[0] (count) = {count}")
        print()

    # --- Part 5: Call get() to read the counter ----------------------------
    print("--- Part 5: Calling get() to Read Counter ---\n")

    calldata = get_sel + b"\x00" * 28
    print(f"  Call: get()")
    print(f"  Calldata: 0x{calldata[:4].hex()}")

    result = world.call_contract(
        caller=alice_addr,
        contract_addr=contract_addr,
        calldata=calldata,
        verbose=True,
    )

    # Decode the return value (32-byte uint256)
    if result:
        returned_value = int.from_bytes(result, "big")
        print(f"\n  Return value: {returned_value}")
    else:
        returned_value = 0
        print(f"\n  Return value: (empty)")

    # --- Part 6: Summary ---------------------------------------------------
    print("\n--- Part 6: Final Contract State ---\n")

    contract = world.contracts[contract_addr]
    print(f"  ┌─────────────────────────────────────────────┐")
    print(f"  │ Contract: 0x{contract_addr[:16]}...{' ' * 11}│")
    print(f"  │ Bytecodes size: {len(contract.bytecode):>4} bytes{' ' * 16}│")
    print(f"  │ Storage slots used: {len(contract.storage)}{' ' * 23}│")
    print(f"  │ Storage[0] (count): {contract.storage.get(0, 0)}{' ' * 23}│")
    print(f"  │ Deployer: 0x{contract.deployer[:16]}...{' ' * 7}│")
    print(f"  └─────────────────────────────────────────────┘")

    print()
    print(f"  After calling increment() 3 times, get() returns: {returned_value}")
    print(f"  The counter value persists in storage slot 0 across calls.")

    print("\n" + "=" * 70)
    print("  KEY TAKEAWAY: Smart contracts are bytecodes stored on-chain at a")
    print("  deterministic address. The EVM loads the code, runs it in a sandbox")
    print("  with msg.sender/msg.value context, and persists state changes in")
    print("  the contract's storage. Function dispatch uses 4-byte selectors.")
    print("=" * 70)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
