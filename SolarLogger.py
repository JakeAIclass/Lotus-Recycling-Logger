import streamlit as st
from streamlit_gsheets import GSheetsConnection
import easyocr
import numpy as np
from PIL import Image
import pandas as pd
import datetime
import re

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="Solar Panel Logger", layout="centered")

st.title("☀️ Solar Panel Recycling Data System")
st.subheader("Designed by Lotus Recycling")

# -------------------------------
# GOOGLE SHEETS CONNECTION
# -------------------------------
conn = st.connection(
    "gsheets",
    type=GSheetsConnection,
    spreadsheet="120o8DAx7Xbi06sL3xVq5Lf-2JXtbdm4_nEvhVymEu_E"
)


# -------------------------------
# LOAD OCR MODEL (cached)
# -------------------------------
@st.cache_resource
def load_model():
    return easyocr.Reader(['en'])

reader = load_model()

# -------------------------------
# INPUT METHOD
# -------------------------------
input_method = st.radio(
    "Select Input Method:",
    ("📷 Scan with Camera", "📁 Upload Image File")
)

if input_method == "📷 Scan with Camera":
    img_file = st.camera_input("Take a photo of the panel label")
else:
    img_file = st.file_uploader("Upload an image...", type=["jpg", "jpeg", "png"])

# -------------------------------
# OCR PROCESSING
# -------------------------------
if img_file:
    input_image = Image.open(img_file)
    image_np = np.array(input_image)

    st.image(input_image, caption="Input Image", use_container_width=True)

    with st.spinner("🔍 AI is reading label..."):
        results = reader.readtext(image_np)
        full_blob = " ".join([res[1] for res in results])

    # -------------------------------
    # IMPROVED EXTRACTION LOGIC
    # -------------------------------
    wattage = re.findall(r'(\d{3,4})\s?[Ww]', full_blob)
    voltage = re.findall(r'(\d{2,3}\.?\d*)\s?[Vv]', full_blob)

    # Common solar model patterns
    model = re.findall(r'(TSM-\w+|JKM\d+\w*|LR\d-\w+|[A-Z0-9\-]{6,})', full_blob)

    extracted_pmax = wattage[0] if wattage else "N/A"
    extracted_voc = voltage[0] if voltage else "N/A"
    extracted_model = model[0] if model else "N/A"

    # -------------------------------
    # DISPLAY RESULTS
    # -------------------------------
    st.markdown("### 📊 Extracted Data")

    col1, col2, col3 = st.columns(3)
    col1.metric("Model", extracted_model)
    col2.metric("Wattage (Pmax)", f"{extracted_pmax} W")
    col3.metric("Voltage (Voc)", f"{extracted_voc} V")

    st.markdown("#### 🧾 Full OCR Text")
    st.text_area("", full_blob, height=120)

    # -------------------------------
    # SAVE BUTTON
    # -------------------------------
    if st.button("💾 Save to Central Database"):
        try:
            # SAFE READ (handles empty sheet)
            try:
                existing_data = conn.read(worksheet="Sheet1")
            except:
                existing_data = pd.DataFrame(columns=[
                    "Timestamp", "Model", "Wattage", "Voltage", "Full_Text"
                ])

            new_entry = pd.DataFrame([{
                "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Model": extracted_model,
                "Wattage": extracted_pmax,
                "Voltage": extracted_voc,
                "Full_Text": full_blob
            }])

            updated_df = pd.concat([existing_data, new_entry], ignore_index=True)

            conn.update(worksheet="Sheet1", data=updated_df)

            st.success("✅ Logged to Google Sheets!")

        except Exception as e:
            st.error(f"❌ Error saving to database: {e}")

# -------------------------------
# GLOBAL DATA VIEW
# -------------------------------
st.divider()
st.markdown("### 🌍 Shared Global Log")

try:
    df = conn.read(worksheet="Sheet1")

    if df.empty:
        st.info("No data logged yet.")
    else:
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Database connection error: {e}")
    st.warning("Check your Streamlit secrets configuration.")
