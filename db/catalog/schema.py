from db.storage.engine import StorageEngine


class SchemaManager:
    def __init__(self, storage: StorageEngine):
        self.storage = storage
        self.schema: dict[str, dict] = self.storage.get("__schema__") or {}

    def table_exists(self, table_name: str) -> bool:
        return f"${table_name}_table" in self.schema

    def get_table_info(self, table_name: str) -> dict:
        return self.schema.get(f"${table_name}_table", {})

    def save(self):
        self.storage.put("__schema__", self.schema)
