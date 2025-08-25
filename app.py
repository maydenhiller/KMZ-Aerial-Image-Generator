import streamlit as st
import pandas as pd
import zipfile
import io
import os
from fastkml import kml
from shapely.geometry import Point
import folium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image

st.title("📍 AGM Snapshot Generator")

uploaded_file = st.file_uploader("Upload KML or KMZ file", type=["kml", "kmz"])

def extract_kml_from_kmz(kmz_bytes):
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

def render_map(lat, lon, name):
    m = folium.Map(location=[lat, lon], zoom_start=16)
    folium.Marker([lat, lon], popup=name).add_to(m)
    return m

def save_map_as_image(m, filename):
    # Save HTML
    m.save("temp_map.html")

    # Headless browser to capture image
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=800,600")
    driver = webdriver.Chrome(options=options)
    driver.get("file://" + os.path.abspath("temp_map.html"))
    driver.save_screenshot(filename)
    driver.quit()

if uploaded_file:
    if uploaded_file.name.endswith(".kmz"):
        kml_bytes = extract_kml_from_kmz(uploaded_file.read())
    else:
        kml_bytes = uploaded_file.read()

    df = parse_agms(kml_bytes)
    st.success(f"Found {len(df)} AGMs")
    st.dataframe(df)

    if st.button("Generate JPGs"):
        os.makedirs("agm_images", exist_ok=True)
        for _, row in df.iterrows():
            name = row["AGM Name"].replace(" ", "_")
            lat, lon = row["Latitude"], row["Longitude"]
            m = render_map(lat, lon, name)
            filename = f"agm_images/{name}.jpg"
            save_map_as_image(m, filename)
        st.success("Images saved to agm_images folder")
