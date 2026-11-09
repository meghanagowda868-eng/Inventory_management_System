"""Reorder Management Service — handles low-stock detection, approval workflow, and PO generation."""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.reorder_request import ReorderRequest
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse
from app.schemas.purchase_order import PurchaseOrderItemResponse, PurchaseOrderResponse
from app.schemas.reorder import (
    ReorderDetectionItem,
    ReorderRequestCreate,
    ReorderRequestResponse,
    ReorderRequestUpdate,
    ReorderSummaryResponse,
    ReorderToPOCreateRequest,
)


class ReorderService:
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
        # Find next available sequential number
        seq = count + 1
        po_num = f"{prefix}{seq:04d}"
        while self.db.query(PurchaseOrder.id).filter(PurchaseOrder.po_number == po_num).first():
            seq += 1
            po_num = f"{prefix}{seq:04d}"
        return po_num

    def _to_reorder_response(self, req: ReorderRequest) -> ReorderRequestResponse:
        po = req.purchase_orders[0] if req.purchase_orders else None
        return ReorderRequestResponse(
            id=req.id,
            product_id=req.product_id,
            product_name=req.product.name if req.product else f"Product #{req.product_id}",
            sku=req.product.sku if req.product else "N/A",
            current_stock=req.product.quantity if req.product else 0,
            reorder_point=req.product.reorder_point if req.product else 10,
            supplier_id=req.supplier_id or (req.product.supplier_id if req.product else None),
            supplier_name=(req.supplier.name if req.supplier else (req.product.supplier_name if req.product else None)),
            requested_quantity=req.requested_quantity,
            reorder_reason=req.reorder_reason,
            rejection_reason=req.rejection_reason,
            status=req.status,
            requested_by=req.requested_by,
            approved_by=req.approved_by,
            approved_at=req.approved_at,
            created_at=req.created_at,
            updated_at=req.updated_at,
            po_id=po.id if po else None,
            po_number=po.po_number if po else None,
        )

    # ── Detection & Recommendations ──────────────────────────────────────────

    def list_reorder_recommendations(self) -> list[ReorderDetectionItem]:
        """Detect all products needing reorders (current_stock <= reorder_point)."""
        products = (
            self.db.query(Product)
            .options(joinedload(Product.supplier), joinedload(Product.subcategory))
            .filter(Product.is_active.is_(True), Product.quantity <= Product.reorder_point)
            .order_by(Product.quantity.asc(), Product.reorder_point.desc())
            .all()
        )

        # Fetch all active reorder requests (not COMPLETED or REJECTED)
        active_requests = (
            self.db.query(ReorderRequest)
            .filter(ReorderRequest.status.in_(["PENDING", "APPROVED", "ORDERED", "RECEIVED"]))
            .all()
        )
        active_map = {r.product_id: r for r in active_requests}

        items: list[ReorderDetectionItem] = []
        for p in products:
            active_req = active_map.get(p.id)
            has_active = active_req is not None
            status_label = active_req.status if has_active else "REQUIRED"

            items.append(
                ReorderDetectionItem(
                    product_id=p.id,
                    product_name=p.name,
                    sku=p.sku,
                    category_name=p.category_name,
                    current_stock=p.quantity,
                    reorder_point=p.reorder_point,
                    reorder_quantity=p.reorder_quantity,
                    unit_cost=float(p.unit_cost) if p.unit_cost is not None else None,
                    price=float(p.price),
                    supplier_id=p.supplier_id,
                    supplier_name=p.supplier_name,
                    has_active_request=has_active,
                    active_reorder_request_id=active_req.id if active_req else None,
                    active_reorder_status=active_req.status if active_req else None,
                    status=status_label,
                )
            )
        return items

    # ── Request Lifecycle ───────────────────────────────────────────────────

    def create_reorder_request(self, data: ReorderRequestCreate, requested_by: int) -> ReorderRequestResponse:
        """Create a new reorder request with duplicate prevention."""
        product = (
            self.db.query(Product)
            .options(joinedload(Product.supplier))
            .filter(Product.id == data.product_id, Product.is_active.is_(True))
            .first()
        )
        if not product:
            raise ValueError(f"Active product {data.product_id} not found")

        # Duplicate active reorder prevention
        existing = (
            self.db.query(ReorderRequest)
            .filter(
                ReorderRequest.product_id == product.id,
                ReorderRequest.status.in_(["PENDING", "APPROVED", "ORDERED", "RECEIVED"]),
            )
            .first()
        )
        if existing:
            raise ValueError(
                f"An active reorder request #{existing.id} ({existing.status}) already exists for '{product.name}'. "
                f"You must complete or reject it before creating a new one."
            )

        # Resolve supplier
        supplier_id = data.supplier_id or product.supplier_id
        if supplier_id:
            supplier = self.db.get(Supplier, supplier_id)
            if not supplier or not supplier.is_active:
                raise ValueError(f"Active supplier {supplier_id} not found")

        if data.requested_quantity <= 0:
            raise ValueError("Requested quantity must be greater than 0")

        req = ReorderRequest(
            product_id=product.id,
            supplier_id=supplier_id,
            requested_quantity=data.requested_quantity,
            reorder_reason=data.reorder_reason.strip() if data.reorder_reason else None,
            status="PENDING",
            requested_by=requested_by,
        )
        self.db.add(req)
        self.db.commit()
        self.db.refresh(req)
        return self.get_reorder_request(req.id)

    def list_reorder_requests(self, status: Optional[str] = None) -> list[ReorderRequestResponse]:
        """List all reorder requests with optional status filter."""
        q = (
            self.db.query(ReorderRequest)
            .options(
                joinedload(ReorderRequest.product).joinedload(Product.supplier),
                joinedload(ReorderRequest.supplier),
                joinedload(ReorderRequest.purchase_orders),
            )
            .order_by(ReorderRequest.created_at.desc())
        )
        if status:
            q = q.filter(ReorderRequest.status == status.upper().strip())
        requests = q.all()
        return [self._to_reorder_response(r) for r in requests]

    def get_reorder_request(self, reorder_id: int) -> ReorderRequestResponse:
        """Fetch a single reorder request by ID."""
        req = (
            self.db.query(ReorderRequest)
            .options(
                joinedload(ReorderRequest.product).joinedload(Product.supplier),
                joinedload(ReorderRequest.supplier),
                joinedload(ReorderRequest.purchase_orders),
            )
            .filter(ReorderRequest.id == reorder_id)
            .first()
        )
        if not req:
            raise ValueError(f"Reorder request {reorder_id} not found")
        return self._to_reorder_response(req)

    def update_reorder_request(self, reorder_id: int, data: ReorderRequestUpdate) -> ReorderRequestResponse:
        """Update a pending reorder request."""
        req = self.db.query(ReorderRequest).filter(ReorderRequest.id == reorder_id).with_for_update().first()
        if not req:
            raise ValueError(f"Reorder request {reorder_id} not found")
        if req.status != "PENDING":
            raise ValueError(f"Only PENDING requests can be modified; current status is {req.status}")

        if data.requested_quantity is not None:
            if data.requested_quantity <= 0:
                raise ValueError("Requested quantity must be greater than 0")
            req.requested_quantity = data.requested_quantity

        if data.supplier_id is not None:
            supplier = self.db.get(Supplier, data.supplier_id)
            if not supplier or not supplier.is_active:
                raise ValueError(f"Active supplier {data.supplier_id} not found")
            req.supplier_id = supplier.id

        if data.reorder_reason is not None:
            req.reorder_reason = data.reorder_reason.strip() or None

        self.db.commit()
        return self.get_reorder_request(reorder_id)

    def approve_reorder_request(self, reorder_id: int, approved_by: int) -> ReorderRequestResponse:
        """Approve a pending reorder request."""
        req = self.db.query(ReorderRequest).filter(ReorderRequest.id == reorder_id).with_for_update().first()
        if not req:
            raise ValueError(f"Reorder request {reorder_id} not found")
        if req.status != "PENDING":
            raise ValueError(f"Only PENDING reorder requests can be approved; current status is {req.status}")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        req.status = "APPROVED"
        req.approved_by = approved_by
        req.approved_at = now
        self.db.commit()
        return self.get_reorder_request(reorder_id)

    def reject_reorder_request(self, reorder_id: int, rejection_reason: str, rejected_by: int) -> ReorderRequestResponse:
        """Reject a pending reorder request with a required reason."""
        if not rejection_reason or not rejection_reason.strip():
            raise ValueError("Rejection reason is required")

        req = self.db.query(ReorderRequest).filter(ReorderRequest.id == reorder_id).with_for_update().first()
        if not req:
            raise ValueError(f"Reorder request {reorder_id} not found")
        if req.status != "PENDING":
            raise ValueError(f"Only PENDING reorder requests can be rejected; current status is {req.status}")

        req.status = "REJECTED"
        req.rejection_reason = rejection_reason.strip()
        req.approved_by = rejected_by
        self.db.commit()
        return self.get_reorder_request(reorder_id)

    # ── Convert Approved Request to Purchase Order ──────────────────────────

    def create_purchase_order_from_reorder(
        self, reorder_id: int, data: ReorderToPOCreateRequest, created_by: int
    ) -> PurchaseOrderResponse:
        """Convert an APPROVED reorder request directly into a Purchase Order."""
        req = (
            self.db.query(ReorderRequest)
            .options(joinedload(ReorderRequest.product).joinedload(Product.supplier))
            .filter(ReorderRequest.id == reorder_id)
            .with_for_update()
            .first()
        )
        if not req:
            raise ValueError(f"Reorder request {reorder_id} not found")
        if req.status != "APPROVED":
            raise ValueError(f"Only APPROVED reorder requests can be converted to Purchase Orders; current status is {req.status}")

        # Resolve supplier
        supplier_id = data.supplier_id or req.supplier_id or (req.product.supplier_id if req.product else None)
        if not supplier_id:
            raise ValueError("A supplier is required to create a purchase order. Please specify or select a supplier.")
        supplier = self.db.get(Supplier, supplier_id)
        if not supplier or not supplier.is_active:
            raise ValueError(f"Active supplier {supplier_id} not found")

        # Resolve warehouse
        warehouse_id = data.warehouse_id or 1
        warehouse = self.db.get(Warehouse, warehouse_id)
        if not warehouse or warehouse.status != "ACTIVE":
            warehouse = self.db.query(Warehouse).filter(Warehouse.status == "ACTIVE").first()
            if not warehouse:
                raise ValueError("No active warehouse found in system")

        # Resolve cost
        unit_cost = data.unit_cost or (req.product.unit_cost if req.product else None) or (Decimal(str(req.product.price)) if req.product else Decimal("10.00"))
        normalized_cost = self._money(unit_cost)
        line_total = self._money(normalized_cost * req.requested_quantity)

        po_number = self._generate_po_number()

        po = PurchaseOrder(
            po_number=po_number,
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            reorder_request_id=req.id,
            status="ORDERED",
            order_date=date.today(),
            expected_delivery=data.expected_delivery,
            total_amount=line_total,
            created_by=created_by,
        )
        po.items.append(
            PurchaseOrderItem(
                product_id=req.product_id,
                quantity=req.requested_quantity,
                unit_cost=normalized_cost,
                total_cost=line_total,
                received_quantity=0,
            )
        )

        req.status = "ORDERED"
        req.supplier_id = supplier.id

        self.db.add(po)
        self.db.commit()

        # Build PurchaseOrderResponse
        return PurchaseOrderResponse(
            id=po.id,
            po_number=po.po_number,
            supplier_id=po.supplier_id,
            supplier_name=supplier.name,
            warehouse_id=warehouse.id,
            warehouse_name=warehouse.name,
            reorder_request_id=req.id,
            status=po.status,
            order_date=po.order_date,
            expected_delivery=po.expected_delivery,
            total_amount=po.total_amount,
            created_by=po.created_by,
            approved_by=po.approved_by,
            received_by=po.received_by,
            received_at=po.received_at,
            created_at=po.created_at,
            updated_at=po.updated_at,
            items=[
                PurchaseOrderItemResponse(
                    id=po.items[0].id,
                    product_id=req.product_id,
                    product_name=req.product.name,
                    sku=req.product.sku,
                    quantity=req.requested_quantity,
                    ordered_quantity=req.requested_quantity,
                    unit_cost=normalized_cost,
                    unit_price=normalized_cost,
                    total_cost=line_total,
                    total_price=line_total,
                    received_quantity=0,
                    remaining_quantity=req.requested_quantity,
                )
            ],
        )

    # ── Summary & Metrics ───────────────────────────────────────────────────

    def get_summary(self) -> ReorderSummaryResponse:
        """Dashboard summary of reorder metrics."""
        requiring = (
            self.db.query(func.count(Product.id))
            .filter(Product.is_active.is_(True), Product.quantity <= Product.reorder_point)
            .scalar()
            or 0
        )
        pending = (
            self.db.query(func.count(ReorderRequest.id))
            .filter(ReorderRequest.status == "PENDING")
            .scalar()
            or 0
        )
        approved = (
            self.db.query(func.count(ReorderRequest.id))
            .filter(ReorderRequest.status == "APPROVED")
            .scalar()
            or 0
        )
        in_transit = (
            self.db.query(func.count(PurchaseOrder.id))
            .filter(PurchaseOrder.status == "ORDERED")
            .scalar()
            or 0
        )
        partially = (
            self.db.query(func.count(PurchaseOrder.id))
            .filter(PurchaseOrder.status == "PARTIALLY_RECEIVED")
            .scalar()
            or 0
        )
        received = (
            self.db.query(func.count(PurchaseOrder.id))
            .filter(PurchaseOrder.status == "RECEIVED")
            .scalar()
            or 0
        )
        total = self.db.query(func.count(ReorderRequest.id)).scalar() or 0

        return ReorderSummaryResponse(
            products_requiring_reorder=int(requiring),
            pending_requests=int(pending),
            approved_requests=int(approved),
            orders_in_transit=int(in_transit),
            partially_received_orders=int(partially),
            recently_received_stock=int(received),
            total_requests=int(total),
        )
