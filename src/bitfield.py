from typing import List

class Bitfield:
    def __init__(self, num_pieces: int):
        self.num_pieces = num_pieces
        self.bits = bytearray((num_pieces + 7) // 8)

    def set_piece(self, index: int):
        self.bits[index // 8] |= 1 << (7 - (index % 8))

    def has_piece(self, index: int) -> bool:
        return bool(self.bits[index // 8] & (1 << (7 - (index % 8))))

    def to_bytes(self) -> bytes:
        return bytes(self.bits)

    def from_bytes(self, data: bytes):
        needed = (self.num_pieces + 7) // 8
        self.bits = bytearray(data[:needed].ljust(needed, b'\x00'))

    def missing_pieces_from(self, other: 'Bitfield') -> List[int]:
        missing = []
        for i in range(self.num_pieces):
            if not self.has_piece(i) and other.has_piece(i):
                missing.append(i)
        return missing

    def is_complete(self) -> bool:
        for i in range(self.num_pieces):
            if not self.has_piece(i):
                return False
        return True
