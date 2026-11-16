import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("State-wise Fuel Mix (100% Stacked)")

# ------------------
# LOAD DATA
# ------------------

FILE_PATH = "Combined_maker_fuel.xlsx"   # change filename

df = pd.read_excel(FILE_PATH)

# ------------------
# FIND MONTH COLUMNS
# ------------------

meta_cols = ["Maker", "Fuel", "State"]

month_cols = [col for col in df.columns if col not in meta_cols]

# ------------------
# STATE SELECTION
# ------------------

states = sorted(df["State"].dropna().unique())

selected_state = st.selectbox(
    "Select State",
    states
)

# ------------------
# FILTER STATE
# ------------------

state_df = df[df["State"] == selected_state].copy()

# ------------------
# IGNORE MAKER
# ------------------

agg_df = (
    state_df
    .groupby("Fuel")[month_cols]
    .sum()
    .reset_index()
)

# ------------------
# WIDE TO LONG
# ------------------

long_df = agg_df.melt(
    id_vars="Fuel",
    value_vars=month_cols,
    var_name="Month",
    value_name="Sales"
)

# ------------------
# REMOVE ZERO TOTAL MONTHS
# ------------------

monthly_total = (
    long_df.groupby("Month")["Sales"]
    .transform("sum")
)

long_df = long_df[monthly_total > 0]

# ------------------
# CALCULATE SHARE
# ------------------

long_df["Share"] = (
    long_df.groupby("Month")["Sales"]
    .transform(lambda x: (x / x.sum()) * 100)
)

# ------------------
# SORT MONTHS
# ------------------

try:
    long_df["MonthSort"] = pd.to_datetime(
        long_df["Month"],
        format="%Y-%b"
    )

    long_df = long_df.sort_values("MonthSort")

except Exception:
    pass

# ------------------
# CHART
# ------------------

fig = px.bar(
    long_df,
    x="Month",
    y="Share",
    color="Fuel",
    title=f"Fuel Mix (%) - {selected_state}",
    labels={
        "Share": "Share (%)",
        "Month": "Month"
    }
)

fig.update_layout(
    barmode="stack",
    height=700,
    legend_title="Fuel Type"
)

fig.update_yaxes(
    range=[0, 100],
    ticksuffix="%"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ------------------
# OPTIONAL DATA TABLE
# ------------------

with st.expander("View Data"):
    pivot_table = (
        long_df.pivot(
            index="Month",
            columns="Fuel",
            values="Share"
        )
        .fillna(0)
        .round(2)
    )

    st.dataframe(
        pivot_table,
        use_container_width=True
    )
