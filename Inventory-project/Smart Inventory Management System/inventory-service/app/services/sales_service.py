"""Service for managing sales orders, POS transactions, stock reductions, and sales history."""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_

from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.inventory import InventoryItem
from app.models.stock_movement import StockMovement
from app.models.sales_history import SalesHistory
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.schemas.sales_order import (
    SalesOrderCreate,
    SalesOrderItemResponse,
    SalesOrderResponse,
    SalesSummaryResponse,
)
from app.services.notification_service import NotificationService


class SalesService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)

    def _generate_order_number(self) -> str:
        now_utc = datetime.now(timezone.utc)
        today_str = now_utc.strftime("%Y%m%d")
        count = self.db.query(SalesOrder).filter(SalesOrder.order_number.like(f"SO-{today_str}-%")).count() + 1
        return f"SO-{today_str}-{count:04d}"

    def create_sales_order(self, data: SalesOrderCreate, created_by: int) -> SalesOrderResponse:
        """Process a checkout sale transaction with real-time stock deductions, ledgers, and history logging."""
        if not data.items:
            raise ValueError("Sales order must contain at least one item")

        # 1. Validate all products and stock availability
        subtotal = Decimal("0.0")
        discount_total = Decimal("0.0")
        line_items_to_create = []
        products_to_update = []

        for item_in in data.items:
            product = self.db.get(Product, item_in.product_id)
            if not product:
                raise ValueError(f"Product ID {item_in.product_id} does not exist")

            if product.quantity < item_in.quantity:
                raise ValueError(
                    f"Insufficient stock for '{product.name}' (SKU: {product.sku}). "
                    f"Requested: {item_in.quantity}, Available: {product.quantity}"
                )

            unit_price = Decimal(str(item_in.unit_price if item_in.unit_price is not None else product.price))
            unit_cost = Decimal(str(product.unit_cost or 0.0))
            disc_pct = Decimal(str(item_in.discount_percent))
            
            raw_line = unit_price * item_in.quantity
            disc_amount = (raw_line * (disc_pct / Decimal("100"))).quantize(Decimal("0.01"))
            line_total = (raw_line - disc_amount).quantize(Decimal("0.01"))

            subtotal += raw_line
            discount_total += disc_amount

            line_items_to_create.append({
                "product": product,
                "product_id": product.id,
                "quantity": item_in.quantity,
                "unit_price": float(unit_price),
                "unit_cost": float(unit_cost),
                "discount_percent": float(disc_pct),
                "discount_amount": float(disc_amount),
                "line_total": float(line_total),
            })
            products_to_update.append((product, item_in.quantity))

        tax_total = Decimal("0.0")  # Can be expanded for regional tax policies
        total_amount = (subtotal - discount_total + tax_total).quantize(Decimal("0.01"))
        order_number = self._generate_order_number()

        # 2. Create the SalesOrder record
        order = SalesOrder(
            order_number=order_number,
            customer_name=data.customer_name,
            customer_email=data.customer_email,
            customer_phone=data.customer_phone,
            channel=data.channel,
            payment_method=data.payment_method,
            subtotal=float(subtotal.quantize(Decimal("0.01"))),
            discount_amount=float(discount_total),
            tax_amount=float(tax_total),
            total_amount=float(total_amount),
            status="COMPLETED",
            notes=data.notes,
            created_by=created_by,
        )
        self.db.add(order)
        self.db.flush()

        # 3. Create items, deduct product inventory, add stock movements & sales history
        today_date = date.today()
        for item_data in line_items_to_create:
            product = item_data["product"]
            qty = item_data["quantity"]

            order_item = SalesOrderItem(
                sales_order_id=order.id,
                product_id=product.id,
                quantity=qty,
                unit_price=item_data["unit_price"],
                unit_cost=item_data["unit_cost"],
                discount_percent=item_data["discount_percent"],
                discount_amount=item_data["discount_amount"],
                line_total=item_data["line_total"],
            )
            self.db.add(order_item)

            # Deduct from product stock
            product.quantity -= qty

            # Deduct from primary inventory item if mapped
            inv_item = (
                self.db.query(InventoryItem)
                .filter(InventoryItem.product_id == product.id)
                .first()
            )
            wh_id = inv_item.warehouse_id if inv_item else 1
            if inv_item:
                inv_item.quantity = max(0, inv_item.quantity - qty)

            # Log stock movement ledger entry
            movement = StockMovement(
                product_id=product.id,
                warehouse_id=wh_id,
                quantity=qty,
                movement_type="STOCK_OUT",
                performed_by=str(created_by),
                reference=f"SALE:{order_number}",
            )
            self.db.add(movement)

            # Record sales history for AI demand forecasting
            history = SalesHistory(
                product_id=product.id,
                sale_date=today_date,
                quantity=qty,
                unit_price=item_data["unit_price"],
                event_name=f"Order {order_number}",
            )
            self.db.add(history)

            # Stock threshold notifications
            if product.quantity == 0:
                self.notification_service.create_notification(
                    title=f"Out of Stock: {product.name}",
                    message=f"Product '{product.name}' (SKU: {product.sku}) is now out of stock following order {order_number}.",
                    category="LOW_STOCK",
                    severity="CRITICAL",
                    link_url="/reorders",
                )
            elif product.quantity <= product.reorder_point:
                self.notification_service.create_notification(
                    title=f"Low Stock Alert: {product.name}",
                    message=f"Product '{product.name}' is at {product.quantity} units (Reorder Point: {product.reorder_point}).",
                    category="LOW_STOCK",
                    severity="WARNING",
                    link_url="/reorders",
                )

        # Notify sale completed
        self.notification_service.create_notification(
            title=f"Sale Completed: {order_number}",
            message=f"Order {order_number} for {data.customer_name} completed (${float(total_amount):,.2f}).",
            category="SALE",
            severity="SUCCESS",
            link_url="/sales",
        )

        self.db.commit()
        return self._format_order_response(order)

    def list_sales_orders(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[List[SalesOrderResponse], int]:
        query = self.db.query(SalesOrder)

        if status:
            query = query.filter(SalesOrder.status == status.upper())
        if start_date:
            query = query.filter(func.date(SalesOrder.created_at) >= start_date)
        if end_date:
            query = query.filter(func.date(SalesOrder.created_at) <= end_date)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    SalesOrder.order_number.ilike(pattern),
                    SalesOrder.customer_name.ilike(pattern),
                    SalesOrder.customer_email.ilike(pattern),
                    SalesOrder.customer_phone.ilike(pattern),
                )
            )

        total = query.count()
        offset = (page - 1) * limit
        orders = query.order_by(desc(SalesOrder.created_at)).offset(offset).limit(limit).all()

        return [self._format_order_response(o) for o in orders], total

    def get_sales_order(self, order_id: int) -> SalesOrderResponse:
        order = self.db.get(SalesOrder, order_id)
        if not order:
            raise ValueError(f"Sales order with id {order_id} not found")
        return self._format_order_response(order)

    def refund_sales_order(self, order_id: int, user_id: int, reason: str) -> SalesOrderResponse:
        order = self.db.get(SalesOrder, order_id)
        if not order:
            raise ValueError(f"Sales order with id {order_id} not found")
        if order.status in ["REFUNDED", "CANCELLED"]:
            raise ValueError(f"Sales order is already {order.status}")

        # Restore inventory for each item
        for item in order.items:
            product = self.db.get(Product, item.product_id)
            if product:
                product.quantity += item.quantity
                inv_item = (
                    self.db.query(InventoryItem)
                    .filter(InventoryItem.product_id == product.id)
                    .first()
                )
                wh_id = inv_item.warehouse_id if inv_item else 1
                if inv_item:
                    inv_item.quantity += item.quantity

                movement = StockMovement(
                    product_id=product.id,
                    warehouse_id=wh_id,
                    quantity=item.quantity,
                    movement_type="STOCK_IN",
                    performed_by=str(user_id),
                    reference=f"REFUND:{order.order_number}",
                )
                self.db.add(movement)

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        order.status = "REFUNDED"
        order.notes = f"{order.notes or ''}\n[Refunded on {now_str}] Reason: {reason}".strip()

        self.notification_service.create_notification(
            title=f"Order Refunded: {order.order_number}",
            message=f"Order {order.order_number} refunded (${order.total_amount:,.2f}). Inventory restored.",
            category="SALE",
            severity="WARNING",
            link_url="/sales",
        )

        self.db.commit()
        return self._format_order_response(order)

    def get_sales_summary(self) -> SalesSummaryResponse:
        total_orders = self.db.query(SalesOrder).count()
        completed_orders = self.db.query(SalesOrder).filter(SalesOrder.status == "COMPLETED").count()
        refunded_orders = self.db.query(SalesOrder).filter(SalesOrder.status == "REFUNDED").count()

        completed_revenue = (
            self.db.query(func.coalesce(func.sum(SalesOrder.total_amount), 0))
            .filter(SalesOrder.status == "COMPLETED")
            .scalar()
        )

        items_sold = (
            self.db.query(func.coalesce(func.sum(SalesOrderItem.quantity), 0))
            .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
            .filter(SalesOrder.status == "COMPLETED")
            .scalar()
        )

        avg_order = (float(completed_revenue) / completed_orders) if completed_orders > 0 else 0.0

        return SalesSummaryResponse(
            total_orders=total_orders,
            total_revenue=float(completed_revenue),
            total_items_sold=int(items_sold),
            average_order_value=round(avg_order, 2),
            completed_orders=completed_orders,
            refunded_orders=refunded_orders,
        )

    def _format_order_response(self, order: SalesOrder) -> SalesOrderResponse:
        items_res = []
        for item in order.items:
            prod_name = item.product.name if item.product else "Unknown Product"
            prod_sku = item.product.sku if item.product else "N/A"
            items_res.append(
                SalesOrderItemResponse(
                    id=item.id,
                    sales_order_id=item.sales_order_id,
                    product_id=item.product_id,
                    product_name=prod_name,
                    product_sku=prod_sku,
                    quantity=item.quantity,
                    unit_price=float(item.unit_price),
                    unit_cost=float(item.unit_cost),
                    discount_percent=float(item.discount_percent),
                    discount_amount=float(item.discount_amount),
                    line_total=float(item.line_total),
                )
            )

        return SalesOrderResponse(
            id=order.id,
            order_number=order.order_number,
            customer_name=order.customer_name,
            customer_email=order.customer_email,
            customer_phone=order.customer_phone,
            channel=order.channel,
            payment_method=order.payment_method,
            subtotal=float(order.subtotal),
            discount_amount=float(order.discount_amount),
            tax_amount=float(order.tax_amount),
            total_amount=float(order.total_amount),
            status=order.status,
            notes=order.notes,
            created_by=order.created_by,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=items_res,
        )
