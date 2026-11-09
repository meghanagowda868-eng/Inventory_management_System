"""
Natural Language Query (NLQ) Service — Phase 1 rule-based parser.

Converts plain English inventory questions into structured queries
and returns human-readable + structured answers.

Phase 2 upgrade path: replace _classify_intent() with an LLM call
(e.g., OpenAI GPT-4o or a local Ollama model).
"""
import re
import httpx
import logging

from app.config import get_settings
from app.schemas.ai_schemas import NLQueryRequest, NLQueryResponse

logger = logging.getLogger("ai_service.nlq")
settings = get_settings()

# ── Intent definitions ────────────────────────────────────────────────────────

INTENT_PATTERNS = [
    ("create_product",      [r"\bcreate\b.*\bproduct\b", r"\badd\b.*\bproduct\b", r"\bnew product\b"]),
    ("update_product",      [r"\bupdate\b.*\bproduct\b", r"\bedit\b.*\bproduct\b", r"\bchange\b.*\bproduct\b", r"\bset\b.*\b(price|quantity|stock|category)\b"]),
    ("delete_product",      [r"\bdelete\b.*\bproduct\b", r"\bremove\b.*\bproduct\b", r"\bdrop\b.*\bproduct\b"]),
    ("get_product",         [r"\bshow\b.*\bproduct\b", r"\bview\b.*\bproduct\b", r"\bget\b.*\bproduct\b", r"\bfind\b.*\bproduct\b", r"\bdetails\b.*\bproduct\b"]),
    ("reorder_urgency_query", [r"\breorder\b", r"re-?stock", r"\brestock\b", r"needs? .*urgently", r"urgent.*stock"]),
    ("low_stock_query",     [r"low.?stock", r"running.?low", r"below.?minimum"]),
    ("out_of_stock_query",  [r"out.?of.?stock", r"zero.?stock", r"empty", r"depleted"]),
    ("top_stock_query",     [r"selling more", r"sold more", r"best.?sell", r"most popular", r"top product", r"highest stock product", r"most stock"]),
    ("count_query",         [r"how many", r"total count", r"number of", r"count"]),
    ("value_query",         [r"total value", r"worth", r"inventory value", r"how much"]),
    ("category_query",      [r"which category", r"top category", r"highest.?stock", r"by category"]),
    ("product_search",      [r"show me", r"find", r"search", r"list", r"available"]),
]


def _classify_intent(query: str) -> str:
    q = query.lower()
    for intent, patterns in INTENT_PATTERNS:
        if any(re.search(p, q) for p in patterns):
            return intent
    return "unknown"


def _extract_product_name(query: str) -> str | None:
    """Attempt to extract a product name from the query."""
    patterns = [
        r"(?:create|add|new|update|edit|change|delete|remove|show|view|get|find|details)\s+(?:a\s+)?(?:new\s+)?product(?:\s+(?:called|named|for|with))?\s+([a-zA-Z0-9][a-zA-Z0-9\s\-&/()]+?)(?=\s+(?:with|sku|category|price|quantity|minimum|stock|for|$))",
        r"(?:called|named)\s+([a-zA-Z0-9][a-zA-Z0-9\s\-&/()]+?)(?=\s+(?:with|sku|category|price|quantity|minimum|stock|$))",
        r"(?:product\s+)([a-zA-Z0-9][a-zA-Z0-9\s\-&/()]+?)(?=\s+(?:with|sku|category|price|quantity|minimum|stock|$))",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if len(candidate) > 2:
                return candidate
    return None


def _extract_sku(query: str) -> str | None:
    match = re.search(r"(?:sku|code)\s*(?:is|=|:)?\s*([A-Za-z0-9\-]+)", query, re.IGNORECASE)
    if match:
        return match.group(1).strip().upper()
    return None


def _extract_category(query: str) -> str | None:
    match = re.search(r"(?:category|type)\s*(?:is|=|:)?\s*([A-Za-z0-9\s\-&]+)", query, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_price(query: str) -> float | None:
    match = re.search(r"(?:price|cost)\s*(?:is|=|:)?\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)", query, re.IGNORECASE)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def _extract_quantity(query: str) -> int | None:
    match = re.search(r"(?:quantity|stock|units)\s*(?:is|=|:)?\s*(\d+)", query, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extract_minimum_stock(query: str) -> int | None:
    match = re.search(r"(?:minimum stock|min stock|reorder level)\s*(?:is|=|:)?\s*(\d+)", query, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _normalize_product_name(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned.strip(" ,.;:-") or None


class NLQService:
    """
    Phase 1: rule-based NL query parser with live inventory data fetching.
    """

    async def query(self, data: NLQueryRequest, access_token: str) -> NLQueryResponse:
        intent = _classify_intent(data.query)
        logger.info("NLQ intent classified: %s for query: '%s'", intent, data.query)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                return await self._handle_intent(intent, data.query, client, headers)
        except Exception as exc:
            logger.warning("NLQ fetch failed: %s — returning demo response.", exc)
            return self._fallback_response(data.query, intent)

    async def _handle_intent(
        self, intent: str, query: str, client: httpx.AsyncClient, headers: dict
    ) -> NLQueryResponse:

        base = settings.inventory_service_url

        if intent == "low_stock_query":
            resp = await client.get(f"{base}/inventory/products/low-stock", headers=headers)
            items = resp.json() if resp.status_code == 200 else []
            count = len(items)
            answer = (
                f"There are {count} products with low stock."
                if count else "No products are currently low on stock. 🎉"
            )
            return NLQueryResponse(
                original_query=query,
                interpreted_intent="Show all low stock products",
                result_type="product_list",
                answer=answer,
                data={"products": items[:10], "total": count},
                suggestions=[
                    "Which low stock product needs reordering most urgently?",
                    "Show out of stock products",
                ],
            )

        elif intent == "reorder_urgency_query":
            resp = await client.get(f"{base}/inventory/products/low-stock", headers=headers)
            resp.raise_for_status()
            items = resp.json()
            urgent_items = sorted(
                items,
                key=lambda item: (
                    item.get("quantity", 0) / max(item.get("minimum_stock", 1), 1),
                    -item.get("minimum_stock", 0),
                ),
            )
            top_items = urgent_items[:5]
            if top_items:
                leader = top_items[0]
                answer = (
                    f"{leader.get('name')} needs reordering most urgently: "
                    f"{leader.get('quantity', 0)} units remaining against a minimum of "
                    f"{leader.get('minimum_stock', 0)}."
                )
            else:
                answer = "No products currently need reordering."
            return NLQueryResponse(
                original_query=query,
                interpreted_intent="Find products needing urgent reorder",
                result_type="product_list",
                answer=answer,
                data={"products": top_items, "total": len(items)},
                suggestions=["Show all low stock products", "Which product has the most stock?"],
            )

        elif intent == "out_of_stock_query":
            resp = await client.get(
                f"{base}/inventory/products",
                params={"stock_status": "out_of_stock", "page_size": 50},
                headers=headers,
            )
            data_json = resp.json() if resp.status_code == 200 else {}
            count = data_json.get("total", 0)
            items = data_json.get("items", [])
            answer = (
                f"{count} products are currently out of stock."
                if count else "All products are in stock! 🎉"
            )
            return NLQueryResponse(
                original_query=query,
                interpreted_intent="Show out of stock products",
                result_type="product_list",
                answer=answer,
                data={"products": items[:10], "total": count},
                suggestions=["Show low stock products", "What is the total inventory value?"],
            )

        elif intent == "create_product":
            payload = {
                "name": _normalize_product_name(_extract_product_name(query)) or "New Product",
                "sku": _extract_sku(query) or (_normalize_product_name(_extract_product_name(query)) or "NEW-PRODUCT").upper().replace(" ", "-")[:50],
                "category": _extract_category(query),
                "price": _extract_price(query) or 0.0,
                "quantity": _extract_quantity(query) or 0,
                "minimum_stock": _extract_minimum_stock(query) or 10,
            }
            if payload["price"] <= 0:
                return NLQueryResponse(
                    original_query=query,
                    interpreted_intent="Create product",
                    result_type="product_action",
                    answer="I need a product name, SKU, and a valid price to create a product.",
                    data={"required_fields": ["name", "sku", "price"]},
                    suggestions=["Create product called Laptop Pro 15 with SKU LAPTOP-PRO-15 and price 1299"],
                )

            resp = await client.post(f"{base}/inventory/products", json=payload, headers=headers)
            if resp.status_code in (200, 201):
                product = resp.json()
                return NLQueryResponse(
                    original_query=query,
                    interpreted_intent="Create product",
                    result_type="product_action",
                    answer=f"Created product '{product.get('name')}' with SKU {product.get('sku')}.",
                    data={"product": product},
                    suggestions=["Show product details", "Update product quantity"],
                )
            detail = resp.text
            return NLQueryResponse(
                original_query=query,
                interpreted_intent="Create product",
                result_type="product_action",
                answer=f"I couldn’t create the product. Inventory service returned: {detail}",
                data={"error": detail},
                suggestions=["Try a product with a unique SKU"],
            )

        elif intent == "get_product":
            product_name = _normalize_product_name(_extract_product_name(query))
            search_term = product_name or _extract_sku(query) or ""
            resp = await client.get(f"{base}/inventory/products", params={"search": search_term, "page_size": 10}, headers=headers)
            items = resp.json().get("items", []) if resp.status_code == 200 else []
            if not items:
                return NLQueryResponse(
                    original_query=query,
                    interpreted_intent="View product",
                    result_type="product_action",
                    answer="I couldn’t find a matching product. Try the product name or SKU.",
                    data={"search_term": search_term},
                    suggestions=["Show all products", "List low stock products"],
                )
            product = items[0]
            return NLQueryResponse(
                original_query=query,
                interpreted_intent="View product",
                result_type="product_action",
                answer=f"Product {product.get('name')} is in stock with {product.get('quantity')} units.",
                data={"product": product},
                suggestions=["Update this product", "Delete this product"],
            )

        elif intent == "update_product":
            product_name = _normalize_product_name(_extract_product_name(query))
            search_term = product_name or _extract_sku(query) or ""
            match_resp = await client.get(f"{base}/inventory/products", params={"search": search_term, "page_size": 10}, headers=headers)
            items = match_resp.json().get("items", []) if match_resp.status_code == 200 else []
            if not items:
                return NLQueryResponse(
                    original_query=query,
                    interpreted_intent="Update product",
                    result_type="product_action",
                    answer="I couldn’t find the product you want updated.",
                    data={"search_term": search_term},
                    suggestions=["Show all products", "Update product name and price"],
                )

            product = items[0]
            update_payload = {}
            if _extract_price(query) is not None:
                update_payload["price"] = _extract_price(query)
            if _extract_quantity(query) is not None:
                update_payload["quantity"] = _extract_quantity(query)
            if _extract_minimum_stock(query) is not None:
                update_payload["minimum_stock"] = _extract_minimum_stock(query)
            if _extract_category(query):
                update_payload["category"] = _extract_category(query)
            if product_name and "rename" in query.lower() or "name" in query.lower() and "to" in query.lower():
                new_name = re.search(r"(?:name|rename)\s+(?:to\s+)?([A-Za-z0-9][A-Za-z0-9\s\-&/()]+)", query, re.IGNORECASE)
                if new_name:
                    update_payload["name"] = new_name.group(1).strip()

            if not update_payload:
                return NLQueryResponse(
                    original_query=query,
                    interpreted_intent="Update product",
                    result_type="product_action",
                    answer="I understood the update request, but I need a field such as price, quantity, minimum stock, or category to change.",
                    data={"search_term": search_term},
                    suggestions=["Update product price to 1499", "Set quantity to 25"],
                )

            resp = await client.put(f"{base}/inventory/products/{product.get('id')}", json=update_payload, headers=headers)
            if resp.status_code in (200, 201):
                updated = resp.json()
                return NLQueryResponse(
                    original_query=query,
                    interpreted_intent="Update product",
                    result_type="product_action",
                    answer=f"Updated product '{updated.get('name')}' successfully.",
                    data={"product": updated},
                    suggestions=["Show product details", "List low stock products"],
                )
            return NLQueryResponse(
                original_query=query,
                interpreted_intent="Update product",
                result_type="product_action",
                answer=f"I couldn’t update the product. Inventory service returned: {resp.text}",
                data={"error": resp.text},
                suggestions=["Try a product name or SKU that exactly matches"],
            )

        elif intent == "delete_product":
            product_name = _normalize_product_name(_extract_product_name(query))
            search_term = product_name or _extract_sku(query) or ""
            match_resp = await client.get(f"{base}/inventory/products", params={"search": search_term, "page_size": 10}, headers=headers)
            items = match_resp.json().get("items", []) if match_resp.status_code == 200 else []
            if not items:
                return NLQueryResponse(
                    original_query=query,
                    interpreted_intent="Delete product",
                    result_type="product_action",
                    answer="I couldn’t find the product to delete.",
                    data={"search_term": search_term},
                    suggestions=["Show all products"],
                )

            product = items[0]
            resp = await client.delete(f"{base}/inventory/products/{product.get('id')}", headers=headers)
            if resp.status_code in (200, 204):
                return NLQueryResponse(
                    original_query=query,
                    interpreted_intent="Delete product",
                    result_type="product_action",
                    answer=f"Deleted product '{product.get('name')}'.",
                    data={"deleted_product": product},
                    suggestions=["Show remaining products"],
                )
            return NLQueryResponse(
                original_query=query,
                interpreted_intent="Delete product",
                result_type="product_action",
                answer=f"I couldn’t delete that product. Inventory service returned: {resp.text}",
                data={"error": resp.text},
                suggestions=["Check whether you have admin permissions"],
            )

        elif intent == "count_query":
            resp = await client.get(
                f"{base}/inventory/products", params={"page_size": 1}, headers=headers
            )
            total = resp.json().get("total", 0) if resp.status_code == 200 else "unknown"
            return NLQueryResponse(
                original_query=query,
                interpreted_intent="Count total products in inventory",
                result_type="count",
                answer=f"There are currently {total} active products in inventory.",
                data={"total_products": total},
                suggestions=["What is the total inventory value?", "Show low stock products"],
            )

        elif intent == "value_query":
            items = await self._fetch_all_products(client, headers)
            total_value = sum(i["price"] * i["quantity"] for i in items)
            return NLQueryResponse(
                original_query=query,
                interpreted_intent="Calculate total inventory value",
                result_type="value",
                answer=f"The total inventory value is ${total_value:,.2f}.",
                data={"total_value": round(total_value, 2), "currency": "USD"},
                suggestions=["Which product has the most stock?", "How many products are in stock?"],
            )

        elif intent == "top_stock_query":
            items = await self._fetch_all_products(client, headers)
            if not items:
                answer = "There are no products available to compare right now."
                top_items = []
            else:
                top_items = sorted(items, key=lambda item: item.get("quantity", 0), reverse=True)[:5]
                leader = top_items[0]
                answer = (
                    f"{leader.get('name')} currently has the highest stock with "
                    f"{leader.get('quantity', 0):,} units. Sales history is not connected yet, "
                    "so this is ranked by current stock quantity."
                )
            return NLQueryResponse(
                original_query=query,
                interpreted_intent="Find products with the highest current stock",
                result_type="product_list",
                answer=answer,
                data={"products": top_items},
                suggestions=["Which category has the highest stock?", "Show low stock products"],
            )

        elif intent == "category_query":
            items = await self._fetch_all_products(client, headers)
            cat_counts: dict[str, int] = {}
            for item in items:
                cat = item.get("category") or "Uncategorized"
                cat_counts[cat] = cat_counts.get(cat, 0) + item.get("quantity", 0)

            if cat_counts:
                top_cat = max(cat_counts, key=lambda k: cat_counts[k])
                answer = (
                    f"The category with the highest stock is '{top_cat}' "
                    f"with {cat_counts[top_cat]:,} units."
                )
            else:
                answer = "No category data available."

            return NLQueryResponse(
                original_query=query,
                interpreted_intent="Find category with highest stock",
                result_type="category_stats",
                answer=answer,
                data={"categories": cat_counts},
                suggestions=["Show products in " + (top_cat if cat_counts else "Electronics")],
            )

        else:
            return NLQueryResponse(
                original_query=query,
                interpreted_intent="General product search",
                result_type="unknown",
                answer=(
                    "I understood your question but couldn't map it to a specific inventory query. "
                    "Try asking: 'Show low stock products', 'How many products?', or 'Total inventory value?'"
                ),
                data=None,
                suggestions=[
                    "Show low stock products",
                    "How many products are in inventory?",
                    "What is the total inventory value?",
                    "Which category has the highest stock?",
                    "Which product is selling the most?",
                    "Which products need restocking?",
                ],
            )

    async def _fetch_all_products(self, client: httpx.AsyncClient, headers: dict) -> list[dict]:
        """Fetch the complete catalog using the inventory API page limit."""
        items = []
        page = 1
        total_pages = 1
        while page <= total_pages:
            response = await client.get(
                f"{settings.inventory_service_url}/inventory/products",
                params={"page": page, "page_size": 100},
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
            items.extend(payload.get("items", []))
            total_pages = payload.get("total_pages", 1)
            page += 1
        return items

    @staticmethod
    def _fallback_response(query: str, intent: str) -> NLQueryResponse:
        return NLQueryResponse(
            original_query=query,
            interpreted_intent=intent.replace("_", " ").title(),
            result_type="unknown",
            answer="The inventory service is currently unavailable. Please try again shortly.",
            suggestions=["Show low stock products", "How many products are in inventory?"],
        )
