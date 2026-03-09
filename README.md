# no-magic-blockchain

> *"Because `web3.sendTransaction()` isn't an explanation."*

Single-file, zero-dependency Python scripts that teach blockchain from scratch.
Every concept is implemented from first principles — no libraries, no hand-waving, no magic.

Inspired by [no-magic](https://github.com/Mathews-Tom/no-magic).

## What This Is

32 self-contained Python scripts across 4 categories that implement blockchain concepts from scratch.
Each script uses **only the Python 3.10+ standard library**, runs in seconds on any machine, and includes
detailed inline comments explaining the *why* behind every decision.

## See It In Action

<table>
<tr>
<td align="center"><strong>SHA-256 From Scratch</strong><br><a href="core/01_hashing.py"><img src="assets/gifs/core_01_hashing.gif" width="400"></a></td>
<td align="center"><strong>Blockchain & Tamper Detection</strong><br><a href="core/05_blockchain.py"><img src="assets/gifs/core_05_blockchain.gif" width="400"></a></td>
</tr>
<tr>
<td align="center"><strong>Proof-of-Work Mining</strong><br><a href="core/06_consensus_pow.py"><img src="assets/gifs/core_06_consensus_pow.gif" width="400"></a></td>
<td align="center"><strong>EVM Bytecode Interpreter</strong><br><a href="ethereum/02_evm_bytecode.py"><img src="assets/gifs/ethereum_02_evm_bytecode.gif" width="400"></a></td>
</tr>
<tr>
<td align="center"><strong>Bitcoin Script VM</strong><br><a href="bitcoin/02_bitcoin_script.py"><img src="assets/gifs/bitcoin_02_bitcoin_script.gif" width="400"></a></td>
<td align="center"><strong>Proof of History</strong><br><a href="solana/02_proof_of_history.py"><img src="assets/gifs/solana_02_proof_of_history.gif" width="400"></a></td>
</tr>
</table>

> Every script produces visual, step-by-step output like these. Just run `python3 <script>.py`.

## Quick Start

```bash
# No setup needed — just Python 3.10+
python3 core/01_hashing.py
python3 bitcoin/01_utxo_model.py
python3 ethereum/02_evm_bytecode.py
python3 solana/02_proof_of_history.py
```

## Topics

### Core (chain-agnostic fundamentals)

| # | Script | Concept |
|---|--------|---------|
| 01 | `core/01_hashing.py` | SHA-256 from scratch with avalanche effect demo |
| 02 | `core/02_public_key_crypto.py` | Elliptic curve math on secp256k1 |
| 03 | `core/03_digital_signatures.py` | ECDSA sign/verify with tamper detection |
| 04 | `core/04_merkle_trees.py` | Binary hash trees with inclusion proofs |
| 05 | `core/05_blockchain.py` | Block structure, chain linking, tamper detection |
| 06 | `core/06_consensus_pow.py` | Proof-of-work mining with difficulty adjustment |
| 07 | `core/07_consensus_pos.py` | Proof-of-stake with validator selection and slashing |
| 08 | `core/08_p2p_network.py` | Gossip protocol simulation with fork resolution |

### Bitcoin

| # | Script | Concept |
|---|--------|---------|
| 01 | `bitcoin/01_utxo_model.py` | UTXO set, transaction chaining, change outputs |
| 02 | `bitcoin/02_bitcoin_script.py` | Stack-based Script VM with P2PKH evaluation |
| 03 | `bitcoin/03_mining.py` | Coinbase tx, Merkle root, double-SHA-256 mining |
| 04 | `bitcoin/04_spv_verification.py` | Lightweight verification with Merkle proofs |
| 05 | `bitcoin/05_wallets_hd.py` | BIP-32 HD wallets with key derivation paths |
| 06 | `bitcoin/06_segwit.py` | Segregated Witness and malleability fix |
| 07 | `bitcoin/07_difficulty_adjustment.py` | Retarget algorithm with 4x clamp |
| 08 | `bitcoin/08_simplified_lightning.py` | Payment channels, HTLCs, multi-hop routing |

### Ethereum

| # | Script | Concept |
|---|--------|---------|
| 01 | `ethereum/01_accounts_state.py` | Account model, world state, state transitions |
| 02 | `ethereum/02_evm_bytecode.py` | EVM stack machine with 27+ opcodes |
| 03 | `ethereum/03_gas_execution.py` | Gas metering and EIP-1559 base fee |
| 04 | `ethereum/04_rlp_encoding.py` | RLP encode/decode with round-trip verification |
| 05 | `ethereum/05_merkle_patricia_trie.py` | Modified Merkle Patricia Trie with proofs |
| 06 | `ethereum/06_smart_contracts.py` | Contract deploy, call, and storage lifecycle |
| 07 | `ethereum/07_pos_beacon.py` | Beacon chain with Casper FFG finality |
| 08 | `ethereum/08_abi_encoding.py` | ABI encoding for function calls and data |

### Solana

| # | Script | Concept |
|---|--------|---------|
| 01 | `solana/01_accounts_model.py` | Account structure, ownership rules, PDAs |
| 02 | `solana/02_proof_of_history.py` | Sequential SHA-256 as verifiable delay function |
| 03 | `solana/03_programs.py` | Stateless programs with cross-program invocation |
| 04 | `solana/04_transactions.py` | Transaction format, serialization, signing |
| 05 | `solana/05_rent_model.py` | Rent exemption and epoch-based rent collection |
| 06 | `solana/06_token_program.py` | SPL Token: mint, transfer, burn |
| 07 | `solana/07_turbine_propagation.py` | Block shredding with erasure coding |
| 08 | `solana/08_gulf_stream.py` | Mempool-less transaction forwarding |

## Prerequisites

- Python 3.10 or later
- That's it. No `pip install`, no virtual environments, no Docker.

## Philosophy

- **Zero dependencies** — every script uses only the Python standard library
- **Self-contained** — each file stands alone, no imports between scripts
- **Comments as docs** — inline comments explain *why*, not just *what*
- **Visual output** — box-drawing characters, formatted tables, step-by-step traces
- **Runs anywhere** — no network, no GPU, no setup, just `python3 script.py`

## Learning Path

Start with `core/` scripts in order (01-08) to build foundational understanding,
then explore any chain folder that interests you. Each chain's scripts are numbered
in suggested reading order.

## Contributing

To add a new script:

1. Follow the template in `CLAUDE.md` exactly (docstring, 4 sections, comment style)
2. Use only Python 3.10+ stdlib — no external packages
3. Ensure it runs standalone in under 30 seconds
4. Include visual demo output with formatted display

## License

MIT

## Credits

Inspired by [no-magic](https://github.com/Mathews-Tom/no-magic) — the idea that you truly understand
something only when you can build it from scratch.
