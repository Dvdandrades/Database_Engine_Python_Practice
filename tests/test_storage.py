from pathlib import Path

import pytest

from db.storage.engine import StorageEngine
from db.storage.page import Page


def test_page_initialization_and_size():
    page = Page(page_id=1)

    assert page.page_id == 1
    assert len(page.data) == 4096
    assert page.PAGE_SIZE == 4096


def test_page_read_write():
    page = Page()
    test_data = b"Hello, Database!"

    page.write(offset=10, data=test_data)

    read_data = page.read(offset=10, size=len(test_data))
    assert read_data == test_data

    empty_region = page.read(offset=0, size=10)
    assert empty_region == bytes(10)


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_storage")


@pytest.fixture
def engine(db_path):
    return StorageEngine(db_path)


def test_engine_initialization(db_path, engine):
    path = Path(db_path)

    assert path.exists()
    assert (path / "data.db").exists()
    assert isinstance(engine.keydir, dict)


def test_engine_put_and_get(engine):
    record = {"name": "David", "age": 28}
    engine.put("user_1", record)

    assert "user_1" in engine.keydir

    retrieved = engine.get("user_1")
    assert retrieved == record

    assert engine.get("non_existent") is None


def test_engine_delete(engine):
    record = {"name": "Ana"}
    engine.put("user_2", record)

    assert engine.get("user_2") == record

    engine.delete("user_2")

    assert "user_2" not in engine.keydir
    assert engine.get("user_2") is None


def test_wal_recovery(db_path):
    engine1 = StorageEngine(db_path)
    engine1.put("key_1", {"data": "v1"})
    engine1.put("key_2", {"data": "v2"})
    engine1.delete("key_1")

    engine2 = StorageEngine(db_path)

    assert engine2.get("key_1") is None
    assert engine2.get("key_2") == {"data": "v2"}

    log_file = Path(db_path) / "wal.log"
    assert not log_file.exists()


def test_engine_compaction(engine, db_path):
    for i in range(100):
        engine.put("counter", {"value": i})

    engine.put("other_key", {"status": "active"})
    engine.delete("other_key")

    data_file = Path(db_path) / "data.db"
    size_before_compaction = data_file.stat().st_size

    engine.compact()

    size_after_compaction = data_file.stat().st_size

    assert size_after_compaction < size_before_compaction

    assert engine.get("counter") == {"value": 99}
    assert engine.get("other_key") is None
