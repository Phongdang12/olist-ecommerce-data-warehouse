from fastapi import APIRouter, HTTPException, Query
from app.recommendation_schemas import RecommendationResponse
from app.services.recommendation_service import build_recommendations

router = APIRouter(prefix="/api/v1/recommendations", tags=["Decision Recommendations"])

@router.get("", response_model=RecommendationResponse)
def get_recommendations(
    order_growth_pct: float | None = Query(None, ge=-90, le=300, description="Optional What-if order growth percentage; supplying any scenario parameter enables R003 evaluation."),
    order_value_change_pct: float | None = Query(None, ge=-90, le=300),
    freight_change_pct: float | None = Query(None, ge=-100, le=300),
    late_rate_reduction_pct: float | None = Query(None, ge=0, le=100),
):
    """Return rule-based decision recommendations using current Olist DSS data."""
    try:
        return build_recommendations(
            order_growth_pct=order_growth_pct,
            order_value_change_pct=order_value_change_pct,
            freight_change_pct=freight_change_pct,
            late_rate_reduction_pct=late_rate_reduction_pct,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not build recommendations: {exc}")
