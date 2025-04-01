import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
from datetime import datetime
import io

st.set_page_config(layout="wide", page_title="Investment Dashboard", page_icon="📊")
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stDataFrame th { background-color: #f1f1f1; }
    </style>
""", unsafe_allow_html=True)

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

        # Compute ROI and Annualized ROI
        today = pd.Timestamp.today()
        df["ROI"] = (df["Fair Value"] - df["Cost"]) / df["Cost"]
        df["Annualized ROI"] = df.apply(lambda row: (row["ROI"] / ((today - row["Date"]).days / 365.25)) if (today - row["Date"]).days > 0 else np.nan, axis=1)

        # Fund Filter
        funds = ["All"] + sorted(df["Fund Name"].dropna().unique())
        selected_fund = st.selectbox("Select Fund", funds)
        df = df if selected_fund == "All" else df[df["Fund Name"] == selected_fund]

        # Date Range Filter
        min_date = df["Date"].min()
        max_date = df["Date"].max()
        start_date, end_date = st.slider("Filter by Investment Date", min_value=min_date, max_value=max_date, value=(min_date, max_date))
        df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

        # ROI Horizon Filter
        roi_horizon = st.selectbox("Select ROI Horizon", ["Since Inception", "1 Year", "3 Years", "5 Years"])
        def calculate_annualized_roi(row, horizon):
            horizon_days = (today - row["Date"]).days if horizon == "Since Inception" else min((today - row["Date"]).days, int(horizon.split()[0]) * 365)
            if horizon_days <= 0:
                return np.nan
            roi = (row["Fair Value"] - row["Cost"]) / row["Cost"]
            return roi / (horizon_days / 365.25)

        df["Annualized ROI"] = df.apply(lambda row: calculate_annualized_roi(row, roi_horizon), axis=1)

        # Portfolio metrics
        total_invested = df["Cost"].sum()
        total_fair_value = df["Fair Value"].sum()
        portfolio_moic = total_fair_value / total_invested if total_invested != 0 else 0

        try:
            df_cashflows = pd.concat([
                df[["Date", "Cost"]].assign(Cost=lambda x: -x["Cost"]).rename(columns={"Cost": "amount"}),
                pd.DataFrame({"date": [today] * len(df), "amount": df["Fair Value"]})
            ])
            df_cashflows = df_cashflows.groupby("date")["amount"].sum().sort_index()
            portfolio_irr = npf.xirr(df_cashflows.to_dict())
        except:
            portfolio_irr = np.nan

        st.markdown("### 📊 Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${total_invested:,.0f}")
        col2.metric("Total Fair Value", f"${total_fair_value:,.0f}")
        col3.metric("Portfolio MOIC", f"{portfolio_moic:.2f}")
        col4.metric("Estimated IRR", f"{portfolio_irr:.1%}" if not np.isnan(portfolio_irr) else "N/A")

        st.markdown("---")
        st.subheader("📊 Portfolio MOIC by Fund")
        moic_by_fund = df.groupby("Fund Name").apply(lambda x: x["Fair Value"].sum() / x["Cost"].sum()).reset_index(name="Portfolio MOIC")
        fig1 = px.bar(moic_by_fund, x="Fund Name", y="Portfolio MOIC", title="MOIC per Fund", text_auto=True)
        st.plotly_chart(fig1, use_container_width=True)

        st.subheader("📈 Annualized ROI by Fund")
        roi_fund = df.groupby("Fund Name")["Annualized ROI"].mean().reset_index()
        fig2 = px.bar(roi_fund, x="Fund Name", y="Annualized ROI", title="Annualized ROI per Fund", text_auto=".1%")
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("💰 Capital Allocation by Fund")
        pie_df = df.groupby("Fund Name")["Cost"].sum().reset_index()
        fig3 = px.pie(pie_df, names="Fund Name", values="Cost", title="Capital Invested per Fund")
        st.plotly_chart(fig3, use_container_width=True)

        def highlight(val):
            return "background-color: #ffe6e6" if isinstance(val, float) and val < 0 else ""

        st.markdown("### 🧮 Investment Table")
        st.dataframe(df[["Investment Name", "Fund Name", "Cost", "Fair Value", "MOIC", "ROI", "Annualized ROI"]].style.applymap(highlight, subset=["ROI", "Annualized ROI"]))
