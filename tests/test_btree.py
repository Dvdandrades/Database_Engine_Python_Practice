from db.indexing.btree import BTree, BTreeNode
from db.indexing.manager import IndexManager


def test_btree_node_initialization():
    node = BTreeNode(leaf=True)
    assert node.leaf is True
    assert node.keys == []
    assert node.values == []
    assert node.children == []


def test_btree_basic_insert_and_search():
    tree = BTree(degree=3)

    tree.insert(10, "A")
    tree.insert(20, "B")
    tree.insert(5, "C")

    assert tree.search(10) == "A"
    assert tree.search(20) == "B"
    assert tree.search(5) == "C"
    assert tree.search(99) is None


def test_btree_split():
    tree = BTree(degree=2)

    tree.insert(10, "v10")
    tree.insert(20, "v20")
    tree.insert(30, "v30")
    tree.insert(40, "v40")

    assert tree.root.leaf is False
    assert len(tree.root.keys) == 1
    assert tree.root.keys[0] == 20
    assert len(tree.root.children) == 2

    assert tree.search(10) == "v10"
    assert tree.search(20) == "v20"
    assert tree.search(30) == "v30"
    assert tree.search(40) == "v40"


class TestIndexManager:
    def setup_method(self):
        self.manager = IndexManager()

    def test_create_index(self):
        index_name = self.manager.create_index("users", "email")

        assert index_name == "$users_$email_idx"
        assert index_name in self.manager.indexes
        assert "email" in self.manager.get_indexed_fields("users")

    def test_insert_and_search_index(self):
        idx_name = self.manager.create_index("users", "age")

        self.manager.insert(idx_name, 30, "user_1")
        self.manager.insert(idx_name, 30, "user_2")
        self.manager.insert(idx_name, 25, "user_3")

        res_30 = self.manager.search(idx_name, 30)
        assert isinstance(res_30, list)
        assert "user_1" in res_30
        assert "user_2" in res_30

        res_25 = self.manager.search(idx_name, 25)
        assert res_25 == ["user_3"]

        assert self.manager.search(idx_name, 99) is None

    def test_rebuild_index(self):
        self.manager.create_index("products", "category")
        records = {
            "prod_1": {"category": "electronics", "price": 100},
            "prod_2": {"category": "books", "price": 20},
            "prod_3": {"category": "electronics", "price": 150},
            "prod_4": {"name": "unknown"},
        }

        self.manager.rebuild_index("products", "category", records)
        idx_name = "$products_$category_idx"

        assert self.manager.search(idx_name, "electronics") == ["prod_1", "prod_3"]
        assert self.manager.search(idx_name, "books") == ["prod_2"]
        assert self.manager.search(idx_name, "unknown") is None
