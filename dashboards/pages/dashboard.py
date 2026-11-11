import streamlit as st

from db import get_connection
from olap import query

##this page is for demonstrative dashboards that immediately answer some questions. no interactive OLAP

conn = get_connection()

##header
st.title("Olist Data Warehouse Dashboard")

st.caption(
    "Overview of marketplace sales, orders, products, "
    "customers, and delivery performance."
)

##KPI
total_revenue_df = query(
    conn,
    dimensions=[],
    measure="revenue"
)

total_orders_df = query(
    conn,
    dimensions=[],
    measure="orders"
)

total_items_df = query(
    conn,
    dimensions=[],
    measure="items"
)

average_price_df = query(
    conn,
    dimensions=[],
    measure="average_item_price"
)

total_revenue = total_revenue_df.iloc[0]["revenue"]
total_orders = total_orders_df.iloc[0]["orders"]
total_items = total_items_df.iloc[0]["items"]
average_price = average_price_df.iloc[0]["average_item_price"]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Revenue",
        f"R$ {total_revenue:,.2f}"
    )

with col2:
    st.metric(
        "Total Orders",
        f"{total_orders:,.0f}"
    )

with col3:
    st.metric(
        "Items Sold",
        f"{total_items:,.0f}"
    )

with col4:
    st.metric(
        "Average Item Price",
        f"R$ {average_price:,.2f}"
    )

st.divider()

##revenue over time

st.subheader("Revenue by Year")

revenue_by_year = query(
    conn,
    dimensions=["year"],
    measure="revenue"
)

st.bar_chart(
    revenue_by_year,
    x="year",
    y="revenue"
)

##2 columns analysis from here

left, right = st.columns(2)

#product categories

with left:

    st.subheader("Top Product Categories")

    category_revenue = query(
        conn,
        dimensions=["category"],
        measure="revenue",
        order_by_measure=True
    )

    # Keep dashboard readable
    category_revenue = category_revenue.head(10)

    st.bar_chart(
        category_revenue,
        x="category",
        y="revenue",
        horizontal=True
    )

##customer geography

with right:

    st.subheader("Revenue by Customer Region")

    region_revenue = query(
        conn,
        dimensions=["customer_region"],
        measure="revenue",
        order_by_measure=True
    )

    st.bar_chart(
        region_revenue,
        x="customer_region",
        y="revenue"
    )

st.divider()

left, right = st.columns(2)

##orders

with left:

    st.subheader("Orders by Year")

    orders_by_year = query(
        conn,
        dimensions=["year"],
        measure="orders"
    )

    st.bar_chart(
        orders_by_year,
        x="year",
        y="orders"
    )

##delivery time

with right:

    st.subheader("Average Delivery Time")

    delivery_time = query(
        conn,
        dimensions=["year"],
        measure="average_delivery_days"
    )

    st.line_chart(
        delivery_time,
        x="year",
        y="average_delivery_days"
    )

st.divider()

#details table

st.subheader("Revenue by Year and Product Category")

year_category = query(
    conn,
    dimensions=["year", "category"],
    measure="revenue",
    order_by_measure=True
)

st.dataframe(
    year_category,
    use_container_width=True,
    hide_index=True
)