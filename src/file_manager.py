import os

class FileManager:
    def __init__(self, file_path: str, piece_size: int):
        self.file_path = file_path
        self.piece_size = piece_size

    def split_file(self) -> list:
        pieces = []
        if not os.path.exists(self.file_path):
            return pieces
        with open(self.file_path, 'rb') as f:
            while True:
                chunk = f.read(self.piece_size)
                if not chunk:
                    break
                pieces.append(chunk)
        return pieces

    def write_piece(self, index: int, data: bytes):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'wb') as f:
                pass
        with open(self.file_path, 'r+b') as f:
            f.seek(index * self.piece_size)
            f.write(data)

    def get_piece(self, index: int) -> bytes:
        if not os.path.exists(self.file_path):
            return b""
        with open(self.file_path, 'rb') as f:
            f.seek(index * self.piece_size)
            return f.read(self.piece_size)

    def is_complete(self, total_pieces: int) -> bool:
        if not os.path.exists(self.file_path):
            return False
        size = os.path.getsize(self.file_path)
        return size >= (total_pieces - 1) * self.piece_size