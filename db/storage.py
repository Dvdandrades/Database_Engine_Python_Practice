import json
import struct
from pathlib import Path
from typing import Any

TOMBSTONE = b"__TOMBSTONE__"


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
        self.keydir: dict[str, tuple[int, int]] = {}

        if not self.data_file.exists():
            self._init_db()
        else:
            self._build_keydir()
            self._recover_from_wal()

    def _init_db(self):
        with open(self.data_file, "wb") as f:
            f.write(struct.pack(">I", 1))
        self._build_keydir()

    def _build_keydir(self):
        self.keydir.clear()
        if not self.data_file.exists():
            return

        with open(self.data_file, "rb") as f:
            f.read(4)
            while True:
                offset = f.tell()
                key_len_bytes = f.read(4)
                if len(key_len_bytes) < 4:
                    break

                key_len = struct.unpack(">I", key_len_bytes)[0]
                key = f.read(key_len).decode("utf-8")

                val_len = struct.unpack(">I", f.read(4))[0]
                val_bytes = f.read(val_len)

                total_len = f.tell() - offset

                if val_bytes == TOMBSTONE:
                    self.keydir.pop(key, None)
                else:
                    self.keydir[key] = (offset, total_len)

    def write_wal(self, op: str, key: str, value: Any = None):
        with open(self.log_file, "a", encoding="utf-8") as f:
            entry = json.dumps({"op": op, "key": key, "val": value})
            f.write(f"{entry}\n")

    def _raw_put(self, key: str, value: dict):
        data_bytes = json.dumps(value).encode("utf-8")
        key_bytes = key.encode("utf-8")

        with open(self.data_file, "ab") as f:
            offset = f.tell()
            f.write(struct.pack(">I", len(key_bytes)))
            f.write(key_bytes)
            f.write(struct.pack(">I", len(data_bytes)))
            f.write(data_bytes)
            total_len = f.tell() - offset

        self.keydir[key] = (offset, total_len)

    def _raw_delete(self, key: str):
        key_bytes = key.encode("utf-8")

        with open(self.data_file, "ab") as f:
            f.write(struct.pack(">I", len(key_bytes)))
            f.write(key_bytes)
            f.write(struct.pack(">I", len(TOMBSTONE)))
            f.write(TOMBSTONE)

        self.keydir.pop(key, None)

    def clear_wal(self):
        if self.log_file.exists():
            self.log_file.unlink()

    def _recover_from_wal(self):
        if not self.log_file.exists():
            return

        print("Recovering data from WAL...")
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry["op"] == "PUT":
                        self._raw_put(entry["key"], entry["val"])
                    elif entry["op"] == "DELETE":
                        self._raw_delete(entry["key"])
                except (json.JSONDecodeError, KeyError):
                    continue

        self.clear_wal()

    def get(self, key: str) -> dict | None:
        if key not in self.keydir:
            return None

        offset, _ = self.keydir[key]
        with open(self.data_file, "rb") as f:
            f.seek(offset)
            key_len = struct.unpack(">I", f.read(4))[0]
            f.read(key_len)
            val_len = struct.unpack(">I", f.read(4))[0]
            val_data = f.read(val_len)
            return json.loads(val_data.decode("utf-8"))

    def put(self, key: str, value: dict):
        self.write_wal("PUT", key, value)
        self._raw_put(key, value)

    def delete(self, key: str):
        if key not in self.keydir:
            return

        self.write_wal("DELETE", key)
        self._raw_delete(key)

    def compact(self):
        temp_file = self.db_path / "data_db.tmp"
        new_keydir = {}

        with open(temp_file, "wb") as f_out:
            f_out.write(struct.pack(">I", 1))

            with open(self.data_file, "rb") as f_in:
                for key, (offset, _) in self.keydir.items():
                    f_in.seek(offset)
                    key_len = struct.unpack(">I", f_in.read(4))[0]
                    k_bytes = f_in.read(key_len)
                    val_len = struct.unpack(">I", f_in.read(4))[0]
                    val_bytes = f_in.read(val_len)

                    new_offset = f_out.tell()
                    f_out.write(struct.pack(">I", len(k_bytes)))
                    f_out.write(k_bytes)
                    f_out.write(struct.pack(">I", len(val_bytes)))
                    f_out.write(val_bytes)

                    total_len = f_out.tell() - new_offset
                    new_keydir[key] = (new_offset, total_len)

        temp_file.replace(self.data_file)
        self.keydir = new_keydir
        self.clear_wal()
