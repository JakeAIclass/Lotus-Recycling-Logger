import streamlit as st
from streamlit_gsheets import GSheetsConnection
import easyocr
import numpy as np
from PIL import Image
import pandas as pd
import datetime
import re

# Connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# OCR Setup
@st.cache_resource
def load_model():
    return easyocr.Reader(['en'])

reader = load_model()

st.title("Solar Panel Recycling Data System")
st.subheader("Designed by Lotus Recycling")

input_method = st.radio("Select Input Method:", ("Scan with Camera", "Upload Image File"))

if input_method == "Scan with Camera":
    img_file = st.camera_input("Take a photo of the data sheet")
else:
    img_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if img_file:
    input_image = Image.open(img_file)
    image_np = np.array(input_image)
    st.image(input_image, caption="Input Image", use_container_width=True)
    
    with st.spinner("AI is reading label..."):
        results = reader.readtext(image_np)
        full_blob = " ".join([res[1] for res in results])
    
    # Extraction Logic
    wattage = re.findall(r'(\d{3})\s?W', full_blob, re.IGNORECASE)
    voltage = re.findall(r'(\d{2}\.?\d?)\s?V', full_blob, re.IGNORECASE)
    model = re.findall(r'(TSM-\d+|JKM\d+|LR\d-\d+)', full_blob, re.IGNORECASE)
    
    extracted_pmax = wattage[0] if wattage else "N/A"
    extracted_voc = voltage[0] if voltage else "N/A"
    extracted_model = model[0] if model else "N/A"

    st.markdown("### Extracted Data")
    st.write(f"**Pmax:** {extracted_pmax}W | **Voc:** {extracted_voc}V")

    if st.button("Save to Central Database"):
        try:
            # Read existing data
            existing_data = conn.read()
            
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
            st.error(f"Error saving to database: {e}")

# Shared Log View
st.write("### Shared Global Log")
try:
    # This will now show us the EXACT error if it fails
    df = conn.read(worksheet="Sheet1")
    st.dataframe(df)
except Exception as e:
    st.error(f"Developer Debug Error: {e}")
    st.warning("Database not connected yet. Please check Secrets.")