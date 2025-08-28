import streamlit as st
import pandas as pd
import zipfile
import io
import requests
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

# 🔑 Your Google Maps Static API Key
API_KEY = "AIzaSyCd7sfheaJIbB8_J9Q9cxWb5jnv4U0K0LA"

st.title("📍 AGM Satellite Snapshot Generator")

uploaded_file = st.file_uploader("Upload KMZ or KML file", type=["kmz", "kml"])

# --- Extract KML from KMZ ---
def extract_kml_from_kmz(kmz_bytes):
    with zipfile.ZipFile(io.BytesIO(kmz_bytes)) as z:
        for name in z.namelist():
            if name.endswith(".kml"):
                return z.read(name)
    return None

# --- Parse KML using XML ---
def parse_kml(kml_bytes):
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    root = ET.fromstring(kml_bytes)
    placemarks = []

    # Find all folders named "AGMs"
    for folder in root.findall(".//kml:Folder", ns):
        name_el = folder.find("kml:name", ns)
        if name_el is not None and name_el.text.strip().lower() == "agms":
            for pm in folder.findall("kml:Placemark", ns):
                name_el = pm.find("kml:name", ns)
                coord_el = pm.find(".//kml:Point/kml:coordinates", ns)
                if name_el is not None and coord_el is not None:
                    name = name_el.text.strip().replace(" ", "_")
                    coords = coord_el.text.strip().split(",")
                    if len(coords) >= 2:
                        lon = float(coords[0])
                        lat = float(coords[1])
                        placemarks.append({
                            "AGM Name": name,
                            "Latitude": lat,
                            "Longitude": lon
                        })
    return pd.DataFrame(placemarks)


# --- Fetch and annotate satellite image ---
def fetch_satellite_image(lat, lon, name):
    url = (
        f"https://maps.googleapis.com/maps/api/staticmap?"
        f"center={lat},{lon}&zoom=18&size=640x640&maptype=satellite&key={API_KEY}"
    )
    response = requests.get(url)
    if response.status_code != 200:
        return None

    image = Image.open(io.BytesIO(response.content)).convert("RGB")
    draw = ImageDraw.Draw(image)

    font_size = 24
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    label = name.replace("_", " ")

    # AGM coordinate is at center of image
    center_x = image.width // 2
    center_y = image.height // 2

    # Draw yellow dot at AGM location
    dot_radius = 6
    draw.ellipse(
        [
            (center_x - dot_radius, center_y - dot_radius),
            (center_x + dot_radius, center_y + dot_radius)
        ],
        fill="yellow",
        outline="black"
    )

    # Measure text size
    try:
        bbox = font.getbbox(label)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = draw.textlength(label, font=font), font_size

    # Offset label slightly above and to the right of the dot
    label_x = center_x + dot_radius + 4
    label_y = center_y - text_height - 4

    # Draw semi-transparent background behind text
    box_margin = 4
    box_coords = [
        label_x - box_margin,
        label_y - box_margin,
        label_x + text_width + box_margin,
        label_y + text_height + box_margin
    ]
    draw.rectangle(box_coords, fill=(0, 0, 0, 180))

    # Draw label
    draw.text((label_x, label_y), label, fill="white", font=font)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.read()

# --- Main logic ---
if uploaded_file:
    if uploaded_file.name.endswith(".kmz"):
        kml_bytes = extract_kml_from_kmz(uploaded_file.read())
    else:
        kml_bytes = uploaded_file.read()

    df = parse_kml(kml_bytes)

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
                label="📦 Download Annotated AGM Images ZIP",
                data=zip_buffer,
                file_name="agm_satellite_images.zip",
                mime="application/zip"
            )
