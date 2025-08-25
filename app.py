import streamlit as st
from fastkml import kml
from zipfile import ZipFile
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import os

st.set_page_config(page_title="AGM Snapshot Generator", layout="centered")
st.title("📸 AGM Satellite Snapshot Generator")

# Create output folder
output_dir = "agm_images"
os.makedirs(output_dir, exist_ok=True)

def extract_agms(file):
    if file.name.endswith('.kmz'):
        with ZipFile(file) as zf:
            kml_data = zf.read('doc.kml')  # adjust if nested differently
    else:
        kml_data = file.read()

    k = kml.KML()
    k.from_string(kml_data)
    agms = []
    for feature in k.features():
        for folder in feature.features():
            if folder.name == "AGMs":
                for placemark in folder.features():
                    name = placemark.name
                    coords = list(placemark.geometry.coords)[0]
                    agms.append((name, coords))
    return agms

def capture_satellite_image(name, lat, lon, zoom=18):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--window-size=800,800')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)

    url = f"https://www.google.com/maps/@{lat},{lon},{zoom}z/data=!3m1!1e3"
    driver.get(url)
    time.sleep(3)  # allow map to load
    filename = os.path.join(output_dir, f"{name}.jpg")
    driver.save_screenshot(filename)
    driver.quit()

uploaded_file = st.file_uploader("Upload KMZ or KML file", type=["kmz", "kml"])

if uploaded_file:
    st.info("Parsing file...")
    agms = extract_agms(uploaded_file)
    st.success(f"Found {len(agms)} AGMs")

    if st.button("Generate Snapshots"):
        for i, (name, (lon, lat)) in enumerate(agms):
            st.write(f"Capturing {name} ({i+1}/{len(agms)})...")
            capture_satellite_image(name, lat, lon)
        st.success("✅ All snapshots saved to 'agm_images' folder.")
