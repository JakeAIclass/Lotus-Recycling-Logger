import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_js_eval import get_geolocation
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
# AUSTRALIAN LOCATIONS
# -------------------------------
AU_LOCATIONS = [
    # NSW
    "Sydney NSW", "Parramatta NSW", "Newcastle NSW", "Wollongong NSW",
    "Central Coast NSW", "Maitland NSW", "Coffs Harbour NSW", "Wagga Wagga NSW",
    "Albury NSW", "Port Macquarie NSW", "Tamworth NSW", "Orange NSW",
    "Dubbo NSW", "Bathurst NSW", "Lismore NSW", "Broken Hill NSW",
    # VIC
    "Melbourne VIC", "Geelong VIC", "Ballarat VIC", "Bendigo VIC",
    "Shepparton VIC", "Melton VIC", "Mildura VIC", "Wodonga VIC",
    "Warrnambool VIC", "Traralgon VIC", "Sunbury VIC", "Wangaratta VIC",
    "Frankston VIC", "Dandenong VIC", "Ringwood VIC", "Footscray VIC",
    "Sunshine VIC", "Werribee VIC", "Hoppers Crossing VIC", "Cranbourne VIC",
    # QLD
    "Brisbane QLD", "Gold Coast QLD", "Sunshine Coast QLD", "Townsville QLD",
    "Cairns QLD", "Toowoomba QLD", "Rockhampton QLD", "Mackay QLD",
    "Bundaberg QLD", "Hervey Bay QLD", "Gladstone QLD", "Mount Isa QLD",
    "Ipswich QLD", "Logan QLD", "Redcliffe QLD", "Caboolture QLD",
    # SA
    "Adelaide SA", "Mount Gambier SA", "Whyalla SA", "Murray Bridge SA",
    "Port Augusta SA", "Port Pirie SA", "Victor Harbor SA", "Gawler SA",
    # WA
    "Perth WA", "Mandurah WA", "Bunbury WA", "Geraldton WA",
    "Albany WA", "Kalgoorlie WA", "Broome WA", "Port Hedland WA",
    "Karratha WA", "Rockingham WA", "Fremantle WA", "Joondalup WA",
    # TAS
    "Hobart TAS", "Launceston TAS", "Devonport TAS", "Burnie TAS",
    # NT
    "Darwin NT", "Alice Springs NT", "Palmerston NT", "Katherine NT",
    # ACT
    "Canberra ACT", "Belconnen ACT", "Tuggeranong ACT", "Gungahlin ACT",
]
AU_LOCATIONS.sort()

# -------------------------------
# GEOLOCATION
# -------------------------------
st.markdown("### 📍 Location")

# Session state init
if "latitude" not in st.session_state:
    st.session_state.latitude = ""
if "longitude" not in st.session_state:
    st.session_state.longitude = ""
if "geo_tried" not in st.session_state:
    st.session_state.geo_tried = False

col_geo1, col_geo2 = st.columns([1, 2])

with col_geo1:
    get_geo = st.button("📍 Get My GPS Location")

with col_geo2:
    if st.session_state.latitude and st.session_state.longitude:
        st.success(f"✅ {st.session_state.latitude}, {st.session_state.longitude}")
    elif st.session_state.geo_tried:
        st.error("❌ GPS unavailable — please enter manually below.")
    else:
        st.info("Press button or enter manually below.")

if get_geo:
    st.session_state.geo_tried = True
    with st.spinner("📡 Getting GPS location..."):
        try:
            loc = get_geolocation()
            if loc and "coords" in loc:
                st.session_state.latitude  = str(round(loc["coords"]["latitude"], 6))
                st.session_state.longitude = str(round(loc["coords"]["longitude"], 6))
                st.rerun()
            else:
                st.session_state.latitude  = ""
                st.session_state.longitude = ""
        except Exception:
            st.session_state.latitude  = ""
            st.session_state.longitude = ""

# Manual entry
with st.expander("✏️ Enter or override location manually", expanded=(not st.session_state.latitude)):
    
    # Australian location autocomplete
    site_search = st.selectbox(
        "🔍 Search Australian location",
        options=[""] + AU_LOCATIONS,
        index=0,
        help="Start typing to filter locations"
    )

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        manual_lat = st.text_input(
            "Latitude",
            value=st.session_state.latitude,
            placeholder="e.g. -37.8136"
        )
    with col_m2:
        manual_lon = st.text_input(
            "Longitude",
            value=st.session_state.longitude,
            placeholder="e.g. 144.9631"
        )

    manual_site = st.text_input(
        "Site Name / Address",
        value=site_search,
        placeholder="e.g. Sunshine Depot, Melbourne VIC"
    )

    if st.button("✅ Confirm Manual Location"):
        if manual_lat and manual_lon:
            st.session_state.latitude  = manual_lat
            st.session_state.longitude = manual_lon
            st.success(f"📍 Location set: {manual_lat}, {manual_lon}")
            st.rerun()
        else:
            st.warning("Please enter both latitude and longitude.")

# Resolve final values
latitude      = st.session_state.latitude  or "Unknown"
longitude     = st.session_state.longitude or "Unknown"
location_name = manual_site if 'manual_site' in dir() and manual_site else (site_search or "")

# Show current location status
if latitude != "Unknown":
    st.success(f"📍 Location ready: **{latitude}, {longitude}** {('— ' + location_name) if location_name else ''}")
else:
    st.warning("⚠️ No location set — you can still save but location will be logged as Unknown.")

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
    image_np    = np.array(input_image)

    st.image(input_image, caption="Input Image", use_container_width=True)

    with st.spinner("🔍 AI is reading label..."):
        results   = reader.readtext(image_np)
        full_blob = " ".join([res[1] for res in results])

    # Extraction
    wattage = re.findall(r'(\d{3,4})\s?[Ww](?!h)', full_blob)
    voltage = re.findall(r'(\d{2,3}\.?\d*)\s?[Vv]', full_blob)
    model   = re.findall(r'(TSM-\w+|JKM\d+\w*|LR\d-\w+|CS\d+-\w+|JAM\d+\w*|[A-Z]{2,4}[-_]\d{2,4}[-_]\w+)', full_blob)
    serial  = re.findall(r'(?:S/?N|Serial\s*(?:No|Number|#)?)[:\s#\-]*([A-Z0-9]{6,20})', full_blob, re.IGNORECASE)
    if not serial:
        serial = re.findall(r'\b([A-Z]{2,4}\d{8,16})\b', full_blob)

    extracted_pmax   = wattage[0] if wattage else "N/A"
    extracted_voc    = voltage[0] if voltage else "N/A"
    extracted_model  = model[0]   if model   else "N/A"
    extracted_serial = serial[0]  if serial  else "N/A"

    st.markdown("### 📊 Extracted Data")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Model",          extracted_model)
    col2.metric("Wattage (Pmax)", f"{extracted_pmax} W")
    col3.metric("Voltage (Voc)",  f"{extracted_voc} V")
    col4.metric("Serial Number",  extracted_serial)

    st.markdown("#### 🧾 Full OCR Text")
    st.text_area("", full_blob, height=120)

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
            st.success("✅ Logged to Google Sheets!")

            if latitude != "Unknown":
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

        map_df = df[["Latitude", "Longitude"]].dropna()
        map_df = map_df[(map_df["Latitude"] != "Unknown") & (map_df["Latitude"] != "N/A")]
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