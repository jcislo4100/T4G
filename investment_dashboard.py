import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Investment Performance Dashboard", layout="wide")

st.title("📈 Investment Performance Dashboard")

uploaded_file = st.file_uploader("Upload Investment Excel", type=["xlsx"])

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file, sheet_name=None)
        sheet_names = df_raw.keys()

        if "Schedule of investments" in sheet_names:
            df = df_raw["Schedule of investments"].copy()
            file_type = "aduro"
        else:
            df = list(df_raw.values())[0].copy()
            file_type = "salesforce"

        df.columns = df.columns.str.strip()

        if file_type == "aduro":
            df = df.rename(columns={
                "Investment Name": "Investment Name",
                "Total Invested Amount": "Cost",
                "Share of Valuation": "Fair Value",
                "Year – Month – Day": "Date",
                "Fund": "Fund Name"
            })
        else:
            df = df.rename(columns={
                "Account Name": "Investment Name",
                "Total Investment": "Cost",
                "Share of Valuation": "Fair Value",
                "Valuation Date": "Date",
                "Parent Account": "Fund Name"
            })

        df = df[["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]].copy()
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df.dropna(subset=["Date", "Cost", "Fair Value"], inplace=True)

        total_invested = df["Cost"].sum()
        total_fair_value = df["Fair Value"].sum()
        moic = total_fair_value / total_invested if total_invested else 0

        def calc_irr(row):
            try:
                cash_flows = [-row["Cost"]]
                dates = [row["Date"]]
                if row["Fair Value"] > 0:
                    cash_flows.append(row["Fair Value"])
                    dates.append(datetime.today())
                return npf.irr(cash_flows)
            except:
                return np.nan

        df["IRR"] = df.apply(calc_irr, axis=1)
        portfolio_irr = npf.irr(
            [-df["Cost"].sum()] + [df["Fair Value"].sum()]
        ) if df["Cost"].sum() > 0 else 0

        df["MOIC"] = df["Fair Value"] / df["Cost"]
        moic_chart = px.histogram(df, x="MOIC", nbins=10, title="Distribution of MOIC across Investments")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${total_invested:,.0f}")
        col2.metric("Total Fair Value", f"${total_fair_value:,.0f}")
        col3.metric("Portfolio MOIC", f"{moic:.2f}")
        col4.metric("Estimated IRR", f"{portfolio_irr*100:.1f}%")

        st.plotly_chart(moic_chart, use_container_width=True)

        st.subheader("📊 Fund-Level Performance")
        fund_group = df.groupby("Fund Name").agg({
            "Cost": "sum",
            "Fair Value": "sum",
            "IRR": "mean"
        }).reset_index()
        fund_group["MOIC"] = fund_group["Fair Value"] / fund_group["Cost"]
        st.dataframe(fund_group.sort_values("Cost", ascending=False))

        st.subheader("📋 Investment Breakdown")
        st.dataframe(df.sort_values("Fair Value", ascending=False))

    except Exception as e:
        st.error(f"Error loading file: {e}")
