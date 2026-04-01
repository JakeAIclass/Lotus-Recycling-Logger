import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import pandas as pd
import datetime

# Page Configuration for Mobile Compatibility
st.set_page_config(page_title="Lotus Recycling", layout="centered")

# Initialize OCR Engine (Cached to prevent reloading on every click)
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'])

reader = load_reader()

# Branding Update
st.title("♻️ Lotus Recycling Solar Panel Logger")
st.write("Scan or upload a solar panel data sheet to log inventory details.")

# Data Ingestion: Camera or File Upload for max compatibility
input_method = st.radio("Choose Input Method:", ("Camera", "Upload Image"))

img_file = None
if input_method == "Camera":
    img_file = st.camera_input("Scan Label")
else:
    img_file = st.file_uploader("Choose an image file", type=['jpg', 'jpeg', 'png'])

if img_file:
    input_image = Image.open(img_file)
    image_np = np.array(input_image)
    
    with st.spinner("Analyzing Label..."):
        # AI Model Integration
        results = reader.readtext(image_np)
        detected_text = [res[1] for res in results]
        full_blob = " ".join(detected_text)
        
        st.subheader("Extracted Information")
        st.info(full_blob if full_blob else "No text detected. Please try a clearer photo.")

        # Automated Logging Logic
        if full_blob:
            log_entry = {
                "Timestamp": [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                "Extracted_Text": [full_blob],
                "Device_Type": ["Mobile/Cloud"]
            }
            
            df = pd.DataFrame(log_entry)
            # This saves to the cloud instance's temporary storage
            df.to_csv("solar_inventory.csv", mode='a', header=not st.io.path.exists("solar_inventory.csv"), index=False)
            st.success("✅ Data logged successfully!")