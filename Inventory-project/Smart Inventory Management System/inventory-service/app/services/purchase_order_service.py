"""Manager-confirmed purchase-order lifecycle, partial/full receipts, and supplier CRUD."""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.inventory import InventoryItem
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.reorder_request import ReorderRequest
from app.models.sales_history import SeasonalEvent
from app.models.stock_movement import StockMovement
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse
from app.schemas.purchase_order import (
    PurchaseOrderCreateRequest,
    PurchaseOrderItemResponse,
    PurchaseOrderResponse,
    ReceiveOrderRequest,
    SupplierCreateRequest,
    SupplierResponse,
    SupplierUpdateRequest,
)


class PurchaseOrderService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _money(value: Decimal | float) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _generate_po_number(self) -> str:
        current_year = date.today().year
        prefix = f"PO-{current_year}-"
        count = (
            self.db.query(func.count(PurchaseOrder.id))
            .filter(PurchaseOrder.po_number.like(f"{prefix}%"))
            .scalar()
            or 0
        )
        seq = count + 1
        po_num = f"{prefix}{seq:04d}"
        while self.db.query(PurchaseOrder.id).filter(PurchaseOrder.po_number == po_num).first():
            seq += 1
            po_num = f"{prefix}{seq:04d}"
        return po_num

    # ── Supplier Management (CRUD) ──────────────────────────────────────────

    def create_supplier(self, name: Union[str, SupplierCreateRequest, None] = None, **fields) -> SupplierResponse:
        if isinstance(name, SupplierCreateRequest):
            data = name
        else:
            data = SupplierCreateRequest(name=name or "", **fields)

        contact = data.contact_person or data.contact_name
        supplier = Supplier(
            name=data.name.strip(),
            contact_name=contact.strip() if contact else None,
            email=data.email.strip().lower() if data.email else None,
            phone=data.phone.strip() if data.phone else None,
            address=data.address.strip() if data.address else None,
            status=data.status or "ACTIVE",
            is_active=True,
        )
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return SupplierResponse.model_validate(supplier)

    def get_supplier(self, supplier_id: int) -> SupplierResponse:
        supplier = self.db.get(Supplier, supplier_id)
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")
        return SupplierResponse.model_validate(supplier)

    def list_suppliers(self, include_inactive: bool = False) -> list[SupplierResponse]:
        q = self.db.query(Supplier)
        if not include_inactive:
            q = q.filter(Supplier.is_active.is_(True))
        suppliers = q.order_by(Supplier.name).all()
        return [SupplierResponse.model_validate(s) for s in suppliers]

    def update_supplier(self, supplier_id: int, data: SupplierUpdateRequest) -> SupplierResponse:
        supplier = self.db.get(Supplier, supplier_id)
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")

        updates = data.model_dump(exclude_none=True)
        if "name" in updates:
            supplier.name = updates["name"].strip()
        contact = updates.get("contact_person") or updates.get("contact_name")
        if contact is not None:
            supplier.contact_name = contact.strip() if contact else None
        if "email" in updates:
            supplier.email = updates["email"].strip().lower() if updates["email"] else None
        if "phone" in updates:
            supplier.phone = updates["phone"].strip() if updates["phone"] else None
        if "address" in updates:
            supplier.address = updates["address"].strip() if updates["address"] else None
        if "status" in updates:
            supplier.status = updates["status"]
            if updates["status"].upper() == "INACTIVE":
                supplier.is_active = False
            elif updates["status"].upper() == "ACTIVE":
                supplier.is_active = True
        if "is_active" in updates:
            supplier.is_active = updates["is_active"]
            supplier.status = "ACTIVE" if updates["is_active"] else "INACTIVE"

        self.db.commit()
        self.db.refresh(supplier)
        return SupplierResponse.model_validate(supplier)

    def delete_supplier(self, supplier_id: int) -> dict:
        supplier = self.db.get(Supplier, supplier_id)
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")
        supplier.is_active = False
        supplier.status = "INACTIVE"
        self.db.commit()
        return {"message": f"Supplier '{supplier.name}' deactivated successfully"}

    # ── Purchase Order Lifecycle ─────────────────────────────────────────────

    def create_order(
        self,
        *,
        supplier_id: int | None = None,
        warehouse_id: int | None = None,
        expected_delivery=None,
        created_by: int,
        items=None,
        data: PurchaseOrderCreateRequest | None = None,
    ) -> PurchaseOrderResponse:
        if data is None:
            data = PurchaseOrderCreateRequest(
                supplier_id=supplier_id or 1,
                warehouse_id=warehouse_id or 1,
                expected_delivery=expected_delivery,
                items=items or [],
            )

        supplier = self.db.get(Supplier, data.supplier_id)
        if not supplier or not supplier.is_active:
            raise ValueError("Active supplier not found")

        warehouse = self.db.get(Warehouse, data.warehouse_id)
        if not warehouse or warehouse.status != "ACTIVE":
            warehouse = self.db.query(Warehouse).filter(Warehouse.status == "ACTIVE").first()
            if not warehouse:
                raise ValueError("Active warehouse not found")

        po_number = self._generate_po_number()

        order = PurchaseOrder(
            po_number=po_number,
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            reorder_request_id=data.reorder_request_id,
            expected_delivery=data.expected_delivery,
            created_by=created_by,
            status="PENDING_APPROVAL",
            total_amount=Decimal("0.00"),
        )
        total = Decimal("0.00")
        for requested_item in data.items:
            product = (
                self.db.query(Product)
                .filter(Product.id == requested_item.product_id, Product.is_active.is_(True))
                .with_for_update()
                .first()
            )
            if not product:
                raise ValueError(f"Active product {requested_item.product_id} not found")
            unit_cost = requested_item.unit_cost or product.unit_cost or product.price
            if unit_cost is None:
                raise ValueError(f"Unit cost is required for {product.name}; no product cost is configured")
            normalized_cost = self._money(unit_cost)
            line_total = self._money(normalized_cost * requested_item.quantity)
            total += line_total
            order.items.append(
                PurchaseOrderItem(
                    product_id=product.id,
                    quantity=requested_item.quantity,
                    unit_cost=normalized_cost,
                    total_cost=line_total,
                    received_quantity=0,
                )
            )

        order.total_amount = self._money(total)

        if data.reorder_request_id:
            reorder_req = self.db.get(ReorderRequest, data.reorder_request_id)
            if reorder_req:
                reorder_req.status = "ORDERED"

        self.db.add(order)
        self.db.commit()
        return self.get_order(order.id)

    def get_order(self, order_id: int) -> PurchaseOrderResponse:
        order = (
            self.db.query(PurchaseOrder)
            .options(
                joinedload(PurchaseOrder.supplier),
                joinedload(PurchaseOrder.warehouse),
                joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            )
            .filter(PurchaseOrder.id == order_id)
            .first()
        )
        if not order:
            raise ValueError(f"Purchase order {order_id} not found")

        po_number = order.po_number or f"PO-{order.created_at.year if order.created_at else date.today().year}-{order.id:04d}"

        return PurchaseOrderResponse(
            id=order.id,
            po_number=po_number,
            supplier_id=order.supplier_id,
            supplier_name=order.supplier.name if order.supplier else f"Supplier #{order.supplier_id}",
            warehouse_id=order.warehouse_id,
            warehouse_name=order.warehouse.name if order.warehouse else f"Warehouse #{order.warehouse_id}",
            reorder_request_id=order.reorder_request_id,
            status=order.status,
            order_date=order.order_date,
            expected_delivery=order.expected_delivery,
            total_amount=order.total_amount,
            created_by=order.created_by,
            approved_by=order.approved_by,
            received_by=order.received_by,
            received_at=order.received_at,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=[
                PurchaseOrderItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    product_name=item.product.name if item.product else f"Product #{item.product_id}",
                    sku=item.product.sku if item.product else "N/A",
                    quantity=item.quantity,
                    ordered_quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    unit_price=item.unit_cost,
                    total_cost=item.total_cost,
                    total_price=item.total_cost,
                    received_quantity=item.received_quantity,
                    remaining_quantity=max(0, item.quantity - item.received_quantity),
                )
                for item in order.items
            ],
        )

    def list_orders(self, status: Optional[str] = None) -> list[PurchaseOrderResponse]:
        q = self.db.query(PurchaseOrder.id).order_by(PurchaseOrder.created_at.desc())
        if status:
            q = q.filter(PurchaseOrder.status == status.upper().strip())
        order_ids = [row.id for row in q.all()]
        return [self.get_order(order_id) for order_id in order_ids]

    def approve_order(self, order_id: int, *, approved_by: int) -> PurchaseOrderResponse:
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).with_for_update().first()
        if not order:
            raise ValueError(f"Purchase order {order_id} not found")
        if order.status not in {"PENDING_APPROVAL", "DRAFT"}:
            raise ValueError(f"Only pending or draft purchase orders can be approved; current status is {order.status}")
        order.status = "APPROVED"
        order.approved_by = approved_by
        self.db.commit()
        return self.get_order(order_id)

    def mark_ordered(self, order_id: int) -> PurchaseOrderResponse:
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).with_for_update().first()
        if not order:
            raise ValueError(f"Purchase order {order_id} not found")
        if order.status not in {"APPROVED", "DRAFT"}:
            raise ValueError(f"Only approved or draft purchase orders can be marked ordered; current status is {order.status}")
        order.status = "ORDERED"
        self.db.commit()
        return self.get_order(order_id)

    # ── Receive Stock (Supports Partial & Full Receipts) ─────────────────────

    def receive_order(
        self,
        order_id: int,
        *,
        received_by: int,
        data: Optional[Union[ReceiveOrderRequest, dict]] = None,
    ) -> PurchaseOrderResponse:
        order = (
            self.db.query(PurchaseOrder)
            .options(joinedload(PurchaseOrder.items))
            .filter(PurchaseOrder.id == order_id)
            .with_for_update()
            .first()
        )
        if not order:
            raise ValueError(f"Purchase order {order_id} not found")
        if order.status == "RECEIVED":
            raise ValueError("Purchase order has already received all ordered stock")
        if order.status == "CANCELLED":
            raise ValueError("Cannot receive stock from a CANCELLED purchase order")
        if order.status not in {"ORDERED", "PARTIALLY_RECEIVED", "APPROVED"}:
            raise ValueError(f"Only ordered or partially received orders can be received; current status is {order.status}")

        # Parse receipt items
        receipt_map: dict[int, int] = {}
        if isinstance(data, ReceiveOrderRequest):
            if data.items:
                for it in data.items:
                    receipt_map[it.product_id] = receipt_map.get(it.product_id, 0) + it.received_quantity
            elif data.received_quantity is not None:
                if len(order.items) == 1:
                    receipt_map[order.items[0].product_id] = data.received_quantity
                else:
                    raise ValueError("Multi-item purchase order requires line item receipt quantities")
        elif isinstance(data, dict):
            if "items" in data and data["items"]:
                for it in data["items"]:
                    p_id = it.get("product_id")
                    qty = it.get("received_quantity")
                    if p_id and qty:
                        receipt_map[p_id] = receipt_map.get(p_id, 0) + int(qty)
            elif "received_quantity" in data and data["received_quantity"] is not None:
                if len(order.items) == 1:
                    receipt_map[order.items[0].product_id] = int(data["received_quantity"])
                else:
                    raise ValueError("Multi-item purchase order requires line item receipt quantities")

        # If no explicit quantities provided, receive remaining balance for all items
        if not receipt_map:
            for item in order.items:
                rem = item.quantity - item.received_quantity
                if rem > 0:
                    receipt_map[item.product_id] = rem

        if not receipt_map:
            raise ValueError("No items or quantities to receive")

        try:
            for item in order.items:
                incoming_qty = receipt_map.get(item.product_id, 0)
                if incoming_qty <= 0:
                    continue

                remaining = item.quantity - item.received_quantity
                if incoming_qty > remaining:
                    raise ValueError(
                        f"Received quantity ({incoming_qty}) cannot exceed remaining ordered quantity ({remaining}) "
                        f"for product {item.product_id}"
                    )

                product = (
                    self.db.query(Product)
                    .filter(Product.id == item.product_id, Product.is_active.is_(True))
                    .with_for_update()
                    .first()
                )
                if not product:
                    raise ValueError(f"Active product {item.product_id} not found")

                # Update warehouse inventory
                inventory = (
                    self.db.query(InventoryItem)
                    .filter(
                        InventoryItem.product_id == product.id,
                        InventoryItem.warehouse_id == order.warehouse_id,
                    )
                    .with_for_update()
                    .first()
                )
                if inventory:
                    inventory.quantity += incoming_qty
                else:
                    inventory = InventoryItem(
                        product_id=product.id,
                        warehouse_id=order.warehouse_id,
                        quantity=incoming_qty,
                    )
                    self.db.add(inventory)

                # Update product master quantity
                product.quantity += incoming_qty
                item.received_quantity += incoming_qty

                # Record stock movement transaction
                self.db.add(
                    StockMovement(
                        product_id=product.id,
                        warehouse_id=order.warehouse_id,
                        movement_type="STOCK_IN",
                        quantity=incoming_qty,
                        performed_by=str(received_by),
                        reference=f"Purchase Order {order.po_number}",
                    )
                )

            # Check if all items fully received
            all_received = all(it.received_quantity >= it.quantity for it in order.items)
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            if all_received:
                order.status = "RECEIVED"
                order.received_by = received_by
                order.received_at = now
                if order.reorder_request_id:
                    reorder_req = self.db.get(ReorderRequest, order.reorder_request_id)
                    if reorder_req:
                        reorder_req.status = "COMPLETED"
            else:
                order.status = "PARTIALLY_RECEIVED"
                order.received_by = received_by
                if order.reorder_request_id:
                    reorder_req = self.db.get(ReorderRequest, order.reorder_request_id)
                    if reorder_req:
                        reorder_req.status = "RECEIVED"

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return self.get_order(order_id)

    def cancel_order(self, order_id: int) -> PurchaseOrderResponse:
        order = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).with_for_update().first()
        if not order:
            raise ValueError(f"Purchase order {order_id} not found")
        if order.status in {"RECEIVED", "CANCELLED"}:
            raise ValueError(f"Purchase order in {order.status} status cannot be cancelled")
        order.status = "CANCELLED"
        if order.reorder_request_id:
            reorder_req = self.db.get(ReorderRequest, order.reorder_request_id)
            if reorder_req:
                reorder_req.status = "REJECTED"
                reorder_req.rejection_reason = f"Associated purchase order {order.po_number} was cancelled."
        self.db.commit()
        return self.get_order(order_id)

    def list_seasonal_events(self) -> list[SeasonalEvent]:
        return self.db.query(SeasonalEvent).filter(SeasonalEvent.is_active.is_(True)).order_by(SeasonalEvent.start_date).all()