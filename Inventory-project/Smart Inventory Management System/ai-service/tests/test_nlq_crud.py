from app.services.nlq_service import _classify_intent


def test_classify_create_product_intent():
    intent = _classify_intent("create a new product called Laptop Pro 15 with sku LAPTOP-PRO-15")
    assert intent == "create_product"


def test_classify_delete_product_intent():
    intent = _classify_intent("delete product called Laptop Pro 15")
    assert intent == "delete_product"


def test_classify_update_product_intent():
    intent = _classify_intent("update product Laptop Pro 15 price to 1299")
    assert intent == "update_product"
