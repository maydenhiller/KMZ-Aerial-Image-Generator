import streamlit as st
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import folium
from folium.plugins import MarkerCluster
import os

st.set_page_config(page_title="AGM Map Generator", layout="centered")
st.title("🗺️ AGM Map Snapshot Generator")

output_dir = "agm_maps"
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

def create_map(name, lat, lon):
    m = folium.Map(location=[lat, lon], zoom_start=18, tiles="Stamen Terrain")
    folium.Marker([lat, lon], popup=name).add_to(m)
    map_path = os.path.join(output_dir, f"{name}.html")
    m.save(map_path)
    return map_path

uploaded_file = st.file_uploader("Upload KMZ or KML file", type=["kmz", "kml"])

if uploaded_file:
    st.info("Parsing file...")
    agms = extract_agms(uploaded_file)
    st.success(f"Found {len(agms)} AGMs")

    if st.button("Generate Maps"):
        for i, (name, lat, lon) in enumerate(agms):
            st.write(f"Rendering {name} ({i+1}/{len(agms)})...")
            map_path = create_map(name, lat, lon)
            st.markdown(f"[View {name} Map]({map_path})")
        st.success("✅ All maps saved as HTML in 'agm_maps' folder.")
