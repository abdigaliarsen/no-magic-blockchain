# no-magic-blockchain

> *"Because `web3.sendTransaction()` isn't an explanation."*

Single-file, zero-dependency Python scripts that teach blockchain from scratch.
Every concept is implemented from first principles — no libraries, no hand-waving, no magic.

Inspired by [no-magic](https://github.com/Mathews-Tom/no-magic).

## What This Is

64 self-contained Python scripts across 4 categories that implement blockchain concepts from scratch.
Each script uses **only the Python 3.10+ standard library**, runs in seconds on any machine, and includes
detailed inline comments explaining the *why* behind every decision.

Scripts are organized into three tiers: **fundamentals** (core concepts), **intermediate** (deeper mechanics), and **advanced** (cutting-edge protocols).

## See It In Action

### Core (chain-agnostic fundamentals)

#### Fundamentals

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

#### Intermediate

<table>
<tr>
<td align="center"><strong>Shamir's Secret Sharing</strong><br><a href="core/intermediate/09_shamirs_secret_sharing.py"><img src="assets/gifs/core_09_shamirs_secret_sharing.gif" width="280"></a><br><em>Threshold Cryptography</em></td>
<td align="center"><strong>Bloom Filters</strong><br><a href="core/intermediate/10_bloom_filters.py"><img src="assets/gifs/core_10_bloom_filters.gif" width="280"></a><br><em>Probabilistic Membership</em></td>
<td align="center"><strong>VRFs</strong><br><a href="core/intermediate/11_verifiable_random_functions.py"><img src="assets/gifs/core_11_verifiable_random_functions.gif" width="280"></a><br><em>Provable Randomness</em></td>
</tr>
<tr>
<td align="center"><strong>DHTs (Kademlia)</strong><br><a href="core/intermediate/12_distributed_hash_tables.py"><img src="assets/gifs/core_12_distributed_hash_tables.gif" width="280"></a><br><em>Decentralized Key-Value Store</em></td>
<td></td>
<td></td>
</tr>
</table>

#### Advanced

<table>
<tr>
<td align="center"><strong>Zero-Knowledge Proofs</strong><br><a href="core/advanced/13_zero_knowledge_proofs.py"><img src="assets/gifs/core_13_zero_knowledge_proofs.gif" width="280"></a><br><em>Schnorr & R1CS</em></td>
<td align="center"><strong>BFT Consensus</strong><br><a href="core/advanced/14_bft_consensus.py"><img src="assets/gifs/core_14_bft_consensus.gif" width="280"></a><br><em>PBFT Byzantine Tolerance</em></td>
<td align="center"><strong>Erasure Coding</strong><br><a href="core/advanced/15_erasure_coding.py"><img src="assets/gifs/core_15_erasure_coding.gif" width="280"></a><br><em>Reed-Solomon Recovery</em></td>
</tr>
<tr>
<td align="center"><strong>Optimistic Rollups</strong><br><a href="core/advanced/16_optimistic_rollups.py"><img src="assets/gifs/core_16_optimistic_rollups.gif" width="280"></a><br><em>L2 Fraud Proofs</em></td>
<td></td>
<td></td>
</tr>
</table>

### Bitcoin

#### Fundamentals

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

#### Intermediate

<table>
<tr>
<td align="center"><strong>Schnorr Signatures</strong><br><a href="bitcoin/intermediate/09_schnorr_signatures.py"><img src="assets/gifs/bitcoin_09_schnorr_signatures.gif" width="280"></a><br><em>BIP 340 & MuSig</em></td>
<td align="center"><strong>Taproot & MAST</strong><br><a href="bitcoin/intermediate/10_taproot_mast.py"><img src="assets/gifs/bitcoin_10_taproot_mast.gif" width="280"></a><br><em>Script Trees & Privacy</em></td>
<td align="center"><strong>Compact Blocks</strong><br><a href="bitcoin/intermediate/11_compact_block_relay.py"><img src="assets/gifs/bitcoin_11_compact_block_relay.gif" width="280"></a><br><em>BIP 152 Bandwidth Savings</em></td>
</tr>
<tr>
<td align="center"><strong>Timelocks & HTLCs</strong><br><a href="bitcoin/intermediate/12_timelocks_htlcs.py"><img src="assets/gifs/bitcoin_12_timelocks_htlcs.gif" width="280"></a><br><em>Atomic Swaps</em></td>
<td></td>
<td></td>
</tr>
</table>

#### Advanced

<table>
<tr>
<td align="center"><strong>Covenants</strong><br><a href="bitcoin/advanced/13_covenants.py"><img src="assets/gifs/bitcoin_13_covenants.gif" width="280"></a><br><em>OP_CTV Vaults</em></td>
<td align="center"><strong>Miniscript</strong><br><a href="bitcoin/advanced/14_miniscript_compiler.py"><img src="assets/gifs/bitcoin_14_miniscript_compiler.gif" width="280"></a><br><em>Policy-to-Script Compiler</em></td>
<td align="center"><strong>BitVM</strong><br><a href="bitcoin/advanced/15_simplified_bitvm.py"><img src="assets/gifs/bitcoin_15_simplified_bitvm.gif" width="280"></a><br><em>Fraud Proof Circuits</em></td>
</tr>
<tr>
<td align="center"><strong>Stratum V2</strong><br><a href="bitcoin/advanced/16_stratum_v2.py"><img src="assets/gifs/bitcoin_16_stratum_v2.gif" width="280"></a><br><em>Mining Pool Protocol</em></td>
<td></td>
<td></td>
</tr>
</table>

### Ethereum

#### Fundamentals

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

#### Intermediate

<table>
<tr>
<td align="center"><strong>SSZ Encoding</strong><br><a href="ethereum/intermediate/09_ssz_encoding.py"><img src="assets/gifs/ethereum_09_ssz_encoding.gif" width="280"></a><br><em>Merkleization & Proofs</em></td>
<td align="center"><strong>ERC-20 Tokens</strong><br><a href="ethereum/intermediate/10_erc20_token.py"><img src="assets/gifs/ethereum_10_erc20_token.gif" width="280"></a><br><em>Fungible Token Standard</em></td>
<td align="center"><strong>Blob Transactions</strong><br><a href="ethereum/intermediate/11_blob_transactions.py"><img src="assets/gifs/ethereum_11_blob_transactions.gif" width="280"></a><br><em>EIP-4844 Proto-Danksharding</em></td>
</tr>
<tr>
<td align="center"><strong>Account Abstraction</strong><br><a href="ethereum/intermediate/12_account_abstraction.py"><img src="assets/gifs/ethereum_12_account_abstraction.gif" width="280"></a><br><em>ERC-4337 Smart Wallets</em></td>
<td></td>
<td></td>
</tr>
</table>

#### Advanced

<table>
<tr>
<td align="center"><strong>MEV & Flashbots</strong><br><a href="ethereum/advanced/13_mev_flashbots.py"><img src="assets/gifs/ethereum_13_mev_flashbots.gif" width="280"></a><br><em>Sandwich Attacks & PBS</em></td>
<td align="center"><strong>Verkle Trees</strong><br><a href="ethereum/advanced/14_verkle_trees.py"><img src="assets/gifs/ethereum_14_verkle_trees.gif" width="280"></a><br><em>Stateless Ethereum</em></td>
<td align="center"><strong>EVM Precompiles</strong><br><a href="ethereum/advanced/15_evm_precompiles.py"><img src="assets/gifs/ethereum_15_evm_precompiles.gif" width="280"></a><br><em>Native Crypto Operations</em></td>
</tr>
<tr>
<td align="center"><strong>devp2p Protocol</strong><br><a href="ethereum/advanced/16_devp2p_wire_protocol.py"><img src="assets/gifs/ethereum_16_devp2p_wire_protocol.gif" width="280"></a><br><em>RLPx & eth/68</em></td>
<td></td>
<td></td>
</tr>
</table>

### Solana

#### Fundamentals

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

#### Intermediate

<table>
<tr>
<td align="center"><strong>Tower BFT</strong><br><a href="solana/intermediate/09_tower_bft.py"><img src="assets/gifs/solana_09_tower_bft.gif" width="280"></a><br><em>PoH-Optimized Consensus</em></td>
<td align="center"><strong>Sealevel</strong><br><a href="solana/intermediate/10_sealevel_parallel.py"><img src="assets/gifs/solana_10_sealevel_parallel.gif" width="280"></a><br><em>Parallel Transaction Runtime</em></td>
<td align="center"><strong>Versioned Transactions</strong><br><a href="solana/intermediate/11_versioned_transactions.py"><img src="assets/gifs/solana_11_versioned_transactions.gif" width="280"></a><br><em>Address Lookup Tables</em></td>
</tr>
<tr>
<td align="center"><strong>Stake Economics</strong><br><a href="solana/intermediate/12_stake_economics.py"><img src="assets/gifs/solana_12_stake_economics.gif" width="280"></a><br><em>Inflation & Rewards</em></td>
<td></td>
<td></td>
</tr>
</table>

#### Advanced

<table>
<tr>
<td align="center"><strong>Jito MEV</strong><br><a href="solana/advanced/13_jito_mev_bundles.py"><img src="assets/gifs/solana_13_jito_mev_bundles.gif" width="280"></a><br><em>Bundle Auctions</em></td>
<td align="center"><strong>PDAs & CPIs</strong><br><a href="solana/advanced/14_pdas_cpis_deep.py"><img src="assets/gifs/solana_14_pdas_cpis_deep.gif" width="280"></a><br><em>Program-Derived Addresses</em></td>
<td align="center"><strong>Clockwork</strong><br><a href="solana/advanced/15_clockwork_automation.py"><img src="assets/gifs/solana_15_clockwork_automation.gif" width="280"></a><br><em>On-Chain Automation</em></td>
</tr>
<tr>
<td align="center"><strong>Banking Stage</strong><br><a href="solana/advanced/16_banking_stage.py"><img src="assets/gifs/solana_16_banking_stage.gif" width="280"></a><br><em>TPU Pipeline</em></td>
<td></td>
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

### Core (chain-agnostic)

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
| 09 | `core/intermediate/09_shamirs_secret_sharing.py` | Shamir's secret sharing with Lagrange interpolation |
| 10 | `core/intermediate/10_bloom_filters.py` | Probabilistic membership with false positive analysis |
| 11 | `core/intermediate/11_verifiable_random_functions.py` | EC-based VRF with DLEQ proofs |
| 12 | `core/intermediate/12_distributed_hash_tables.py` | Kademlia DHT with XOR routing |
| 13 | `core/advanced/13_zero_knowledge_proofs.py` | Schnorr sigma protocol and R1CS circuits |
| 14 | `core/advanced/14_bft_consensus.py` | PBFT with Byzantine fault simulation |
| 15 | `core/advanced/15_erasure_coding.py` | Reed-Solomon encode/decode over GF(p) |
| 16 | `core/advanced/16_optimistic_rollups.py` | L2 sequencer with fraud proofs and slashing |

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
| 09 | `bitcoin/intermediate/09_schnorr_signatures.py` | BIP 340 Schnorr with MuSig key aggregation |
| 10 | `bitcoin/intermediate/10_taproot_mast.py` | BIP 341 Taproot with MAST script trees |
| 11 | `bitcoin/intermediate/11_compact_block_relay.py` | BIP 152 compact blocks with SipHash IDs |
| 12 | `bitcoin/intermediate/12_timelocks_htlcs.py` | CLTV/CSV timelocks and cross-chain atomic swaps |
| 13 | `bitcoin/advanced/13_covenants.py` | OP_CTV covenants with vault construction |
| 14 | `bitcoin/advanced/14_miniscript_compiler.py` | Policy AST to Bitcoin Script compiler |
| 15 | `bitcoin/advanced/15_simplified_bitvm.py` | BitVM bit commitments and fraud proofs |
| 16 | `bitcoin/advanced/16_stratum_v2.py` | Mining pool protocol with PPLNS rewards |

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
| 09 | `ethereum/intermediate/09_ssz_encoding.py` | SSZ serialization with Merkleization and proofs |
| 10 | `ethereum/intermediate/10_erc20_token.py` | Complete ERC-20 token standard implementation |
| 11 | `ethereum/intermediate/11_blob_transactions.py` | EIP-4844 proto-danksharding and blob fee market |
| 12 | `ethereum/intermediate/12_account_abstraction.py` | ERC-4337 smart wallets with paymaster |
| 13 | `ethereum/advanced/13_mev_flashbots.py` | MEV extraction, sandwich attacks, PBS |
| 14 | `ethereum/advanced/14_verkle_trees.py` | Verkle trees with Pedersen commitments |
| 15 | `ethereum/advanced/15_evm_precompiles.py` | All 9 EVM precompiled contracts |
| 16 | `ethereum/advanced/16_devp2p_wire_protocol.py` | RLPx framing and eth/68 messages |

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
| 09 | `solana/intermediate/09_tower_bft.py` | Tower BFT with vote lockouts and fork choice |
| 10 | `solana/intermediate/10_sealevel_parallel.py` | Parallel runtime with conflict detection |
| 11 | `solana/intermediate/11_versioned_transactions.py` | v0 transactions with Address Lookup Tables |
| 12 | `solana/intermediate/12_stake_economics.py` | Inflation schedule and validator rewards |
| 13 | `solana/advanced/13_jito_mev_bundles.py` | Jito bundle auctions and tip distribution |
| 14 | `solana/advanced/14_pdas_cpis_deep.py` | PDA derivation and CPI with signer seeds |
| 15 | `solana/advanced/15_clockwork_automation.py` | On-chain cron jobs with trigger conditions |
| 16 | `solana/advanced/16_banking_stage.py` | TPU pipeline and multi-threaded banking |

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
then explore any chain folder that interests you. Within each chain, follow the tiers:

1. **Fundamentals** (01-08) — core protocol concepts
2. **Intermediate** (09-12) — deeper protocol mechanics
3. **Advanced** (13-16) — cutting-edge features and research topics

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
