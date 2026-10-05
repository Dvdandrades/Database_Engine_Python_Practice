from typing import Any

from .btree import BTree


class IndexManager:
    def __init__(self):
        self.indexes: dict[str, BTree] = {}
        self.table_fields: dict[str, set[str]] = {}

    def create_index(self, table: str, field: str) -> str:
        index_name = f"${table}_${field}_idx"
        if index_name not in self.indexes:
            self.indexes[index_name] = BTree()
            if table not in self.table_fields:
                self.table_fields[table] = set()
            self.table_fields[table].add(field)
        return index_name

    def insert(self, index_name: str, key: Any, value: Any):
        if index_name in self.indexes:
            btree = self.indexes[index_name]
            existing_list = btree.search(key)
            if existing_list is not None:
                if value not in existing_list:
                    existing_list.append(value)
            else:
                btree.insert(key, [value])

    def search(self, index_name: str, key: Any) -> list[Any] | None:
        if index_name in self.indexes:
            return self.indexes[index_name].search(key)
        return None

    def get_indexed_fields(self, table: str) -> set[str]:
        return self.table_fields.get(table, set())

    def rebuild_index(self, table: str, field: str, records: dict):
        index_name = f"${table}_${field}_idx"
        self.indexes[index_name] = BTree()
        for rid, record in records.items():
            if field in record:
                self.insert(index_name, record[field], rid)
