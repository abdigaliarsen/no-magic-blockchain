"""
TITLE: Recursive Length Prefix (RLP) Encoding
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    A complete RLP encoder and decoder from scratch. RLP is Ethereum's canonical
    serialization format — every transaction, block header, and state trie node
    is RLP-encoded before hashing or transmission.

KEY CONCEPTS:
    - Single byte (0x00-0x7f): encoded as itself (no prefix)
    - Short string (0-55 bytes): 0x80 + length prefix, then data
    - Long string (>55 bytes): 0xb7 + length-of-length, then length, then data
    - Short list (0-55 bytes total payload): 0xc0 + length prefix, then items
    - Long list (>55 bytes payload): 0xf7 + length-of-length, then length, then items

PREREQUISITE SCRIPTS:
    - None (RLP is a standalone encoding format)

REAL-WORLD RELEVANCE:
    RLP is used everywhere in Ethereum: transaction serialization, block headers,
    state trie nodes, receipt encoding, and network protocol messages. Understanding
    RLP is essential for building Ethereum tools, parsers, and clients.
"""

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# --- RLP prefix ranges --------------------------------------------------------
# These byte ranges define how to interpret the first byte of an RLP item.

# Single byte: 0x00..0x7f — the byte IS the value (1 byte, no prefix)
SINGLE_BYTE_MAX = 0x7F

# Short string: prefix 0x80..0xb7 — string of length 0..55
# The string length = first_byte - 0x80
SHORT_STRING_PREFIX = 0x80
SHORT_STRING_MAX_LEN = 55  # Strings up to 55 bytes use this encoding

# Long string: prefix 0xb8..0xbf — string of length > 55
# The length-of-length = first_byte - 0xb7, then that many bytes encode the length
LONG_STRING_PREFIX = 0xB7

# Short list: prefix 0xc0..0xf7 — list with total payload 0..55 bytes
# The payload length = first_byte - 0xc0
SHORT_LIST_PREFIX = 0xC0
SHORT_LIST_MAX_LEN = 55  # List payloads up to 55 bytes use this encoding

# Long list: prefix 0xf8..0xff — list with total payload > 55 bytes
# The length-of-length = first_byte - 0xf7
LONG_LIST_PREFIX = 0xF7


# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Encoding -----------------------------------------------------------------

def _encode_length(length: int, offset: int) -> bytes:
    """Encode a length value with the appropriate RLP prefix.

    For lengths 0-55: single prefix byte = offset + length
    For lengths >55: prefix byte = offset + 55 + len_of_len, then length in big-endian

    Args:
        length: The number of bytes in the payload
        offset: 0x80 for strings, 0xc0 for lists
    """
    if length <= SHORT_STRING_MAX_LEN:
        # Short form: one prefix byte encodes the length directly
        return bytes([offset + length])
    else:
        # Long form: encode the length itself as big-endian bytes
        # Then prefix with (offset + 55 + number_of_length_bytes)
        length_bytes = _int_to_min_bytes(length)
        len_of_len = len(length_bytes)
        # offset + 55 = 0xb7 for strings, 0xf7 for lists
        return bytes([offset + SHORT_STRING_MAX_LEN + len_of_len]) + length_bytes


def _int_to_min_bytes(value: int) -> bytes:
    """Convert a non-negative integer to the minimum number of big-endian bytes.

    Examples: 0 → b'' (empty), 1 → b'\\x01', 256 → b'\\x01\\x00'
    """
    if value == 0:
        return b""
    # Calculate how many bytes we need
    byte_length = (value.bit_length() + 7) // 8
    return value.to_bytes(byte_length, "big")


def rlp_encode(item) -> bytes:
    """RLP-encode a Python object.

    Supported types:
      - bytes: encoded as an RLP string
      - str: UTF-8 encoded, then treated as bytes
      - int: converted to minimal big-endian bytes, then encoded as string
      - list/tuple: each element is recursively RLP-encoded
      - bool: True=1, False=0 (encoded as int)

    Returns the RLP-encoded bytes.
    """
    if isinstance(item, bool):
        # Must check bool before int because bool is a subclass of int
        return rlp_encode(1 if item else 0)

    elif isinstance(item, int):
        if item == 0:
            # Zero is encoded as empty string (0x80), NOT as 0x00
            return bytes([SHORT_STRING_PREFIX])
        elif item < 0:
            raise ValueError("RLP cannot encode negative integers")
        else:
            # Convert integer to its minimal big-endian byte representation
            return rlp_encode(_int_to_min_bytes(item))

    elif isinstance(item, str):
        # Encode the UTF-8 bytes of the string
        return rlp_encode(item.encode("utf-8"))

    elif isinstance(item, (bytes, bytearray)):
        data = bytes(item)
        if len(data) == 1 and data[0] <= SINGLE_BYTE_MAX:
            # Single byte in range 0x00..0x7f — it's its own RLP encoding
            return data
        else:
            # Prefix with length encoding
            return _encode_length(len(data), SHORT_STRING_PREFIX) + data

    elif isinstance(item, (list, tuple)):
        # Recursively encode each element
        payload = b""
        for element in item:
            payload += rlp_encode(element)
        # Prefix the concatenated payload with list length encoding
        return _encode_length(len(payload), SHORT_LIST_PREFIX) + payload

    else:
        raise TypeError(f"Cannot RLP-encode type: {type(item).__name__}")


# --- Decoding -----------------------------------------------------------------

def rlp_decode(data: bytes):
    """Decode an RLP-encoded byte sequence.

    Returns a Python object:
      - bytes for RLP strings
      - list for RLP lists (elements recursively decoded)

    Raises ValueError for invalid RLP data.
    """
    if not data:
        raise ValueError("Cannot decode empty RLP data")

    result, consumed = _decode_item(data, 0)

    if consumed != len(data):
        raise ValueError(
            f"RLP data has trailing bytes: consumed {consumed} of {len(data)}"
        )

    return result


def _decode_item(data: bytes, pos: int) -> tuple:
    """Decode a single RLP item starting at position `pos`.

    Returns (decoded_item, new_position).
    """
    if pos >= len(data):
        raise ValueError(f"Unexpected end of RLP data at position {pos}")

    prefix = data[pos]

    if prefix <= SINGLE_BYTE_MAX:
        # --- Single byte (0x00..0x7f) ---
        # The byte itself is the encoded value
        return bytes([prefix]), pos + 1

    elif prefix <= LONG_STRING_PREFIX:
        # --- Short string (0x80..0xb7) ---
        str_len = prefix - SHORT_STRING_PREFIX  # Length of the string
        start = pos + 1                         # String data starts after prefix
        end = start + str_len
        if end > len(data):
            raise ValueError(f"Short string overflows data at position {pos}")
        return data[start:end], end

    elif prefix <= 0xBF:
        # --- Long string (0xb8..0xbf) ---
        len_of_len = prefix - LONG_STRING_PREFIX  # How many bytes encode the length
        # Read the length value from the next len_of_len bytes
        len_start = pos + 1
        len_end = len_start + len_of_len
        if len_end > len(data):
            raise ValueError(f"Long string length overflows data at position {pos}")
        str_len = int.from_bytes(data[len_start:len_end], "big")
        start = len_end
        end = start + str_len
        if end > len(data):
            raise ValueError(f"Long string data overflows at position {pos}")
        return data[start:end], end

    elif prefix <= LONG_LIST_PREFIX:
        # --- Short list (0xc0..0xf7) ---
        payload_len = prefix - SHORT_LIST_PREFIX  # Total payload length
        start = pos + 1
        end = start + payload_len
        if end > len(data):
            raise ValueError(f"Short list overflows data at position {pos}")
        # Decode each item in the payload
        items = []
        current = start
        while current < end:
            item, current = _decode_item(data, current)
            items.append(item)
        return items, end

    else:
        # --- Long list (0xf8..0xff) ---
        len_of_len = prefix - LONG_LIST_PREFIX
        len_start = pos + 1
        len_end = len_start + len_of_len
        if len_end > len(data):
            raise ValueError(f"Long list length overflows data at position {pos}")
        payload_len = int.from_bytes(data[len_start:len_end], "big")
        start = len_end
        end = start + payload_len
        if end > len(data):
            raise ValueError(f"Long list data overflows at position {pos}")
        items = []
        current = start
        while current < end:
            item, current = _decode_item(data, current)
            items.append(item)
        return items, end


# --- Helper to convert decoded bytes back to int for display -------------------

def bytes_to_int(b: bytes) -> int:
    """Convert bytes back to an integer (big-endian). Empty bytes = 0."""
    if not b:
        return 0
    return int.from_bytes(b, "big")


def format_hex(data: bytes) -> str:
    """Format bytes as a hex string with spaces every 2 chars for readability."""
    hex_str = data.hex()
    # Group into pairs
    pairs = [hex_str[i:i+2] for i in range(0, len(hex_str), 2)]
    return " ".join(pairs)


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a comprehensive demonstration of RLP encoding and decoding."""

    print("=" * 64)
    print("  RLP (RECURSIVE LENGTH PREFIX) ENCODING")
    print("  Ethereum's canonical serialization format")
    print("=" * 64)

    # --- Part 1: Single bytes -------------------------------------------------

    print("\n" + "=" * 64)
    print("  Part 1: Single byte encoding (0x00..0x7f)")
    print("=" * 64)
    print("  Values 0-127 encode as themselves (no prefix needed)")

    test_bytes = [b"\x00", b"\x01", b"\x42", b"\x7f"]
    for tb in test_bytes:
        encoded = rlp_encode(tb)
        decoded = rlp_decode(encoded)
        print(f"\n  Input:    0x{tb.hex()}")
        print(f"  Encoded:  {format_hex(encoded)}")
        print(f"  Decoded:  0x{decoded.hex()}")
        assert decoded == tb, "Round-trip failed!"
        print(f"  [PASS] Round-trip verified")

    # --- Part 2: Short strings (0-55 bytes) -----------------------------------

    print("\n" + "=" * 64)
    print("  Part 2: Short string encoding (0-55 bytes)")
    print("=" * 64)
    print("  Prefix = 0x80 + length, then the raw bytes")

    test_strings = [
        b"",                    # Empty string
        b"dog",                 # 3 bytes
        b"hello world",        # 11 bytes
        b"A" * 55,             # Max short string length
    ]

    for ts in test_strings:
        encoded = rlp_encode(ts)
        decoded = rlp_decode(encoded)
        label = ts.decode("ascii", errors="replace") if len(ts) <= 20 else f"{ts[:20].decode('ascii')}... ({len(ts)} bytes)"
        print(f"\n  Input:    \"{label}\" ({len(ts)} bytes)")
        hex_display = format_hex(encoded)
        if len(hex_display) > 50:
            hex_display = hex_display[:50] + "..."
        print(f"  Encoded:  {hex_display}")
        prefix = encoded[0]
        if len(ts) == 0 or (len(ts) == 1 and ts[0] <= 0x7f):
            print(f"  Prefix:   0x{prefix:02x} (special case)")
        else:
            print(f"  Prefix:   0x{prefix:02x} = 0x80 + {prefix - 0x80} (length)")
        print(f"  Size:     {len(encoded)} bytes encoded from {len(ts)} bytes input")
        assert decoded == ts, "Round-trip failed!"
        print(f"  [PASS] Round-trip verified")

    # --- Part 3: Long strings (>55 bytes) -------------------------------------

    print("\n" + "=" * 64)
    print("  Part 3: Long string encoding (>55 bytes)")
    print("=" * 64)
    print("  Prefix = 0xb7 + len_of_len, then length bytes, then data")

    long_strings = [
        b"B" * 56,            # Just over the short threshold
        b"C" * 256,           # Needs 1 byte for length
        b"D" * 1024,          # Needs 2 bytes for length
    ]

    for ls in long_strings:
        encoded = rlp_encode(ls)
        decoded = rlp_decode(encoded)
        prefix = encoded[0]
        len_of_len = prefix - 0xb7   # How many bytes encode the length
        length_bytes = encoded[1:1 + len_of_len]
        actual_len = int.from_bytes(length_bytes, "big")

        print(f"\n  Input:    \"{ls[:10].decode()}...\" ({len(ls)} bytes)")
        print(f"  Prefix:   0x{prefix:02x} = 0xb7 + {len_of_len} (length uses {len_of_len} byte{'s' if len_of_len > 1 else ''})")
        print(f"  Length:   {format_hex(length_bytes)} = {actual_len}")
        print(f"  Total:    {len(encoded)} bytes ({len_of_len + 1} overhead + {actual_len} data)")
        assert decoded == ls, "Round-trip failed!"
        print(f"  [PASS] Round-trip verified")

    # --- Part 4: Integer encoding ---------------------------------------------

    print("\n" + "=" * 64)
    print("  Part 4: Integer encoding")
    print("=" * 64)
    print("  Integers → minimal big-endian bytes → encoded as strings")

    test_ints = [0, 1, 127, 128, 255, 256, 1024, 65535, 2**24]
    for ti in test_ints:
        encoded = rlp_encode(ti)
        decoded = rlp_decode(encoded)
        decoded_int = bytes_to_int(decoded)
        print(f"\n  Input:     {ti} (0x{ti:X})")
        print(f"  As bytes:  {format_hex(_int_to_min_bytes(ti)) if ti else '(empty)'}")
        print(f"  Encoded:   {format_hex(encoded)}")
        print(f"  Decoded:   {decoded_int}")
        assert decoded_int == ti, f"Round-trip failed for {ti}!"
        print(f"  [PASS] Round-trip verified")

    # --- Part 5: Lists --------------------------------------------------------

    print("\n" + "=" * 64)
    print("  Part 5: List encoding")
    print("=" * 64)
    print("  Lists: encode each item, concat, prefix with total payload length")

    # Empty list
    print("\n  --- Empty list ---")
    encoded_empty = rlp_encode([])
    decoded_empty = rlp_decode(encoded_empty)
    print(f"  Input:    []")
    print(f"  Encoded:  {format_hex(encoded_empty)}")
    print(f"  Prefix:   0x{encoded_empty[0]:02x} = 0xc0 + 0 (empty payload)")
    print(f"  Decoded:  {decoded_empty}")
    assert decoded_empty == [], "Empty list round-trip failed!"
    print(f"  [PASS] Round-trip verified")

    # Simple list
    print("\n  --- List of strings ---")
    test_list = [b"cat", b"dog"]
    encoded_list = rlp_encode(test_list)
    decoded_list = rlp_decode(encoded_list)
    print(f"  Input:    [\"cat\", \"dog\"]")
    print(f"  Encoded:  {format_hex(encoded_list)}")
    prefix = encoded_list[0]
    payload_len = prefix - 0xc0
    print(f"  Prefix:   0x{prefix:02x} = 0xc0 + {payload_len} (payload length)")
    print(f"  Breakdown:")
    print(f"    0xc8     = list prefix (payload = {payload_len} bytes)")
    cat_enc = rlp_encode(b"cat")
    dog_enc = rlp_encode(b"dog")
    print(f"    {format_hex(cat_enc)}  = \"cat\" (0x83 + 3 bytes)")
    print(f"    {format_hex(dog_enc)}  = \"dog\" (0x83 + 3 bytes)")
    assert decoded_list == test_list, "List round-trip failed!"
    print(f"  [PASS] Round-trip verified")

    # Nested list
    print("\n  --- Nested list ---")
    nested = [b"hello", [b"world", b"!"]]
    encoded_nested = rlp_encode(nested)
    decoded_nested = rlp_decode(encoded_nested)
    print(f"  Input:    [\"hello\", [\"world\", \"!\"]]")
    print(f"  Encoded:  {format_hex(encoded_nested)}")
    print(f"  Decoded:  {_display_decoded(decoded_nested)}")
    assert decoded_nested == nested, "Nested list round-trip failed!"
    print(f"  [PASS] Round-trip verified")

    # --- Part 6: Real Ethereum structure (transaction-like) --------------------

    print("\n" + "=" * 64)
    print("  Part 6: Encoding an Ethereum-like transaction")
    print("=" * 64)
    print("  A transaction is an RLP-encoded list of fields")

    # Simulate a transaction: [nonce, gasPrice, gasLimit, to, value, data]
    tx_fields = [
        b"\x09",                             # nonce = 9
        b"\x04\xa8\x17\xc8\x00",            # gasPrice = 20 Gwei
        b"\x52\x08",                          # gasLimit = 21000
        bytes.fromhex("3535353535353535353535353535353535353535"),  # to address (20 bytes)
        b"\x0d\xe0\xb6\xb3\xa7\x64\x00\x00", # value = 1 ETH in Wei
        b"",                                   # data (empty for transfers)
    ]

    encoded_tx = rlp_encode(tx_fields)

    print(f"\n  Transaction fields:")
    field_names = ["nonce", "gasPrice", "gasLimit", "to", "value", "data"]
    for name, val in zip(field_names, tx_fields):
        if name == "to":
            print(f"    {name:<12} 0x{val.hex()} ({len(val)} bytes)")
        elif name == "data":
            print(f"    {name:<12} (empty)")
        else:
            print(f"    {name:<12} {bytes_to_int(val)} (0x{val.hex()})")

    print(f"\n  Encoded transaction ({len(encoded_tx)} bytes):")
    # Print in rows of 16 bytes
    hex_str = encoded_tx.hex()
    for i in range(0, len(hex_str), 32):
        chunk = hex_str[i:i+32]
        spaced = " ".join(chunk[j:j+2] for j in range(0, len(chunk), 2))
        print(f"    {spaced}")

    # Decode and verify
    decoded_tx = rlp_decode(encoded_tx)
    print(f"\n  Decoded back:")
    for name, original, decoded_val in zip(field_names, tx_fields, decoded_tx):
        match = "OK" if original == decoded_val else "MISMATCH"
        print(f"    {name:<12} [{match}]")

    all_match = all(o == d for o, d in zip(tx_fields, decoded_tx))
    print(f"\n  [{'PASS' if all_match else 'FAIL'}] Full transaction round-trip")

    # --- Part 7: Encoding rules summary ---------------------------------------

    print("\n" + "=" * 64)
    print("  RLP Encoding Rules Summary")
    print("=" * 64)
    print("""
  ┌─────────────────────────────────────────────────────────┐
  │  Type          │  Prefix Range  │  Rule                 │
  ├─────────────────────────────────────────────────────────┤
  │  Single byte   │  0x00..0x7f    │  byte IS the encoding │
  │  Short string  │  0x80..0xb7    │  0x80+len, data       │
  │  Long string   │  0xb8..0xbf    │  0xb7+LL, len, data   │
  │  Short list    │  0xc0..0xf7    │  0xc0+len, items      │
  │  Long list     │  0xf8..0xff    │  0xf7+LL, len, items  │
  └─────────────────────────────────────────────────────────┘

  LL = "length of the length" (how many bytes encode the length)
  len = payload length in bytes
  """)

    # --- Summary --------------------------------------------------------------

    print("=" * 64)
    print("  KEY TAKEAWAYS")
    print("=" * 64)
    print("  1. RLP has only two data types: strings (bytes) and lists")
    print("  2. The first byte determines the type and length encoding")
    print("  3. Short items (<= 55 bytes) use a 1-byte prefix")
    print("  4. Long items use a multi-byte length after the prefix")
    print("  5. Lists are recursive — they contain RLP-encoded items")
    print("  6. Integers are encoded as their minimal big-endian bytes")
    print("  7. Zero is encoded as empty string (0x80), NOT as 0x00")
    print()


def _display_decoded(item) -> str:
    """Format a decoded RLP item for display (recursive)."""
    if isinstance(item, bytes):
        try:
            text = item.decode("ascii")
            if all(32 <= c < 127 for c in item):
                return f'"{text}"'
        except (UnicodeDecodeError, ValueError):
            pass
        return f"0x{item.hex()}"
    elif isinstance(item, list):
        inner = ", ".join(_display_decoded(i) for i in item)
        return f"[{inner}]"
    return str(item)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
