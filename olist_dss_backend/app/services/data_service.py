import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from app.config import DATA_MODE, DATABASE_URL, RANDOM_SEED

REQUIRED_COLUMNS = [
    "order_id", "purchase_date", "customer_state", "seller_state",
    "category_name_en", "order_status", "order_value", "freight_value",
    "item_count", "delivery_days", "delay_days", "is_late", "review_score"
]

def get_orders() -> pd.DataFrame:
    """Return one row per order. Demo mode is synthetic, never real Olist results."""
    if DATA_MODE == "demo":
        return _demo_orders()
    if DATA_MODE != "sql":
        raise ValueError("DSS_DATA_MODE must be either 'demo' or 'sql'.")
    if not DATABASE_URL:
        raise ValueError("DSS_DATA_MODE=sql requires DSS_DATABASE_URL in .env.")
    # Query the existing Gold tables directly; no dss.vw_dss_orders view is required.
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    query = text("""
        SELECT
            f.order_id AS order_id,
            MIN(d.full_date) AS purchase_date,
            MAX(c.current_state) AS customer_state,
            MAX(s.seller_state) AS seller_state,
            MAX(p.category_name_en) AS category_name_en,
            MAX(f.order_status) AS order_status,
            SUM(CAST(f.price AS float)) AS order_value,
            SUM(CAST(f.freight_value AS float)) AS freight_value,
            COUNT_BIG(*) AS item_count,
            MAX(CAST(f.delivery_days AS float)) AS delivery_days,
            MAX(CAST(f.delay_days AS float)) AS delay_days,
            MAX(CAST(f.is_late AS int)) AS is_late,
            AVG(CAST(f.review_score AS float)) AS review_score
        FROM gold.fact_order_item AS f
        LEFT JOIN gold.dim_date AS d ON f.date_key = d.date_key
        LEFT JOIN gold.dim_customer AS c ON f.customer_key = c.customer_key
        LEFT JOIN gold.dim_seller AS s ON f.seller_key = s.seller_key
        LEFT JOIN gold.dim_product AS p ON f.product_key = p.product_key
        GROUP BY f.order_id
    """)
    with engine.connect() as connection:
        df = pd.read_sql(query, connection)
    return _normalize(df)

def _normalize(df):
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Orders view is missing columns: {missing}")
    df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
    for col in ["order_value", "freight_value", "item_count", "delivery_days", "delay_days", "review_score", "is_late"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["customer_state", "seller_state"]:
        df[col] = df[col].fillna("NA").astype(str).str.upper().str[:2]
    df["category_name_en"] = df["category_name_en"].fillna("unknown").astype(str)
    df["order_status"] = df["order_status"].fillna("unknown").astype(str)
    return df

def _demo_orders(n=4500):
    rng = np.random.default_rng(RANDOM_SEED)
    states = np.array(["SP", "RJ", "MG", "PR", "RS", "SC", "BA", "DF", "GO", "PE"])
    categories = np.array(["bed_bath_table", "health_beauty", "sports_leisure", "furniture_decor", "computers_accessories", "unknown"])
    purchase = pd.Timestamp("2017-01-01") + pd.to_timedelta(rng.integers(0, 690, n), unit="D")
    customer_state = rng.choice(states, n)
    seller_state = rng.choice(states, n)
    item_count = rng.integers(1, 5, n)
    order_value = np.round(np.clip(rng.lognormal(4.1, 0.8, n), 15, 3000), 2)
    freight = np.round(rng.gamma(2.0, 12, n), 2)
    month = pd.DatetimeIndex(purchase).month
    weekday = pd.DatetimeIndex(purchase).weekday
    category = rng.choice(categories, n)
    logit = -1.4 + .025 * (freight / 2) + .28 * (customer_state != seller_state) + .22 * np.isin(month, [11, 12]) + .15 * (item_count > 2)
    probability = 1 / (1 + np.exp(-logit))
    is_late = rng.binomial(1, probability, n)
    delay = np.where(is_late == 1, rng.integers(1, 10, n), -rng.integers(0, 6, n))
    delivery_days = rng.integers(2, 26, n)
    df = pd.DataFrame({
        "order_id": [f"DEMO-{i:06d}" for i in range(n)],
        "purchase_date": purchase,
        "customer_state": customer_state,
        "seller_state": seller_state,
        "category_name_en": category,
        "order_status": "delivered",
        "order_value": order_value,
        "freight_value": freight,
        "item_count": item_count,
        "delivery_days": delivery_days,
        "delay_days": delay,
        "is_late": is_late,
        "review_score": rng.integers(1, 6, n),
    })
    return _normalize(df)
