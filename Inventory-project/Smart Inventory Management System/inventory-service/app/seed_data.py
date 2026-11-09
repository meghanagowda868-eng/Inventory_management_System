"""Seed data for the electronics catalog and warehouses.

This script is intentionally safe to run repeatedly and inserts only the required
catalog baseline if it does not already exist.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.category import Category
from app.models.inventory import InventoryItem
from app.models.product import Product
from app.models.subcategory import Subcategory
from app.models.warehouse import Warehouse
from app.models.sales_history import SalesHistory, SeasonalEvent
from app.models.promotion import Campaign, Offer


ELECTRONICS_CATALOG = {
    "Computers & Laptops": ["Laptops", "Desktops", "Monitors", "Keyboards", "Mice", "Webcams", "Computer Accessories"],
    "Mobile & Tablets": ["Smartphones", "Tablets", "Mobile Accessories", "Chargers", "Power Banks", "Cases & Covers"],
    "Audio": ["Headphones", "Earphones", "Bluetooth Speakers", "Soundbars", "Microphones"],
    "TV & Home Entertainment": ["Smart TVs", "Streaming Devices", "Projectors", "Gaming Consoles", "TV Accessories"],
    "Cameras": ["DSLR Cameras", "Mirrorless Cameras", "Action Cameras", "Security Cameras", "Camera Accessories"],
    "Networking": ["Wi-Fi Routers", "Modems", "Network Switches", "Wi-Fi Extenders", "Network Accessories"],
    "Storage": ["SSDs", "HDDs", "USB Flash Drives", "Memory Cards", "External Storage"],
    "Computer Components": ["CPUs", "GPUs", "RAM", "Motherboards", "Power Supplies", "Cooling Systems"],
    "Smart Devices": ["Smart Watches", "Smart Home Devices", "Smart Lighting", "Smart Plugs", "IoT Devices"],
    "Printers & Office Electronics": ["Printers", "Scanners", "UPS", "POS Devices"],
    "Gaming": ["Gaming Laptops", "Gaming PCs", "Gaming Monitors", "Controllers", "Gaming Accessories"],
}

BRANDS = ["Apple", "Samsung", "Dell", "HP", "Lenovo", "Logitech", "Sony", "ASUS", "Acer", "TP-Link", "Canon", "Epson"]

WAREHOUSES = [
    {
        "warehouse_code": "WH-BLR-001",
        "name": "Bangalore Central Warehouse",
        "location": "Bengaluru, Karnataka",
        "city": "Bengaluru",
        "state": "Karnataka",
        "status": "ACTIVE",
        "contact_name": "Ravi Menon",
        "contact_phone": "+91-98765-11111",
    },
    {
        "warehouse_code": "WH-MYS-001",
        "name": "Mysore Distribution Center",
        "location": "Mysore, Karnataka",
        "city": "Mysore",
        "state": "Karnataka",
        "status": "ACTIVE",
        "contact_name": "Ananya S",
        "contact_phone": "+91-98765-22222",
    },
    {
        "warehouse_code": "WH-CHE-001",
        "name": "Chennai Electronics Hub",
        "location": "Chennai, Tamil Nadu",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "status": "ACTIVE",
        "contact_name": "Karthik R",
        "contact_phone": "+91-98765-33333",
    },
    {
        "warehouse_code": "WH-HYD-001",
        "name": "Hyderabad Distribution Center",
        "location": "Hyderabad, Telangana",
        "city": "Hyderabad",
        "state": "Telangana",
        "status": "ACTIVE",
        "contact_name": "Meera Rao",
        "contact_phone": "+91-98765-44444",
    },
]

SEASONAL_EVENTS = [
    {"name": "Diwali", "start_date": date(2026, 10, 20), "end_date": date(2026, 11, 8), "keywords": "smartphone,laptop,smart tv,headphone,speaker,smart watch,earphone"},
    {"name": "Christmas", "start_date": date(2026, 12, 15), "end_date": date(2026, 12, 26), "keywords": "smartphone,gaming,headphone,smart watch,speaker,camera"},
    {"name": "New Year", "start_date": date(2026, 12, 27), "end_date": date(2027, 1, 3), "keywords": "smart tv,speaker,smartphone,smart watch,headphone"},
    {"name": "Back-to-School", "start_date": date(2027, 5, 15), "end_date": date(2027, 7, 15), "keywords": "laptop,tablet,keyboard,mouse,headphone,usb,accessories"},
    {"name": "Summer", "start_date": date(2027, 4, 1), "end_date": date(2027, 5, 31), "keywords": "speaker,power bank,smart tv"},
]

FESTIVE_CAMPAIGNS = [
    {
        "name": "Diwali Mega Sale",
        "description": "A festive electronics sale across personal technology and home entertainment.",
        "banner_title": "Light up your Diwali with smarter technology",
        "starts_at": datetime(2026, 10, 1),
        "ends_at": datetime(2026, 11, 1),
        "offers": [
            {"name": "Diwali Personal Tech 20% Off", "discount_type": "percentage", "discount_value": 20, "minimum_purchase": 1000, "maximum_discount": 5000, "priority": 90, "categories": ["Computers & Laptops", "Mobile & Tablets"]},
            {"name": "Diwali Audio Save 1500", "discount_type": "fixed", "discount_value": 1500, "minimum_purchase": 8000, "maximum_discount": None, "priority": 80, "subcategories": ["Headphones", "Bluetooth Speakers"]},
        ],
    },
    {
        "name": "Christmas Tech Fest",
        "description": "Gift-ready offers on audio, cameras, gaming, and smart devices.",
        "banner_title": "Give the gift of great tech",
        "starts_at": datetime(2026, 12, 1),
        "ends_at": datetime(2026, 12, 26),
        "offers": [
            {"name": "Christmas Gadgets 15% Off", "discount_type": "percentage", "discount_value": 15, "minimum_purchase": 2500, "maximum_discount": 3500, "priority": 75, "categories": ["Audio", "Cameras", "Smart Devices"]},
            {"name": "Christmas Gaming Gift Save 2500", "discount_type": "fixed", "discount_value": 2500, "minimum_purchase": 15000, "maximum_discount": None, "priority": 70, "categories": ["Gaming"]},
        ],
    },
    {
        "name": "New Year Electronics Sale",
        "description": "Start the year with upgrades for entertainment and connected living.",
        "banner_title": "New year, new tech",
        "starts_at": datetime(2026, 12, 20),
        "ends_at": datetime(2027, 1, 5),
        "offers": [
            {"name": "New Year Home Entertainment 18% Off", "discount_type": "percentage", "discount_value": 18, "minimum_purchase": 10000, "maximum_discount": 7500, "priority": 65, "categories": ["TV & Home Entertainment", "Audio"]},
            {"name": "New Year Smart Tech Save 2000", "discount_type": "fixed", "discount_value": 2000, "minimum_purchase": 12000, "maximum_discount": None, "priority": 60, "categories": ["Smart Devices", "Mobile & Tablets"]},
        ],
    },
    {
        "name": "Back to College Sale",
        "description": "Study and campus essentials for students returning to college.",
        "banner_title": "Gear up for your next semester",
        "starts_at": datetime(2027, 5, 15),
        "ends_at": datetime(2027, 7, 15),
        "offers": [
            {"name": "Back to College Computing 12% Off", "discount_type": "percentage", "discount_value": 12, "minimum_purchase": 20000, "maximum_discount": 6000, "priority": 55, "categories": ["Computers & Laptops", "Storage"]},
            {"name": "Student Accessories Save 750", "discount_type": "fixed", "discount_value": 750, "minimum_purchase": 3000, "maximum_discount": None, "priority": 50, "subcategories": ["Keyboards", "Mice", "Computer Accessories"]},
        ],
    },
    {
        "name": "Summer Tech Sale",
        "description": "Portable entertainment and connected home offers for summer.",
        "banner_title": "Make summer more connected",
        "starts_at": datetime(2027, 4, 1),
        "ends_at": datetime(2027, 5, 31),
        "offers": [
            {"name": "Summer Portable Tech 16% Off", "discount_type": "percentage", "discount_value": 16, "minimum_purchase": 2500, "maximum_discount": 4000, "priority": 45, "subcategories": ["Power Banks", "Bluetooth Speakers", "Action Cameras"]},
            {"name": "Summer Smart TV Save 3000", "discount_type": "fixed", "discount_value": 3000, "minimum_purchase": 30000, "maximum_discount": None, "priority": 40, "subcategories": ["Smart TVs"]},
        ],
    },
    {
        "name": "Annual Store Anniversary Celebration",
        "description": "Our annual celebration with special savings across the electronics catalog.",
        "banner_title": "Celebrating another year of smart shopping",
        "starts_at": datetime(2026, 9, 1),
        "ends_at": datetime(2026, 9, 30),
        "offers": [
            {"name": "Anniversary Storewide 10% Off", "discount_type": "percentage", "discount_value": 10, "minimum_purchase": 5000, "maximum_discount": 3000, "priority": 35},
            {"name": "Anniversary Premium Tech Save 5000", "discount_type": "fixed", "discount_value": 5000, "minimum_purchase": 50000, "maximum_discount": None, "priority": 30, "categories": ["Computers & Laptops", "TV & Home Entertainment"]},
        ],
    },
]

PRODUCTS = [
    {
        "subcategory": "Laptops",
        "name": "Dell Inspiron 15 3530",
        "brand": "Dell",
        "model_number": "Inspiron 15 3530",
        "sku": "ELEC-LAP-DELL-001",
        "price": 65499,
        "minimum_stock": 10,
        "quantity": 42,
    },
    {
        "subcategory": "Laptops",
        "name": "Dell XPS 13 Plus",
        "brand": "Dell",
        "model_number": "XPS 13 Plus",
        "sku": "ELEC-LAP-DELL-002",
        "price": 124999,
        "minimum_stock": 8,
        "quantity": 18,
    },
    {
        "subcategory": "Laptops",
        "name": "HP Pavilion 14",
        "brand": "HP",
        "model_number": "Pavilion 14",
        "sku": "ELEC-LAP-HP-003",
        "price": 72999,
        "minimum_stock": 10,
        "quantity": 30,
    },
    {
        "subcategory": "Laptops",
        "name": "HP Envy x360 14",
        "brand": "HP",
        "model_number": "Envy x360 14",
        "sku": "ELEC-LAP-HP-004",
        "price": 98999,
        "minimum_stock": 7,
        "quantity": 14,
    },
    {
        "subcategory": "Laptops",
        "name": "Lenovo IdeaPad Slim 5",
        "brand": "Lenovo",
        "model_number": "IdeaPad Slim 5",
        "sku": "ELEC-LAP-LEN-005",
        "price": 68999,
        "minimum_stock": 9,
        "quantity": 24,
    },
    {
        "subcategory": "Laptops",
        "name": "Lenovo ThinkPad E14",
        "brand": "Lenovo",
        "model_number": "ThinkPad E14",
        "sku": "ELEC-LAP-LEN-006",
        "price": 91899,
        "minimum_stock": 10,
        "quantity": 12,
    },
    {
        "subcategory": "Laptops",
        "name": "ASUS Vivobook 15",
        "brand": "ASUS",
        "model_number": "Vivobook 15",
        "sku": "ELEC-LAP-ASU-007",
        "price": 59999,
        "minimum_stock": 12,
        "quantity": 29,
    },
    {
        "subcategory": "Laptops",
        "name": "ASUS ROG Strix G16",
        "brand": "ASUS",
        "model_number": "ROG Strix G16",
        "sku": "ELEC-LAP-ASU-008",
        "price": 159999,
        "minimum_stock": 6,
        "quantity": 8,
    },
    {
        "subcategory": "Laptops",
        "name": "Acer Aspire 5",
        "brand": "Acer",
        "model_number": "Aspire 5",
        "sku": "ELEC-LAP-ACE-009",
        "price": 54999,
        "minimum_stock": 11,
        "quantity": 21,
    },
    {
        "subcategory": "Laptops",
        "name": "Acer Nitro V",
        "brand": "Acer",
        "model_number": "Nitro V",
        "sku": "ELEC-LAP-ACE-010",
        "price": 114999,
        "minimum_stock": 7,
        "quantity": 11,
    },
    {
        "subcategory": "Desktop Computers",
        "name": "Dell OptiPlex Tower 7020",
        "brand": "Dell",
        "model_number": "OptiPlex 7020",
        "sku": "ELEC-DES-DLL-011",
        "price": 76999,
        "minimum_stock": 8,
        "quantity": 16,
    },
    {
        "subcategory": "Desktop Computers",
        "name": "HP ProDesk 400 G9",
        "brand": "HP",
        "model_number": "ProDesk 400 G9",
        "sku": "ELEC-DES-HP-012",
        "price": 71999,
        "minimum_stock": 8,
        "quantity": 18,
    },
    {
        "subcategory": "Desktop Computers",
        "name": "Lenovo ThinkCentre M90q",
        "brand": "Lenovo",
        "model_number": "ThinkCentre M90q",
        "sku": "ELEC-DES-LEN-013",
        "price": 83999,
        "minimum_stock": 7,
        "quantity": 12,
    },
    {
        "subcategory": "Desktop Computers",
        "name": "ASUS ExpertCenter D7",
        "brand": "ASUS",
        "model_number": "ExpertCenter D7",
        "sku": "ELEC-DES-ASU-014",
        "price": 74999,
        "minimum_stock": 8,
        "quantity": 10,
    },
    {
        "subcategory": "Desktop Computers",
        "name": "Acer Veriton M200",
        "brand": "Acer",
        "model_number": "Veriton M200",
        "sku": "ELEC-DES-ACE-015",
        "price": 68999,
        "minimum_stock": 10,
        "quantity": 20,
    },
    {
        "subcategory": "Monitors",
        "name": "LG UltraGear 27GR83Q",
        "brand": "LG",
        "model_number": "UltraGear 27GR83Q",
        "sku": "ELEC-MON-LG-016",
        "price": 46999,
        "minimum_stock": 12,
        "quantity": 26,
    },
    {
        "subcategory": "Monitors",
        "name": "Samsung Odyssey G5",
        "brand": "Samsung",
        "model_number": "Odyssey G5",
        "sku": "ELEC-MON-SAM-017",
        "price": 42999,
        "minimum_stock": 12,
        "quantity": 22,
    },
    {
        "subcategory": "Monitors",
        "name": "Dell UltraSharp U2723QE",
        "brand": "Dell",
        "model_number": "UltraSharp U2723QE",
        "sku": "ELEC-MON-DEL-018",
        "price": 52999,
        "minimum_stock": 10,
        "quantity": 19,
    },
    {
        "subcategory": "Monitors",
        "name": "ASUS ProArt PA278CV",
        "brand": "ASUS",
        "model_number": "ProArt PA278CV",
        "sku": "ELEC-MON-ASU-019",
        "price": 49999,
        "minimum_stock": 9,
        "quantity": 17,
    },
    {
        "subcategory": "Mobile Phones",
        "name": "Samsung Galaxy A56",
        "brand": "Samsung",
        "model_number": "Galaxy A56",
        "sku": "ELEC-MOB-SAM-020",
        "price": 46999,
        "minimum_stock": 15,
        "quantity": 28,
    },
    {
        "subcategory": "Mobile Phones",
        "name": "Samsung Galaxy S25",
        "brand": "Samsung",
        "model_number": "Galaxy S25",
        "sku": "ELEC-MOB-SAM-021",
        "price": 79999,
        "minimum_stock": 10,
        "quantity": 18,
    },
    {
        "subcategory": "Mobile Phones",
        "name": "Apple iPhone 16",
        "brand": "Apple",
        "model_number": "iPhone 16",
        "sku": "ELEC-MOB-APP-022",
        "price": 79999,
        "minimum_stock": 12,
        "quantity": 24,
    },
    {
        "subcategory": "Mobile Phones",
        "name": "Apple iPhone 16 Pro",
        "brand": "Apple",
        "model_number": "iPhone 16 Pro",
        "sku": "ELEC-MOB-APP-023",
        "price": 119999,
        "minimum_stock": 7,
        "quantity": 13,
    },
    {
        "subcategory": "Mobile Phones",
        "name": "Google Pixel 9",
        "brand": "Google",
        "model_number": "Pixel 9",
        "sku": "ELEC-MOB-GOO-024",
        "price": 69999,
        "minimum_stock": 12,
        "quantity": 20,
    },
    {
        "subcategory": "Tablets",
        "name": "Apple iPad Air",
        "brand": "Apple",
        "model_number": "iPad Air",
        "sku": "ELEC-TAB-APP-025",
        "price": 59999,
        "minimum_stock": 8,
        "quantity": 16,
    },
    {
        "subcategory": "Tablets",
        "name": "Samsung Galaxy Tab S10",
        "brand": "Samsung",
        "model_number": "Galaxy Tab S10",
        "sku": "ELEC-TAB-SAM-026",
        "price": 64999,
        "minimum_stock": 8,
        "quantity": 15,
    },
    {
        "subcategory": "Audio & Headphones",
        "name": "Sony WH-1000XM5",
        "brand": "Sony",
        "model_number": "WH-1000XM5",
        "sku": "ELEC-AUD-SON-027",
        "price": 29999,
        "minimum_stock": 14,
        "quantity": 33,
    },
    {
        "subcategory": "Audio & Headphones",
        "name": "Bose QuietComfort Ultra",
        "brand": "Bose",
        "model_number": "QuietComfort Ultra",
        "sku": "ELEC-AUD-BOS-028",
        "price": 28999,
        "minimum_stock": 12,
        "quantity": 25,
    },
    {
        "subcategory": "Networking Devices",
        "name": "TP-Link Archer AX55",
        "brand": "TP-Link",
        "model_number": "Archer AX55",
        "sku": "ELEC-NET-TP-029",
        "price": 9999,
        "minimum_stock": 15,
        "quantity": 22,
    },
    {
        "subcategory": "Storage Devices",
        "name": "Samsung 990 Pro 1TB",
        "brand": "Samsung",
        "model_number": "990 Pro 1TB",
        "sku": "ELEC-STR-SAM-030",
        "price": 10999,
        "minimum_stock": 20,
        "quantity": 45,
    },
]


def seed_catalog(db: Session) -> dict:
    sub_map: dict[tuple[str, str], Subcategory] = {}
    for category_name, subcategories in ELECTRONICS_CATALOG.items():
        category = db.query(Category).filter(Category.name == category_name).first()
        if not category:
            category = Category(name=category_name, description=f"{category_name} electronics catalog")
            db.add(category)
            db.flush()
        for subcategory_name in subcategories:
            subcategory = (
                db.query(Subcategory)
                .filter(Subcategory.category_id == category.id, Subcategory.name == subcategory_name)
                .first()
            )
            if not subcategory:
                subcategory = Subcategory(
                    category_id=category.id,
                    name=subcategory_name,
                    description=f"{subcategory_name} products and accessories.",
                )
                db.add(subcategory)
                db.flush()
            sub_map[(category_name, subcategory_name)] = subcategory

    if db.query(Warehouse).count() == 0:
        db.add_all(Warehouse(**warehouse) for warehouse in WAREHOUSES)
        db.flush()
    warehouse_rows = db.query(Warehouse).order_by(Warehouse.id).all()

    created = 0
    for category_index, (category_name, subcategories) in enumerate(ELECTRONICS_CATALOG.items(), start=1):
        for subcategory_index, subcategory_name in enumerate(subcategories, start=1):
            subcategory = sub_map[(category_name, subcategory_name)]
            for variant in range(1, 5):
                sku = f"ELEC-{category_index:02d}-{subcategory_index:02d}-{variant:02d}"
                if db.query(Product).filter(Product.sku == sku).first():
                    continue
                brand = BRANDS[(category_index + subcategory_index + variant) % len(BRANDS)]
                quantity = 12 + ((category_index * 13 + subcategory_index * 7 + variant * 5) % 80)
                product = Product(
                    subcategory_id=subcategory.id,
                    category=category_name,
                    name=f"{brand} {subcategory_name} Series {variant}",
                    brand=brand,
                    model_number=f"{subcategory_name[:3].upper()}-{category_index:02d}{subcategory_index:02d}{variant:02d}",
                    sku=sku,
                    description=f"{brand} {subcategory_name} electronics product.",
                    price=float(999 + ((category_index * 1875 + subcategory_index * 925 + variant * 310) % 145000)),
                    quantity=quantity,
                    minimum_stock=10 + ((subcategory_index + variant) % 12),
                    image_url="/api/v1/inventory/uploads/electronics-placeholder.svg",
                    status="active",
                    is_active=True,
                )
                db.add(product)
                db.flush()
                for warehouse_index, warehouse in enumerate(warehouse_rows):
                    db.add(InventoryItem(
                        product_id=product.id,
                        warehouse_id=warehouse.id,
                        quantity=max(0, quantity // len(warehouse_rows) + (1 if warehouse_index == 0 else 0)),
                    ))
                created += 1

    for event_data in SEASONAL_EVENTS:
        event = db.query(SeasonalEvent).filter(SeasonalEvent.name == event_data["name"]).first()
        if not event:
            db.add(SeasonalEvent(**event_data))
    db.flush()

    # Clearly labeled demo history gives the rule-based recommender persisted inputs.
    for product in db.query(Product).filter(Product.sku.like("ELEC-%")).all():
        for days_ago, quantity in ((75, 2), (45, 3), (20, 5)):
            sale_date = date.today() - timedelta(days=days_ago)
            exists = db.query(SalesHistory).filter(
                SalesHistory.product_id == product.id,
                SalesHistory.sale_date == sale_date,
                SalesHistory.event_name == "Seeded sample history",
            ).first()
            if not exists:
                db.add(SalesHistory(
                    product_id=product.id,
                    sale_date=sale_date,
                    quantity=quantity,
                    unit_price=product.price,
                    event_name="Seeded sample history",
                ))

    category_map = {category.name: category for category in db.query(Category).all()}
    subcategory_map = {subcategory.name: subcategory for subcategory in db.query(Subcategory).all()}
    campaigns_created = 0
    offers_created = 0
    for campaign_data in FESTIVE_CAMPAIGNS:
        campaign = db.query(Campaign).filter(Campaign.name == campaign_data["name"]).first()
        if not campaign:
            campaign = Campaign(
                name=campaign_data["name"],
                description=campaign_data["description"],
                banner_title=campaign_data["banner_title"],
                starts_at=campaign_data["starts_at"],
                ends_at=campaign_data["ends_at"],
                is_enabled=True,
            )
            db.add(campaign)
            db.flush()
            campaigns_created += 1

        for offer_data in campaign_data["offers"]:
            if db.query(Offer).filter(Offer.name == offer_data["name"]).first():
                continue
            offer = Offer(
                campaign_id=campaign.id,
                name=offer_data["name"],
                description=f"{offer_data['name']} offer for {campaign.name}.",
                discount_type=offer_data["discount_type"],
                discount_value=offer_data["discount_value"],
                starts_at=campaign.starts_at,
                ends_at=campaign.ends_at,
                minimum_purchase=offer_data["minimum_purchase"],
                maximum_discount=offer_data["maximum_discount"],
                priority=offer_data["priority"],
                is_enabled=True,
            )
            offer.categories = [category_map[name] for name in offer_data.get("categories", []) if name in category_map]
            offer.subcategories = [subcategory_map[name] for name in offer_data.get("subcategories", []) if name in subcategory_map]
            db.add(offer)
            offers_created += 1

    db.commit()
    return {
        "categories_created": len(ELECTRONICS_CATALOG),
        "products_created": created,
        "warehouses_created": db.query(Warehouse).count(),
        "seasonal_events": db.query(SeasonalEvent).count(),
        "sales_history_rows": db.query(SalesHistory).count(),
        "campaigns": db.query(Campaign).count(),
        "offers": db.query(Offer).count(),
        "campaigns_created": campaigns_created,
        "offers_created": offers_created,
    }


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print(seed_catalog(db))
    finally:
        db.close()
