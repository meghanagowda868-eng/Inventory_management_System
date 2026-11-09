"""AI Service routers — insights, prediction, reorder, NLQ."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings
from app.schemas.ai_schemas import (
    DemandPredictionRequest, DemandPredictionResponse,
    InventoryInsightsResponse,
    NLQueryRequest, NLQueryResponse,
    ReorderSuggestionRequest, ReorderSuggestionResponse,
)
from app.services.demand_service import DemandService
from app.services.insights_service import InsightsService
from app.services.nlq_service import NLQService
from app.services.reorder_service import ReorderService

_bearer = HTTPBearer()
settings = get_settings()
router = APIRouter(prefix="/ai", tags=["AI"])


def get_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> HTTPAuthorizationCredentials:
    """Validate the signed access token before accepting AI requests."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "ai-service"}


# ── Inventory Insights ────────────────────────────────────────────────────────

@router.get(
    "/insights",
    response_model=InventoryInsightsResponse,
    summary="Get inventory overview insights",
)
async def get_insights(
    credentials: HTTPAuthorizationCredentials = Depends(get_access_token),
):
    """
    Returns total products, inventory value, low stock count, out of stock count.
    Fetches live data from Inventory Service.
    """
    service = InsightsService()
    return await service.get_insights(credentials.credentials)


# ── Demand Prediction ─────────────────────────────────────────────────────────

@router.post(
    "/predict-demand",
    response_model=DemandPredictionResponse,
    summary="Predict product demand level",
    dependencies=[Depends(get_access_token)],
)
def predict_demand(
    data: DemandPredictionRequest,
):
    """
    Predict demand level (low/medium/high) for a product.
    Uses RandomForest model trained on synthetic sales data.
    """
    return DemandService().predict(data)


# ── Reorder Suggestion ────────────────────────────────────────────────────────

@router.post(
    "/reorder-suggestion",
    response_model=ReorderSuggestionResponse,
    summary="Get smart reorder quantity suggestion",
    dependencies=[Depends(get_access_token)],
)
def reorder_suggestion(
    data: ReorderSuggestionRequest,
):
    """
    Calculate recommended reorder quantity based on current stock,
    minimum stock, average daily sales, and supplier lead time.
    """
    return ReorderService().suggest(data)


# ── Natural Language Query ────────────────────────────────────────────────────

@router.post(
    "/query",
    response_model=NLQueryResponse,
    summary="Natural language inventory query",
)
async def nl_query(
    data: NLQueryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(get_access_token),
):
    """
    Convert a plain English question into an inventory query.
    Examples: 'Show low stock products', 'What is the total inventory value?'
    """
    service = NLQService()
    return await service.query(data, credentials.credentials)
