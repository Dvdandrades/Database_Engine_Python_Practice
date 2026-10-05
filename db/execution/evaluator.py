from typing import Any


class ConditionEvaluator:
    @staticmethod
    def matches(record: dict, node: Any) -> bool:
        if node is None:
            return True

        if type(node).__name__ == "LogicalNode":
            left_eval = ConditionEvaluator.matches(record, node.left)

            if node.op == "AND":
                return left_eval and ConditionEvaluator.matches(record, node.right)
            elif node.op == "OR":
                return left_eval or ConditionEvaluator.matches(record, node.right)

        elif type(node).__name__ == "ConditionNode":
            field = node.left
            if field not in record:
                return False

            op = node.op
            value = str(node.right)
            record_value = str(record[field])

            if op == "=":
                return record_value == value
            if op == "!=":
                return record_value != value
            if op == "LIKE":
                import re

                pattern = ".*".join(re.escape(part) for part in value.split("%"))
                return bool(re.fullmatch(pattern, record_value))

        return False
