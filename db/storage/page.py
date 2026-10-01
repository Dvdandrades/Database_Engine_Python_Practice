class Page:
    PAGE_SIZE = 4096

    def __init__(self, page_id: int = 0):
        self.page_id = page_id
        self.data = bytearray(self.PAGE_SIZE)

    def read(self, offset: int, size: int) -> bytes:
        return bytes(self.data[offset : offset + size])

    def write(self, offset: int, data: bytes):
        self.data[offset : offset + len(data)] = data
