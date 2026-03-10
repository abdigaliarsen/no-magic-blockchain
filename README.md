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

### Core (chain-agnostic fundamentals)

<table>
<tr>
<td align="center"><strong>SHA-256 Hashing</strong><br><a href="core/fundamentals/01_hashing.py"><img src="assets/gifs/core_01_hashing.gif" width="280"></a><br><em>Hashing & Avalanche Effect</em></td>
<td align="center"><strong>Public Key Crypto</strong><br><a href="core/fundamentals/02_public_key_crypto.py"><img src="assets/gifs/core_02_public_key_crypto.gif" width="280"></a><br><em>Elliptic Curve Key Generation</em></td>
<td align="center"><strong>Digital Signatures</strong><br><a href="core/fundamentals/03_digital_signatures.py"><img src="assets/gifs/core_03_digital_signatures.gif" width="280"></a><br><em>ECDSA Tamper Detection</em></td>
</tr>
<tr>
<td align="center"><strong>Merkle Trees</strong><br><a href="core/fundamentals/04_merkle_trees.py"><img src="assets/gifs/core_04_merkle_trees.gif" width="280"></a><br><em>Binary Hash Trees & Proofs</em></td>
<td align="center"><strong>The Blockchain</strong><br><a href="core/fundamentals/05_blockchain.py"><img src="assets/gifs/core_05_blockchain.gif" width="280"></a><br><em>Blocks Linked by Hashes</em></td>
<td align="center"><strong>Proof of Work</strong><br><a href="core/fundamentals/06_consensus_pow.py"><img src="assets/gifs/core_06_consensus_pow.gif" width="280"></a><br><em>Difficulty Adjustment</em></td>
</tr>
<tr>
<td align="center"><strong>Proof of Stake</strong><br><a href="core/fundamentals/07_consensus_pos.py"><img src="assets/gifs/core_07_consensus_pos.gif" width="280"></a><br><em>Rewards & Slashing</em></td>
<td align="center"><strong>P2P Network</strong><br><a href="core/fundamentals/08_p2p_network.py"><img src="assets/gifs/core_08_p2p_network.gif" width="280"></a><br><em>Gossip Propagation</em></td>
<td></td>
</tr>
</table>

### Bitcoin

<table>
<tr>
<td align="center"><strong>UTXO Model</strong><br><a href="bitcoin/fundamentals/01_utxo_model.py"><img src="assets/gifs/bitcoin_01_utxo_model.gif" width="280"></a><br><em>Inputs, Outputs & Change</em></td>
<td align="center"><strong>Bitcoin Script</strong><br><a href="bitcoin/fundamentals/02_bitcoin_script.py"><img src="assets/gifs/bitcoin_02_bitcoin_script.gif" width="280"></a><br><em>Lock & Unlock</em></td>
<td align="center"><strong>Mining</strong><br><a href="bitcoin/fundamentals/03_mining.py"><img src="assets/gifs/bitcoin_03_mining.gif" width="280"></a><br><em>Block Assembly</em></td>
</tr>
<tr>
<td align="center"><strong>SPV Verification</strong><br><a href="bitcoin/fundamentals/04_spv_verification.py"><img src="assets/gifs/bitcoin_04_spv_verification.gif" width="280"></a><br><em>Full Node vs Light Client</em></td>
<td align="center"><strong>HD Wallets</strong><br><a href="bitcoin/fundamentals/05_wallets_hd.py"><img src="assets/gifs/bitcoin_05_wallets_hd.gif" width="280"></a><br><em>BIP-32 Derivation Paths</em></td>
<td align="center"><strong>SegWit</strong><br><a href="bitcoin/fundamentals/06_segwit.py"><img src="assets/gifs/bitcoin_06_segwit.gif" width="280"></a><br><em>The Malleability Fix</em></td>
</tr>
<tr>
<td align="center"><strong>Difficulty Adjustment</strong><br><a href="bitcoin/fundamentals/07_difficulty_adjustment.py"><img src="assets/gifs/bitcoin_07_difficulty_adjustment.gif" width="280"></a><br><em>The Thermostat</em></td>
<td align="center"><strong>Lightning Network</strong><br><a href="bitcoin/fundamentals/08_simplified_lightning.py"><img src="assets/gifs/bitcoin_08_simplified_lightning.gif" width="280"></a><br><em>Payment Channels</em></td>
<td></td>
</tr>
</table>

### Ethereum

<table>
<tr>
<td align="center"><strong>Accounts & State</strong><br><a href="ethereum/fundamentals/01_accounts_state.py"><img src="assets/gifs/ethereum_01_accounts_state.gif" width="280"></a><br><em>World State Transitions</em></td>
<td align="center"><strong>EVM Architecture</strong><br><a href="ethereum/fundamentals/02_evm_bytecode.py"><img src="assets/gifs/ethereum_02_evm_bytecode.gif" width="280"></a><br><em>Stack, Memory & Storage</em></td>
<td align="center"><strong>EIP-1559 Gas</strong><br><a href="ethereum/fundamentals/03_gas_execution.py"><img src="assets/gifs/ethereum_03_gas_execution.gif" width="280"></a><br><em>Base Fee & Block Fullness</em></td>
</tr>
<tr>
<td align="center"><strong>RLP Encoding</strong><br><a href="ethereum/fundamentals/04_rlp_encoding.py"><img src="assets/gifs/ethereum_04_rlp_encoding.gif" width="280"></a><br><em>Nested Structure</em></td>
<td align="center"><strong>Merkle Patricia Trie</strong><br><a href="ethereum/fundamentals/05_merkle_patricia_trie.py"><img src="assets/gifs/ethereum_05_merkle_patricia_trie.gif" width="280"></a><br><em>Trie Path Routing</em></td>
<td align="center"><strong>Smart Contracts</strong><br><a href="ethereum/fundamentals/06_smart_contracts.py"><img src="assets/gifs/ethereum_06_smart_contracts.gif" width="280"></a><br><em>Deploy vs Call</em></td>
</tr>
<tr>
<td align="center"><strong>Casper FFG</strong><br><a href="ethereum/fundamentals/07_pos_beacon.py"><img src="assets/gifs/ethereum_07_pos_beacon.gif" width="280"></a><br><em>Beacon Chain Finality</em></td>
<td align="center"><strong>ABI Encoding</strong><br><a href="ethereum/fundamentals/08_abi_encoding.py"><img src="assets/gifs/ethereum_08_abi_encoding.gif" width="280"></a><br><em>Function Selectors & Calldata</em></td>
<td></td>
</tr>
</table>

### Solana

<table>
<tr>
<td align="center"><strong>Account Model</strong><br><a href="solana/fundamentals/01_accounts_model.py"><img src="assets/gifs/solana_01_accounts_model.gif" width="280"></a><br><em>Wallet vs Program Account</em></td>
<td align="center"><strong>Proof of History</strong><br><a href="solana/fundamentals/02_proof_of_history.py"><img src="assets/gifs/solana_02_proof_of_history.gif" width="280"></a><br><em>Event Ordering</em></td>
<td align="center"><strong>Program Model</strong><br><a href="solana/fundamentals/03_programs.py"><img src="assets/gifs/solana_03_programs.gif" width="280"></a><br><em>Solana vs Ethereum</em></td>
</tr>
<tr>
<td align="center"><strong>Transactions</strong><br><a href="solana/fundamentals/04_transactions.py"><img src="assets/gifs/solana_04_transactions.gif" width="280"></a><br><em>Anatomy & Signing</em></td>
<td align="center"><strong>Rent Model</strong><br><a href="solana/fundamentals/05_rent_model.py"><img src="assets/gifs/solana_05_rent_model.gif" width="280"></a><br><em>Pay Rent or Die</em></td>
<td align="center"><strong>SPL Tokens</strong><br><a href="solana/fundamentals/06_token_program.py"><img src="assets/gifs/solana_06_token_program.gif" width="280"></a><br><em>Mint, Transfer & Burn</em></td>
</tr>
<tr>
<td align="center"><strong>Turbine</strong><br><a href="solana/fundamentals/07_turbine_propagation.py"><img src="assets/gifs/solana_07_turbine_propagation.gif" width="280"></a><br><em>Broadcast vs Tree Propagation</em></td>
<td align="center"><strong>Gulf Stream</strong><br><a href="solana/fundamentals/08_gulf_stream.py"><img src="assets/gifs/solana_08_gulf_stream.gif" width="280"></a><br><em>Leader Schedule Pipeline</em></td>
<td></td>
</tr>
</table>

## Quick Start

```bash
# No setup needed — just Python 3.10+
python3 core/fundamentals/01_hashing.py
python3 bitcoin/fundamentals/01_utxo_model.py
python3 ethereum/fundamentals/02_evm_bytecode.py
python3 solana/fundamentals/02_proof_of_history.py
```

## Topics

### Core (chain-agnostic fundamentals)

| # | Script | Concept |
|---|--------|---------|
| 01 | `core/fundamentals/01_hashing.py` | SHA-256 from scratch with avalanche effect demo |
| 02 | `core/fundamentals/02_public_key_crypto.py` | Elliptic curve math on secp256k1 |
| 03 | `core/fundamentals/03_digital_signatures.py` | ECDSA sign/verify with tamper detection |
| 04 | `core/fundamentals/04_merkle_trees.py` | Binary hash trees with inclusion proofs |
| 05 | `core/fundamentals/05_blockchain.py` | Block structure, chain linking, tamper detection |
| 06 | `core/fundamentals/06_consensus_pow.py` | Proof-of-work mining with difficulty adjustment |
| 07 | `core/fundamentals/07_consensus_pos.py` | Proof-of-stake with validator selection and slashing |
| 08 | `core/fundamentals/08_p2p_network.py` | Gossip protocol simulation with fork resolution |

### Bitcoin

| # | Script | Concept |
|---|--------|---------|
| 01 | `bitcoin/fundamentals/01_utxo_model.py` | UTXO set, transaction chaining, change outputs |
| 02 | `bitcoin/fundamentals/02_bitcoin_script.py` | Stack-based Script VM with P2PKH evaluation |
| 03 | `bitcoin/fundamentals/03_mining.py` | Coinbase tx, Merkle root, double-SHA-256 mining |
| 04 | `bitcoin/fundamentals/04_spv_verification.py` | Lightweight verification with Merkle proofs |
| 05 | `bitcoin/fundamentals/05_wallets_hd.py` | BIP-32 HD wallets with key derivation paths |
| 06 | `bitcoin/fundamentals/06_segwit.py` | Segregated Witness and malleability fix |
| 07 | `bitcoin/fundamentals/07_difficulty_adjustment.py` | Retarget algorithm with 4x clamp |
| 08 | `bitcoin/fundamentals/08_simplified_lightning.py` | Payment channels, HTLCs, multi-hop routing |

### Ethereum

| # | Script | Concept |
|---|--------|---------|
| 01 | `ethereum/fundamentals/01_accounts_state.py` | Account model, world state, state transitions |
| 02 | `ethereum/fundamentals/02_evm_bytecode.py` | EVM stack machine with 27+ opcodes |
| 03 | `ethereum/fundamentals/03_gas_execution.py` | Gas metering and EIP-1559 base fee |
| 04 | `ethereum/fundamentals/04_rlp_encoding.py` | RLP encode/decode with round-trip verification |
| 05 | `ethereum/fundamentals/05_merkle_patricia_trie.py` | Modified Merkle Patricia Trie with proofs |
| 06 | `ethereum/fundamentals/06_smart_contracts.py` | Contract deploy, call, and storage lifecycle |
| 07 | `ethereum/fundamentals/07_pos_beacon.py` | Beacon chain with Casper FFG finality |
| 08 | `ethereum/fundamentals/08_abi_encoding.py` | ABI encoding for function calls and data |

### Solana

| # | Script | Concept |
|---|--------|---------|
| 01 | `solana/fundamentals/01_accounts_model.py` | Account structure, ownership rules, PDAs |
| 02 | `solana/fundamentals/02_proof_of_history.py` | Sequential SHA-256 as verifiable delay function |
| 03 | `solana/fundamentals/03_programs.py` | Stateless programs with cross-program invocation |
| 04 | `solana/fundamentals/04_transactions.py` | Transaction format, serialization, signing |
| 05 | `solana/fundamentals/05_rent_model.py` | Rent exemption and epoch-based rent collection |
| 06 | `solana/fundamentals/06_token_program.py` | SPL Token: mint, transfer, burn |
| 07 | `solana/fundamentals/07_turbine_propagation.py` | Block shredding with erasure coding |
| 08 | `solana/fundamentals/08_gulf_stream.py` | Mempool-less transaction forwarding |

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

Start with `core/fundamentals/` scripts in order (01-08) to build foundational understanding,
then explore any chain folder that interests you. Each chain's scripts are numbered
in suggested reading order within each tier (fundamentals → intermediate → advanced).

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
