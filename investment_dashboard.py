import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
from datetime import datetime
import io

st.set_page_config(layout="wide")
st.title("📈 Investment Performance Dashboard")

uploaded_file = st.file_uploader("Upload Investment Excel", type="xlsx")

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, header=1)

        # Rename for consistency
        df = df.rename(columns={
            "Account Name": "Investment Name",
            "Total Investment": "Cost",
            "Share of Valuation": "Fair Value",
            "Valuation Date": "Date",
            "Parent Account": "Fund Name"
        })

        df = df[["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]]
        df = df.dropna(subset=["Investment Name", "Cost", "Fair Value", "Date"])

        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df = df.dropna(subset=["Date"])

        df["MOIC"] = df["Fair Value"] / df["Cost"]

        # Portfolio-level metrics
        total_invested = df["Cost"].sum()
        total_fair_value = df["Fair Value"].sum()
        portfolio_moic = total_fair_value / total_invested if total_invested else 0

        # Portfolio IRR Calculation
        cashflows = []
        today = datetime.today()
        for _, row in df.iterrows():
            cashflows.append((row["Date"], -row["Cost"]))
        cashflows.append((today, total_fair_value))

        cf_dates, cf_amounts = zip(*sorted(cashflows))
        days = [(d - cf_dates[0]).days for d in cf_dates]
        try:
            irr = np.irr(cf_amounts)
            irr_annualized = (1 + irr) ** 365 - 1 if irr is not None else None
        except:
            irr_annualized = None

        st.markdown("### 📊 Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${total_invested:,.0f}")
        col2.metric("Total Fair Value", f"${total_fair_value:,.0f}")
        col3.metric("Portfolio MOIC", f"{portfolio_moic:.2f}")
        col4.metric("Estimated IRR", f"{irr_annualized:.1%}" if irr_annualized is not None else "N/A")

        # MOIC Distribution
        st.markdown("### 📈 MOIC Distribution")
        fig = px.histogram(df, x="MOIC", nbins=20, title="Distribution of MOIC across Investments")
        st.plotly_chart(fig, use_container_width=True)

        # IRR by Investment
        st.markdown("### 📉 IRR by Investment")
        def compute_individual_irr(row):
            try:
                cfs = [(-row["Cost"], row["Date"]), (row["Fair Value"], today)]
                dates, amounts = zip(*cfs)
                delta_days = [(d - dates[0]).days for d in dates]
                return (1 + np.irr(amounts)) ** 365 - 1
            except:
                return None

        df["IRR"] = df.apply(compute_individual_irr, axis=1)
        st.dataframe(df[["Investment Name", "Cost", "Fair Value", "Date", "MOIC", "IRR"]].sort_values(by="IRR", ascending=False))

        # Export
        st.markdown("### 📥 Export")
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download Portfolio Table as CSV",
            data=csv_buffer.getvalue(),
            file_name="portfolio_summary.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error loading file: {e}")
