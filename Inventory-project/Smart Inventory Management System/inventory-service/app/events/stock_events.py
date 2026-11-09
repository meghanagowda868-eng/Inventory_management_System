"""
Stock event stubs — emits events when stock changes.
Phase 1: logs the event only.
Phase 4: replace emit() body with RabbitMQ/Kafka publish call.
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger("inventory_service.events")


@dataclass
class StockEvent:
    product_id: int
    product_name: str
    sku: str
    previous_quantity: int
    new_quantity: int
    minimum_stock: int
    event_type: str  # "LOW_STOCK" | "OUT_OF_STOCK" | "STOCK_UPDATED"


def emit_stock_event(event: StockEvent) -> None:
    """
    Emit a stock change event.

    Phase 1 implementation: structured log output only.
    Phase 4 upgrade: publish to RabbitMQ exchange 'inventory.events'.

    Example RabbitMQ upgrade (do NOT implement yet):
        channel.basic_publish(
            exchange='inventory.events',
            routing_key=event.event_type.lower(),
            body=json.dumps(asdict(event)),
        )
    """
    logger.info(
        "STOCK_EVENT | type=%s | product_id=%s | sku=%s | qty=%s→%s | min=%s",
        event.event_type,
        event.product_id,
        event.sku,
        event.previous_quantity,
        event.new_quantity,
        event.minimum_stock,
    )


def build_stock_event(
    product_id: int,
    product_name: str,
    sku: str,
    previous_quantity: int,
    new_quantity: int,
    minimum_stock: int,
) -> StockEvent:
    """Determine event type and build StockEvent."""
    if new_quantity == 0:
        event_type = "OUT_OF_STOCK"
    elif new_quantity < minimum_stock:
        event_type = "LOW_STOCK"
    else:
        event_type = "STOCK_UPDATED"

    return StockEvent(
        product_id=product_id,
        product_name=product_name,
        sku=sku,
        previous_quantity=previous_quantity,
        new_quantity=new_quantity,
        minimum_stock=minimum_stock,
        event_type=event_type,
    )
