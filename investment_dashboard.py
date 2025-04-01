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

        # Calculate Portfolio-level Metrics
        total_invested = df["Cost"].sum()
        total_fair_value = df["Fair Value"].sum()
        portfolio_moic = total_fair_value / total_invested

        # IRR calculations per investment (using cash flow: -Cost, +FairValue today)
        def compute_irr(row):
            try:
                cash_flows = [-row["Cost"]]
                days_held = (datetime.today() - row["Date"]).days
                years_held = days_held / 365.0
                cash_flows += [0] * int(np.floor(years_held - 1))  # padding if held > 1 year
                cash_flows.append(row["Fair Value"])
                return npf.irr(cash_flows)
            except:
                return np.nan

        df["IRR"] = df.apply(compute_irr, axis=1)
        portfolio_cash_flows = []
        for _, row in df.iterrows():
            portfolio_cash_flows.append((row["Date"], -row["Cost"]))
        portfolio_cash_flows.append((datetime.today(), df["Fair Value"].sum()))
        portfolio_cash_flows.sort()

        cf_dates, cf_values = zip(*portfolio_cash_flows)
        cf_days = [(d - cf_dates[0]).days / 365.0 for d in cf_dates]
        irr_guess = 0.1

        def xnpv(rate, values, times):
            return sum([val / (1 + rate) ** t for val, t in zip(values, times)])

        def xirr(values, times):
            from scipy.optimize import newton
            return newton(lambda r: xnpv(r, values, times), irr_guess)

        try:
            portfolio_irr = xirr(cf_values, cf_days)
        except:
            portfolio_irr = np.nan

        # Display KPIs
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Amount Invested", f"${total_invested:,.0f}")
        kpi2.metric("Total Fair Value", f"${total_fair_value:,.0f}")
        kpi3.metric("Portfolio MOIC", f"{portfolio_moic:.2f}")
        kpi4.metric("Estimated IRR", f"{portfolio_irr:.1%}" if pd.notna(portfolio_irr) else "N/A")

        st.markdown("---")
        st.subheader("Top 10 Investments by Fair Value")
        top_fv = df.sort_values("Fair Value", ascending=False).head(10)
        st.dataframe(top_fv[["Investment Name", "Fair Value", "MOIC", "IRR"]])

        st.markdown("---")
        st.subheader("MOIC Distribution")
        fig_moic = px.histogram(df, x="MOIC", nbins=30, title="Distribution of MOIC across Investments")
        st.plotly_chart(fig_moic, use_container_width=True)

        st.markdown("---")
        st.subheader("IRR by Investment")
        fig_irr = px.histogram(df.dropna(subset=["IRR"]), x="IRR", nbins=30, title="Distribution of IRRs")
        st.plotly_chart(fig_irr, use_container_width=True)

        st.markdown("---")
        st.subheader("Full Investment Table")
        st.dataframe(df)

        st.download_button(
            label="Download Portfolio Data as CSV",
            data=df.to_csv(index=False),
            file_name="investment_dashboard_output.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error loading file: {e}")
