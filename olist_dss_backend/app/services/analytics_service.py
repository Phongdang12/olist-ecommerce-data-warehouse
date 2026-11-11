import pandas as pd

def _valid_late(df):
    # Null is_late means no reliable outcome; exclude it from the denominator.
    return pd.to_numeric(df["is_late"], errors="coerce")

def dashboard_summary(df):
    total_orders = int(df["order_id"].nunique())
    revenue = float(df["order_value"].sum())
    known = _valid_late(df).dropna()
    delivered_like = int(known.shape[0])
    late_rate = float(known.mean() * 100) if delivered_like else None
    scores = pd.to_numeric(df["review_score"], errors="coerce").dropna()
    return {
        "data_mode_note": "SYNTHETIC DEMO DATA" if df["order_id"].astype(str).str.startswith("DEMO-").all() else "WAREHOUSE DATA",
        "orders": total_orders,
        "order_value_total": round(revenue, 2),
        "average_order_value": round(revenue / total_orders, 2) if total_orders else 0,
        "freight_value_total": round(float(df["freight_value"].sum()), 2),
        "orders_with_known_late_status": delivered_like,
        "late_rate_pct": round(late_rate, 2) if late_rate is not None else None,
        "average_review_score": round(float(scores.mean()), 2) if len(scores) else None,
    }

def sales_by_category(df):
    grouped = df.groupby("category_name_en", dropna=False).agg(
        revenue=("order_value", "sum"), orders=("order_id", "nunique")
    ).reset_index().sort_values("revenue", ascending=False)
    return [{"category": str(r.category_name_en), "revenue": round(float(r.revenue), 2), "orders": int(r.orders)}
            for r in grouped.itertuples(index=False)]

def delivery_by_state(df):
    work = df.copy()
    work["is_late_num"] = _valid_late(work)
    grouped = work.groupby("customer_state", dropna=False).agg(
        orders=("order_id", "nunique"),
        known_labels=("is_late_num", "count"),
        late_orders=("is_late_num", "sum"),
    ).reset_index()
    grouped["late_rate_pct"] = grouped.apply(
        lambda r: round(100 * r["late_orders"] / r["known_labels"], 2) if r["known_labels"] else None, axis=1
    )
    grouped = grouped.sort_values(["late_rate_pct", "orders"], ascending=[False, False], na_position="last")
    return [{"state": str(r.customer_state), "orders": int(r.orders), "known_labels": int(r.known_labels),
             "late_orders": int(r.late_orders), "late_rate_pct": r.late_rate_pct}
            for r in grouped.itertuples(index=False)]
