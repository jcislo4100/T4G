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

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    required_columns = ["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]
    if not all(col in df.columns for col in required_columns):
        st.error("Missing required columns in uploaded file. Please ensure headers match expected structure.")
    else:
        df = df.dropna(subset=["Cost", "Fair Value", "Date"])
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df = df.dropna(subset=["Date"])

        # Compute MOIC
        df["MOIC"] = df["Fair Value"] / df["Cost"]

        # Compute IRR per investment using xirr
        def calc_irr(row):
            try:
                cash_flows = {
                    row["Date"]: -row["Cost"],
                    pd.Timestamp.today(): row["Fair Value"]
                }
                return npf.xirr(cash_flows)
            except:
                return np.nan

        df["IRR"] = df.apply(calc_irr, axis=1)

        # Portfolio Metrics
        total_invested = df["Cost"].sum()
        total_fair_value = df["Fair Value"].sum()
        portfolio_moic = total_fair_value / total_invested if total_invested != 0 else 0

        # Portfolio-level IRR (aggregate cashflows)
        all_cashflows = []
        for _, row in df.iterrows():
            all_cashflows.append((row["Date"], -row["Cost"]))
            all_cashflows.append((pd.Timestamp.today(), row["Fair Value"]))

        cashflow_series = pd.DataFrame(all_cashflows, columns=["date", "amount"]).groupby("date").sum().sort_index()

        try:
            portfolio_irr = npf.xirr(cashflow_series["amount"].to_dict())
        except:
            portfolio_irr = np.nan

        # Fund Filter
        funds = ["All"] + sorted(df["Fund Name"].dropna().unique())
        selected_fund = st.selectbox("Select Fund", funds)
        if selected_fund != "All":
            df = df[df["Fund Name"] == selected_fund]

        # Summary
        st.markdown("### Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${total_invested:,.0f}")
        col2.metric("Total Fair Value", f"${total_fair_value:,.0f}")
        col3.metric("Portfolio MOIC", f"{portfolio_moic:.2f}")
        col4.metric("Estimated IRR", f"{portfolio_irr:.1%}" if not np.isnan(portfolio_irr) else "N/A")

        # MOIC by Fund Chart
        st.subheader("📊 Portfolio MOIC by Fund")
        moic_by_fund = df.groupby("Fund Name").apply(lambda x: x["Fair Value"].sum() / x["Cost"].sum()).reset_index(name="Portfolio MOIC")
        fig1 = px.bar(moic_by_fund, x="Fund Name", y="Portfolio MOIC", title="MOIC per Fund")
        st.plotly_chart(fig1, use_container_width=True)

        # IRR by Fund Chart (aggregated IRR based on cashflows)
        st.subheader("📈 Portfolio IRR by Fund")
        irr_data = []
        for fund in df["Fund Name"].unique():
            fdf = df[df["Fund Name"] == fund]
            cashflows = []
            for _, row in fdf.iterrows():
                cashflows.append((row["Date"], -row["Cost"]))
                cashflows.append((pd.Timestamp.today(), row["Fair Value"]))
            series = pd.DataFrame(cashflows, columns=["date", "amount"]).groupby("date").sum().sort_index()
            try:
                irr_val = npf.xirr(series["amount"].to_dict())
                irr_data.append((fund, irr_val))
            except:
                irr_data.append((fund, np.nan))

        irr_df = pd.DataFrame(irr_data, columns=["Fund Name", "Portfolio IRR"]).dropna()
        fig2 = px.bar(irr_df, x="Fund Name", y="Portfolio IRR", title="IRR per Fund")
        st.plotly_chart(fig2, use_container_width=True)

        # Investment Table
        st.markdown("---")
        st.subheader("🧮 Investment Table")
        st.dataframe(df[["Investment Name", "Fund Name", "Cost", "Fair Value", "MOIC", "IRR"]])
