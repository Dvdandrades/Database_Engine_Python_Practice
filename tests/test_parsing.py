import pytest

from db.parsing.ast import ConditionNode, LogicalNode
from db.parsing.lexer import Lexer
from db.parsing.parser import QueryParser


def test_lexer_tokenization():
    sql = "SELECT id, 'John Doe' FROM users WHERE age >= 18"
    lexer = Lexer(sql)

    assert lexer.current_token == ("KEYWORD", "SELECT")
    lexer.consume("KEYWORD", "SELECT")

    assert lexer.current_token == ("IDENT", "id")
    lexer.consume("IDENT")

    assert lexer.current_token == ("PUNC", ",")
    lexer.consume("PUNC")

    assert lexer.current_token == ("STRING", "'John Doe'")


def test_lexer_invalid_character():
    with pytest.raises(ValueError, match="Unexpected character"):
        Lexer("SELECT * FROM users %")


class TestQueryParser:
    def setup_method(self):
        self.parser = QueryParser()

    def test_parse_create_table_and_index(self):
        query_table = self.parser.parse("CREATE TABLE users")
        assert query_table.operation == "CREATE"
        assert query_table.table == "users"

        query_idx = self.parser.parse("CREATE INDEX ON users (name)")
        assert query_idx.operation == "CREATE_INDEX"
        assert query_idx.table == "users"
        assert query_idx.fields == ["name"]

    def test_parse_insert(self):
        sql = "INSERT INTO users (name, email) VALUES ('David', 'david@test.com')"
        query = self.parser.parse(sql)

        assert query.operation == "INSERT"
        assert query.table == "users"
        assert query.values == {"name": "David", "email": "david@test.com"}

    def test_parse_insert_mismatch_fields(self):
        sql = "INSERT INTO users (name, email) VALUES ('David')"
        with pytest.raises(ValueError, match="Mismatched fields and values count"):
            self.parser.parse(sql)

    def test_parse_select_basic(self):
        sql = "SELECT id, name FROM users"
        query = self.parser.parse(sql)

        assert query.operation == "SELECT"
        assert query.table == "users"
        assert query.fields == ["id", "name"]
        assert query.conditions is None

    def test_parse_select_with_complex_where(self):
        sql = "SELECT * FROM users WHERE age >= 18 AND status = 'active' OR role = 'admin'"
        query = self.parser.parse(sql)

        assert query.operation == "SELECT"
        assert query.table == "users"
        assert query.fields == []

        assert isinstance(query.conditions, LogicalNode)
        assert query.conditions.op == "OR"

        assert isinstance(query.conditions.right, ConditionNode)
        assert query.conditions.right.left == "role"
        assert query.conditions.right.right == "admin"

        left_node = query.conditions.left
        assert isinstance(left_node, LogicalNode)
        assert left_node.op == "AND"
        assert left_node.left.left == "age"
        assert left_node.left.right == "18"

    def test_parse_update(self):
        sql = "UPDATE users SET status = 'inactive', role = 'guest' WHERE id = 1"
        query = self.parser.parse(sql)

        assert query.operation == "UPDATE"
        assert query.table == "users"
        assert query.values == {"status": "inactive", "role": "guest"}

        assert isinstance(query.conditions, ConditionNode)
        assert query.conditions.left == "id"
        assert query.conditions.op == "="
        assert query.conditions.right == "1"

    def test_parse_delete(self):
        sql = "DELETE FROM users WHERE name = 'John'"
        query = self.parser.parse(sql)

        assert query.operation == "DELETE"
        assert query.table == "users"

        assert isinstance(query.conditions, ConditionNode)
        assert query.conditions.left == "name"
        assert query.conditions.right == "John"

    def test_parse_transactions(self):
        assert self.parser.parse("BEGIN").operation == "BEGIN"
        assert self.parser.parse("COMMIT").operation == "COMMIT"
        assert self.parser.parse("ROLLBACK").operation == "ROLLBACK"

    def test_invalid_syntax(self):
        with pytest.raises(ValueError):
            self.parser.parse("DROP TABLE users")
