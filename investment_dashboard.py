import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
from datetime import datetime
import io

st.set_page_config(layout="wide")
st.title("📈 Investment Performance Dashboard")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload Investment Excel", type=["xlsx"])

if uploaded_file:
    df_raw = pd.read_excel(uploaded_file, sheet_name=0)

    # --- Column Auto-Mapping ---
    column_map = {
        "Investment Name": ["Account Name", "Company", "Investment"],
        "Cost": ["Total Investment", "Amount Invested"],
        "Fair Value": ["Share of Valuation", "Fair Value"],
        "Date": ["Valuation Date", "Investment Date"],
        "Fund Name": ["Parent Account", "Fund"]
    }

    mapped_cols = {}
    for std_col, options in column_map.items():
        for opt in options:
            if opt in df_raw.columns:
                mapped_cols[std_col] = opt
                break

    required_cols = ["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]
    if all(col in mapped_cols for col in required_cols):
        df = df_raw[[mapped_cols[col] for col in required_cols]].copy()
        df.columns = required_cols

        # --- Preprocessing ---
        df = df.dropna(subset=["Cost", "Fair Value"])
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce")
        df["Fair Value"] = pd.to_numeric(df["Fair Value"], errors="coerce")
        df = df.dropna()

        # --- MOIC ---
        df["MOIC"] = df["Fair Value"] / df["Cost"]

        # --- IRR ---
        def calculate_irr(row):
            dates = [row["Date"], datetime.today()]
            cash_flows = [-row["Cost"], row["Fair Value"]]
            try:
                return round(npf.irr(cash_flows) * 100, 2)
            except:
                return np.nan

        df["IRR"] = df.apply(calculate_irr, axis=1)

        # --- Portfolio Stats ---
        total_cost = df["Cost"].sum()
        total_fv = df["Fair Value"].sum()
        portfolio_moic = total_fv / total_cost if total_cost else 0
        try:
            portfolio_irr = npf.irr([-total_cost] + [total_fv]) * 100
        except:
            portfolio_irr = np.nan

        # --- Metrics ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${total_cost:,.0f}")
        col2.metric("Total Fair Value", f"${total_fv:,.0f}")
        col3.metric("Portfolio MOIC", f"{portfolio_moic:.2f}")
        col4.metric("Estimated IRR", f"{portfolio_irr:.2f}%")

        # --- Top & Bottom Investments ---
        st.markdown("### 📊 Top 5 Investments by MOIC")
        st.dataframe(df.sort_values("MOIC", ascending=False).head(5))

        st.markdown("### 🔻 Bottom 5 Investments by MOIC")
        st.dataframe(df.sort_values("MOIC").head(5))

        # --- Fund-Level Analysis ---
        st.markdown("### 🏦 Fund-Level Summary")
        fund_group = df.groupby("Fund Name").agg({
            "Cost": "sum",
            "Fair Value": "sum"
        })
        fund_group["MOIC"] = fund_group["Fair Value"] / fund_group["Cost"]
        st.dataframe(fund_group.reset_index())

        # --- Charts ---
        st.markdown("### 📈 MOIC Distribution")
        st.plotly_chart(px.histogram(df, x="MOIC", nbins=20))

        st.markdown("### 🏢 IRR by Investment")
        st.plotly_chart(px.bar(df, x="Investment Name", y="IRR", color="Fund Name"))

        # --- CSV Export ---
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Full Table as CSV",
            csv,
            "investments.csv",
            "text/csv",
            key='download-csv'
        )
    else:
        st.error("Missing required columns in uploaded file. Please ensure headers match expected structure.")
