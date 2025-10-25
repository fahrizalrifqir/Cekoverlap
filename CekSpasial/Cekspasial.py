# streamlit_overlay_geojson.py
import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from shapely.geometry import Polygon, MultiPolygon
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import contextily as ctx
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import io

st.set_page_config(page_title="Overlay Tapak Proyek", layout="wide")

st.title("🗺️ Analisis Overlay Tapak Proyek dengan PIPPIB / Kawasan Hutan")

# Pilihan overlay
overlay_option = st.radio(
    "Pilih Layer Overlay:",
    ["PIPPIB", "Kawasan Hutan"],
    horizontal=True
)

# Load data dari Google Drive (format GeoJSON)
url_pippib = "https://drive.google.com/uc?id=1trh7h1SG1-AcuRfyaUqJq-qMJWKPiaez"
url_kawasan = "https://drive.google.com/uc?id=11cFQG0jdDauc0mOha8AiTndB-AqRB7GA"

@st.cache_data
def load_overlay_data(option):
    if option == "PIPPIB":
        gdf = gpd.read_file(url_pippib)
    else:
        gdf = gpd.read_file(url_kawasan)
    gdf = gdf.to_crs(epsg=4326)
    return gdf

gdf_overlay = load_overlay_data(overlay_option)

# Upload shapefile tapak proyek (ZIP)
uploaded_file = st.file_uploader("Unggah file SHP tapak proyek (.zip)", type=["zip"])

if uploaded_file:
    with st.spinner("Membaca data tapak proyek..."):
        gdf_tapak = gpd.read_file(f"zip://{uploaded_file}")
        gdf_tapak = gdf_tapak.to_crs(epsg=4326)
    
    # Hitung overlap
    with st.spinner("Menghitung area overlap..."):
        gdf_overlay_valid = gdf_overlay[gdf_overlay.is_valid]
        overlap = gpd.overlay(gdf_tapak, gdf_overlay_valid, how="intersection")
    
    # Hitung luas overlap (hektar)
    overlap = overlap.to_crs(epsg=3857)
    overlap["Luas_ha"] = overlap.geometry.area / 10000
    
    st.success(f"✅ Ditemukan {len(overlap)} area overlap, total luas {overlap['Luas_ha'].sum():,.2f} ha")

    # --- Peta interaktif ---
    st.subheader("🧭 Peta Interaktif")
    m = folium.Map(location=[-2, 117], zoom_start=5)
    folium.GeoJson(gdf_overlay, name=overlay_option, style_function=lambda x: {"color": "green", "weight": 1}).add_to(m)
    folium.GeoJson(gdf_tapak, name="Tapak Proyek", style_function=lambda x: {"color": "blue", "weight": 2}).add_to(m)
    folium.GeoJson(overlap, name="Overlap", style_function=lambda x: {"color": "red", "fillOpacity": 0.4}).add_to(m)
    folium.LayerControl().add_to(m)
    st_folium(m, height=500)

    # --- Layout PNG ---
    st.subheader("🖼️ Download Layout Peta PNG")

    try:
        gdf_tapak_3857 = gdf_tapak.to_crs(epsg=3857)
        gdf_overlay_3857 = gdf_overlay.to_crs(epsg=3857)
        overlap_3857 = overlap.to_crs(epsg=3857)

        xmin, ymin, xmax, ymax = gdf_tapak_3857.total_bounds
        fig, ax = plt.subplots(figsize=(10, 10), dpi=150)
        gdf_overlay_3857.plot(ax=ax, facecolor="none", edgecolor="green", linewidth=1)
        gdf_tapak_3857.plot(ax=ax, facecolor="blue", alpha=0.3)
        overlap_3857.plot(ax=ax, facecolor="red", alpha=0.4)

        ctx.add_basemap_
