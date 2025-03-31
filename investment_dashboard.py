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
        raw_df = pd.read_excel(uploaded_file, skiprows=2)

        rename_map = {
            "Account Name": "Investment Name",
            "Total Investment": "Cost",
            "Share of Valuation": "Fair Value",
            "Valuation Date": "Date"
        }

        df = raw_df.rename(columns=rename_map)
        df = df[["Investment Name", "Cost", "Fair Value", "Date"]].copy()

        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df["Cost"] = pd.to_numeric(df["Cost"], errors='coerce')
        df["Fair Value"] = pd.to_numeric(df["Fair Value"], errors='coerce')
        df.dropna(subset=["Investment Name", "Cost", "Fair Value", "Date"], inplace=True)

        df["MOIC"] = df["Fair Value"] / df["Cost"]

        def calculate_irr(row):
            try:
                days_held = (datetime.today() - row["Date"]).days
                if days_held <= 0:
                    return np.nan
                years = days_held / 365.25
                cashflows = [-row["Cost"]] + [row["Fair Value"]]
                dates = [0, years]
                return npf.irr(cashflows)
            except:
                return np.nan

        df["IRR"] = df.apply(calculate_irr, axis=1) * 100

        total_cost = df["Cost"].sum()
        total_fair_value = df["Fair Value"].sum()
        portfolio_moic = total_fair_value / total_cost if total_cost != 0 else np.nan

        irr_cashflows = []
        irr_dates = []
        for _, row in df.iterrows():
            irr_cashflows.append((-row["Cost"], row["Date"]))
        irr_cashflows.append((total_fair_value, datetime.today()))
        try:
            sorted_flows = sorted(irr_cashflows, key=lambda x: x[1])
            amounts = [x[0] for x in sorted_flows]
            days = [(x[1] - sorted_flows[0][1]).days / 365.25 for x in sorted_flows]
            portfolio_irr = npf.irr(amounts) * 100 if len(amounts) > 1 else np.nan
        except:
            portfolio_irr = np.nan

        st.markdown("###")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${total_cost:,.0f}")
        col2.metric("Total Fair Value", f"${total_fair_value:,.0f}")
        col3.metric("Portfolio MOIC", f"{portfolio_moic:.2f}")
        col4.metric("Estimated IRR", f"{portfolio_irr:.1f}%")

        st.markdown("### IRR by Investment")
        st.dataframe(df[["Investment Name", "IRR", "Cost", "Fair Value", "Date"]].sort_values("IRR", ascending=False))

        fig = px.histogram(df, x="IRR", nbins=25, title="Distribution of IRRs")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Export")
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
