from dataclasses import dataclass
from typing import Any


@dataclass
class ASTNode:
    pass


@dataclass
class BinaryOp(ASTNode):
    left: str
    op: str
    right: Any


@dataclass
class SelectNode(ASTNode):
    table: str
    fields: list[str]
    where: BinaryOp | None = None


@dataclass
class ConditionNode(ASTNode):
    left: str
    op: str
    right: Any


@dataclass
class LogicalNode(ASTNode):
    left: ASTNode
    op: str
    right: ASTNode


class Query:
    def __init__(
        self,
        operation: str,
        table: str = "",
        conditions: Any = None,
        values: dict | None = None,
        fields: list[str] | None = None,
    ):
        self.operation = operation
        self.table = table
        self.conditions = conditions
        self.values = values or {}
        self.fields = fields or []
