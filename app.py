import streamlit as st
import pandas as pd
from io import BytesIO
import base64

# ---- CONFIG ----
VAT_RATE = 1.15
BRAND_RED = "#B22222"

# ---- LOAD LOGO ----
def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = get_base64_of_bin_file("logo.png")

# ---- STYLING ----
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');

    * {{
        font-family: 'Cairo', sans-serif !important;
    }}

    .stApp {{
        background: linear-gradient(
            rgba(255,255,255,0.85),
            rgba(255,255,255,0.85)
        ),
        url("data:image/png;base64,{logo_base64}");

        background-repeat: no-repeat;
        background-position: center;
        background-size: 400px;
    }}

    .title {{
        color: {BRAND_RED};
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 5px;
    }}

    .subtitle {{
        color: {BRAND_RED};
        font-size: 18px;
        font-weight: 500;
        margin-bottom: 20px;
    }}

    .stButton>button {{
        background-color: {BRAND_RED};
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-weight: 600;
    }}

    .stDownloadButton>button {{
        background-color: {BRAND_RED};
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-weight: 600;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---- HEADER (LOGO REMOVED) ----
st.markdown(
    f"<div class='title'>RHB Monthly Baladiya Report</div>",
    unsafe_allow_html=True
)

st.markdown(
    "<div class='subtitle'>Upload your CSV file to generate the Baladiya report.</div>",
    unsafe_allow_html=True
)

st.markdown("---")

# ---- FILE UPLOAD ----
uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

if uploaded_file:

    try:
        df = pd.read_csv(uploaded_file)

        st.success("File uploaded successfully!")
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

        # ---- CREATE EXCEL ----
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="All Data", index=False)

            if "Area/Neighborhood" in df.columns:
                for area in df["Area/Neighborhood"].dropna().unique():
                    area_df = df[df["Area/Neighborhood"] == area]
                    area_df.to_excel(writer, sheet_name=str(area)[:31], index=False)

        output.seek(0)

        st.success(f"Report ready: {month_year}.xlsx")

        st.download_button(
            label="📥 Download Excel Report",
            data=output,
            file_name=f"{month_year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error: {e}")
