import streamlit as st
import zipfile, os, requests
from fastkml import kml
import pandas as pd

st.title("AGM Aerial Image Extractor")
st.markdown("Upload a `.kml` or `.kmz` file containing AGMs and get satellite images for each point.")

API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]  # Store securely in .streamlit/secrets.toml

def extract_kml(file):
    if file.name.endswith('.kmz'):
        with zipfile.ZipFile(file, 'r') as zip_ref:
            zip_ref.extractall("temp_kmz")
        with open("temp_kmz/doc.kml", 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return file.read().decode("utf-8")

def parse_agms(kml_string):
    k = kml.KML()
    k.from_string(kml_string)
    folders = list(next(k.features()).features())
    agm_folder = next((f for f in folders if f.name == "AGMs"), None)
    if not agm_folder:
        st.error("No folder named 'AGMs' found.")
        return []
    return [(p.name, p.geometry.coords[0]) for p in agm_folder.features()]

def get_image_url(lat, lon):
    return f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=18&size=600x600&maptype=satellite&key={API_KEY}"

uploaded_file = st.file_uploader("Upload KML/KMZ", type=["kml", "kmz"])
if uploaded_file:
    kml_data = extract_kml(uploaded_file)
    agms = parse_agms(kml_data)

    if agms:
        df = pd.DataFrame(agms, columns=["AGM Name", "Coordinates"])
        df["Latitude"] = df["Coordinates"].apply(lambda x: x[1])
        df["Longitude"] = df["Coordinates"].apply(lambda x: x[0])
        df["Image URL"] = df.apply(lambda row: get_image_url(row["Latitude"], row["Longitude"]), axis=1)

        st.success(f"Found {len(df)} AGMs.")
        for _, row in df.iterrows():
            st.subheader(row["AGM Name"])
            st.image(row["Image URL"], caption=f"{row['AGM Name']} @ ({row['Latitude']}, {row['Longitude']})")

        st.download_button("Download AGM CSV", df.drop(columns=["Coordinates"]).to_csv(index=False), "agm_images.csv")
