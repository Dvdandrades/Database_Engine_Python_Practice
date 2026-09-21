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
        self.undo_actions: list[dict] = []
        self.locks: set = set()

    def add_undo_action(self, operation: dict):
        if self.state == TransactionState.ACTIVE:
            self.undo_actions.append(operation)

    def commit(self):
        self.state = TransactionState.COMMITTED
        self.undo_actions.clear()

    def abort(self):
        self.state = TransactionState.ABORTED


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
            self._write_log(f"BEGIN {tx.tx_id}")
            return tx

    def commit(self, tx_id: int) -> bool:
        with self.lock:
            if tx_id not in self.transactions:
                return False

            tx = self.transactions[tx_id]

            if tx.state != TransactionState.ACTIVE:
                return False

            self._write_log(f"COMMIT {tx_id}")

            tx.commit()

            return True

    def abort(self, tx_id: int) -> Transaction | None:
        with self.lock:
            if tx_id not in self.transactions:
                return None

            tx = self.transactions[tx_id]

            if tx.state != TransactionState.ACTIVE:
                return None

            self._write_log(f"ABORT {tx_id}")

            tx.abort()

            return tx

    def _write_log(self, message: str):
        self.write_ahead_log.append(message)

        if len(self.write_ahead_log) > 1000:
            self.write_ahead_log = self.write_ahead_log[-500:]

    def get_transaction(self, tx_id: int) -> Transaction | None:
        return self.transactions.get(tx_id)
