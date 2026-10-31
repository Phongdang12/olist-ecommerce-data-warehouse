import streamlit as st

st.set_page_config(
    page_title="Olist Data Warehouse",
    page_icon="📊",
    layout="wide"
)

dashboard_page = st.Page(
    "pages/dashboard.py",
    title="Dashboard"
)

olap_page = st.Page(
    "pages/interactive_board.py",
    title="OLAP Explorer"
)

navigation = st.navigation([
    dashboard_page,
    olap_page
])

navigation.run()