"""FastAPI router for inventory valuation, sales reports, and CSV exports."""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import TokenData, require_role, get_token_data
from app.schemas.report import InventoryValuationReport, SalesPerformanceReport
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


@router.get("/valuation", response_model=InventoryValuationReport)
def get_inventory_valuation(
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "manager")),
):
    """Get complete inventory valuation, cost value, retail value, and profit margins."""
    service = ReportService(db)
    return service.get_inventory_valuation_report()


@router.get("/sales-performance", response_model=SalesPerformanceReport)
def get_sales_performance(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "manager")),
):
    """Get sales performance KPIs, top selling products, and daily revenue trends."""
    service = ReportService(db)
    return service.get_sales_performance_report(start_date=start_date, end_date=end_date)


@router.get("/export/inventory-csv")
def export_inventory_csv(
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "manager")),
):
    """Export inventory valuation and stock levels as a CSV spreadsheet."""
    service = ReportService(db)
    csv_data = service.generate_inventory_csv()
    filename = f"inventory_valuation_{date.today().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/sales-csv")
def export_sales_csv(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "manager")),
):
    """Export sales orders history as a CSV spreadsheet."""
    service = ReportService(db)
    csv_data = service.generate_sales_csv(start_date=start_date, end_date=end_date)
    filename = f"sales_orders_{date.today().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/movements-csv")
def export_stock_movements_csv(
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "manager")),
):
    """Export stock ledger movements audit log as a CSV spreadsheet."""
    service = ReportService(db)
    csv_data = service.generate_stock_movements_csv(limit=limit)
    filename = f"stock_movements_{date.today().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
