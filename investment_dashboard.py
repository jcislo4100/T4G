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
    st.header("📅 Export Options")
    download_csv = st.button("📄 Download CSV")
    download_pdf = st.button("🧾 Download PDF")
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
        if "Realized / Unrealized" in df.columns and realization_filter != "All":
        df = df[df["Realized / Unrealized"].str.lower() == realization_filter.lower()]

        selected_funds = st.multiselect("Select Fund(s)", options=unique_funds, default=unique_funds)
        df_filtered = df[df["Fund Name"].isin(selected_funds)]

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

        st.subheader(":world_map: Geographic Investment Map")
        location_coords = {
            "Cincinnati, OH": (39.1031, -84.5120),
            "Ann Arbor, MI": (42.2808, -83.7430),
            "San Francisco, CA": (37.7749, -122.4194),
            "Cleveland, OH": (41.4993, -81.6944),
            "Chicago, IL": (41.8781, -87.6298),
            "Lansing, MI": (42.7325, -84.5555),
            "Boston, MA": (42.3601, -71.0589),
            "Grand Rapids, MI": (42.9634, -85.6681),
            "Brooklyn, NY": (40.6782, -73.9442),
            "Miami, FL": (25.7617, -80.1918),
            "New York, NY": (40.7128, -74.0060),
            "Nashville, TN": (36.1627, -86.7816),
            "Waco, TX": (31.5493, -97.1467),
            "Sunnyvale, CA": (37.3688, -122.0363),
            "Hawthorne, NY": (41.1076, -73.7954),
            "Boulder, CO": (40.01499, -105.2705),
            "Palo Alto, CA": (37.4419, -122.1430),
            "Oakland, CA": (37.8044, -122.2711),
            "Carlsbad, CA": (33.1581, -117.3506),
            "Tampa, FL": (27.9506, -82.4572),
            "Columbus, OH": (39.9612, -82.9988)
        }

        if "City" in df_filtered.columns and "State" in df_filtered.columns:
            df_filtered["CityState"] = df_filtered["City"].str.strip() + ", " + df_filtered["State"].str.strip()
            df_filtered["Latitude"] = df_filtered["CityState"].map(lambda x: location_coords.get(x, (np.nan, np.nan))[0])
            df_filtered["Longitude"] = df_filtered["CityState"].map(lambda x: location_coords.get(x, (np.nan, np.nan))[1])

        if "Latitude" in df_filtered.columns and "Longitude" in df_filtered.columns:
            geo_df = df_filtered.dropna(subset=["Latitude", "Longitude"])
            if not geo_df.empty:
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
                st.info("Map data columns are available but contain no valid location data.")
        else:
            st.info("No geographic columns found. Add 'Latitude' and 'Longitude' to use the map feature.")

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

        if download_pdf:
            import tempfile
            import os

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Investment Performance Summary", ln=True, align='C')
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Total Invested: ${total_invested:,.0f}", ln=True)
            pdf.cell(200, 10, txt=f"Total Fair Value: ${total_fair_value:,.0f}", ln=True)
            pdf.cell(200, 10, txt=f"Portfolio MOIC: {portfolio_moic:.2f}", ln=True)
            pdf.cell(200, 10, txt=f"Annualized ROI: {portfolio_annualized_roi:.2%}", ln=True)
            pdf.ln(10)

            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt="Top Performing Investments:", ln=True)
            for name in top_roi:
                pdf.cell(200, 10, txt=f"- {name}", ln=True)

            pdf.ln(5)
            pdf.cell(200, 10, txt="Lowest Performing Investments:", ln=True)
            for name in low_roi:
                pdf.cell(200, 10, txt=f"- {name}", ln=True)

            # Save plots as images
            with tempfile.TemporaryDirectory() as tmpdir:
                fig1_path = os.path.join(tmpdir, "moic_by_fund.png")
                fig2_path = os.path.join(tmpdir, "roi_by_fund.png")
                fig3_path = os.path.join(tmpdir, "capital_allocation.png")
                fig4_path = os.path.join(tmpdir, "investments_by_stage.png")
                fig_cost_path = os.path.join(tmpdir, "cost_vs_value.png")

                fig1.write_image(fig1_path)
                fig2.write_image(fig2_path)
                fig3.write_image(fig3_path)
                if 'fig4' in locals():
                    fig4.write_image(fig4_path)
                fig_cost_value.write_image(fig_cost_path)

                for img_path in [fig1_path, fig2_path, fig3_path, fig4_path if 'fig4' in locals() else None, fig_cost_path]:
                    if img_path and os.path.exists(img_path):
                        pdf.add_page()
                        pdf.image(img_path, x=10, w=190)

                pdf_bytes = pdf.output(dest='S').encode('latin1')
            st.download_button("⬇️ Click to Save PDF", data=pdf_bytes, file_name="investment_summary.pdf", mime="application/pdf")
