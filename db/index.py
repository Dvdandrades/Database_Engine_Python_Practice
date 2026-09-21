from typing import Any


class BTreeNode:
    def __init__(self, leaf: bool = True):
        self.leaf = leaf
        self.keys: list[Any] = []
        self.values: list[Any] = []
        self.children: list[BTreeNode] = []


class BTree:
    def __init__(self, degree: int = 3):
        self.degree = degree
        self.root = BTreeNode(leaf=True)

    def search(self, key: Any) -> Any | None:
        return self._search(self.root, key)

    def _search(self, node: BTreeNode, key: Any) -> Any | None:
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1

        if i < len(node.keys) and key == node.keys[i]:
            return node.values[i]

        if node.leaf:
            return None

        return self._search(node.children[i], key)

    def insert(self, key: Any, value: Any):
        if len(self.root.keys) == 2 * self.degree - 1:
            new_root = BTreeNode(leaf=False)
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root

        self._insert_non_full(self.root, key, value)

    def _split_child(self, parent: BTreeNode, index: int):
        child = parent.children[index]
        new_child = BTreeNode(leaf=child.leaf)

        mid_key = child.keys[self.degree - 1]
        mid_value = child.values[self.degree - 1]

        new_child.keys = child.keys[self.degree :]
        new_child.values = child.values[self.degree :]

        if not child.leaf:
            child.children = child.children[: self.degree]

        parent.children.insert(index + 1, new_child)
        parent.keys.insert(index, mid_key)
        parent.values.insert(index, mid_value)

    def _insert_non_full(self, node: BTreeNode, key: Any, value: Any):
        i = len(node.keys) - 1

        if node.leaf:
            while i >= 0 and key < node.keys[i]:
                i -= 1

            node.keys.insert(i + 1, key)
            node.values.insert(i + 1, value)
        else:
            while i >= 0 and key < node.keys[i]:
                i -= 1

            i += 1

            if len(node.children[i].keys) == 2 * self.degree - 1:
                self._split_child(node, i)

                if key > node.keys[i]:
                    i += 1

            self._insert_non_full(node.children[i], key, value)


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
