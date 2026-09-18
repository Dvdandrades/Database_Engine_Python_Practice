# Database Engine Python

A minimal relational database engine implemented from scratch in Python, utilizing `uv` for fast package and project management.

# Features

- **Query Engine & Parser:** Custom Regex-based SQL parser supporting basic `CREATE`, `SELECT`, `INSERT`, `UPDATE`, and `DELETE` queries with conditional matching (`=`, `!=`, `LIKE`).

- **B-Tree Indexing:** Core B-Tree implementation supporting dynamic node splits and fast lookup.

- **Storage Engine:** Low-level binary file storage (`data.db`) featuring a page structure and custom key-value binary encoding.

- **Transaction Management:** ACID-oriented transaction coordinator tracking operational states (`ACTIVE`, `COMMITTED`, `ABORTED`) with a Write-Ahead Log (WAL) and locking primitives.

# Getting Started

## Running the Project

Run the primary application script directly through `uv`:

```bash
uv run main.py
```

## Usage Example

```bash
from db.storage import StorageEngine
from db.engine import QueryEngine

# Initialize storage and query execution engines
storage = StorageEngine("./testdb")
engine = QueryEngine(storage)

# Execute SQL operations
engine.execute("CREATE TABLE users")
engine.execute("INSERT INTO users (name, email) VALUES ('David', 'david@example.com')")

# Query records
results = engine.execute("SELECT * FROM users WHERE name = 'David'")
print(results)
```