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
        # Load Excel file and target the correct sheet
        xl = pd.ExcelFile(uploaded_file)
        sheet_name = [s for s in xl.sheet_names if "Schedule Of Investments" in s][0]
        df = xl.parse(sheet_name)

        # Clean headers
        df.columns = df.columns.str.strip()

        # Filter for rows with required columns
        required_cols = ["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        df = df[required_cols + [col for col in df.columns if col not in required_cols]]
        df = df.dropna(subset=["Investment Name", "Cost", "Fair Value", "Date"])
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df = df.dropna(subset=["Date"])

        # Calculate MOIC
        df["MOIC"] = df["Fair Value"] / df["Cost"]

        # IRR calculations per investment (using cash flow: -Cost, +FairValue today)
        def compute_irr(row):
            try:
                cash_flows = [-row["Cost"], row["Fair Value"]]
                return npf.irr(cash_flows)
            except:
                return np.nan

        df["IRR"] = df.apply(compute_irr, axis=1)

        # Portfolio-level Metrics
        total_invested = df["Cost"].sum()
        total_fair_value = df["Fair Value"].sum()
        portfolio_moic = total_fair_value / total_invested

        try:
            portfolio_irr = npf.irr([-total_invested, total_fair_value])
        except:
            portfolio_irr = np.nan

        # Filter by fund
        fund_list = df["Fund Name"].dropna().unique().tolist()
        selected_funds = st.multiselect("Select Funds to View", fund_list, default=fund_list)
        df_filtered = df[df["Fund Name"].isin(selected_funds)]

        st.markdown("### 📊 Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${df_filtered['Cost'].sum():,.0f}")
        col2.metric("Total Fair Value", f"${df_filtered['Fair Value'].sum():,.0f}")
        col3.metric("Portfolio MOIC", f"{(df_filtered['Fair Value'].sum() / df_filtered['Cost'].sum()):.2f}")
        try:
            irr_filtered = npf.irr([-df_filtered["Cost"].sum(), df_filtered["Fair Value"].sum()])
            col4.metric("Estimated IRR", f"{irr_filtered:.1%}")
        except:
            col4.metric("Estimated IRR", "N/A")

        st.markdown("---")
        st.subheader("Top 10 Investments by Fair Value")
        top_fv = df_filtered.sort_values("Fair Value", ascending=False).head(10)
        st.dataframe(top_fv[["Investment Name", "Fair Value", "MOIC", "IRR"]])

        st.markdown("---")
        st.subheader("MOIC Distribution")
        fig_moic = px.histogram(df_filtered, x="MOIC", nbins=30, title="Distribution of MOIC across Investments")
        st.plotly_chart(fig_moic, use_container_width=True)

        st.markdown("---")
        st.subheader("IRR by Investment")
        fig_irr = px.histogram(df_filtered.dropna(subset=["IRR"]), x="IRR", nbins=30, title="Distribution of IRRs")
        st.plotly_chart(fig_irr, use_container_width=True)

        st.markdown("---")
        st.subheader("Full Investment Table")
        st.dataframe(df_filtered)

        st.download_button(
            label="Download Portfolio Data as CSV",
            data=df_filtered.to_csv(index=False),
            file_name="investment_dashboard_output.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error loading file: {e}")
