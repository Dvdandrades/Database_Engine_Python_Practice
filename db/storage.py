import json
import struct
from pathlib import Path


class Page:
    PAGE_SIZE = 4096

    def __init__(self, page_id: int = 0):
        self.page_id = page_id
        self.data = bytearray(self.PAGE_SIZE)

    def read(self, offset: int, size: int) -> bytes:
        return bytes(self.data[offset : offset + size])

    def write(self, offset: int, data: bytes):
        self.data[offset : offset + len(data)] = data


class StorageEngine:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.data_file = self.db_path / "data.db"
        self.log_file = self.db_path / "wal.log"

        if not self.data_file.exists():
            self._init_db()

    def _init_db(self):
        with open(self.data_file, "wb") as f:
            f.write(struct.pack(">I", 1))

    def write_record(self, key: str, value: dict) -> int:
        key_bytes = key.encode("utf-8")
        data = json.dumps(value).encode("utf-8")

        with open(self.data_file, "ab") as f:
            f.write(struct.pack(">I", len(key_bytes)))
            f.write(key_bytes)
            f.write(struct.pack(">I", len(data)))
            f.write(data)
            return f.tell()

    def read_all_records(self) -> dict[str, dict]:
        records = {}

        with open(self.data_file, "rb") as f:
            f.read(4)

            while True:
                key_len_data = f.read(4)
                if len(key_len_data) < 4:
                    break

                key_len = struct.unpack(">I", key_len_data)[0]
                key = f.read(key_len).decode("utf-8")

                val_len = struct.unpack(">I", f.read(4))[0]
                data = f.read(val_len)
                value = json.loads(data.decode("utf-8"))

                records[key] = value

        return records

    def get(self, key: str) -> dict | None:
        records = self.read_all_records()
        return records.get(key)

    def put(self, key: str, value: dict):
        self.write_record(key, value)

    def delete(self, key: str):
        records = self.read_all_records()
        if key in records:
            del records[key]
            self._rewrite_db(records)

    def _rewrite_db(self, records: dict):
        temp_file = self.db_path / "data_db.tmp"

        with open(temp_file, "wb") as f:
            f.write(struct.pack(">I", 1))
            for key, value in records.items():
                key_bytes = key.encode("utf-8")
                data = json.dumps(value).encode("utf-8")
                f.write(struct.pack(">I", len(key_bytes)))
                f.write(key_bytes)
                f.write(struct.pack(">I", len(data)))
                f.write(data)

            temp_file.replace(self.data_file)
