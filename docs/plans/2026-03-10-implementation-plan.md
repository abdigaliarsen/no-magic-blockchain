# no-magic-blockchain Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build 32 single-file, zero-dependency Python scripts that teach blockchain from scratch, plus a README.

**Architecture:** 4 folders (core, bitcoin, ethereum, solana) with 8 scripts each. Each script is self-contained Python 3.10+ stdlib only. Scripts follow the template in CLAUDE.md exactly.

**Tech Stack:** Python 3.10+ standard library only. No pip packages. No network calls.

**IMPORTANT:** Read `CLAUDE.md` in the project root FIRST. It contains the exact template, conventions, topic specs, and quality checklist that every script must follow. Do not deviate from it.

**Branch:** You are on `v1`. Stay on `v1`.

---

## Phase 1: Core Scripts (build these FIRST — all chain scripts depend on these concepts)

### Task 1: core/01_hashing.py

**Files:**
- Create: `core/01_hashing.py`

**Step 1: Write the script**

Implement SHA-256 from scratch using only bit manipulation, following the FIPS 180-4 spec:
- Initial hash values (first 32 bits of fractional parts of sqrt of first 8 primes)
- Round constants (first 32 bits of fractional parts of cube roots of first 64 primes)
- Message padding (append 1-bit, zeros, 64-bit length)
- Message schedule (16 words expanded to 64)
- 64 rounds of compression (Ch, Maj, Sigma0, Sigma1, sigma0, sigma1)
- Demo: hash several strings, show avalanche effect (change 1 bit, count how many output bits flip)

Output should show:
```
=== SHA-256 From Scratch ===
Input: "hello"
Hash:  2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

=== Avalanche Effect ===
"hello"  → 2cf24dba...
"hallo"  → 20671...    (flipped 128/256 bits = 50.0%)
```

**Step 2: Run and verify**

Run: `python3 core/01_hashing.py`
Expected: Runs without error, output matches Python's `hashlib.sha256` for the same inputs. Verify inside the script by comparing against hashlib at the end of demo().

**Step 3: Commit**

```bash
git add core/01_hashing.py
git commit -m "feat(core): add SHA-256 from scratch with avalanche effect demo"
```

---

### Task 2: core/02_public_key_crypto.py

**Files:**
- Create: `core/02_public_key_crypto.py`

**Step 1: Write the script**

Implement elliptic curve cryptography over finite fields:
- Define secp256k1 curve parameters (p, a, b, G, n)
- Point addition and doubling on the curve
- Scalar multiplication (double-and-add)
- Key generation: private key (random int < n) → public key (scalar mult of G)
- Demo: generate keypair, show the math, verify public key is on curve

Output should show:
```
=== Elliptic Curve Cryptography (secp256k1) ===
Private Key: 0x1a2b3c... (256-bit random)
Public Key:
  x: 0x4f3c...
  y: 0x7a2e...
Point on curve? True (y² = x³ + 7 mod p)
```

**Step 2: Run and verify**

Run: `python3 core/02_public_key_crypto.py`
Expected: Runs without error, generated public key satisfies curve equation.

**Step 3: Commit**

```bash
git add core/02_public_key_crypto.py
git commit -m "feat(core): add elliptic curve cryptography with secp256k1"
```

---

### Task 3: core/03_digital_signatures.py

**Files:**
- Create: `core/03_digital_signatures.py`

**Step 1: Write the script**

Implement ECDSA sign and verify from scratch:
- Copy/re-implement the EC math from 02 (remember: self-contained, no imports from other scripts)
- Sign: hash message, pick random k, compute r = (k*G).x mod n, s = k⁻¹(hash + r*privkey) mod n
- Verify: compute u1, u2, recover point, check r
- Demo: sign a message, verify it, then tamper with message and show verification fails

Output should show:
```
=== ECDSA Digital Signatures ===
Message: "Transfer 5 BTC to Alice"
Signature:
  r: 0x3a4b...
  s: 0x7c8d...

Verification: VALID ✓

Tampered message: "Transfer 50 BTC to Alice"
Verification: INVALID ✗
```

**Step 2: Run and verify**

Run: `python3 core/03_digital_signatures.py`
Expected: Valid signature verifies, tampered message fails verification.

**Step 3: Commit**

```bash
git add core/03_digital_signatures.py
git commit -m "feat(core): add ECDSA digital signatures with tamper detection"
```

---

### Task 4: core/04_merkle_trees.py

**Files:**
- Create: `core/04_merkle_trees.py`

**Step 1: Write the script**

Implement binary Merkle tree:
- Build tree from list of transaction hashes (use hashlib.sha256 — it's stdlib)
- Handle odd number of leaves (duplicate last)
- Generate inclusion proof (list of sibling hashes + directions)
- Verify proof given leaf, proof, and root
- Demo: build tree from 8 transactions, prove one is included, show proof size efficiency

Output should show:
```
=== Merkle Tree ===
Transactions: [tx0, tx1, tx2, tx3, tx4, tx5, tx6, tx7]

Tree Structure:
                    ROOT: a1b2...
                   /            \
            h01: 3c4d...    h23: 5e6f...
            /       \        /       \
         ...        ...    ...       ...

=== Inclusion Proof for tx5 ===
Proof: [hash4, hash67, hash0123]  (3 hashes)
Verification: VALID ✓
Efficiency: 3 hashes to prove 1 of 8 transactions (log2(8) = 3)
```

**Step 2: Run and verify**

Run: `python3 core/04_merkle_trees.py`
Expected: Proof verification succeeds, tree structure displays correctly.

**Step 3: Commit**

```bash
git add core/04_merkle_trees.py
git commit -m "feat(core): add Merkle tree with inclusion proofs"
```

---

### Task 5: core/05_blockchain.py

**Files:**
- Create: `core/05_blockchain.py`

**Step 1: Write the script**

Implement basic blockchain:
- Block class: index, timestamp, data, previous_hash, nonce, hash
- Chain class: list of blocks, genesis block creation, add_block, validate_chain
- Hash each block with SHA-256 (hashlib)
- Demo: build 5-block chain, display it visually, tamper with block 2, show validation catches it

Output should show visual chain with box-drawing characters as specified in CLAUDE.md output style section.

**Step 2: Run and verify**

Run: `python3 core/05_blockchain.py`
Expected: Chain builds correctly, tampering is detected.

**Step 3: Commit**

```bash
git add core/05_blockchain.py
git commit -m "feat(core): add blockchain with tamper detection"
```

---

### Task 6: core/06_consensus_pow.py

**Files:**
- Create: `core/06_consensus_pow.py`

**Step 1: Write the script**

Implement proof-of-work consensus:
- Mining function: find nonce where SHA-256(block_header + nonce) starts with N zero bits
- Difficulty target as number of leading zeros
- Difficulty adjustment: if blocks too fast → increase difficulty, too slow → decrease
- Demo: mine 5 blocks at difficulty 16 (2 hex zeros), show nonce attempts and time per block

Output should show:
```
=== Proof of Work Mining ===
Difficulty: 16 bits (target starts with 0000...)

Mining Block #1...
  Attempts: 45,231
  Time: 0.82s
  Nonce: 45230
  Hash: 0000a3b7c8...
```

**Step 2: Run and verify**

Run: `python3 core/06_consensus_pow.py`
Expected: All mined blocks have hashes meeting difficulty target. Runs in <30 seconds.

**Step 3: Commit**

```bash
git add core/06_consensus_pow.py
git commit -m "feat(core): add proof-of-work with difficulty adjustment"
```

---

### Task 7: core/07_consensus_pos.py

**Files:**
- Create: `core/07_consensus_pos.py`

**Step 1: Write the script**

Implement proof-of-stake consensus:
- Validator class: address, stake amount, active status
- Validator selection: weighted random by stake
- Slashing: detect double-signing, reduce stake
- Epoch-based rotation
- Demo: 5 validators with different stakes, simulate 100 slot selections (show distribution matches stake weight), slash one for double-signing

Output should show selection distribution and slashing event.

**Step 2: Run and verify**

Run: `python3 core/07_consensus_pos.py`
Expected: Selection frequency roughly proportional to stake. Slashed validator loses stake.

**Step 3: Commit**

```bash
git add core/07_consensus_pos.py
git commit -m "feat(core): add proof-of-stake with validator selection and slashing"
```

---

### Task 8: core/08_p2p_network.py

**Files:**
- Create: `core/08_p2p_network.py`

**Step 1: Write the script**

Simulate peer-to-peer gossip network (no actual networking — simulate in-memory):
- Node class: id, peers list, known_blocks
- Network class: manages all nodes
- Gossip protocol: when node gets new block, forward to all peers
- Peer discovery: bootstrap nodes, random peer exchange
- Fork handling: longest-chain rule
- Demo: 10 nodes, create a block at node 0, show propagation step by step (which node has it at each tick)

Output should show:
```
=== P2P Gossip Network (10 nodes) ===
Tick 0: Node 0 creates Block #1
Tick 1: Node 0 → [Node 2, Node 5]  (2 nodes have block)
Tick 2: Node 2 → [Node 7], Node 5 → [Node 3, Node 8]  (5 nodes)
...
Tick 4: All 10 nodes have Block #1
```

**Step 2: Run and verify**

Run: `python3 core/08_p2p_network.py`
Expected: Block reaches all nodes, propagation steps are logical.

**Step 3: Commit**

```bash
git add core/08_p2p_network.py
git commit -m "feat(core): add P2P gossip network simulation"
```

---

## Phase 2: Bitcoin Scripts (after Phase 1 is committed)

Phase 2, 3, and 4 can be built in PARALLEL if using subagents.

### Task 9: bitcoin/01_utxo_model.py

**Files:**
- Create: `bitcoin/01_utxo_model.py`

**Step 1: Write the script**

Implement UTXO (Unspent Transaction Output) model:
- Transaction class: inputs (references to previous tx output), outputs (amount + recipient)
- UTXO set: track all unspent outputs
- Spending: consume inputs, create new outputs, handle change
- Validation: inputs must reference existing UTXOs, no double-spending
- Demo: chain of transactions — coinbase → Alice, Alice → Bob (with change back to Alice), Bob → Charlie

**Step 2: Run and verify**

Run: `python3 bitcoin/01_utxo_model.py`
Expected: UTXO set updates correctly, balances match.

**Step 3: Commit**

```bash
git add bitcoin/01_utxo_model.py
git commit -m "feat(bitcoin): add UTXO model with transaction chaining"
```

---

### Task 10: bitcoin/02_bitcoin_script.py

**Files:**
- Create: `bitcoin/02_bitcoin_script.py`

**Step 1: Write the script**

Implement Bitcoin Script VM:
- Stack-based execution engine
- Opcodes: OP_DUP, OP_HASH160, OP_EQUAL, OP_EQUALVERIFY, OP_CHECKSIG, OP_VERIFY, OP_IF/OP_ELSE/OP_ENDIF, OP_ADD, OP_SUB, OP_TRUE, OP_FALSE
- P2PKH (Pay-to-Public-Key-Hash) script evaluation
- Demo: step-by-step execution of P2PKH showing stack state after each opcode

**Step 2: Run and verify**

Run: `python3 bitcoin/02_bitcoin_script.py`

**Step 3: Commit**

```bash
git add bitcoin/02_bitcoin_script.py
git commit -m "feat(bitcoin): add Script VM with P2PKH evaluation"
```

---

### Task 11: bitcoin/03_mining.py

**Files:**
- Create: `bitcoin/03_mining.py`

**Step 1: Write the script**

Implement Bitcoin-specific mining:
- Coinbase transaction (block reward + fees)
- Block header: version, prev_hash, merkle_root, timestamp, bits (difficulty), nonce
- Double SHA-256 hashing (Bitcoin uses SHA256(SHA256(header)))
- Halving schedule (every 210,000 blocks: 50 → 25 → 12.5 → 6.25...)
- Demo: mine a block with 5 transactions, show coinbase, Merkle root, and reward

**Step 2: Run and verify**

Run: `python3 bitcoin/03_mining.py`

**Step 3: Commit**

```bash
git add bitcoin/03_mining.py
git commit -m "feat(bitcoin): add mining with coinbase tx and halving"
```

---

### Task 12: bitcoin/04_spv_verification.py

**Files:**
- Create: `bitcoin/04_spv_verification.py`

**Step 1: Write the script**

Implement SPV (Simplified Payment Verification):
- Block headers chain (80 bytes each — no full blocks)
- Merkle proof verification against header's merkle_root
- Lightweight client: verify transaction with just headers + proof
- Demo: full node creates proof, light client verifies with minimal data, show data savings

**Step 2: Run and verify**

Run: `python3 bitcoin/04_spv_verification.py`

**Step 3: Commit**

```bash
git add bitcoin/04_spv_verification.py
git commit -m "feat(bitcoin): add SPV verification with Merkle proofs"
```

---

### Task 13: bitcoin/05_wallets_hd.py

**Files:**
- Create: `bitcoin/05_wallets_hd.py`

**Step 1: Write the script**

Implement HD (Hierarchical Deterministic) wallets:
- BIP-32: master key from seed, child key derivation (HMAC-SHA512)
- Derivation paths: m/44'/0'/0'/0/0 format
- Hardened vs normal derivation
- Generate multiple addresses from single seed
- Demo: generate seed, derive 5 addresses at path m/44'/0'/0'/0/N, show each

**Step 2: Run and verify**

Run: `python3 bitcoin/05_wallets_hd.py`

**Step 3: Commit**

```bash
git add bitcoin/05_wallets_hd.py
git commit -m "feat(bitcoin): add HD wallets with BIP-32 derivation"
```

---

### Task 14: bitcoin/06_segwit.py

**Files:**
- Create: `bitcoin/06_segwit.py`

**Step 1: Write the script**

Implement Segregated Witness:
- Legacy transaction structure vs SegWit (witness separated)
- Weight units calculation (non-witness * 4 + witness * 1)
- Transaction malleability: show how legacy txids change when signature changes, SegWit txids don't
- Demo: same transaction in legacy vs segwit format, compare sizes and txids

**Step 2: Run and verify**

Run: `python3 bitcoin/06_segwit.py`

**Step 3: Commit**

```bash
git add bitcoin/06_segwit.py
git commit -m "feat(bitcoin): add SegWit with malleability fix demo"
```

---

### Task 15: bitcoin/07_difficulty_adjustment.py

**Files:**
- Create: `bitcoin/07_difficulty_adjustment.py`

**Step 1: Write the script**

Implement Bitcoin's difficulty retarget algorithm:
- Target: 1 block per 10 minutes → 2016 blocks per 2 weeks
- Retarget: new_target = old_target * (actual_time / expected_time)
- Clamp: max 4x increase or decrease per period
- Demo: simulate 10 retarget epochs with varying hash rates, show difficulty curve

**Step 2: Run and verify**

Run: `python3 bitcoin/07_difficulty_adjustment.py`

**Step 3: Commit**

```bash
git add bitcoin/07_difficulty_adjustment.py
git commit -m "feat(bitcoin): add difficulty adjustment algorithm"
```

---

### Task 16: bitcoin/08_simplified_lightning.py

**Files:**
- Create: `bitcoin/08_simplified_lightning.py`

**Step 1: Write the script**

Implement simplified Lightning Network:
- Payment channel: funding tx locks funds, commitment txs track balances
- HTLC (Hash Time-Locked Contracts): hash preimage reveals enable payment routing
- Multi-hop routing: A→B→C payment through intermediary
- Channel close: cooperative (latest state) vs force close (timelock)
- Demo: open channel, make 3 payments, route through intermediary, close cooperatively

**Step 2: Run and verify**

Run: `python3 bitcoin/08_simplified_lightning.py`

**Step 3: Commit**

```bash
git add bitcoin/08_simplified_lightning.py
git commit -m "feat(bitcoin): add simplified Lightning Network"
```

---

## Phase 3: Ethereum Scripts (parallel with Phase 2)

### Task 17: ethereum/01_accounts_state.py

**Files:**
- Create: `ethereum/01_accounts_state.py`

**Step 1: Write the script**

Implement Ethereum's account-based state model:
- Account: nonce, balance, code_hash, storage_root
- EOA (externally owned) vs contract accounts
- World state: mapping of address → account
- State transition: process transfer tx (update nonces, balances)
- Demo: create accounts, process 3 transfers, show world state before/after each

**Step 2: Run and verify**

Run: `python3 ethereum/01_accounts_state.py`

**Step 3: Commit**

```bash
git add ethereum/01_accounts_state.py
git commit -m "feat(ethereum): add account-based state model"
```

---

### Task 18: ethereum/02_evm_bytecode.py

**Files:**
- Create: `ethereum/02_evm_bytecode.py`

**Step 1: Write the script**

Implement a minimal EVM:
- 256-bit stack machine
- Opcodes: STOP, ADD, MUL, SUB, DIV, MOD, LT, GT, EQ, ISZERO, AND, OR, NOT, POP, MLOAD, MSTORE, SLOAD, SSTORE, JUMP, JUMPI, JUMPDEST, PUSH1-PUSH32, DUP1, SWAP1, RETURN
- Memory: byte-addressable, word-aligned reads/writes
- Storage: key-value (256-bit → 256-bit)
- Demo: execute a bytecode program (e.g., compute 2+3, store result) step-by-step showing stack, memory, storage after each opcode

**Step 2: Run and verify**

Run: `python3 ethereum/02_evm_bytecode.py`

**Step 3: Commit**

```bash
git add ethereum/02_evm_bytecode.py
git commit -m "feat(ethereum): add EVM bytecode interpreter"
```

---

### Task 19: ethereum/03_gas_execution.py

**Files:**
- Create: `ethereum/03_gas_execution.py`

**Step 1: Write the script**

Implement gas metering and EIP-1559:
- Gas costs per opcode (ADD=3, MUL=5, SSTORE=20000, etc.)
- Gas limit and out-of-gas handling
- EIP-1559: base fee (adjusted per block based on utilization), priority fee (tip), elastic block size (target vs max)
- Demo: execute contract with gas tracking per opcode, simulate 10 blocks of varying utilization showing base fee adjustment

**Step 2: Run and verify**

Run: `python3 ethereum/03_gas_execution.py`

**Step 3: Commit**

```bash
git add ethereum/03_gas_execution.py
git commit -m "feat(ethereum): add gas metering and EIP-1559 fee model"
```

---

### Task 20: ethereum/04_rlp_encoding.py

**Files:**
- Create: `ethereum/04_rlp_encoding.py`

**Step 1: Write the script**

Implement RLP (Recursive Length Prefix) encoding/decoding:
- Single byte (0x00-0x7f): itself
- Short string (0-55 bytes): 0x80 + len, then data
- Long string (>55 bytes): 0xb7 + len_of_len, then len, then data
- Short list, long list: same pattern with 0xc0/0xf7
- Demo: encode various types (empty string, "dog", nested lists, transaction-like structure), show hex output, decode back and verify round-trip

**Step 2: Run and verify**

Run: `python3 ethereum/04_rlp_encoding.py`

**Step 3: Commit**

```bash
git add ethereum/04_rlp_encoding.py
git commit -m "feat(ethereum): add RLP encoding and decoding"
```

---

### Task 21: ethereum/05_merkle_patricia_trie.py

**Files:**
- Create: `ethereum/05_merkle_patricia_trie.py`

**Step 1: Write the script**

Implement Modified Merkle Patricia Trie:
- Node types: blank, leaf, extension, branch (17-element array)
- Hex-prefix encoding for nibble paths (compact encoding)
- Insert, lookup, delete operations
- Generate and verify state proofs
- Demo: insert 5 key-value pairs, visualize trie structure, lookup key, generate proof

**Step 2: Run and verify**

Run: `python3 ethereum/05_merkle_patricia_trie.py`

**Step 3: Commit**

```bash
git add ethereum/05_merkle_patricia_trie.py
git commit -m "feat(ethereum): add Merkle Patricia Trie"
```

---

### Task 22: ethereum/06_smart_contracts.py

**Files:**
- Create: `ethereum/06_smart_contracts.py`

**Step 1: Write the script**

Implement smart contract lifecycle (builds on EVM concepts):
- Deploy: store bytecode at address (keccak256 of deployer + nonce)
- Call: load code, set up execution context (msg.sender, msg.value), run EVM
- Storage: persistent key-value per contract
- Demo: deploy a simple counter contract, call increment() 3 times, call get() — show storage state changes

**Step 2: Run and verify**

Run: `python3 ethereum/06_smart_contracts.py`

**Step 3: Commit**

```bash
git add ethereum/06_smart_contracts.py
git commit -m "feat(ethereum): add smart contract deploy and call lifecycle"
```

---

### Task 23: ethereum/07_pos_beacon.py

**Files:**
- Create: `ethereum/07_pos_beacon.py`

**Step 1: Write the script**

Implement simplified Beacon chain:
- Validator registry: deposit 32 ETH, activation queue
- Slot/epoch structure (32 slots per epoch)
- Proposer selection per slot (RANDAO-based)
- Attestations: validators vote on head block
- Simplified Casper FFG: justified → finalized after 2 epochs of supermajority
- Demo: 10 validators, simulate 3 epochs, show proposals, attestations, finalization

**Step 2: Run and verify**

Run: `python3 ethereum/07_pos_beacon.py`

**Step 3: Commit**

```bash
git add ethereum/07_pos_beacon.py
git commit -m "feat(ethereum): add Beacon chain with Casper FFG finality"
```

---

### Task 24: ethereum/08_abi_encoding.py

**Files:**
- Create: `ethereum/08_abi_encoding.py`

**Step 1: Write the script**

Implement Ethereum ABI encoding:
- Function selector: first 4 bytes of keccak256 of signature
- Static types: uint256, address, bool, bytesN — left-padded to 32 bytes
- Dynamic types: bytes, string, arrays — offset pointer + length + data
- Tuples and nested arrays
- Demo: encode `transfer(address,uint256)` call, encode complex function with mixed types, decode calldata back

Note: implement keccak256 from scratch OR use hashlib (Python 3.11+ has hashlib.sha3_256 which is NOT keccak256 — they differ in padding). Implement the keccak256 variant if feasible, or use a simplified version with a clear comment explaining the difference.

**Step 2: Run and verify**

Run: `python3 ethereum/08_abi_encoding.py`

**Step 3: Commit**

```bash
git add ethereum/08_abi_encoding.py
git commit -m "feat(ethereum): add ABI encoding and decoding"
```

---

## Phase 4: Solana Scripts (parallel with Phase 2 and 3)

### Task 25: solana/01_accounts_model.py

**Files:**
- Create: `solana/01_accounts_model.py`

**Step 1: Write the script**

Implement Solana's account model:
- Account: pubkey, owner (program), lamports, data (byte array), executable flag, rent_epoch
- Ownership rules: only owner program can modify data, anyone can credit lamports
- Program-Derived Addresses (PDAs): deterministic address from seeds + program_id (find off-curve point)
- System program: create account, transfer, assign owner
- Demo: create accounts, transfer lamports, derive PDA, show ownership rules

**Step 2: Run and verify**

Run: `python3 solana/01_accounts_model.py`

**Step 3: Commit**

```bash
git add solana/01_accounts_model.py
git commit -m "feat(solana): add account model with PDAs"
```

---

### Task 26: solana/02_proof_of_history.py

**Files:**
- Create: `solana/02_proof_of_history.py`

**Step 1: Write the script**

Implement Proof of History:
- Sequential SHA-256: each hash = SHA256(previous_hash). This creates a verifiable passage of time.
- Tick: record hash at regular intervals
- Event insertion: mix external data (transaction hash) into the sequence
- Verification: re-compute sequence to verify ordering and timing
- Demo: generate 1000-hash PoH sequence, insert 3 events, verify the sequence, show that verification confirms ordering

**Step 2: Run and verify**

Run: `python3 solana/02_proof_of_history.py`

**Step 3: Commit**

```bash
git add solana/02_proof_of_history.py
git commit -m "feat(solana): add Proof of History"
```

---

### Task 27: solana/03_programs.py

**Files:**
- Create: `solana/03_programs.py`

**Step 1: Write the script**

Implement Solana's stateless program model:
- Programs are stateless — they process instructions and modify accounts passed to them
- Instruction: program_id, account keys (with is_signer/is_writable flags), data
- Program entrypoint: process_instruction(program_id, accounts, instruction_data)
- Cross-Program Invocation (CPI): one program calls another
- Demo: implement a simple "counter" program and a "proxy" program that calls it via CPI

**Step 2: Run and verify**

Run: `python3 solana/03_programs.py`

**Step 3: Commit**

```bash
git add solana/03_programs.py
git commit -m "feat(solana): add stateless programs with CPI"
```

---

### Task 28: solana/04_transactions.py

**Files:**
- Create: `solana/04_transactions.py`

**Step 1: Write the script**

Implement Solana transaction format:
- Message: header (num_signers, num_readonly_signed, num_readonly_unsigned), account_keys[], recent_blockhash, instructions[]
- Compact instruction format: program_id_index, account_indexes[], data
- Signatures: Ed25519 (simplified — use ECDSA from earlier concepts or simplified Ed25519)
- Transaction serialization
- Demo: build a multi-instruction transaction (create account + transfer), serialize, sign, verify

**Step 2: Run and verify**

Run: `python3 solana/04_transactions.py`

**Step 3: Commit**

```bash
git add solana/04_transactions.py
git commit -m "feat(solana): add transaction format and signing"
```

---

### Task 29: solana/05_rent_model.py

**Files:**
- Create: `solana/05_rent_model.py`

**Step 1: Write the script**

Implement Solana's rent model:
- Rent rate: lamports per byte per epoch
- Rent exemption: minimum balance = 2 years of rent (account is exempt if balance >= this)
- Rent collection: non-exempt accounts get rent deducted each epoch
- Account size impact on minimum balance
- Demo: create accounts of sizes 0, 100, 1000, 10000 bytes, show rent-exempt minimums, simulate rent collection over epochs for non-exempt account

**Step 2: Run and verify**

Run: `python3 solana/05_rent_model.py`

**Step 3: Commit**

```bash
git add solana/05_rent_model.py
git commit -m "feat(solana): add rent model and exemption calculation"
```

---

### Task 30: solana/06_token_program.py

**Files:**
- Create: `solana/06_token_program.py`

**Step 1: Write the script**

Implement simplified SPL Token program:
- Mint account: supply, decimals, mint_authority, freeze_authority
- Token account: mint (which token), owner, amount
- Instructions: InitializeMint, InitializeAccount, MintTo, Transfer, Burn
- Authority checks: only mint_authority can mint, only owner can transfer
- Demo: create a token (MAGIC), mint 1000 to Alice, Alice transfers 300 to Bob, Bob burns 100

**Step 2: Run and verify**

Run: `python3 solana/06_token_program.py`

**Step 3: Commit**

```bash
git add solana/06_token_program.py
git commit -m "feat(solana): add SPL Token program simulation"
```

---

### Task 31: solana/07_turbine_propagation.py

**Files:**
- Create: `solana/07_turbine_propagation.py`

**Step 1: Write the script**

Implement Turbine block propagation:
- Shredding: split block into fixed-size shreds (data packets)
- Erasure coding: simplified Reed-Solomon — generate recovery shreds so block can be reconstructed from subset
- Tree propagation: organize validators into layers, each layer fans out to next
- Demo: create a block, shred it into 32 data + 32 recovery shreds, simulate tree broadcast to 100 validators, reconstruct block from 60% of shreds

**Step 2: Run and verify**

Run: `python3 solana/07_turbine_propagation.py`

**Step 3: Commit**

```bash
git add solana/07_turbine_propagation.py
git commit -m "feat(solana): add Turbine block propagation with erasure coding"
```

---

### Task 32: solana/08_gulf_stream.py

**Files:**
- Create: `solana/08_gulf_stream.py`

**Step 1: Write the script**

Implement Gulf Stream (mempool-less transaction forwarding):
- Leader schedule: deterministic rotation based on stake and epoch
- Transaction forwarding: clients send txs directly to current + next leaders
- No mempool: transactions go straight to the leader, reducing confirmation latency
- Recent blockhash expiry: transactions expire after ~60 seconds if not included
- Demo: simulate leader schedule for 10 slots, show transaction routing from 5 clients to correct leaders, show expired transaction handling

**Step 2: Run and verify**

Run: `python3 solana/08_gulf_stream.py`

**Step 3: Commit**

```bash
git add solana/08_gulf_stream.py
git commit -m "feat(solana): add Gulf Stream transaction forwarding"
```

---

## Phase 5: README and Polish

### Task 33: README.md

**Files:**
- Create: `README.md`

**Step 1: Write the README**

Structure:
1. Title and tagline: *"Because `web3.sendTransaction()` isn't an explanation."*
2. What This Is — 2-3 sentence description
3. Quick Start — `python3 core/01_hashing.py`
4. Topics table — 4 tables (core, bitcoin, ethereum, solana) with script name, concept, one-line description
5. "See It In Action" section — placeholder for GIFs (will be filled in Phase 6)
6. Prerequisites — Python 3.10+, nothing else
7. Philosophy — zero deps, self-contained, comments-as-docs
8. Contributing — guidelines for adding scripts
9. License — MIT
10. Credits/inspiration — link to no-magic repo

**Step 2: Verify README renders**

Eyeball the markdown structure for correctness.

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with project overview and topic tables"
```

---

### Task 34: Final verification

**Step 1: Run ALL 32 scripts and verify none error out**

```bash
for f in core/*.py bitcoin/*.py ethereum/*.py solana/*.py; do
    echo "=== Running $f ==="
    python3 "$f" || echo "FAILED: $f"
    echo ""
done
```

All 32 must pass with no errors.

**Step 2: Check conventions**

For each script verify:
- Module docstring follows template
- 4 sections present
- Inline comments on non-obvious lines
- No imports outside stdlib
- Visual demo output

**Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: polish scripts after final verification"
```

---

## Parallelization Guide

For subagent-driven execution:

```
Phase 1 (core/):     Tasks 1-8   [SEQUENTIAL — each builds conceptually on prior]
Phase 2 (bitcoin/):  Tasks 9-16  [CAN PARALLEL with Phase 3 and 4]
Phase 3 (ethereum/): Tasks 17-24 [CAN PARALLEL with Phase 2 and 4]
Phase 4 (solana/):   Tasks 25-32 [CAN PARALLEL with Phase 2 and 3]
Phase 5 (README):    Task 33     [AFTER Phases 1-4]
Phase 6 (verify):    Task 34     [LAST]
```

Within each phase, scripts should ideally be built in order (01→08) as later scripts sometimes build on concepts from earlier ones, but they are all self-contained so parallel is possible if needed.
