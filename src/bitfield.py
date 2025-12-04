from typing import List

class Bitfield:
    # 1 if has piece, 0 if missing
    def __init__(self, num_pieces: int):
        self.num_pieces = num_pieces
        # required bytes = (n + 7) // 8
        self.bits = bytearray((num_pieces + 7) // 8)

    # set bit at index to 1 
    def set_piece(self, index: int):
        self.bits[index // 8] |= 1 << (7 - (index % 8))

    # returns true if bit at index is 1
    def has_piece(self, index: int) -> bool:
        return bool(self.bits[index // 8] & (1 << (7 - (index % 8))))

    # returns bytes to be transmitted
    def to_bytes(self) -> bytes:
        return bytes(self.bits)

    # converts incoming data to bytes
    def from_bytes(self, data: bytes):
        needed = (self.num_pieces + 7) // 8
        self.bits = bytearray(data[:needed].ljust(needed, b'\x00'))

    # returns arr of pieces that we dont have but other peer has
    def missing_pieces_from(self, other: 'Bitfield') -> List[int]:
        missing = []
        for i in range(self.num_pieces):
            if not self.has_piece(i) and other.has_piece(i):
                missing.append(i)
        return missing

    # returns true if we have the full file
    def is_complete(self) -> bool:
        for i in range(self.num_pieces):
            if not self.has_piece(i):
                return False
        return True