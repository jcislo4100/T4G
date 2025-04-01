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
    df = pd.read_excel(uploaded_file)

    df = df[['Investment Name', 'Cost', 'Fair Value', 'Date', 'Fund Name']].dropna()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])

    df['MOIC'] = df['Fair Value'] / df['Cost']

    # IRR Calculation per Investment
    def calculate_irr(row):
        try:
            cash_flows = [-row['Cost'], row['Fair Value']]
            dates = [row['Date'], datetime.today()]
            days = [(d - dates[0]).days for d in dates]
            return npf.xirr(dict(zip(dates, cash_flows)))
        except Exception:
            return np.nan

    df['IRR'] = df.apply(calculate_irr, axis=1)

    # Fund-Level Aggregation
    fund_group = df.groupby('Fund Name').agg({
        'Cost': 'sum',
        'Fair Value': 'sum'
    }).reset_index()
    fund_group['Portfolio MOIC'] = fund_group['Fair Value'] / fund_group['Cost']

    # Fund-Level IRR Calculation
    fund_irr = []
    for fund in df['Fund Name'].unique():
        fund_df = df[df['Fund Name'] == fund]
        cash_flows = [-fund_df['Cost'].sum(), fund_df['Fair Value'].sum()]
        dates = [fund_df['Date'].min(), datetime.today()]
        try:
            irr = npf.xirr(dict(zip(dates, cash_flows)))
        except Exception:
            irr = np.nan
        fund_irr.append({'Fund Name': fund, 'Portfolio IRR': irr})

    fund_irr_df = pd.DataFrame(fund_irr)
    fund_summary = pd.merge(fund_group, fund_irr_df, on='Fund Name')

    # Metrics
    st.metric("Total Amount Invested", f"${df['Cost'].sum():,.0f}")
    st.metric("Total Fair Value", f"${df['Fair Value'].sum():,.0f}")
    st.metric("Portfolio MOIC", f"{df['Fair Value'].sum() / df['Cost'].sum():.2f}")
    st.metric("Estimated IRR", f"{npf.xirr(dict(zip([df['Date'].min(), datetime.today()], [-df['Cost'].sum(), df['Fair Value'].sum()])):.1%}")

    # Portfolio MOIC Chart
    st.header("📊 Portfolio MOIC by Fund")
    st.plotly_chart(px.bar(fund_summary, x='Fund Name', y='Portfolio MOIC', title="MOIC by Fund"))

    # Portfolio IRR Chart
    st.header("📉 Portfolio IRR by Fund")
    st.plotly_chart(px.bar(fund_summary, x='Fund Name', y='Portfolio IRR', title="IRR by Fund"))

    # MOIC Histogram
    st.header("📈 MOIC Distribution")
    st.subheader("Distribution of MOIC across Investments")
    st.plotly_chart(px.histogram(df, x='MOIC'))

    # IRR Histogram
    st.header("📉 IRR by Investment")
    st.subheader("Distribution of IRRs")
    st.plotly_chart(px.histogram(df, x='IRR'))

        # Show Table
        st.markdown("---")
        st.subheader("🧮 Investment Table")
        st.dataframe(df[["Investment Name", "Fund Name", "Cost", "Fair Value", "MOIC", "IRR"]])
