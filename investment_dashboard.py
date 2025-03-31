# IRR and MOIC Calculator Prototype using Streamlit

import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
from datetime import datetime
import io

st.set_page_config(layout="wide")
st.title("📈 Investment Performance Dashboard")

uploaded_file = st.file_uploader("Upload Investment Excel", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, engine="openpyxl")

    # Auto-map known Salesforce column names to dashboard field names
    column_mapping = {
        "Account Name": "Investment Name",
        "Total Investment": "Cost",
        "Share of Valuation": "Fair Value",
        "Valuation Date": "Date",
        "Parent Account": "Fund Name"
    }

    df.rename(columns=column_mapping, inplace=True)

    # Clean column names
    df.columns = df.columns.str.strip()

    # Check for required columns
    required_cols = ["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]
    if not all(col in df.columns for col in required_cols):
        st.error(f"Error loading file: File must contain the columns: {required_cols}")
        st.stop()

    # Preprocessing
    df = df.dropna(subset=["Cost", "Fair Value"])
    df["MOIC"] = df["Fair Value"] / df["Cost"]

    try:
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df = df.dropna(subset=["Date"])
        df["Years"] = (datetime.today() - df["Date"]).dt.days / 365.25
        df["IRR"] = df.apply(lambda row: npf.irr([-row["Cost"], row["Fair Value"]]) if row["Years"] > 0 else np.nan, axis=1)
    except Exception as e:
        st.warning("IRR calculation failed. Check date formatting.")

    # KPI Metrics
    total_cost = df["Cost"].sum()
    total_fair_value = df["Fair Value"].sum()
    portfolio_moic = total_fair_value / total_cost if total_cost > 0 else 0
    irr_values = df["IRR"].dropna()
    portfolio_irr = npf.irr([-total_cost] + [total_fair_value]) if total_cost > 0 else np.nan

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Amount Invested", f"${total_cost:,.0f}")
    col2.metric("Total Fair Value", f"${total_fair_value:,.0f}")
    col3.metric("Portfolio MOIC", f"{portfolio_moic:.2f}")
    col4.metric("Estimated IRR", f"{portfolio_irr:.0%}" if not np.isnan(portfolio_irr) else "n/a")

    # MOIC Distribution
    st.subheader("📊 MOIC Breakdown by Fund")
    moic_by_fund = df.groupby("Fund Name")["MOIC"].mean().sort_values(ascending=False).reset_index()
    st.plotly_chart(px.bar(moic_by_fund, x="Fund Name", y="MOIC", title="Average MOIC by Fund"))

    # Downloadable CSV
    st.markdown("---")
    st.subheader("⬇️ Export")
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button("Download Portfolio Table as CSV", data=csv_buffer.getvalue(), file_name="portfolio_summary.csv", mime="text/csv")
