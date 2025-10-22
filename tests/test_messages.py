import struct
from src.messages import (
    HANDSHAKE_FIRST, encode_handshake, decode_handshake, encode_message, 
    decode_message, CHOKE, INTERESTED, NOT_INTERESTED, HAVE, BITFIELD
)

def test_handshake_roundtrip():
    bytes_obj = encode_handshake(1001) # This builds a handshake for peer_ID 1001
    assert len(bytes_obj) == 32 # Ensure that the bytes obj has 32 bytes
    assert bytes_obj[:28] == HANDSHAKE_FIRST # Ensure that the first 28 bytes are the Header + Zeroes
    assert decode_handshake(bytes_obj) == 1001 # Ensure that the peer_ID stays the same

def test_message_roundtrip_no_payload(): # Checks if the round trip choke message stays the same
    buffer = bytearray(encode_message(CHOKE)) 
    msg_type, payload = decode_message(buffer)
    assert msg_type == CHOKE and payload == b""

def test_encode_message_raw_choke(): # Checks the actual bytes after encoding a choke message
    frame = encode_message(CHOKE)
    assert frame[:4] == b"\x00\x00\x00\x01"
    assert frame[4] == CHOKE
    assert len(frame) == 5

def test_message_roundtrip_payload():
    payload = (7).to_bytes(4, "big") # HAVE Message with payload
    buffer = bytearray(encode_message(HAVE, payload))
    msg_type, payload_received = decode_message(buffer)
    assert msg_type == HAVE and int.from_bytes(payload_received, "big") == 7 # payload bytes decoded must be the same

def test_two_messages_and_partial_reads():
    # INTERESTED: [00 00 00 01][02]
    # NOT_INTERESTED: [00 00 00 01][03]
    frame = encode_message(INTERESTED) + encode_message(NOT_INTERESTED)
    buffer = bytearray()
    for byte in frame:  # drip-feed one byte at a time
        buffer.append(byte)
        decoded = decode_message(buffer)
        if decoded:
            msg_type, payload = decoded
            assert payload == b"" # No payloads 
            assert msg_type in (INTERESTED, NOT_INTERESTED)