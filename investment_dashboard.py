import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import io

st.set_page_config(layout="wide", page_title="Investment Dashboard", page_icon="📊")

# Sidebar menu for export options
with st.sidebar:
    st.header("🗕️ Export Options")
    download_csv = st.button("📄 Download CSV")
    download_pdf = st.button("🩾 Download PDF")
    st.caption("Click a button to generate and download your export.")

st.title(":bar_chart: Investment Performance Dashboard")

uploaded_file = st.file_uploader("Upload Investment Excel", type=["xlsx"])

# Realized / Unrealized filter
st.markdown("### :mag: Filter Investments")
realization_options = ["All", "Realized", "Unrealized"]
realization_filter = st.radio("Show Investments:", realization_options, horizontal=True)

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    required_columns = ["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]
    if not all(col in df.columns for col in required_columns):
        st.error("Missing required columns in uploaded file. Please ensure headers match expected structure.")
    else:
        df = df.dropna(subset=["Cost", "Fair Value", "Date"])
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df = df.dropna(subset=["Date"])

        df["MOIC"] = df["Fair Value"] / df["Cost"]

        today = pd.Timestamp.today()
        df["ROI"] = (df["Fair Value"] - df["Cost"]) / df["Cost"]
        df["Annualized ROI"] = df.apply(lambda row: (row["ROI"] / ((today - row["Date"]).days / 365.25)) if (today - row["Date"]).days > 0 else np.nan, axis=1)

        unique_funds = sorted(df["Fund Name"].dropna().unique())
        selected_funds = st.multiselect("Select Fund(s)", options=unique_funds, default=unique_funds, key="fund_selector")

        # Apply filters (FIXED)
        df_filtered = df.copy()
        if "Realized / Unrealized" in df_filtered.columns:
            df_filtered["Realized / Unrealized"] = df_filtered["Realized / Unrealized"].astype(str).str.strip().str.lower()
            if realization_filter != "All":
                df_filtered = df_filtered[df_filtered["Realized / Unrealized"] == realization_filter.lower()]

        df_filtered = df_filtered[df_filtered["Fund Name"].isin(selected_funds)]

        total_invested = df_filtered["Cost"].sum()
        total_fair_value = df_filtered["Fair Value"].sum()
        portfolio_moic = total_fair_value / total_invested if total_invested != 0 else 0
        portfolio_roi = (total_fair_value - total_invested) / total_invested
        total_days = (today - df_filtered["Date"].min()).days
        portfolio_annualized_roi = portfolio_roi / (total_days / 365.25) if total_days > 0 else np.nan

        st.markdown("### :bar_chart: Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${total_invested:,.0f}")
        col2.metric("Total Fair Value", f"${total_fair_value:,.0f}")
        col3.metric("Portfolio MOIC", f"{portfolio_moic:.2f}")
        col4.metric("Annual ROI", f"{portfolio_annualized_roi:.1%}" if not np.isnan(portfolio_annualized_roi) else "N/A")

        st.markdown("---")
        st.subheader(":bar_chart: Portfolio MOIC by Fund")
        moic_by_fund = df_filtered.groupby("Fund Name").apply(lambda x: x["Fair Value"].sum() / x["Cost"].sum()).reset_index(name="Portfolio MOIC")
        fig1 = px.bar(moic_by_fund, x="Fund Name", y="Portfolio MOIC", title="MOIC per Fund", text_auto=True, color_discrete_sequence=["#B1874C"] * len(moic_by_fund))
        st.plotly_chart(fig1, use_container_width=True)

        st.subheader(":chart_with_upwards_trend: Annualized ROI by Fund")
        roi_fund = df_filtered.groupby("Fund Name")["Annualized ROI"].mean().reset_index()
        fig2 = px.bar(roi_fund, x="Fund Name", y="Annualized ROI", title="Annualized ROI per Fund", text_auto=".1%", color_discrete_sequence=["#B1874C"] * len(roi_fund))
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader(":moneybag: Capital Allocation by Fund")
        pie_df = df_filtered.groupby("Fund Name")["Cost"].sum().reset_index()
        gold_shades = ["#A67B43", "#BA905C", "#CEA574", "#E3BA8D", "#F7CFA5", "#FCE9D2", "#FFF5EA"]
        fig3 = px.pie(pie_df, names="Fund Name", values="Cost", title="Capital Invested per Fund", color_discrete_sequence=gold_shades[:len(pie_df)])
        st.plotly_chart(fig3, use_container_width=True)

        if "Stage" in df_filtered.columns:
            st.subheader(":dna: Investments by Stage")
            stage_df = df_filtered.groupby("Stage")["Cost"].sum().reset_index()
            fig4 = px.pie(stage_df, names="Stage", values="Cost", title="Investments by Stage", color_discrete_sequence=gold_shades[:len(stage_df)])
            st.plotly_chart(fig4, use_container_width=True)

        st.subheader(":bar_chart: Cost Basis vs Fair Value Since Inception")
        cost_value_df = df_filtered.groupby("Date").agg({"Cost": "sum", "Fair Value": "sum"}).sort_index().cumsum().reset_index()
        fig_cost_value = px.line(cost_value_df, x="Date", y=["Cost", "Fair Value"], title="Cost vs Fair Value Over Time", color_discrete_sequence=["#B1874C", "#D4B885"])
        st.plotly_chart(fig_cost_value, use_container_width=True)

        st.subheader(":robot_face: AI Summary")
        top_roi = df_filtered.sort_values("Annualized ROI", ascending=False).head(3)["Investment Name"].tolist()
        low_roi = df_filtered.sort_values("Annualized ROI", ascending=True).head(3)["Investment Name"].tolist()
        avg_roi = df_filtered["Annualized ROI"].mean()
        st.markdown(f"**Top Performing Investments:** {', '.join(top_roi)}")
        st.markdown(f"**Lowest Performing Investments:** {', '.join(low_roi)}")
        st.markdown(f"**Average Annualized ROI:** {avg_roi:.2%}")

        def highlight(val):
            return "background-color: #ffe6e6" if isinstance(val, float) and val < 0 else ""

        st.markdown("### :abacus: Investment Table")
        st.dataframe(df_filtered[["Investment Name", "Fund Name", "Cost", "Fair Value", "MOIC", "ROI", "Annualized ROI"]].style.applymap(highlight, subset=["ROI", "Annualized ROI"]))

        if download_csv:
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Click to Save CSV", data=csv, file_name="investment_summary.csv", mime="text/csv")
