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

uploaded_file = st.file_uploader("Upload Investment Excel", type="xlsx")

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip()  # Normalize column headers

        # Required columns
        required_cols = ["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]
        if not all(col in df.columns for col in required_cols):
            st.error("Missing required columns in uploaded file. Please ensure headers match expected structure.")
        else:
            df = df[required_cols].copy()
            df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
            df = df.dropna(subset=["Date", "Cost", "Fair Value"])

            # Portfolio Metrics
            total_invested = df["Cost"].sum()
            total_fair_value = df["Fair Value"].sum()
            moic = total_fair_value / total_invested if total_invested else np.nan

            # IRR Calculation
            df_grouped = df.groupby("Date").agg({"Cost": "sum", "Fair Value": "sum"}).sort_index()
            cash_flows = []
            for date, row in df_grouped.iterrows():
                cash_flows.append((-row["Cost"], date))
            if not df.empty:
                latest_date = df["Date"].max()
                final_value = df[df["Date"] == latest_date]["Fair Value"].sum()
                cash_flows.append((final_value, latest_date))

            cf_series = pd.Series({dt: cf for cf, dt in cash_flows})
            cf_series = cf_series.sort_index()
            try:
                irr = npf.irr(cf_series.values)
                irr_percent = irr * 100 if irr is not None else np.nan
            except:
                irr_percent = np.nan

            # Layout
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Amount Invested", f"${total_invested:,.0f}")
            col2.metric("Total Fair Value", f"${total_fair_value:,.0f}")
            col3.metric("Portfolio MOIC", f"{moic:.2f}")
            col4.metric("Estimated IRR", f"{irr_percent:.1f}%")

            # MOIC by Investment
            df["MOIC"] = df["Fair Value"] / df["Cost"]
            st.subheader("📊 MOIC by Investment")
            st.dataframe(df[["Investment Name", "Cost", "Fair Value", "MOIC"]])

            # Distribution Chart
            st.subheader("📉 MOIC Distribution")
            fig = px.histogram(df, x="MOIC", nbins=20, title="Distribution of MOIC across Investments")
            st.plotly_chart(fig, use_container_width=True)

            # Top Performers
            st.markdown("**Top 5 Investments by MOIC**")
            top_moic = df.sort_values("MOIC", ascending=False).head(5)
            st.dataframe(top_moic[["Investment Name", "MOIC", "Fair Value"]])

            # Bottom Performers
            low_moic = df[df["MOIC"] < 1.0]
            unrealized_pct = low_moic.shape[0] / df.shape[0] * 100
            avg_holding_period = (datetime.today() - df["Date"]).dt.days.mean() / 365

            st.markdown(f"**Investments below 1.0x MOIC:** {low_moic.shape[0]} ({unrealized_pct:.1f}%)")
            st.markdown(f"**Avg. Holding Period:** {avg_holding_period:.2f} years")

            # Export
            st.markdown("---")
            st.subheader("📤 Export")
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
