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

        # MOIC Calculation
        df["MOIC"] = df["Fair Value"] / df["Cost"]

        # IRR Calculation Per Investment
        def calc_irr(row):
            try:
                dates = [row["Date"], pd.Timestamp.today()]
                cash_flows = [-row["Cost"], row["Fair Value"]]
                return npf.xirr(dict(zip(dates, cash_flows)))
            except Exception:
                return np.nan

        df["IRR"] = df.apply(calc_irr, axis=1)

        # Portfolio Summary Metrics
        total_invested = df["Cost"].sum()
        total_fair_value = df["Fair Value"].sum()
        portfolio_moic = total_fair_value / total_invested if total_invested != 0 else 0

        all_cashflows = []
        for _, row in df.iterrows():
            all_cashflows.append((row["Date"], -row["Cost"]))
            all_cashflows.append((pd.Timestamp.today(), row["Fair Value"]))

        cashflow_series = pd.DataFrame(all_cashflows, columns=["date", "amount"]).groupby("date").sum().sort_index()
        try:
            portfolio_irr = npf.xirr(cashflow_series["amount"].to_dict())
        except Exception:
            portfolio_irr = np.nan

        # Fund Filter
        funds = ["All"] + sorted(df["Fund Name"].dropna().unique())
        selected_fund = st.selectbox("Select Fund", funds)
        df_filtered = df.copy()
        if selected_fund != "All":
            df_filtered = df[df["Fund Name"] == selected_fund]

        # Summary Metrics Display
        st.markdown("### Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${total_invested:,.0f}")
        col2.metric("Total Fair Value", f"${total_fair_value:,.0f}")
        col3.metric("Portfolio MOIC", f"{portfolio_moic:.2f}")
        col4.metric("Estimated IRR", f"{portfolio_irr:.1%}" if not np.isnan(portfolio_irr) else "N/A")

        # MOIC Chart by Fund
        st.subheader("📊 Portfolio MOIC by Fund")
        moic_by_fund = df.groupby("Fund Name").apply(lambda x: x["Fair Value"].sum() / x["Cost"].sum()).reset_index(name="Portfolio MOIC")
        fig1 = px.bar(moic_by_fund, x="Fund Name", y="Portfolio MOIC", title="MOIC per Fund")
        st.plotly_chart(fig1, use_container_width=True)

        # IRR Chart by Fund
        st.subheader("📈 Portfolio IRR by Fund")
        irr_rows = []
        for fund in df["Fund Name"].unique():
            fdf = df[df["Fund Name"] == fund]
            fund_cashflows = []
            for _, row in fdf.iterrows():
                fund_cashflows.append((row["Date"], -row["Cost"]))
                fund_cashflows.append((pd.Timestamp.today(), row["Fair Value"]))
            cf_series = pd.DataFrame(fund_cashflows, columns=["date", "amount"]).groupby("date").sum().sort_index()
            try:
                irr_val = npf.xirr(cf_series["amount"].to_dict())
                irr_rows.append((fund, irr_val))
            except:
                irr_rows.append((fund, np.nan))

        irr_df = pd.DataFrame(irr_rows, columns=["Fund Name", "Portfolio IRR"]).dropna()
        fig2 = px.bar(irr_df, x="Fund Name", y="Portfolio IRR", title="IRR per Fund")
        st.plotly_chart(fig2, use_container_width=True)

        # Export CSV Button
        st.markdown("### ⬇️ Export")
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download Portfolio Table as CSV",
            data=csv_buffer.getvalue(),
            file_name="portfolio_summary.csv",
            mime="text/csv"
        )

        # Display Table
        st.markdown("---")
        st.subheader("🔢 Investment Table")
        st.dataframe(df_filtered[["Investment Name", "Fund Name", "Cost", "Fair Value", "MOIC", "IRR"]]
