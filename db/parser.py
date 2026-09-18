import re
from typing import Dict, List, Any, Optional

class Query:
    def __init__(self, operation: str, table: str, conditions: Dict = None, values: Dict = None, fields: List[str] = None):
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
        pattern = r"CREATE TABLE\s+(\w+)"
        match = re.match(pattern, sql, re.IGNORECASE)

        if not match:
            raise ValueError("Invalid CREATE syntax")

        table = match.group(1)

        return Query("CREATE", table)

    def _parse_select_(self, sql: str) -> Query:
        pattern = r"SELECT\s+(.*?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*))?"
        match = re.match(pattern, sql, re.IGNORECASE)

        if not match:
            raise ValueError("Invalid SELECT syntax")

        fields_str, table, conditions_str = match.groups()

        fields = [f.strip() for f in fields_str.split(",")] if fields_str.strip() != "*" else []
        conditions = self._parse_conditions(conditions_str) if conditions_str else {}

        return Query("SELECT", table, conditions, fields=fields)

    def _parse_insert_(self, sql: str) -> Query:
        pattern = r"INSERT\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)"
        match = re.match(pattern, sql, re.IGNORECASE)

        if not match:
            raise ValueError("Invalid INSERT syntax")

        table, fields_str, values_str = match.groups()

        fields = [f.strip() for f in fields_str.split(",")]
        values = [v.strip().strip("'\"") for v in values_str.split(",")]

        values_dict = dict(zip(fields, values))

        return Query("INSERT", table, values=values_dict)

    def _parse_update_(self, sql: str) -> Query:
        pattern = r'UPDATE\s+(\w+)\s+SET\s+(.*)'
        match = re.match(pattern, sql, re.IGNORECASE)

        if not match:
            raise ValueError("Invalid UPDATE syntax")

        table, rest = match.groups()

        where_split = re.split(r'\s+WHERE\s+', rest, flags=re.IGNORECASE)
        set_str = where_split[0]
        conditions_str = where_split[1] if len(where_split) > 1 else None

        set_pairs = [s.strip() for s in set_str.split(",")]
        values = {}
        for pair in set_pairs:
            key, val = pair.split("=")
            values[key.strip()] = val.strip().strip("'\"")

        conditions = self._parse_conditions(conditions_str) if conditions_str else {}

        return Query("UPDATE", table, conditions, values)

    def _parse_delete_(self, sql: str) -> Query:
        pattern = r'DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*))?'
        match = re.match(pattern, sql, re.IGNORECASE)

        if not match:
            raise ValueError("Invalid DELETE syntax")

        table, conditions_str = match.groups()
        conditions = self._parse_conditions(conditions_str) if conditions_str else {}

        return Query("DELETE", table, conditions)

    def _parse_conditions(self, cond_str: str) -> Dict:
        conditions = {}

        if not cond_str:
            return conditions

        pattern = r'(\w+)\s*(=|!=|<|>|<=|>=|LIKE)\s*["\']?([^"\']+)["\']?'

        for match in re.finditer(pattern, cond_str):
            field, op, value = match.groups()
            conditions[field] = {"op": op, "value": value}

        return conditions