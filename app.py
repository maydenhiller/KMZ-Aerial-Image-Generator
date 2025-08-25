import streamlit as st
from fastkml import kml
from zipfile import ZipFile
from io import BytesIO

def extract_agms(file):
    if file.name.endswith('.kmz'):
        with ZipFile(file) as zf:
            kml_data = zf.read('doc.kml')  # adjust if nested
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
