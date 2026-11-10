"""
Dashboard Segmentasi Kecamatan Berdasarkan Potensi Tanaman Pangan — Kabupaten Tuban
Projek 2 Magang MBKM BPS Kabupaten Tuban (Program Studi Sains Data)

Jalankan lokal :  streamlit run app.py
Data           :  data/Data_Projek_2_Pyhton.xlsx  (data bersih luas panen & produksi per kecamatan)
Peta (opsional):  data/batas_kecamatan_tuban.geojson  (ekspor dari QGIS, berisi kolom "Kecamatan")
"""
import base64
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_samples, silhouette_score
from sklearn.preprocessing import StandardScaler

# ----------------------------------------------------------------------------------------------
# Konfigurasi dasar
# ----------------------------------------------------------------------------------------------
BASE = Path(__file__).parent
FILE_DATA = BASE / "data" / "Data_Projek_2_Pyhton.xlsx"
FILE_KOORD = BASE / "data" / "koordinat_kecamatan.csv"
FILE_GEOJSON = BASE / "data" / "batas_kecamatan_tuban.geojson"
FILE_LOGO = BASE / "assets" / "logo_bps_tuban.png"
FILE_IKON = BASE / "assets" / "ikon.png"

st.set_page_config(page_title="Dashboard Segmentasi Tanaman Pangan Tuban",
                   page_icon=str(FILE_IKON), layout="wide", initial_sidebar_state="expanded")

BIRU, HIJAU, ORANYE, NAVY, ABU = "#1C8BE6", "#5DB83A", "#F28C1B", "#0F2A4A", "#94A3B8"
EMAS = "#D99A00"  # warna komoditas jagung pada grafik tren
URL_PETA_QGIS = ("https://danadyaksa2709.github.io/Peta-Interaktif-Segmentasi-Kecamatan-Berdasarkan-"
                 "Potensi-Tanaman-Pangan-di-Kabupaten-Tuban/")
SEGMEN_K3 = ["Lumbung Padi", "Campuran Padi–Jagung", "Sentra Jagung & Palawija Lahan Kering"]
SEGMEN_K4 = ["Lumbung Padi", "Campuran–Jagung Produktif", "Campuran–Produktivitas Rendah",
             "Sentra Jagung & Palawija Lahan Kering"]
# Warna segmen disamakan dengan peta QGIS (qgis2web) agar dashboard dan peta konsisten
WARNA = {"Lumbung Padi": "#FF7C00", "Campuran Padi–Jagung": "#16B82C",
         "Sentra Jagung & Palawija Lahan Kering": "#C9C502",
         "Campuran–Jagung Produktif": "#0E7A1E", "Campuran–Produktivitas Rendah": "#7FD98B"}
FITUR_CLUSTER = ["Luas_Padi_ha", "Luas_Jagung_ha", "Luas_Palawija_Lain_ha",
                 "Produktivitas_Padi", "Produktivitas_Jagung"]
LABEL = {"Luas_Padi_ha": "Luas panen padi (ha/th)", "Produksi_Padi_ton": "Produksi padi (ton/th)",
         "Produktivitas_Padi": "Produktivitas padi (ton/ha)", "Luas_Jagung_ha": "Luas panen jagung (ha/th)",
         "Produksi_Jagung_ton": "Produksi jagung (ton/th)", "Produktivitas_Jagung": "Produktivitas jagung (ton/ha)",
         "Luas_Palawija_Lain_ha": "Luas palawija lain (ha/th)", "Pangsa_Jagung_persen": "Pangsa jagung (%)",
         "Pertumbuhan_Produksi_persen": "Pertumbuhan produksi (%)"}
PENDEK = {"Luas_Padi_ha": "Luas padi", "Luas_Jagung_ha": "Luas jagung", "Luas_Palawija_Lain_ha": "Luas palawija lain",
          "Produktivitas_Padi": "Produktivitas padi", "Produktivitas_Jagung": "Produktivitas jagung",
          "Pangsa_Jagung_persen": "Pangsa jagung", "Pertumbuhan_Produksi_persen": "Pertumbuhan produksi"}
REKOMENDASI = {
    "Lumbung Padi": ("Jaga kapasitas produksi padi",
                     ["Pemeliharaan irigasi & tanggul Bengawan Solo", "Mekanisasi tanam dan panen",
                      "Penguatan penggilingan & cadangan beras", "Perlindungan lahan sawah dari alih fungsi"]),
    "Campuran Padi–Jagung": ("Intensifikasi untuk menaikkan produktivitas",
                             ["Penyuluhan & sekolah lapang budidaya", "Pupuk berimbang dan benih unggul",
                              "Prioritas pada kecamatan produktivitas rendah", "Pendampingan kelompok tani"]),
    "Sentra Jagung & Palawija Lahan Kering": ("Tingkatkan nilai tambah lahan kering",
                                              ["Benih jagung hibrida", "Embung / sumur dangkal untuk lahan kering",
                                               "Pengering & gudang jagung (pascapanen)",
                                               "Kemitraan dengan industri pakan; hilirisasi kacang tanah & ubi kayu"]),
}
REKOMENDASI["Campuran–Jagung Produktif"] = ("Perkuat keunggulan jagung",
                                             ["Kemitraan pemasaran jagung", "Pascapanen & gudang",
                                              "Pertahankan produktivitas dengan benih unggul"])
REKOMENDASI["Campuran–Produktivitas Rendah"] = ("Prioritas intensifikasi",
                                                 ["Sekolah lapang & penyuluhan intensif", "Pupuk berimbang",
                                                  "Perbaikan irigasi tersier"])

# ----------------------------------------------------------------------------------------------
# Gaya tampilan (CSS)
# ----------------------------------------------------------------------------------------------
st.markdown(f"""
<style>
.block-container {{padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px;}}
[data-testid="stSidebar"] {{background: linear-gradient(180deg, #FFFFFF 0%, #EEF4FB 100%);}}
.hero {{display:flex; align-items:center; gap:22px; padding:18px 26px; border-radius:18px;
        background: linear-gradient(110deg, {NAVY} 0%, #12457A 55%, {BIRU} 100%); color:white;
        box-shadow: 0 8px 24px rgba(15,42,74,.18); margin-bottom: 18px;}}
.hero img {{height:74px; background:white; border-radius:14px; padding:6px 10px;}}
.hero h1 {{font-size:1.65rem; margin:0; color:white; line-height:1.25;}}
.hero p {{margin:4px 0 0 0; opacity:.88; font-size:.95rem;}}
.kpi {{background:white; border-radius:16px; padding:16px 18px; box-shadow:0 2px 10px rgba(15,42,74,.07);
       border-top:4px solid var(--c); height:100%;}}
.kpi .lbl {{font-size:.80rem; color:#64748B; text-transform:uppercase; letter-spacing:.04em;}}
.kpi .val {{font-size:1.65rem; font-weight:700; color:{NAVY}; margin-top:2px;}}
.kpi .sub {{font-size:.82rem; color:#64748B;}}
.card {{background:white; border-radius:16px; padding:16px 18px; box-shadow:0 2px 10px rgba(15,42,74,.07);
        border-left:6px solid var(--c); margin-bottom:12px;}}
.card h4 {{margin:0 0 6px 0; color:{NAVY};}}
.card .anggota {{font-size:.88rem; color:#334155; margin-bottom:6px;}}
.card ul {{margin:4px 0 0 18px; padding:0; font-size:.88rem;}}
.pill {{display:inline-block; padding:2px 10px; border-radius:999px; font-size:.75rem; font-weight:600;
        color:{NAVY}; background:var(--c); margin-bottom:6px;}}
.insight {{background:#EEF6FF; border-left:5px solid {BIRU}; border-radius:10px; padding:12px 16px;
           font-size:.93rem; color:#1F2A44; margin:6px 0 14px 0;}}
.footer {{text-align:center; color:#64748B; font-size:.8rem; margin-top:30px; padding-top:14px;
          border-top:1px solid #E2E8F0;}}
div[data-testid="stTabs"] button p {{font-size:0.98rem; font-weight:600;}}
</style>""", unsafe_allow_html=True)


def logo_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def fmt(x, d=0):
    """Format angka gaya Indonesia: 12.345,6"""
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def gaya(fig, h=420, legend=True):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=95 if legend else 60, b=10), paper_bgcolor="white",
                      plot_bgcolor="white", font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#1F2A44"),
                      title=dict(y=0.985, yanchor="top", x=0.01, xanchor="left", font=dict(size=16, color=NAVY)),
                      hoverlabel=dict(font_size=13),
                      showlegend=legend,
                      legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, title=None,
                                  traceorder="normal", font=dict(size=12)))
    fig.update_xaxes(showgrid=False, linecolor="#CBD5E1")
    fig.update_yaxes(gridcolor="#EEF2F7", zeroline=False)
    return fig


# ----------------------------------------------------------------------------------------------
# Data & model (di-cache agar cepat)
# ----------------------------------------------------------------------------------------------
@st.cache_data
def muat_data():
    d = pd.read_excel(FILE_DATA)
    for c in ["Kecamatan", "Kelompok", "Komoditas"]:
        d[c] = d[c].astype(str).str.strip()
    d["Produktivitas"] = np.where(d["Luas Panen (ha)"] > 0, d["Produksi (ton)"] / d["Luas Panen (ha)"], np.nan)
    ubah_luas = d["Luas Panen Asli (ha)"] != d["Luas Panen (ha)"]
    ubah_prod = d["Produksi Asli (ton)"] != d["Produksi (ton)"]
    d["Status Data"] = np.select([ubah_luas | (ubah_prod & (d["Produksi Asli (ton)"] == 0)), ubah_prod],
                                 ["Diimputasi", "Dikoreksi"], default="Asli")
    return d


@st.cache_data
def buat_fitur(d: pd.DataFrame) -> pd.DataFrame:
    L, P, W = "Luas Panen (ha)", "Produksi (ton)", [2020, 2021, 2022, 2024]

    def agg(mask, kol, th):
        return d[mask & d["Tahun"].isin(th)].groupby("Kecamatan")[kol].sum()

    padi, jagung = d["Kelompok"] == "Padi", d["Komoditas"] == "Jagung"
    lain = (d["Kelompok"] == "Palawija") & ~jagung
    f = pd.DataFrame({"Luas_Padi_ha": agg(padi, L, W) / 4, "Produksi_Padi_ton": agg(padi, P, W) / 4,
                      "Luas_Jagung_ha": agg(jagung, L, W) / 4, "Produksi_Jagung_ton": agg(jagung, P, W) / 4,
                      "Luas_Palawija_Lain_ha": agg(lain, L, W) / 4})
    f["Produktivitas_Padi"] = f["Produksi_Padi_ton"] / f["Luas_Padi_ha"]
    f["Produktivitas_Jagung"] = agg(jagung, P, [2020, 2021, 2022]) / agg(jagung, L, [2020, 2021, 2022])
    f["Pangsa_Jagung_persen"] = f["Luas_Jagung_ha"] / f[["Luas_Padi_ha", "Luas_Jagung_ha", "Luas_Palawija_Lain_ha"]].sum(axis=1) * 100
    awal = agg(padi | jagung, P, [2012, 2013, 2014]) / 3
    f["Pertumbuhan_Produksi_persen"] = ((f["Produksi_Padi_ton"] + f["Produksi_Jagung_ton"]) / awal - 1) * 100
    return f[list(LABEL)]


@st.cache_data
def segmentasi(f: pd.DataFrame):
    Z = StandardScaler().fit_transform(f[FITUR_CLUSTER])
    km3 = KMeans(n_clusters=3, n_init=50, random_state=42).fit(Z)
    km4 = KMeans(n_clusters=4, n_init=50, random_state=42).fit(Z)
    s = f.copy()
    s["k3"], s["k4"] = km3.labels_, km4.labels_
    prof = s.groupby("k3")[FITUR_CLUSTER].mean()
    nama = {prof["Luas_Padi_ha"].idxmax(): SEGMEN_K3[0], prof["Luas_Jagung_ha"].idxmax(): SEGMEN_K3[2]}
    for c in prof.index:
        nama.setdefault(c, SEGMEN_K3[1])
    s["Segmen"] = s["k3"].map(nama)
    camp = s[s["Segmen"] == SEGMEN_K3[1]]
    hi = camp.groupby("k4")["Produktivitas_Jagung"].mean().idxmax()
    s["Segmen_Rinci"] = np.where(s["Segmen"] != SEGMEN_K3[1], s["Segmen"],
                                 np.where(s["k4"] == hi, SEGMEN_K4[1], SEGMEN_K4[2]))
    s["Silhouette"] = silhouette_samples(Z, km3.labels_)
    pca = PCA(n_components=2, random_state=42).fit(Z)
    P = pca.transform(Z)
    s["PC1"], s["PC2"] = P[:, 0], P[:, 1]
    eval_k = []
    for k in range(2, 7):
        km = KMeans(n_clusters=k, n_init=50, random_state=42).fit(Z)
        hc = AgglomerativeClustering(n_clusters=k, linkage="ward").fit(Z)
        eval_k.append({"k": k, "Inertia": km.inertia_, "Silhouette K-Means": silhouette_score(Z, km.labels_),
                       "Silhouette Hierarchical": silhouette_score(Z, hc.labels_),
                       "ARI": adjusted_rand_score(km.labels_, hc.labels_)})
    info = {"sil": silhouette_score(Z, km3.labels_), "var": pca.explained_variance_ratio_,
            "ari": adjusted_rand_score(km3.labels_, AgglomerativeClustering(n_clusters=3, linkage="ward").fit(Z).labels_)}
    return s.drop(columns=["k3", "k4"]), pd.DataFrame(eval_k), info


@st.cache_data
def muat_geojson():
    if FILE_GEOJSON.exists():
        gj = json.loads(FILE_GEOJSON.read_text(encoding="utf-8"))
        kunci = next((k for k in gj["features"][0]["properties"] if k.lower() in ("kecamatan", "wadmkc", "nama_kec")), None)
        if kunci:
            for ft in gj["features"]:
                ft["properties"]["_kec"] = str(ft["properties"][kunci]).strip().title()
            return gj
    return None


data = muat_data()
fitur = buat_fitur(data)
seg, eval_k, info = segmentasi(fitur)
koord = pd.read_csv(FILE_KOORD)
seg = seg.join(koord.set_index("Kecamatan")[["Join_No", "Longitude", "Latitude"]])
seg["Kontribusi_Padi_persen"] = seg["Produksi_Padi_ton"] / seg["Produksi_Padi_ton"].sum() * 100
seg["Kontribusi_Jagung_persen"] = seg["Produksi_Jagung_ton"] / seg["Produksi_Jagung_ton"].sum() * 100
geojson = muat_geojson()

# ----------------------------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------------------------
with st.sidebar:
    st.image(str(FILE_LOGO), width="stretch")
    st.markdown("### Pengaturan tampilan")
    tingkat = st.radio("Tingkat segmentasi", ["3 segmen (utama)", "4 segmen (rinci)"],
                       help="Versi rinci memecah segmen Campuran menjadi Jagung Produktif dan Produktivitas Rendah.")
    KOL = "Segmen" if tingkat.startswith("3") else "Segmen_Rinci"
    URUT = SEGMEN_K3 if KOL == "Segmen" else SEGMEN_K4
    pilih = st.multiselect("Tampilkan segmen", URUT, default=URUT)
    if not pilih:
        st.warning("Pilih minimal satu segmen.")
        pilih = URUT
    st.markdown("---")
    st.caption("**Sumber data:** BPS Kabupaten Tuban, Tabel Dinamis subjek Pertanian, Kehutanan, Perikanan "
               "(data asal Dinas Pertanian dan Ketahanan Pangan Kab. Tuban), 2012–2024.")
    st.caption("**Metode:** K-Means (k = 3) pada 5 fitur terstandardisasi, divalidasi dengan Hierarchical Clustering (Ward).")

tampil = seg[seg[KOL].isin(pilih)]

# ----------------------------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------------------------
st.markdown(f"""
<div class="hero">
  <img src="data:image/png;base64,{logo_b64(FILE_LOGO)}">
  <div><h1>Segmentasi Kecamatan Berdasarkan Potensi Tanaman Pangan</h1>
  <p>Kabupaten Tuban · rata-rata 2020–2024 · 20 kecamatan · 8 komoditas tanaman pangan</p></div>
</div>""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Ringkasan", "🗺️ Peta Segmen", "🧩 Profil Segmen",
                                         "🔎 Eksplorasi Kecamatan", "🧪 Metodologi & Data"])

# ============================== TAB 1: RINGKASAN ==============================================
with tab1:
    c = st.columns(4)
    kpi = [("Produksi padi", f"{fmt(seg['Produksi_Padi_ton'].sum() / 1000, 1)} rb ton", "rata-rata per tahun 2020–2024", BIRU),
           ("Produksi jagung", f"{fmt(seg['Produksi_Jagung_ton'].sum() / 1000, 1)} rb ton", "rata-rata per tahun 2020–2024", EMAS),
           ("Kecamatan", f"{len(seg)}", f"terbagi dalam {len(URUT)} segmen", HIJAU),
           ("Kualitas segmen", f"{fmt(info['sil'], 3)}", f"silhouette · K-Means = Hierarchical (ARI {fmt(info['ari'], 2)})", NAVY)]
    for col, (l, v, s_, w) in zip(c, kpi):
        col.markdown(f'<div class="kpi" style="--c:{w}"><div class="lbl">{l}</div><div class="val">{v}</div>'
                     f'<div class="sub">{s_}</div></div>', unsafe_allow_html=True)
    st.write("")

    kiri, kanan = st.columns([1.15, 1])
    with kiri:
        tren = (data[(data["Kelompok"] == "Padi") | (data["Komoditas"] == "Jagung")]
                .assign(Komoditas=lambda x: np.where(x["Kelompok"] == "Padi", "Padi", "Jagung"))
                .groupby(["Tahun", "Komoditas"])["Produksi (ton)"].sum().unstack() / 1000)
        tren = tren.reindex(range(tren.index.min(), tren.index.max() + 1))
        fig = go.Figure()
        for kom, w in [("Padi", BIRU), ("Jagung", EMAS)]:
            fig.add_trace(go.Scatter(x=tren.index, y=tren[kom], name=kom, mode="lines+markers",
                                     line=dict(color=w, width=3), marker=dict(size=8),
                                     hovertemplate=f"<b>{kom}</b> %{{x}}<br>%{{y:,.1f}} ribu ton<extra></extra>"))
        fig.add_annotation(x=2023, y=tren.max().max() * 0.62, text="2023<br>tidak tersedia", showarrow=False,
                           font=dict(size=11, color="#94A3B8"))
        fig.update_layout(title="Produksi padi & jagung Kabupaten Tuban (ribu ton)", hovermode="x unified")
        fig.update_xaxes(dtick=2)
        st.plotly_chart(gaya(fig, 400), width="stretch")
    with kanan:
        k = tampil.groupby(KOL)[["Produksi_Padi_ton", "Produksi_Jagung_ton", "Luas_Palawija_Lain_ha"]].sum()
        jml = tampil[KOL].value_counts()
        tot = seg[["Produksi_Padi_ton", "Produksi_Jagung_ton", "Luas_Palawija_Lain_ha"]].sum()
        pct = (k / tot * 100).reindex([u for u in URUT if u in pilih])
        pct.insert(0, "Jumlah kecamatan", jml / len(seg) * 100)
        pct.columns = ["Jumlah kecamatan", "Produksi padi", "Produksi jagung", "Luas palawija lain"]
        fig = go.Figure()
        for sname in pct.index:
            fig.add_trace(go.Bar(y=pct.columns, x=pct.loc[sname], name=sname, orientation="h",
                                 marker_color=WARNA[sname], text=[f"{v:.0f}%" for v in pct.loc[sname]],
                                 textposition="inside", insidetextanchor="middle",
                                 hovertemplate=f"<b>{sname}</b><br>%{{y}}: %{{x:.1f}}%<extra></extra>"))
        fig.update_layout(barmode="stack", title="Porsi tiap segmen terhadap total kabupaten (%)")
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(range=[0, 100], ticksuffix="%")
        st.plotly_chart(gaya(fig, 400), width="stretch")

    lp = seg.loc[seg["Segmen"] == SEGMEN_K3[0]]
    sj = seg.loc[seg["Segmen"] == SEGMEN_K3[2]]
    st.markdown(f"""<div class="insight">💡 <b>Pesan utama:</b> segmen <b>Lumbung Padi</b> hanya {len(lp)} kecamatan,
    tetapi menyumbang <b>{lp['Kontribusi_Padi_persen'].sum():.0f}% produksi padi</b> kabupaten. Segmen <b>Sentra Jagung</b>
    ({len(sj)} kecamatan) menyumbang <b>{sj['Kontribusi_Jagung_persen'].sum():.0f}% produksi jagung</b>.
    Sejak 2019 produksi jagung Tuban konsisten melampaui padi.</div>""", unsafe_allow_html=True)

    st.markdown("#### Peringkat kecamatan")
    a, b = st.columns([1, 3])
    with a:
        ind = st.selectbox("Indikator", list(LABEL), index=1, format_func=lambda x: LABEL[x], key="rank_ind")
        n_top = st.slider("Jumlah kecamatan", 5, 20, 20, key="rank_n")
    with b:
        r = tampil.sort_values(ind, ascending=False).head(n_top).reset_index()
        fig = px.bar(r, x=ind, y="Kecamatan", color=KOL, orientation="h", color_discrete_map=WARNA,
                     category_orders={KOL: URUT}, text=r[ind].map(lambda v: fmt(v, 2 if v < 100 else 0)),
                     labels={ind: LABEL[ind], KOL: "Segmen"})
        fig.update_yaxes(categoryorder="array", categoryarray=r["Kecamatan"].tolist()[::-1], title=None)
        fig.update_traces(textposition="outside", cliponaxis=False,
                          hovertemplate="<b>%{y}</b><br>" + LABEL[ind] + ": %{x:,.2f}<extra></extra>")
        st.plotly_chart(gaya(fig, max(320, 26 * len(r) + 90)), width="stretch")

# ============================== TAB 2: PETA ===================================================
with tab2:
    sumber = st.radio("Pilih peta", ["🧭 Peta interaktif dashboard", "🛰️ Peta QGIS (citra satelit)"], horizontal=True,
                      label_visibility="collapsed")
    if sumber.startswith("🛰️"):
        st.markdown(f"""<div class="insight">Peta tematik hasil olahan <b>QGIS</b> (diekspor dengan qgis2web) dengan latar
        citra satelit Google Hybrid. Klik poligon kecamatan untuk melihat atributnya. Peta memuat data segmen yang sama
        dengan dashboard ini.</div>""", unsafe_allow_html=True)
        components.iframe(URL_PETA_QGIS, height=680, scrolling=False)
        st.link_button("↗️ Buka peta QGIS di tab baru", URL_PETA_QGIS)
    else:
        a, b = st.columns([1, 3])
        with a:
            st.markdown("#### Pengaturan peta")
            OPSI_WARNA = ["Segmen", "Kontribusi_Padi_persen", "Kontribusi_Jagung_persen", "Produktivitas_Padi",
                          "Produktivitas_Jagung", "Pangsa_Jagung_persen", "Pertumbuhan_Produksi_persen"]
            LBL_WARNA = {**LABEL, "Segmen": "Segmen (kategori)", "Kontribusi_Padi_persen": "Kontribusi produksi padi (%)",
                         "Kontribusi_Jagung_persen": "Kontribusi produksi jagung (%)"}
            if geojson is not None:
                warnai = st.selectbox("Warnai peta menurut", OPSI_WARNA, format_func=lambda x: LBL_WARNA[x])
            else:
                warnai = "Segmen"
                ukuran = st.selectbox("Ukuran lingkaran menurut", ["Produksi_Padi_ton", "Produksi_Jagung_ton",
                                                                     "Luas_Padi_ha", "Luas_Jagung_ha", "Luas_Palawija_Lain_ha"],
                                      format_func=lambda x: LABEL[x])
            label_on = st.toggle("Tampilkan nama kecamatan", value=True)
            gaya_peta = st.selectbox("Latar peta", ["Terang", "OpenStreetMap", "Polos"])
            MAPSTYLE = {"Terang": "carto-positron", "OpenStreetMap": "open-street-map", "Polos": "white-bg"}[gaya_peta]
            st.markdown("")
            for sname in URUT:
                if sname in pilih:
                    n_ = (seg[KOL] == sname).sum()
                    st.markdown(f'<span class="pill" style="--c:{WARNA[sname]}">{n_} kec.</span> {sname}',
                                unsafe_allow_html=True)
            if geojson is None:
                st.caption("Peta menampilkan titik pusat kecamatan. Untuk peta batas wilayah (poligon), simpan "
                           "`data/batas_kecamatan_tuban.geojson`.")
            else:
                st.caption("Arahkan kursor ke kecamatan untuk melihat detail; gulir untuk zoom.")
        with b:
            hover = {"Join_No": False, "Longitude": False, "Latitude": False, "Produksi_Padi_ton": ":,.0f",
                     "Produksi_Jagung_ton": ":,.0f", "Produktivitas_Padi": ":.2f", "Produktivitas_Jagung": ":.2f",
                     "Pangsa_Jagung_persen": ":.1f", KOL: True}
            dfm = tampil.reset_index()
            lbl = {**LABEL, KOL: "Segmen", "Kontribusi_Padi_persen": "Kontribusi padi (%)",
                   "Kontribusi_Jagung_persen": "Kontribusi jagung (%)"}
            if geojson is not None:
                umum = dict(geojson=geojson, locations="Kecamatan", featureidkey="properties._kec", hover_name="Kecamatan",
                            hover_data=hover, opacity=0.8, center={"lat": -6.96, "lon": 111.90}, zoom=9.45,
                            map_style=MAPSTYLE, labels=lbl)
                if warnai == "Segmen":
                    fig = px.choropleth_map(dfm, color=KOL, color_discrete_map=WARNA, category_orders={KOL: URUT}, **umum)
                else:
                    skala = "Oranges" if "Padi" in warnai else "YlGn" if "Jagung" in warnai else "Blues"
                    fig = px.choropleth_map(dfm, color=warnai, color_continuous_scale=skala, **umum)
                    fig.update_layout(coloraxis_colorbar=dict(title=dict(text=LBL_WARNA[warnai], side="right"),
                                                              thickness=14, len=0.8))
                fig.update_traces(marker_line_width=1.2, marker_line_color="white", selector=dict(type="choroplethmap"))
                if label_on:
                    fig.add_trace(go.Scattermap(lat=dfm["Latitude"], lon=dfm["Longitude"], mode="text",
                                                text=dfm["Kecamatan"], textfont=dict(size=12, color=NAVY),
                                                hoverinfo="skip", showlegend=False))
            else:
                fig = px.scatter_map(dfm, lat="Latitude", lon="Longitude", color=KOL, size=ukuran, size_max=42,
                                     color_discrete_map=WARNA, category_orders={KOL: URUT}, hover_name="Kecamatan",
                                     hover_data=hover, zoom=9.2, center={"lat": -6.95, "lon": 111.90},
                                     map_style=MAPSTYLE, labels=lbl, text="Kecamatan" if label_on else None)
                fig.update_traces(marker=dict(opacity=0.85), textposition="top center",
                                  textfont=dict(size=11, color=NAVY))
            fig.update_layout(height=660, margin=dict(l=0, r=0, t=10, b=0),
                              legend=dict(orientation="h", y=1.02, x=0, title=None, bgcolor="rgba(255,255,255,.85)"))
            st.plotly_chart(fig, width="stretch")

    st.markdown("#### Tabel segmen per kecamatan")
    tabel = tampil.reset_index()[["Join_No", "Kecamatan", KOL, "Luas_Padi_ha", "Produksi_Padi_ton", "Produktivitas_Padi",
                                  "Luas_Jagung_ha", "Produksi_Jagung_ton", "Produktivitas_Jagung", "Pangsa_Jagung_persen",
                                  "Kontribusi_Padi_persen", "Kontribusi_Jagung_persen", "Silhouette"]].sort_values("Join_No")
    st.dataframe(tabel, hide_index=True, width="stretch", height=36 * len(tabel) + 40, column_config={
        "Join_No": st.column_config.NumberColumn("No", width="small"),
        KOL: st.column_config.TextColumn("Segmen"),
        "Luas_Padi_ha": st.column_config.NumberColumn("Luas padi (ha)", format="%.0f"),
        "Produksi_Padi_ton": st.column_config.NumberColumn("Produksi padi (ton)", format="%.0f"),
        "Produktivitas_Padi": st.column_config.NumberColumn("Prod.vitas padi", format="%.2f"),
        "Luas_Jagung_ha": st.column_config.NumberColumn("Luas jagung (ha)", format="%.0f"),
        "Produksi_Jagung_ton": st.column_config.NumberColumn("Produksi jagung (ton)", format="%.0f"),
        "Produktivitas_Jagung": st.column_config.NumberColumn("Prod.vitas jagung", format="%.2f"),
        "Pangsa_Jagung_persen": st.column_config.ProgressColumn("Pangsa jagung", format="%.0f%%", min_value=0, max_value=100),
        "Kontribusi_Padi_persen": st.column_config.NumberColumn("Kontribusi padi", format="%.1f%%"),
        "Kontribusi_Jagung_persen": st.column_config.NumberColumn("Kontribusi jagung", format="%.1f%%"),
        "Silhouette": st.column_config.NumberColumn("Silhouette", format="%.2f")})

# ============================== TAB 3: PROFIL SEGMEN ==========================================
with tab3:
    urut_p = [u for u in URUT if u in pilih]
    cols = st.columns(len(urut_p))
    for col, sname in zip(cols, urut_p):
        anggota = seg.index[seg[KOL] == sname].tolist()
        judul, butir = REKOMENDASI[sname]
        p = seg.loc[anggota]
        col.markdown(f"""<div class="card" style="--c:{WARNA[sname]}">
            <span class="pill" style="--c:{WARNA[sname]}">{len(anggota)} kecamatan</span>
            <h4>{sname}</h4><div class="anggota">{", ".join(anggota)}</div>
            <div style="font-size:.85rem;color:#475569">Padi {fmt(p['Produktivitas_Padi'].mean(), 2)} t/ha ·
            Jagung {fmt(p['Produktivitas_Jagung'].mean(), 2)} t/ha · Pangsa jagung {p['Pangsa_Jagung_persen'].mean():.0f}%</div>
            <div style="margin-top:8px;font-weight:600;color:{NAVY}">🎯 {judul}</div>
            <ul>{"".join(f"<li>{x}</li>" for x in butir)}</ul></div>""", unsafe_allow_html=True)

    a, b = st.columns([1, 1.35])
    with a:
        rad_f = FITUR_CLUSTER + ["Pangsa_Jagung_persen", "Pertumbuhan_Produksi_persen"]
        mm = (seg[rad_f] - seg[rad_f].min()) / (seg[rad_f].max() - seg[rad_f].min())
        prof = mm.join(seg[KOL]).groupby(KOL).mean()
        fig = go.Figure()
        for sname in urut_p:
            v = prof.loc[sname].tolist()
            fig.add_trace(go.Scatterpolar(r=v + v[:1], theta=[PENDEK[x] for x in rad_f] + [PENDEK[rad_f[0]]],
                                          name=sname, fill="toself", line=dict(color=WARNA[sname], width=2),
                                          opacity=0.55, hovertemplate="%{theta}: %{r:.2f}<extra>" + sname + "</extra>"))
        fig.update_layout(title="Radar profil segmen (skala 0–1)",
                          polar=dict(radialaxis=dict(range=[0, 1], showticklabels=False, gridcolor="#E2E8F0"),
                                     angularaxis=dict(tickfont=dict(size=12), gridcolor="#E2E8F0"), domain=dict(x=[0.24, 0.76], y=[0.1, 0.9])))
        fig = gaya(fig, 500)
        fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.04, x=0.5, xanchor="center"),
                          margin=dict(t=60, b=40, l=40, r=40))
        st.plotly_chart(fig, width="stretch")
    with b:
        z = (seg[rad_f] - seg[rad_f].mean()) / seg[rad_f].std(ddof=0)
        zp = z.join(seg[KOL]).groupby(KOL).mean().loc[urut_p]
        SINGKAT = {"Lumbung Padi": "Lumbung<br>Padi", "Campuran Padi–Jagung": "Campuran",
                   "Sentra Jagung & Palawija Lahan Kering": "Sentra<br>Jagung", "Campuran–Jagung Produktif": "Campuran<br>Jagung Prod.",
                   "Campuran–Produktivitas Rendah": "Campuran<br>Prod. Rendah"}
        fig = px.imshow(zp.values, x=["Luas<br>padi", "Luas<br>jagung", "Luas<br>palawija", "Prod.<br>padi", "Prod.<br>jagung",
                           "Pangsa<br>jagung", "Pertum-<br>buhan"],
                        y=[SINGKAT[u] for u in urut_p], color_continuous_scale="RdBu_r",
                        zmin=-2, zmax=2, text_auto=".2f", aspect="auto")
        fig.update_traces(textfont=dict(size=13), xgap=3, ygap=3,
                          hovertemplate="%{y}<br>%{x}: z = %{z:.2f}<extra></extra>")
        fig.update_layout(title="Heatmap z-score (positif = di atas rata-rata kab.; Prod. = produktivitas)",
                          coloraxis_colorbar=dict(title="z"))
        fig.update_xaxes(tickangle=0, side="bottom")
        st.plotly_chart(gaya(fig, 500, legend=False), width="stretch")

    st.markdown("#### Bandingkan sebaran indikator antarsegmen")
    ind2 = st.selectbox("Indikator", list(LABEL), index=2, format_func=lambda x: LABEL[x], key="box_ind")
    dfb = tampil.reset_index()
    fig = px.box(dfb, x=KOL, y=ind2, color=KOL, points="all", color_discrete_map=WARNA,
                 category_orders={KOL: urut_p}, hover_name="Kecamatan", labels={ind2: LABEL[ind2], KOL: ""})
    fig.update_traces(marker=dict(size=10, line=dict(width=1, color="white")), boxmean=True,
                      pointpos=0, jitter=0.35, fillcolor="rgba(255,255,255,0)")
    st.plotly_chart(gaya(fig, 420, legend=False), width="stretch")

# ============================== TAB 4: EKSPLORASI KECAMATAN ===================================
with tab4:
    a, b = st.columns([1, 2.4])
    with a:
        kec = st.selectbox("Pilih kecamatan", sorted(seg.index), index=sorted(seg.index).index("Soko"))
        r = seg.loc[kec]
        st.markdown(f'<span class="pill" style="--c:{WARNA[r[KOL]]}">{r[KOL]}</span>', unsafe_allow_html=True)
        st.markdown(f"**Silhouette:** {r['Silhouette']:.2f} "
                    + ("· _kecamatan perbatasan antarsegmen_" if r["Silhouette"] < 0.15 else ""))
        for f_, d_ in [("Produksi_Padi_ton", 0), ("Produksi_Jagung_ton", 0), ("Produktivitas_Padi", 2),
                       ("Produktivitas_Jagung", 2), ("Pertumbuhan_Produksi_persen", 1)]:
            rata = seg[f_].mean()
            st.metric(LABEL[f_], fmt(r[f_], d_), f"{(r[f_] / rata - 1) * 100:+.0f}% vs rata-rata kab.")
    with b:
        c1, c2 = st.columns(2)
        ukur = c1.radio("Ukuran", ["Produksi (ton)", "Luas Panen (ha)", "Produktivitas"], horizontal=True)
        kom_all = data["Komoditas"].unique().tolist()
        koms = c2.multiselect("Komoditas", kom_all, default=["Padi Sawah", "Jagung"])
        dk = data[(data["Kecamatan"] == kec) & (data["Komoditas"].isin(koms))]
        pv = dk.pivot_table(index="Tahun", columns="Komoditas", values=ukur, aggfunc="sum")
        pv = pv.reindex(range(2012, 2025))
        pal = px.colors.qualitative.Set2
        fig = go.Figure()
        for i, kom in enumerate(pv.columns):
            w = BIRU if kom == "Padi Sawah" else EMAS if kom == "Jagung" else pal[i % len(pal)]
            fig.add_trace(go.Scatter(x=pv.index, y=pv[kom], name=kom, mode="lines+markers",
                                     line=dict(width=3, color=w), marker=dict(size=7)))
        fig.update_layout(title=f"{ukur} per komoditas — Kecamatan {kec} (2023 tidak tersedia)", hovermode="x unified")
        fig.update_xaxes(dtick=2)
        st.plotly_chart(gaya(fig, 380), width="stretch")

        c3, c4 = st.columns(2)
        with c3:
            kmp = (data[(data["Kecamatan"] == kec) & data["Tahun"].isin([2020, 2021, 2022, 2024])]
                   .groupby("Komoditas")["Luas Panen (ha)"].sum() / 4)
            kmp = kmp[kmp > 0].sort_values(ascending=False)
            fig = px.pie(values=kmp.values, names=kmp.index, hole=0.55,
                         color=kmp.index, color_discrete_map={"Padi Sawah": BIRU, "Jagung": EMAS, "Padi Ladang": "#7CC0F2"},
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_traces(textinfo="percent", textposition="inside", sort=False,
                              hovertemplate="%{label}: %{value:,.0f} ha (%{percent})<extra></extra>")
            fig = gaya(fig, 380)
            fig.update_layout(title="Komposisi luas panen (rata-rata 2020–2024)", uniformtext_minsize=11,
                              uniformtext_mode="hide", margin=dict(t=60, b=10),
                              legend=dict(orientation="v", yanchor="middle", y=0.5, x=1.0, xanchor="left"))
            st.plotly_chart(fig, width="stretch")
        with c4:
            bandingan = pd.DataFrame({
                "Kecamatan ini": seg.loc[kec, FITUR_CLUSTER],
                "Rata-rata segmen": seg[seg[KOL] == r[KOL]][FITUR_CLUSTER].mean(),
                "Rata-rata kabupaten": seg[FITUR_CLUSTER].mean()})
            idx = bandingan.div(bandingan["Rata-rata kabupaten"], axis=0) * 100
            idx.index = [LABEL[x].split(" (")[0] for x in idx.index]
            fig = go.Figure()
            for nm, w in [("Kecamatan ini", WARNA[r[KOL]]), ("Rata-rata segmen", ABU)]:
                fig.add_trace(go.Bar(y=idx.index, x=idx[nm], name=nm, orientation="h", marker_color=w,
                                     hovertemplate="%{y}: %{x:.0f}<extra>" + nm + "</extra>"))
            fig.add_vline(x=100, line_dash="dash", line_color=NAVY)
            fig.update_layout(title="Indeks vs rata-rata kabupaten (= 100)", barmode="group")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(gaya(fig, 380), width="stretch")

# ============================== TAB 5: METODOLOGI =============================================
with tab5:
    st.markdown("""
**Alur analisis:** data bersih (1.920 baris) → rekayasa 9 fitur per kecamatan (rata-rata 2020, 2021, 2022, 2024) →
seleksi 5 fitur tidak redundan → standardisasi z-score → penentuan k (Elbow, Silhouette, ARI, dendrogram) →
K-Means (k = 3, `n_init` = 50, `random_state` = 42) → validasi Hierarchical (Ward) → profiling & penamaan segmen.

**Fitur clustering:** luas panen padi, luas panen jagung, luas palawija lain, produktivitas padi, produktivitas jagung
(2020–2022, karena produktivitas palawija 2024 seragam di semua kecamatan).
""")
    a, b = st.columns(2)
    with a:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=eval_k["k"], y=eval_k["Silhouette K-Means"], name="K-Means", mode="lines+markers",
                                 line=dict(color=BIRU, width=3), marker=dict(size=9)))
        fig.add_trace(go.Scatter(x=eval_k["k"], y=eval_k["Silhouette Hierarchical"], name="Hierarchical",
                                 mode="lines+markers", line=dict(color=ORANYE, width=3, dash="dash"), marker=dict(size=9)))
        fig.add_vrect(x0=2.7, x1=3.3, fillcolor=HIJAU, opacity=0.15, line_width=0, annotation_text="k terpilih")
        fig.update_layout(title="Silhouette score menurut jumlah segmen (k)", xaxis_title="k", yaxis_title="Silhouette")
        st.plotly_chart(gaya(fig, 380), width="stretch")
    with b:
        fig = go.Figure(go.Scatter(x=eval_k["k"], y=eval_k["Inertia"], mode="lines+markers",
                                   line=dict(color=NAVY, width=3), marker=dict(size=9),
                                   customdata=eval_k["ARI"],
                                   hovertemplate="k = %{x}<br>Inertia = %{y:.2f}<br>ARI = %{customdata:.2f}<extra></extra>"))
        fig.update_layout(title="Metode Elbow (inertia K-Means)", xaxis_title="k", yaxis_title="Inertia")
        st.plotly_chart(gaya(fig, 380, legend=False), width="stretch")

    dfp = seg.reset_index()
    fig = px.scatter(dfp, x="PC1", y="PC2", color=KOL, text="Kecamatan", color_discrete_map=WARNA,
                     category_orders={KOL: URUT}, hover_data={"Silhouette": ":.2f", "PC1": ":.2f", "PC2": ":.2f"},
                     labels={KOL: "Segmen", "PC1": f"PC1 ({info['var'][0] * 100:.0f}%)",
                             "PC2": f"PC2 ({info['var'][1] * 100:.0f}%)"})
    fig.update_traces(marker=dict(size=16, line=dict(width=1.5, color="white")), textposition="top center",
                      textfont=dict(size=11))
    fig.update_layout(title=f"Peta segmen dengan PCA (menjelaskan {info['var'].sum() * 100:.0f}% variasi)")
    st.plotly_chart(gaya(fig, 520), width="stretch")

    st.markdown("#### Data yang dikoreksi saat pembersihan")
    kor = data[data["Status Data"] != "Asli"][["Kecamatan", "Tahun", "Komoditas", "Luas Panen Asli (ha)",
                                               "Produksi Asli (ton)", "Luas Panen (ha)", "Produksi (ton)", "Status Data"]]
    st.dataframe(kor, hide_index=True, width="stretch")
    st.caption("Koreksi memakai rekonsiliasi terhadap total kabupaten dan deteksi outlier produktivitas "
               "(modified z-score); imputasi memakai median produktivitas kecamatan.")

    st.markdown("#### Unduh data")
    d1, d2 = st.columns(2)
    unduh = seg.reset_index().drop(columns=["PC1", "PC2"]).sort_values("Join_No")
    d1.download_button("⬇️ Hasil segmentasi per kecamatan (CSV)", unduh.to_csv(index=False).encode("utf-8-sig"),
                       "segmentasi_kecamatan_tuban.csv", "text/csv", width="stretch")
    d2.download_button("⬇️ Data bersih tanaman pangan (CSV)", data.to_csv(index=False).encode("utf-8-sig"),
                       "data_bersih_tanaman_pangan_tuban.csv", "text/csv", width="stretch")

st.markdown("""<div class="footer">Dashboard projek magang MBKM Program Studi Sains Data di BPS Kabupaten Tuban ·
Data diolah dari Tabel Dinamis BPS Kabupaten Tuban · Peta tematik dibuat dengan QGIS ·
Bukan publikasi resmi BPS</div>""", unsafe_allow_html=True)
