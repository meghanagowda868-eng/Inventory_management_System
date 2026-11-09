"""Repository for stock movement analytics."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.warehouse import Warehouse


class StockMovementRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        product_id: int,
        warehouse_id: int,
        movement_type: str,
        quantity: int,
        performed_by: str | None = None,
        reference: str | None = None,
    ) -> StockMovement:
        movement = StockMovement(
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type=movement_type,
            quantity=quantity,
            performed_by=performed_by,
            reference=reference,
        )
        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def list_recent(self, limit: int = 10) -> list[StockMovement]:
        return (
            self.db.query(StockMovement)
            .options(joinedload(StockMovement.product), joinedload(StockMovement.warehouse))
            .order_by(StockMovement.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_summary_by_day(self, days: int = 30) -> list[dict]:
        cutoff = datetime.utcnow() - timedelta(days=days)

        rows = (
            self.db.query(
                func.date(StockMovement.created_at).label("movement_day"),
                func.sum(case((StockMovement.movement_type == "STOCK_IN", StockMovement.quantity), else_=0)).label("stock_in"),
                func.sum(case((StockMovement.movement_type == "STOCK_OUT", StockMovement.quantity), else_=0)).label("stock_out"),
                func.sum(case((StockMovement.movement_type == "TRANSFER_IN", StockMovement.quantity), else_=0)).label("transfer_in"),
                func.sum(case((StockMovement.movement_type == "TRANSFER_OUT", StockMovement.quantity), else_=0)).label("transfer_out"),
                func.sum(case((StockMovement.movement_type == "RESTOCK", StockMovement.quantity), else_=0)).label("restock"),
                func.sum(case((StockMovement.movement_type == "ADJUSTMENT", StockMovement.quantity), else_=0)).label("adjustment"),
            )
            .filter(StockMovement.created_at >= cutoff)
            .group_by(func.date(StockMovement.created_at))
            .order_by(func.date(StockMovement.created_at).asc())
            .all()
        )

        return [
            {
                "date": row.movement_day.isoformat() if row.movement_day else "",
                "stock_in": int(row.stock_in or 0),
                "stock_out": int(row.stock_out or 0),
                "transfer_in": int(row.transfer_in or 0),
                "transfer_out": int(row.transfer_out or 0),
                "restock": int(row.restock or 0),
                "adjustment": int(row.adjustment or 0),
            }
            for row in rows
        ]
