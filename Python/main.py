import streamlit as st
import pandas as pd
import plotly.express as px
from config import TECH_OWNER_KNOWLEDGE

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Cloud Cost - PT Jalin Mayantara", layout="wide")

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_data():
    # Load data untuk grafik (Pastikan file ini ada di folder yang sama)
    try:
        df_lite = pd.read_csv("dashboard_data_lite.csv")
        df_lite['timestamp'] = pd.to_datetime({
            'year': 2025, 'month': 2,
            'day': df_lite['day_of_month'], 'hour': df_lite['hour_of_day']
        })
    except FileNotFoundError:
        # Jika file belum ada, buat dummy data sementara agar UI tetap jalan untuk demo dospem
        st.warning("File 'dashboard_data_lite.csv' tidak ditemukan. Menampilkan UI tanpa data grafik.")
        df_lite = pd.DataFrame()

    return df_lite

df_lite = load_data()

# HEADER & FILTER (Sesuai Sketsa: Pemilihan Tech Owner)
st.title("☁️ Identifikasi Peluang Optimasi Biaya Cloud AWS")
st.markdown("Dashboard ini menampilkan profil biaya, visualisasi performa, dan insight otomatis berbasis AI untuk setiap divisi (Tech Owner).")

# Filter Sidebar sesuai sketsa
st.sidebar.header("Pilih Parameter")
selected_owner = st.sidebar.selectbox("Pilih Divisi (Tech Owner):", list(TECH_OWNER_KNOWLEDGE.keys()))


# BAGIAN A: PROFIL DIVISI & SUMMARY BIAYA
st.markdown("---")
st.header(f"Bagian A: Profil {selected_owner}")

info = TECH_OWNER_KNOWLEDGE[selected_owner]

# Membagi layar jadi 2 kolom: Kiri untuk Deskripsi, Kanan untuk Angka Biaya (Harga per hari)
col_a1, col_a2 = st.columns([2, 1])

with col_a1:
    st.markdown(f"**Nama Divisi:** {info['full_name']}")
    st.markdown(f"**Deskripsi Pekerjaan:** {info['description']}")
    st.markdown(f"**Scope Pekerjaan:** {info['scope']}")
    st.markdown(f"**Produk AWS yang Dikelola:** {', '.join(info['products_handled'])}")

    # Menampilkan max 5 project agar UI tidak berantakan
    projects_display = info['projects_handled'][:5]
    if len(info['projects_handled']) > 5:
        st.markdown(f"**Proyek Utama:** {', '.join(projects_display)}, dan {len(info['projects_handled'])-5} lainnya.")
    else:
        st.markdown(f"**Proyek Utama:** {', '.join(projects_display)}")

with col_a2:
    st.markdown("### Ringkasan Biaya")
    # Menghitung Total dan Rata-rata harian (jika data CSV tersedia)
    if not df_lite.empty:
        owner_data = df_lite[df_lite['resource_tags_user_tech_owner'] == selected_owner]
        total_cost = owner_data['line_item_unblended_cost'].sum()

        # Hitung jumlah hari unik untuk rata-rata
        unique_days = owner_data['day_of_month'].nunique()
        avg_daily_cost = total_cost / unique_days if unique_days > 0 else 0

        st.metric(label="Total Biaya (Actual)", value=f"${total_cost:,.2f}")
        st.metric(label="Rata-rata Biaya per Hari", value=f"${avg_daily_cost:,.2f}")
    else:
        st.metric(label="Total Biaya (Actual)", value="$0.00")
        st.metric(label="Rata-rata Biaya per Hari", value="$0.00")

# BAGIAN B: VISUALISASI GRAFIK
st.markdown("---")
st.header("Bagian B: Visualisasi Performa & Akses Data")

if not df_lite.empty:
    # Filter data berdasarkan owner
    owner_data = df_lite[df_lite['resource_tags_user_tech_owner'] == selected_owner]

    # Plotly Line Chart
    df_melted = owner_data.melt(id_vars=['timestamp'],
                                value_vars=['line_item_unblended_cost', 'predicted_cost'],
                                var_name='Cost Type', value_name='Total Cost (USD)')

    df_melted['Cost Type'] = df_melted['Cost Type'].replace({
        'line_item_unblended_cost': 'Actual Cost (Riil)',
        'predicted_cost': 'Predicted Cost (Baseline AI)'
    })

    fig = px.line(df_melted, x='timestamp', y='Total Cost (USD)', color='Cost Type',
                  color_discrete_map={"Actual Cost (Riil)": "#1f77b4", "Predicted Cost (Baseline AI)": "#ff7f0e"},
                  markers=True,
                  title=f"Grafik Biaya: {selected_owner} (14 - 16 Februari)")

    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Grafik akan muncul di sini setelah data CSV di-load.")


# BAGIAN C: NARASI AI (PLACEHOLDER SEMENTARA)
st.markdown("---")
st.header("🤖 AI Insight & Evaluasi Efisiensi")

# Membuat kotak dengan warna latar belakang agar menonjol seperti output AI
st.info(f"""
**(INI ADALAH TEKS SEMENTARA (MOCKUP))**

Berdasarkan analisis data dari Bagian A (Profil {selected_owner}) dan Bagian B (Grafik Biaya), berikut adalah insight efisiensi operasional:

**1. Analisis Efisiensi:**
Secara umum, divisi **{selected_owner}** menunjukkan pola pengeluaran yang [**Efisiensi Terjaga / Terdapat Anomali**]. Terdapat deviasi biaya sebesar X% dibandingkan dengan prediksi baseline pada tanggal [Tanggal Anomali].

**2. Identifikasi Pemborosan (Technical Root Cause):**
Lonjakan biaya tersebut dipicu oleh tingginya aktivitas operasi **[Nama Operasi, misal: InterZone-Out]** pada layanan **[Nama Produk, misal: Data Transfer]**. Berdasarkan *scope* pekerjaan {selected_owner} yang fokus pada **{info['scope']}**, aktivitas ini kemungkinan berasal dari proyek **[Nama Proyek, misal: SIMPKB]** yang sedang melakukan sinkronisasi data antar zona secara masif.

**3. Rekomendasi Optimasi Actionable:**
* **Arsitektur:** Evaluasi arsitektur jaringan proyek [Nama Proyek]. Pastikan *resource* yang sering berkomunikasi diletakkan pada *Availability Zone* (AZ) yang sama untuk memangkas biaya *InterZone*.
* **Rightsizing:** Pertimbangkan untuk menghentikan layanan *[Nama Layanan]* jika tidak diperlukan di luar jam kerja.
* **Tagging:** Tingkatkan kedisiplinan pelabelan (*tagging*) untuk mempermudah alokasi biaya di masa depan.
""")

st.caption("Catatan: Narasi di atas akan digenerate secara otomatis (dinamis) oleh API LLM berdasarkan data aktual saat pengembangan dilanjutkan.")