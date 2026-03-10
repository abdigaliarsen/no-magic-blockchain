"""
TITLE: Gas Metering and EIP-1559 Fee Model
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    A gas-metered EVM execution engine and a simulation of Ethereum's EIP-1559
    dynamic fee mechanism. Each opcode costs gas, execution reverts on out-of-gas,
    and the base fee adjusts per block based on gas utilization.

KEY CONCEPTS:
    - Gas costs per opcode (ADD=3, MUL=5, SSTORE=20000, etc.)
    - Gas limit enforcement and out-of-gas revert
    - EIP-1559: base fee, priority fee (tip), elastic block size
    - Base fee adjustment: increases when blocks are >50% full, decreases when <50%

PREREQUISITE SCRIPTS:
    - ethereum/02_evm_bytecode.py (the EVM interpreter this builds on)

REAL-WORLD RELEVANCE:
    Gas is how Ethereum prevents infinite loops and allocates scarce block space.
    EIP-1559 (London upgrade, Aug 2021) replaced the first-price auction with a
    more predictable fee mechanism. The base fee is burned, and tips go to validators.
"""

import hashlib  # Only for generating example transaction hashes

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# --- Gas costs per opcode (simplified from the Yellow Paper, Appendix G) ------
# Real Ethereum has more nuanced costs (warm/cold access, etc.), but these
# capture the essential idea: simple ops are cheap, storage is expensive.

GAS_COSTS = {
    0x00: 0,       # STOP — free (execution is ending)
    0x01: 3,       # ADD
    0x02: 5,       # MUL
    0x03: 3,       # SUB
    0x04: 5,       # DIV
    0x06: 5,       # MOD
    0x10: 3,       # LT
    0x11: 3,       # GT
    0x14: 3,       # EQ
    0x15: 3,       # ISZERO
    0x16: 3,       # AND
    0x17: 3,       # OR
    0x19: 3,       # NOT
    0x50: 2,       # POP
    0x51: 3,       # MLOAD (+ memory expansion cost, simplified)
    0x52: 3,       # MSTORE (+ memory expansion cost, simplified)
    0x54: 100,     # SLOAD — reading storage is expensive (disk I/O)
    0x55: 20000,   # SSTORE — writing storage is very expensive (permanent state)
    0x56: 8,       # JUMP
    0x57: 10,      # JUMPI
    0x5B: 1,       # JUMPDEST
    0x80: 3,       # DUP1
    0x90: 3,       # SWAP1
    0xF3: 0,       # RETURN — free (execution is ending)
}
# PUSH1..PUSH32 all cost 3 gas
for i in range(32):
    GAS_COSTS[0x60 + i] = 3

# Default gas cost for any unlisted opcode
DEFAULT_GAS = 3

# --- EIP-1559 constants -------------------------------------------------------

# Target gas per block (the protocol aims for blocks to be 50% full)
TARGET_GAS_PER_BLOCK = 15_000_000

# Maximum gas per block (elastic ceiling = 2x target)
MAX_GAS_PER_BLOCK = 30_000_000

# Initial base fee in Gwei
INITIAL_BASE_FEE_GWEI = 20

# Gwei to Wei conversion
GWEI = 10 ** 9

# Base fee adjustment denominator — controls how fast base fee changes
# Real value is 8, meaning max 12.5% change per block
BASE_FEE_CHANGE_DENOMINATOR = 8

# Gas cost for a simple ETH transfer (used in block simulation)
SIMPLE_TRANSFER_GAS = 21_000

# --- Opcode names (for display) -----------------------------------------------

OPCODE_NAMES = {
    0x00: "STOP",   0x01: "ADD",    0x02: "MUL",    0x03: "SUB",
    0x04: "DIV",    0x06: "MOD",    0x10: "LT",     0x11: "GT",
    0x14: "EQ",     0x15: "ISZERO", 0x16: "AND",    0x17: "OR",
    0x19: "NOT",    0x50: "POP",    0x51: "MLOAD",  0x52: "MSTORE",
    0x54: "SLOAD",  0x55: "SSTORE", 0x56: "JUMP",   0x57: "JUMPI",
    0x5B: "JUMPDEST", 0x80: "DUP1", 0x90: "SWAP1", 0xF3: "RETURN",
}
for i in range(32):
    OPCODE_NAMES[0x60 + i] = f"PUSH{i + 1}"

# 256-bit mask for uint256
UINT256_MAX = (1 << 256) - 1
MAX_STACK_DEPTH = 1024

# Opcodes used in assemble()
STOP = 0x00; ADD = 0x01; MUL = 0x02; SUB = 0x03; DIV = 0x04
MOD = 0x06; POP = 0x50; MLOAD = 0x51; MSTORE = 0x52
SLOAD = 0x54; SSTORE = 0x55; PUSH1 = 0x60; DUP1 = 0x80
SWAP1 = 0x90; RETURN = 0xF3; JUMP = 0x56; JUMPI = 0x57
JUMPDEST = 0x5B; EQ = 0x14; ISZERO = 0x15; LT = 0x10
GT = 0x11; AND = 0x16; OR = 0x17; NOT = 0x19


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Gas-metered EVM ----------------------------------------------------------

class OutOfGasError(Exception):
    """Raised when execution exceeds the gas limit."""
    pass


class EVMError(Exception):
    """General EVM execution error."""
    pass


class GasMeteredEVM:
    """EVM with per-opcode gas tracking.

    Extends the basic EVM from script 02 with gas accounting. Each opcode
    deducts its gas cost before execution. If gas runs out, execution reverts.
    """

    def __init__(self, code: bytes, gas_limit: int):
        self.code = code
        self.pc = 0
        self.stack: list[int] = []
        self.memory = bytearray()
        self.storage: dict[int, int] = {}
        self.running = True
        self.gas_limit = gas_limit       # Maximum gas available
        self.gas_used = 0                # Gas consumed so far
        self.gas_log: list[tuple[str, int, int]] = []  # (opcode_name, cost, cumulative)

    @property
    def gas_remaining(self) -> int:
        """Gas still available for execution."""
        return self.gas_limit - self.gas_used

    def _consume_gas(self, opcode: int, name: str):
        """Deduct gas for the given opcode. Raises OutOfGasError if insufficient."""
        cost = GAS_COSTS.get(opcode, DEFAULT_GAS)
        if self.gas_used + cost > self.gas_limit:
            raise OutOfGasError(
                f"Out of gas at {name} (pc={self.pc}): "
                f"need {cost}, have {self.gas_remaining}"
            )
        self.gas_used += cost
        self.gas_log.append((name, cost, self.gas_used))

    def _push(self, value: int):
        if len(self.stack) >= MAX_STACK_DEPTH:
            raise EVMError("Stack overflow")
        self.stack.append(value & UINT256_MAX)

    def _pop(self) -> int:
        if not self.stack:
            raise EVMError("Stack underflow")
        return self.stack.pop()

    def _memory_extend(self, offset: int, size: int):
        needed = offset + size
        if needed > len(self.memory):
            self.memory.extend(b"\x00" * (needed - len(self.memory)))

    def run(self) -> tuple[bool, int]:
        """Execute bytecode with gas tracking.

        Returns (success: bool, gas_used: int).
        """
        try:
            while self.running and self.pc < len(self.code):
                opcode = self.code[self.pc]
                name = OPCODE_NAMES.get(opcode, f"0x{opcode:02X}")

                # --- Charge gas BEFORE execution (pre-pay model) ----
                self._consume_gas(opcode, name)

                self.pc += 1

                # --- Execute (same logic as script 02, condensed) ---
                if opcode == 0x00:    # STOP
                    self.running = False
                elif opcode == 0x01:  # ADD
                    self._push(self._pop() + self._pop())
                elif opcode == 0x02:  # MUL
                    self._push(self._pop() * self._pop())
                elif opcode == 0x03:  # SUB
                    self._push(self._pop() - self._pop())
                elif opcode == 0x04:  # DIV
                    a, b = self._pop(), self._pop()
                    self._push(a // b if b else 0)
                elif opcode == 0x06:  # MOD
                    a, b = self._pop(), self._pop()
                    self._push(a % b if b else 0)
                elif opcode == 0x10:  # LT
                    self._push(1 if self._pop() < self._pop() else 0)
                elif opcode == 0x11:  # GT
                    self._push(1 if self._pop() > self._pop() else 0)
                elif opcode == 0x14:  # EQ
                    self._push(1 if self._pop() == self._pop() else 0)
                elif opcode == 0x15:  # ISZERO
                    self._push(1 if self._pop() == 0 else 0)
                elif opcode == 0x16:  # AND
                    self._push(self._pop() & self._pop())
                elif opcode == 0x17:  # OR
                    self._push(self._pop() | self._pop())
                elif opcode == 0x19:  # NOT
                    self._push(UINT256_MAX ^ self._pop())
                elif opcode == 0x50:  # POP
                    self._pop()
                elif opcode == 0x51:  # MLOAD
                    off = self._pop()
                    self._memory_extend(off, 32)
                    self._push(int.from_bytes(bytes(self.memory[off:off+32]), "big"))
                elif opcode == 0x52:  # MSTORE
                    off, val = self._pop(), self._pop()
                    self._memory_extend(off, 32)
                    self.memory[off:off+32] = val.to_bytes(32, "big")
                elif opcode == 0x54:  # SLOAD
                    self._push(self.storage.get(self._pop(), 0))
                elif opcode == 0x55:  # SSTORE
                    key, val = self._pop(), self._pop()
                    self.storage[key] = val
                elif opcode == 0x56:  # JUMP
                    self.pc = self._pop()
                elif opcode == 0x57:  # JUMPI
                    dest, cond = self._pop(), self._pop()
                    if cond: self.pc = dest
                elif opcode == 0x5B:  # JUMPDEST
                    pass
                elif 0x60 <= opcode <= 0x7F:  # PUSH1..PUSH32
                    n = opcode - 0x60 + 1
                    raw = self.code[self.pc:self.pc + n]
                    self._push(int.from_bytes(raw, "big"))
                    self.pc += n
                elif opcode == 0x80:  # DUP1
                    self._push(self.stack[-1])
                elif opcode == 0x90:  # SWAP1
                    self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]
                elif opcode == 0xF3:  # RETURN
                    self.running = False
                else:
                    raise EVMError(f"Unknown opcode 0x{opcode:02X}")

            return True, self.gas_used

        except OutOfGasError:
            return False, self.gas_used


# --- EIP-1559 Fee Model -------------------------------------------------------

class Block:
    """A simplified Ethereum block with EIP-1559 fee mechanics."""

    def __init__(self, number: int, base_fee: int, gas_used: int, gas_limit: int):
        self.number = number
        self.base_fee = base_fee        # Base fee in Wei (burned)
        self.gas_used = gas_used        # Total gas consumed by all txs
        self.gas_limit = gas_limit      # Max gas allowed in this block
        self.tx_count = 0               # Number of transactions included

    @property
    def utilization(self) -> float:
        """Block fullness as a fraction of the target (not limit).

        >1.0 means the block is more than 50% full (above target).
        <1.0 means it's below target.
        """
        return self.gas_used / TARGET_GAS_PER_BLOCK if TARGET_GAS_PER_BLOCK > 0 else 0


def calculate_next_base_fee(parent_gas_used: int, parent_base_fee: int) -> int:
    """Compute the base fee for the next block using EIP-1559 rules.

    If the parent block used MORE gas than the target, base fee increases.
    If it used LESS, base fee decreases.
    The maximum change per block is 1/8 (12.5%) of the current base fee.
    """
    if parent_gas_used == TARGET_GAS_PER_BLOCK:
        # Perfectly at target — no change
        return parent_base_fee

    if parent_gas_used > TARGET_GAS_PER_BLOCK:
        # Above target — increase base fee
        gas_delta = parent_gas_used - TARGET_GAS_PER_BLOCK
        # fee_delta = parent_base_fee * gas_delta / TARGET / denominator
        fee_delta = max(
            1,  # Ensure at least 1 Wei increase
            parent_base_fee * gas_delta // TARGET_GAS_PER_BLOCK // BASE_FEE_CHANGE_DENOMINATOR
        )
        return parent_base_fee + fee_delta
    else:
        # Below target — decrease base fee
        gas_delta = TARGET_GAS_PER_BLOCK - parent_gas_used
        fee_delta = (
            parent_base_fee * gas_delta // TARGET_GAS_PER_BLOCK // BASE_FEE_CHANGE_DENOMINATOR
        )
        # Base fee can never go below 0
        return max(0, parent_base_fee - fee_delta)


def simulate_blocks(
    num_blocks: int,
    gas_usage_pattern: list[float],
    initial_base_fee: int,
) -> list[Block]:
    """Simulate a sequence of blocks with varying gas usage.

    gas_usage_pattern: list of utilization fractions (1.0 = target, 2.0 = max).
    Pattern repeats cyclically if shorter than num_blocks.
    """
    blocks = []
    current_base_fee = initial_base_fee

    for i in range(num_blocks):
        # Determine gas usage for this block
        utilization = gas_usage_pattern[i % len(gas_usage_pattern)]
        gas_used = int(TARGET_GAS_PER_BLOCK * utilization)
        gas_used = min(gas_used, MAX_GAS_PER_BLOCK)  # Cap at block limit

        # Estimate tx count (rough: each tx uses ~21000 gas for a transfer)
        tx_count = gas_used // SIMPLE_TRANSFER_GAS if gas_used > 0 else 0

        block = Block(
            number=i + 1,
            base_fee=current_base_fee,
            gas_used=gas_used,
            gas_limit=MAX_GAS_PER_BLOCK,
        )
        block.tx_count = tx_count
        blocks.append(block)

        # Calculate next block's base fee from this block's usage
        current_base_fee = calculate_next_base_fee(gas_used, current_base_fee)

    return blocks


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run demonstrations of gas metering and EIP-1559 dynamics."""

    print("=" * 64)
    print("  GAS METERING AND EIP-1559 FEE MODEL")
    print("  How Ethereum prices computation and block space")
    print("=" * 64)

    # --- Part 1: Gas cost per opcode ------------------------------------------

    print("\n" + "=" * 64)
    print("  Part 1: Executing a contract with gas tracking")
    print("=" * 64)
    print("\n  Program: compute (5 + 10) * 3, store result in storage[0]")
    print("  Then load it back from storage")

    code = bytes([
        PUSH1, 5,       # 3 gas — push 5
        PUSH1, 10,      # 3 gas — push 10
        ADD,            # 3 gas — 5 + 10 = 15
        PUSH1, 3,       # 3 gas — push 3
        MUL,            # 5 gas — 15 * 3 = 45
        PUSH1, 0,       # 3 gas — storage key 0
        SSTORE,         # 20000 gas — store 45 at key 0 (EXPENSIVE!)
        PUSH1, 0,       # 3 gas — storage key 0
        SLOAD,          # 100 gas — load from key 0
        STOP,           # 0 gas
    ])

    evm = GasMeteredEVM(code, gas_limit=100_000)
    success, gas_used = evm.run()

    # Print gas log as a table
    print(f"\n  {'Step':<6} {'Opcode':<12} {'Cost':<8} {'Cumulative':<12}")
    print(f"  {'─' * 6} {'─' * 12} {'─' * 8} {'─' * 12}")
    for i, (name, cost, cumulative) in enumerate(evm.gas_log):
        bar = "#" * (cost // 100 + 1) if cost > 0 else ""  # Visual bar scaled
        print(f"  {i+1:<6} {name:<12} {cost:<8} {cumulative:<12} {bar}")

    print(f"\n  Total gas used: {gas_used:,}")
    print(f"  Gas limit:      {evm.gas_limit:,}")
    print(f"  Gas remaining:  {evm.gas_remaining:,}")
    print(f"  Result:         storage[0] = {evm.storage.get(0, '???')}")
    print(f"  Status:         {'SUCCESS' if success else 'REVERTED'}")

    # --- Part 2: Out-of-gas demonstration -------------------------------------

    print("\n" + "=" * 64)
    print("  Part 2: Out-of-gas revert")
    print("=" * 64)
    print("  Same program but with only 100 gas (needs ~20,121)")

    evm_oog = GasMeteredEVM(code, gas_limit=100)
    success_oog, gas_used_oog = evm_oog.run()

    print(f"\n  Gas limit:  100")
    print(f"  Gas used:   {gas_used_oog}")
    print(f"  Status:     {'SUCCESS' if success_oog else 'OUT OF GAS (reverted)'}")

    # Show which opcode caused the failure
    if not success_oog and evm_oog.gas_log:
        last = evm_oog.gas_log[-1]
        print(f"  Failed at:  {last[0]} (needed more gas at cumulative={last[2]})")

    print("\n  In real Ethereum, out-of-gas reverts ALL state changes")
    print("  but the gas fee is still charged (you pay for failed work)")

    # --- Part 3: Gas costs comparison -----------------------------------------

    print("\n" + "=" * 64)
    print("  Part 3: Why storage is so expensive")
    print("=" * 64)
    print("  Comparing gas costs of different operations:")

    comparisons = [
        ("ADD (arithmetic)",     0x01, 3),
        ("MUL (arithmetic)",     0x02, 5),
        ("MLOAD (memory read)",  0x51, 3),
        ("MSTORE (memory write)",0x52, 3),
        ("SLOAD (storage read)", 0x54, 100),
        ("SSTORE (storage write)",0x55, 20000),
    ]

    print(f"\n  {'Operation':<24} {'Gas Cost':<10} {'Relative':<10} {'Visual'}")
    print(f"  {'─' * 24} {'─' * 10} {'─' * 10} {'─' * 30}")
    for name, _, cost in comparisons:
        # Scale bar: 1 block per 500 gas, minimum 1
        blocks = max(1, cost // 500)
        bar = "█" * blocks
        relative = f"{cost / 3:.0f}x" if cost >= 3 else "1x"
        print(f"  {name:<24} {cost:<10} {relative:<10} {bar}")

    print("\n  Storage is expensive because it must be stored FOREVER by all nodes.")
    print("  Memory is cheap because it's discarded after execution.")

    # --- Part 4: EIP-1559 base fee simulation ---------------------------------

    print("\n" + "=" * 64)
    print("  Part 4: EIP-1559 base fee adjustment")
    print("=" * 64)
    print("  Simulating 15 blocks with varying demand")
    print(f"  Target gas: {TARGET_GAS_PER_BLOCK:,} | Max gas: {MAX_GAS_PER_BLOCK:,}")
    print(f"  Initial base fee: {INITIAL_BASE_FEE_GWEI} Gwei")

    # Simulate a demand surge followed by a cooldown
    # Pattern: moderate → high → very high → moderate → low
    gas_pattern = [
        1.0,   # Block 1: exactly at target
        1.0,   # Block 2: at target
        1.5,   # Block 3: 50% above target (demand rising)
        1.8,   # Block 4: 80% above target
        2.0,   # Block 5: max (100% above target — full block)
        2.0,   # Block 6: still maxed out
        2.0,   # Block 7: still maxed out
        1.5,   # Block 8: demand dropping
        1.0,   # Block 9: back to target
        0.5,   # Block 10: below target (demand cooling)
        0.3,   # Block 11: very low demand
        0.2,   # Block 12: nearly empty
        0.5,   # Block 13: recovering
        0.8,   # Block 14: approaching target
        1.0,   # Block 15: back to target
    ]

    blocks = simulate_blocks(15, gas_pattern, INITIAL_BASE_FEE_GWEI * GWEI)

    print(f"\n  {'Block':<7} {'Gas Used':<14} {'Util %':<9} "
          f"{'Base Fee':<14} {'Change':<10} {'Visual'}")
    print(f"  {'─' * 7} {'─' * 14} {'─' * 9} {'─' * 14} {'─' * 10} {'─' * 20}")

    prev_fee = blocks[0].base_fee
    for b in blocks:
        util_pct = b.utilization * 100
        fee_gwei = b.base_fee / GWEI
        change = b.base_fee - prev_fee
        change_str = f"+{change/GWEI:.2f}" if change >= 0 else f"{change/GWEI:.2f}"

        # Visual bar: scale utilization percentage
        bar_len = int(util_pct / 5)  # 20 chars = 100%
        bar = "█" * bar_len + "░" * (20 - bar_len)

        print(f"  {b.number:<7} {b.gas_used:>12,}  {util_pct:>6.1f}%  "
              f"{fee_gwei:>10.2f} Gw  {change_str:>8} Gw  {bar}")
        prev_fee = b.base_fee

    # --- Part 5: Transaction cost calculation ---------------------------------

    print("\n" + "=" * 64)
    print("  Part 5: What a user actually pays")
    print("=" * 64)

    example_base_fee = blocks[6].base_fee  # Peak base fee from simulation
    priority_fee = 2 * GWEI               # 2 Gwei tip to the validator
    gas_used_example = 21_000              # Simple transfer

    total_fee = gas_used_example * (example_base_fee + priority_fee)
    burned = gas_used_example * example_base_fee   # Burned (EIP-1559)
    to_validator = gas_used_example * priority_fee  # Goes to block proposer

    print(f"\n  Scenario: simple ETH transfer during peak demand")
    print(f"  ┌{'─' * 44}┐")
    print(f"  │ {'Gas used:':<20} {gas_used_example:>20,} │")
    print(f"  │ {'Base fee:':<20} {example_base_fee/GWEI:>17.2f} Gw │")
    print(f"  │ {'Priority fee:':<20} {priority_fee/GWEI:>17.2f} Gw │")
    print(f"  │{'─' * 44}│")
    print(f"  │ {'Total fee:':<20} {total_fee/10**18:>15.6f} ETH │")
    print(f"  │ {'  Burned:':<20} {burned/10**18:>15.6f} ETH │")
    print(f"  │ {'  To validator:':<20} {to_validator/10**18:>15.6f} ETH │")
    print(f"  └{'─' * 44}┘")

    # --- Summary --------------------------------------------------------------

    print("\n" + "=" * 64)
    print("  KEY TAKEAWAYS")
    print("=" * 64)
    print("  1. Every opcode has a fixed gas cost (ADD=3, SSTORE=20000)")
    print("  2. Gas prevents infinite loops and prices computational resources")
    print("  3. Out-of-gas reverts state changes but still charges the fee")
    print("  4. EIP-1559 adjusts base fee to target 50% block utilization")
    print("  5. Base fee is BURNED (reducing ETH supply); tips go to validators")
    print("  6. When blocks are full, base fee rises ~12.5% per block")
    print("  7. This makes fees more predictable vs the old auction model")
    print()


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
