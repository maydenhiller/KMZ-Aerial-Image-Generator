import io
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

APP_TITLE = "📍 AGM Satellite Snapshot Generator"

# Matches "Picture 5" in the provided spreadsheet (Pre_Dig_Photos sheet).
OUTPUT_WIDTH_PX = 275
OUTPUT_HEIGHT_PX = 183

# Fetch larger imagery then downscale for sharper results.
FETCH_SCALE = 4
MAPBOX_MAX_DIM_PX = 1280


def extract_kml_from_kmz(kmz_bytes: bytes) -> bytes | None:
    with zipfile.ZipFile(io.BytesIO(kmz_bytes)) as z:
        for name in z.namelist():
            if name.lower().endswith(".kml"):
                return z.read(name)
    return None


def parse_kml_agms_folder(kml_bytes: bytes) -> pd.DataFrame:
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    root = ET.fromstring(kml_bytes)
    placemarks: list[dict[str, object]] = []

    for folder in root.findall(".//kml:Folder", ns):
        folder_name_el = folder.find("kml:name", ns)
        if folder_name_el is None or not folder_name_el.text:
            continue

        if folder_name_el.text.strip().lower() != "agms":
            continue

        for pm in folder.findall("kml:Placemark", ns):
            name_el = pm.find("kml:name", ns)
            coord_el = pm.find(".//kml:Point/kml:coordinates", ns)
            if name_el is None or coord_el is None or not coord_el.text:
                continue

            name = (name_el.text or "").strip()
            coords = coord_el.text.strip().split(",")
            if len(coords) < 2:
                continue

            try:
                lon = float(coords[0])
                lat = float(coords[1])
            except ValueError:
                continue

            placemarks.append({"AGM Name": name, "Latitude": lat, "Longitude": lon})

    return pd.DataFrame(placemarks, columns=["AGM Name", "Latitude", "Longitude"])


def _get_resample_lanczos():
    try:
        return Image.Resampling.LANCZOS  # Pillow >= 9
    except AttributeError:
        return Image.LANCZOS


def _load_font(size_px: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size_px)
    except Exception:
        return ImageFont.load_default()


def fetch_satellite_image_exact_size(lat: float, lon: float, name: str, mapbox_token: str) -> bytes | None:
    fetch_w = min(int(OUTPUT_WIDTH_PX * FETCH_SCALE), MAPBOX_MAX_DIM_PX)
    fetch_h = min(int(OUTPUT_HEIGHT_PX * FETCH_SCALE), MAPBOX_MAX_DIM_PX)
    scale = fetch_w / OUTPUT_WIDTH_PX

    url = (
        "https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"{lon},{lat},18,0/{fetch_w}x{fetch_h}"
        f"?access_token={mapbox_token}"
    )

    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        return None

    image = Image.open(io.BytesIO(response.content)).convert("RGB")
    draw = ImageDraw.Draw(image)

    label = (name or "").upper()
    font_size = max(10, int(14 * scale))
    font = _load_font(font_size)

    center_x = image.width // 2
    center_y = image.height // 2

    dot_radius = max(2, int(3 * scale))
    draw.ellipse(
        [
            (center_x - dot_radius, center_y - dot_radius),
            (center_x + dot_radius, center_y + dot_radius),
        ],
        fill="yellow",
        outline="black",
        width=max(1, int(1 * scale)),
    )

    try:
        bbox = font.getbbox(label)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except Exception:
        text_w = int(draw.textlength(label, font=font))
        text_h = font_size

    margin = max(2, int(3 * scale))
    offset = max(2, int(3 * scale))
    label_x = center_x + dot_radius + offset
    label_y = center_y - text_h - offset

    box = [
        label_x - margin,
        label_y - margin,
        label_x + text_w + margin,
        label_y + text_h + margin,
    ]
    draw.rectangle(box, fill="white", outline="black", width=max(1, int(1 * scale)))
    draw.text((label_x, label_y), label, fill="black", font=font)

    # Downscale to exact template size (Picture 5) for output.
    resample = _get_resample_lanczos()
    image = image.resize((OUTPUT_WIDTH_PX, OUTPUT_HEIGHT_PX), resample=resample)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95, optimize=True)
    buffer.seek(0)
    return buffer.read()


def main():
    st.set_page_config(page_title="AGM Satellite Snapshot Generator", layout="centered")
    st.title(APP_TITLE)

    try:
        mapbox_token = st.secrets["mapbox"]["token"]
    except Exception:
        st.error("Missing Mapbox token. Set `st.secrets['mapbox']['token']`.")
        return

    st.caption(f"Output size: {OUTPUT_WIDTH_PX}×{OUTPUT_HEIGHT_PX} px (matches spreadsheet Picture 5).")

    uploaded_file = st.file_uploader("Upload KMZ or KML file", type=["kmz", "kml"])
    if not uploaded_file:
        st.info("Awaiting file upload.")
        return

    raw = uploaded_file.read()
    if uploaded_file.name.lower().endswith(".kmz"):
        kml_bytes = extract_kml_from_kmz(raw)
        if kml_bytes is None:
            st.error("No KML found inside the uploaded KMZ.")
            return
    else:
        kml_bytes = raw

    df = parse_kml_agms_folder(kml_bytes)
    if df.empty:
        st.error("No valid AGM placemarks found in the 'AGMs' folder.")
        return

    st.success(f"Found {len(df)} AGMs")
    st.dataframe(df, use_container_width=True)

    if st.button("Generate Satellite Images"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for _, row in df.iterrows():
                name = str(row["AGM Name"])
                lat = float(row["Latitude"])
                lon = float(row["Longitude"])
                image_data = fetch_satellite_image_exact_size(lat, lon, name, mapbox_token)
                if image_data:
                    safe_name = "".join(c for c in name if c not in '\\\\/:*?\"<>|').strip() or "AGM"
                    zip_file.writestr(f"{safe_name}.jpg", image_data)

        zip_buffer.seek(0)
        st.download_button(
            label="📦 Download Annotated AGM Images ZIP",
            data=zip_buffer,
            file_name="agm_satellite_images.zip",
            mime="application/zip",
        )

    st.caption("© Mapbox © OpenStreetMap contributors")


if __name__ == "__main__":
    main()

