import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import pandas as pd
import datetime

# 1. Page Config for Mobile
st.set_page_config(page_title="Lotus-Sense Scanner", layout="centered")

# 2. Setup the OCR Engine (Cached to save memory)
@st.cache_resource
def load_model():
    return easyocr.Reader(['en'])

reader = load_model()

st.title("☀️ Lotus-Sense: Solar Scanner")
st.info("Group Project: Automated Recycling Log [cite: 17, 18]")

# 3. Camera Input
img_file = st.camera_input("Scan Solar Panel Label")

# Initialize a session state to store data across the group members' sessions
if 'group_data' not in st.session_state:
    st.session_state.group_data = pd.DataFrame(columns=["Timestamp", "Manufacturer", "Raw_Text"])

if img_file:
    input_image = Image.open(img_file)
    image_np = np.array(input_image)
    
    with st.spinner("AI is reading label..."):
        results = reader.readtext(image_np)
        detected_text = [res[1] for res in results]
        full_blob = " ".join(detected_text)
    
    # Simple Logic to find a Brand (You can expand this!)
    brand = "Unknown"
    if "Trina" in full_blob: brand = "Trina Solar"
    elif "Jinko" in full_blob: brand = "Jinko Solar"

    # 4. Update the shared table
    new_entry = {
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Manufacturer": brand,
        "Raw_Text": full_blob[:100] + "..." # Truncate for display
    }
    
    # Add to the list
    st.session_state.group_data = pd.concat([st.session_state.group_data, pd.DataFrame([new_entry])], ignore_index=True)
    
    st.success(f"Successfully Scanned: {brand}")
    st.table(st.session_state.group_data)

    # 5. Export for the Group Report
    csv = st.session_state.group_data.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Full Log (CSV)",
        data=csv,
        file_name="lotus_solar_log.csv",
        mime="text/csv",
    )