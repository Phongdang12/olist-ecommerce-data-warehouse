from app.rules.recommendation_rules import (
    rule_r001_high_value_segment,
    rule_r002_late_delivery_by_state,
    rule_r003_freight_scenario,
)


def test_r001_uses_monetary_values_not_cluster_id():
    rows = [
        {"cluster_id": 0, "segment_name": "Low value", "customer_count": 100, "avg_monetary": 50, "total_monetary": 5000},
        {"cluster_id": 3, "segment_name": "Premium", "customer_count": 20, "avg_monetary": 300, "total_monetary": 6000},
    ]
    result = rule_r001_high_value_segment(rows)
    assert result is not None
    assert result["rule_id"] == "R001"
    assert result["evidence"]["cluster_id"] == 3
    assert result["evidence"]["segment_name"] == "Premium"


def test_r002_requires_sample_size_and_three_point_gap():
    rows = [
        {"state": "SP", "known_labels": 150, "late_orders": 30, "late_rate_pct": 20},
        {"state": "RJ", "known_labels": 99, "late_orders": 30, "late_rate_pct": 30},
        {"state": "MG", "known_labels": 150, "late_orders": 15, "late_rate_pct": 10},
    ]
    result = rule_r002_late_delivery_by_state(rows, 10)
    assert [r["evidence"]["state"] for r in result] == ["SP"]
    assert result[0]["evidence"]["gap_percentage_points"] == 10


def test_r003_uses_whatif_result_and_threshold():
    low = {"baseline": {"freight_value_total": 1000}, "scenario": {"freight_value_total": 1099}}
    high = {"method": "deterministic_scenario_calculation", "baseline": {"freight_value_total": 1000}, "scenario": {"freight_value_total": 1150}}
    assert rule_r003_freight_scenario(low) is None
    result = rule_r003_freight_scenario(high)
    assert result["rule_id"] == "R003"
    assert result["evidence"]["freight_increase_pct"] == 15


def test_r002_does_not_trigger_when_overall_rate_unknown():
    assert rule_r002_late_delivery_by_state(
        [{"state": "SP", "known_labels": 500, "late_rate_pct": 25}], None
    ) == []
