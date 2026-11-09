"""Demand prediction service — delegates to ML model."""
from app.ml.demand_model import get_demand_model
from app.schemas.ai_schemas import DemandPredictionRequest, DemandPredictionResponse


class DemandService:
    def predict(self, data: DemandPredictionRequest) -> DemandPredictionResponse:
        model = get_demand_model()
        result = model.predict(
            product_id=data.product_id,
            category=data.category,
            price=data.price,
            current_quantity=data.current_quantity,
        )
        return DemandPredictionResponse(
            product_id=data.product_id,
            product_name=data.product_name,
            **result,
        )
