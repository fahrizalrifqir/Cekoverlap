import streamlit as st
import geopandas as gpd
import tempfile
import os
import zipfile
from shapely.geometry import Polygon, MultiPolygon

st.set_page_config(page_title="KML to SHP Converter", page_icon="🌍")

st.title("🌍 KML to SHP Converter")
st.write("Upload file **.kml** untuk dikonversi menjadi shapefile (.shp.zip). Hanya fitur **Polygon** yang akan disimpan.")

uploaded_file = st.file_uploader("Pilih file KML", type=["kml"])

if uploaded_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, uploaded_file.name)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.read())

        st.info("📂 Membaca file KML...")
        try:
            # Baca file KML menggunakan driver 'KML'
            gdf = gpd.read_file(input_path, driver='KML')

            # Filter hanya Polygon dan MultiPolygon
            polygon_gdf = gdf[gdf.geometry.apply(lambda geom: isinstance(geom, (Polygon, MultiPolygon)))]

            if polygon_gdf.empty:
                st.warning("⚠️ Tidak ditemukan fitur Polygon di file KML ini.")
            else:
                st.success(f"✅ Ditemukan {len(polygon_gdf)} fitur Polygon.")
                st.map(polygon_gdf)

                # Simpan ke shapefile
                shp_dir = os.path.join(tmpdir, "output_shp")
                os.makedirs(shp_dir, exist_ok=True)
                shp_path = os.path.join(shp_dir, "data.shp")
                polygon_gdf.to_file(shp_path, driver="ESRI Shapefile")

                # Kompres ke ZIP
                zip_path = os.path.join(tmpdir, "shapefile.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(shp_dir):
                        for file in files:
                            zipf.write(os.path.join(root, file), file)

                # Tombol download
                with open(zip_path, "rb") as fp:
                    st.download_button(
                        label="⬇️ Download Shapefile (.zip)",
                        data=fp,
                        file_name="converted_polygon_shapefile.zip",
                        mime="application/zip"
                    )

        except Exception as e:
            st.error(f"❌ Terjadi kesalahan: {e}")
