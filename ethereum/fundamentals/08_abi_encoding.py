"""
TITLE: ABI Encoding
CATEGORY: ethereum

WHAT THIS IMPLEMENTS:
    Ethereum's Application Binary Interface (ABI) encoding and decoding from
    scratch. Covers function selectors, static types (uint256, address, bool,
    bytesN), dynamic types (bytes, string, arrays), and tuples. Includes both
    encoding and decoding of calldata.

KEY CONCEPTS:
    - Function selectors: first 4 bytes of hash of the function signature
    - Static types: left/right-padded to 32-byte words
    - Dynamic types: offset pointer + length prefix + padded data
    - Head-tail encoding: static parts first, dynamic parts appended after

PREREQUISITE SCRIPTS:
    - core/01_hashing.py (hashing fundamentals)
    - ethereum/06_smart_contracts.py (how contracts use ABI encoding)

REAL-WORLD RELEVANCE:
    Every Ethereum transaction that calls a smart contract uses ABI encoding.
    The calldata field contains the function selector + encoded arguments.
    Tools like ethers.js, web3.py, and Foundry's cast all implement ABI
    encoding/decoding to interact with contracts.
"""

import hashlib  # SHA-256 as stand-in for keccak256 — stdlib only
import struct   # For packing integers into bytes

# ============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# ============================================================================

# Each ABI-encoded value occupies a 32-byte (256-bit) "word"
WORD_SIZE = 32

# Maximum display width for hex output
HEX_DISPLAY_WIDTH = 66  # "0x" + 64 hex chars

# NOTE ON KECCAK-256 VS SHA-256:
# Real Ethereum ABI encoding uses keccak256 for function selectors.
# Python's stdlib does not include keccak256 (it's NOT the same as SHA-3).
# We use SHA-256 as a stand-in throughout this script. The encoding LOGIC
# is identical — only the hash function used for selectors differs.
# In production, you'd use: from Crypto.Hash import keccak (pycryptodome)
# or web3.py's Web3.keccak()

# ============================================================================
# SECTION 2: IMPLEMENTATION
# ============================================================================

# --- Hashing (selector computation) ----------------------------------------

def sha256_hex(data: bytes) -> str:
    """SHA-256 hash as hex string. Stand-in for keccak256."""
    return hashlib.sha256(data).hexdigest()


def function_selector(signature: str) -> bytes:
    """Compute the 4-byte function selector from a canonical signature.

    The selector is the first 4 bytes of the hash of the function signature.
    Example: "transfer(address,uint256)" → 4 bytes

    In real Ethereum, this uses keccak256. We use SHA-256 as a stand-in.
    The encoding logic is the same — only the hash function differs.
    """
    full_hash = hashlib.sha256(signature.encode("utf-8")).digest()
    return full_hash[:4]  # First 4 bytes = function selector


# --- Type definitions for the encoder -------------------------------------

class ABIType:
    """Base class for ABI type descriptors."""

    def is_dynamic(self) -> bool:
        """Return True if this type is dynamically sized."""
        return False


class Uint256Type(ABIType):
    """uint256: a 256-bit unsigned integer (static, 32 bytes)."""

    def __repr__(self):
        return "uint256"


class AddressType(ABIType):
    """address: a 20-byte Ethereum address, left-padded to 32 bytes (static)."""

    def __repr__(self):
        return "address"


class BoolType(ABIType):
    """bool: 0 or 1, encoded as uint256 (static, 32 bytes)."""

    def __repr__(self):
        return "bool"


class Bytes32Type(ABIType):
    """bytes32: exactly 32 bytes, right-padded if shorter (static)."""

    def __init__(self, size: int = 32):
        self.size = size  # bytesN where N = 1..32

    def __repr__(self):
        return f"bytes{self.size}"


class BytesType(ABIType):
    """bytes: dynamically-sized byte array."""

    def is_dynamic(self) -> bool:
        return True  # Dynamic: needs offset pointer + length + data

    def __repr__(self):
        return "bytes"


class StringType(ABIType):
    """string: dynamically-sized UTF-8 string (encoded same as bytes)."""

    def is_dynamic(self) -> bool:
        return True

    def __repr__(self):
        return "string"


class ArrayType(ABIType):
    """T[]: dynamically-sized array of elements of type T."""

    def __init__(self, element_type: ABIType):
        self.element_type = element_type

    def is_dynamic(self) -> bool:
        return True  # Dynamic arrays always need offset + length

    def __repr__(self):
        return f"{self.element_type}[]"


class TupleType(ABIType):
    """(T1, T2, ...): a tuple of typed values.

    A tuple is dynamic if any of its elements is dynamic.
    """

    def __init__(self, element_types: list[ABIType]):
        self.element_types = element_types

    def is_dynamic(self) -> bool:
        return any(t.is_dynamic() for t in self.element_types)

    def __repr__(self):
        inner = ",".join(str(t) for t in self.element_types)
        return f"({inner})"


# --- ABI Encoder -----------------------------------------------------------

def encode_uint256(value: int) -> bytes:
    """Encode a uint256 as a 32-byte big-endian word.

    Values are left-padded with zeros to fill 32 bytes.
    Example: 42 → 0x000...002a (32 bytes)
    """
    if value < 0:
        raise ValueError(f"uint256 cannot be negative: {value}")
    return value.to_bytes(WORD_SIZE, "big")


def encode_address(addr: str) -> bytes:
    """Encode an Ethereum address (20 bytes) as a 32-byte left-padded word.

    Address is typically a 40-char hex string (with or without 0x prefix).
    It goes into the LOW 20 bytes of the 32-byte word.
    """
    # Strip 0x prefix if present
    addr = addr.lower().replace("0x", "")
    addr_bytes = bytes.fromhex(addr)
    if len(addr_bytes) > 20:
        raise ValueError(f"Address too long: {len(addr_bytes)} bytes")
    # Left-pad with zeros: [12 zero bytes][20 address bytes]
    return b"\x00" * (WORD_SIZE - len(addr_bytes)) + addr_bytes


def encode_bool(value: bool) -> bytes:
    """Encode a boolean as uint256 (0 or 1, 32 bytes)."""
    return encode_uint256(1 if value else 0)


def encode_bytesN(data: bytes, n: int) -> bytes:
    """Encode a fixed-size bytesN (1 <= N <= 32) as a 32-byte right-padded word.

    Unlike address/uint256 which are LEFT-padded, bytesN is RIGHT-padded.
    Example: bytes4(0xdeadbeef) → 0xdeadbeef000...000 (32 bytes)
    """
    if len(data) > n:
        raise ValueError(f"Data too long for bytes{n}: {len(data)} bytes")
    # Right-pad with zeros
    return data.ljust(WORD_SIZE, b"\x00")


def encode_bytes_dynamic(data: bytes) -> bytes:
    """Encode a dynamic bytes value: length prefix + padded data.

    Layout: [32-byte length][data padded to 32-byte boundary]
    """
    length = len(data)
    # Pad data to the next 32-byte boundary
    padded_len = ((length + WORD_SIZE - 1) // WORD_SIZE) * WORD_SIZE
    padded_data = data.ljust(padded_len, b"\x00")
    return encode_uint256(length) + padded_data


def encode_string(s: str) -> bytes:
    """Encode a dynamic string (same encoding as bytes, just UTF-8 first)."""
    return encode_bytes_dynamic(s.encode("utf-8"))


def encode_array(elements: list, element_type: ABIType) -> bytes:
    """Encode a dynamic array: length prefix + encoded elements.

    For static element types: [length][element1][element2]...
    For dynamic element types: [length][offset1][offset2]...[data1][data2]...
    """
    count = len(elements)
    if not element_type.is_dynamic():
        # Static elements: just concatenate encoded values after the length
        encoded = encode_uint256(count)
        for elem in elements:
            encoded += encode_value(elem, element_type)
        return encoded
    else:
        # Dynamic elements: use head-tail encoding within the array
        return encode_uint256(count) + _encode_head_tail(elements,
            [element_type] * count)


def encode_tuple(values: list, types: list[ABIType]) -> bytes:
    """Encode a tuple using head-tail encoding.

    Static values go directly in the "head" section.
    Dynamic values get an offset pointer in the head, with actual data in the "tail".
    """
    return _encode_head_tail(values, types)


def _encode_head_tail(values: list, types: list[ABIType]) -> bytes:
    """Core head-tail encoding used by both tuples and dynamic arrays.

    Head section: for each value, either the encoded value (static) or a
                  32-byte offset pointer to the tail section (dynamic).
    Tail section: encoded data for all dynamic values, concatenated.

    The offset is relative to the start of the encoding (not the calldata).
    """
    head_size = len(types) * WORD_SIZE  # Each head entry is exactly 32 bytes
    head_parts: list[bytes] = []
    tail_parts: list[bytes] = []
    tail_offset = head_size  # Dynamic data starts after the head

    for value, typ in zip(values, types):
        if typ.is_dynamic():
            # Dynamic: put an offset pointer in the head
            head_parts.append(encode_uint256(tail_offset))
            # Encode the dynamic value and add it to the tail
            encoded = encode_value(value, typ)
            tail_parts.append(encoded)
            tail_offset += len(encoded)  # Advance the tail offset
        else:
            # Static: put the encoded value directly in the head
            head_parts.append(encode_value(value, typ))

    return b"".join(head_parts) + b"".join(tail_parts)


def encode_value(value, typ: ABIType) -> bytes:
    """Encode a single value based on its ABI type."""
    if isinstance(typ, Uint256Type):
        return encode_uint256(value)
    elif isinstance(typ, AddressType):
        return encode_address(value)
    elif isinstance(typ, BoolType):
        return encode_bool(value)
    elif isinstance(typ, Bytes32Type):
        return encode_bytesN(value, typ.size)
    elif isinstance(typ, BytesType):
        return encode_bytes_dynamic(value)
    elif isinstance(typ, StringType):
        return encode_string(value)
    elif isinstance(typ, ArrayType):
        return encode_array(value, typ.element_type)
    elif isinstance(typ, TupleType):
        return encode_tuple(value, typ.element_types)
    else:
        raise ValueError(f"Unknown ABI type: {typ}")


def encode_function_call(signature: str, types: list[ABIType],
                         values: list) -> bytes:
    """Encode a complete function call: selector + ABI-encoded arguments.

    This is what goes into a transaction's calldata field.

    Args:
        signature: Canonical function signature, e.g., "transfer(address,uint256)"
        types: List of ABIType objects matching the function parameters
        values: List of Python values to encode

    Returns:
        Complete calldata: [4-byte selector][encoded arguments]
    """
    selector = function_selector(signature)
    if types:
        encoded_args = _encode_head_tail(values, types)
    else:
        encoded_args = b""
    return selector + encoded_args


# --- ABI Decoder -----------------------------------------------------------

def decode_uint256(data: bytes, offset: int = 0) -> int:
    """Decode a uint256 from 32 bytes at the given offset."""
    word = data[offset:offset + WORD_SIZE]
    return int.from_bytes(word, "big")


def decode_address(data: bytes, offset: int = 0) -> str:
    """Decode an address from 32 bytes (last 20 bytes are the address)."""
    word = data[offset:offset + WORD_SIZE]
    # Address is in the low 20 bytes (bytes 12-31)
    return "0x" + word[12:].hex()


def decode_bool(data: bytes, offset: int = 0) -> bool:
    """Decode a boolean from 32 bytes."""
    return decode_uint256(data, offset) != 0


def decode_string(data: bytes, offset: int = 0) -> str:
    """Decode a dynamic string from the given data offset.

    First read the offset pointer, then jump to that location to read
    the length-prefixed string data.
    """
    # The first word at 'offset' is the actual data offset (from start of args)
    length = decode_uint256(data, offset)
    # Read 'length' bytes after the length word
    string_data = data[offset + WORD_SIZE:offset + WORD_SIZE + length]
    return string_data.decode("utf-8")


def decode_bytes_dynamic(data: bytes, offset: int = 0) -> bytes:
    """Decode dynamic bytes from a length-prefixed location."""
    length = decode_uint256(data, offset)
    return data[offset + WORD_SIZE:offset + WORD_SIZE + length]


def decode_function_call(calldata: bytes, param_types: list[ABIType]) -> tuple:
    """Decode a function call's calldata back into selector + argument values.

    Args:
        calldata: The raw calldata bytes (selector + encoded args)
        param_types: Expected parameter types for decoding

    Returns:
        (selector_hex, decoded_values) tuple
    """
    selector = calldata[:4]                # First 4 bytes
    args_data = calldata[4:]               # Everything after the selector
    selector_hex = "0x" + selector.hex()

    decoded = []
    for i, typ in enumerate(param_types):
        offset = i * WORD_SIZE

        if typ.is_dynamic():
            # Read the offset pointer, then decode at that location
            data_offset = decode_uint256(args_data, offset)
            if isinstance(typ, StringType):
                decoded.append(decode_string(args_data, data_offset))
            elif isinstance(typ, BytesType):
                decoded.append(decode_bytes_dynamic(args_data, data_offset))
            elif isinstance(typ, ArrayType):
                arr_data = args_data[data_offset:]
                count = decode_uint256(arr_data, 0)
                elements = []
                for j in range(count):
                    elem_offset = WORD_SIZE + j * WORD_SIZE
                    elements.append(decode_uint256(arr_data, elem_offset))
                decoded.append(elements)
            else:
                decoded.append(f"<dynamic:{typ}>")
        else:
            if isinstance(typ, Uint256Type):
                decoded.append(decode_uint256(args_data, offset))
            elif isinstance(typ, AddressType):
                decoded.append(decode_address(args_data, offset))
            elif isinstance(typ, BoolType):
                decoded.append(decode_bool(args_data, offset))
            else:
                decoded.append(args_data[offset:offset + WORD_SIZE])

    return selector_hex, decoded


# --- Display helpers -------------------------------------------------------

def format_calldata(data: bytes, label: str = "Calldata") -> str:
    """Format calldata as annotated 32-byte rows for visual display."""
    lines = [f"  {label} ({len(data)} bytes):"]
    lines.append(f"  {'─' * 68}")

    # First 4 bytes: selector
    if len(data) >= 4:
        sel = data[:4].hex()
        lines.append(f"  0x{sel}  ← function selector (4 bytes)")

    # Remaining data in 32-byte chunks
    args = data[4:]
    for i in range(0, len(args), WORD_SIZE):
        chunk = args[i:i + WORD_SIZE]
        hex_str = chunk.hex()
        word_num = i // WORD_SIZE
        # Try to annotate non-zero portions
        value = int.from_bytes(chunk, "big")
        if value == 0:
            annotation = "(zero)"
        elif value < 10000:
            annotation = f"(decimal: {value})"
        else:
            annotation = ""
        lines.append(f"  [{word_num:>2}] 0x{hex_str}  {annotation}")

    return "\n".join(lines)


# ============================================================================
# SECTION 3: DEMONSTRATION
# ============================================================================

def demo():
    """Run a visual demonstration of ABI encoding and decoding."""

    print("=" * 70)
    print("  ABI ENCODING — How Ethereum Encodes Function Calls")
    print("=" * 70)

    # --- Part 1: Function selectors ----------------------------------------
    print("\n--- Part 1: Function Selectors ---\n")
    print("  The function selector is the first 4 bytes of hash(signature).")
    print("  NOTE: Real Ethereum uses keccak256; we use SHA-256 as a stand-in.\n")

    signatures = [
        "transfer(address,uint256)",
        "approve(address,uint256)",
        "balanceOf(address)",
        "totalSupply()",
        "transferFrom(address,address,uint256)",
    ]

    print(f"  {'Signature':<40} {'Selector'}")
    print(f"  {'─' * 40} {'─' * 12}")
    for sig in signatures:
        sel = function_selector(sig)
        print(f"  {sig:<40} 0x{sel.hex()}")

    # --- Part 2: Static type encoding -------------------------------------
    print("\n--- Part 2: Static Type Encoding ---\n")
    print("  Static types are encoded directly as 32-byte words:\n")

    # uint256
    val_uint = 1000000
    enc_uint = encode_uint256(val_uint)
    print(f"  uint256({val_uint}):")
    print(f"    0x{enc_uint.hex()}")
    print(f"    (left-padded with zeros to 32 bytes)\n")

    # address
    val_addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    enc_addr = encode_address(val_addr)
    print(f"  address({val_addr[:20]}...):")
    print(f"    0x{enc_addr.hex()}")
    print(f"    (20-byte address in the low bytes, 12 zero bytes prefix)\n")

    # bool
    enc_true = encode_bool(True)
    enc_false = encode_bool(False)
    print(f"  bool(true):  0x{enc_true.hex()}")
    print(f"  bool(false): 0x{enc_false.hex()}")
    print(f"    (encoded as uint256: 1 or 0)\n")

    # bytes4
    val_b4 = b"\xde\xad\xbe\xef"
    enc_b4 = encode_bytesN(val_b4, 4)
    print(f"  bytes4(0xdeadbeef):")
    print(f"    0x{enc_b4.hex()}")
    print(f"    (RIGHT-padded, unlike uint256 which is left-padded)")

    # --- Part 3: Encoding transfer(address, uint256) -----------------------
    print("\n--- Part 3: Encoding transfer(address, uint256) ---\n")

    transfer_sig = "transfer(address,uint256)"
    transfer_types = [AddressType(), Uint256Type()]
    recipient = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    amount = 1500000000000000000  # 1.5 ETH in wei

    calldata = encode_function_call(transfer_sig, transfer_types,
                                     [recipient, amount])

    print(format_calldata(calldata, "transfer() calldata"))

    print(f"\n  This is exactly what goes into a transaction's 'data' field")
    print(f"  when you call transfer() on an ERC-20 contract.")

    # --- Part 4: Dynamic type encoding -------------------------------------
    print("\n--- Part 4: Dynamic Type Encoding (string, bytes) ---\n")
    print("  Dynamic types use offset pointers in the head + data in the tail:\n")

    # Encode a function with both static and dynamic params
    # greet(string name, uint256 age)
    greet_sig = "greet(string,uint256)"
    greet_types = [StringType(), Uint256Type()]
    greet_values = ["Hello, Ethereum!", 42]

    calldata2 = encode_function_call(greet_sig, greet_types, greet_values)
    print(format_calldata(calldata2, "greet() calldata"))

    print(f"\n  Word [0] = 0x{decode_uint256(calldata2[4:], 0):064x}")
    print(f"    → offset pointer: decimal {decode_uint256(calldata2[4:], 0)} "
          f"(points to word [{decode_uint256(calldata2[4:], 0) // 32}])")
    print(f"  Word [1] = decimal {decode_uint256(calldata2[4:], 32)} (the uint256 age)")
    print(f"  Word [2] = decimal {decode_uint256(calldata2[4:], 64)} "
          f"(string length in bytes)")
    string_start = 4 + 64 + 32
    string_len = decode_uint256(calldata2[4:], 64)
    print(f"  Word [3] = \"{calldata2[string_start:string_start + string_len].decode()}\" "
          f"(the actual string data, right-padded)")

    # --- Part 5: Array encoding --------------------------------------------
    print("\n--- Part 5: Array Encoding ---\n")

    # batchTransfer(address[], uint256[])
    batch_sig = "batchTransfer(address[],uint256[])"
    batch_types = [ArrayType(AddressType()), ArrayType(Uint256Type())]

    addrs = [
        "0x" + "11" * 20,
        "0x" + "22" * 20,
        "0x" + "33" * 20,
    ]
    amounts = [100, 200, 300]

    calldata3 = encode_function_call(batch_sig, batch_types, [addrs, amounts])
    print(format_calldata(calldata3, "batchTransfer() calldata"))

    print(f"\n  Two dynamic arrays → two offset pointers in the head,")
    print(f"  each pointing to [count][elem1][elem2][elem3] in the tail.")

    # --- Part 6: Decoding calldata -----------------------------------------
    print("\n--- Part 6: Decoding Calldata ---\n")

    print("  Decoding the transfer() calldata back to values:\n")

    sel_hex, decoded = decode_function_call(calldata, transfer_types)
    print(f"  Selector:  {sel_hex}")
    print(f"  Param [0]: {decoded[0]} (address)")
    print(f"  Param [1]: {decoded[1]} (uint256)")
    print(f"             = {decoded[1] / 10**18:.1f} ETH (at 18 decimals)")

    # --- Part 7: Tuple encoding --------------------------------------------
    print("\n--- Part 7: Tuple Encoding ---\n")

    print("  Tuples group multiple values. A tuple is dynamic if any element is.\n")

    # createOrder((address seller, uint256 price, string description))
    order_sig = "createOrder((address,uint256,string))"
    order_tuple = TupleType([AddressType(), Uint256Type(), StringType()])
    order_types = [order_tuple]
    order_values = [["0x" + "aa" * 20, 5000, "Widget"]]

    calldata4 = encode_function_call(order_sig, order_types, order_values)
    print(format_calldata(calldata4, "createOrder() calldata"))

    print(f"\n  The tuple itself is dynamic (contains a string), so the head")
    print(f"  contains an offset pointer to the tuple's encoded data.")

    # --- Summary -----------------------------------------------------------
    print("\n" + "=" * 70)
    print("  ENCODING RULES SUMMARY")
    print("─" * 70)
    print("  Static types (uint256, address, bool, bytesN):")
    print("    → Encoded in-place as 32-byte words")
    print("    → uint/address/bool: left-padded; bytesN: right-padded")
    print()
    print("  Dynamic types (string, bytes, T[]):")
    print("    → Head: 32-byte offset pointer")
    print("    → Tail: [length][padded data]")
    print()
    print("  Function call = [4-byte selector] + [ABI-encoded arguments]")
    print("  Selector = first 4 bytes of keccak256(signature)")
    print("  (We used SHA-256 as a stand-in — same logic, different hash)")
    print("=" * 70)


# ============================================================================
# SECTION 4: ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    demo()
