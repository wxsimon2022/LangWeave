"""Example business tool: order domain."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def query_order_status(order_id: str) -> str:
    """Query order status by order id (demo business logic)."""
    # Replace with real DB / API calls in production
    demo_orders = {
        "10001": "shipped",
        "10002": "processing",
        "10003": "delivered",
    }
    status = demo_orders.get(order_id.strip())
    if status is None:
        return f"Order {order_id} not found"
    return f"Order {order_id} status: {status}"
