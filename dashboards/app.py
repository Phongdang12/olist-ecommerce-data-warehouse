import streamlit as st

st.set_page_config(
    page_title="Olist Data Warehouse",
    page_icon="📊",
    layout="wide"
)

dashboard_page = st.Page("pages/dashboard.py", title="Dashboard", icon="📊")
olap_page = st.Page("pages/interactive_board.py", title="OLAP Explorer", icon="🔎")
dss_page = st.Page("pages/dss.py", title="DSS Dashboard", icon="🧠")

navigation = st.navigation([dashboard_page, olap_page, dss_page])
navigation.run()
