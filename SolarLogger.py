import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_js_eval import streamlit_js_eval
from PIL import Image
import pandas as pd
import datetime
import re
import requests
import anthropic
import base64

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
# CLAUDE VISION OCR
# -------------------------------
def read_label_with_claude(image_file):
    """Use Claude vision to extract text from solar panel label."""
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

    image_bytes = image_file.getvalue()
    b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")

    suffix = getattr(image_file, 'name', 'image.jpg').split('.')[-1].lower()
    media_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
    media_type = media_map.get(suffix, "image/jpeg")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64_image
                    }
                },
                {
                    "type": "text",
                    "text": """You are reading a solar panel label. Extract ALL text you can see and return it as a single plain text blob.
Include everything: model numbers, serial numbers, wattage, voltage, current, certifications, manufacturer info.
Return only the raw extracted text, nothing else."""
                }
            ]
        }]
    )
    return response.content[0].text

# -------------------------------
# SESSION STATE INIT
# -------------------------------
if "latitude" not in st.session_state:
    st.session_state.latitude = ""
if "longitude" not in st.session_state:
    st.session_state.longitude = ""
if "location_name" not in st.session_state:
    st.session_state.location_name = ""
if "geo_status" not in st.session_state:
    st.session_state.geo_status = "idle"

# -------------------------------
# LOCATION SECTION
# -------------------------------
st.markdown("### 📍 Location")

# --- AUTO GPS ---
st.markdown("**Option 1: Automatic GPS**")
col_gps1, col_gps2 = st.columns([1, 2])

with col_gps1:
    if st.button("📍 Get GPS Location"):
        st.session_state.geo_status = "waiting"

if st.session_state.geo_status == "waiting":
    coords = streamlit_js_eval(
        js_expressions="""
            new Promise((resolve) => {
                if (!navigator.geolocation) {
                    resolve(null);
                } else {
                    navigator.geolocation.getCurrentPosition(
                        (pos) => resolve({
                            lat: pos.coords.latitude,
                            lon: pos.coords.longitude,
                            acc: pos.coords.accuracy
                        }),
                        () => resolve(null),
                        {enableHighAccuracy: true, timeout: 10000, maximumAge: 0}
                    );
                }
            })
        """,
        key="gps_grab"
    )

    if coords is not None:
        if coords:
            st.session_state.latitude   = str(round(coords["lat"], 6))
            st.session_state.longitude  = str(round(coords["lon"], 6))
            st.session_state.geo_status = "success"
        else:
            st.session_state.geo_status = "failed"
        st.rerun()

with col_gps2:
    if st.session_state.geo_status == "success":
        st.success(f"✅ GPS: {st.session_state.latitude}, {st.session_state.longitude}")
    elif st.session_state.geo_status == "failed":
        st.error("❌ GPS failed — use address search below.")
    elif st.session_state.geo_status == "waiting":
        st.info("📡 Requesting GPS... allow location in your browser.")
    else:
        st.info("Click button to get GPS coordinates.")

st.markdown("---")

# --- ADDRESS SEARCH ---
st.markdown("**Option 2: Search by Address**")

address_input = st.text_input(
    "🔍 Type an address or suburb",
    placeholder="e.g. Sunshine VIC or 123 Main St Melbourne"
)

if address_input and len(address_input) > 3:
    with st.spinner("🔍 Looking up address..."):
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": address_input + ", Australia",
                "format": "json",
                "limit": 5,
                "countrycodes": "au"
            }
            headers = {"User-Agent": "LotusRecyclingLogger/1.0"}
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            results = resp.json()
        except Exception:
            results = []

    if results:
        options = {r["display_name"]: (float(r["lat"]), float(r["lon"])) for r in results}
        selected = st.selectbox("Select the correct address:", list(options.keys()))

        if st.button("✅ Use This Address"):
            lat, lon = options[selected]
            st.session_state.latitude      = str(round(lat, 6))
            st.session_state.longitude     = str(round(lon, 6))
            st.session_state.location_name = selected
            st.session_state.geo_status    = "success"
            st.rerun()
    else:
        st.warning("No results found — try a different search term.")

st.markdown("---")

# --- MANUAL OVERRIDE ---
with st.expander("✏️ Enter coordinates manually"):
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        manual_lat = st.text_input("Latitude",  value=st.session_state.latitude,  placeholder="-37.8136")
    with col_m2:
        manual_lon = st.text_input("Longitude", value=st.session_state.longitude, placeholder="144.9631")
    manual_site = st.text_input("Site Name", value=st.session_state.location_name, placeholder="e.g. Sunshine Depot")

    if st.button("✅ Confirm Manual Entry"):
        if manual_lat and manual_lon:
            st.session_state.latitude      = manual_lat
            st.session_state.longitude     = manual_lon
            st.session_state.location_name = manual_site
            st.success("📍 Manual location saved!")
            st.rerun()
        else:
            st.warning("Please enter both latitude and longitude.")

# --- CURRENT STATUS ---
latitude      = st.session_state.latitude      or "Unknown"
longitude     = st.session_state.longitude     or "Unknown"
location_name = st.session_state.location_name or ""

if latitude != "Unknown":
    st.success(f"📍 Location set: **{latitude}, {longitude}**  {('— ' + location_name) if location_name else ''}")
    if st.button("🔄 Reset Location"):
        st.session_state.latitude      = ""
        st.session_state.longitude     = ""
        st.session_state.location_name = ""
        st.session_state.geo_status    = "idle"
        st.rerun()
else:
    st.warning("⚠️ No location set yet — use GPS or address search above.")

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
    st.image(input_image, caption="Input Image", use_container_width=True)

    with st.spinner("🔍 Claude is reading the label..."):
        full_blob = read_label_with_claude(img_file)

    # -------------------------------
    # EXTRACTION LOGIC
    # -------------------------------
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

    # -------------------------------
    # DISPLAY RESULTS
    # -------------------------------
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
            except Exception:
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
            except Exception:
                pass

except Exception as e:
    st.error(f"⚠️ Database connection error: {e}")