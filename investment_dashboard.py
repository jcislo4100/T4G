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
        xl = pd.ExcelFile(uploaded_file)
        sheet_name = [s for s in xl.sheet_names if "Schedule Of Investments" in s][0]
        df = xl.parse(sheet_name)
        df.columns = df.columns.str.strip()

        required_cols = ["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        df = df.dropna(subset=required_cols)
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df = df.dropna(subset=["Date"])

        df["MOIC"] = df["Fair Value"] / df["Cost"]

        def compute_irr(row):
            try:
                cash_flows = [-row["Cost"]]
                years_held = (datetime.today() - row["Date"]).days / 365.0
                if years_held <= 0:
                    return np.nan
                cash_flows.append(row["Fair Value"])
                return npf.irr(cash_flows)
            except:
                return np.nan

        df["IRR"] = df.apply(compute_irr, axis=1)

        portfolio_cash_flows = [(row["Date"], -row["Cost"]) for _, row in df.iterrows()]
        portfolio_cash_flows.append((datetime.today(), df["Fair Value"].sum()))
        portfolio_cash_flows.sort()
        cf_dates, cf_values = zip(*portfolio_cash_flows)
        cf_days = [(d - cf_dates[0]).days / 365.0 for d in cf_dates]

        def xnpv(rate, values, times):
            return sum([val / (1 + rate) ** t for val, t in zip(values, times)])

        def xirr(values, times):
            from scipy.optimize import newton
            return newton(lambda r: xnpv(r, values, times), 0.1)

        try:
            portfolio_irr = xirr(cf_values, cf_days)
        except:
            portfolio_irr = np.nan

        total_invested = df["Cost"].sum()
        total_fair_value = df["Fair Value"].sum()
        portfolio_moic = total_fair_value / total_invested

        # --- KPIs ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${total_invested:,.0f}")
        col2.metric("Total Fair Value", f"${total_fair_value:,.0f}")
        col3.metric("Portfolio MOIC", f"{portfolio_moic:.2f}")
        col4.metric("Estimated IRR", f"{portfolio_irr:.1%}" if pd.notna(portfolio_irr) else "N/A")

        # --- Filters ---
        with st.expander("🔎 Filter Data"):
            selected_funds = st.multiselect("Select Fund(s)", options=sorted(df["Fund Name"].unique()), default=list(df["Fund Name"].unique()))
            min_moic, max_moic = st.slider("MOIC Range", 0.0, float(df["MOIC"].max())+1, (0.0, float(df["MOIC"].max())))
            df = df[(df["Fund Name"].isin(selected_funds)) & (df["MOIC"] >= min_moic) & (df["MOIC"] <= max_moic)]

        # --- Visualizations ---
        st.markdown("### 💹 Investment Distributions")
        col5, col6 = st.columns(2)
        with col5:
            st.plotly_chart(px.histogram(df, x="MOIC", nbins=30, title="MOIC Distribution"), use_container_width=True)
        with col6:
            st.plotly_chart(px.histogram(df.dropna(subset=["IRR"]), x="IRR", nbins=30, title="IRR Distribution"), use_container_width=True)

        st.markdown("### 📊 MOIC by Fund")
        fund_summary = df.groupby("Fund Name").agg({"Cost": "sum", "Fair Value": "sum"}).reset_index()
        fund_summary["MOIC"] = fund_summary["Fair Value"] / fund_summary["Cost"]
        st.plotly_chart(px.bar(fund_summary, x="Fund Name", y="MOIC", title="MOIC by Fund"), use_container_width=True)

        st.markdown("### 🔝 Top 10 by Fair Value")
        top_fv = df.sort_values("Fair Value", ascending=False).head(10)
        st.dataframe(top_fv[["Investment Name", "Fair Value", "MOIC", "IRR"]])

        st.markdown("### 📋 Full Investment Table")
        st.dataframe(df.sort_values("Fair Value", ascending=False))

        st.download_button(
            label="Download Filtered Data as CSV",
            data=df.to_csv(index=False),
            file_name="investment_dashboard_output.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error loading file: {e}")

