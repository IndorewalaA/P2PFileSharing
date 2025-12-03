import socket
import threading
import time
from messages import encode_handshake, decode_handshake
from config import parse_config, parse_peer_info
from message_handler import send_message, recv_message, INTERESTED


def test_config_files():
    print("Testing config file parsing...")
    c = parse_config()
    peers = parse_peer_info()
    assert c.file_size > 0
    assert len(peers) > 0
    print("✓ Config OK")


def test_handshake_roundtrip():
    print("Testing handshake encode/decode...")
    msg = encode_handshake(1234)
    assert decode_handshake(msg) == 1234
    print("✓ Handshake OK")


def test_socket_message_exchange():
    print("Testing message exchange over loopback...")

    PORT = 60000
    def listener():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("localhost", PORT))
        s.listen(1)
        conn, _ = s.accept()

        # read handshake
        data = conn.recv(32)
        their_id = decode_handshake(data)
        conn.sendall(encode_handshake(9999))

        # read a full message
        msg_type, payload = recv_message(conn)
        assert msg_type == INTERESTED
        assert payload == b"hello"

        print("✓ Message exchange OK")
        conn.close()
        s.close()

    threading.Thread(target=listener, daemon=True).start()
    time.sleep(0.5)

    # client
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c.connect(("localhost", PORT))
    c.sendall(encode_handshake(7777))

    # receive handshake back
    resp = c.recv(32)
    assert decode_handshake(resp) == 9999

    # send message
    send_message(c, INTERESTED, b"hello")
    c.close()


if __name__ == "__main__":
    test_config_files()
    test_handshake_roundtrip()
    test_socket_message_exchange()
    print("\nAll tests passed!\n")
