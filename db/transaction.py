import threading
from enum import Enum


class TransactionState(Enum):
    ACTIVE = "active"
    COMMITTED = "committed"
    ABORTED = "aborted"


class Transaction:
    def __init__(self, tx_id: int):
        self.tx_id = tx_id
        self.state = TransactionState.ACTIVE
        self.operations: list[dict] = []
        self.locks: set = set()

    def add_operation(self, operation: dict):
        if self.state == TransactionState.ACTIVE:
            self.operations.append(operation)

    def commit(self):
        self.state = TransactionState.COMMITTED

    def abort(self):
        self.state = TransactionState.ABORTED
        self.operations.clear()


class TransactionManager:
    def __init__(self):
        self.transactions: dict[int, Transaction] = {}
        self.lock = threading.Lock()
        self.next_tx_id = 1
        self.write_ahead_log: list[str] = []

    def begin(self) -> Transaction:
        with self.lock:
            tx = Transaction(self.next_tx_id)
            self.transactions[self.next_tx_id] = tx
            self.next_tx_id += 1
            return tx

    def commit(self, tx_id: int) -> bool:
        with self.lock:
            if tx_id not in self.transactions:
                return False

            tx = self.transactions[tx_id]

            if tx.state != TransactionState.ACTIVE:
                return False

            self._write_log(f"COMMIT ${tx_id}")

            tx.commit()

            return True

    def abort(self, tx_id: int) -> bool:
        with self.lock:
            if tx_id not in self.transactions:
                return False

            tx = self.transactions[tx_id]

            if tx.state != TransactionState.ACTIVE:
                return False

            self._write_log(f"ABORT ${tx_id}")

            tx.abort()

            return True

    def _write_log(self, message: str):
        self.write_ahead_log.append(message)

        if len(self.write_ahead_log) > 1000:
            self.write_ahead_log = self.write_ahead_log[-500:]

    def get_transaction(self, tx_id: int) -> Transaction:
        return self.transactions.get(tx_id)
