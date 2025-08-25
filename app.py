import streamlit as st
import simplekml
from zipfile import ZipFile
from io import BytesIO
import requests
import os

st.set_page_config(page_title="AGM Snapshot Generator", layout="centered")
st.title("📸 AGM Satellite Snapshot Generator")

GOOGLE_MAPS_API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
output_dir = "agm_images"
os.makedirs(output_dir, exist_ok=True)

def extract_agms(file):
    if file.name.endswith('.kmz'):
        with ZipFile(file) as zf:
            kml_data = zf.read('doc.kml')
    else:
        kml_data = file.read()

    kml_obj = simplekml.Kml()
    kml_obj.from_string(kml_data)
    agms = []
    for placemark in kml_obj.features():
        if placemark.name and placemark.geometry:
            coords = placemark.geometry.coords[0]
            agms.append((placemark.name, coords))
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
        for i, (name, (lon, lat)) in enumerate(agms):
            st.write(f"Capturing {name} ({i+1}/{len(agms)})...")
            fetch_satellite_image(name, lat, lon)
        st.success("✅ All snapshots saved to 'agm_images' folder.")
