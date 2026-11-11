from datetime import datetime, timezone
from app.config import DATA_MODE
from app.schemas import WhatIfRequest
from app.services.data_service import get_orders
from app.services.analytics_service import dashboard_summary, delivery_by_state
from app.services.customer_segmentation_service import get_latest_segment_summary
from app.services.whatif_service import run_what_if
from app.rules.recommendation_rules import (
    rule_r001_high_value_segment,
    rule_r002_late_delivery_by_state,
    rule_r003_freight_scenario,
)


def build_recommendations(*, order_growth_pct=None, order_value_change_pct=None,
                          freight_change_pct=None, late_rate_reduction_pct=None):
    """Compute recommendations from current warehouse data and optional What-if inputs."""
    warnings = []
    recommendations = []
    orders = get_orders()
    summary = dashboard_summary(orders)
    state_rows = delivery_by_state(orders)

    # State and global rates share the same order-level is_late definition.
    recommendations.extend(rule_r002_late_delivery_by_state(
        state_rows, summary.get("late_rate_pct"), min_eligible_orders=100, min_gap_pp=3.0
    ))

    # Segmentation tables are created only after a successful retraining run.
    try:
        segment_rows = get_latest_segment_summary()
        if segment_rows:
            r001 = rule_r001_high_value_segment(segment_rows, min_avg_monetary_ratio=1.5)
            if r001:
                recommendations.append(r001)
        else:
            warnings.append("Chưa có dữ liệu phân cụm khách hàng; chạy POST /api/v1/segments/retrain trước để đánh giá R001.")
    except Exception as exc:
        warnings.append("Không đọc được bảng dss.customer_segment_summary trong chế độ dữ liệu hiện tại; R001 chưa được đánh giá.")

    # R003 is evaluated only when the caller supplies scenario parameters.
    scenario_values = [order_growth_pct, order_value_change_pct, freight_change_pct, late_rate_reduction_pct]
    if any(value is not None for value in scenario_values):
        request = WhatIfRequest(
            order_growth_pct=0 if order_growth_pct is None else order_growth_pct,
            order_value_change_pct=0 if order_value_change_pct is None else order_value_change_pct,
            freight_change_pct=0 if freight_change_pct is None else freight_change_pct,
            late_rate_reduction_pct=0 if late_rate_reduction_pct is None else late_rate_reduction_pct,
        )
        r003 = rule_r003_freight_scenario(run_what_if(orders, request), min_freight_increase_pct=10.0)
        if r003:
            recommendations.append(r003)

    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda item: (priority_order.get(item["priority"], 3), item["rule_id"]))
    return {
        "recommendations": recommendations,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_mode": summary.get("data_mode_note", DATA_MODE),
        "warnings": warnings,
        "thresholds": {
            "R001_min_avg_monetary_ratio": 1.5,
            "R002_min_eligible_orders": 100,
            "R002_min_gap_percentage_points": 3.0,
            "R003_min_freight_increase_pct": 10.0,
        },
    }
