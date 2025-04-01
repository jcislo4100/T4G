import streamlit as st
import pandas as pd
import numpy as np
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

        # Date Range Filter
        min_date = df["Date"].min()
        max_date = df["Date"].max()
        start_date, end_date = st.slider("Filter by Investment Date", min_value=min_date, max_value=max_date, value=(min_date, max_date))
        df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

        # ROI Horizon Selector
        roi_horizon = st.selectbox("Select ROI Horizon", ["Since Inception", "1 Year", "3 Years", "5 Years"])
        today = pd.Timestamp.today()

        def calculate_annualized_roi(row):
            cost = row["Cost"]
            fair_value = row["Fair Value"]
            if roi_horizon == "Since Inception":
                days = (today - row["Date"]).days
            else:
                years = int(roi_horizon.split()[0])
                days = min((today - row["Date"]).days, years * 365)
            if days <= 0:
                return np.nan
            roi = (fair_value - cost) / cost
            return roi / (days / 365.25)

        # MOIC and ROI Calculations
        df["MOIC"] = df["Fair Value"] / df["Cost"]
        df["ROI"] = (df["Fair Value"] - df["Cost"]) / df["Cost"]
        df["Holding Years"] = (today - df["Date"]).dt.days / 365.25
        df["Annualized ROI"] = df.apply(calculate_annualized_roi, axis=1)

        # Portfolio Summary Metrics
        total_invested = df["Cost"].sum()
        total_fair_value = df["Fair Value"].sum()
        portfolio_moic = total_fair_value / total_invested if total_invested != 0 else 0
        portfolio_roi = (total_fair_value - total_invested) / total_invested
        weighted_avg_holding = (df["Holding Years"] * df["Cost"]).sum() / total_invested
        portfolio_annualized_roi = portfolio_roi / weighted_avg_holding if weighted_avg_holding > 0 else 0

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
        col4.metric("Annualized ROI", f"{portfolio_annualized_roi:.1%}" if not np.isnan(portfolio_annualized_roi) else "N/A")

        # MOIC Chart by Fund
        st.subheader("📊 Portfolio MOIC by Fund")
        moic_by_fund = df.groupby("Fund Name").apply(lambda x: x["Fair Value"].sum() / x["Cost"].sum()).reset_index(name="Portfolio MOIC")
        fig1 = px.bar(moic_by_fund, x="Fund Name", y="Portfolio MOIC", title="MOIC per Fund")
        st.plotly_chart(fig1, use_container_width=True)

        # Annualized ROI Chart by Fund
        st.subheader("📈 Annualized ROI by Fund")
        roi_by_fund = df.groupby("Fund Name").apply(
            lambda x: ((x["Fair Value"].sum() - x["Cost"].sum()) / x["Cost"].sum()) / ((x["Holding Years"] * x["Cost"]).sum() / x["Cost"].sum())
        ).reset_index(name="Annualized ROI")
        fig2 = px.bar(roi_by_fund, x="Fund Name", y="Annualized ROI", title="Annualized ROI per Fund")
        st.plotly_chart(fig2, use_container_width=True)

        # Pie Chart: Capital Allocation by Fund
        st.subheader("💰 Capital Allocation by Fund")
        cap_chart = df.groupby("Fund Name")["Cost"].sum().reset_index()
        fig3 = px.pie(cap_chart, names="Fund Name", values="Cost", title="Capital Invested per Fund")
        st.plotly_chart(fig3, use_container_width=True)

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

        # Highlight underperformers
        def highlight_low(val):
            return "background-color: #ffe6e6" if isinstance(val, float) and val < 0 else ""

        # Display Table
        st.markdown("---")
        st.subheader("🔢 Investment Table")
        st.dataframe(
            df_filtered[["Investment Name", "Fund Name", "Cost", "Fair Value", "MOIC", "ROI", "Annualized ROI"]]
            .style.applymap(highlight_low, subset=["ROI", "Annualized ROI"])
