import streamlit as st
import pandas as pd
from pathlib import Path
from io import BytesIO
import altair as alt
import json

# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="Maker Fuel Dashboard",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Maker Fuel Dashboard")


# ============================================================
# FILE PATH
# ============================================================

file_path = Path(
    "Combined_maker_fuel.xlsx"
)
geojson_path = Path(
    "india.geojson"
)


# ============================================================
# LOAD EXCEL
# IMPORTANT:
# The original dataframe is NOT changed anywhere.
# ============================================================

@st.cache_data
def load_data(path, modified_time):
    return pd.read_excel(
        path,
        engine="openpyxl"
    )


if not file_path.exists():
    st.error(
        f"File not found:\n\n{file_path}\n\n"
        "Please check the location of Combined_maker_fuel.xlsx."
    )
    st.stop()


try:
    # modified_time makes Streamlit reload if Excel file changes
    modified_time = file_path.stat().st_mtime

    df = load_data(
        str(file_path),
        modified_time
    )

except Exception as e:
    st.error(f"Unable to read Excel file: {e}")
    st.stop()


# ============================================================
# CLEAN COLUMN NAMES ONLY
# This does NOT touch the actual data values
# ============================================================

df.columns = [
    str(col).strip()
    for col in df.columns
]


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required_columns = [
    "Maker",
    "State",
    "Fuel"
]

missing_columns = [
    col
    for col in required_columns
    if col not in df.columns
]

if missing_columns:
    st.error(
        "These required columns were not found:\n\n"
        + ", ".join(missing_columns)
    )

    st.write("Columns found in Excel:")
    st.write(list(df.columns))

    st.stop()


# ============================================================
# USE COLUMN NAMES, NOT COLUMN POSITIONS
# ============================================================

maker_col = "Maker"
state_col = "State"
fuel_col = "Fuel"


# ============================================================
# FIND DATE COLUMNS
#
# Your date columns are expected to be like:
# 2018-Jan
# 2018-Feb
# ...
# 2026-Oct
#
# We identify them by whether pandas can parse the header
# as a date.
# ============================================================

date_info = []

for col in df.columns:

    if col in [maker_col, state_col, fuel_col]:
        continue

    parsed_date = pd.to_datetime(
        str(col),
        format="%Y-%b",
        errors="coerce"
    )

    if pd.notna(parsed_date):
        date_info.append(
            (col, parsed_date)
        )


if len(date_info) == 0:
    st.error(
        "No monthly date columns were found."
    )
    st.stop()


# ============================================================
# SORT DATES CHRONOLOGICALLY
# ============================================================

date_info = sorted(
    date_info,
    key=lambda x: x[1]
)

date_columns = [
    item[0]
    for item in date_info
]


# Nice display labels
# Example:
# 2026-Jul remains 2026-Jul
# ============================================================

date_labels = {
    original: parsed.strftime("%Y-%b")
    for original, parsed in date_info
}


# ============================================================
# HELPER FUNCTION
# Makes unique non-blank dropdown values
# ============================================================

def dropdown_values(series):

    values = (
        series
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[
        values != ""
    ]

    return sorted(
        values.unique().tolist()
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Filters")


# ============================================================
# MAKER FILTER
# ============================================================

maker_options = (
    ["All"]
    + dropdown_values(df[maker_col])
)

selected_maker = st.sidebar.selectbox(
    "Maker",
    maker_options,
    key="maker_filter"
)


# ============================================================
# CREATE TEMP FILTER ONLY FOR DROPDOWN OPTIONS
#
# Source df remains untouched.
# ============================================================

dropdown_df = df.copy()


if selected_maker != "All":

    dropdown_df = dropdown_df[
        dropdown_df[maker_col]
        .astype(str)
        .str.strip()
        .eq(selected_maker)
    ]


# ============================================================
# STATE FILTER
# ============================================================

state_options = (
    ["All"]
    + dropdown_values(
        dropdown_df[state_col]
    )
)

selected_state = st.sidebar.selectbox(
    "State",
    state_options,
    key="state_filter"
)


if selected_state != "All":

    dropdown_df = dropdown_df[
        dropdown_df[state_col]
        .astype(str)
        .str.strip()
        .eq(selected_state)
    ]


# ============================================================
# FUEL FILTER
# ============================================================

fuel_options = (
    ["All"]
    + dropdown_values(
        dropdown_df[fuel_col]
    )
)

selected_fuel = st.sidebar.selectbox(
    "Fuel",
    fuel_options,
    key="fuel_filter"
)


# ============================================================
# DATE FILTERS
# ============================================================

st.sidebar.divider()

st.sidebar.subheader(
    "Date Range"
)


from_date = st.sidebar.selectbox(
    "From Date",
    date_columns,
    index=0,
    format_func=lambda x: date_labels[x],
    key="from_date"
)


to_date = st.sidebar.selectbox(
    "To Date",
    date_columns,
    index=len(date_columns) - 1,
    format_func=lambda x: date_labels[x],
    key="to_date"
)


# ============================================================
# VALIDATE DATE RANGE
# ============================================================

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
# APPLY FINAL FILTER
#
# VERY IMPORTANT:
#
# We filter rows from ORIGINAL df.
#
# No numerical conversion
# No groupby
# No pivot
# No aggregation
# No fillna
#
# This preserves original Excel values.
# ============================================================

mask = pd.Series(
    True,
    index=df.index
)


if selected_maker != "All":

    mask &= (
        df[maker_col]
        .astype(str)
        .str.strip()
        .eq(selected_maker)
    )


if selected_state != "All":

    mask &= (
        df[state_col]
        .astype(str)
        .str.strip()
        .eq(selected_state)
    )


if selected_fuel != "All":

    mask &= (
        df[fuel_col]
        .astype(str)
        .str.strip()
        .eq(selected_fuel)
    )


# ============================================================
# DOWNLOAD DATAFRAME
#
# This comes DIRECTLY from original df.
# Values are NOT changed.
# ============================================================

download_df = df.loc[
    mask,
    [
        maker_col,
        state_col,
        fuel_col,
        *selected_date_columns
    ]
].copy()


# Reset index affects only row numbering.
# It does NOT modify data.
download_df.reset_index(
    drop=True,
    inplace=True
)


# ============================================================
# DISPLAY SELECTED FILTERS
# ============================================================

st.subheader(
    "Selected Filters"
)


c1, c2, c3, c4, c5 = st.columns(5)


c1.metric(
    "Maker",
    selected_maker
)

c2.metric(
    "State",
    selected_state
)

c3.metric(
    "Fuel",
    selected_fuel
)

c4.metric(
    "From Date",
    date_labels[from_date]
)

c5.metric(
    "To Date",
    date_labels[to_date]
)


st.divider()


# ============================================================
# SHOW NUMBER OF MATCHING ROWS
# ============================================================

st.metric(
    "Matching Rows",
    f"{len(download_df):,}"
)


# ============================================================
# IMPORTANT:
# CREATE A SEPARATE COPY FOR CALCULATIONS
#
# download_df is NEVER modified.
# ============================================================

calc_df = download_df.copy()


for col in selected_date_columns:

    calc_df[col] = pd.to_numeric(
        calc_df[col],
        errors="coerce"
    )


# ============================================================
# MONTH-WISE TOTAL
# ============================================================

monthly_total = (
    calc_df[selected_date_columns]
    .sum(
        axis=0,
        skipna=True
    )
)


# ============================================================
# GRAND TOTAL
# ============================================================

grand_total = monthly_total.sum()


st.metric(
    "Total for Selected Period",
    f"{grand_total:,.0f}"
)


# ============================================================
# PREPARE CHART DATA
# ============================================================

chart_df = pd.DataFrame({
    "Sort_Date": [
        pd.to_datetime(col, format="%Y-%b")
        for col in selected_date_columns
    ],

    "Month-Year": [
        date_labels[col]
        for col in selected_date_columns
    ],

    "Value": [
        monthly_total[col]
        for col in selected_date_columns
    ]
})

# TRUE CHRONOLOGICAL SORT
chart_df = (
    chart_df
    .sort_values("Sort_Date")
    .reset_index(drop=True)
)

# Explicit chronological order for chart axis
month_order = chart_df["Month-Year"].tolist()


#-
# ============================================================
# MAKER-WISE MONTHLY TREND AND BAR CHART
# NO FILTERS ARE APPLIED TO THIS SECTION
# ============================================================

st.divider()

st.subheader("Maker-wise Monthly Analysis")


# ============================================================
# CREATE COLUMN LIST
# ============================================================

maker_monthly_columns = [maker_col] + selected_date_columns


# ============================================================
# CREATE SEPARATE COPY
# ============================================================

maker_monthly_df = df[
    maker_monthly_columns
].copy()


# ============================================================
# CLEAN MAKER NAMES
# ============================================================

maker_monthly_df[maker_col] = (
    maker_monthly_df[maker_col]
    .astype(str)
    .str.strip()
)


# Remove blank Maker rows

maker_monthly_df = maker_monthly_df[
    maker_monthly_df[maker_col].ne("")
    & maker_monthly_df[maker_col].ne("nan")
].copy()


# ============================================================
# CONVERT MONTH VALUES TO NUMERIC
# ORIGINAL df IS NOT CHANGED
# ============================================================

for col in selected_date_columns:

    maker_monthly_df[col] = pd.to_numeric(
        maker_monthly_df[col],
        errors="coerce"
    )


# ============================================================
# MONTHLY TOTAL BY MAKER
# ============================================================

maker_monthly_summary = (
    maker_monthly_df
    .groupby(
        maker_col,
        as_index=False
    )[selected_date_columns]
    .sum()
)


# ============================================================
# CONVERT TO LONG FORMAT
# ============================================================

maker_monthly_long = (
    maker_monthly_summary
    .melt(
        id_vars=[maker_col],
        value_vars=selected_date_columns,
        var_name="Month_Column",
        value_name="Value"
    )
)


# ============================================================
# CREATE ACTUAL DATE FOR CORRECT SORTING
# ============================================================

maker_monthly_long["Sort_Date"] = pd.to_datetime(
    maker_monthly_long["Month_Column"],
    format="%Y-%b",
    errors="coerce"
)


maker_monthly_long["Month-Year"] = (
    maker_monthly_long["Sort_Date"]
    .dt.strftime("%Y-%b")
)


# ============================================================
# SORT CORRECTLY
# ============================================================

maker_monthly_long = (
    maker_monthly_long
    .sort_values(
        [
            maker_col,
            "Sort_Date"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# CORRECT MONTH ORDER
# ============================================================

all_month_order = []

for col in selected_date_columns:

    all_month_order.append(
        date_labels[col]
    )


# ============================================================
# MAKER-WISE TREND CHART
# ============================================================

st.markdown("### Maker-wise Month Trend")


maker_trend_chart = (
    alt.Chart(
        maker_monthly_long
    )
    .mark_line(
        point=True
    )
    .encode(

        x=alt.X(
            "Month-Year:N",
            sort=all_month_order,
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
            "Maker:N",
            title="Maker"
        ),

        tooltip=[
            alt.Tooltip(
                "Maker:N",
                title="Maker"
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
    maker_trend_chart,
    use_container_width=True
)


# ============================================================
# MAKER-WISE BAR CHART
# ============================================================

st.markdown("### Maker-wise Month Values")


maker_bar_chart = (
    alt.Chart(
        maker_monthly_long
    )
    .mark_bar()
    .encode(

        x=alt.X(
            "Month-Year:N",
            sort=all_month_order,
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
            "Maker:N",
            title="Maker"
        ),

        xOffset=alt.XOffset(
            "Maker:N"
        ),

        tooltip=[
            alt.Tooltip(
                "Maker:N",
                title="Maker"
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
    maker_bar_chart,
    use_container_width=True
)


st.caption(
    "These Maker-wise charts use the complete dataset "
    "and are not affected by dashboard filters."
)
#-


# ============================================================
# LINE CHART
# ============================================================

st.subheader("Month-wise Trend")

line_chart = (
    alt.Chart(chart_df)
    .mark_line(point=True)
    .encode(
        x=alt.X(
            "Month-Year:N",
            sort=month_order,
            title="Month"
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
                format=","
            )
        ]
    )
)

st.altair_chart(
    line_chart,
    use_container_width=True
)


# ============================================================
# BAR CHART
# ============================================================

st.subheader("Month-wise Values")

bar_chart = (
    alt.Chart(chart_df)
    .mark_bar()
    .encode(
        x=alt.X(
            "Month-Year:N",
            sort=month_order,
            title="Month"
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
                format=","
            )
        ]
    )
)

st.altair_chart(
    bar_chart,
    use_container_width=True
)





#-
# ============================================================
# MAKER-WISE FUEL MIX - 100% STACKED BAR
#
# Uses ONLY:
# 1. From Date
# 2. To Date
# 3. State filter
#
# Maker filter is intentionally ignored.
# Fuel filter is intentionally ignored.
# ============================================================

st.subheader("Maker-wise Fuel Mix (%)")


# ============================================================
# CREATE SEPARATE FILTER FOR FUEL MIX
# ============================================================

fuel_mix_mask = pd.Series(
    True,
    index=df.index
)


# Apply State filter only
if selected_state != "All":

    fuel_mix_mask &= (
        df[state_col]
        .astype(str)
        .str.strip()
        .eq(selected_state)
    )


# ============================================================
# TAKE REQUIRED DATA
# ============================================================

fuel_mix_df = df.loc[
    fuel_mix_mask,
    [
        maker_col,
        fuel_col,
        *selected_date_columns
    ]
].copy()


# Clean Maker and Fuel names
fuel_mix_df[maker_col] = (
    fuel_mix_df[maker_col]
    .astype(str)
    .str.strip()
)

fuel_mix_df[fuel_col] = (
    fuel_mix_df[fuel_col]
    .astype(str)
    .str.strip()
)


# Remove blank / invalid Maker and Fuel rows
fuel_mix_df = fuel_mix_df[
    fuel_mix_df[maker_col].ne("")
    & fuel_mix_df[fuel_col].ne("")
    & fuel_mix_df[maker_col].ne("nan")
    & fuel_mix_df[fuel_col].ne("nan")
].copy()


# ============================================================
# CONVERT SELECTED MONTHS TO NUMERIC
#
# Original df is NOT changed.
# ============================================================

for col in selected_date_columns:

    fuel_mix_df[col] = pd.to_numeric(
        fuel_mix_df[col],
        errors="coerce"
    )


# ============================================================
# TOTAL SALES FOR EACH ROW FOR SELECTED DATE RANGE
# ============================================================

fuel_mix_df["Fuel_Value"] = (
    fuel_mix_df[selected_date_columns]
    .sum(
        axis=1,
        skipna=True
    )
)


# ============================================================
# SUM BY MAKER + FUEL
# ============================================================

fuel_mix_summary = (
    fuel_mix_df
    .groupby(
        [maker_col, fuel_col],
        as_index=False
    )["Fuel_Value"]
    .sum()
)


# ============================================================
# REMOVE ZERO VALUES
# ============================================================

fuel_mix_summary = fuel_mix_summary[
    fuel_mix_summary["Fuel_Value"] > 0
].copy()


# ============================================================
# CALCULATE TOTAL FOR EACH MAKER
# ============================================================

fuel_mix_summary["Maker_Total"] = (
    fuel_mix_summary
    .groupby(maker_col)["Fuel_Value"]
    .transform("sum")
)


# ============================================================
# CALCULATE FUEL MIX %
# ============================================================

fuel_mix_summary["Fuel_Mix_Percent"] = (
    fuel_mix_summary["Fuel_Value"]
    / fuel_mix_summary["Maker_Total"]
    * 100
)


# ============================================================
# SORT MAKERS BY TOTAL VOLUME
# Largest maker appears first
# ============================================================

maker_order = (
    fuel_mix_summary[
        [maker_col, "Maker_Total"]
    ]
    .drop_duplicates()
    .sort_values(
        "Maker_Total",
        ascending=False
    )[maker_col]
    .tolist()
)


# ============================================================
# CREATE 100% STACKED BAR CHART
# ============================================================

if fuel_mix_summary.empty:

    st.info(
        "No data available for the selected "
        "State and date range."
    )

else:

    fuel_mix_chart = (
        alt.Chart(fuel_mix_summary)
        .mark_bar()
        .encode(

            x=alt.X(
                f"{maker_col}:N",
                sort=maker_order,
                title="Maker",
                axis=alt.Axis(
                    labelAngle=-45
                )
            ),

            y=alt.Y(
                "Fuel_Mix_Percent:Q",
                title="Fuel Mix (%)",
                scale=alt.Scale(
                    domain=[0, 100]
                ),
                axis=alt.Axis(
                    format=".0f"
                )
            ),

            color=alt.Color(
                f"{fuel_col}:N",
                title="Fuel"
            ),

            order=alt.Order(
                f"{fuel_col}:N"
            ),

            tooltip=[
                alt.Tooltip(
                    f"{maker_col}:N",
                    title="Maker"
                ),

                alt.Tooltip(
                    f"{fuel_col}:N",
                    title="Fuel"
                ),

                alt.Tooltip(
                    "Fuel_Value:Q",
                    title="Volume",
                    format=",.0f"
                ),

                alt.Tooltip(
                    "Fuel_Mix_Percent:Q",
                    title="Fuel Mix",
                    format=".1f"
                )
            ]
        )
        .properties(
            height=500
        )
    )

    st.altair_chart(
        fuel_mix_chart,
        use_container_width=True
    )

    st.caption(
        "Each Maker represents 100% of its total volume. "
        "Fuel mix is calculated for "
        + date_labels[from_date]
        + " to "
        + date_labels[to_date]
        + " | State: "
        + selected_state
    )

#-



#-
# ============================================================
# INDIA STATE / UT CHOROPLETH
# ============================================================

st.subheader("State-wise Geographic Analysis")


# GeoJSON file location
geojson_path = Path(
    r"C:\Users\866083\OneDrive - Maruti Suzuki India Limited\Desktop\india.geojson"
)


# ============================================================
# CREATE MAP FILTER
# State filter is intentionally NOT applied
# ============================================================

map_mask = pd.Series(
    True,
    index=df.index
)


# Apply Maker filter
if selected_maker != "All":

    map_mask = map_mask & (
        df[maker_col]
        .astype(str)
        .str.strip()
        .eq(selected_maker)
    )


# Apply Fuel filter
if selected_fuel != "All":

    map_mask = map_mask & (
        df[fuel_col]
        .astype(str)
        .str.strip()
        .eq(selected_fuel)
    )


# ============================================================
# SELECT COLUMNS FOR MAP
# ============================================================

map_columns = [
    maker_col,
    state_col,
    fuel_col
]

map_columns = map_columns + selected_date_columns


map_df = df.loc[
    map_mask,
    map_columns
].copy()


# ============================================================
# CONVERT MONTH VALUES TO NUMERIC
# Original dataframe is NOT changed
# ============================================================

for col in selected_date_columns:

    map_df[col] = pd.to_numeric(
        map_df[col],
        errors="coerce"
    )


# ============================================================
# CALCULATE TOTAL FOR SELECTED DATE RANGE
# ============================================================

map_df["Map_Value"] = (
    map_df[selected_date_columns]
    .sum(
        axis=1,
        skipna=True
    )
)


# ============================================================
# TOTAL BY STATE
# ============================================================

state_map_data = (
    map_df
    .groupby(
        state_col,
        as_index=False
    )["Map_Value"]
    .sum()
)


# ============================================================
# CLEAN STATE NAMES
# ============================================================

state_map_data[state_col] = (
    state_map_data[state_col]
    .astype(str)
    .str.strip()
)


# ============================================================
# STATE NAME CORRECTIONS
# These help Excel names match GeoJSON names
# ============================================================

state_name_mapping = {

    "Andaman & Nicobar Island":
        "Andaman and Nicobar Islands",

    "Andaman & Nicobar Islands":
        "Andaman and Nicobar Islands",

    "Jammu & Kashmir":
        "Jammu and Kashmir",

    "UT of DNH and DD":
        "Dadra and Nagar Haveli and Daman and Diu",

    "Dadra & Nagar Haveli and Daman & Diu":
        "Dadra and Nagar Haveli and Daman and Diu",

    "NCT of Delhi":
        "Delhi",

    "Orissa":
        "Odisha",

    "Pondicherry":
        "Puducherry",

    "Uttaranchal":
        "Uttarakhand"
}


state_map_data["Map_State"] = (
    state_map_data[state_col]
    .replace(state_name_mapping)
)


# ============================================================
# CHECK GEOJSON FILE
# ============================================================

if not geojson_path.exists():

    st.warning(
        "India GeoJSON file was not found."
    )

    st.write(
        "Expected location:"
    )

    st.code(
        str(geojson_path)
    )


else:

    try:

        # ====================================================
        # LOAD GEOJSON
        # ====================================================

        with open(
            geojson_path,
            "r",
            encoding="utf-8"
        ) as file:

            india_geojson = json.load(file)


        features = india_geojson.get(
            "features",
            []
        )


        # ====================================================
        # CHECK GEOJSON
        # ====================================================

        if len(features) == 0:

            st.error(
                "No State/UT boundaries were found "
                "inside the GeoJSON file."
            )


        else:

            # =================================================
            # FIND STATE NAME FIELD
            # =================================================

            first_properties = features[0].get(
                "properties",
                {}
            )


            possible_name_fields = [
                "ST_NM",
                "st_nm",
                "STATE",
                "State",
                "state",
                "NAME_1",
                "NAME",
                "Name",
                "name"
            ]


            geo_state_field = None


            for field in possible_name_fields:

                if field in first_properties:

                    geo_state_field = field

                    break


            # =================================================
            # STATE NAME FIELD NOT FOUND
            # =================================================

            if geo_state_field is None:

                st.error(
                    "Could not identify the State name "
                    "field in the GeoJSON."
                )


                st.write(
                    "Fields available in your GeoJSON:"
                )


                st.write(
                    list(
                        first_properties.keys()
                    )
                )


            else:

                # =============================================
                # CREATE VALUE LOOKUP
                # =============================================

                state_value_lookup = dict(
                    zip(
                        state_map_data["Map_State"],
                        state_map_data["Map_Value"]
                    )
                )


                # =============================================
                # ADD VALUES TO GEOJSON
                # =============================================

                for feature in features:

                    properties = feature.get(
                        "properties",
                        {}
                    )


                    geo_state_name = str(
                        properties.get(
                            geo_state_field,
                            ""
                        )
                    ).strip()


                    value = state_value_lookup.get(
                        geo_state_name,
                        0
                    )


                    properties["Dashboard_Value"] = value

                    properties["Display_State"] = geo_state_name


                # =============================================
                # FIND UNMATCHED STATES
                # =============================================

                geo_state_names = set()


                for feature in features:

                    properties = feature.get(
                        "properties",
                        {}
                    )


                    geo_name = str(
                        properties.get(
                            geo_state_field,
                            ""
                        )
                    ).strip()


                    if geo_name != "":

                        geo_state_names.add(
                            geo_name
                        )


                excel_state_names = set(
                    state_map_data[
                        "Map_State"
                    ].dropna()
                )


                unmatched_states = (
                    excel_state_names
                    .difference(
                        geo_state_names
                    )
                )


                unmatched_states = sorted(
                    unmatched_states
                )


                # =============================================
                # CREATE MAP DATA
                # =============================================

                geo_data = alt.Data(
                    values=features
                )


                # =============================================
                # CREATE CHOROPLETH
                # =============================================

                india_map = (
                    alt.Chart(
                        geo_data
                    )
                    .mark_geoshape(
                        stroke="white",
                        strokeWidth=0.7
                    )
                    .encode(

                        color=alt.Color(
                            "properties.Dashboard_Value:Q",
                            title="Value",
                            scale=alt.Scale(
                                scheme="blues"
                            )
                        ),

                        tooltip=[

                            alt.Tooltip(
                                "properties.Display_State:N",
                                title="State / UT"
                            ),

                            alt.Tooltip(
                                "properties.Dashboard_Value:Q",
                                title="Value",
                                format=","
                            )
                        ]
                    )
                    .project(
                        type="mercator"
                    )
                    .properties(
                        height=650
                    )
                )


                # =============================================
                # DISPLAY MAP
                # =============================================

                st.altair_chart(
                    india_map,
                    use_container_width=True
                )


                # =============================================
                # DESCRIPTION
                # =============================================

                st.caption(
                    "Map shows State/UT totals from "
                    + date_labels[from_date]
                    + " to "
                    + date_labels[to_date]
                    + ". The State filter is ignored for "
                    + "this map so all States/UTs can be compared."
                )


                # =============================================
                # SHOW UNMATCHED STATES
                # =============================================

                if len(unmatched_states) > 0:

                    with st.expander(
                        "States not matched with map"
                    ):

                        st.write(
                            "The following State/UT names "
                            "could not be matched:"
                        )


                        for state in unmatched_states:

                            st.write(state)


    except Exception as e:

        st.error(
            "Unable to create India map: "
            + str(e)
        )

#-



# ============================================================
# FILTERED DATA PREVIEW
#
# Preview uses original values.
# ============================================================

st.subheader(
    "Filtered Data"
)

st.dataframe(
    download_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# CREATE EXCEL DOWNLOAD
#
# Again:
# download_df contains original source values.
# ============================================================

def create_excel_download(dataframe):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        dataframe.to_excel(
            writer,
            index=False,
            sheet_name="Filtered Data"
        )

    output.seek(0)

    return output.getvalue()


excel_data = create_excel_download(
    download_df
)


# ============================================================
# DOWNLOAD BUTTON
# ============================================================

st.download_button(
    label="⬇️ Download Filtered Data",
    data=excel_data,
    file_name="Filtered_Maker_Fuel_Data.xlsx",
    mime=(
        "application/vnd.openxmlformats-"
        "officedocument.spreadsheetml.sheet"
    ),
    key="download_filtered_data"
)


# ============================================================
# FOOTER INFORMATION
# ============================================================

st.caption(
    f"Showing {len(download_df):,} rows | "
    f"{len(selected_date_columns)} months selected"
)
