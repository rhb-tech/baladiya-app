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

# ---- SAFE STRING CONVERSION (pandas 3.0 compatible) ----
def safe_to_str(df):
    """
    Safely convert all columns to plain Python str.
    Handles pandas 3.0 StringDtype, NaT, NA, NaN, and mixed-type columns.
    Returns a plain object-dtype DataFrame suitable for Arrow/Streamlit/Excel.
    """
    result = pd.DataFrame(index=df.index)
    for col in df.columns:
        result[col] = df[col].apply(lambda x: "" if pd.isna(x) else str(x))
    return result

# ---- CLEANING FUNCTION ----
def clean_hostaway_data(df):
    # Normalize nulls
    df = df.replace({None: "", "None": "", "nan": ""})
    df = df.fillna("")

    # Strip strings
    df = df.apply(lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x))

    # Numeric columns
    numeric_cols = [
        "Total price",
        "Airbnb listing cleaning fee",
        "Airbnb Listing host fee",
        "Airbnb listing security price",
        "Cancellation payout"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Date columns
    for col in ["Check-in date", "Check-out date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Guests & nights
    for col in ["Number of guests", "Number of nights"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(1)

    # Ensure unit column exists as string
    if "MultiUnit Unit Names" not in df.columns:
        df["MultiUnit Unit Names"] = ""
    else:
        # Force to string — pandas 3.0 may read this as int64 if values are numeric
        df["MultiUnit Unit Names"] = df["MultiUnit Unit Names"].astype(object).apply(
            lambda x: "" if pd.isna(x) else str(x)
        )

    # Fill missing unit names from fallback apartment column
    possible_apartment_cols = [
        "Apartment Number", "Apartment No", "Apartment",
        "Unit Number", "Unit No", "Unit"
    ]
    apartment_col = next((c for c in possible_apartment_cols if c in df.columns), None)

    if apartment_col:
        mask = df["MultiUnit Unit Names"].astype(str).str.strip() == ""
        df.loc[mask, "MultiUnit Unit Names"] = df.loc[mask, apartment_col].astype(str)

    return df

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
    }}

    .subtitle {{
        color: {BRAND_RED};
        font-size: 18px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---- HEADER ----
st.markdown("<div class='title'>RHB Monthly Baladiya Report</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Upload your CSV file</div>", unsafe_allow_html=True)
st.markdown("---")

# ---- FILE UPLOAD ----
uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

if uploaded_file:
    try:
        # FIX: dtype=object prevents pandas 3.0 from using StringDtype/int64
        # for columns that should be treated as plain strings.
        df = pd.read_csv(uploaded_file, dtype=object)

        # ---- CLEAN DATA ----
        df = clean_hostaway_data(df)

        st.success("File uploaded successfully!")

        # FIX: use safe_to_str instead of astype(str) to avoid Arrow serialization
        # errors caused by pandas 3.0 StringDtype with NaN/NaT values.
        st.dataframe(safe_to_str(df.head()))

        # ---- VALIDATION ----
        required_cols = ["Total price", "Check-out date"]
        missing = [c for c in required_cols if c not in df.columns]

        if missing:
            st.error(f"Missing required columns: {missing}")
            st.stop()

        # ---- NET REVENUE ----
        df["Net Revenue"] = (
            df.get("Total price", pd.Series(0, index=df.index))
            - df.get("Airbnb Listing host fee", pd.Series(0, index=df.index))
            - df.get("Airbnb listing cleaning fee", pd.Series(0, index=df.index))
            + df.get("Cancellation payout", pd.Series(0, index=df.index))
        )

        # ---- VAT ----
        df["Price Before VAT"] = df["Net Revenue"].apply(
            lambda x: round(x / VAT_RATE, 2) if x > 0 else 0
        )

        # ---- MONTH NAME ----
        if df["Check-out date"].dropna().empty:
            month_year = "Report"
        else:
            month_year = df["Check-out date"].dt.strftime("%B %Y").mode()[0]

        # ---- FINAL COLUMNS ----
        final_columns = [
            "MultiUnit Unit Names",
            "Check-in date",
            "Check-out date",
            "Guest name",
            "Channel",
            "Price Before VAT",
            "Net Revenue",
            "Total price",
            "Number of guests",
            "Number of nights",
            "Listing",
            "Hostaway reservation ID",
            "Apartment Size",
            "Area/Neighborhood"
        ]

        df = df[[c for c in final_columns if c in df.columns]]

        # ---- EXPORT ----
        output = BytesIO()

        # FIX: use safe_to_str instead of astype(str) for reliable Excel export
        df_export = safe_to_str(df)

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_export.to_excel(writer, sheet_name="All Data", index=False)

            if "Area/Neighborhood" in df_export.columns:
                for area in df_export["Area/Neighborhood"].dropna().unique():
                    if area and area != "":
                        df_export[df_export["Area/Neighborhood"] == area].to_excel(
                            writer,
                            sheet_name=str(area)[:31],
                            index=False
                        )

        output.seek(0)

        st.success(f"Report ready: {month_year}.xlsx")

        st.download_button(
            "📥 Download Excel",
            data=output,
            file_name=f"{month_year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error: {e}")
