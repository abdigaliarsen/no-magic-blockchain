# no-magic-blockchain

> "Because `web3.sendTransaction()` isn't an explanation."

Single-file, zero-dependency Python scripts that teach blockchain from scratch.
Inspired by [no-magic](https://github.com/Mathews-Tom/no-magic).

## Project Overview

This project contains ~32 Python scripts across 4 categories that implement blockchain
concepts from first principles. Each script is self-contained, uses only Python 3.10+ stdlib,
and runs in seconds on CPU.

## Branch Strategy

- **v1 branch**: Approach A — flat folders per chain, ~8 scripts each
- **v2 branch**: Approach B — tiered sub-folders (fundamentals/intermediate/advanced), 20+ scripts per chain (CURRENT)

## Directory Structure

```
no-magic-blockchain/
├── CLAUDE.md              # THIS FILE — project rules and conventions
├── README.md              # Project overview with GIF previews
├── core/                  # Chain-agnostic fundamentals
│   ├── fundamentals/      # 8 scripts (01-08)
│   ├── intermediate/      # (planned)
│   └── advanced/          # (planned)
├── bitcoin/               # Bitcoin-specific implementations
│   ├── fundamentals/      # 8 scripts (01-08)
│   ├── intermediate/      # (planned)
│   └── advanced/          # (planned)
├── ethereum/              # Ethereum-specific implementations
│   ├── fundamentals/      # 8 scripts (01-08)
│   ├── intermediate/      # (planned)
│   └── advanced/          # (planned)
├── solana/                # Solana-specific implementations
│   ├── fundamentals/      # 8 scripts (01-08)
│   ├── intermediate/      # (planned)
│   └── advanced/          # (planned)
├── animations/            # Manim animation scripts (HAS external deps, separate from core)
│   └── requirements.txt   # manim dependency lives here only
├── assets/gifs/           # Pre-rendered GIFs for README
└── docs/plans/            # Design documents
```

## Script Conventions — FOLLOW EXACTLY

### Rules (non-negotiable)

1. **Zero external dependencies** — ONLY Python 3.10+ standard library (hashlib, struct, os, json, math, etc.)
2. **Single file** — each script is completely self-contained, no imports from other scripts
3. **Runs standalone** — `python3 core/fundamentals/01_hashing.py` must work with no setup
4. **Runs in seconds on CPU** — no GPU, no network calls, no file I/O beyond stdout
5. **Naming** — `NN_snake_case_topic.py` (zero-padded number for learning order)

### Script Structure (every script must follow this template)

```python
"""
TITLE: <Concept Name>
CATEGORY: <core|bitcoin|ethereum|solana>

WHAT THIS IMPLEMENTS:
    <2-3 sentences explaining what this script builds from scratch>

KEY CONCEPTS:
    - <concept 1>
    - <concept 2>
    - <concept 3>

PREREQUISITE SCRIPTS:
    - <list scripts that should be read/run before this one, or "None">

REAL-WORLD RELEVANCE:
    <1-2 sentences on where this is used in production blockchains>
"""

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# <explain each constant>

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# <the actual algorithm, with inline comments on every non-obvious line>
# <use classes and functions, not a giant script>
# <break complex logic into small, named functions>

# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of the concept."""
    # <create example data>
    # <run the algorithm>
    # <print formatted, visual output showing what happened>
    # <use box-drawing characters, ASCII art, or formatted tables for clarity>
    pass

# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
```

### Comment Style

- **Every non-obvious line** gets an inline comment
- **Section headers** use `# ====` full-width separators
- **Sub-sections** use `# ----` separators
- Comments explain **WHY**, not just **WHAT**
- Use analogies where helpful (e.g., "Think of this like a post office box...")
- Target audience: developer who knows Python but not blockchain

### Output Style

Each script's demo() must print clear, formatted output:
- Use section headers with `=` or `-` underlines
- Use box-drawing characters for visual structures (blocks, trees, chains)
- Show before/after states for transformations
- Print intermediate steps, not just final results
- Example output for a blockchain script:

```
=== Building a Blockchain ===

Block #0 (Genesis)
┌─────────────────────────────────┐
│ prev_hash: 0000000000000000     │
│ data:      Genesis Block        │
│ nonce:     0                    │
│ hash:      a1b2c3d4...         │
└─────────────────────────────────┘
         │
         ▼
Block #1
┌─────────────────────────────────┐
│ prev_hash: a1b2c3d4...         │
│ data:      Alice pays Bob 5    │
│ nonce:     23847                │
│ hash:      e5f6a7b8...         │
└─────────────────────────────────┘

Tampering with Block #0...
✗ Chain validation FAILED — hash mismatch at Block #1
```

## Implementation Order

Build scripts in this EXACT order. Each group can be parallelized internally,
but groups must be sequential (core first, then chains).

### Group 1: core/ (build first — chains depend on these concepts)

| # | File | What to Build |
|---|------|--------------|
| 01 | `core/fundamentals/01_hashing.py` | SHA-256 from scratch (bit manipulation, padding, rounds). Demo: hash strings, show avalanche effect (1-bit input change → ~50% output change) |
| 02 | `core/fundamentals/02_public_key_crypto.py` | Elliptic curve math over finite fields (point addition, scalar multiplication). Generate keypairs on secp256k1. Demo: generate keys, show math |
| 03 | `core/fundamentals/03_digital_signatures.py` | ECDSA sign/verify from scratch. Demo: sign message, verify, then tamper and show verification fails |
| 04 | `core/fundamentals/04_merkle_trees.py` | Binary hash tree. Build tree from transactions, generate/verify inclusion proofs. Demo: build tree, prove membership, show proof size vs data size |
| 05 | `core/fundamentals/05_blockchain.py` | Block structure (prev_hash, timestamp, data, nonce, hash). Chain blocks, validate chain integrity. Demo: build chain, tamper with block, show detection |
| 06 | `core/fundamentals/06_consensus_pow.py` | Proof-of-work: find nonce where hash < target. Difficulty adjustment. Demo: mine blocks with increasing difficulty, show time/attempts |
| 07 | `core/fundamentals/07_consensus_pos.py` | Proof-of-stake: validator selection weighted by stake, slashing for double-signing. Demo: simulate validator set, show selection distribution, slash a misbehaving validator |
| 08 | `core/fundamentals/08_p2p_network.py` | Gossip protocol simulation: nodes discover peers, propagate blocks, handle forks. Demo: simulate 10-node network, show message propagation steps |

### Group 2: bitcoin/ (after core is done)

| # | File | What to Build |
|---|------|--------------|
| 01 | `bitcoin/fundamentals/01_utxo_model.py` | UTXO set management: create transactions consuming inputs, producing outputs, tracking unspent set. Demo: multi-tx chain with change outputs |
| 02 | `bitcoin/fundamentals/02_bitcoin_script.py` | Stack-based Script VM: implement OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, etc. Demo: evaluate P2PKH script step-by-step showing stack state |
| 03 | `bitcoin/fundamentals/03_mining.py` | Bitcoin-specific mining: coinbase transaction, block header construction, nonce search. Demo: mine a block with transactions, show reward |
| 04 | `bitcoin/fundamentals/04_spv_verification.py` | Simplified Payment Verification: verify transaction inclusion using block headers + Merkle proofs without full blockchain. Demo: verify tx with minimal data |
| 05 | `bitcoin/fundamentals/05_wallets_hd.py` | HD wallets: BIP-32 key derivation, master seed → child keys, derivation paths (m/44'/0'/0'/0/0). Demo: derive multiple addresses from one seed |
| 06 | `bitcoin/fundamentals/06_segwit.py` | Segregated Witness: separate witness data, calculate weight units, show malleability fix. Demo: compare legacy vs segwit transaction structure |
| 07 | `bitcoin/fundamentals/07_difficulty_adjustment.py` | Retarget algorithm: every 2016 blocks, adjust target based on actual vs expected time. Demo: simulate 10 epochs with varying hash rates |
| 08 | `bitcoin/fundamentals/08_simplified_lightning.py` | Payment channels: funding tx, commitment txs, HTLCs, channel close. Demo: open channel, route payment through 3 nodes, settle |

### Group 3: ethereum/ (after core is done, parallel with bitcoin)

| # | File | What to Build |
|---|------|--------------|
| 01 | `ethereum/fundamentals/01_accounts_state.py` | World state: account objects (nonce, balance, codeHash, storageRoot), state transitions from transactions. Demo: process transfers, show state changes |
| 02 | `ethereum/fundamentals/02_evm_bytecode.py` | EVM implementation: stack machine with PUSH, POP, ADD, MUL, MSTORE, MLOAD, SSTORE, SLOAD, JUMP, JUMPI, etc. Demo: execute bytecode step-by-step showing stack/memory/storage |
| 03 | `ethereum/fundamentals/03_gas_execution.py` | Gas model: assign gas costs per opcode, track gas usage, implement EIP-1559 (base fee + priority fee, elastic block size). Demo: execute contract, show gas consumption per opcode |
| 04 | `ethereum/fundamentals/04_rlp_encoding.py` | RLP encode/decode: handle strings, lists, nested structures, empty values. Demo: encode various types, show byte output, round-trip verification |
| 05 | `ethereum/fundamentals/05_merkle_patricia_trie.py` | Modified Merkle Patricia Trie: extension/branch/leaf nodes, nibble path encoding, insert/lookup/proof. Demo: build trie, lookup key, generate state proof |
| 06 | `ethereum/fundamentals/06_smart_contracts.py` | Contract lifecycle: deploy bytecode, call functions via ABI, read/write storage slots. Demo: deploy a simple counter contract, call increment, read value |
| 07 | `ethereum/fundamentals/07_pos_beacon.py` | Beacon chain: validator registration, epoch/slot structure, attestations, finality (simplified Casper FFG). Demo: simulate validators across epochs, show finalization |
| 08 | `ethereum/fundamentals/08_abi_encoding.py` | ABI encoding: function selectors (keccak256), uint256/address/bytes/string/tuple encoding, decode calldata. Demo: encode function call, decode it back |

### Group 4: solana/ (after core is done, parallel with bitcoin/ethereum)

| # | File | What to Build |
|---|------|--------------|
| 01 | `solana/fundamentals/01_accounts_model.py` | Solana account structure: owner, lamports, data, executable flag. Program-derived addresses (PDAs). Demo: create accounts, show ownership rules |
| 02 | `solana/fundamentals/02_proof_of_history.py` | PoH: sequential SHA-256 hashing as verifiable delay function, embed external events. Demo: generate PoH sequence, verify ordering, show timestamp proofs |
| 03 | `solana/fundamentals/03_programs.py` | Stateless program model: instruction processing, account validation, cross-program invocation (CPI). Demo: process instructions, show account mutations |
| 04 | `solana/fundamentals/04_transactions.py` | Transaction format: message (header, account keys, recent blockhash, instructions), signatures. Demo: build, sign, and verify a multi-instruction transaction |
| 05 | `solana/fundamentals/05_rent_model.py` | Rent: calculate minimum balance for rent exemption based on data size, show rent collection. Demo: create accounts of various sizes, show rent thresholds |
| 06 | `solana/fundamentals/06_token_program.py` | SPL Token: mint accounts, token accounts, mint/transfer/burn instructions. Demo: create token, mint supply, transfer between accounts |
| 07 | `solana/fundamentals/07_turbine_propagation.py` | Turbine: shred blocks into packets, erasure coding (Reed-Solomon simplified), tree-based propagation to validators. Demo: shred block, simulate tree broadcast, reconstruct from partial data |
| 08 | `solana/fundamentals/08_gulf_stream.py` | Gulf Stream: transaction forwarding to upcoming leaders, leader schedule, mempool-less architecture. Demo: simulate leader rotation, show tx forwarding path |

## Animations (separate from core scripts)

- Located in `animations/` folder
- USE Manim (external dependency, listed in `animations/requirements.txt`)
- One animation per core script: `animations/core_01_hashing.py`, etc.
- Pre-rendered GIFs saved to `assets/gifs/` for README embedding
- Animations are OPTIONAL — build them AFTER all 32 scripts are done

## Quality Checklist (verify each script against this)

- [ ] Runs with `python3 <script>.py` — no args, no setup, no errors
- [ ] Zero imports outside stdlib
- [ ] Module docstring follows the template exactly
- [ ] All 4 sections present (constants, implementation, demo, entry point)
- [ ] Demo output is visual and formatted (not just raw print statements)
- [ ] Every non-obvious line has an inline comment
- [ ] Comments explain WHY not just WHAT
- [ ] No network calls, no file reads, no external data
- [ ] Runs in under 30 seconds on a modern laptop

## v2 Plan (in progress — v2 branch)

Expanding to 16 scripts per chain (8 fundamentals + 4 intermediate + 4 advanced):
1. ~~Create `v2` branch from `v1`~~ (done)
2. ~~Reorganize each chain folder into `fundamentals/`, `intermediate/`, `advanced/`~~ (done)
3. Add intermediate topics: 4 scripts per chain covering deeper protocol mechanics
4. Add advanced topics: 4 scripts per chain (ZK proofs, MEV, sharding, rollups, etc.)
5. Generate GIFs for all new scripts
6. Future: add more chains (Cosmos/Tendermint, Polkadot, Cardano)
