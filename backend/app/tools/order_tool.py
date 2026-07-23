import json
from pathlib import Path


ORDERS_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "mock"
    / "orders.json"
)


def get_order_by_id(order_id: str) -> dict | None:
    """Return an order record by its identifier."""

    with ORDERS_FILE.open("r", encoding="utf-8") as file:
        orders = json.load(file)

    normalized_order_id = order_id.strip().upper()

    for order in orders:
        if order["order_id"] == normalized_order_id:
            return order

    return None