import streamlit as st
import geopandas as gpd
import requests
import tempfile
import folium
from shapely.geometry import Polygon, MultiPolygon
from streamlit_folium import st_folium

# ------------------------------
# Konfigurasi dasar
# ------------------------------
st.set_page_config(page_title="Cek Spasial PIPPIB & Kawasan Hutan", layout="wide")
st.title("🌳 Cek Spasial PIPPIB dan Kawasan Hutan")
st.caption("Aplikasi ini menampilkan peta dan analisis tumpang tindih (overlap) antara PIPPIB dan Kawasan Hutan.")

# ------------------------------
# Fungsi bantu
# ------------------------------
def gdrive_to_download_url(url: str):
    """Ubah tautan Google Drive menjadi tautan unduhan langsung"""
    if "drive.google.com" not in url:
        return url
    file_id = None
    if "id=" in url:
        file_id = url.split("id=")[-1]
    elif "/d/" in url:
        file_id = url.split("/d/")[1].split("/")[0]
    return f"https://drive.google.com/uc?export=download&id={file_id}" if file_id else url


@st.cache_data(show_spinner=False)
def download_geojson_from_drive(url: str):
    """Unduh GeoJSON besar dari Google Drive dan simpan di file sementara"""
    try:
        download_url = gdrive_to_download_url(url)
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson") as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            return tmp_file.name
    except Exception as e:
        st.error(f"Gagal mengunduh file dari Google Drive: {e}")
        return None


@st.cache_data(show_spinner=False)
def load_geojson(path: str):
    """Baca file GeoJSON menjadi GeoDataFrame"""
    try:
        gdf = gpd.read_file(path)
        gdf = gdf.to_crs(epsg=4326)
        return gdf
    except Exception as e:
        st.error(f"Gagal memuat GeoJSON: {e}")
        return None


def calculate_overlap(gdf1, gdf2):
    """Hitung irisan antar dua layer (overlap area)"""
    try:
        gdf1 = gdf1.to_crs(epsg=3857)
        gdf2 = gdf2.to_crs(epsg=3857)
        intersection = gpd.overlay(gdf1, gdf2, how='intersection')
        intersection["luas_m2"] = intersection.geometry.area
        intersection["luas_ha"] = intersection["luas_m2"] / 10000
        return intersection.to_crs(epsg=4326)
    except Exception as e:
        st.error(f"Gagal menghitung overlap: {e}")
        return None


# ------------------------------
# Input tautan dari pengguna
# ------------------------------
st.subheader("🔗 Masukkan tautan data GeoJSON dari Google Drive")

col1, col2 = st.columns(2)
with col1:
    url_pippib = st.text_input(
        "URL PIPPIB",
        "https://drive.google.com/file/d/1trh7h1SG1-AcuRfyaUqJq-qMJWKPiaez/view?usp=drive_link"
    )
with col2:
    url_kawasan = st.text_input(
        "URL Kawasan Hutan",
        "https://drive.google.com/file/d/11cFQG0jdDauc0mOha8AiTndB-AqRB7GA/view?usp=drive_link"
    )

# ------------------------------
# Tombol utama
# ------------------------------
if st.button("🚀 Jalankan Analisis"):
    with st.spinner("Mengunduh dan memproses data..."):
        path_pippib = download_geojson_from_drive(url_pippib)
        path_kawasan = download_geojson_from_drive(url_kawasan)

        if not path_pippib or not path_kawasan:
            st.error("❌ Gagal mengunduh salah satu file.")
            st.stop()

        gdf_pippib = load_geojson(path_pippib)
        gdf_kawasan = load_geojson(path_kawasan)

        if gdf_pippib is None or gdf_kawasan is None:
            st.error("❌ Gagal memuat GeoJSON.")
            st.stop()

    st.success("✅ Data berhasil dimuat!")

    # ------------------------------
    # Analisis overlap
    # ------------------------------
    st.subheader("📊 Hasil Analisis Overlap")
    overlap_gdf = calculate_overlap(gdf_pippib, gdf_kawasan)

    if overlap_gdf is not None and not overlap_gdf.empty:
        total_area_ha = overlap_gdf["luas_ha"].sum()
        st.write(f"**Total Luas Overlap:** {total_area_ha:,.2f} hektar")

        # Simpan hasil overlap ke file sementara
        overlap_path = tempfile.NamedTemporaryFile(delete=False, suffix=".geojson").name
        overlap_gdf.to_file(overlap_path, driver="GeoJSON")

        with open(overlap_path, "rb") as f:
            st.download_button(
                label="⬇️ Unduh Hasil Overlap (GeoJSON)",
                data=f,
                file_name="hasil_overlap.geojson",
                mime="application/geo+json"
            )
    else:
        st.warning("Tidak ditemukan area tumpang tindih antara dua layer.")

    # ------------------------------
    # Peta interaktif
    # ------------------------------
    st.subheader("🗺️ Peta Interaktif")
    m = folium.Map(location=[-1.5, 117], zoom_start=5, tiles="CartoDB positron")

    folium.GeoJson(
        gdf_pippib,
        name="PIPPIB",
        style_function=lambda x: {"color": "red", "weight": 1, "fillOpacity": 0.2},
        tooltip=folium.GeoJsonTooltip(fields=list(gdf_pippib.columns)[:3])
    ).add_to(m)

    folium.GeoJson(
        gdf_kawasan,
        name="Kawasan Hutan",
        style_function=lambda x: {"color": "green", "weight": 1, "fillOpacity": 0.3},
        tooltip=folium.GeoJsonTooltip(fields=list(gdf_kawasan.columns)[:3])
    ).add_to(m)

    if overlap_gdf is not None and not overlap_gdf.empty:
        folium.GeoJson(
            overlap_gdf,
            name="Overlap Area",
            style_function=lambda x: {"color": "blue", "weight": 2, "fillOpacity": 0.4},
            tooltip=folium.GeoJsonTooltip(fields=["luas_ha"])
        ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, height=650, width=1200)
