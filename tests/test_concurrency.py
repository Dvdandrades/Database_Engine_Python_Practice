import pytest

from db.concurrency.locks import LockManager
from db.concurrency.transaction import TransactionManager, TransactionState


def test_shared_locks_allow_multiple_readers():
    manager = LockManager()

    manager.acquire_read(tx_id=1, key="row_1")
    manager.acquire_read(tx_id=2, key="row_1")

    lock = manager._record_locks["row_1"]
    assert 1 in lock.shared_owners
    assert 2 in lock.shared_owners
    assert lock.exclusive_owner is None


def test_exclusive_lock_blocks_others():
    manager = LockManager()
    manager.acquire_write(tx_id=1, key="row_1")

    with pytest.raises(TimeoutError, match="timeout expired for SHARED lock"):
        manager.acquire_read(tx_id=2, key="row_1", timeout=0.1)

    with pytest.raises(TimeoutError, match="timeout expired for EXCLUSIVE lock"):
        manager.acquire_write(tx_id=3, key="row_1", timeout=0.1)


def test_lock_escalation():
    manager = LockManager()
    manager.acquire_read(tx_id=1, key="row_1")

    manager.acquire_write(tx_id=1, key="row_1", timeout=0.1)

    lock = manager._record_locks["row_1"]
    assert lock.exclusive_owner == 1


class TestTransactionManager:
    def setup_method(self):
        self.tm = TransactionManager()

    def test_transaction_begin_and_commit(self):
        tx = self.tm.begin()

        assert tx.tx_id == 1
        assert tx.state == TransactionState.ACTIVE
        assert "BEGIN 1" in self.tm.write_ahead_log

        success = self.tm.commit(tx.tx_id)

        assert success is True
        assert tx.state == TransactionState.COMMITTED
        assert "COMMIT 1" in self.tm.write_ahead_log

    def test_transaction_abort_releases_locks(self):
        tx = self.tm.begin()

        self.tm.acquire_lock(tx.tx_id, "row_A", "EXCLUSIVE")
        assert len(tx.locks) == 1

        aborted_tx = self.tm.abort(tx.tx_id)

        assert aborted_tx.state == TransactionState.ABORTED
        assert "ABORT 1" in self.tm.write_ahead_log

        assert len(aborted_tx.locks) == 0

        tx2 = self.tm.begin()
        self.tm.acquire_lock(tx2.tx_id, "row_A", "EXCLUSIVE")
        assert len(tx2.locks) == 1

    def test_invalid_lock_mode(self):
        tx = self.tm.begin()
        with pytest.raises(ValueError, match="Unknown lock mode"):
            self.tm.acquire_lock(tx.tx_id, "row_A", "MAGIC_MODE")
