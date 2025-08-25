import streamlit as st
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import requests
import os

st.set_page_config(page_title="AGM Snapshot Generator", layout="centered")
st.title("📸 AGM Satellite Snapshot Generator")

GOOGLE_MAPS_API_KEY = st.secrets["AIzaSyB9HxznAvlGb02e-K1rhld_CPeAm_wvPWU"]
output_dir = "agm_images"
os.makedirs(output_dir, exist_ok=True)

def extract_agms(file):
    if file.name.endswith('.kmz'):
        with ZipFile(file) as zf:
            kml_data = zf.read('doc.kml').decode('utf-8')
    else:
        kml_data = file.read().decode('utf-8')

    root = ET.fromstring(kml_data)
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    agms = []
    for folder in root.findall(".//kml:Folder", ns):
        name_tag = folder.find("kml:name", ns)
        if name_tag is not None and name_tag.text == "AGMs":
            for placemark in folder.findall("kml:Placemark", ns):
                name = placemark.find("kml:name", ns).text
                coords = placemark.find(".//kml:coordinates", ns).text.strip()
                lon, lat, *_ = coords.split(",")
                agms.append((name, float(lat), float(lon)))
    return agms

def fetch_satellite_image(name, lat, lon, zoom=18):
    url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom={zoom}&size=800x800&maptype=satellite&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        with open(os.path.join(output_dir, f"{name}.jpg"), "wb") as f:
            f.write(response.content)

uploaded_file = st.file_uploader("Upload KMZ or KML file", type=["kmz", "kml"])

if uploaded_file:
    st.info("Parsing file...")
    agms = extract_agms(uploaded_file)
    st.success(f"Found {len(agms)} AGMs")

    if st.button("Generate Snapshots"):
        for i, (name, lat, lon) in enumerate(agms):
            st.write(f"Capturing {name} ({i+1}/{len(agms)})...")
            fetch_satellite_image(name, lat, lon)
        st.success("✅ All snapshots saved to 'agm_images' folder.")
