import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
from datetime import datetime
import io

st.set_page_config(layout="wide", page_title="Investment Dashboard", page_icon="📊")
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stDataFrame th { background-color: #f1f1f1; }
    </style>
""", unsafe_allow_html=True)

st.title(":bar_chart: Investment Performance Dashboard")

uploaded_file = st.file_uploader("Upload Investment Excel", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    required_columns = ["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]
    if not all(col in df.columns for col in required_columns):
        st.error("Missing required columns in uploaded file. Please ensure headers match expected structure.")
    else:
        df = df.dropna(subset=["Cost", "Fair Value", "Date"])
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df = df.dropna(subset=["Date"])

        # Compute MOIC
        df["MOIC"] = df["Fair Value"] / df["Cost"]

        # Compute ROI and Annualized ROI
        today = pd.Timestamp.today()
        df["ROI"] = (df["Fair Value"] - df["Cost"]) / df["Cost"]
        df["Annualized ROI"] = df.apply(lambda row: (row["ROI"] / ((today - row["Date"]).days / 365.25)) if (today - row["Date"]).days > 0 else np.nan, axis=1)

        # Fund Filter
        funds = ["All"] + sorted(df["Fund Name"].dropna().unique())
        selected_fund = st.selectbox("Select Fund", funds)
        df_filtered = df if selected_fund == "All" else df[df["Fund Name"] == selected_fund]

        # Date Range Filter (Fixed)
        min_date = pd.to_datetime(df_filtered["Date"].min()).date()
        max_date = pd.to_datetime(df_filtered["Date"].max()).date()
        start_date, end_date = st.slider(
            "Filter by Investment Date",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date)
        )
        df_filtered = df_filtered[(df_filtered["Date"].dt.date >= start_date) & (df_filtered["Date"].dt.date <= end_date)]

        # ROI Horizon Filter
        roi_horizon = st.selectbox("Select ROI Horizon", ["Since Inception", "1 Year", "3 Years", "5 Years"])
        def calculate_annualized_roi(row, horizon):
            horizon_days = (today - row["Date"]).days if horizon == "Since Inception" else min((today - row["Date"]).days, int(horizon.split()[0]) * 365)
            if horizon_days <= 0:
                return np.nan
            roi = (row["Fair Value"] - row["Cost"]) / row["Cost"]
            return roi / (horizon_days / 365.25)

        df_filtered["Annualized ROI"] = df_filtered.apply(lambda row: calculate_annualized_roi(row, roi_horizon), axis=1)

        # Portfolio metrics
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
        fig1 = px.bar(moic_by_fund, x="Fund Name", y="Portfolio MOIC", title="MOIC per Fund", text_auto=True)
        st.plotly_chart(fig1, use_container_width=True)

        st.subheader(":chart_with_upwards_trend: Annualized ROI by Fund")
        roi_fund = df_filtered.groupby("Fund Name")["Annualized ROI"].mean().reset_index()
        fig2 = px.bar(roi_fund, x="Fund Name", y="Annualized ROI", title="Annualized ROI per Fund", text_auto=".1%")
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader(":moneybag: Capital Allocation by Fund")
        pie_df = df_filtered.groupby("Fund Name")["Cost"].sum().reset_index()
        fig3 = px.pie(pie_df, names="Fund Name", values="Cost", title="Capital Invested per Fund")
        st.plotly_chart(fig3, use_container_width=True)

        if "Stage" in df_filtered.columns:
            st.subheader(":dna: Investments by Stage")
            stage_df = df_filtered.groupby("Stage")["Cost"].sum().reset_index()
            fig4 = px.pie(stage_df, names="Stage", values="Cost", title="Investments by Stage")
            st.plotly_chart(fig4, use_container_width=True)

        if "Latitude" in df_filtered.columns and "Longitude" in df_filtered.columns:
            geo_df = df_filtered.dropna(subset=["Latitude", "Longitude"])
            if not geo_df.empty:
                st.subheader(":world_map: Geographic Investment Map")
                st.markdown("#### Investments by Location")
                fig_map = px.scatter_geo(
                    geo_df,
                    lat="Latitude",
                    lon="Longitude",
                    hover_name="Investment Name",
                    color="Investment Name",
                    size="Cost",
                    projection="albers usa",
                    color_discrete_sequence=["#B1874C"] * len(geo_df["Investment Name"].unique())
                )
                fig_map.update_layout(geo=dict(bgcolor='rgba(0,0,0,0)'))
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.subheader(":world_map: Geographic Investment Map")
                st.info("No valid location data to display a map.")

        # AI Summary Generator
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
