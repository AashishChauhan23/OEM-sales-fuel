import streamlit as st
import pandas as pd
from pathlib import Path
import altair as alt


st.title("⛽ Fuel Analysis")


# ============================================================
# FILE PATH
# ============================================================

file_path = Path("Combined_maker_fuel.xlsx")


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data(path, modified_time):

    return pd.read_excel(
        path,
        engine="openpyxl"
    )


if not file_path.exists():

    st.error(
        "Combined_maker_fuel.xlsx was not found."
    )

    st.stop()


modified_time = file_path.stat().st_mtime

df = load_data(
    str(file_path),
    modified_time
)


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

df.columns = [
    str(col).strip()
    for col in df.columns
]


fuel_col = "Fuel"
maker_col = "Maker"


# ============================================================
# CHECK FUEL COLUMN
# ============================================================

if fuel_col not in df.columns:

    st.error(
        "Fuel column was not found in the Excel file."
    )

    st.stop()


# ============================================================
# FIND DATE COLUMNS
# Expected format:
# 2018-Jan
# 2018-Feb
# ...
# ============================================================

date_info = []


for col in df.columns:

    parsed_date = pd.to_datetime(
        str(col),
        format="%Y-%b",
        errors="coerce"
    )

    if pd.notna(parsed_date):

        date_info.append(
            (
                col,
                parsed_date
            )
        )


if len(date_info) == 0:

    st.error(
        "No monthly date columns were found."
    )

    st.stop()


# ============================================================
# SORT MONTHS CHRONOLOGICALLY
# ============================================================

date_info = sorted(
    date_info,
    key=lambda x: x[1]
)


date_columns = [
    item[0]
    for item in date_info
]


date_labels = {
    original: parsed.strftime("%Y-%b")
    for original, parsed in date_info
}


#-
# ============================================================
# STICKY DATE FILTERS
# ============================================================

date_filter_container = st.container()


with date_filter_container:

    # Marker used to identify this container
    st.markdown(
        '<div class="sticky-date-marker"></div>',
        unsafe_allow_html=True
    )

    date_c1, date_c2 = st.columns(2)


    with date_c1:

        from_date = st.selectbox(
            "From Date",
            date_columns,
            index=0,
            format_func=lambda x: date_labels[x],
            key="main_from_date"
        )


    with date_c2:

        to_date = st.selectbox(
            "To Date",
            date_columns,
            index=len(date_columns) - 1,
            format_func=lambda x: date_labels[x],
            key="main_to_date"
        )


# ============================================================
# MAKE DATE FILTER CONTAINER STICKY
# ============================================================

st.markdown(
    """
    <style>

    div[data-testid="stVerticalBlock"]
    div:has(div.sticky-date-marker) {
        position: sticky;
        top: 3.5rem;
        background: white;
        z-index: 999;
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #dddddd;
    }

    .sticky-date-marker {
        display: none;
    }

    </style>
    """,
    unsafe_allow_html=True
)
#-




# ============================================================
# VALIDATE DATE RANGE
# ============================================================
# ============================================================
# MAKER FILTER
# Nothing selected = All Makers
# ============================================================

maker_list = sorted(
    df[maker_col]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
    .tolist()
)

selected_makers = st.multiselect(
    "Maker",
    maker_list,
    default=[],
    placeholder="All Makers"
)

from_index = date_columns.index(
    from_date
)

to_index = date_columns.index(
    to_date
)


if from_index > to_index:

    st.error(
        "From Date cannot be later than To Date."
    )

    st.stop()


selected_date_columns = date_columns[
    from_index:to_index + 1
]


# ============================================================
# CREATE CALCULATION COPY
# Original df remains unchanged
# ============================================================

fuel_columns = [
    maker_col,
    fuel_col
] + selected_date_columns


fuel_df = df[
    fuel_columns
].copy()


# ============================================================
# APPLY MAKER FILTER
# If nothing selected, keep all Makers
# ============================================================

fuel_df[maker_col] = (
    fuel_df[maker_col]
    .astype(str)
    .str.strip()
)

if selected_makers:
    fuel_df = fuel_df[
        fuel_df[maker_col].isin(selected_makers)
    ].copy()


# ============================================================
# CLEAN FUEL VALUES
# ============================================================

fuel_df[fuel_col] = (
    fuel_df[fuel_col]
    .astype(str)
    .str.strip()
)


fuel_df = fuel_df[
    fuel_df[fuel_col].ne("")
    & fuel_df[fuel_col].ne("nan")
].copy()


# ============================================================
# CONVERT MONTH VALUES TO NUMERIC
# ============================================================

for col in selected_date_columns:

    fuel_df[col] = pd.to_numeric(
        fuel_df[col],
        errors="coerce"
    )


# ============================================================
# MONTH-WISE TOTAL BY FUEL
# ============================================================

fuel_summary = (
    fuel_df
    .groupby(
        fuel_col,
        as_index=False
    )[selected_date_columns]
    .sum()
)


# ============================================================
# CONVERT TO LONG FORMAT
# ============================================================

fuel_long = (
    fuel_summary
    .melt(
        id_vars=[fuel_col],
        value_vars=selected_date_columns,
        var_name="Month_Column",
        value_name="Value"
    )
)


# ============================================================
# CREATE REAL DATE FOR SORTING
# ============================================================

fuel_long["Sort_Date"] = pd.to_datetime(
    fuel_long["Month_Column"],
    format="%Y-%b",
    errors="coerce"
)


fuel_long["Month-Year"] = (
    fuel_long["Sort_Date"]
    .dt.strftime("%Y-%b")
)


fuel_long = (
    fuel_long
    .sort_values(
        [
            fuel_col,
            "Sort_Date"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# MONTH ORDER
# ============================================================

month_order = []


for col in selected_date_columns:

    month_order.append(
        date_labels[col]
    )


# ============================================================
# GET LIST OF FUELS
# ============================================================

fuel_list = (
    fuel_long[fuel_col]
    .dropna()
    .unique()
    .tolist()
)



#-
# ============================================================
# ONE LINE CHART WITH ALL FUELS
# ============================================================

st.divider()

st.subheader("Fuel-wise Monthly Trend")


fuel_line_chart = (
    alt.Chart(
        fuel_long
    )
    .mark_line(
        point=True
    )
    .encode(

        x=alt.X(
            "Month-Year:N",
            sort=month_order,
            title="Month",
            axis=alt.Axis(
                labelAngle=-45
            )
        ),

        y=alt.Y(
            "Value:Q",
            title="Value"
        ),

        color=alt.Color(
            "Fuel:N",
            title="Fuel"
        ),

        tooltip=[
            alt.Tooltip(
                "Fuel:N",
                title="Fuel"
            ),

            alt.Tooltip(
                "Month-Year:N",
                title="Month"
            ),

            alt.Tooltip(
                "Value:Q",
                title="Value",
                format=",.0f"
            )
        ]
    )
    .properties(
        height=500
    )
)


st.altair_chart(
    fuel_line_chart,
    use_container_width=True
)




#-
# ============================================================
# FUEL-WISE MARKET SHARE DONUT CHART
# Linked to From Date and To Date
# ============================================================

st.divider()

st.subheader("Fuel-wise Market Share")


# ============================================================
# TOTAL SELECTED PERIOD BY FUEL
# ============================================================

fuel_market_share = (
    fuel_long
    .groupby(
        fuel_col,
        as_index=False
    )["Value"]
    .sum()
)


# Remove zero values
fuel_market_share = fuel_market_share[
    fuel_market_share["Value"] > 0
].copy()


# ============================================================
# CALCULATE TOTAL MARKET
# ============================================================

total_market = (
    fuel_market_share["Value"]
    .sum()
)


# ============================================================
# CALCULATE FUEL SHARE
# ============================================================

if total_market > 0:

    fuel_market_share["Market_Share"] = (
        fuel_market_share["Value"]
        / total_market
        * 100
    )


    # Sort highest to lowest
    fuel_market_share = (
        fuel_market_share
        .sort_values(
            "Market_Share",
            ascending=False
        )
        .reset_index(drop=True)
    )


    # ========================================================
    # CREATE DONUT CHART
    # ========================================================

    fuel_donut_chart = (
        alt.Chart(
            fuel_market_share
        )
        .mark_arc(
            innerRadius=90,
            outerRadius=160
        )
        .encode(

            theta=alt.Theta(
                "Value:Q"
            ),

            color=alt.Color(
                "Fuel:N",
                title="Fuel"
            ),

            tooltip=[
                alt.Tooltip(
                    "Fuel:N",
                    title="Fuel"
                ),

                alt.Tooltip(
                    "Value:Q",
                    title="Volume",
                    format=",.0f"
                ),

                alt.Tooltip(
                    "Market_Share:Q",
                    title="Market Share (%)",
                    format=".1f"
                )
            ]
        )
        .properties(
            height=400
        )
    )


    st.altair_chart(
        fuel_donut_chart,
        use_container_width=True
    )


    st.caption(
        "Fuel market share from "
        + date_labels[from_date]
        + " to "
        + date_labels[to_date]
    )


else:

    st.info(
        "No data available for the selected date range."
    )
#-





# ============================================================
# SEPARATE BAR CHART FOR EACH FUEL
# ============================================================

st.divider()

st.subheader("Fuel-wise Monthly Values")


for fuel in fuel_list:

    # Data for one Fuel
    single_fuel_df = fuel_long[
        fuel_long[fuel_col] == fuel
    ].copy()


    # Fuel name
    st.markdown(
        "### " + str(fuel)
    )


    # ========================================================
    # BAR CHART
    # ========================================================

    fuel_bar_chart = (
        alt.Chart(
            single_fuel_df
        )
        .mark_bar()
        .encode(

            x=alt.X(
                "Month-Year:N",
                sort=month_order,
                title="Month",
                axis=alt.Axis(
                    labelAngle=-45
                )
            ),

            y=alt.Y(
                "Value:Q",
                title="Value"
            ),

            tooltip=[
                alt.Tooltip(
                    "Month-Year:N",
                    title="Month"
                ),

                alt.Tooltip(
                    "Value:Q",
                    title="Value",
                    format=",.0f"
                )
            ]
        )
        .properties(
            height=400
        )
    )


    st.altair_chart(
        fuel_bar_chart,
        use_container_width=True
    )


# ============================================================
# FOOTER
# ============================================================

st.caption(
    "Fuel-wise analysis from "
    + date_labels[from_date]
    + " to "
    + date_labels[to_date]
)
#-