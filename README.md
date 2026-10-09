# Database Engine Python

A small relational database engine built in Python for learning about SQL parsing, record storage, indexes, and transaction coordination. It includes an interactive SQL terminal and a Python API.

> This is an educational prototype. Its transaction and recovery mechanisms are intentionally limited and are not a production-grade ACID database.

## Features

- SQL parsing and execution for `CREATE TABLE`, `CREATE INDEX`, `INSERT`, `SELECT`, `UPDATE`, and `DELETE`.
- Record storage in an append-only binary data file, with a key directory, tombstones, compaction, and a write-ahead log used during recovery.
- In-memory B-tree indexes for equality lookups on indexed fields; index definitions are saved with the schema and rebuilt at startup.
- Explicit `BEGIN`, `COMMIT`, and `ROLLBACK` transaction commands, undo actions, and shared/exclusive record locks.
- A command-line REPL with table listing and storage compaction.

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) for the commands below

Install the project dependencies from the repository root:

```bash
uv sync
```

## Run the SQL terminal

```bash
uv run main.py
```

The REPL stores its database files in `./db_data` by default. Enter SQL statements ending in a semicolon, or press Enter after a complete statement. REPL commands are:

| Command | Action |
| --- | --- |
| `.tables` | List known tables |
| `.compact` | Compact the storage file |
| `.exit` | Close the terminal |

Example session:

```sql
CREATE TABLE users;
CREATE INDEX ON users (name);
INSERT INTO users (name, email) VALUES ('David', 'david@example.com');
SELECT name, email FROM users WHERE name = 'David';
UPDATE users SET email = 'david.new@example.com' WHERE name = 'David';
DELETE FROM users WHERE name = 'David';
```

Transactions can be entered as individual commands:

```sql
BEGIN;
INSERT INTO users (name) VALUES ('Juan');
ROLLBACK;
```

`ABORT` is also accepted as an alias for `ROLLBACK`.

## Supported SQL

Tables are created by name only; columns and types are not declared in the schema. Fields are supplied on each insert. `SELECT` accepts `*` or a comma-separated field list and optional conditions. The implemented condition operators are `=`, `!=`, and `LIKE`; `%` in a `LIKE` pattern matches any sequence of characters. `UPDATE` and `DELETE` accept optional conditions. `CREATE INDEX ON table (field)` creates an index.

Values are stored as JSON values, but the current SQL parser reads inserted and updated values as strings. SQL support is intentionally small and does not include joins, aggregates, `ORDER BY`, or a complete SQL type system.

## Use from Python

```python
from db.execution.engine import QueryEngine
from db.storage.engine import StorageEngine

storage = StorageEngine("./my_database")
engine = QueryEngine(storage)

engine.execute("CREATE TABLE users")
engine.execute("INSERT INTO users (name, email) VALUES ('David', 'david@example.com')")
rows = engine.execute("SELECT * FROM users WHERE name = 'David'")
print(rows)
```

`StorageEngine` creates the database directory if it does not exist. Reuse the same path to reopen its data.

## Run the test suite

```bash
uv run pytest
```

The tests cover parsing, query execution, storage, B-tree indexing, and transaction behavior.
