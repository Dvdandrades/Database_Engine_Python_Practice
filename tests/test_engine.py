import pytest

from db.engine import QueryEngine
from db.storage import StorageEngine


@pytest.fixture
def engine(tmp_path):
    db_dir = tmp_path / "test_db"
    storage = StorageEngine(str(db_dir))
    return QueryEngine(storage)


def test_create_table_and_insert(engine):
    create_res = engine.execute("CREATE TABLE users")
    assert create_res == {"created": 1}

    insert_res = engine.execute(
        "INSERT INTO users (name, email) VALUES ('David', 'david@example.com')"
    )
    assert insert_res == {"inserted": 1, "id": 1}

    users = engine.execute("SELECT * FROM users")
    assert len(users) == 1
    assert users[0] == {
        "id": 1,
        "name": "David",
        "email": "david@example.com",
    }


def test_select_queries(engine):
    engine.execute("CREATE TABLE users")
    engine.execute(
        "INSERT INTO users (name, email) VALUES ('David', ''david@example.com)"
    )
    engine.execute(
        "INSERT INTO users (name, email) VALUES ('Juan', 'juan@example.com')"
    )

    david = engine.execute("SELECT * FROM users WHERE name = 'David'")
    assert len(david) == 1
    assert david[0]["name"] == "David"

    prefix_match = engine.execute("SELECT * FROM users WHERE name LIKE 'Da%'")
    assert len(prefix_match) == 1
    assert prefix_match[0]["name"] == "David"

    suffix_match = engine.execute(
        "SELECT * FROM users WHERE email LIKE '%@example.com'"
    )
    assert len(suffix_match) == 2


def test_update_and_delete(engine):
    engine.execute("CREATE TABLE users")
    engine.execute(
        "INSERT INTO users (name, email) VALUES ('David', 'david@example.com')"
    )
    engine.execute(
        "INSERT INTO users (name, email) VALUES ('Juan', 'juan@example.com')"
    )

    update_res = engine.execute(
        "UPDATE users SET email = 'david.new@example.com' WHERE name = 'David'"
    )
    assert update_res == {"updated": 1}

    updated_user = engine.execute("SELECT * FROM users WHERE name = 'David'")
    assert updated_user[0]["email"] == "david.new@example.com"

    delete_res = engine.execute("DELETE FROM users WHERE name = 'Juan'")
    assert delete_res == {"deleted": 1}

    remaining_users = engine.execute("SELECT * FROM users")
    assert len(remaining_users) == 1
    assert remaining_users[0]["name"] == "David"


def test_transactions_rollback_and_commit(engine):
    engine.execute("CREATE TABLE users")

    engine.execute("BEGIN")
    engine.execute(
        "INSERT INTO users (name, email) VALUES ('Temporal', 'temp@example.com')"
    )

    inside_tx = engine.execute("SELECT * FROM users")
    assert len(inside_tx) == 1

    engine.execute("ROLLBACK")
    after_rollback = engine.execute("SELECT * FROM users")
    assert len(after_rollback) == 0

    engine.execute("BEGIN")
    engine.execute(
        "INSERT INTO users (name, email) VALUES ('Juan', 'juan@example.com')"
    )
    engine.execute("COMMIT")

    after_commit = engine.execute("SELECT * FROM users")
    assert len(after_commit) == 1
    assert after_commit[0]["name"] == "Juan"


def test_indexes(engine):
    engine.execute("CREATE TABLE users")
    index_res = engine.execute("CREATE INDEX ON users (name)")
    assert index_res["created_index"] == 1

    engine.execute(
        "INSERT INTO users (name, email) VALUES ('David', 'david@example.com')"
    )

    res = engine.execute("SELECT * FROM users WHERE name = 'David'")
    assert len(res) == 1
    assert res[0]["name"] == "David"
