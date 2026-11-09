"""Analytics and dashboard intelligence service."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.warehouse import Warehouse
from app.repositories.stock_movement_repository import StockMovementRepository
from app.schemas.stock_movement import (
    InventoryDashboardSummary,
    MovementSummaryItem,
    ProductRiskItem,
    RiskSnapshotResponse,
    StockMovementResponse,
)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.stock_movement_repo = StockMovementRepository(db)

    def get_dashboard_summary(self) -> InventoryDashboardSummary:
        total_products = self.db.query(func.count(Product.id)).filter(Product.is_active.is_(True)).scalar() or 0
        total_stock_units = self.db.query(func.coalesce(func.sum(Product.quantity), 0)).filter(Product.is_active.is_(True)).scalar() or 0
        low_stock_products = self.db.query(func.count(Product.id)).filter(
            Product.is_active.is_(True),
            Product.quantity > 0,
            Product.quantity < Product.minimum_stock,
        ).scalar() or 0
        out_of_stock_products = self.db.query(func.count(Product.id)).filter(
            Product.is_active.is_(True),
            Product.quantity == 0,
        ).scalar() or 0
        overstocked_products = self.db.query(func.count(Product.id)).filter(
            Product.is_active.is_(True),
            Product.quantity > Product.minimum_stock * 2,
        ).scalar() or 0
        total_warehouses = self.db.query(func.count(Warehouse.id)).scalar() or 0

        healthy_stock_ratio = 0.0
        if total_products:
            healthy = total_products - low_stock_products - out_of_stock_products
            healthy_stock_ratio = max(0.0, healthy / total_products)

        health_score = int(round(healthy_stock_ratio * 100))

        pending_reorders = self.db.query(func.count(Product.id)).filter(
            Product.is_active.is_(True),
            Product.quantity <= Product.reorder_point,
        ).scalar() or 0

        from app.models.reorder_request import ReorderRequest
        pending_requests_count = self.db.query(func.count(ReorderRequest.id)).filter(
            ReorderRequest.status == "PENDING"
        ).scalar() or 0

        return InventoryDashboardSummary(
            total_products=int(total_products),
            total_stock_units=int(total_stock_units),
            low_stock_products=int(low_stock_products),
            out_of_stock_products=int(out_of_stock_products),
            overstocked_products=int(overstocked_products),
            total_warehouses=int(total_warehouses),
            pending_restock_requests=int(pending_requests_count),
            pending_transfers=0,
            inventory_health_score=max(0, min(100, health_score)),
        )

    def get_recent_movements(self, limit: int = 10) -> list[StockMovementResponse]:
        movements = self.stock_movement_repo.list_recent(limit=limit)
        items = []
        for m in movements:
            items.append(
                StockMovementResponse(
                    id=m.id,
                    product_id=m.product_id,
                    warehouse_id=m.warehouse_id,
                    product_name=m.product.name,
                    warehouse_name=m.warehouse.name,
                    movement_type=m.movement_type,
                    quantity=m.quantity,
                    performed_by=m.performed_by,
                    reference=m.reference,
                    created_at=m.created_at,
                )
            )
        return items

    def get_movement_summary(self, days: int = 30) -> list[MovementSummaryItem]:
        rows = self.stock_movement_repo.get_summary_by_day(days=days)
        items = []
        for row in rows:
            items.append(
                MovementSummaryItem(
                    date=row["date"],
                    stock_in=row["stock_in"],
                    stock_out=row["stock_out"],
                    transfer_in=row["transfer_in"],
                    transfer_out=row["transfer_out"],
                    restock=row["restock"],
                    adjustment=row["adjustment"],
                )
            )
        return items

    def get_total_movements_count(self) -> int:
        return self.db.query(func.count(StockMovement.id)).scalar() or 0

    def get_risk_snapshot(self) -> RiskSnapshotResponse:
        products = (
            self.db.query(Product)
            .filter(Product.is_active.is_(True))
            .order_by(Product.quantity.asc(), Product.minimum_stock.asc())
            .all()
        )

        items: list[ProductRiskItem] = []
        for product in products:
            if product.quantity == 0:
                score = 100
                level = "critical"
                recommendation = "Immediate restock required to avoid severe stockout risk."
            elif product.quantity < product.minimum_stock:
                coverage_gap = max(1, product.minimum_stock - product.quantity)
                score = min(95, 55 + int((coverage_gap / max(1, product.minimum_stock)) * 40))
                level = "high" if score >= 70 else "medium"
                recommendation = "Reorder soon to protect service levels and avoid stockout events."
            elif product.quantity < product.minimum_stock * 1.5:
                score = 40
                level = "medium"
                recommendation = "Monitor closely and trigger a replenishment review this week."
            else:
                score = 15
                level = "low"
                recommendation = "Healthy stock position; continue normal replenishment cadence."

            items.append(
                ProductRiskItem(
                    product_id=product.id,
                    product_name=product.name,
                    sku=product.sku,
                    quantity=product.quantity,
                    minimum_stock=product.minimum_stock,
                    risk_score=score,
                    risk_level=level,
                    recommendation=recommendation,
                )
            )

        at_risk = [item for item in items if item.risk_score >= 40]
        avg_score = round(sum(item.risk_score for item in at_risk) / len(at_risk)) if at_risk else 0

        return RiskSnapshotResponse(
            total_at_risk=len(at_risk),
            average_risk_score=avg_score,
            items=at_risk[:5],
        )
