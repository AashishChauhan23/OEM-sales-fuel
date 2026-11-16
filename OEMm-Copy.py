import streamlit as st

st.set_page_config(
    page_title="Maker Fuel Dashboard",
    page_icon="🚗",
    layout="wide"
)

main_page = st.Page(
    "main_dashboard-Copy.py",
    title="Registrations",
    icon="📊",
    default=True
)

fuel_page = st.Page(
    "fuel_analysis-Copy.py",
    title="Fuel Analysis",
    icon="⛽"
)

more_page = st.Page(
    "more_analysis-Copy.py",
    title="More Analysis",
    icon="🔍"
)

state_stacked = st.Page(
    "state_stacked.py",
    title="State fuel mix Analysis",
    icon="🔍"
)



navigation = st.navigation(
    [
        main_page,
        fuel_page,
        more_page,
        state-stacked
    ],
    position="top"
)

navigation.run()
