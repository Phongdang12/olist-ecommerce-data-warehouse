import streamlit as st
import pandas as pd

from db import get_connection

from olap import (
    query,
    slice_data,
    dice_data,
    pivot_data,
    drill_down,
    roll_up,
    get_dimension_values,

    TIME_HIERARCHY,
    CUSTOMER_LOCATION_HIERARCHY,
    SELLER_LOCATION_HIERARCHY,
    DELIVERY_LOCATION_HIERARCHY,
)
##this page is for the user to interacte with the data warehouse using the OLAP operations:
#SLICE (filter 1 attribute), DICE (filter multiple attributes), and PIVOT (replace axes in a 2d tables) change subset of cube
#ROLLUP and DRILLDOWN change granularity

conn = get_connection()


st.title("Interactive OLAP Explorer")

st.caption(
    "Explore the Olist data warehouse using "
    "slice, dice, pivot, drill-down, and roll-up operations."
)

MEASURE_LABELS = {
    "Revenue": "revenue",
    "Orders": "orders",
    "Items Sold": "items",
    "Freight Value": "freight",
    "Average Item Price": "average_item_price",
    "Average Freight": "average_freight",
    "Average Delivery Days": "average_delivery_days",
    "Average Delay Days": "average_delay_days",
    "Late Items": "late_items",
}


DIMENSION_LABELS = {
    "Year": "year",
    "Quarter": "quarter",
    "Month": "month",
    "Day": "day",

    "Product Category": "category",
    "Weight Class": "weight_class",

    "Customer Region": "customer_region",
    "Customer State": "customer_state",
    "Customer City": "customer_city",

    "Seller Region": "seller_region",
    "Seller State": "seller_state",
    "Seller City": "seller_city",

    "Delivery Region": "delivery_region",
    "Delivery State": "delivery_state",
    "Delivery City": "delivery_city",

    "Order Status": "order_status",
    "Late Status": "late_status",
}

DIMENSION_DISPLAY_NAMES = {
    value: key
    for key, value in DIMENSION_LABELS.items()
}


HIERARCHIES = {
    "Time": TIME_HIERARCHY,
    "Customer Geography": CUSTOMER_LOCATION_HIERARCHY,
    "Seller Geography": SELLER_LOCATION_HIERARCHY,
    "Delivery Geography": DELIVERY_LOCATION_HIERARCHY,
}

if "olap_filter_ids" not in st.session_state:
    st.session_state.olap_filter_ids = []

if "olap_next_filter_id" not in st.session_state:
    st.session_state.olap_next_filter_id = 0

if "hierarchy_level" not in st.session_state:
    st.session_state.hierarchy_level = 0

if "hierarchy_last_action" not in st.session_state:
    st.session_state.hierarchy_last_action = "drill"

if "row_axis_label" not in st.session_state:
    st.session_state.row_axis_label = "Product Category"

if "column_axis_label" not in st.session_state:
    st.session_state.column_axis_label = "None"

def swap_axes():
    """
    Swap the two axes.

    This is the most obvious visual demonstration of PIVOT.
    """

    row = st.session_state.row_axis_label
    column = st.session_state.column_axis_label

    # Cannot make "None" a row dimension.
    if column != "None":
        st.session_state.row_axis_label = column
        st.session_state.column_axis_label = row

st.subheader("Measure")

measure_label = st.selectbox(
    "Measure to analyse",
    list(MEASURE_LABELS.keys()),
    label_visibility="collapsed",
)

measure = MEASURE_LABELS[measure_label]


st.divider()

st.subheader("Axes")

st.caption(
    "Choose how the aggregated data should be arranged. "
    "Using both rows and columns produces a pivot table."
)


axis_col1, axis_col2, axis_col3 = st.columns([3, 3, 1])


with axis_col1:

    row_label = st.selectbox(
        "Rows",
        list(DIMENSION_LABELS.keys()),
        key="row_axis_label",
    )


with axis_col2:

    column_label = st.selectbox(
        "Columns",
        ["None"] + list(DIMENSION_LABELS.keys()),
        key="column_axis_label",
    )


with axis_col3:

    st.write("")

    st.button(
        "⇄ Swap",
        on_click=swap_axes,
        use_container_width=True,
        disabled=(column_label == "None"),
        help="Swap the row and column dimensions.",
    )


row_dimension = DIMENSION_LABELS[row_label]

column_dimension = (
    None
    if column_label == "None"
    else DIMENSION_LABELS[column_label]
)


if (
    column_dimension is not None
    and row_dimension == column_dimension
):

    st.warning(
        "Rows and columns must use different dimensions."
    )


# ============================================================
# HIERARCHY / DRILL-DOWN / ROLL-UP
# ============================================================

st.divider()

st.subheader("Hierarchy")

use_hierarchy = st.checkbox(
    "Use a hierarchy on the row axis",
    help=(
        "Allows the row axis to move between levels such as "
        "Year → Quarter → Month → Day. THIS WILL OVERRIDE THE ROW SELECTION ABOVE."
    ),
)


hierarchy = None
active_row_dimensions = [row_dimension]


if use_hierarchy:

    hierarchy_col1, hierarchy_col2 = st.columns([2, 3])

    with hierarchy_col1:

        hierarchy_name = st.selectbox(
            "Hierarchy",
            list(HIERARCHIES.keys()),
        )

        hierarchy = HIERARCHIES[hierarchy_name]


    # Prevent an old level from being outside a newly selected hierarchy.
    st.session_state.hierarchy_level = min(
        st.session_state.hierarchy_level,
        len(hierarchy) - 1
    )

    current_level = st.session_state.hierarchy_level


    with hierarchy_col2:

        visible_levels = hierarchy[:current_level + 1]

        pretty_hierarchy = " → ".join(
            DIMENSION_DISPLAY_NAMES.get(
                dimension,
                dimension
            )
            for dimension in visible_levels
        )

        st.write("Current path")

        st.code(
            pretty_hierarchy,
            language=None
        )


    drill_col, rollup_col = st.columns(2)


    with drill_col:

        if st.button(
            "↓ Drill Down",
            use_container_width=True,
            disabled=(
                current_level
                >= len(hierarchy) - 1
            ),
        ):

            st.session_state.hierarchy_level += 1
            st.session_state.hierarchy_last_action = "drill"

            st.rerun()


    with rollup_col:

        if st.button(
            "↑ Roll Up",
            use_container_width=True,
            disabled=(current_level == 0),
        ):

            st.session_state.hierarchy_level -= 1
            st.session_state.hierarchy_last_action = "rollup"

            st.rerun()


    current_level = st.session_state.hierarchy_level

    active_row_dimensions = hierarchy[:current_level + 1]

    # The deepest currently visible level is the actual chart axis.
    row_dimension = hierarchy[current_level]

    st.info(
        "Row granularity: "
        + DIMENSION_DISPLAY_NAMES.get(
            row_dimension,
            row_dimension
        )
    )


st.divider()


st.subheader("Filters")

st.caption(
    "Add any warehouse dimension as a filter. "
    "One dimension with one selected value is treated as a "
    "slice. Multiple values or dimensions form a dice."
)


if st.button("+ Add Filter"):

    new_id = st.session_state.olap_next_filter_id

    st.session_state.olap_filter_ids.append(
        new_id
    )

    st.session_state.olap_next_filter_id += 1

    st.rerun()


filters = {}


for filter_id in list(
    st.session_state.olap_filter_ids
):

    filter_col1, filter_col2, filter_col3 = st.columns(
        [2, 5, 1]
    )


    with filter_col1:

        dimension_label = st.selectbox(
            "Dimension",
            list(DIMENSION_LABELS.keys()),
            key=f"filter_dimension_{filter_id}",
        )

        filter_dimension = DIMENSION_LABELS[
            dimension_label
        ]


    dimension_values = get_dimension_values(
        conn,
        filter_dimension
    )


    with filter_col2:

        selected_values = st.multiselect(
            "Values",
            dimension_values,
            key=f"filter_values_{filter_id}_{filter_dimension}",
        )


    with filter_col3:

        st.write("")

        if st.button(
            "✕",
            key=f"remove_filter_{filter_id}",
            help="Remove this filter",
            use_container_width=True,
        ):

            st.session_state.olap_filter_ids.remove(
                filter_id
            )

            st.rerun()


    if selected_values:

        # If the same dimension was accidentally added twice,
        # merge the selected values rather than generating
        # contradictory filters.
        if filter_dimension not in filters:

            filters[filter_dimension] = []

        for value in selected_values:

            if value not in filters[filter_dimension]:

                filters[filter_dimension].append(
                    value
                )


if not st.session_state.olap_filter_ids:

    st.caption(
        "No filters added."
    )


filter_operation = None


if filters:

    total_selected_values = sum(
        len(values)
        for values in filters.values()
    )

    # Definition used by this project:
    #
    # one dimension + one value = slice
    #
    # anything more complex = dice
    if (
        len(filters) == 1
        and total_selected_values == 1
    ):

        filter_operation = "SLICE"

    else:

        filter_operation = "DICE"

st.divider()

st.subheader("Current Analysis")


summary_col1, summary_col2 = st.columns(2)


with summary_col1:

    st.write(
        f"**Measure:** {measure_label}"
    )

    if use_hierarchy:

        st.write(
            "**Rows:** "
            + " → ".join(
                DIMENSION_DISPLAY_NAMES.get(
                    d,
                    d
                )
                for d in active_row_dimensions
            )
        )

    else:

        st.write(
            f"**Rows:** {row_label}"
        )

    st.write(
        f"**Columns:** {column_label}"
    )


with summary_col2:

    if filters:

        st.write("**Filters:**")

        for dimension, values in filters.items():

            pretty_dimension = (
                DIMENSION_DISPLAY_NAMES.get(
                    dimension,
                    dimension
                )
            )

            values_string = ", ".join(
                str(value)
                for value in values
            )

            st.write(
                f"- {pretty_dimension}: "
                f"{values_string}"
            )

    else:

        st.write("**Filters:** None")


operations = []


if filter_operation:
    operations.append(filter_operation)


if column_dimension is not None:
    operations.append("PIVOT")


if use_hierarchy:

    if st.session_state.hierarchy_last_action == "rollup":
        operations.append("ROLL-UP")
    else:
        operations.append("DRILL-DOWN")


if operations:

    st.info(
        "Active OLAP operation(s): "
        + " + ".join(operations)
    )

else:

    st.info(
        "No explicit OLAP transformation is currently active."
    )

st.divider()

st.subheader("Result")


# Cannot execute a pivot where both axes are identical.
if (
    column_dimension is not None
    and row_dimension == column_dimension
):

    st.warning(
        "Choose different row and column dimensions "
        "before running this analysis."
    )

    st.stop()


# ============================================================
# CASE 1
#
# Hierarchy, without a column dimension
#
# Explicitly use drill_down() / roll_up()
# ============================================================

if (
    use_hierarchy
    and column_dimension is None
):

    current_level = st.session_state.hierarchy_level


    if st.session_state.hierarchy_last_action == "rollup":

        result = roll_up(
            conn,
            hierarchy=hierarchy,
            level=current_level,
            measure=measure,
            filters=filters,
        )

    else:

        result = drill_down(
            conn,
            hierarchy=hierarchy,
            level=current_level,
            measure=measure,
            filters=filters,
        )


# ============================================================
# CASE 2
#
# Hierarchy + column axis
#
# Query all hierarchy levels and then pivot them.
#
# This allows:
#
# DICE + DRILL-DOWN + PIVOT
#
# simultaneously.
# ============================================================

elif (
    use_hierarchy
    and column_dimension is not None
):

    dimensions = active_row_dimensions.copy()

    if column_dimension not in dimensions:
        dimensions.append(column_dimension)


    raw_result = query(
        conn,
        dimensions=dimensions,
        measure=measure,
        filters=filters,
    )


    result = raw_result.pivot_table(
        index=active_row_dimensions,
        columns=column_dimension,
        values=measure,
        aggfunc="sum",
        fill_value=0,
    )


# ============================================================
# CASE 3
#
# Normal pivot
# ============================================================

elif column_dimension is not None:

    result = pivot_data(
        conn,
        row_dimension=row_dimension,
        column_dimension=column_dimension,
        measure=measure,
        filters=filters,
    )


# ============================================================
# CASE 4
#
# One-dimensional result.
#
# Explicitly dispatch SLICE / DICE / ordinary query.
# ============================================================

else:

    if filter_operation == "SLICE":

        filter_dimension = next(
            iter(filters)
        )

        filter_value = filters[
            filter_dimension
        ][0]


        result = slice_data(
            conn,
            dimension=filter_dimension,
            value=filter_value,
            group_by=[row_dimension],
            measure=measure,
        )


    elif filter_operation == "DICE":

        result = dice_data(
            conn,
            filters=filters,
            group_by=[row_dimension],
            measure=measure,
        )


    else:

        result = query(
            conn,
            dimensions=[row_dimension],
            measure=measure,
            order_by_measure=True,
        )


st.dataframe(
    result,
    use_container_width=True,
)


if column_dimension is None:

    if use_hierarchy:

        chart_dimension = hierarchy[
            st.session_state.hierarchy_level
        ]

    else:

        chart_dimension = row_dimension


    # Time-based dimensions make more sense as lines.
    if chart_dimension in {
        "year",
        "quarter",
        "month",
        "day",
    }:

        st.line_chart(
            result,
            x=chart_dimension,
            y=measure,
        )

    else:

        st.bar_chart(
            result,
            x=chart_dimension,
            y=measure,
        )