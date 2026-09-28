import re
from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass
class ASTNode:
    pass


@dataclass
class BinaryOp(ASTNode):
    left: str
    op: str
    right: Any


@dataclass
class SelectNode(ASTNode):
    table: str
    fields: list[str]
    where: BinaryOp | None = None


@dataclass
class ConditionNode(ASTNode):
    left: str
    op: str
    right: Any


@dataclass
class LogicalNode(ASTNode):
    left: ASTNode
    op: str
    right: ASTNode


class Query:
    def __init__(
        self,
        operation: str,
        table: str = "",
        conditions: Any = None,
        values: dict | None = None,
        fields: list[str] | None = None,
    ):
        self.operation = operation
        self.table = table
        self.conditions = conditions
        self.values = values or {}
        self.fields = fields or []


class Lexer:
    TOKENS: ClassVar[list[tuple[str, str]]] = [
        ("STRING", r"'[^']*'|\"[^\"]*\""),
        ("NUMBER", r"\d+(\.\d+)?"),
        (
            "KEYWORD",
            r"\b(SELECT|FROM|WHERE|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|TABLE|INDEX|ON|AND|OR|BEGIN|COMMIT|ROLLBACK|ABORT)\b",
        ),
        ("OP", r"!=|>=|<=|=|<|>|\bLIKE\b"),
        ("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("PUNC", r"[\(\)\*,;]"),
        ("WS", r"\s+"),
    ]

    def __init__(self, text: str):
        self.text = text.strip()
        self.pos = 0
        self.current_token = None
        self.tok_regex = "|".join(
            f"(?P<{name}>{pattern})" for name, pattern in self.TOKENS
        )
        self.advance()

    def advance(self):
        if self.pos >= len(self.text):
            self.current_token = ("EOF", None)
            return

        match = re.compile(self.tok_regex, re.IGNORECASE).match(self.text, self.pos)
        if not match:
            raise ValueError(
                f"Unexpect character in position {self.pos}: {self.text[self.pos]}"
            )

        self.pos = match.end()
        tok_type = match.lastgroup
        tok_val = match.group(tok_type)

        if tok_type == "WS":
            self.advance()
        else:
            self.current_token = (tok_type, tok_val)

    def consume(self, expected_type: str, expected_val: str | None = None) -> str:
        tok_type, tok_val = self.current_token
        if tok_type == expected_type and (
            expected_val is None or tok_val.upper() == expected_val.upper()
        ):
            self.advance()
            return tok_val
        raise ValueError(
            f"Expecting {expected_type} {expected_val or ''}, got {tok_type} '{tok_val}'"
        )


class QueryParser:
    def parse(self, sql: str) -> Query:
        lexer = Lexer(sql)
        tok_type, tok_val = lexer.current_token

        if tok_type == "KEYWORD":
            op = tok_val.upper()
            if op == "SELECT":
                ast = self._parse_select(lexer)
                return self._ast_to_query(ast)
            elif op == "INSERT":
                return self._parse_insert_(sql)
            elif op == "UPDATE":
                return self._parse_update_(sql)
            elif op == "DELETE":
                return self._parse_delete_(sql)
            elif op == "CREATE":
                return self._parse_create_(sql)
            elif op == "BEGIN":
                return self._parse_begin_(sql)
            elif op == "COMMIT":
                return self._parse_commit_(sql)
            elif op in ("ROLLBACK", "ABORT"):
                return self._parse_rollback_(sql)

        raise ValueError(f"Operation not supported or invalid syntax: {sql}")

    def _parse_begin_(self, sql: str) -> Query:
        return Query("BEGIN")

    def _parse_commit_(self, sql: str) -> Query:
        return Query("COMMIT")

    def _parse_rollback_(self, sql: str) -> Query:
        return Query("ROLLBACK")

    def _parse_abort_(self, sql: str) -> Query:
        return Query("ROLLBACK")

    def _parse_create_(self, sql: str) -> Query:
        idx_pattern = r"^CREATE\s+INDEX\s+(?:\w+\s+)?ON\s+(\w+)\s*\(\s*(\w+)\s*\)\s*;?$"
        idx_match = re.match(idx_pattern, sql, re.IGNORECASE)

        if idx_match:
            table, field = idx_match.groups()
            return Query("CREATE_INDEX", table, fields=[field])

        table_pattern = r"^CREATE\s+TABLE\s+(\w+)\s*;?$"
        table_match = re.match(table_pattern, sql, re.IGNORECASE)

        if not table_match:
            raise ValueError(f"Invalid CREATE syntax: '{sql}'")

        table = table_match.group(1)

        return Query("CREATE", table)

    def _parse_select(self, lexer: Lexer) -> SelectNode:
        lexer.consume("KEYWORD", "SELECT")

        fields = []
        if lexer.current_token[0] == "PUNC" and lexer.current_token[1] == "*":
            lexer.consume("PUNC", "*")
        else:
            fields.append(lexer.consume("IDENT"))
            while lexer.current_token[0] == "PUNC" and lexer.current_token[1] == ",":
                lexer.consume("PUNC", ",")
                fields.append(lexer.consume("IDENT"))

        lexer.consume("KEYWORD", "FROM")
        table = lexer.consume("IDENT")

        condition = None
        if (
            lexer.current_token[0] == "KEYWORD"
            and lexer.current_token[1].upper() == "WHERE"
        ):
            lexer.consume("KEYWORD", "WHERE")
            condition = self._parse_expression(lexer)

        return SelectNode(table=table, fields=fields, where=condition)

    def _parse_expression(self, lexer: Lexer) -> ASTNode:
        node = self._parse_term(lexer)

        while (
            lexer.current_token[0] == "KEYWORD"
            and lexer.current_token[1].upper() == "OR"
        ):
            op = lexer.consume("KEYWORD", "OR").upper()
            right = self._parse_term(lexer)
            node = LogicalNode(left=node, op=op, right=right)

        return node

    def _parse_term(self, lexer: Lexer) -> ASTNode:
        node = self._parse_factor(lexer)

        while (
            lexer.current_token[0] == "KEYWORD"
            and lexer.current_token[1].upper() == "AND"
        ):
            op = lexer.consume("KEYWORD", "AND").upper()
            right = self._parse_factor(lexer)
            node = LogicalNode(left=node, op=op, right=right)

        return node

    def _parse_factor(self, lexer: Lexer) -> ASTNode:
        left = lexer.consume("IDENT")
        op = lexer.consume("OP").upper()

        tok_type, tok_val = lexer.current_token
        if tok_type in ("STRING", "NUMBER"):
            right = lexer.consume(tok_type)
            if tok_type == "STRING":
                right = right[1:-1]
        else:
            raise ValueError(f"Expecting literal value, got: {tok_val}")

        return ConditionNode(left=left, op=op, right=right)

    def _ast_to_query(self, node: ASTNode) -> Query:
        if isinstance(node, SelectNode):
            return Query(
                operation="SELECT",
                table=node.table,
                fields=node.fields,
                conditions=node.where,
            )
        raise NotImplementedError("Conversion AST not implemented for this node")

    def _parse_insert_(self, sql: str) -> Query:
        pattern = r"^INSERT\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)\s*;?$"
        match = re.match(pattern, sql, re.IGNORECASE)

        if not match:
            raise ValueError(f"Invalid INSERT syntax: '{sql}'")

        table, fields_str, values_str = match.groups()

        fields = [f.strip() for f in fields_str.split(",")]
        values = [v.strip().strip("'\"") for v in values_str.split(",")]

        if len(fields) != len(values):
            raise ValueError("Mismatched fields and values count in INSERT statement")

        values_dict = dict(zip(fields, values))

        return Query("INSERT", table, values=values_dict)

    def _parse_update_(self, sql: str) -> Query:
        pattern = r"^UPDATE\s+(\w+)\s+SET\s+(.*)\s*;?$"
        match = re.match(pattern, sql, re.IGNORECASE)

        if not match:
            raise ValueError(f"Invalid UPDATE syntax: '{sql}'")

        table, rest = match.groups()

        where_split = re.split(r"\s+WHERE\s+", rest, flags=re.IGNORECASE)
        set_str = where_split[0]
        conditions_str = where_split[1] if len(where_split) > 1 else None

        set_pairs = [s.strip() for s in set_str.split(",")]
        values = {}
        for pair in set_pairs:
            if "=" not in pair:
                raise ValueError(f"Invalid SET pair: '{pair}'")
            key, val = pair.split("=", 1)
            values[key.strip()] = val.strip().strip("'\"")

        conditions = self._parse_conditions(conditions_str) if conditions_str else None

        return Query("UPDATE", table, conditions, values)

    def _parse_delete_(self, sql: str) -> Query:
        pattern = r"^DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*))?\s*;?$"
        match = re.match(pattern, sql, re.IGNORECASE)

        if not match:
            raise ValueError(f"Invalid DELETE syntax: '{sql}'")

        table, conditions_str = match.groups()
        conditions = self._parse_conditions(conditions_str) if conditions_str else None

        return Query("DELETE", table, conditions)

    def _parse_conditions(self, cond_str: str) -> Any:
        if not cond_str:
            return None

        cond_pattern = r'(\w+)\s*(=|!=|<|>|<=|>=|LIKE)\s*(?:(["\'])(.*?)\3|(\w+))'

        matches = list(re.finditer(cond_pattern, cond_str, re.IGNORECASE))

        if not matches:
            raise ValueError(f"Invalid WHERE clause syntax: '{cond_str}'")

        node = None
        for match in matches:
            field, op, quote, quoted_value, unquoted_value = match.groups()
            value = quoted_value if quote else unquoted_value

            cond_node = ConditionNode(left=field, op=op.upper(), right=value)

            if node is None:
                node = cond_node
            else:
                node = LogicalNode(left=node, op="AND", right=cond_node)

        return node
