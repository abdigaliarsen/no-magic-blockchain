# v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand from 32 to 64 scripts with tiered sub-folders, 32 new GIFs, and updated README.

**Architecture:** Create v2 branch, reorganize existing scripts into fundamentals/ tiers, build 32 new intermediate+advanced scripts with paired GIF animations, update README grid.

**Tech Stack:** Python 3.10+ stdlib only (scripts), Pillow (GIFs only), git

---

## Phase 0: Branch & Reorganize

### Task 0.1: Create v2 branch

**Step 1:** Create and switch to v2 branch
```bash
git checkout -b v2
```

**Step 2:** Push branch
```bash
git push -u origin v2
```

### Task 0.2: Reorganize existing scripts into fundamentals/

**Files to move (32 scripts):**
- `core/01_*.py` through `core/08_*.py` → `core/fundamentals/01_*.py` through `08_*.py`
- `bitcoin/01_*.py` through `bitcoin/08_*.py` → `bitcoin/fundamentals/01_*.py` through `08_*.py`
- `ethereum/01_*.py` through `ethereum/08_*.py` → `ethereum/fundamentals/01_*.py` through `08_*.py`
- `solana/01_*.py` through `solana/08_*.py` → `solana/fundamentals/01_*.py` through `08_*.py`

**Step 1:** Create directories
```bash
mkdir -p core/fundamentals core/intermediate core/advanced
mkdir -p bitcoin/fundamentals bitcoin/intermediate bitcoin/advanced
mkdir -p ethereum/fundamentals ethereum/intermediate ethereum/advanced
mkdir -p solana/fundamentals solana/intermediate solana/advanced
```

**Step 2:** Move scripts (use git mv to preserve history)
```bash
for chain in core bitcoin ethereum solana; do
  git mv $chain/[0-9]*.py $chain/fundamentals/
done
```

**Step 3:** Verify all scripts still run
```bash
for f in */fundamentals/*.py; do python3 "$f" > /dev/null && echo "OK: $f" || echo "FAIL: $f"; done
```

**Step 4:** Update animation output paths — animations still save to `assets/gifs/` (no change needed, they use relative paths from repo root)

**Step 5:** Update README.md — all script links now point to `<chain>/fundamentals/NN_topic.py`

**Step 6:** Update CLAUDE.md — reflect new directory structure

**Step 7:** Commit
```bash
git add -A
git commit -m "refactor: reorganize existing scripts into fundamentals/ sub-folders"
```

---

## Phase 1: Core — Intermediate & Advanced (8 scripts + 8 GIFs)

### Task 1.1: Write core/intermediate/ scripts (4 parallel)

Each script MUST follow the template in CLAUDE.md exactly:
- Module docstring (TITLE, CATEGORY, WHAT, KEY CONCEPTS, PREREQUISITES, RELEVANCE)
- Section 1: Constants
- Section 2: Implementation
- Section 3: Demo with visual output
- Section 4: Entry point

**Scripts to create:**

| File | Topic | Key implementation |
|------|-------|--------------------|
| `core/intermediate/09_shamirs_secret_sharing.py` | Shamir's Secret Sharing | Polynomial eval over GF(p), Lagrange interpolation, split(secret,n,k), reconstruct(shares) |
| `core/intermediate/10_bloom_filters.py` | Bloom Filters | Bit array, multiple hash functions, insert/query, false positive rate measurement |
| `core/intermediate/11_verifiable_random_functions.py` | VRFs | EC-based VRF: prove(sk,input)→(output,proof), verify(pk,input,output,proof) |
| `core/intermediate/12_distributed_hash_tables.py` | DHTs (Kademlia) | XOR distance, k-buckets, iterative lookup, key-value store/retrieve over simulated 50-node network |

**Verification:** `python3 core/intermediate/09_*.py` runs with visual demo output, under 30 seconds.

### Task 1.2: Write core/advanced/ scripts (4 parallel)

| File | Topic | Key implementation |
|------|-------|--------------------|
| `core/advanced/13_zero_knowledge_proofs.py` | ZK Proofs | Schnorr sigma protocol + simplified R1CS circuit satisfiability |
| `core/advanced/14_bft_consensus.py` | PBFT | Pre-prepare/prepare/commit, 3f+1 nodes, Byzantine fault simulation |
| `core/advanced/15_erasure_coding.py` | Reed-Solomon | Polynomial evaluation + Lagrange interpolation over GF(p), encode/decode/reconstruct |
| `core/advanced/16_optimistic_rollups.py` | Optimistic Rollups | L2 sequencer, state root posting, challenge window, fraud proof |

### Task 1.3: Generate 8 core GIFs

Use the judge system: 3 variants per concept, pick best.
- Create `animations/core_09_shamirs_secret_sharing.py` through `animations/core_16_optimistic_rollups.py`
- Output to `assets/gifs/core_09_*.gif` through `assets/gifs/core_16_*.gif`
- Specs: 800x550, 36 frames, 90ms, standard color palette, Pillow only

### Task 1.4: Audit core batch

Run the gif-audit-workflow (see memory/gif-audit-workflow.md):
- Visual audit of 8 GIFs
- Code review of 8 animation scripts
- Cross-reference against research
- Fix issues, regenerate

### Task 1.5: Commit core batch
```bash
git add core/intermediate/ core/advanced/ animations/core_09_* animations/core_1[0-6]_* assets/gifs/core_09_* assets/gifs/core_1[0-6]_*
git commit -m "feat: add 8 intermediate+advanced core scripts with GIFs"
```

---

## Phase 2: Bitcoin — Intermediate & Advanced (8 scripts + 8 GIFs)

### Task 2.1: Write bitcoin/intermediate/ scripts (4 parallel)

| File | Topic | Key implementation |
|------|-------|--------------------|
| `bitcoin/intermediate/09_schnorr_signatures.py` | Schnorr (BIP 340) | Sign/verify over secp256k1, MuSig key aggregation |
| `bitcoin/intermediate/10_taproot_mast.py` | Taproot (BIP 341) | MAST construction, key-path spend, script-path spend + Merkle proof |
| `bitcoin/intermediate/11_compact_block_relay.py` | Compact Blocks (BIP 152) | SipHash short IDs, mempool reconstruction, bandwidth savings |
| `bitcoin/intermediate/12_timelocks_htlcs.py` | Timelocks & HTLCs | CLTV, CSV opcodes, cross-chain atomic swap demo |

### Task 2.2: Write bitcoin/advanced/ scripts (4 parallel)

| File | Topic | Key implementation |
|------|-------|--------------------|
| `bitcoin/advanced/13_covenants.py` | Covenants (OP_CTV) | CheckTemplateVerify, vault construct, 2-step withdrawal |
| `bitcoin/advanced/14_miniscript_compiler.py` | Miniscript | Policy AST → Script compilation, witness cost analysis |
| `bitcoin/advanced/15_simplified_bitvm.py` | BitVM | Bit commitments, NAND gates, bisection fraud proof |
| `bitcoin/advanced/16_stratum_v2.py` | Stratum V2 | Job negotiation, template selection, PPLNS rewards |

### Task 2.3: Generate 8 Bitcoin GIFs (judge system)

### Task 2.4: Audit Bitcoin batch

### Task 2.5: Commit Bitcoin batch

---

## Phase 3: Ethereum — Intermediate & Advanced (8 scripts + 8 GIFs)

### Task 3.1: Write ethereum/intermediate/ scripts (4 parallel)

| File | Topic | Key implementation |
|------|-------|--------------------|
| `ethereum/intermediate/09_ssz_encoding.py` | SSZ | Serialize/deserialize, Merkleization, hash tree root, generalized index proofs |
| `ethereum/intermediate/10_erc20_token.py` | ERC-20 | Full token on v1 EVM: totalSupply, balanceOf, transfer, approve, transferFrom |
| `ethereum/intermediate/11_blob_transactions.py` | EIP-4844 | Type-3 tx structure, KZG commitment simulation, blob fee market |
| `ethereum/intermediate/12_account_abstraction.py` | ERC-4337 | UserOperation, EntryPoint, Paymaster, social recovery |

### Task 3.2: Write ethereum/advanced/ scripts (4 parallel)

| File | Topic | Key implementation |
|------|-------|--------------------|
| `ethereum/advanced/13_mev_flashbots.py` | MEV & PBS | Mempool, searcher bots, sandwich attack, proposer-builder separation |
| `ethereum/advanced/14_verkle_trees.py` | Verkle Trees | Vector commitments, polynomial evaluation, multiproof generation |
| `ethereum/advanced/15_evm_precompiles.py` | Precompiles | ecRecover, SHA-256, modexp, bn128 add/mul — integrated with EVM |
| `ethereum/advanced/16_devp2p_wire_protocol.py` | Devp2p | ECIES handshake, AES-CTR encryption, eth/68 protocol |

### Task 3.3: Generate 8 Ethereum GIFs (judge system)

### Task 3.4: Audit Ethereum batch

### Task 3.5: Commit Ethereum batch

---

## Phase 4: Solana — Intermediate & Advanced (8 scripts + 8 GIFs)

### Task 4.1: Write solana/intermediate/ scripts (4 parallel)

| File | Topic | Key implementation |
|------|-------|--------------------|
| `solana/intermediate/09_tower_bft.py` | Tower BFT | Vote lockout (exponential), fork choice, rollback cost, finality |
| `solana/intermediate/10_sealevel_parallel.py` | Sealevel | Account access lists, dependency graph, parallel scheduling |
| `solana/intermediate/11_versioned_transactions.py` | Versioned Txs | Address Lookup Tables, v0 format, index-based references |
| `solana/intermediate/12_stake_economics.py` | Stake & Rewards | Inflation schedule, commission, epoch rewards, slashing |

### Task 4.2: Write solana/advanced/ scripts (4 parallel)

| File | Topic | Key implementation |
|------|-------|--------------------|
| `solana/advanced/13_jito_mev_bundles.py` | Jito MEV | AMM arbitrage, tip auction, atomic bundle execution |
| `solana/advanced/14_pdas_cpis_deep.py` | PDAs & CPIs | AMM with pool PDA, multi-program CPI chain |
| `solana/advanced/15_clockwork_automation.py` | Clockwork | Trigger system, auto-compounding vault, scheduled execution |
| `solana/advanced/16_banking_stage.py` | Banking Stage | Fetch→sigverify→banking→broadcast pipeline |

### Task 4.3: Generate 8 Solana GIFs (judge system)

### Task 4.4: Audit Solana batch

### Task 4.5: Commit Solana batch

---

## Phase 5: README & Final Polish

### Task 5.1: Update README.md

Expand the 3-column grid to include 3 sections per chain:
- Fundamentals (existing 8)
- Intermediate (new 4)
- Advanced (new 4)

### Task 5.2: Update CLAUDE.md

Add all 32 new scripts to the implementation table with full descriptions.

### Task 5.3: Final verification

```bash
# All 64 scripts run without errors
for f in */fundamentals/*.py */intermediate/*.py */advanced/*.py; do
  python3 "$f" > /dev/null 2>&1 && echo "OK: $f" || echo "FAIL: $f"
done

# All 64 GIFs exist
ls assets/gifs/*.gif | wc -l  # should be 64
```

### Task 5.4: Final commit and push
```bash
git add -A
git commit -m "docs: update README and CLAUDE.md for v2 expansion"
git push origin v2
```
