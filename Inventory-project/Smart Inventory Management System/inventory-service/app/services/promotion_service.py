"""Offer lifecycle, targeting, and dynamic pricing rules."""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.product import Product
from app.models.promotion import Campaign, Offer
from app.models.subcategory import Subcategory
from app.models.sales_history import SeasonalEvent
from app.schemas.promotion import (
    CampaignCreateRequest,
    CampaignApplyDiscountRequest,
    CampaignResponse,
    OfferCreateRequest,
    OfferResponse,
    CampaignUpdateRequest,
    OfferUpdateRequest,
    PricingResponse,
)


class PromotionService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _money(value: Decimal | float) -> float:
        return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _status(item, now: datetime) -> str:
        if not item.is_enabled:
            return "disabled"
        if now < item.starts_at:
            return "scheduled"
        if now > item.ends_at:
            return "expired"
        return "active"

    def _campaign_response(self, campaign: Campaign) -> CampaignResponse:
        return CampaignResponse(
            id=campaign.id,
            name=campaign.name,
            description=campaign.description,
            banner_title=campaign.banner_title,
            starts_at=campaign.starts_at,
            ends_at=campaign.ends_at,
            is_enabled=campaign.is_enabled,
            status=campaign.effective_status,
            festival_event_id=campaign.festival_event_id,
            minimum_discount=float(campaign.minimum_discount) if campaign.minimum_discount is not None else None,
            maximum_discount=float(campaign.maximum_discount) if campaign.maximum_discount is not None else None,
            selected_discount=float(campaign.selected_discount) if campaign.selected_discount is not None else None,
        )

    def list_campaigns(self) -> list[CampaignResponse]:
        return [self._campaign_response(item) for item in self.db.query(Campaign).order_by(Campaign.starts_at.desc()).all()]

    def create_campaign(self, data: CampaignCreateRequest) -> CampaignResponse:
        if self.db.query(Campaign).filter(Campaign.name == data.name.strip()).first():
            raise ValueError(f"Campaign '{data.name}' already exists")
        if data.festival_event_id and not self.db.get(SeasonalEvent, data.festival_event_id):
            raise ValueError(f"Festival event {data.festival_event_id} not found")
        campaign = Campaign(**data.model_dump())
        campaign.name = campaign.name.strip()
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return self._campaign_response(campaign)

    def update_campaign(self, campaign_id: int, data: CampaignUpdateRequest) -> CampaignResponse:
        campaign = self.db.get(Campaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        updates = data.model_dump(exclude_none=True)
        if updates.get("festival_event_id") and not self.db.get(SeasonalEvent, updates["festival_event_id"]):
            raise ValueError(f"Festival event {updates['festival_event_id']} not found")
        if "name" in updates:
            updates["name"] = updates["name"].strip()
        for field, value in updates.items():
            setattr(campaign, field, value)
        if campaign.ends_at <= campaign.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if campaign.minimum_discount is not None and campaign.maximum_discount is not None:
            if campaign.minimum_discount > campaign.maximum_discount:
                raise ValueError("minimum_discount must not exceed maximum_discount")
            if campaign.selected_discount is not None and not campaign.minimum_discount <= campaign.selected_discount <= campaign.maximum_discount:
                raise ValueError("selected_discount must stay within the campaign range")
        self.db.commit()
        self.db.refresh(campaign)
        return self._campaign_response(campaign)

    def apply_campaign_discount(self, campaign_id: int, data: CampaignApplyDiscountRequest) -> OfferResponse:
        campaign = self.db.get(Campaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        if campaign.minimum_discount is None or campaign.maximum_discount is None:
            raise ValueError("Configure a discount range before applying a campaign offer")
        if not campaign.minimum_discount <= data.selected_discount <= campaign.maximum_discount:
            raise ValueError("Selected discount must stay within the manager-configured campaign range")
        if self.db.query(Offer.id).filter(Offer.campaign_id == campaign.id, Offer.is_enabled.is_(True)).first():
            raise ValueError("This campaign already has an enabled offer")

        target_product_ids: set[int] = set()
        if data.product_ids:
            product_rows = self.db.query(Product.id).filter(
                Product.id.in_(data.product_ids), Product.is_active.is_(True)
            ).all()
            target_product_ids.update(row.id for row in product_rows)
            if len(target_product_ids) < len(data.product_ids):
                raise ValueError("One or more product targets do not exist")
        if data.category_ids:
            category_rows = self.db.query(Category.id).filter(Category.id.in_(data.category_ids)).all()
            if len(category_rows) != len(data.category_ids):
                raise ValueError("One or more category targets do not exist")
            category_products = self.db.query(Product.id).join(Product.subcategory).filter(
                Product.is_active.is_(True), Subcategory.category_id.in_(data.category_ids)
            ).all()
            target_product_ids.update(row.id for row in category_products)
        if data.subcategory_ids:
            subcategory_rows = self.db.query(Subcategory.id).filter(Subcategory.id.in_(data.subcategory_ids)).all()
            if len(subcategory_rows) != len(data.subcategory_ids):
                raise ValueError("One or more subcategory targets do not exist")
            subcategory_products = self.db.query(Product.id).filter(
                Product.is_active.is_(True), Product.subcategory_id.in_(data.subcategory_ids)
            ).all()
            target_product_ids.update(row.id for row in subcategory_products)
        if not target_product_ids:
            raise ValueError("Discount targets do not include any active products")
        targeted_products = self.db.query(Product).filter(Product.id.in_(target_product_ids)).all()
        if data.product_ids and len({p.id for p in targeted_products} & set(data.product_ids)) != len(data.product_ids):
            raise ValueError("One or more product targets do not exist")
        for product in targeted_products:
            if product.unit_cost is not None and product.price * (1 - data.selected_discount / 100) < product.unit_cost:
                raise ValueError(f"Discount would sell {product.name} below its recorded unit cost")

        now = datetime.utcnow()
        starts_at = max(campaign.starts_at, now)
        if campaign.ends_at <= starts_at:
            raise ValueError("Campaign end date must be in the future to apply a discount")
        offer_name = f"{campaign.name[:140]} - festive offer"
        offer = self.create_offer(OfferCreateRequest(
            name=offer_name,
            description=f"Manager-confirmed {data.selected_discount}% offer for {campaign.name}",
            campaign_id=campaign.id,
            discount_type="percentage",
            discount_value=data.selected_discount,
            starts_at=starts_at,
            ends_at=campaign.ends_at,
            minimum_purchase=0,
            priority=100,
            is_enabled=True,
            product_ids=data.product_ids,
            category_ids=data.category_ids,
            subcategory_ids=data.subcategory_ids,
        ))
        campaign.selected_discount = data.selected_discount
        campaign.is_enabled = True
        self.db.commit()
        return offer

    def delete_campaign(self, campaign_id: int) -> None:
        campaign = self.db.get(Campaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        if campaign.offers:
            raise ValueError("Campaigns with offers cannot be deleted; disable the campaign instead")
        self.db.delete(campaign)
        self.db.commit()

    def _offer_response(self, offer: Offer) -> OfferResponse:
        return OfferResponse(
            id=offer.id,
            name=offer.name,
            description=offer.description,
            campaign_id=offer.campaign_id,
            discount_type=offer.discount_type,
            discount_value=self._money(offer.discount_value),
            starts_at=offer.starts_at,
            ends_at=offer.ends_at,
            minimum_purchase=self._money(offer.minimum_purchase),
            maximum_discount=self._money(offer.maximum_discount) if offer.maximum_discount is not None else None,
            priority=offer.priority,
            is_enabled=offer.is_enabled,
            status=offer.effective_status,
            product_ids=[product.id for product in offer.products],
            category_ids=[category.id for category in offer.categories],
            subcategory_ids=[subcategory.id for subcategory in offer.subcategories],
        )

    def list_offers(self) -> list[OfferResponse]:
        offers = (
            self.db.query(Offer)
            .options(joinedload(Offer.products), joinedload(Offer.categories), joinedload(Offer.subcategories))
            .order_by(Offer.priority.desc(), Offer.starts_at.desc())
            .all()
        )
        return [self._offer_response(item) for item in offers]

    def create_offer(self, data: OfferCreateRequest) -> OfferResponse:
        if self.db.query(Offer).filter(Offer.name == data.name.strip()).first():
            raise ValueError(f"Offer '{data.name}' already exists")
        if data.campaign_id and not self.db.get(Campaign, data.campaign_id):
            raise ValueError(f"Campaign {data.campaign_id} not found")
        products = self.db.query(Product).filter(Product.id.in_(data.product_ids), Product.is_active.is_(True)).all() if data.product_ids else []
        categories = self.db.query(Category).filter(Category.id.in_(data.category_ids)).all() if data.category_ids else []
        subcategories = self.db.query(Subcategory).filter(Subcategory.id.in_(data.subcategory_ids)).all() if data.subcategory_ids else []
        if len(products) != len(data.product_ids) or len(categories) != len(data.category_ids) or len(subcategories) != len(data.subcategory_ids):
            raise ValueError("One or more offer targets do not exist")
        offer = Offer(**data.model_dump(exclude={"product_ids", "category_ids", "subcategory_ids"}))
        offer.name = offer.name.strip()
        offer.products = products
        offer.categories = categories
        offer.subcategories = subcategories
        self.db.add(offer)
        self.db.commit()
        self.db.refresh(offer)
        return self._offer_response(offer)

    def update_offer(self, offer_id: int, data: OfferUpdateRequest) -> OfferResponse:
        offer = self.db.get(Offer, offer_id)
        if not offer:
            raise ValueError(f"Offer {offer_id} not found")
        updates = data.model_dump(exclude_none=True)
        product_ids = updates.pop("product_ids", None)
        category_ids = updates.pop("category_ids", None)
        subcategory_ids = updates.pop("subcategory_ids", None)
        if "campaign_id" in updates and not self.db.get(Campaign, updates["campaign_id"]):
            raise ValueError(f"Campaign {updates['campaign_id']} not found")
        if product_ids is not None:
            products = self.db.query(Product).filter(Product.id.in_(product_ids), Product.is_active.is_(True)).all()
            if len(products) != len(product_ids):
                raise ValueError("One or more product targets do not exist")
            offer.products = products
        if category_ids is not None:
            categories = self.db.query(Category).filter(Category.id.in_(category_ids)).all()
            if len(categories) != len(category_ids):
                raise ValueError("One or more category targets do not exist")
            offer.categories = categories
        if subcategory_ids is not None:
            subcategories = self.db.query(Subcategory).filter(Subcategory.id.in_(subcategory_ids)).all()
            if len(subcategories) != len(subcategory_ids):
                raise ValueError("One or more subcategory targets do not exist")
            offer.subcategories = subcategories
        for field, value in updates.items():
            setattr(offer, field, value.strip() if field == "name" else value)
        if offer.discount_type == "percentage" and offer.discount_value > 100:
            raise ValueError("percentage discount cannot exceed 100")
        if offer.ends_at <= offer.starts_at:
            raise ValueError("ends_at must be after starts_at")
        self.db.commit()
        self.db.refresh(offer)
        return self._offer_response(offer)

    def disable_offer(self, offer_id: int) -> OfferResponse:
        offer = self.db.get(Offer, offer_id)
        if not offer:
            raise ValueError(f"Offer {offer_id} not found")
        offer.is_enabled = False
        self.db.commit()
        self.db.refresh(offer)
        return self._offer_response(offer)

    def delete_offer(self, offer_id: int) -> None:
        offer = self.db.get(Offer, offer_id)
        if not offer:
            raise ValueError(f"Offer {offer_id} not found")
        self.db.delete(offer)
        self.db.commit()

    def _applies(self, offer: Offer, product: Product) -> bool:
        has_targets = bool(offer.products or offer.categories or offer.subcategories)
        if not has_targets:
            return True
        return (
            product.id in {item.id for item in offer.products}
            or (product.category_id is not None and product.category_id in {item.id for item in offer.categories})
            or (product.subcategory_id is not None and product.subcategory_id in {item.id for item in offer.subcategories})
        )

    def pricing(self, product_id: int, purchase_amount: float | None = None) -> PricingResponse:
        product = (
            self.db.query(Product)
            .options(joinedload(Product.subcategory))
            .filter(Product.id == product_id, Product.is_active.is_(True))
            .first()
        )
        if not product:
            raise ValueError(f"Product {product_id} not found")
        now = datetime.utcnow()
        amount = Decimal(str(purchase_amount if purchase_amount is not None else product.price))
        candidates = (
            self.db.query(Offer)
            .options(joinedload(Offer.products), joinedload(Offer.categories), joinedload(Offer.subcategories), joinedload(Offer.campaign))
            .filter(Offer.is_enabled.is_(True), Offer.starts_at <= now, Offer.ends_at >= now)
            .order_by(Offer.priority.desc(), Offer.id.asc())
            .all()
        )
        chosen = next(
            (offer for offer in candidates if self._applies(offer, product) and (not offer.campaign or offer.campaign.effective_status == "active") and amount >= Decimal(str(offer.minimum_purchase))),
            None,
        )
        if not chosen:
            return PricingResponse(product_id=product.id, product_name=product.name, original_price=self._money(product.price), offer_id=None, offer_name=None, discount_type=None, discount_value=None, discount_amount=0, final_price=self._money(product.price), offer_status=None)
        if chosen.discount_type == "percentage":
            discount = amount * Decimal(str(chosen.discount_value)) / Decimal("100")
        else:
            discount = Decimal(str(chosen.discount_value))
        if chosen.maximum_discount is not None:
            discount = min(discount, Decimal(str(chosen.maximum_discount)))
        discount = min(discount, amount)
        final = max(Decimal("0"), amount - discount)
        return PricingResponse(product_id=product.id, product_name=product.name, original_price=self._money(product.price), offer_id=chosen.id, offer_name=chosen.name, discount_type=chosen.discount_type, discount_value=self._money(chosen.discount_value), discount_amount=self._money(discount), final_price=self._money(final), offer_status="active")
