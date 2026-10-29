#flow: streamlit UI (app.py) -> olap.py (this file) -> parameterized SQL query -> SQL server -> useful query results for the requested op -> pandas dataframe -> Streamlit chart/table (display out app.py)
import pandas as pd


# ============================================================
# Dimensions that the OLAP layer is allowed to use.
#
# We whitelist these because SQL column/table names cannot be
# supplied safely through ? parameters.
# ============================================================

DIMENSIONS = {
    # Time
    "year": "d.year_num",
    "quarter": "d.quarter_name",
    "month": "d.year_month",
    "day": "d.full_date",

    # Product
    "category": "p.category_name_en",
    "weight_class": "p.weight_class",

    # Customer
    "customer_region": "c.current_region",
    "customer_state": "c.current_state",
    "customer_city": "c.current_city",

    # Seller
    "seller_region": "s.seller_region",
    "seller_state": "s.seller_state",
    "seller_city": "s.seller_city",

    # Delivery destination
    "delivery_region": "f.delivery_region",
    "delivery_state": "f.delivery_state",
    "delivery_city": "f.delivery_city",

    # Order attributes
    "order_status": "f.order_status",
    "late_status": "f.is_late",
}


# ============================================================
# Measures
# ============================================================

MEASURES = {
    # One fact row = one item, therefore COUNT(*) = item count
    "items": "COUNT(*)",

    # Orders require DISTINCT because one order can contain
    # multiple fact rows.
    "orders": "COUNT(DISTINCT f.order_id)",

    "revenue": "SUM(f.price)",
    "freight": "SUM(f.freight_value)",

    "average_item_price": "AVG(f.price)",
    "average_freight": "AVG(f.freight_value)",

    "average_delivery_days": "AVG(CAST(f.delivery_days AS FLOAT))",
    "average_delay_days": "AVG(CAST(f.delay_days AS FLOAT))",

    "late_items": """
        SUM(
            CASE
                WHEN f.is_late = 1 THEN 1
                ELSE 0
            END
        )
    """,
}


BASE_FROM = """
FROM gold.fact_order_item f

JOIN gold.dim_date d
    ON f.date_key = d.date_key

JOIN gold.dim_customer c
    ON f.customer_key = c.customer_key

JOIN gold.dim_seller s
    ON f.seller_key = s.seller_key

JOIN gold.dim_product p
    ON f.product_key = p.product_key
"""


# ============================================================
# Internal helpers
# ============================================================

def _validate_dimension(dimension):
    if dimension not in DIMENSIONS:
        raise ValueError(
            f"Unknown dimension '{dimension}'. "
            f"Valid dimensions: {list(DIMENSIONS.keys())}"
        )


def _validate_measure(measure):
    if measure not in MEASURES:
        raise ValueError(
            f"Unknown measure '{measure}'. "
            f"Valid measures: {list(MEASURES.keys())}"
        )


def _build_where(filters):
    """
    Convert:
        {
            "year": 2018,
            "customer_state": "SP"
        }

    into:
        WHERE d.year_num = ?
          AND c.current_state = ?

    and return the corresponding parameter list.
    """

    if not filters:
        return "", []

    conditions = []
    params = []

    for dimension, value in filters.items():

        _validate_dimension(dimension)

        # None means no filter on that dimension
        if value is None:
            continue

        column = DIMENSIONS[dimension]

        # Allow a list for IN (...) filtering
        if isinstance(value, (list, tuple, set)):
            values = list(value)

            if len(values) == 0:
                continue

            placeholders = ", ".join(["?"] * len(values))

            conditions.append(
                f"{column} IN ({placeholders})"
            )

            params.extend(values)

        else:
            conditions.append(
                f"{column} = ?"
            )

            params.append(value)

    if not conditions:
        return "", []

    return "WHERE " + " AND ".join(conditions), params


# ============================================================
# Generic OLAP query
# ============================================================

def query(
    conn,
    dimensions,
    measure,
    filters=None,
    order_by_measure=False
):
    """
    Generic aggregation query.

    Example:

        query(
            conn,
            dimensions=["year", "category"],
            measure="revenue",
            filters={"customer_state": "SP"}
        )
    """

    _validate_measure(measure)

    for dimension in dimensions:
        _validate_dimension(dimension)

    dimension_columns = [
        DIMENSIONS[d] for d in dimensions
    ]

    measure_sql = MEASURES[measure]

    where_clause, params = _build_where(filters)

    # Give columns nice names in returned DataFrame
    select_dimensions = ",\n".join(
        f"{DIMENSIONS[d]} AS {d}"
        for d in dimensions
    )

    if select_dimensions:
        select_clause = (
            select_dimensions +
            f",\n{measure_sql} AS {measure}"
        )
    else:
        select_clause = f"{measure_sql} AS {measure}"

    sql = f"""
        SELECT
            {select_clause}

        {BASE_FROM}

        {where_clause}
    """

    if dimension_columns:
        sql += "\nGROUP BY " + ", ".join(dimension_columns)

        if order_by_measure:
            sql += f"\nORDER BY {measure} DESC"
        else:
            sql += "\nORDER BY " + ", ".join(dimension_columns)

    return pd.read_sql(
        sql,
        conn,
        params=params
    )


# ============================================================
# OLAP operations
# ============================================================

def slice_data(
    conn,
    dimension,
    value,
    group_by,
    measure="revenue"
):
    """
    SLICE

    Fix one dimension to a single value.

    Example:
        Year = 2018
        Revenue grouped by category
    """

    return query(
        conn,
        dimensions=group_by,
        measure=measure,
        filters={
            dimension: value
        }
    )


def dice_data(
    conn,
    filters,
    group_by,
    measure="revenue"
):
    """
    DICE

    Filter several dimensions simultaneously.

    Example:
        Year = 2018
        Customer State = SP
        Categories = health_beauty, sports_leisure
    """

    return query(
        conn,
        dimensions=group_by,
        measure=measure,
        filters=filters
    )


# ============================================================
# Drill-down / roll-up
# ============================================================

TIME_HIERARCHY = [
    "year",
    "quarter",
    "month",
    "day"
]

CUSTOMER_LOCATION_HIERARCHY = [
    "customer_region",
    "customer_state",
    "customer_city"
]

SELLER_LOCATION_HIERARCHY = [
    "seller_region",
    "seller_state",
    "seller_city"
]

DELIVERY_LOCATION_HIERARCHY = [
    "delivery_region",
    "delivery_state",
    "delivery_city"
]


def drill_down(
    conn,
    hierarchy,
    level,
    measure="revenue",
    filters=None
):
    """
    DRILL DOWN

    level determines how far down a hierarchy we go.

    TIME example:

        level=0 -> year
        level=1 -> year, quarter
        level=2 -> year, quarter, month
        level=3 -> year, quarter, month, day
    """

    if level < 0 or level >= len(hierarchy):
        raise ValueError("Invalid hierarchy level")

    dimensions = hierarchy[:level + 1]

    return query(
        conn,
        dimensions=dimensions,
        measure=measure,
        filters=filters
    )


def roll_up(
    conn,
    hierarchy,
    level,
    measure="revenue",
    filters=None
):
    """
    ROLL UP

    Same underlying aggregation mechanism as drill-down;
    the UI simply moves toward a higher level.

    Example:
        month -> quarter -> year
    """

    return drill_down(
        conn,
        hierarchy,
        level,
        measure,
        filters
    )


# ============================================================
# Pivot
# ============================================================

def pivot_data(
    conn,
    row_dimension,
    column_dimension,
    measure="revenue",
    filters=None
):
    """
    PIVOT

    Example:

                   2016       2017       2018
        SP         ...
        RJ         ...
        MG         ...

    row_dimension = customer_state
    column_dimension = year
    """

    df = query(
        conn,
        dimensions=[
            row_dimension,
            column_dimension
        ],
        measure=measure,
        filters=filters
    )

    return df.pivot_table(
        index=row_dimension,
        columns=column_dimension,
        values=measure,
        aggfunc="sum",
        fill_value=0
    )