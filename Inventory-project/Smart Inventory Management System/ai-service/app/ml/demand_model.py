"""
Demand prediction ML model using scikit-learn RandomForestClassifier.
Trained once on startup, cached as a singleton.
"""
from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from app.ml.mock_data import (
    generate_synthetic_sales_history,
    get_baseline_for_category,
    get_training_dataset,
    price_demand_factor,
)

logger = logging.getLogger("ai_service.ml")

DEMAND_LABELS = {0: "low", 1: "medium", 2: "high"}
CATEGORY_ENCODER = LabelEncoder()


class DemandModel:
    """
    Phase 1: RandomForestClassifier trained on synthetic data.
    Phase 3 upgrade: retrain on real Sales Service data.
    """

    def __init__(self):
        self._model: RandomForestClassifier | None = None
        self._is_trained = False

    def _build_features(
        self,
        category: str,
        price: float,
        avg_daily_sales: float | None = None,
    ) -> np.ndarray:
        """Build feature vector for prediction."""
        price_factor = price_demand_factor(price)
        baseline = get_baseline_for_category(category)

        if avg_daily_sales is None:
            avg_daily_sales = baseline["avg_daily_sales"] * price_factor

        # One-hot-style category embedding via known categories
        cat_lower = category.lower()
        cat_score = 1.0 if any(
            k in cat_lower for k in ["food", "clothing", "toys"]
        ) else 0.5

        return np.array([[avg_daily_sales, price, price_factor, cat_score]])

    def train(self) -> None:
        """Train on synthetic dataset. Called once at startup."""
        logger.info("Training demand prediction model...")
        df = get_training_dataset()

        X = df[["avg_daily_sales", "price", "price_demand_factor"]].values
        y = df["demand_label"].values

        self._model = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42,
        )
        self._model.fit(X, y)
        self._is_trained = True
        logger.info("Demand model trained on %d samples.", len(df))

    def predict(
        self,
        product_id: int,
        category: str,
        price: float,
        current_quantity: int,
    ) -> dict:
        """
        Predict demand level for a product.
        Returns: {demand_level, confidence, predicted_daily_sales, reasoning}
        """
        if not self._is_trained:
            self.train()

        # Generate synthetic history to estimate avg daily sales
        hist = generate_synthetic_sales_history(product_id, category, price, days=30)
        avg_daily_sales = hist["quantity_sold"].mean()
        price_factor = price_demand_factor(price)

        features = np.array([[avg_daily_sales, price, price_factor]])
        prediction = self._model.predict(features)[0]
        probabilities = self._model.predict_proba(features)[0]
        confidence = float(probabilities[prediction])

        demand_label = DEMAND_LABELS[prediction]
        reasoning = self._build_reasoning(
            demand_label, category, price, avg_daily_sales, current_quantity
        )

        return {
            "demand_level": demand_label,
            "confidence": round(confidence, 3),
            "confidence_percentage": round(confidence * 100, 1),
            "predicted_daily_sales": round(float(avg_daily_sales), 2),
            "reasoning": reasoning,
        }

    @staticmethod
    def _build_reasoning(
        demand_level: str,
        category: str,
        price: float,
        avg_daily_sales: float,
        current_quantity: int,
    ) -> str:
        parts = [
            f"Category '{category}' has a {demand_level} demand profile.",
            f"Price ${price:.2f} places this product in the "
            + ("premium" if price > 500 else "mid-range" if price > 100 else "budget")
            + " tier.",
            f"Estimated average daily sales: {avg_daily_sales:.1f} units.",
        ]
        if current_quantity < avg_daily_sales * 7:
            parts.append("⚠ Current stock may run out within 7 days at this demand rate.")
        return " ".join(parts)


@lru_cache(maxsize=1)
def get_demand_model() -> DemandModel:
    """Return singleton trained model."""
    model = DemandModel()
    model.train()
    return model
