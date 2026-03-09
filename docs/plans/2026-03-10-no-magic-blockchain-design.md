# no-magic-blockchain — Design Document

**Date:** 2026-03-10
**Status:** Approved

## Vision

A curated collection of single-file, zero-dependency Python implementations of blockchain
algorithms. Follows the same philosophy as [no-magic](https://github.com/Mathews-Tom/no-magic)
for AI — but applied to blockchain technology.

Tagline: *"Because `web3.sendTransaction()` isn't an explanation."*

## Constraints

- Python 3.10+ standard library only (no pip installs)
- Each script self-contained and runnable standalone
- CPU-only, runs in seconds, no network calls
- Heavy inline comments as guided walkthrough

## v1 Scope (branch: v1)

32 scripts across 4 categories:
- `core/` — 8 chain-agnostic fundamentals
- `bitcoin/` — 8 Bitcoin-specific implementations
- `ethereum/` — 8 Ethereum-specific implementations
- `solana/` — 8 Solana-specific implementations

Plus:
- `animations/` — Manim-based visual animations (external dep allowed here only)
- `assets/gifs/` — pre-rendered GIFs for README
- README.md with "See It In Action" GIF grid

## v2 Scope (branch: v2, future)

- Reorganize into tiered sub-folders: `<chain>/fundamentals/`, `intermediate/`, `advanced/`
- Expand to 20+ scripts per chain
- Add chains: Cosmos, Polkadot, Cardano
- Advanced topics: ZK proofs, MEV, sharding, bridges, rollups

## Implementation Order

1. Create repo, v1 branch, CLAUDE.md
2. Build `core/` scripts (01-08) — these are prerequisites for chain-specific scripts
3. Build `bitcoin/`, `ethereum/`, `solana/` in parallel (01-08 each)
4. Write README.md with topic table and descriptions
5. Build Manim animations and render GIFs
6. Add "See It In Action" GIF grid to README

## Full topic list and script specifications

See CLAUDE.md — it contains the complete implementation table with exact
file names, descriptions, and what each script's demo should show.
