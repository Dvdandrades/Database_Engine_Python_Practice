import re


class Query:
    def __init__(
        self,
        operation: str,
        table: str,
        conditions: dict | None = None,
        values: dict | None = None,
        fields: list[str] | None = None,
    ):
        self.operation = operation
        self.table = table
        self.conditions = conditions or {}
        self.values = values or {}
        self.fields = fields or []


class QueryParser:
    def __init__(self):
        self.operations = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE"]

    def parse(self, sql: str) -> Query:
        sql = sql.strip()

        for op in self.operations:
            if sql.upper().startswith(op):
                return getattr(self, f"_parse_{op.lower()}_")(sql)

        raise ValueError(f"Unknown operation: {sql}")

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

    def _parse_select_(self, sql: str) -> Query:
        pattern = r"^SELECT\s+(.*?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*))?\s*;?$"
        match = re.match(pattern, sql, re.IGNORECASE)

        if not match:
            raise ValueError(f"Invalid SELECT syntax: '{sql}'")

        fields_str, table, conditions_str = match.groups()

        fields = (
            [f.strip() for f in fields_str.split(",")]
            if fields_str.strip() != "*"
            else []
        )
        conditions = self._parse_conditions(conditions_str) if conditions_str else {}

        return Query("SELECT", table, conditions, fields=fields)

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

        conditions = self._parse_conditions(conditions_str) if conditions_str else {}

        return Query("UPDATE", table, conditions, values)

    def _parse_delete_(self, sql: str) -> Query:
        pattern = r"^DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*))?\s*;?$"
        match = re.match(pattern, sql, re.IGNORECASE)

        if not match:
            raise ValueError(f"Invalid DELETE syntax: '{sql}'")

        table, conditions_str = match.groups()
        conditions = self._parse_conditions(conditions_str) if conditions_str else {}

        return Query("DELETE", table, conditions)

    def _parse_conditions(self, cond_str: str) -> dict:
        conditions = {}

        if not cond_str:
            return conditions

        cond_pattern = r'(\w+)\s*(=|!=|<|>|<=|>=|LIKE)\s*(?:(["\'])(.*?)\3|(\w+))'

        matches = list(re.finditer(cond_pattern, cond_str, re.IGNORECASE))

        if not matches:
            raise ValueError(f"Invalid WHERE clause syntax: '{cond_str}'")

        for match in matches:
            field, op, quote, quoted_value, unquoted_value = match.groups()
            value = quoted_value if quote else unquoted_value
            conditions[field] = {"op": op.upper(), "value": value}

        return conditions
