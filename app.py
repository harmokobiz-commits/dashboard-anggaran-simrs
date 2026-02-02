import streamlit as st
import pandas as pd
import re
import altair as alt
from io import BytesIO
from datetime import date

st.set_page_config(page_title="Dashboard Anggaran SIMRS", layout="wide")
st.title("📊 Dashboard Anggaran SIMRS")

# =============================
# LOGIN USER
# =============================
USERS = {
    "admin": "admin123",
    "anggaran": "simrs2026"
}

if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.subheader("🔐 Login Dashboard")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username] == password:
            st.session_state.login = True
            st.rerun()
        else:
            st.error("❌ Username atau password salah")

    st.stop()

st.sidebar.success("Login sebagai pengguna")
if st.sidebar.button("🚪 Logout"):
    st.session_state.login = False
    st.rerun()

if st.sidebar.button("🔄 Reset ke Data Google Drive"):
    st.session_state.ma_raw = None
    st.session_state.simrs_raw = None
    st.session_state.data_source = "drive"
    st.rerun()    

with st.sidebar.expander("📥 Upload Data Manual (Opsional)", expanded=False):

    ma_file = st.file_uploader(
        "📘 Upload MA SMART",
        type=["xlsx"],
        key="upload_ma"
    )

    simrs_file = st.file_uploader(
        "📙 Upload SIMRS",
        type=["xlsx"],
        key="upload_simrs"
    )

    if ma_file is not None and simrs_file is not None:
        st.session_state.ma_raw = pd.read_excel(ma_file)
        st.session_state.simrs_raw = pd.read_excel(simrs_file)
        st.session_state.data_source = "upload"
        st.success("✅ Data manual berhasil digunakan")    

with st.sidebar.expander("ℹ️ About Aplikasi"):
    st.markdown("""
    **Dashboard Anggaran SIMRS**

    **Dikembangkan oleh:**  
    **Adi Harmoko**

    **Fungsi Utama:**
    - Monitoring realisasi anggaran SIMRS
    - Rekap per pengendali
    - Laporan transaksi SIMRS
    - Export Excel & print laporan

    **Teknologi:**
    - Python
    - Streamlit
    - Pandas
    - Altair

    © 2026
    """)

# =============================
# SESSION STATE DATA
# =============================
if "ma_raw" not in st.session_state:
    st.session_state.ma_raw = None

if "simrs_raw" not in st.session_state:
    st.session_state.simrs_raw = None

if "data_source" not in st.session_state:
    st.session_state.data_source = "drive"  # drive | upload

# =============================
# REFERENSI PENGENDALI
# =============================
PENGENDALI_MAP = {
    "1": "TIM KERJA PELAYANAN PENUNJANG",
    "2": "INST. PEMELIHARAAN SARANA DAN PERALATAN RS (IPSRS)",
    "3": "INSTALASI KESEHATAN LINGKUNGAN & K3 RS",
    "4": "TIM KERJA TATA USAHA & RUMAH TANGGA",
    "5": "INSTALASI SIM RS",
    "6": "TIM KERJA ORGANISASI & SDM",
    "7": "TIM KERJA PENDIDIKAN & PELATIHAN",
    "8": "INSTALASI PEMASARAN & PENGEMBANGAN BISNIS",
}

# =============================
# DEFAULT DATA GOOGLE DRIVE
# =============================
MA_DRIVE_URL = "https://docs.google.com/spreadsheets/d/15StwZUyvQ7jhkVE97sL6tSO5z3UPXk0-/export?format=xlsx"
SIMRS_DRIVE_URL = "https://docs.google.com/spreadsheets/d/1dS9ukqE-epEapvaAySZEuyyhYkZsBsxF/export?format=xlsx"

# =============================
# UTIL
# =============================
def export_excel(df_dict):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet, index=False)

            ws = writer.sheets[sheet]
            ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
            ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
            ws.page_setup.fitToHeight = 1
            ws.page_setup.fitToWidth = 1

    buffer.seek(0)
    return buffer

def normalisasi_angka(series):
    return (
        series.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace("-", "0", regex=False)
        .str.strip()
        .replace("", "0")
        .astype(float)
    )

def format_rp(x):
    return f"{x:,.0f}".replace(",", ".")

def warna_persen(val):
    try:
        val = float(str(val).replace("%", ""))
    except:
        return ""
    if val >= 100:
        return "background-color: #f8d7da; color: #721c24;"  # merah
    elif val >= 70:
        return "background-color: #fff3cd; color: #856404;"  # kuning
    else:
        return "background-color: #d4edda; color: #155724;"  # hijau

def parse_kode_ma(kode):
    if pd.isna(kode):
        return None, None
    m = re.search(r"(\d{6})\.(\d+)\.\d+", str(kode))
    if not m:
        return None, None
    return m.group(1), m.group(2)

def ekstrak_kode_simrs(text):
    if pd.isna(text):
        return None
    m = re.search(r"(\d{6}\.\d+\.\d+)", str(text))
    return m.group(1) if m else None

# =============================
# EXPORT EXCEL (TAMBAHAN)
# =============================
def export_excel_realisasi(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Realisasi_Anggaran", index=False)
    buffer.seek(0)
    return buffer

def export_excel_simrs(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Laporan_SIMRS", index=False)
    buffer.seek(0)
    return buffer

# =============================
# LOAD DATA DEFAULT (GOOGLE DRIVE)
# =============================
if st.session_state.data_source == "drive" and st.session_state.ma_raw is None:
    try:
        st.session_state.ma_raw = pd.read_excel(MA_DRIVE_URL)
        st.session_state.simrs_raw = pd.read_excel(SIMRS_DRIVE_URL)
        st.success("📂 Data default dimuat dari Google Drive")
    except Exception as e:
        st.error("❌ Gagal memuat data dari Google Drive")
        st.stop()

# =============================
# BACA MA SMART
# =============================
ma_raw = st.session_state.ma_raw

ma = pd.DataFrame({
    "kode_dana": ma_raw.iloc[:, 2],
    "kode_ma": ma_raw.iloc[:, 3],
    "uraian": ma_raw.iloc[:, 5],
    "pagu": normalisasi_angka(ma_raw.iloc[:, 7]),
})

ma[["kode_anggaran", "kode_pengendali"]] = ma["kode_ma"].apply(
    lambda x: pd.Series(parse_kode_ma(x))
)

ma["pengendali"] = ma["kode_pengendali"].map(PENGENDALI_MAP)
ma["key"] = ma["kode_ma"].astype(str).str.strip()
ma = ma.dropna(subset=["kode_anggaran", "kode_pengendali"])

# =============================
# BACA SIMRS
# =============================
simrs_raw = st.session_state.simrs_raw

simrs = pd.DataFrame({
    "kepada": simrs_raw.iloc[:, 0],
    "tanggal": pd.to_datetime(simrs_raw.iloc[:, 1], errors="coerce"),
    "no_transaksi": simrs_raw.iloc[:, 2],
    "nama_anggaran": simrs_raw.iloc[:, 3],
    "kode_ma": simrs_raw.iloc[:, 5].apply(ekstrak_kode_simrs),
    "nilai": normalisasi_angka(simrs_raw.iloc[:, 8]),
})

simrs = simrs.dropna(subset=["kode_ma"])
simrs["key"] = simrs["kode_ma"].astype(str).str.strip()
simrs[["kode_anggaran", "kode_pengendali"]] = simrs["kode_ma"].apply(
    lambda x: pd.Series(parse_kode_ma(x))
)
simrs["pengendali"] = simrs["kode_pengendali"].map(PENGENDALI_MAP)

simrs["bulan"] = simrs["tanggal"].dt.to_period("M").astype(str)

# =============================
# INFO UPDATE DATA (DARI ISI FILE)
# =============================
last_update_simrs = simrs["tanggal"].max()

if pd.notna(last_update_simrs):
    info_update = last_update_simrs.strftime("%d %B %Y")
else:
    info_update = "Tanggal tidak tersedia"

# =============================
# FILTER BULAN (DEFAULT SEMUA)
# =============================
daftar_bulan = sorted(simrs["bulan"].dropna().unique())
f_bulan = daftar_bulan  # default semua bulan

# =============================
# HITUNG REALISASI (DENGAN FILTER BULAN)
# =============================
simrs_f = simrs.copy()

if f_bulan:
    simrs_f = simrs_f[simrs_f["bulan"].isin(f_bulan)]

realisasi = (
    simrs_f
    .groupby("key", as_index=False)
    .agg(
        capaian=("nilai", "sum"),
        jumlah_transaksi=("nilai", lambda x: (x > 0).sum())
    )
)

lap = ma.merge(realisasi, on="key", how="left")
lap["capaian"] = lap["capaian"].fillna(0)
lap["jumlah_transaksi"] = lap["jumlah_transaksi"].fillna(0).astype(int)
lap["sisa"] = lap["pagu"] - lap["capaian"]
lap["persen"] = (lap["capaian"] / lap["pagu"]).fillna(0) * 100

# =============================
# TAB
# =============================
tab1, tab2 = st.tabs(["📊 Realisasi Anggaran", "📄 Laporan SIMRS"])

# ======================================================
# TAB 1 – REALISASI ANGGARAN
# ======================================================
with tab1:
    st.subheader("🔎 Filter Realisasi Anggaran")

    daftar_bulan = sorted(simrs["bulan"].dropna().unique())

    f_bulan = st.multiselect(
        "Pilih Bulan Realisasi",
        daftar_bulan,
        default=daftar_bulan
    )

    daftar_pengendali = sorted(lap["pengendali"].dropna().unique())

    f_pengendali_realisasi = st.multiselect(
    "Pilih Pengendali",
    daftar_pengendali,
    default=daftar_pengendali
    )

    sumber = "Google Drive" if st.session_state.data_source == "drive" else "Upload Manual"

    st.caption(
    f"📅 Data ({sumber}) terakhir diperbarui: **{info_update}**"
    )

    lap_f = lap.copy()

    # filter pengendali
    if f_pengendali_realisasi:
        lap_f = lap_f[lap_f["pengendali"].isin(f_pengendali_realisasi)]

    tampil = lap_f.copy()
    tampil["jumlah_transaksi"] = tampil["jumlah_transaksi"]
    tampil["pagu"] = tampil["pagu"].apply(format_rp)
    tampil["capaian"] = tampil["capaian"].apply(format_rp)
    tampil["sisa"] = tampil["sisa"].apply(format_rp)
    tampil["persen"] = tampil["persen"].apply(lambda x: f"{x:.2f}%")

    tampil = tampil[
    [
        "kode_dana",
        "kode_ma",
        "uraian",
        "pagu",
        "capaian",
        "jumlah_transaksi",
        "sisa",
        "persen",
        "pengendali"
    ]
]

    st.dataframe(
        tampil.style.applymap(warna_persen, subset=["persen"]),
        use_container_width=True
    )

    st.markdown("---")
    st.subheader("🔍 Detail Transaksi SIMRS")

    opsi_anggaran = (
        lap_f[lap_f["jumlah_transaksi"] > 0]
        .sort_values("capaian", ascending=False)
        ["uraian"]
        .unique()
    )

    pilih_uraian = st.selectbox(
        "Pilih Mata Anggaran",
        options=["-- Pilih --"] + list(opsi_anggaran)
    )

    if pilih_uraian != "-- Pilih --":
        key_terpilih = lap_f.loc[
            lap_f["uraian"] == pilih_uraian,
            "key"
        ].iloc[0]

        detail = simrs[
            (simrs["key"] == key_terpilih) &
            (simrs["nilai"] > 0)
        ]

        total_detail = detail["nilai"].sum()
        jumlah_dok = len(detail)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("💰 Total Nilai", f"Rp {format_rp(total_detail)}")
        with col2:
            st.metric("📄 Jumlah Dokumen", jumlah_dok)

        tampil_detail = detail.copy()
        tampil_detail["nilai"] = tampil_detail["nilai"].apply(format_rp)

        st.dataframe(
            tampil_detail[
            ["tanggal", "no_transaksi", "nama_anggaran", "nilai", "kepada"]
            ],
            use_container_width=True
        )

    st.caption(
    f"📅 Bulan dipilih: {', '.join(f_bulan)} | "
    f"👥 Pengendali: {', '.join(f_pengendali_realisasi)}" )

    st.download_button(
        "⬇️ Download Excel Realisasi Anggaran",
        data=export_excel_realisasi(tampil
        ),
        file_name="realisasi_anggaran.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    grafik = (
        lap_f.groupby("pengendali", as_index=False)
        .agg({"capaian": "sum", "pagu": "sum"})
    )

    chart = (
        alt.Chart(grafik)
        .transform_fold(["capaian", "pagu"], as_=["Jenis", "Nilai"])
        .mark_bar()
        .encode(
            y=alt.Y("pengendali:N", sort="-x", axis=alt.Axis(labelLimit=1000)),
            x=alt.X("Nilai:Q", axis=alt.Axis(format=",.0f")),
            color="Jenis:N"
        )
        .properties(height=30 * len(grafik))
    )

    st.altair_chart(chart, use_container_width=True)

    rekap = (
    lap_f.groupby("pengendali", as_index=False)
    .agg(
        pagu=("pagu", "sum"),
        capaian=("capaian", "sum")
    )
    )

    rekap["persen"] = (rekap["capaian"] / rekap["pagu"]).fillna(0) * 100

    total_row = pd.DataFrame([{
    "pengendali": "TOTAL",
    "pagu": rekap["pagu"].sum(),
    "capaian": rekap["capaian"].sum(),
    "persen": (rekap["capaian"].sum() / rekap["pagu"].sum()) * 100
    }])

    rekap_all = pd.concat([rekap, total_row], ignore_index=True)

    rekap_tampil = rekap_all.copy()
    rekap_tampil["pagu"] = rekap_tampil["pagu"].apply(format_rp)
    rekap_tampil["capaian"] = rekap_tampil["capaian"].apply(format_rp)
    rekap_tampil["persen"] = rekap_tampil["persen"].apply(lambda x: f"{x:.2f} %")

    st.subheader("📋 Rekap Realisasi per Pengendali")
    st.dataframe(
    rekap_tampil.style.applymap(warna_persen, subset=["persen"]),
    use_container_width=True)

    st.download_button(
    "📥 Export Realisasi Anggaran (Excel)",
    data=export_excel({
        "Realisasi Anggaran": tampil,
        "Rekap Pengendali": rekap_tampil
    }),
    file_name="Realisasi_Anggaran_SIMRS.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ======================================================
# TAB 2 – LAPORAN SIMRS
# ======================================================
with tab2:
    st.subheader("🔎 Filter Laporan SIMRS")

    f_kepada = st.multiselect(
        "Perusahaan / Kepada",
        sorted(simrs["kepada"].dropna().unique())
    )

    f_anggaran = st.multiselect(
        "Nama Anggaran",
        sorted(simrs["nama_anggaran"].dropna().unique())
    )

    f_pengendali = st.multiselect(
        "Pengendali",
        sorted(simrs["pengendali"].dropna().unique())
    )

    f_kode_anggaran = st.multiselect(
    "Kode Anggaran",
    sorted(simrs["kode_anggaran"].dropna().unique())
    )
    
    min_tgl = simrs["tanggal"].min()
    max_tgl = simrs["tanggal"].max()

    if pd.notna(min_tgl) and pd.notna(max_tgl):
        f_tgl = st.date_input(
            "Rentang Tanggal",
            [min_tgl.date(), max_tgl.date()]
        )
    else:
        f_tgl = None

    data = simrs.copy()

    if f_kepada:
        data = data[data["kepada"].isin(f_kepada)]
    if f_anggaran:
        data = data[data["nama_anggaran"].isin(f_anggaran)]
    if f_pengendali:
        data = data[data["pengendali"].isin(f_pengendali)]
    if f_kode_anggaran:
        data = data[data["kode_anggaran"].isin(f_kode_anggaran)]    
    if f_tgl:
        data = data[
            (data["tanggal"].dt.date >= f_tgl[0]) &
            (data["tanggal"].dt.date <= f_tgl[1])
        ]

    data_tampil = data.copy()
    data_tampil["nilai"] = data_tampil["nilai"].apply(format_rp)

    st.dataframe(data_tampil, use_container_width=True)

    st.download_button(
        "⬇️ Download Excel Laporan SIMRS",
        data=export_excel_simrs(data),
        file_name="laporan_simrs.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    total = data["nilai"].sum()
    jumlah_dokumen = (data["nilai"] > 0).sum()
    jumlah_batal = (data["nilai"] == 0).sum()    
    
    col1, col2 = st.columns(2)

    with col1:
        st.metric("💰 Total Nilai", f"Rp {format_rp(total)}")

    with col2:
        st.metric("📄 Jumlah Dokumen", f"{jumlah_dokumen}")

    with col2:
        st.metric("❌ Dokumen Batal", jumlah_batal)    
        
