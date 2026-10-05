import threading
import time


class RecordLock:
    def __init__(self):
        self.shared_owners: set[int] = set()
        self.exclusive_owner: int | None = None
        self.condition = threading.Condition()


class LockManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._record_locks: dict[str, RecordLock] = {}

    def _get_or_create_lock(self, key: str) -> RecordLock:
        with self._lock:
            if key not in self._record_locks:
                self._record_locks[key] = RecordLock()
            return self._record_locks[key]

    def acquire_read(self, tx_id: int, key: str, timeout: float = 5.0):
        rlock = self._get_or_create_lock(key)
        with rlock.condition:
            end_time = time.time() + timeout
            while rlock.exclusive_owner is not None and rlock.exclusive_owner != tx_id:
                remaining = end_time - time.time()
                if remaining <= 0 or not rlock.condition.wait(timeout=remaining):
                    raise TimeoutError(
                        f"Transaction {tx_id}: timeout expired for SHARED lock in '{key}'"
                    )
            rlock.shared_owners.add(tx_id)

    def acquire_write(self, tx_id: int, key: str, timeout: float = 5.0):
        rlock = self._get_or_create_lock(key)
        with rlock.condition:
            end_time = time.time() + timeout
            while (
                rlock.exclusive_owner is not None and rlock.exclusive_owner != tx_id
            ) or (
                len(rlock.shared_owners) > 0
                and not (len(rlock.shared_owners) == 1 and tx_id in rlock.shared_owners)
            ):
                remaining = end_time - time.time()
                if remaining <= 0 or not rlock.condition.wait(timeout=remaining):
                    raise TimeoutError(
                        f"Transaction {tx_id}: timeout expired for EXCLUSIVE lock in '{key}'"
                    )
            rlock.exclusive_owner = tx_id

    def release_locks(self, tx_id: int, locks: set[tuple[str, str]]):
        for key, mode in locks:
            with self._lock:
                rlock = self._record_locks.get(key)
            if not rlock:
                continue

            with rlock.condition:
                if mode == "SHARED":
                    rlock.shared_owners.discard(tx_id)
                elif mode == "EXCLUSIVE" and rlock.exclusive_owner == tx_id:
                    rlock.exclusive_owner = None
                rlock.condition.notify_all()
