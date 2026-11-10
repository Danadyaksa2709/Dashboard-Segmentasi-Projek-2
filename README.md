# Dashboard Segmentasi Kecamatan — Potensi Tanaman Pangan Kabupaten Tuban

Dashboard interaktif Projek 2 Magang MBKM (Program Studi Sains Data) di BPS Kabupaten Tuban.
Kecamatan dikelompokkan dengan **K-Means (k = 3)** berdasarkan luas panen dan produktivitas padi, jagung,
dan palawija lain (rata-rata 2020–2024), lalu divalidasi dengan Hierarchical Clustering (Ward).

**Isi dashboard:** Ringkasan (KPI, tren produksi, kontribusi segmen, peringkat kecamatan) · Peta Segmen (peta poligon interaktif + peta QGIS citra satelit) ·
Profil Segmen (radar, heatmap, rekomendasi) · Eksplorasi Kecamatan · Metodologi & Data (silhouette, elbow, PCA, unduh data).

## Struktur folder
```
├── app.py                         # kode dashboard
├── requirements.txt               # library yang dibutuhkan
├── .streamlit/config.toml         # tema warna
├── assets/logo_bps_tuban.png, ikon.png
└── data/
    ├── Data_Projek_2_Pyhton.xlsx  # data bersih tanaman pangan per kecamatan
    ├── koordinat_kecamatan.csv    # titik pusat kecamatan (dari layer QGIS)
    └── batas_kecamatan_tuban.geojson   # batas kecamatan (dari peta QGIS, sudah disederhanakan)
```

## Menjalankan di komputer sendiri
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publikasi gratis (GitHub + Streamlit Community Cloud)
1. Buat repository **public** baru di GitHub, misalnya `dashboard-segmentasi-tuban`.
2. Unggah semua isi folder ini dengan struktur folder yang sama (**Add file → Upload files**, seret seluruh folder).
   Jika folder `.streamlit` tidak ikut terunggah, buat manual lewat **Add file → Create new file** dengan nama
   `.streamlit/config.toml` lalu salin isinya.
3. Buka **https://share.streamlit.io**, masuk dengan akun GitHub → **Create app** → pilih repository,
   branch `main`, main file path `app.py` → (opsional) di *Advanced settings* pilih Python 3.12 → **Deploy**.
4. Tunggu 2–5 menit. Link publik berbentuk `https://<nama-app>.streamlit.app` dan bisa langsung dibagikan.
   Setiap kali file di GitHub diperbarui, dashboard ikut diperbarui otomatis.

## Peta di tab "Peta Segmen"
- **Peta interaktif dashboard:** peta poligon dari `data/batas_kecamatan_tuban.geojson` (diambil dari ekspor qgis2web,
  geometri disederhanakan ±20 m agar ringan). Bisa diwarnai menurut segmen atau indikator angka.
- **Peta QGIS (citra satelit):** peta qgis2web yang di-hosting di GitHub Pages
  (https://danadyaksa2709.github.io/Peta-Interaktif-Segmentasi-Kecamatan-Berdasarkan-Potensi-Tanaman-Pangan-di-Kabupaten-Tuban/),
  ditampilkan lewat iframe. Jika alamatnya berubah, ganti variabel `URL_PETA_QGIS` di `app.py`.

### Memperbarui batas wilayah dari QGIS
Jika file GeoJSON dihapus, peta otomatis kembali ke lingkaran di titik pusat kecamatan. Untuk membuat ulang:
1. Di QGIS, klik kanan layer batas kecamatan → **Export → Save Features As**.
2. Format **GeoJSON**, CRS **EPSG:4326 - WGS 84**, simpan sebagai `data/batas_kecamatan_tuban.geojson`.
3. Pastikan layer punya kolom **`Kecamatan`** berisi nama kecamatan (mis. "Soko"). Kolom `WADMKC` juga dikenali.
4. Unggah file tersebut ke folder `data/` di GitHub. Dashboard otomatis beralih ke peta poligon.

## Sumber data
BPS Kabupaten Tuban, Tabel Dinamis subjek Pertanian, Kehutanan, Perikanan (data asal Dinas Pertanian dan
Ketahanan Pangan Kab. Tuban), 2012–2024. Dashboard ini adalah projek magang, bukan publikasi resmi BPS.
