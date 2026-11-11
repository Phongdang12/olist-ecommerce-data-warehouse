"""Pure business rules for the first version of Decision Recommendations."""
from __future__ import annotations
from typing import Any
import math


def _num(value: Any, default=None):
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def rule_r001_high_value_segment(segment_rows: list[dict], *, min_avg_monetary_ratio: float = 1.5):
    """Recommend retention for the cluster with highest average monetary value.

    Cluster IDs are arbitrary; selection is based on measured RFM monetary values.
    """
    rows = []
    for row in segment_rows:
        count = _num(row.get("customer_count"), 0)
        avg_money = _num(row.get("avg_monetary"))
        total_money = _num(row.get("total_monetary"), 0)
        if count and count > 0 and avg_money is not None:
            rows.append({**row, "_count": count, "_avg_money": avg_money, "_total_money": total_money or 0})
    if not rows:
        return None
    total_customers = sum(r["_count"] for r in rows)
    overall_avg = sum(r["_total_money"] for r in rows) / total_customers if total_customers else 0
    best = max(rows, key=lambda r: (r["_avg_money"], r["_total_money"]))
    if overall_avg <= 0 or best["_avg_money"] < overall_avg * min_avg_monetary_ratio:
        return None
    cluster_id = int(best["cluster_id"])
    segment_name = str(best.get("segment_name") or f"Cluster {cluster_id}")
    ratio = best["_avg_money"] / overall_avg
    return {
        "rule_id": "R001",
        "title": "Phát hiện cụm khách hàng có giá trị mua hàng cao",
        "priority": "high" if ratio >= 2 else "medium",
        "evidence": {
            "cluster_id": cluster_id,
            "segment_name": segment_name,
            "customer_count": int(best["_count"]),
            "avg_monetary": round(best["_avg_money"], 2),
            "overall_avg_monetary_per_customer": round(overall_avg, 2),
            "value_ratio_vs_overall": round(ratio, 2),
        },
        "suggested_action": f"Ưu tiên chương trình giữ chân và chăm sóc cá nhân hóa cho cụm '{segment_name}'.",
        "reason": f"Chi tiêu trung bình của cụm cao nhất gấp {ratio:.2f} lần mức trung bình mỗi khách hàng toàn bộ các cụm; lựa chọn dựa trên RFM thực tế, không dựa vào cluster_id.",
    }


def rule_r002_late_delivery_by_state(
    state_rows: list[dict], overall_late_rate_pct: float | None,
    *, min_eligible_orders: int = 100, min_gap_pp: float = 3.0,
):
    if overall_late_rate_pct is None:
        return []
    recommendations = []
    for row in state_rows:
        late_rate = _num(row.get("late_rate_pct"))
        eligible = int(_num(row.get("known_labels"), 0) or 0)
        state = str(row.get("state", "NA"))
        if late_rate is None or eligible < min_eligible_orders:
            continue
        gap = late_rate - overall_late_rate_pct
        if gap < min_gap_pp:
            continue
        recommendations.append({
            "rule_id": "R002",
            "title": "Tỷ lệ giao trễ cao",
            "priority": "high" if gap >= 7 else "medium",
            "evidence": {
                "state": state,
                "late_rate_pct": round(late_rate, 2),
                "overall_late_rate_pct": round(overall_late_rate_pct, 2),
                "gap_percentage_points": round(gap, 2),
                "eligible_orders": eligible,
                "late_orders": int(_num(row.get("late_orders"), 0) or 0),
            },
            "suggested_action": f"Kiểm tra hiệu quả vận chuyển, hãng vận chuyển và thời gian xử lý đơn tại bang {state}.",
            "reason": f"Bang {state} có tỷ lệ giao trễ cao hơn mức toàn hệ thống {gap:.2f} điểm phần trăm trên {eligible} đơn có trạng thái giao hàng xác định.",
        })
    return sorted(recommendations, key=lambda x: (x["priority"] != "high", -x["evidence"]["gap_percentage_points"], -x["evidence"]["eligible_orders"]))


def rule_r003_freight_scenario(what_if_result: dict | None, *, min_freight_increase_pct: float = 10.0):
    """Only fires when a user explicitly supplies What-if scenario parameters."""
    if not what_if_result:
        return None
    baseline = what_if_result.get("baseline") or {}
    scenario = what_if_result.get("scenario") or {}
    base_freight = _num(baseline.get("freight_value_total"))
    scenario_freight = _num(scenario.get("freight_value_total"))
    if base_freight is None or scenario_freight is None or base_freight <= 0:
        return None
    change_pct = (scenario_freight / base_freight - 1) * 100
    if change_pct < min_freight_increase_pct:
        return None
    return {
        "rule_id": "R003",
        "title": "Kịch bản làm tăng đáng kể tổng phí vận chuyển ghi nhận",
        "priority": "high" if change_pct >= 25 else "medium",
        "evidence": {
            "baseline_freight_value_total": round(base_freight, 2),
            "scenario_freight_value_total": round(scenario_freight, 2),
            "freight_increase_pct": round(change_pct, 2),
            "freight_increase_amount": round(scenario_freight - base_freight, 2),
            "method": what_if_result.get("method", "deterministic_scenario_calculation"),
        },
        "suggested_action": "Đánh giá lại chính sách phí vận chuyển, năng lực xử lý đơn và phương án thương lượng với đối tác vận chuyển trước khi triển khai kịch bản.",
        "reason": f"Kết quả What-if cho thấy tổng freight_value ghi nhận tăng {change_pct:.2f}% so với đường cơ sở. Đây là phân tích độ nhạy, không phải dự báo nhân quả hay chi phí vận hành thực tế.",
    }
