"""
Inventory Insights Service.
Fetches live data from Inventory Service and computes insights.
"""
import httpx
import logging
from typing import Optional

from app.config import get_settings
from app.schemas.ai_schemas import InventoryInsightsResponse

logger = logging.getLogger("ai_service.insights")
settings = get_settings()


class InsightsService:
    """Compute inventory overview insights."""

    async def get_insights(self, access_token: str) -> InventoryInsightsResponse:
        """
        Fetch product stats from Inventory Service.
        Falls back to demo data if service is unreachable (Phase 1 dev mode).
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{settings.inventory_service_url}/inventory/products",
                    params={"page_size": 1},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                total_products = resp.json().get("total", 0)

                # Fetch low stock
                low_resp = await client.get(
                    f"{settings.inventory_service_url}/inventory/products/low-stock",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                low_resp.raise_for_status()
                low_stock_items = low_resp.json()
                low_stock_count = len(low_stock_items)

                # Fetch out of stock
                out_resp = await client.get(
                    f"{settings.inventory_service_url}/inventory/products",
                    params={"stock_status": "out_of_stock", "page_size": 100},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                out_resp.raise_for_status()
                out_of_stock_count = out_resp.json().get("total", 0)

                # Fetch all pages using the inventory API's maximum page size.
                all_items = []
                page = 1
                total_pages = 1
                while page <= total_pages:
                    all_resp = await client.get(
                        f"{settings.inventory_service_url}/inventory/products",
                        params={"page": page, "page_size": 100},
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    all_resp.raise_for_status()
                    page_data = all_resp.json()
                    all_items.extend(page_data.get("items", []))
                    total_pages = page_data.get("total_pages", 1)
                    page += 1
                total_value = sum(
                    item["price"] * item["quantity"] for item in all_items
                )

        except Exception as exc:
            logger.warning("Could not reach inventory service: %s. Using demo data.", exc)
            # Demo fallback for development
            return self._demo_insights()

        healthy = max(0, total_products - low_stock_count - out_of_stock_count)
        low_pct = round((low_stock_count / total_products * 100), 1) if total_products else 0

        return InventoryInsightsResponse(
            total_products=total_products,
            total_inventory_value=round(total_value, 2),
            low_stock_count=low_stock_count,
            out_of_stock_count=out_of_stock_count,
            healthy_stock_count=healthy,
            low_stock_percentage=low_pct,
        )

    @staticmethod
    def _demo_insights() -> InventoryInsightsResponse:
        """Demo data when inventory service is unreachable."""
        return InventoryInsightsResponse(
            total_products=247,
            total_inventory_value=384750.50,
            low_stock_count=18,
            out_of_stock_count=5,
            healthy_stock_count=224,
            low_stock_percentage=7.3,
        )
