from db.engine import QueryEngine
from db.storage import StorageEngine

engine = QueryEngine(StorageEngine("./testdb"))

result = engine.execute("CREATE TABLE users")
print("Create:", result)

result = engine.execute("CREATE INDEX ON users (name)")
print("Create Index On: ", result)

result = engine.execute(
    "INSERT INTO users (name, email) VALUES ('David', 'david@example.com')"
)
print("Insert:", result)

result = engine.execute(
    "INSERT INTO users (name, email) VALUES ('Juan', 'juan@example.com')"
)
print("Insert", result)

engine.execute("BEGIN")
engine.execute(
    "INSERT INTO users (name, email) VALUES ('Temporal', 'temp@example.com')"
)
print("Inside tx:", engine.execute("SELECT * FROM users"))

engine.execute("ROLLBACK")
print("After ROLLBACK:", engine.execute("SELECT * FROM users"))

engine.execute("BEGIN")
engine.execute("INSERT INTO users (name, email) VALUES ('Juan', 'juan@example.com')")
engine.execute("COMMIT")
print("After COMMIT:", engine.execute("SELECT * FROM users"))

result = engine.execute("SELECT * FROM users")
print("Select all: ", result)

result = engine.execute("SELECT * FROM users WHERE name = 'David'")
print("Select with WHERE: ", result)

result = engine.execute(
    "UPDATE users SET email = 'david.new@example.com' WHERE name = 'David'"
)
print("Update: ", result)

result = engine.execute("SELECT * FROM users WHERE name = 'David'")
print("Select with WHERE and UPDATE: ", result)

result = engine.execute("SELECT * FROM users WHERE email LIKE '%@example.com'")
print("Select with LIKE (suffix): ", result)

result = engine.execute("SELECT * FROM users WHERE name LIKE 'Da%'")
print("Select with LIKE (prefix): ", result)

result = engine.execute("DELETE FROM users WHERE name = 'Juan'")
print("Delete: ", result)
