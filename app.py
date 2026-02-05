import streamlit as st
import pandas as pd
import re
import altair as alt
from io import BytesIO
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# =============================
# KONFIGURASI AWAL
# =============================
st.set_page_config(page_title="Dashboard Anggaran SIMRS", layout="wide")
st.title("📊 Dashboard Anggaran SIMRS")

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
# URL GOOGLE DRIVE
# =============================
MA_DRIVE_URL = "https://docs.google.com/spreadsheets/d/15StwZUyvQ7jhkVE97sL6tSO5z3UPXk0-/export?format=xlsx"
SIMRS_DRIVE_URL = "https://docs.google.com/spreadsheets/d/1dS9ukqE-epEapvaAySZEuyyhYkZsBsxF/export?format=xlsx"
VERIFIKASI_DRIVE_URL = "https://docs.google.com/spreadsheets/d/1qhw5rS_dXNpcqzuOOQqdCQSvIhC1mAb1YC0Un_zf8_c/export?format=xlsx"
VERIFIKASI_FILE_ID = "1qhw5rS_dXNpcqzuOOQqdCQSvIhC1mAb1YC0Un_zf8_c"

# =============================
# FUNGSI GOOGLE DRIVE
# =============================
@st.cache_resource
def connect_gdrive():
    """Koneksi ke Google Drive"""
    try:
        scope = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]

        creds = Credentials.from_service_account_info(
            st.secrets["gdrive"],
            scopes=scope
        )

        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Gagal koneksi Google Drive: {e}")
        return None

def simpan_dokumen_bermasalah(df):
    """
    Menyimpan DataFrame dokumen bermasalah ke Google Sheet
    """
    try:
        client = connect_gdrive()
        if client is None:
            raise Exception("Koneksi Google Drive gagal")
            
        sheet = client.open_by_key(VERIFIKASI_FILE_ID).sheet1
        sheet.clear()
        sheet.update(
            [df.columns.tolist()] + df.astype(str).values.tolist()
        )
        return True
    except Exception as e:
        st.error(f"❌ Gagal menyimpan ke Google Drive: {e}")
        return False

# =============================
# FUNGSI UTILITY
# =============================
def export_excel(df_dict):
    """Export multiple dataframes ke Excel dengan multiple sheets"""
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

def export_excel_single(df, sheet_name="Sheet1"):
    """Export single dataframe ke Excel"""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    buffer.seek(0)
    return buffer

def normalisasi_angka(series):
    """Konversi format angka Indonesia ke float"""
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
    """Format angka ke Rupiah"""
    return f"{x:,.0f}".replace(",", ".")

def warna_persen(val):
    """Memberikan warna background berdasarkan persentase"""
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
    """Extract kode anggaran dan kode pengendali dari kode MA"""
    if pd.isna(kode):
        return None, None
    m = re.search(r"(\d{6})\.(\d+)\.\d+", str(kode))
    if not m:
        return None, None
    return m.group(1), m.group(2)

def ekstrak_kode_simrs(text):
    """Extract kode MA dari text SIMRS"""
    if pd.isna(text):
        return None
    m = re.search(r"(\d{6}\.\d+\.\d+)", str(text))
    return m.group(1) if m else None

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

# =============================
# SIDEBAR
# =============================
st.sidebar.success("✅ Login sebagai pengguna")

if st.sidebar.button("🚪 Logout"):
    # Reset semua session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
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
        try:
            st.session_state.ma_raw = pd.read_excel(ma_file)
            st.session_state.simrs_raw = pd.read_excel(simrs_file)
            st.session_state.data_source = "upload"
            st.success("✅ Data manual berhasil digunakan")
        except Exception as e:
            st.error(f"❌ Gagal membaca file: {e}")

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
    - Entry dan Laporan Verifikasi/ Masalah Dokumen 

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
    st.session_state.data_source = "drive"

# =============================
# LOAD DATA DEFAULT (GOOGLE DRIVE)
# =============================
if st.session_state.data_source == "drive" and st.session_state.ma_raw is None:
    try:
        with st.spinner("📂 Memuat data dari Google Drive..."):
            st.session_state.ma_raw = pd.read_excel(MA_DRIVE_URL)
            st.session_state.simrs_raw = pd.read_excel(SIMRS_DRIVE_URL)
        st.success("📂 Data default dimuat dari Google Drive")
    except Exception as e:
        st.error(f"❌ Gagal memuat data dari Google Drive: {e}")
        st.info("💡 Silakan upload data manual menggunakan sidebar")
        st.stop()

# =============================
# BACA MA SMART
# =============================
ma_raw = st.session_state.ma_raw

try:
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
except Exception as e:
    st.error(f"❌ Gagal memproses data MA SMART: {e}")
    st.stop()

# =============================
# BACA SIMRS
# =============================
simrs_raw = st.session_state.simrs_raw

try:
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
except Exception as e:
    st.error(f"❌ Gagal memproses data SIMRS: {e}")
    st.stop()

# =============================
# INFO UPDATE DATA
# =============================
last_update_simrs = simrs["tanggal"].max()

if pd.notna(last_update_simrs):
    info_update = last_update_simrs.strftime("%d %B %Y")
else:
    info_update = "Tanggal tidak tersedia"

# =============================
# TAB NAVIGASI
# =============================
tab1, tab2, tab3 = st.tabs([
    "📊 Realisasi Anggaran",
    "📄 Laporan SIMRS",
    "⚠️ Dokumen Bermasalah"
])

# ======================================================
# TAB 1 – REALISASI ANGGARAN
# ======================================================
with tab1:
    st.subheader("🔎 Filter Realisasi Anggaran")

    # Filter Bulan
    daftar_bulan = sorted(simrs["bulan"].dropna().unique())

    f_bulan = st.multiselect(
        "Pilih Bulan Realisasi",
        daftar_bulan,
        default=daftar_bulan
    )

    # Filter Pengendali
    daftar_pengendali = sorted(ma["pengendali"].dropna().unique())

    f_pengendali_realisasi = st.multiselect(
        "Pilih Pengendali",
        daftar_pengendali,
        default=daftar_pengendali
    )

    # Info sumber data
    sumber = "Google Drive" if st.session_state.data_source == "drive" else "Upload Manual"

    st.caption(
        f"📅 Data ({sumber}) terakhir diperbarui: **{info_update}**"
    )

    # =============================
    # HITUNG REALISASI SESUAI FILTER BULAN
    # =============================
    simrs_bulan = simrs.copy()

    if f_bulan:
        simrs_bulan = simrs_bulan[simrs_bulan["bulan"].isin(f_bulan)]

    realisasi_bulan = (
        simrs_bulan
        .groupby("key", as_index=False)
        .agg(
            capaian=("nilai", "sum"),
            jumlah_transaksi=("nilai", lambda x: (x > 0).sum())
        )
    )

    lap_f = ma.merge(realisasi_bulan, on="key", how="left")
    lap_f["capaian"] = lap_f["capaian"].fillna(0)
    lap_f["jumlah_transaksi"] = lap_f["jumlah_transaksi"].fillna(0).astype(int)
    lap_f["sisa"] = lap_f["pagu"] - lap_f["capaian"]
    lap_f["persen"] = (lap_f["capaian"] / lap_f["pagu"]).fillna(0) * 100

    # Filter pengendali
    if f_pengendali_realisasi:
        lap_f = lap_f[lap_f["pengendali"].isin(f_pengendali_realisasi)]

    # Format untuk tampilan
    tampil = lap_f.copy()
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

        # Filter hanya transaksi di bulan terpilih
        detail = simrs[
            (simrs["key"] == key_terpilih) &
            (simrs["nilai"] > 0)
        ]
        
        if f_bulan:
            detail = detail[detail["bulan"].isin(f_bulan)]

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
        f"👥 Pengendali: {', '.join(f_pengendali_realisasi)}"
    )

    st.download_button(
        "⬇️ Download Excel Realisasi Anggaran",
        data=export_excel_single(tampil, "Realisasi_Anggaran"),
        file_name="realisasi_anggaran.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # =============================
    # GRAFIK REALISASI
    # =============================
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

    # =============================
    # REKAP PER PENGENDALI
    # =============================
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
        use_container_width=True
    )

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

    # =============================
    # TERAPKAN FILTER
    # =============================
    data = simrs.copy()

    if f_kepada:
        data = data[data["kepada"].isin(f_kepada)]
    if f_anggaran:
        data = data[data["nama_anggaran"].isin(f_anggaran)]
    if f_pengendali:
        data = data[data["pengendali"].isin(f_pengendali)]
    if f_kode_anggaran:
        data = data[data["kode_anggaran"].isin(f_kode_anggaran)]    
    if f_tgl and len(f_tgl) == 2:
        data = data[
            (data["tanggal"].dt.date >= f_tgl[0]) &
            (data["tanggal"].dt.date <= f_tgl[1])
        ]

    data_tampil = data.copy()
    data_tampil["nilai"] = data_tampil["nilai"].apply(format_rp)

    st.dataframe(data_tampil, use_container_width=True)

    st.download_button(
        "⬇️ Download Excel Laporan SIMRS",
        data=export_excel_single(data, "Laporan_SIMRS"),
        file_name="laporan_simrs.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # =============================
    # METRIK
    # =============================
    total = data["nilai"].sum()
    jumlah_dokumen = (data["nilai"] > 0).sum()
    jumlah_batal = (data["nilai"] == 0).sum()    
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("💰 Total Nilai", f"Rp {format_rp(total)}")

    with col2:
        st.metric("📄 Jumlah Dokumen", f"{jumlah_dokumen}")

    with col3:
        st.metric("❌ Dokumen Batal", jumlah_batal)

# ======================================================
# TAB 3 – DOKUMEN BERMASALAH
# ======================================================
with tab3:
    st.subheader("⚠️ Dokumen / Tagihan Bermasalah")
    
    # =============================
    # FORM ENTRY (COLLAPSIBLE)
    # =============================
    with st.expander("➕ Entry Dokumen Bermasalah Baru", expanded=False):
        with st.form("form_tagihan_bermasalah", clear_on_submit=True):

            tgl_verifikasi = st.date_input(
                "📅 Tanggal Verifikasi",
                value=date.today()
            )

            perusahaan = st.text_input("🏢 Nama Perusahaan / Kepada")
            keterangan = st.text_area("📝 Keterangan Tagihan")
            no_dokumen = st.text_input("📄 No. Dokumen")
            nilai = st.number_input(
                "💰 Nilai Tagihan",
                min_value=0.0,
                step=1000.0
            )
            masalah = st.text_area("❌ Masalah / Kesalahan Dokumen")

            status_selesai = st.checkbox("✅ Masalah sudah selesai")

            submit = st.form_submit_button("💾 Simpan Dokumen Bermasalah")

            if submit:
                # Validasi input
                if not perusahaan or not no_dokumen or not masalah:
                    st.error("❌ Perusahaan, No. Dokumen, dan Masalah harus diisi!")
                else:
                    data_baru = pd.DataFrame([{
                        "tanggal_verifikasi": pd.to_datetime(tgl_verifikasi),
                        "perusahaan": perusahaan,
                        "keterangan": keterangan,
                        "no_dokumen": no_dokumen,
                        "nilai": nilai,
                        "masalah": masalah,
                        "status": "SELESAI" if status_selesai else "BELUM",
                        "tanggal_input": pd.to_datetime(date.today())
                    }])

                    # Load data lama dari Google Drive
                    try:
                        df_lama = pd.read_excel(VERIFIKASI_DRIVE_URL)
                        if not df_lama.empty:
                            df_all = pd.concat([df_lama, data_baru], ignore_index=True)
                        else:
                            df_all = data_baru
                    except Exception as e:
                        # Jika file belum ada, gunakan data baru saja
                        df_all = data_baru

                    # Simpan ke Google Drive
                    if simpan_dokumen_bermasalah(df_all):
                        st.success("✅ Data berhasil disimpan ke Google Drive")
                        st.rerun()
                    else:
                        st.error("❌ Gagal menyimpan data. Silakan coba lagi.")

    st.markdown("---")
    st.subheader("📋 Daftar Dokumen Bermasalah")

    # Tombol refresh manual
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("🔄 Refresh"):
            st.rerun()

    # =============================
    # LOAD DATA DARI GOOGLE DRIVE
    # =============================
    try:
        with st.spinner("📂 Memuat data dokumen bermasalah..."):
            df_verif = pd.read_excel(VERIFIKASI_DRIVE_URL)
            
            # Pastikan kolom yang diperlukan ada
            required_columns = ['tanggal_verifikasi', 'perusahaan', 'keterangan', 
                              'no_dokumen', 'nilai', 'masalah', 'status']
            
            # Jika DataFrame kosong atau tidak punya kolom yang benar, inisialisasi
            if df_verif.empty or not all(col in df_verif.columns for col in required_columns):
                df_verif = pd.DataFrame(columns=required_columns)
                
    except Exception as e:
        st.warning(f"⚠️ Tidak bisa membaca data dari Google Drive: {e}")
        st.info("💡 Pastikan Google Sheet sudah di-share ke service account")
        # Buat DataFrame kosong dengan struktur yang benar
        df_verif = pd.DataFrame(columns=['tanggal_verifikasi', 'perusahaan', 'keterangan', 
                                        'no_dokumen', 'nilai', 'masalah', 'status', 'tanggal_input'])

    if df_verif.empty:
        st.info("ℹ️ Belum ada data dokumen bermasalah. Silakan entry data baru di form di atas.")
    else:
        # Tampilkan jumlah total data
        st.success(f"📊 Total data: **{len(df_verif)}** dokumen bermasalah tersimpan di Google Drive")
        
        st.download_button(
            "⬇️ Download Excel Dokumen Bermasalah",
            data=export_excel_single(df_verif, "Dokumen_Bermasalah"),
            file_name="dokumen_bermasalah.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # =============================
        # FILTER DATA
        # =============================
        st.markdown("### 🔍 Filter Data")
        
        # Convert tanggal ke datetime
        df_verif["tanggal_verifikasi"] = pd.to_datetime(
            df_verif["tanggal_verifikasi"], errors="coerce"
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            min_tgl = df_verif["tanggal_verifikasi"].min()
            max_tgl = df_verif["tanggal_verifikasi"].max()

            if pd.notna(min_tgl) and pd.notna(max_tgl):
                f_tgl = st.date_input(
                    "📅 Rentang Tanggal",
                    [min_tgl.date(), max_tgl.date()],
                    key="filter_tgl_verif"
                )
            else:
                f_tgl = None

        with col2:
            unique_perusahaan = df_verif["perusahaan"].dropna().unique().tolist()
            f_perusahaan = st.multiselect(
                "🏢 Perusahaan",
                sorted(unique_perusahaan) if unique_perusahaan else [],
                help="Kosongkan untuk tampilkan semua"
            )

        with col3:
            f_no = st.text_input("📄 Cari No. Dokumen", help="Ketik sebagian nomor dokumen")

        with col4:
            # Default filter: tampilkan SEMUA status
            f_status = st.multiselect(
                "📌 Status",
                ["BELUM", "SELESAI"],
                default=["BELUM", "SELESAI"],
                help="Pilih status yang ingin ditampilkan"
            )

        # =============================
        # TERAPKAN FILTER
        # =============================
        data = df_verif.copy()
        
        # Tambahkan index sebagai ID untuk edit/delete
        data = data.reset_index(drop=False)
        data.rename(columns={'index': 'id'}, inplace=True)

        if f_tgl and len(f_tgl) == 2:
            data = data[
                (data["tanggal_verifikasi"].dt.date >= f_tgl[0]) &
                (data["tanggal_verifikasi"].dt.date <= f_tgl[1])
            ]

        if f_perusahaan:
            data = data[data["perusahaan"].isin(f_perusahaan)]

        if f_no:
            data = data[
                data["no_dokumen"]
                .astype(str)
                .str.contains(f_no, case=False, na=False)
            ]

        if f_status:
            data = data[data["status"].isin(f_status)]

        # =============================
        # EDIT STATUS & HAPUS DATA
        # =============================
        st.markdown("### ✏️ Edit Status atau Hapus Data")
        
        if not data.empty:
            # Pilih dokumen untuk edit/hapus
            opsi_dokumen = data.apply(
                lambda row: f"[{row['no_dokumen']}] {row['perusahaan']} - {row['status']}", 
                axis=1
            ).tolist()
            
            col_select, col_action = st.columns([3, 1])
            
            with col_select:
                selected_doc = st.selectbox(
                    "Pilih Dokumen:",
                    options=["-- Pilih Dokumen --"] + opsi_dokumen,
                    key="select_doc_edit"
                )
            
            if selected_doc != "-- Pilih Dokumen --":
                # Ambil index dokumen yang dipilih
                selected_idx = opsi_dokumen.index(selected_doc)
                selected_row = data.iloc[selected_idx]
                doc_id = selected_row['id']
                
                with col_action:
                    st.write("")  # Spacing
                    st.write("")  # Spacing
                    action_type = st.radio(
                        "Aksi:",
                        ["Ubah Status", "Hapus Data"],
                        horizontal=True,
                        key="action_radio"
                    )
                
                st.markdown("---")
                
                # AKSI: UBAH STATUS
                if action_type == "Ubah Status":
                    st.info(f"📄 **Dokumen:** {selected_row['no_dokumen']} | **Perusahaan:** {selected_row['perusahaan']}")
                    st.warning(f"⚠️ **Status Saat Ini:** {selected_row['status']}")
                    
                    col_status, col_btn = st.columns([2, 1])
                    
                    with col_status:
                        new_status = st.selectbox(
                            "Ubah Status Menjadi:",
                            ["BELUM", "SELESAI"],
                            index=0 if selected_row['status'] == "BELUM" else 1,
                            key="new_status_select"
                        )
                    
                    with col_btn:
                        st.write("")  # Spacing
                        if st.button("💾 Simpan Perubahan", type="primary", key="btn_update_status"):
                            # Update status di DataFrame
                            df_verif.loc[doc_id, 'status'] = new_status
                            
                            # Simpan ke Google Drive
                            if simpan_dokumen_bermasalah(df_verif):
                                st.success(f"✅ Status berhasil diubah menjadi: **{new_status}**")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Gagal menyimpan perubahan")
                
                # AKSI: HAPUS DATA
                elif action_type == "Hapus Data":
                    st.error(f"⚠️ **PERHATIAN:** Anda akan menghapus data berikut:")
                    
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.write(f"**No. Dokumen:** {selected_row['no_dokumen']}")
                        st.write(f"**Perusahaan:** {selected_row['perusahaan']}")
                        st.write(f"**Tanggal:** {selected_row['tanggal_verifikasi']}")
                    with col_info2:
                        st.write(f"**Nilai:** Rp {format_rp(float(selected_row['nilai']))}")
                        st.write(f"**Status:** {selected_row['status']}")
                        st.write(f"**Masalah:** {selected_row['masalah'][:50]}...")
                    
                    st.markdown("---")
                    
                    col_confirm, col_delete = st.columns([3, 1])
                    
                    with col_confirm:
                        confirm_text = st.text_input(
                            "Ketik 'HAPUS' untuk konfirmasi:",
                            key="confirm_delete"
                        )
                    
                    with col_delete:
                        st.write("")  # Spacing
                        if st.button("🗑️ Hapus Data", type="primary", key="btn_delete", disabled=(confirm_text != "HAPUS")):
                            # Hapus data dari DataFrame
                            df_verif = df_verif.drop(doc_id).reset_index(drop=True)
                            
                            # Simpan ke Google Drive
                            if simpan_dokumen_bermasalah(df_verif):
                                st.success("✅ Data berhasil dihapus!")
                                st.rerun()
                            else:
                                st.error("❌ Gagal menghapus data")
        else:
            st.info("ℹ️ Tidak ada data untuk diedit atau dihapus")

        # =============================
        # TAMPILAN TABEL DATA
        # =============================
        st.markdown("---")
        st.markdown("### 📊 Tabel Data Dokumen Bermasalah")
        
        # Reset data tanpa kolom 'id' untuk tampilan
        data_tampil = data.copy()
        if 'id' in data_tampil.columns:
            data_tampil = data_tampil.drop('id', axis=1)
        
        # Format nilai ke Rupiah
        if "nilai" in data_tampil.columns:
            data_tampil["nilai"] = data_tampil["nilai"].apply(lambda x: format_rp(float(x)) if pd.notna(x) else "0")
        
        # Format tanggal
        if "tanggal_verifikasi" in data_tampil.columns:
            data_tampil["tanggal_verifikasi"] = data_tampil["tanggal_verifikasi"].dt.strftime("%Y-%m-%d")

        # Pilih kolom yang akan ditampilkan
        display_columns = []
        for col in ["tanggal_verifikasi", "perusahaan", "keterangan", "no_dokumen", "nilai", "masalah", "status"]:
            if col in data_tampil.columns:
                display_columns.append(col)

        # Tampilkan dataframe dengan styling untuk status
        def highlight_status(row):
            if row['status'] == 'SELESAI':
                return ['background-color: #d4edda'] * len(row)
            else:
                return ['background-color: #fff3cd'] * len(row)

        st.dataframe(
            data_tampil[display_columns].style.apply(highlight_status, axis=1),
            use_container_width=True,
            height=400
        )

        st.caption(f"📊 Menampilkan **{len(data_tampil)}** dari **{len(df_verif)}** total dokumen")
        
        # Ringkasan status
        if not data.empty:
            status_count = data['status'].value_counts()
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                belum = status_count.get('BELUM', 0)
                st.metric("⏳ Belum Selesai", belum)
            with col_stat2:
                selesai = status_count.get('SELESAI', 0)
                st.metric("✅ Sudah Selesai", selesai)
