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
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0)

        column_mapping = {
            "Account Name": "Investment Name",
            "Total Investment": "Cost",
            "Share of Valuation": "Fair Value",
            "Valuation Date": "Date",
            "Parent Account": "Fund Name"
        }

        df.rename(columns=column_mapping, inplace=True)

        required_columns = ["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]
        if not all(col in df.columns for col in required_columns):
            raise ValueError("Missing required columns in the uploaded file.")

        df = df[required_columns]

        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df.dropna(subset=["Date", "Cost", "Fair Value"], inplace=True)

        df["MOIC"] = df["Fair Value"] / df["Cost"]

        # Portfolio Metrics
        total_cost = df["Cost"].sum()
        total_fv = df["Fair Value"].sum()
        portfolio_moic = total_fv / total_cost if total_cost else 0

        cashflows = []
        for _, row in df.iterrows():
            cashflows.append((row["Date"], -row["Cost"]))
        latest_date = df["Date"].max()
        cashflows.append((latest_date, total_fv))

        cashflows.sort(key=lambda x: x[0])
        cashflow_values = [cf[1] for cf in cashflows]

        irr = npf.irr(cashflow_values)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${total_cost:,.0f}")
        col2.metric("Total Fair Value", f"${total_fv:,.0f}")
        col3.metric("Portfolio MOIC", f"{portfolio_moic:.2f}")
        col4.metric("Estimated IRR", f"{irr*100:.2f}%" if irr is not None else "N/A")

        st.markdown("---")
        st.subheader("📊 Portfolio Overview")
        st.dataframe(df)

        st.markdown("---")
        st.subheader("📌 Top 5 Investments by MOIC")
        top_moic = df.sort_values(by="MOIC", ascending=False).head(5)
        st.dataframe(top_moic[["Investment Name", "MOIC", "Fair Value"]])

        st.markdown(f"**Investments below 1.0x MOIC:** {df[df['MOIC'] < 1.0].shape[0]} ({(df[df['MOIC'] < 1.0].shape[0]/df.shape[0])*100:.1f}%)")
        unrealized_pct = df[df["Fair Value"] > df["Cost"]].shape[0] / df.shape[0]
        avg_holding_period = (datetime.today() - df["Date"]).dt.days.mean() / 365
        st.markdown(f"**% of Unrealized Investments:** {unrealized_pct:.1%}")
        st.markdown(f"**Avg. Holding Period:** {avg_holding_period:.2f} years")

        st.markdown("---")
        st.subheader("⬇️ Export")
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download Portfolio Table as CSV",
            data=csv_buffer.getvalue(),
            file_name="portfolio_summary.csv",
            mime="text/csv"
        )

        st.markdown("---")
        st.subheader("📉 MOIC Distribution")
        fig = px.histogram(df, x="MOIC", nbins=10, title="Distribution of MOIC across Investments")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading file: {e}")
