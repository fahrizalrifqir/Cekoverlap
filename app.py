import streamlit as st
import geopandas as gpd
import tempfile
import os
import zipfile

st.set_page_config(page_title="KML to SHP Converter", page_icon="🌍")

st.title("🌍 KML to SHP Converter")
st.write("Upload file **.kml** untuk dikonversi menjadi shapefile (.shp.zip).")

uploaded_file = st.file_uploader("Pilih file KML", type=["kml"])

if uploaded_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, uploaded_file.name)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.read())

        st.info("📂 Membaca file KML...")
        try:
            # Baca KML menggunakan GeoPandas
            gdf = gpd.read_file(input_path, driver='KML')
            
            st.success(f"✅ File berhasil dibaca. Jumlah fitur: {len(gdf)}")
            st.map(gdf)
            
            # Simpan ke shapefile
            shp_dir = os.path.join(tmpdir, "output_shp")
            os.makedirs(shp_dir, exist_ok=True)
            shp_path = os.path.join(shp_dir, "data.shp")
            gdf.to_file(shp_path, driver="ESRI Shapefile")
            
            # Kompres ke zip
            zip_path = os.path.join(tmpdir, "shapefile.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(shp_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)
            
            with open(zip_path, "rb") as fp:
                st.download_button(
                    label="⬇️ Download Shapefile (.zip)",
                    data=fp,
                    file_name="converted_shapefile.zip",
                    mime="application/zip"
                )
                
        except Exception as e:
            st.error(f"❌ Terjadi kesalahan: {e}")
