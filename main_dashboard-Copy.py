import streamlit as st
import pandas as pd
from pathlib import Path
import altair as alt
import json


st.title("🚗 Maker Fuel Dashboard")


# ============================================================
# FILE PATHS
# ============================================================

file_path = Path(
    "Combined_maker_fuel.xlsx"
)

geojson_path = Path(
    "india.geojson"
)


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
        "Excel file not found."
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


maker_col = "Maker"
state_col = "State"
fuel_col = "Fuel"


# ============================================================
# FIND MONTH COLUMNS
# ============================================================

date_info = []


for col in df.columns:

    if col in [
        maker_col,
        state_col,
        fuel_col
    ]:
        continue

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
# DATE FILTERS
# ============================================================



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
#-


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
# SEPARATE MONTHLY BAR CHART FOR EACH MAKER
# ============================================================

st.subheader("Maker-wise Monthly Values")


# Get list of Makers
maker_list = (
    maker_monthly_long[maker_col]
    .dropna()
    .unique()
    .tolist()
)


# ============================================================
# CREATE ONE BAR CHART FOR EACH MAKER
# ============================================================

for maker in maker_list:

    # Take data only for current Maker
    single_maker_df = maker_monthly_long[
        maker_monthly_long[maker_col] == maker
    ].copy()


    # Display Maker name
    st.markdown(
        "### " + str(maker)
    )


    # Create chart
    single_maker_bar = (
        alt.Chart(
            single_maker_df
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
        single_maker_bar,
        use_container_width=True
    )

st.caption(
    "These Maker-wise charts use the complete dataset "
    "and are not affected by dashboard filters."
)

#-



#-
# ============================================================
# MAKER MARKET SHARE - DONUT CHART
# Uses From Date and To Date only
# ============================================================

st.subheader("Maker Market Share")


# ============================================================
# CREATE SEPARATE DATA COPY
# ============================================================

market_share_columns = [
    maker_col
] + selected_date_columns


market_share_df = df[
    market_share_columns
].copy()


# ============================================================
# CLEAN MAKER NAME
# ============================================================

market_share_df[maker_col] = (
    market_share_df[maker_col]
    .astype(str)
    .str.strip()
)


# Remove blank Maker rows

market_share_df = market_share_df[
    market_share_df[maker_col].ne("")
    & market_share_df[maker_col].ne("nan")
].copy()


# ============================================================
# CONVERT SELECTED MONTHS TO NUMERIC
# Original df is NOT changed
# ============================================================

for col in selected_date_columns:

    market_share_df[col] = pd.to_numeric(
        market_share_df[col],
        errors="coerce"
    )


# ============================================================
# TOTAL VALUE FOR SELECTED PERIOD
# ============================================================

market_share_df["Selected_Period_Total"] = (
    market_share_df[selected_date_columns]
    .sum(
        axis=1,
        skipna=True
    )
)


# ============================================================
# TOTAL BY MAKER
# ============================================================

maker_market_share = (
    market_share_df
    .groupby(
        maker_col,
        as_index=False
    )["Selected_Period_Total"]
    .sum()
)


# Remove zero values

maker_market_share = maker_market_share[
    maker_market_share["Selected_Period_Total"] > 0
].copy()


# ============================================================
# CALCULATE MARKET SHARE
# ============================================================

overall_total = (
    maker_market_share["Selected_Period_Total"]
    .sum()
)


if overall_total > 0:

    maker_market_share["Market_Share"] = (
        maker_market_share["Selected_Period_Total"]
        / overall_total
        * 100
    )


    # ========================================================
    # SORT FROM HIGHEST TO LOWEST MARKET SHARE
    # ========================================================

    maker_market_share = (
        maker_market_share
        .sort_values(
            "Market_Share",
            ascending=False
        )
        .reset_index(drop=True)
    )


    # ========================================================
    # DONUT CHART
    # ========================================================

    market_share_donut = (
        alt.Chart(
            maker_market_share
        )
        .mark_arc(
            innerRadius=90,
            outerRadius=160
        )
        .encode(

            theta=alt.Theta(
                "Selected_Period_Total:Q"
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
                    "Selected_Period_Total:Q",
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
        market_share_donut,
        use_container_width=True
    )


else:

    st.info(
        "No data available for the selected date range."
    )


st.caption(
    "Market share for "
    + date_labels[from_date]
    + " to "
    + date_labels[to_date]
)
#-





#-
# ============================================================
# INDIA STATE / UT CHOROPLETH
# ============================================================

st.subheader("State-wise Geographic Analysis")





# ============================================================
# CREATE MAP FILTER
# State filter is intentionally NOT applied
# ============================================================

map_mask = pd.Series(
    True,
    index=df.index
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
        "Orissa",

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
                with st.expander("Check GeoJSON State Names"):


                    for state in sorted(geo_state_names):

                        st.write(state)

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