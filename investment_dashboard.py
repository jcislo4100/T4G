# Column Mapping Configuration
# Define rules and logic for multiple formats (Salesforce, Aduro, etc.)

import re
import streamlit as st
import pandas as pd

# Mapping presets for known sources
COLUMN_PRESETS = {
    "Salesforce": {
        "Investment Name": "Account Name",
        "Cost": "Total Investment",
        "Fair Value": "Share of Valuation",
        "Date": "Valuation Date",
        "Fund Name": "Parent Account"
    },
    "Aduro": {
        "Investment Name": "Investment Name",
        "Cost": "Total Invested Amount",
        "Fair Value": "Fair Value",
        "Date": "Date",
        "Fund Name": "Fund Name"
    }
}

# Heuristic fallback mapping for unknown files based on fuzzy matching
AUTO_PATTERNS = {
    "Investment Name": ["investment", "account"],
    "Cost": ["invested", "total investment", "amount invested"],
    "Fair Value": ["fair value", "valuation"],
    "Date": ["date"],
    "Fund Name": ["fund", "parent"]
}

def auto_detect_mapping(headers):
    mapping = {}
    for field, patterns in AUTO_PATTERNS.items():
        for header in headers:
            clean = header.lower().strip()
            if any(p in clean for p in patterns):
                mapping[field] = header
                break
    return mapping

# Dropdown interface to choose file type or auto-detect
@st.cache_data(show_spinner=False)
def get_column_mapping(df):
    st.sidebar.markdown("### File Format Type")
    file_type = st.sidebar.selectbox(
        "What type of file is this?",
        ["Auto-Detect", "Salesforce", "Aduro", "Custom"]
    )

    if file_type == "Auto-Detect":
        mapping = auto_detect_mapping(df.columns)
        st.sidebar.caption("🔍 Auto-detected column headers based on fuzzy rules.")
    elif file_type in COLUMN_PRESETS:
        preset = COLUMN_PRESETS[file_type]
        mapping = {k: preset[k] for k in preset if preset[k] in df.columns}
        st.sidebar.caption(f"🗂️ Using {file_type} preset mapping.")
    else:
        # Manual column selection from dropdowns
        mapping = {}
        for field in AUTO_PATTERNS:
            options = ["None"] + list(df.columns)
            selected = st.sidebar.selectbox(f"Select column for '{field}'", options)
            if selected != "None":
                mapping[field] = selected

    return mapping
