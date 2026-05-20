"""Built-in tools that work without external APIs."""

from __future__ import annotations

import ast
import operator as op
from datetime import datetime, timezone

from langchain_core.tools import tool

_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_safe_eval(node.operand))
    msg = "Unsupported expression"
    raise ValueError(msg)


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression (numbers, +, -, *, /, **, parentheses)."""
    tree = ast.parse(expression, mode="eval")
    result = _safe_eval(tree.body)
    return str(result)


@tool
def current_time() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()
