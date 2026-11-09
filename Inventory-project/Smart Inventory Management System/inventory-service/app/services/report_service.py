"""Service for generating inventory valuation, sales performance, and CSV exports."""
import csv
import io
from datetime import date, datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.schemas.report import (
    DailySalesMetric,
    InventoryValuationReport,
    ProductValuationItem,
    SalesPerformanceReport,
    TopSellingProduct,
)


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_inventory_valuation_report(self) -> InventoryValuationReport:
        products = self.db.query(Product).order_by(Product.name).all()

        items: List[ProductValuationItem] = []
        total_units = 0
        total_cost = 0.0
        total_retail = 0.0
        low_stock_count = 0
        out_of_stock_count = 0

        for p in products:
            qty = p.quantity
            cost = float(p.unit_cost or 0.0)
            price = float(p.price)
            line_cost = qty * cost
            line_retail = qty * price
            line_profit = line_retail - line_cost
            margin = (line_profit / line_retail * 100.0) if line_retail > 0 else 0.0

            if qty == 0:
                status = "OUT_OF_STOCK"
                out_of_stock_count += 1
            elif qty <= p.reorder_point:
                status = "LOW_STOCK"
                low_stock_count += 1
            elif qty > (p.reorder_point * 4):
                status = "OVERSTOCKED"
            else:
                status = "HEALTHY"

            total_units += qty
            total_cost += line_cost
            total_retail += line_retail

            items.append(
                ProductValuationItem(
                    product_id=p.id,
                    product_name=p.name,
                    sku=p.sku,
                    category=p.category or "General",
                    quantity_on_hand=qty,
                    unit_cost=round(cost, 2),
                    unit_price=round(price, 2),
                    total_cost_value=round(line_cost, 2),
                    total_retail_value=round(line_retail, 2),
                    potential_profit=round(line_profit, 2),
                    margin_percent=round(margin, 1),
                    reorder_point=p.reorder_point,
                    stock_status=status,
                )
            )

        total_profit = total_retail - total_cost
        overall_margin = (total_profit / total_retail * 100.0) if total_retail > 0 else 0.0

        return InventoryValuationReport(
            total_products=len(products),
            total_units_in_stock=total_units,
            total_cost_value=round(total_cost, 2),
            total_retail_value=round(total_retail, 2),
            total_potential_profit=round(total_profit, 2),
            overall_margin_percent=round(overall_margin, 1),
            low_stock_product_count=low_stock_count,
            out_of_stock_product_count=out_of_stock_count,
            products=items,
        )

    def get_sales_performance_report(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> SalesPerformanceReport:
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        orders_query = self.db.query(SalesOrder).filter(
            SalesOrder.status == "COMPLETED",
            func.date(SalesOrder.created_at) >= start_date,
            func.date(SalesOrder.created_at) <= end_date,
        )

        total_orders = orders_query.count()
        total_revenue = orders_query.with_entities(func.coalesce(func.sum(SalesOrder.total_amount), 0.0)).scalar()
        total_discount = orders_query.with_entities(func.coalesce(func.sum(SalesOrder.discount_amount), 0.0)).scalar()

        total_units = (
            self.db.query(func.coalesce(func.sum(SalesOrderItem.quantity), 0))
            .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
            .filter(
                SalesOrder.status == "COMPLETED",
                func.date(SalesOrder.created_at) >= start_date,
                func.date(SalesOrder.created_at) <= end_date,
            )
            .scalar()
        )

        avg_order = (float(total_revenue) / total_orders) if total_orders > 0 else 0.0

        # Top products
        top_rows = (
            self.db.query(
                Product.id,
                Product.name,
                Product.sku,
                func.sum(SalesOrderItem.quantity).label("units_sold"),
                func.sum(SalesOrderItem.line_total).label("revenue"),
                func.sum(SalesOrderItem.line_total - (SalesOrderItem.quantity * SalesOrderItem.unit_cost)).label("profit"),
            )
            .join(SalesOrderItem, SalesOrderItem.product_id == Product.id)
            .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
            .filter(
                SalesOrder.status == "COMPLETED",
                func.date(SalesOrder.created_at) >= start_date,
                func.date(SalesOrder.created_at) <= end_date,
            )
            .group_by(Product.id, Product.name, Product.sku)
            .order_by(desc("revenue"))
            .limit(10)
            .all()
        )

        top_products = [
            TopSellingProduct(
                product_id=row[0],
                product_name=row[1],
                sku=row[2],
                units_sold=int(row[3] or 0),
                total_revenue=round(float(row[4] or 0.0), 2),
                gross_profit=round(float(row[5] or 0.0), 2),
            )
            for row in top_rows
        ]

        # Daily trends
        daily_rows = (
            self.db.query(
                func.date(SalesOrder.created_at).label("sale_date"),
                func.count(SalesOrder.id).label("orders"),
                func.sum(SalesOrder.total_amount).label("revenue"),
            )
            .filter(
                SalesOrder.status == "COMPLETED",
                func.date(SalesOrder.created_at) >= start_date,
                func.date(SalesOrder.created_at) <= end_date,
            )
            .group_by(func.date(SalesOrder.created_at))
            .order_by("sale_date")
            .all()
        )

        daily_trends = [
            DailySalesMetric(
                date=datetime.strptime(str(row[0]), "%Y-%m-%d").date() if isinstance(row[0], str) else row[0],
                order_count=int(row[1] or 0),
                units_sold=0,  # aggregated via orders
                revenue=round(float(row[2] or 0.0), 2),
            )
            for row in daily_rows
        ]

        return SalesPerformanceReport(
            start_date=start_date,
            end_date=end_date,
            total_orders=total_orders,
            total_revenue=round(float(total_revenue), 2),
            total_units_sold=int(total_units),
            total_discount_given=round(float(total_discount), 2),
            average_order_value=round(avg_order, 2),
            top_products=top_products,
            daily_trends=daily_trends,
        )

    def generate_inventory_csv(self) -> str:
        report = self.get_inventory_valuation_report()
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Product ID",
            "Product Name",
            "SKU",
            "Category",
            "Stock On Hand",
            "Reorder Point",
            "Unit Cost ($)",
            "Unit Price ($)",
            "Total Cost Value ($)",
            "Total Retail Value ($)",
            "Potential Profit ($)",
            "Margin (%)",
            "Stock Status",
        ])

        for p in report.products:
            writer.writerow([
                p.product_id,
                p.product_name,
                p.sku,
                p.category,
                p.quantity_on_hand,
                p.reorder_point,
                f"{p.unit_cost:.2f}",
                f"{p.unit_price:.2f}",
                f"{p.total_cost_value:.2f}",
                f"{p.total_retail_value:.2f}",
                f"{p.potential_profit:.2f}",
                f"{p.margin_percent:.1f}%",
                p.stock_status,
            ])

        return output.getvalue()

    def generate_sales_csv(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> str:
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        orders = (
            self.db.query(SalesOrder)
            .filter(
                func.date(SalesOrder.created_at) >= start_date,
                func.date(SalesOrder.created_at) <= end_date,
            )
            .order_by(desc(SalesOrder.created_at))
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Order Number",
            "Date",
            "Customer Name",
            "Email",
            "Phone",
            "Channel",
            "Payment Method",
            "Subtotal ($)",
            "Discount ($)",
            "Total Amount ($)",
            "Status",
            "Items Count",
        ])

        for o in orders:
            writer.writerow([
                o.order_number,
                o.created_at.strftime("%Y-%m-%d %H:%M:%S") if o.created_at else "",
                o.customer_name,
                o.customer_email or "",
                o.customer_phone or "",
                o.channel,
                o.payment_method,
                f"{o.subtotal:.2f}",
                f"{o.discount_amount:.2f}",
                f"{o.total_amount:.2f}",
                o.status,
                len(o.items),
            ])

        return output.getvalue()

    def generate_stock_movements_csv(self, limit: int = 500) -> str:
        movements = (
            self.db.query(StockMovement)
            .order_by(desc(StockMovement.created_at))
            .limit(limit)
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Movement ID",
            "Timestamp",
            "Product ID",
            "Product Name",
            "SKU",
            "Movement Type",
            "Quantity",
            "Reference",
            "Notes",
            "User ID",
        ])

        for m in movements:
            prod_name = m.product.name if m.product else "N/A"
            prod_sku = m.product.sku if m.product else "N/A"
            writer.writerow([
                m.id,
                m.created_at.strftime("%Y-%m-%d %H:%M:%S") if m.created_at else "",
                m.product_id,
                prod_name,
                prod_sku,
                m.movement_type,
                m.quantity,
                m.reference or "",
                m.notes or "",
                m.created_by,
            ])

        return output.getvalue()
