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
conn = st.connection("gsheets", type=GSheetsConnection)

# -------------------------------
# LOAD OCR MODEL (cached)
# -------------------------------
@st.cache_resource
def load_model():
    return easyocr.Reader(['en'])

reader = load_model()

# -------------------------------
# GEOLOCATION (Browser-based)
# -------------------------------
st.markdown("### 📍 Location")

# Inject JS to get browser geolocation and pass back via query param workaround
geo_script = """
    <script>
    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const lat = position.coords.latitude.toFixed(6);
                    const lon = position.coords.longitude.toFixed(6);
                    const acc = Math.round(position.coords.accuracy);
                    document.getElementById('geo_output').innerText = lat + ',' + lon + ',' + acc;
                    document.getElementById('geo_status').innerText = '✅ Location captured: ' + lat + ', ' + lon + ' (±' + acc + 'm)';
                },
                function(error) {
                    document.getElementById('geo_status').innerText = '❌ Location error: ' + error.message;
                },
                {enableHighAccuracy: true, timeout: 10000}
            );
        } else {
            document.getElementById('geo_status').innerText = '❌ Geolocation not supported by this browser.';
        }
    }
    </script>
    <button onclick="getLocation()" style="padding:8px 16px;background:#4CAF50;color:white;border:none;border-radius:6px;cursor:pointer;font-size:15px;">
        📍 Get My Location
    </button>
    <p id="geo_status" style="margin-top:8px;color:gray;">Click button to capture location...</p>
    <p id="geo_output" style="display:none;"></p>
"""

st.components.v1.html(geo_script, height=100)

# Manual fallback inputs
with st.expander("✏️ Enter location manually (or to override)"):
    col1, col2 = st.columns(2)
    with col1:
        manual_lat = st.text_input("Latitude", placeholder="e.g. -37.8136")
    with col2:
        manual_lon = st.text_input("Longitude", placeholder="e.g. 144.9631")
    manual_location_name = st.text_input("Site Name / Address", placeholder="e.g. Sunshine Depot, Melbourne")

# Use manual if provided
latitude = manual_lat if manual_lat else "Pending (use button above)"
longitude = manual_lon if manual_lon else "Pending (use button above)"
location_name = manual_location_name if manual_location_name else ""

st.info("💡 Tip: Use the **Get My Location** button for automatic GPS, or enter manually above.")

# -------------------------------
# INPUT METHOD
# -------------------------------
st.markdown("### 📷 Scan Panel Label")
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
    # EXTRACTION LOGIC
    # -------------------------------
    wattage = re.findall(r'(\d{3,4})\s?[Ww](?!h)', full_blob)
    voltage = re.findall(r'(\d{2,3}\.?\d*)\s?[Vv]', full_blob)

    # Solar model patterns
    model = re.findall(r'(TSM-\w+|JKM\d+\w*|LR\d-\w+|CS\d+-\w+|JAM\d+\w*|[A-Z]{2,4}[-_]\d{2,4}[-_]\w+)', full_blob)

    # Serial number patterns — covers most manufacturer formats
    serial = re.findall(
        r'(?:S/?N|Serial\s*(?:No|Number|#)?)[:\s#\-]*([A-Z0-9]{6,20})',
        full_blob, re.IGNORECASE
    )
    # Fallback: look for standalone long alphanumeric strings if no labeled SN found
    if not serial:
        serial = re.findall(r'\b([A-Z]{2,4}\d{8,16})\b', full_blob)

    extracted_pmax   = wattage[0] if wattage else "N/A"
    extracted_voc    = voltage[0] if voltage else "N/A"
    extracted_model  = model[0]   if model   else "N/A"
    extracted_serial = serial[0]  if serial  else "N/A"

    # -------------------------------
    # DISPLAY RESULTS
    # -------------------------------
    st.markdown("### 📊 Extracted Data")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Model",           extracted_model)
    col2.metric("Wattage (Pmax)",  f"{extracted_pmax} W")
    col3.metric("Voltage (Voc)",   f"{extracted_voc} V")
    col4.metric("Serial Number",   extracted_serial)

    st.markdown("#### 🧾 Full OCR Text")
    st.text_area("", full_blob, height=120)

    # Allow manual correction
    st.markdown("#### ✏️ Correct Extracted Values")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        extracted_model  = st.text_input("Model",         value=extracted_model)
    with c2:
        extracted_pmax   = st.text_input("Wattage (W)",   value=extracted_pmax)
    with c3:
        extracted_voc    = st.text_input("Voltage (V)",   value=extracted_voc)
    with c4:
        extracted_serial = st.text_input("Serial Number", value=extracted_serial)

    # -------------------------------
    # SAVE BUTTON
    # -------------------------------
    if st.button("💾 Save to Central Database"):

        # Warn if location not set
        if "Pending" in latitude or "Pending" in longitude:
            st.warning("⚠️ Location not captured — please press 'Get My Location' or enter manually before saving.")
        else:
            try:
                try:
                    existing_data = conn.read(worksheet="Sheet1")
                except:
                    existing_data = pd.DataFrame(columns=[
                        "Timestamp", "Model", "Serial_Number", "Wattage",
                        "Voltage", "Latitude", "Longitude", "Site_Name", "Full_Text"
                    ])

                new_entry = pd.DataFrame([{
                    "Timestamp":     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Model":         extracted_model,
                    "Serial_Number": extracted_serial,
                    "Wattage":       extracted_pmax,
                    "Voltage":       extracted_voc,
                    "Latitude":      latitude,
                    "Longitude":     longitude,
                    "Site_Name":     location_name,
                    "Full_Text":     full_blob
                }])

                updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("✅ Logged to Google Sheets with location!")
                st.map(pd.DataFrame({"lat": [float(latitude)], "lon": [float(longitude)]}))

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

        # Show map of all scan locations
        map_df = df[["Latitude", "Longitude"]].dropna()
        map_df = map_df[map_df["Latitude"] != "N/A"]
        if not map_df.empty:
            try:
                map_df = map_df.rename(columns={"Latitude": "lat", "Longitude": "lon"})
                map_df["lat"] = map_df["lat"].astype(float)
                map_df["lon"] = map_df["lon"].astype(float)
                st.markdown("#### 🗺️ All Scan Locations")
                st.map(map_df)
            except:
                pass

except Exception as e:
    st.error(f"⚠️ Database connection error: {e}")