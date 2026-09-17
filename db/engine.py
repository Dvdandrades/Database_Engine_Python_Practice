from typing import List, Dict, Any, Optional
from .storage import StorageEngine
from .parser import Query, QueryParser

class QueryEngine:
    def __init__(self, storage: StorageEngine):
        self.storage = storage
        self.parser = QueryParser()
        self.tables: Dict[str, Dict] = {}

    def execute(self, sql: str) -> Any:
        query = self.parser.parse(sql)

        if query.operation == "SELECT":
            return self._execute_select(query)
        elif query.operation == "INSERT":
            return self._execute_insert(query)
        elif query.operation == "UPDATE":
            return self._execute_update(query)
        elif query.operation == "DELETE":
            return self._execute_delete(query)
        elif query.operation == "CREATE":
            return self._execute_create(query)

    def _execute_select(self, query: Query) -> List[Dict]:
        table_name = f"${query.table}_table"

        if table_name not in self.tables:
            return []

        records = self.tables[table_name]

        results = []
        for record in records.values():
            if self._matches_conditions(record, query.conditions):
                if query.fields:
                    results.append({k: v for k, v in record.items() if k in query.fields})
                else:
                    results.append(record)

        return results

    def _execute_insert(self, query: Query) -> Dict:
        table_name = f"${query.table}_table"

        if table_name not in self.tables:
            self.tables[table_name] = {}

        records = self.tables[table_name]

        record_id = len(records) + 1
        record = {"id": record_id, **query.values}

        records[record_id] = record

        return {"inserted": 1, "id": record_id}

    def _execute_update(self, query: Query) -> Dict:
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

    def _execute_delete(self, query: Query) -> Dict:
        table_name = f"${query.table}_table"

        if table_name not in self.tables:
            return {"deleted": 0}

        records = self.tables[table_name]
        deleted = 0

        to_delete = [
            rid for rid, record in records.items()
            if self._matches_conditions(record, query.conditions)
        ]

        for rid in to_delete:
            del records[rid]
            deleted += 1

        return {"deleted": deleted}

    def _execute_create(self, query: Query) -> Dict:
        table_name = f"${query.table}_table"

        if table_name in self.tables:
            return {"created": 0, "error": "Table already exists"}

        self.tables[table_name] = {}

        return {"created": 1}

    def _matches_conditions(self, record: Dict, conditions: Dict) -> bool:
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
                pattern = value.replace("%", ".*")
                if not re.match(pattern, record_value):
                    return False

        return True
