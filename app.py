
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Paneer Cold-Chain Quality Analysis",
    page_icon="🥛",
    layout="wide",
)

st.title("Paneer Cold-Chain Quality Analysis")
st.caption(
    "Temperature monitoring, refrigeration excursions, "
    "and paneer quality trends during storage."
)

st.info(
    "Dashboard setup is complete. Upload your datasets "
    "to begin exploring the analysis."
)

st.header("Upload datasets")

temperature_file = st.file_uploader(
    "Upload refrigerator temperature log (CSV)",
    type=["csv"],
    key="temperature",
)

quality_file = st.file_uploader(
    "Upload paneer quality testing data (Excel)",
    type=["xlsx", "xls"],
    key="quality",
)

if temperature_file is not None:
    temperature_df = pd.read_csv(temperature_file)

    st.subheader("Temperature log preview")
    st.write(f"Rows: {len(temperature_df):,}")
    st.dataframe(temperature_df.head())

if quality_file is not None:
    quality_df = pd.read_excel(quality_file)

    st.subheader("Quality testing workbook preview")
    st.write(f"Rows: {len(quality_df):,}")
    st.dataframe(quality_df.head())
