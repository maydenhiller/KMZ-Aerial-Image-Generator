import streamlit as st
import pandas as pd
import zipfile
import io
from fastkml import kml
from shapely.geometry import Point
from staticmap import StaticMap, CircleMarker
from PIL import Image

st.title("📍 AGM Snapshot Generator (Streamlit Cloud)")

uploaded_file = st.file_uploader("Upload KML or KMZ file", type=["kml", "kmz"])

def extract_kml(kmz_bytes):
    with zipfile.ZipFile(io.BytesIO(kmz_bytes)) as z:
        for name in z.namelist():
            if name.endswith(".kml"):
                return z.read(name)
    return None

def parse_agms(kml_bytes):
    k = kml.KML()
    k.from_string(kml_bytes)
    placemarks = []
    for doc in k.features():
        for folder in doc.features():
            for pm in folder.features():
                if isinstance(pm.geometry, Point):
                    lon, lat = pm.geometry.x, pm.geometry.y
                    placemarks.append({
                        "AGM Name": pm.name,
                        "Latitude": lat,
                        "Longitude": lon
                    })
    return pd.DataFrame(placemarks)

def generate_image(lat, lon, name):
    m = StaticMap(600, 400)
    marker = CircleMarker((lon, lat), 'red', 12)
    m.add_marker(marker)
    image = m.render()
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer

if uploaded_file:
    if uploaded_file.name.endswith(".kmz"):
        kml_bytes = extract_kml(uploaded_file.read())
    else:
        kml_bytes = uploaded_file.read()

    df = parse_agms(kml_bytes)
    st.success(f"Found {len(df)} AGMs")
    st.dataframe(df)

    if st.button("Generate JPG Snapshots"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for _, row in df.iter
