import streamlit as st
from streamlit_gsheets import GSheetsConnection
import easyocr
import numpy as np
from PIL import Image
import pandas as pd
import datetime
import re  # Added for data extraction

# 1. Setup Connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Setup OCR Engine
@st.cache_resource
def load_model():
    return easyocr.Reader(['en'])

reader = load_model()

st.title("Solar Panel Recycling Data System")
st.subheader("Designed by Lotus Recycling")

# 3. Input Methods
input_method = st.radio("Select Input Method:", ("Scan with Camera", "Upload Image File"))

if input_method == "Scan with Camera":
    img_file = st.camera_input("Take a photo of the data sheet") [cite: 53]
else:
    img_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"]) [cite: 53]

if img_file:
    input_image = Image.open(img_file)
    image_np = np.array(input_image)
    st.image(input_image, caption="Input Image", use_container_width=True)
    
    with st.spinner("AI is reading label..."):
        results = reader.readtext(image_np)
        full_blob = " ".join([res[1] for res in results])
    
    # --- NEW: DATA EXTRACTION LOGIC ---
    # These patterns look for common labels on solar data sheets
    wattage = re.findall(r'(\d{3})\s?W', full_blob, re.IGNORECASE)
    voltage = re.findall(r'(\d{2}\.?\d?)\s?V', full_blob, re.IGNORECASE)
    model = re.findall(r'(TSM-\d+|JKM\d+|LR\d-\d+)', full_blob, re.IGNORECASE)

    extracted_pmax = wattage[0] if wattage else "Not Found"
    extracted_voc = voltage[0] if voltage else "Not Found"
    extracted_model = model[0] if model else "Not Found"

    st.markdown("### Extracted Data Points")
    col1, col2, col3 = st.columns(3)
    col1.metric("Model", extracted_model)
    col2.metric("Wattage", f"{extracted_pmax}W")
    col3.metric("Voltage", f"{extracted_voc}V")

    # 4. Permanent Database Logic
    if st.button("Save to Central Database"):
        existing_data = conn.read(worksheet="Sheet1")
        
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

# 5. Shared Log View
st.write("### Shared Global Log")
st.dataframe(conn.read(worksheet="Sheet1"))