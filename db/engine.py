from typing import Any

from .index import IndexManager
from .parser import Query, QueryParser
from .storage import StorageEngine
from .transaction import Transaction, TransactionManager


class QueryEngine:
    def __init__(self, storage: StorageEngine):
        self.storage = storage
        self.parser = QueryParser()
        self.tables: dict[str, dict] = self.storage.get("__tables__") or {}
        self.index_manager = IndexManager()
        self.transaction_manager = TransactionManager()
        self.current_tx: Transaction | None = None

    def execute(self, sql: str) -> Any:
        query = self.parser.parse(sql)

        if query.operation == "BEGIN":
            return self._execute_begin()
        elif query.operation == "COMMIT":
            return self._execute_commit()
        elif query.operation == "ROLLBACK":
            return self._execute_rollback()

        autocommit = self.current_tx is None
        if autocommit:
            self.current_tx = self.transaction_manager.begin()

        try:
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
            else:
                raise ValueError(f"Unsupported operation: {query.operation}")

            if autocommit:
                self._execute_commit()

            return result
        except Exception:
            if autocommit:
                self._execute_rollback()
            raise

    def _execute_begin(self) -> dict:
        if self.current_tx is not None:
            return {"error": "Transaction already active"}
        tx = self.transaction_manager.begin()
        self.current_tx = tx
        return {"transaction": tx.tx_id, "status": "BEGIN"}

    def _execute_commit(self) -> dict:
        if self.current_tx is None:
            return {"error": "No active transaction to commit"}
        tx_id = self.current_tx.tx_id
        self.transaction_manager.commit(tx_id)
        self.storage.put("__tables__", self.tables)
        self.current_tx = None
        return {"transaction": tx_id, "status": "COMMITTED"}

    def _execute_rollback(self) -> dict:
        if self.current_tx is None:
            return {"error": "No active transaction to rollback"}

        tx = self.current_tx
        affected_tables = set()

        for action in reversed(tx.undo_actions):
            tbl = action["table"]
            raw_tbl = action["raw_table"]
            affected_tables.add(raw_tbl)

            if action["type"] == "INSERT":
                rid = action["id"]
                if rid in self.tables.get(tbl, {}):
                    del self.tables[tbl][rid]
            elif action["type"] == "UPDATE" or action["type"] == "DELETE":
                rid = action["id"]
                self.tables[tbl][rid] = action["old_record"]

        for raw_tbl in affected_tables:
            tbl_name = f"${raw_tbl}_table"
            records = self.tables.get(tbl_name, {})
            for field in self.index_manager.get_indexed_fields(raw_tbl):
                self.index_manager.rebuild_index(raw_tbl, field, records)

        self.transaction_manager.abort(tx.tx_id)
        self.current_tx = None
        return {"transaction": tx.tx_id, "status": "ROLLED_BACK"}

    def _execute_create_index(self, query: Query) -> dict:
        table_name = f"${query.table}_table"

        if table_name not in self.tables:
            return {
                "created_index": 0,
                "error": f"Table '{query.table}' does not exist",
            }

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

        if self.current_tx:
            self.current_tx.add_undo_action(
                {
                    "type": "INSERT",
                    "table": table_name,
                    "raw_table": query.table,
                    "id": record_id,
                    "record": record,
                }
            )

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

        for rid, record in records.items():
            if self._matches_conditions(record, query.conditions):
                old_record = record.copy()
                for key, value in query.values.items():
                    record[key] = value

                if self.current_tx:
                    self.current_tx.add_undo_action(
                        {
                            "type": "UPDATE",
                            "table": table_name,
                            "raw_table": query.table,
                            "id": rid,
                            "old_record": old_record,
                            "new_record": record.copy(),
                        }
                    )
                updated += 1

        indexed_fields = self.index_manager.get_indexed_fields(query.table)
        if indexed_fields and updated > 0:
            for field in indexed_fields:
                self.index_manager.rebuild_index(query.table, field, records)

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
            old_record = records[rid].copy()
            del records[rid]
            if self.current_tx:
                self.current_tx.add_undo_action(
                    {
                        "type": "DELETE",
                        "table": table_name,
                        "raw_table": query.table,
                        "id": rid,
                        "old_record": old_record,
                    }
                )
            deleted += 1

        indexed_fields = self.index_manager.get_indexed_fields(query.table)
        if indexed_fields and deleted > 0:
            for field in indexed_fields:
                self.index_manager.rebuild_index(query.table, field, records)

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
