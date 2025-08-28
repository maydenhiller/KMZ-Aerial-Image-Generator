import streamlit as st
import pandas as pd
import zipfile
import io
import requests
from fastkml import kml
from shapely.geometry import Point

API_KEY = "AIzaSyCd7sfheaJIbB8_J9Q9cxWb5jnv4U0K0LA"

st.title("📍 AGM Satellite Snapshot Generator")

uploaded_file = st.file_uploader("Upload KMZ or KML file", type=["kmz", "kml"])

def extract_kml_from_kmz(kmz_bytes):
    with zipfile.ZipFile(io.BytesIO(kmz_bytes)) as z:
        for name in z.namelist():
            if name.endswith(".kml"):
                return z.read(name)
    return None

def extract_all_placemarks(element):
    placemarks = []
    if hasattr(element, 'features'):
        for f in element.features():
            placemarks.extend(extract_all_placemarks(f))
    elif isinstance(element.geometry, Point):
        lon, lat = element.geometry.x, element.geometry.y
        name = element.name.strip().replace(" ", "_") if element.name else "Unnamed"
        placemarks.append({"AGM Name": name, "Latitude": lat, "Longitude": lon})
    return placemarks

def parse_agms(kml_bytes):
    k = kml.KML()
    k.from_string(kml_bytes)
    all_features = []
    for feature in k.features():
        all_features.extend(extract_all_placemarks(feature))
    return pd.DataFrame(all_features)

def fetch_satellite_image(lat, lon, name):
    url = (
        f"https://maps.googleapis.com/maps/api/staticmap?"
        f"center={lat},{lon}&zoom=18&size=640x640&maptype=satellite&key={API_KEY}"
    )
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    return None

if uploaded_file:
    if uploaded_file.name.endswith(".kmz"):
        kml_bytes = extract_kml_from_kmz(uploaded_file.read())
    else:
        kml_bytes = uploaded_file.read()

    df = parse_agms(kml_bytes)

    if df.empty:
        st.error("No valid placemarks with coordinates found.")
    else:
        st.success(f"Found {len(df)} placemarks")
        st.dataframe(df)

        if st.button("Generate Satellite Images"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for _, row in df.iterrows():
                    name = row["AGM Name"]
                    lat, lon = row["Latitude"], row["Longitude"]
                    image_data = fetch_satellite_image(lat, lon, name)
                    if image_data:
                        zip_file.writestr(f"{name}.jpg", image_data)
            zip_buffer.seek(0)
            st.download_button(
                label="📦 Download Satellite Image ZIP",
                data=zip_buffer,
                file_name="agm_satellite_images.zip",
                mime="application/zip"
            )
