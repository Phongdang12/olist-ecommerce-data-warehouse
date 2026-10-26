from app.services.analytics_service import dashboard_summary

def run_what_if(df, request):
    base = dashboard_summary(df)
    order_multiplier = 1 + request.order_growth_pct / 100
    value_multiplier = 1 + request.order_value_change_pct / 100
    freight_multiplier = 1 + request.freight_change_pct / 100
    projected_orders = round(base["orders"] * order_multiplier)
    projected_aov = base["average_order_value"] * value_multiplier
    projected_revenue = projected_orders * projected_aov
    projected_freight = base["freight_value_total"] * order_multiplier * freight_multiplier
    late_rate = base["late_rate_pct"]
    projected_late_rate = None if late_rate is None else late_rate * (1 - request.late_rate_reduction_pct / 100)
    return {
        "method": "deterministic_scenario_calculation",
        "warning": "What-if is simplified sensitivity analysis, not a causal forecast. Olist freight_value is recorded shipping charged, not necessarily operating cost.",
        "baseline": base,
        "scenario": {
            "orders": projected_orders, "average_order_value": round(projected_aov, 2),
            "order_value_total": round(projected_revenue, 2), "freight_value_total": round(projected_freight, 2),
            "late_rate_pct": round(projected_late_rate, 2) if projected_late_rate is not None else None,
        },
        "change": {
            "order_value_total": round(projected_revenue - base["order_value_total"], 2),
            "order_value_total_pct": round(100 * (projected_revenue / base["order_value_total"] - 1), 2) if base["order_value_total"] else None,
        },
    }
