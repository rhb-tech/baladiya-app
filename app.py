
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

# ---- CONFIG ----
import base64

def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = get_base64_of_bin_file("logo.png")

st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(
    rgba(255,255,255,0.85),
    rgba(255,255,255,0.85)
),
url("data:image/png;base64,{logo_base64}");

background-size: 400px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)
st.image("logo.png", width=200)
st.markdown("---")
VAT_RATE = 1.15

st.set_page_config(page_title="Monthly Baladiya Report", layout="centered")

st.title("RHB Monthly Baladiya Report")

st.write("Upload your CSV file to generate the formatted Excel report.")

# ---- FILE UPLOAD ----
uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

if uploaded_file:

    try:
        df = pd.read_csv(uploaded_file)

        st.success("File uploaded successfully!")
        st.write("Preview:")
        st.dataframe(df.head())

        # ---- DETECT APARTMENT COLUMN ----
        possible_apartment_cols = [
            "Apartment Number", "Apartment No", "Apartment",
            "Unit Number", "Unit No", "Unit"
        ]

        apartment_col = next(
            (c for c in possible_apartment_cols if c in df.columns),
            None
        )

        if apartment_col is None:
            st.error("Apartment / Unit column not found")
            st.stop()

        # ---- FILL BLANK MultiUnit Unit Names ----
        mask = (
            df["MultiUnit Unit Names"].isna() |
            (df["MultiUnit Unit Names"].astype(str).str.strip() == "")
        )

        df.loc[mask, "MultiUnit Unit Names"] = df.loc[mask, apartment_col]

        # ---- PRICE BEFORE VAT ----
        df["Price Before VAT"] = df["Total price"].apply(
            lambda x: round(x / VAT_RATE, 2) if x > 0 else 0
        )

        # ---- DATE HANDLING ----
        df["Check-out date"] = pd.to_datetime(df["Check-out date"], errors="coerce")

        month_year = (
            df["Check-out date"]
            .dropna()
            .dt.strftime("%B %Y")
            .mode()[0]
        )

        # ---- FINAL COLUMN ORDER ----
        final_columns = [
            "MultiUnit Unit Names",
            "Check-in date",
            "Check-out date",
            "Guest name",
            "Channel",
            "Price Before VAT",
            "Total price",
            "Number of guests",
            "Number of nights",
            "Listing",
            "Hostaway reservation ID",
            "Apartment Size",
            "Area/Neighborhood"
        ]

        df = df[[c for c in final_columns if c in df.columns]]

        # ---- CREATE EXCEL IN MEMORY ----
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="All Data", index=False)

            if "Area/Neighborhood" in df.columns:
                for area in df["Area/Neighborhood"].dropna().unique():
                    area_df = df[df["Area/Neighborhood"] == area]
                    area_df.to_excel(writer, sheet_name=str(area)[:31], index=False)

        output.seek(0)

        # ---- DOWNLOAD BUTTON ----
        st.success(f"Report ready: {month_year}.xlsx")

        st.download_button(
            label="📥 Download Excel Report",
            data=output,
            file_name=f"{month_year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error: {e}")
