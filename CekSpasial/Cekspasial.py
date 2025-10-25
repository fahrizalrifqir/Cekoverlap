import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import contextily as ctx
import matplotlib.patches as mpatches
import requests
import tempfile
import os
import io

# -------------------------------------------------------------------
# 🧭 Konfigurasi Halaman
# -------------------------------------------------------------------
st.set_page_config(page_title="Overlay Tapak Proyek", layout="wide")
st.title("🗺️ Analisis Overlay Tapak Proyek dengan PIPPIB / Kawasan Hutan")

# -------------------------------------------------------------------
# 🔗 Link Google Drive (ubah sesuai kebutuhan)
# -------------------------------------------------------------------
url_pippib = "https://drive.google.com/uc?export=download&id=1trh7h1SG1-AcuRfyaUqJq-qMJWKPiaez"
url_kawasan = "https://drive.google.com/uc?export=download&id=11cFQG0jdDauc0mOha8AiTndB-AqRB7GA"

# -------------------------------------------------------------------
# 📦 Fungsi memuat data dari Google Drive
# -------------------------------------------------------------------
@st.cache_data
def load_overlay_data(option):
    """Mengunduh dan memuat GeoJSON overlay dari Google Drive"""
    url = url_pippib if option == "PIPPIB" else url_kawasan
    st.info(f"📥 Mengunduh data {option} dari Google Drive, mohon tunggu...")

    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise Exception(f"Gagal mengunduh {option}: status {response.status_code}")

    total_length = int(response.headers.get("content-length", 0))
    progress_bar = st.progress(0)
    downloaded = 0

    with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson") as tmpfile:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                tmpfile.write(chunk)
                downloaded += len(chunk)
                if total_length:
                    progress = int(downloaded / total_length * 100)
                    progress_bar.progress(progress)
        tmp_path = tmpfile.name

    progress_bar.empty()

    # Validasi isi file
    with open(tmp_path, "rb") as f:
        head = f.read(500)
        if b"<html" in head.lower():
            os.remove(tmp_path)
            raise ValueError(
                f"File {option} bukan GeoJSON asli. "
                "Pastikan link Drive sudah berbentuk tautan unduhan langsung."
            )

    try:
        gdf = gpd.read_file(tmp_path, driver="GeoJSON")
        gdf = gdf.to_crs(epsg=4326)
    finally:
        os.remove(tmp_path)

    return gdf

# -------------------------------------------------------------------
# 🔘 Pilihan Overlay
# -------------------------------------------------------------------
overlay_option = st.radio(
    "Pilih Layer Overlay:",
    ["PIPPIB", "Kawasan Hutan"],
    horizontal=True
)

# -------------------------------------------------------------------
# 📥 Load Data Overlay
# -------------------------------------------------------------------
try:
    gdf_overlay = load_overlay_data(overlay_option)
    st.success(f"✅ Layer {overlay_option} berhasil dimuat ({len(gdf_overlay)} fitur)")
except Exception as e:
    st.error(f"Gagal memuat layer {overlay_option}: {e}")
    st.stop()

# -------------------------------------------------------------------
# 📤 Upload Tapak Proyek (SHP dalam ZIP)
# -------------------------------------------------------------------
uploaded_file = st.file_uploader("Unggah file SHP tapak proyek (.zip)", type=["zip"])

if uploaded_file:
    try:
        st.info("📂 Membaca file SHP tapak proyek...")
        gdf_tapak = gpd.read_file(f"zip://{uploaded_file}")
        gdf_tapak = gdf_tapak.to_crs(epsg=4326)

        st.info("🔎 Menghitung area overlap...")
        gdf_overlay_valid = gdf_overlay[gdf_overlay.is_valid]
        overlap = gpd.overlay(gdf_tapak, gdf_overlay_valid, how="intersection")

        if overlap.empty:
            st.warning("⚠️ Tidak ada area overlap yang ditemukan.")
        else:
            # Hitung luas overlap (ha)
            overlap = overlap.to_crs(epsg=3857)
            overlap["Luas_ha"] = overlap.geometry.area / 10000
            total_luas = overlap["Luas_ha"].sum()

            st.success(f"✅ Ditemukan {len(overlap)} area overlap, total luas {total_luas:,.2f} ha")

            # -------------------------------------------------------------------
            # 🧭 Peta Interaktif
            # -------------------------------------------------------------------
            st.subheader("🌍 Peta Interaktif")
            m = folium.Map(location=[-2, 117], zoom_start=5)
            folium.GeoJson(
                gdf_overlay, name=overlay_option,
                style_function=lambda x: {"color": "green", "weight": 1}
            ).add_to(m)
            folium.GeoJson(
                gdf_tapak, name="Tapak Proyek",
                style_function=lambda x: {"color": "blue", "weight": 2}
            ).add_to(m)
            folium.GeoJson(
                overlap, name="Overlap",
                style_function=lambda x: {"color": "red", "fillOpacity": 0.4}
            ).add_to(m)
            folium.LayerControl().add_to(m)
            st_folium(m, height=500)

            # -------------------------------------------------------------------
            # 🖼️ Layout PNG
            # -------------------------------------------------------------------
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

                ctx.add_basemap(ax, crs=3857, source=ctx.providers.Esri.WorldImagery)

                ax.set_xlim(xmin - (xmax - xmin) * 0.05, xmax + (xmax - xmin) * 0.05)
                ax.set_ylim(ymin - (ymax - ymin) * 0.05, ymax + (ymax - ymin) * 0.05)
                ax.axis("off")
                ax.set_title(f"Peta Overlay Tapak Proyek dengan {overlay_option}", fontsize=14, pad=15)

                # Legenda dinamis
                legend_elements = [
                    mpatches.Patch(facecolor="blue", alpha=0.3, label="Tapak Proyek"),
                    mpatches.Patch(facecolor="none", edgecolor="green", label=overlay_option),
                    mpatches.Patch(facecolor="red", alpha=0.4, label="Overlap Area"),
                ]
                ax.legend(handles=legend_elements, loc="upper right", fontsize=9, frameon=True)

                # Outline hitam di sekeliling peta
                for spine in ax.spines.values():
                    spine.set_edgecolor('black')
                    spine.set_linewidth(1.5)

                buf = io.BytesIO()
                plt.savefig(buf, format="png", bbox_inches="tight", dpi=200)
                buf.seek(0)
                plt.close(fig)

                st.download_button(
                    "⬇️ Download Peta PNG",
                    data=buf,
                    file_name=f"Peta_Overlay_{overlay_option}.png",
                    mime="image/png"
                )

            except Exception as e:
                st.error(f"Gagal membuat layout PNG: {e}")

    except Exception as e:
        st.error(f"Gagal memproses file: {e}")

else:
    st.info("📤 Unggah file tapak proyek (.zip) terlebih dahulu untuk mulai analisis.")
