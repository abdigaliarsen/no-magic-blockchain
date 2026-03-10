"""
TITLE: Simple Serialize (SSZ)
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    Ethereum's Simple Serialize (SSZ) encoding from scratch — the serialization
    format used by the Consensus Layer (Beacon Chain). Covers fixed-size types
    (bool, uint8/16/32/64/256), variable-size types (bytes, lists), containers,
    Merkleization (hash tree roots), and generalized-index proofs.

KEY CONCEPTS:
    - Fixed-size vs variable-size serialization with offset pointers
    - Merkleization: pad chunks to next power of 2, build binary hash tree
    - Hash tree root: a single 32-byte commitment to any SSZ object
    - Generalized indices: navigate the Merkle tree to prove specific fields

PREREQUISITE SCRIPTS:
    - core/fundamentals/01_hashing.py (hashing fundamentals)
    - ethereum/fundamentals/04_rlp_encoding.py (contrast with RLP)
    - ethereum/fundamentals/07_pos_beacon.py (Beacon Chain context)

REAL-WORLD RELEVANCE:
    SSZ replaced RLP for all Consensus Layer data structures in Ethereum 2.0.
    Every beacon block, attestation, validator record, and state snapshot is
    SSZ-encoded. Light clients use Merkleization proofs to verify specific
    fields without downloading the full state.
"""

import hashlib  # SHA-256 for Merkleization (stand-in for SHA-256 used in real SSZ)
import struct   # For packing integers into little-endian bytes
import math     # For log2, ceil

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# SSZ uses 32-byte chunks as the leaf size for Merkleization
BYTES_PER_CHUNK = 32

# The number of bytes used for offset pointers to variable-length fields
BYTES_PER_LENGTH_OFFSET = 4

# Zero hash — used to pad Merkle trees to a power of 2
ZERO_HASH = b'\x00' * BYTES_PER_CHUNK

# Maximum display width for hex strings in demo output
HEX_DISPLAY = 16


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Hashing ----------------------------------------------------------------

def sha256(data: bytes) -> bytes:
    """SHA-256 hash. Real SSZ also uses SHA-256 for Merkleization."""
    return hashlib.sha256(data).digest()


# --- Basic type serialization ----------------------------------------------

def serialize_bool(value: bool) -> bytes:
    """Serialize a boolean: 0x01 for True, 0x00 for False."""
    return b'\x01' if value else b'\x00'


def deserialize_bool(data: bytes) -> bool:
    """Deserialize a boolean from a single byte."""
    if data[0] == 0x01:
        return True
    elif data[0] == 0x00:
        return False
    raise ValueError(f"Invalid bool byte: 0x{data[0]:02x}")


def serialize_uint(value: int, byte_length: int) -> bytes:
    """Serialize an unsigned integer as little-endian bytes.

    SSZ uses little-endian (unlike RLP's big-endian). This is because
    the Beacon Chain targets efficient proof generation, and little-endian
    makes certain bit-level operations more natural.
    """
    if value < 0:
        raise ValueError("SSZ uints must be non-negative")
    if value >= (1 << (byte_length * 8)):
        raise ValueError(f"Value {value} too large for uint{byte_length * 8}")
    return value.to_bytes(byte_length, byteorder='little')


def deserialize_uint(data: bytes, byte_length: int) -> int:
    """Deserialize a little-endian unsigned integer."""
    return int.from_bytes(data[:byte_length], byteorder='little')


# --- Variable-size serialization --------------------------------------------

def serialize_bytes(data: bytes) -> bytes:
    """Serialize a variable-length byte string.

    In SSZ, variable-length bytes are just the raw bytes themselves
    (the length is tracked via offset pointers in the container).
    """
    return data  # Length is implicit from context/offsets


def serialize_list(items: list, item_serialize_fn, item_size: int | None) -> bytes:
    """Serialize a list of items.

    Fixed-size items: concatenate serialized forms directly.
    Variable-size items: use offset table + concatenated data.
    """
    if item_size is not None:
        # Fixed-size elements — just concatenate
        return b''.join(item_serialize_fn(item) for item in items)
    else:
        # Variable-size elements — build offset table then data
        serialized_items = [item_serialize_fn(item) for item in items]
        # Offsets start after the offset table itself
        offset_start = len(items) * BYTES_PER_LENGTH_OFFSET
        offsets = []
        current_offset = offset_start
        for s in serialized_items:
            offsets.append(serialize_uint(current_offset, BYTES_PER_LENGTH_OFFSET))
            current_offset += len(s)
        return b''.join(offsets) + b''.join(serialized_items)


# --- Container serialization -----------------------------------------------

class SSZType:
    """Descriptor for an SSZ type."""

    def __init__(self, name: str, fixed_size: int | None = None):
        self.name = name
        # fixed_size is None for variable-size types
        self.fixed_size = fixed_size

    def is_fixed(self) -> bool:
        return self.fixed_size is not None


# Pre-defined types
BOOL_TYPE = SSZType("bool", fixed_size=1)
UINT8_TYPE = SSZType("uint8", fixed_size=1)
UINT16_TYPE = SSZType("uint16", fixed_size=2)
UINT32_TYPE = SSZType("uint32", fixed_size=4)
UINT64_TYPE = SSZType("uint64", fixed_size=8)
UINT256_TYPE = SSZType("uint256", fixed_size=32)
BYTES_TYPE = SSZType("bytes", fixed_size=None)  # Variable-size


def serialize_container(fields: list[tuple[str, SSZType, object]]) -> bytes:
    """Serialize an SSZ container (struct-like type with named fields).

    SSZ containers have a fixed portion and a variable portion:
    - Fixed-size fields are serialized inline
    - Variable-size fields get a 4-byte offset pointer inline,
      with the actual data appended at the end

    This two-pass approach lets parsers jump directly to any fixed field
    without scanning through variable-length data.
    """
    fixed_parts = []   # Fixed-size field values OR offset placeholders
    variable_parts = []  # Serialized variable-size field data
    field_types = []     # Track which fields are variable for offset calc

    # First pass: serialize each field
    for name, ssz_type, value in fields:
        serialized = _serialize_value(ssz_type, value)
        if ssz_type.is_fixed():
            fixed_parts.append(serialized)
            field_types.append(('fixed', len(serialized)))
        else:
            # Placeholder — will be replaced with offset
            fixed_parts.append(None)
            variable_parts.append(serialized)
            field_types.append(('variable', len(serialized)))

    # Calculate the total fixed section size (fixed fields + offset placeholders)
    fixed_section_size = 0
    for ftype, fsize in field_types:
        if ftype == 'fixed':
            fixed_section_size += fsize
        else:
            fixed_section_size += BYTES_PER_LENGTH_OFFSET  # 4-byte offset pointer

    # Second pass: fill in offsets for variable fields
    var_offset = fixed_section_size  # Variable data starts right after fixed section
    var_idx = 0
    result_fixed = []
    for i, (ftype, fsize) in enumerate(field_types):
        if ftype == 'fixed':
            result_fixed.append(fixed_parts[i])
        else:
            # Write the offset where this variable field's data will be
            result_fixed.append(serialize_uint(var_offset, BYTES_PER_LENGTH_OFFSET))
            var_offset += len(variable_parts[var_idx])
            var_idx += 1

    return b''.join(result_fixed) + b''.join(variable_parts)


def _serialize_value(ssz_type: SSZType, value: object) -> bytes:
    """Serialize a single value based on its SSZ type."""
    if ssz_type.name == "bool":
        return serialize_bool(value)
    elif ssz_type.name.startswith("uint"):
        bits = int(ssz_type.name[4:])
        return serialize_uint(value, bits // 8)
    elif ssz_type.name == "bytes":
        return serialize_bytes(value)
    else:
        raise ValueError(f"Unknown SSZ type: {ssz_type.name}")


def deserialize_container(data: bytes, schema: list[tuple[str, SSZType]]) -> dict:
    """Deserialize an SSZ container given its schema.

    Reads fixed fields directly and follows offsets for variable fields.
    """
    result = {}
    pos = 0  # Current position in the fixed section

    # First pass: read fixed values and collect offsets for variable fields
    fixed_values = []
    var_offsets = []  # (field_name, offset) for variable fields
    var_field_indices = []  # Indices of variable fields in schema

    for i, (name, ssz_type) in enumerate(schema):
        if ssz_type.is_fixed():
            size = ssz_type.fixed_size
            raw = data[pos:pos + size]
            if ssz_type.name == "bool":
                result[name] = deserialize_bool(raw)
            elif ssz_type.name.startswith("uint"):
                bits = int(ssz_type.name[4:])
                result[name] = deserialize_uint(raw, bits // 8)
            pos += size
        else:
            # Read the 4-byte offset
            offset = deserialize_uint(data[pos:pos + BYTES_PER_LENGTH_OFFSET], BYTES_PER_LENGTH_OFFSET)
            var_offsets.append((name, offset))
            var_field_indices.append(i)
            pos += BYTES_PER_LENGTH_OFFSET

    # Second pass: extract variable-length fields using offsets
    for idx, (name, offset) in enumerate(var_offsets):
        # End boundary is either the next variable offset or end of data
        if idx + 1 < len(var_offsets):
            end = var_offsets[idx + 1][1]
        else:
            end = len(data)
        result[name] = data[offset:end]

    return result


# --- Merkleization ----------------------------------------------------------

def next_power_of_two(n: int) -> int:
    """Return the smallest power of 2 >= n."""
    if n <= 1:
        return 1
    return 1 << (n - 1).bit_length()


def pack_chunks(data: bytes) -> list[bytes]:
    """Split serialized data into 32-byte chunks, zero-padding the last one.

    Merkleization operates on fixed 32-byte chunks. If the data doesn't
    fill the last chunk, it's right-padded with zeros.
    """
    chunks = []
    for i in range(0, len(data), BYTES_PER_CHUNK):
        chunk = data[i:i + BYTES_PER_CHUNK]
        if len(chunk) < BYTES_PER_CHUNK:
            chunk = chunk + b'\x00' * (BYTES_PER_CHUNK - len(chunk))
        chunks.append(chunk)
    if not chunks:
        chunks = [ZERO_HASH]  # At least one chunk
    return chunks


def merkleize(chunks: list[bytes], limit: int | None = None) -> bytes:
    """Compute the Merkle root of a list of 32-byte chunks.

    Pads with zero hashes to the next power of 2, then builds a binary
    hash tree bottom-up. The root is the hash tree root of the object.
    """
    # Pad to the required number of leaves
    if limit is not None:
        target_count = next_power_of_two(limit)
    else:
        target_count = next_power_of_two(len(chunks))

    # Ensure at least 1 leaf
    target_count = max(target_count, 1)

    # Pad with zero hashes to fill the tree
    padded = list(chunks)
    while len(padded) < target_count:
        padded.append(ZERO_HASH)

    # Build the Merkle tree bottom-up
    layer = padded
    while len(layer) > 1:
        next_layer = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else ZERO_HASH
            # Parent = hash(left || right)
            next_layer.append(sha256(left + right))
        layer = next_layer

    return layer[0]


def hash_tree_root_basic(value: int, byte_length: int) -> bytes:
    """Hash tree root for a basic (fixed-size) type.

    Pack the serialized value into a single chunk and return it directly.
    A single chunk IS its own Merkle root (no hashing needed).
    """
    serialized = serialize_uint(value, byte_length)
    chunk = serialized + b'\x00' * (BYTES_PER_CHUNK - len(serialized))
    return chunk  # Single leaf — the root is the leaf itself


def hash_tree_root_container(fields: list[tuple[str, SSZType, object]]) -> bytes:
    """Compute the hash tree root of a container.

    Each field gets its own hash tree root (recursively), and these roots
    become the leaves of the container's Merkle tree. This allows proving
    individual fields without revealing the entire container.
    """
    field_roots = []
    for name, ssz_type, value in fields:
        if ssz_type.name == "bool":
            # Bool: pack into a 32-byte chunk
            root = serialize_bool(value) + b'\x00' * 31
        elif ssz_type.name.startswith("uint"):
            bits = int(ssz_type.name[4:])
            root = hash_tree_root_basic(value, bits // 8)
        elif ssz_type.name == "bytes":
            # Variable-length bytes: Merkleize the chunks, then mix in the length
            chunks = pack_chunks(value)
            data_root = merkleize(chunks)
            # Mix in the length — this prevents length-extension attacks
            length_bytes = serialize_uint(len(value), 32)
            root = sha256(data_root + length_bytes)
        else:
            raise ValueError(f"Unsupported type for HTR: {ssz_type.name}")
        field_roots.append(root)

    return merkleize(field_roots)


# --- Generalized Index Proofs -----------------------------------------------

def generalized_index(depth: int, field_index: int) -> int:
    """Compute the generalized index for a field in a container.

    The generalized index uniquely identifies a node in the Merkle tree.
    Root = 1, left child = 2*i, right child = 2*i + 1.
    Leaves at depth d start at index 2^d.

    This addressing scheme lets light clients request proofs for specific
    fields by number, without knowing the full tree structure.
    """
    return (1 << depth) + field_index


def build_merkle_tree(chunks: list[bytes]) -> list[list[bytes]]:
    """Build a full Merkle tree and return all layers (bottom-up).

    Returns layers[0] = leaves, layers[-1] = [root].
    We store all layers so we can extract sibling nodes for proofs.
    """
    target = next_power_of_two(len(chunks))
    padded = list(chunks) + [ZERO_HASH] * (target - len(chunks))

    layers = [padded]
    current = padded
    while len(current) > 1:
        next_layer = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if i + 1 < len(current) else ZERO_HASH
            next_layer.append(sha256(left + right))
        layers.append(next_layer)
        current = next_layer

    return layers


def generate_proof(layers: list[list[bytes]], leaf_index: int) -> list[bytes]:
    """Generate a Merkle proof for a leaf at the given index.

    A proof consists of the sibling hashes along the path from leaf to root.
    The verifier can reconstruct the root using just the leaf + proof.
    """
    proof = []
    idx = leaf_index
    for layer in layers[:-1]:  # Skip the root layer
        # The sibling is at the adjacent index (flip the last bit)
        sibling_idx = idx ^ 1  # XOR with 1 to get sibling
        if sibling_idx < len(layer):
            proof.append(layer[sibling_idx])
        else:
            proof.append(ZERO_HASH)
        idx //= 2  # Move up to parent
    return proof


def verify_proof(leaf: bytes, proof: list[bytes], leaf_index: int, root: bytes) -> bool:
    """Verify a Merkle proof against a known root.

    Starting from the leaf, hash with each sibling in the proof to
    reconstruct what should be the root. If it matches, the proof is valid.
    """
    current = leaf
    idx = leaf_index
    for sibling in proof:
        if idx % 2 == 0:
            # Current node is a left child
            current = sha256(current + sibling)
        else:
            # Current node is a right child
            current = sha256(sibling + current)
        idx //= 2
    return current == root


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def _hex(data: bytes, length: int = HEX_DISPLAY) -> str:
    """Format bytes as a truncated hex string for display."""
    full = data.hex()
    if len(full) > length:
        return full[:length] + "..."
    return full


def demo():
    """Run a visual demonstration of SSZ encoding and Merkleization."""

    # --- Part 1: Basic type serialization -----------------------------------
    print("=" * 70)
    print("SIMPLE SERIALIZE (SSZ) — Ethereum Consensus Layer Encoding")
    print("=" * 70)
    print()
    print("--- Part 1: Basic Type Serialization ---")
    print()

    # Demonstrate little-endian encoding
    test_values = [
        ("bool (True)", BOOL_TYPE, True),
        ("bool (False)", BOOL_TYPE, False),
        ("uint8 (255)", UINT8_TYPE, 255),
        ("uint16 (1024)", UINT16_TYPE, 1024),
        ("uint32 (305419896)", UINT32_TYPE, 305419896),  # 0x12345678
        ("uint64 (slot number)", UINT64_TYPE, 6789012),
    ]

    print(f"  {'Type':<25} {'Value':<15} {'SSZ Bytes (hex, little-endian)'}")
    print(f"  {'─' * 25} {'─' * 15} {'─' * 35}")
    for label, ssz_type, value in test_values:
        serialized = _serialize_value(ssz_type, value)
        print(f"  {label:<25} {str(value):<15} {serialized.hex()}")

    print()
    print("  Note: uint32 305419896 = 0x12345678")
    print("  SSZ little-endian: 78 56 34 12 (bytes reversed vs big-endian)")

    # --- Part 2: Container serialization ------------------------------------
    print()
    print("--- Part 2: Container Serialization (BeaconBlockHeader) ---")
    print()

    # A simplified BeaconBlockHeader — real one has these exact fields
    header_fields = [
        ("slot", UINT64_TYPE, 6789012),
        ("proposer_index", UINT64_TYPE, 42),
        ("parent_root", UINT256_TYPE, 0xABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789),
        ("state_root", UINT256_TYPE, 0x1111111122222222333333334444444455555555666666667777777788888888),
        ("body_root", UINT256_TYPE, 0xAAAABBBBCCCCDDDDEEEEFFFF00001111AAAABBBBCCCCDDDDEEEE000011112222),
    ]

    serialized = serialize_container(header_fields)

    print("  BeaconBlockHeader:")
    print("  ┌─────────────────────────────────────────────────────┐")
    for name, ssz_type, value in header_fields:
        if ssz_type.name.startswith("uint") and int(ssz_type.name[4:]) > 64:
            display = f"0x{value:064x}"[:26] + "..."
        else:
            display = str(value)
        print(f"  │  {name:<20} = {display:<30}│")
    print("  └─────────────────────────────────────────────────────┘")
    print()
    print(f"  Serialized size: {len(serialized)} bytes")
    print(f"  All fields are fixed-size → no offset pointers needed")
    print(f"  Layout: [slot:8][proposer_index:8][parent_root:32][state_root:32][body_root:32]")

    # --- Part 3: Container with variable-size fields ------------------------
    print()
    print("--- Part 3: Variable-Size Fields (offset pointers) ---")
    print()

    mixed_fields = [
        ("version", UINT32_TYPE, 3),
        ("graffiti", BYTES_TYPE, b"Hello Ethereum!"),
        ("epoch", UINT64_TYPE, 1234),
        ("extra_data", BYTES_TYPE, b"custom payload here"),
    ]

    serialized_mixed = serialize_container(mixed_fields)

    print("  Container with mixed fixed + variable fields:")
    print()
    # Show the layout with offsets
    print("  Fixed section (inline values + offset pointers):")
    print("  ┌──────────┬──────────────┬──────────┬──────────────┐")
    print("  │ version  │ graffiti_off │  epoch   │ extra_off    │")
    print("  │ (4 bytes)│ (4 bytes)    │ (8 bytes)│ (4 bytes)    │")
    print("  └──────────┴──────────────┴──────────┴──────────────┘")
    print("  Variable section (actual data, pointed to by offsets):")
    print("  ┌───────────────────────┬─────────────────────────────┐")
    print("  │ graffiti data         │ extra_data data             │")
    print("  │ (15 bytes)            │ (19 bytes)                  │")
    print("  └───────────────────────┴─────────────────────────────┘")
    print()
    print(f"  Total serialized: {len(serialized_mixed)} bytes")

    # Round-trip deserialization
    schema = [(n, t) for n, t, _ in mixed_fields]
    deserialized = deserialize_container(serialized_mixed, schema)
    print()
    print("  Round-trip deserialization:")
    for name, ssz_type in schema:
        val = deserialized[name]
        if isinstance(val, bytes):
            print(f"    {name}: {val.decode('utf-8', errors='replace')} ({len(val)} bytes)")
        else:
            print(f"    {name}: {val}")

    # --- Part 4: Merkleization and Hash Tree Roots --------------------------
    print()
    print("--- Part 4: Merkleization (Hash Tree Roots) ---")
    print()

    # Compute hash tree root of the BeaconBlockHeader
    htr = hash_tree_root_container(header_fields)

    print("  Hash tree root of BeaconBlockHeader:")
    print()

    # Show the Merkle tree structure
    field_names = [name for name, _, _ in header_fields]
    # Pad to power of 2 for visualization
    num_leaves = next_power_of_two(len(field_names))
    padded_names = field_names + ["(zero pad)"] * (num_leaves - len(field_names))

    # Build tree from field roots for visualization
    field_roots = []
    for name, ssz_type, value in header_fields:
        if ssz_type.name == "bool":
            root = serialize_bool(value) + b'\x00' * 31
        elif ssz_type.name.startswith("uint"):
            bits = int(ssz_type.name[4:])
            root = hash_tree_root_basic(value, bits // 8)
        else:
            root = ZERO_HASH
        field_roots.append(root)

    tree = build_merkle_tree(field_roots)

    # Print the tree layers
    print(f"  {'Root (hash tree root)':^60}")
    print(f"  {'HTR = ' + _hex(htr, 32) + '...':^60}")
    print(f"  {'/' + ' ' * 28 + chr(92):^60}")

    # Show leaves
    print()
    print("  Leaves (one per field, padded to 8):")
    for i, name in enumerate(padded_names):
        if i < len(field_roots):
            h = _hex(field_roots[i], 12)
        else:
            h = _hex(ZERO_HASH, 12)
        print(f"    [{i}] {name:<20} → {h}...")
    print()
    print(f"  5 fields padded to {num_leaves} leaves (next power of 2)")
    print(f"  Tree depth: {int(math.log2(num_leaves)) + 1} layers")

    # --- Part 5: Generalized Index Proofs -----------------------------------
    print()
    print("--- Part 5: Generalized Index Proofs ---")
    print()

    # Prove that a specific field has a specific value
    target_field = 1  # proposer_index
    target_name = header_fields[target_field][0]
    target_value = header_fields[target_field][2]

    # Build tree from field roots
    tree = build_merkle_tree(field_roots)

    # Generate proof
    proof = generate_proof(tree, target_field)
    root = tree[-1][0]  # The Merkle root

    # Compute generalized index
    depth = int(math.log2(num_leaves))
    gen_idx = generalized_index(depth, target_field)

    print(f"  Proving field: {target_name} = {target_value}")
    print(f"  Generalized index: {gen_idx} (depth={depth}, field={target_field})")
    print()

    # Verify the proof
    leaf = field_roots[target_field]
    valid = verify_proof(leaf, proof, target_field, root)

    print(f"  Proof path ({len(proof)} sibling hashes):")
    for i, sibling in enumerate(proof):
        direction = "left" if (target_field >> i) % 2 == 1 else "right"
        print(f"    Layer {i}: sibling on {direction:>5} = {_hex(sibling, 24)}...")
    print()
    print(f"  Leaf:             {_hex(leaf, 32)}...")
    print(f"  Reconstructed root: {_hex(root, 32)}...")
    print(f"  Expected root:      {_hex(htr, 32)}...")
    print(f"  Proof valid: {'YES' if valid else 'NO'}")

    # Tamper with the leaf and show proof fails
    print()
    print("  --- Tampering test ---")
    fake_leaf = hash_tree_root_basic(9999, 8)  # Wrong proposer_index
    valid_fake = verify_proof(fake_leaf, proof, target_field, root)
    print(f"  Fake leaf (proposer_index=9999): {_hex(fake_leaf, 24)}...")
    print(f"  Proof valid with fake leaf: {'YES' if valid_fake else 'NO'}")
    print()

    # --- Part 6: Comparison with RLP ----------------------------------------
    print("--- Part 6: SSZ vs RLP ---")
    print()
    print("  ┌────────────────────┬──────────────────────────────┐")
    print("  │ Feature            │ SSZ              RLP         │")
    print("  ├────────────────────┼──────────────────────────────┤")
    print("  │ Byte order         │ Little-endian    Big-endian  │")
    print("  │ Schema required?   │ Yes              No          │")
    print("  │ Merkle proofs      │ Native (HTR)     Not built-in│")
    print("  │ Fixed-size access  │ O(1) offset      O(n) scan   │")
    print("  │ Used in            │ Consensus Layer  Exec. Layer │")
    print("  └────────────────────┴──────────────────────────────┘")
    print()
    print("  SSZ was designed for proof-friendly serialization.")
    print("  Every field can be proven independently via Merkle proofs.")


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
