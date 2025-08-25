import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import os
import requests
from PIL import Image
from io import BytesIO

# --- CONFIG ---
API_KEY = "AIzaSyB9HxznAvlGb02e-K1rhld_CPeAm_wvPWU"
ZOOM = 18
IMG_SIZE = "800x800"
MAPTYPE = "satellite"

# --- FUNCTIONS ---
def extract_agms_from_kmz(kmz_file):
    with zipfile.ZipFile(kmz_file, 'r') as z:
        kml_files = [f for f in z.namelist() if f.endswith('.kml')]
        if not kml_files:
            return []
        with z.open(kml_files[0]) as kml:
            tree = ET.parse(kml)
            root = tree.getroot()
            ns = {'kml': 'http://www.opengis.net/kml/2.2'}
            placemarks = root.findall(".//kml:Placemark", ns)
            agms = []
            for pm in placemarks:
                name = pm.find("kml:name", ns)
                coord = pm.find(".//kml:coordinates", ns)
                if name is not None and coord is not None:
                    lon, lat, *_ = coord.text.strip().split(",")
                    agms.append((name.text.strip(), float(lat), float(lon)))
            return agms

def fetch_satellite_image(lat, lon, name):
    url = (
        f"https://maps.googleapis.com/maps/api/staticmap?"
        f"center={lat},{lon}&zoom={ZOOM}&size={IMG_SIZE}&maptype={MAPTYPE}&key={API_KEY}"
    )
    response = requests.get(url)
    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        filename = f"{name.replace(' ', '_')}.jpg"
        img.save(filename)
        return filename
    return None

# --- STREAMLIT UI ---
st.set_page_config(page_title="AGM Aerial Generator", layout="centered")
st.title("📸 AGM Aerial Image Generator")

st.markdown("Upload a `.kmz` file containing AGM points. This app will generate a satellite `.jpg` for each AGM.")

uploaded_file = st.file_uploader("Upload KMZ file", type=["kmz"])

if uploaded_file:
    with st.spinner("Parsing KMZ and extracting AGM coordinates..."):
        agms = extract_agms_from_kmz(uploaded_file)

    if agms:
        st.success(f"✅ Found {len(agms)} AGMs.")
        for name, lat, lon in agms:
            st.write(f"🛰️ Generating image for **{name}** at ({lat}, {lon})...")
            img_path = fetch_satellite_image(lat, lon, name)
            if img_path:
                st.image(img_path, caption=name, use_column_width=True)
            else:
                st.warning(f"Image fetch failed for {name}.")
    else:
        st.error("❌ No valid AGM coordinates found in the KMZ.")
