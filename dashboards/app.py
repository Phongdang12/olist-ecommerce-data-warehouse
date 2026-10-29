import streamlit as st

from db import get_connection
from olap import query

conn = get_connection()

df = query( #query for number of orders group by year
    conn,
    dimensions=["year"],
    measure="orders"
)

st.dataframe(df)

st.bar_chart(
    df,
    x="year",
    y="orders"
)

from olap import slice_data

df = slice_data( #query for revenue of each category in only the year 2018 (filtered by year)
    conn,
    dimension="year",
    value=2018,
    group_by=["category"],
    measure="revenue"
)

st.bar_chart(
    df,
    x="category",
    y="revenue"
)

from olap import dice_data

df = dice_data( #query for revenue of each category in only the year 2018, customer state is SP, and only categories health_beauty and sports_leisure
    conn,

    filters={
        "year": 2018,
        "customer_state": "SP",
        "category": [
            "health_beauty",
            "sports_leisure"
        ]
    },

    group_by=["category"],

    measure="revenue"
)

st.dataframe(df)

from olap import drill_down, TIME_HIERARCHY

level_names = {
    "Year": 0,
    "Quarter": 1,
    "Month": 2,
    "Day": 3
}

selected_level_name = st.selectbox(
    "Time granularity",
    level_names.keys()
)

selected_level = level_names[selected_level_name]

df = drill_down( #display revenue group by TIME_HIERARCHY, 0 means year, change to 1 and it displays year and quarter, and so on
    conn,
    TIME_HIERARCHY,
    selected_level,
    measure="revenue"
) #rollup is actually the exact same op, just reversed. here we display everything up to the deepest level based on a select box, so just choose a lower number
#to rollup. the roll_up() function is an alias of drill_down().

st.dataframe(df)

from olap import pivot_data

df = pivot_data( #display a row/column table with each cell being a revenue of the corresponding customer_state x year
    conn,
    row_dimension="customer_state",
    column_dimension="year",
    measure="revenue"
)

st.dataframe(df)