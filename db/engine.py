from typing import Any

from .index import IndexManager
from .parser import Query, QueryParser
from .storage import StorageEngine


class QueryEngine:
    def __init__(self, storage: StorageEngine):
        self.storage = storage
        self.parser = QueryParser()
        self.tables: dict[str, dict] = self.storage.get("__tables__") or {}
        self.index_manager = IndexManager()

    def execute(self, sql: str) -> Any:
        query = self.parser.parse(sql)

        if query.operation == "SELECT":
            return self._execute_select(query)
        elif query.operation == "INSERT":
            result = self._execute_insert(query)
        elif query.operation == "UPDATE":
            result = self._execute_update(query)
        elif query.operation == "DELETE":
            result = self._execute_delete(query)
        elif query.operation == "CREATE":
            result = self._execute_create(query)
        elif query.operation == "CREATE_INDEX":
            result = self._execute_create_index(query)

        self.storage.put("__tables__", self.tables)
        return result

    def _execute_create_index(self, query: Query) -> dict:
        table_name = f"${query.table}_table"

        if table_name not in self.tables:
            return {"created_index": 0, "error": f"Table '{query.table}' does not exist"}

        field = query.fields[0]
        index_name = self.index_manager.create_index(query.table, field)

        records = self.tables[table_name]
        indexed_count = 0
        for rid, record in records.items():
            if field in record:
                self.index_manager.insert(index_name, record[field], rid)
                indexed_count += 1

        return {"created_index": 1, "field": field, "indexed_records": indexed_count}

    def _execute_select(self, query: Query) -> list[dict]:
        table_name = f"${query.table}_table"

        if table_name not in self.tables:
            return []

        records = self.tables[table_name]

        candidate_rids = self._get_candidate_rids_from_index(query)

        if candidate_rids is not None:
            target_records = [records[rid] for rid in candidate_rids if rid in records]
        else:
            target_records = records.values()

        results = []
        for record in target_records:
            if self._matches_conditions(record, query.conditions):
                if query.fields:
                    results.append(
                        {k: v for k, v in record.items() if k in query.fields}
                    )
                else:
                    results.append(record)

        return results

    def _execute_insert(self, query: Query) -> dict:
        table_name = f"${query.table}_table"

        if table_name not in self.tables:
            self.tables[table_name] = {}

        records = self.tables[table_name]

        record_id = len(records) + 1
        record = {"id": record_id, **query.values}

        records[record_id] = record

        indexed_fields = self.index_manager.get_indexed_fields(query.table)
        for field in indexed_fields:
            if field in record:
                index_name = f"${query.table}_${field}_idx"
                self.index_manager.insert(index_name, record[field], record_id)

        return {"inserted": 1, "id": record_id}

    def _execute_update(self, query: Query) -> dict:
        table_name = f"${query.table}_table"

        if table_name not in self.tables:
            return {"updated": 0}

        records = self.tables[table_name]
        updated = 0

        for record in records.values():
            if self._matches_conditions(record, query.conditions):
                for key, value in query.values.items():
                    record[key] = value
                updated += 1

        return {"updated": updated}

    def _execute_delete(self, query: Query) -> dict:
        table_name = f"${query.table}_table"

        if table_name not in self.tables:
            return {"deleted": 0}

        records = self.tables[table_name]
        deleted = 0

        to_delete = [
            rid
            for rid, record in records.items()
            if self._matches_conditions(record, query.conditions)
        ]

        for rid in to_delete:
            del records[rid]
            deleted += 1

        return {"deleted": deleted}

    def _execute_create(self, query: Query) -> dict:
        table_name = f"${query.table}_table"

        if table_name in self.tables:
            return {"created": 0, "error": "Table already exists"}

        self.tables[table_name] = {}

        return {"created": 1}

    def _get_candidate_rids_from_index(self, query: Query) -> list[int] | None:
        if not query.conditions:
            return None

        for field, cond in query.conditions.items():
            if cond["op"] == "=":
                index_name = f"${query.table}_${field}_idx"
                if index_name in self.index_manager.indexes:
                    rids = self.index_manager.search(index_name, cond["value"])
                    return rids if rids is not None else []

        return None

    def _matches_conditions(self, record: dict, conditions: dict) -> bool:
        if not conditions:
            return True

        for field, condition in conditions.items():
            if field not in record:
                return False

            op = condition["op"]
            value = condition["value"]
            record_value = str(record[field])

            if op == "=" and record_value != value:
                return False
            if op == "!=" and record_value == value:
                return False
            if op == "LIKE":
                import re

                pattern = ".*".join(re.escape(part) for part in value.split("%"))
                if not re.fullmatch(pattern, record_value):
                    return False

        return True
