import pandas as pd
import plotly.express as px

# ===========================
# READ FILE
# ===========================

file_path = "Combined_maker_fuel.xlsx"  # change to your file

df = pd.read_excel(file_path)

# ===========================
# REMOVE MAKER DIMENSION
# ===========================

month_cols = [col for col in df.columns
              if col not in ["Maker", "Fuel", "State"]]

# Sum across makers
df_agg = (
    df.groupby(["Fuel", "State"])[month_cols]
      .sum()
      .reset_index()
)

# ===========================
# CONVERT WIDE TO LONG
# ===========================

long_df = df_agg.melt(
    id_vars=["Fuel", "State"],
    value_vars=month_cols,
    var_name="Month",
    value_name="Sales"
)

# ===========================
# CALCULATE PERCENT SHARE
# ===========================

long_df["Total"] = (
    long_df.groupby(["State", "Month"])["Sales"]
           .transform("sum")
)

long_df["Share"] = (
    long_df["Sales"] /
    long_df["Total"]
) * 100

# remove zero-total months
long_df = long_df[long_df["Total"] > 0]

# ===========================
# 100% STACKED CHART
# ===========================

fig = px.bar(
    long_df,
    x="Month",
    y="Share",
    color="Fuel",
    animation_frame="State",
    title="Fuel Mix by State (100% Stacked)",
)

fig.update_layout(
    barmode="stack",
    yaxis_title="Fuel Share (%)",
    xaxis_title="Month",
    yaxis=dict(range=[0, 100]),
    height=700,
    width=1400,
)

fig.show()