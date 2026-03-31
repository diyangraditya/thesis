import streamlit as st
import pandas as pd
import plotly.express as px
from config import TECH_OWNER_KNOWLEDGE
from dotenv import load_dotenv

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Cloud Cost - PT Jalin Mayantara", layout="wide")

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_data():
    # Load data untuk grafik (Pastikan file ini ada di folder yang sama)
    try:
        df_lite = pd.read_csv("../cleaned-datasets/dashboard_data_FULL.csv")
        df_lite['timestamp'] = pd.to_datetime({
            'year': 2025, 'month': 2,
            'day': df_lite['day_of_month'], 'hour': df_lite['hour_of_day']
        })
    except FileNotFoundError:
        # Jika file belum ada, buat dummy data sementara agar UI tetap jalan untuk demo dospem
        st.warning("Data tidak ditemukan. Menampilkan UI tanpa data grafik.")
        df_lite = pd.DataFrame()

    return df_lite

df_lite = load_data()

# ==============================================================================
# --- HEADER & FILTER (TENGAH ATAS) ---
# Menggunakan HTML untuk menengahkan teks judul dan deskripsi
st.markdown("<h1 style='text-align: center;'>☁️ Identifikasi Peluang Optimasi Biaya Cloud AWS ☁️ ️</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 18px; color: gray;'>Dashboard ini menampilkan profil biaya, visualisasi performa, dan insight otomatis berbasis AI untuk setiap divisi (Tech Owner).</p>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True) # Jarak estetik

# Trik menengahkan Dropdown Filter: Bikin 3 kolom, taruh dropdown di kolom tengah
col_kosong1, col_filter, col_kosong2 = st.columns([1, 2, 1])

with col_filter:
    st.markdown("<h4 style='text-align: center;'>🔍 Pilih Divisi yang Ingin Dianalisis:</h4>", unsafe_allow_html=True)
    # label_visibility="collapsed" menyembunyikan label bawaan agar UI lebih bersih
    selected_owner = st.selectbox("Pilih Divisi (Tech Owner):", list(TECH_OWNER_KNOWLEDGE.keys()), label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True) # Jarak estetik
# ==============================================================================


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

# BAGIAN B: VISUALISASI DASHBOARD (Konteks Biaya & Servis)
st.markdown("---")
st.header("Bagian B: Visualisasi Performa & Distribusi Biaya")

if not df_lite.empty:
    # Filter data berdasarkan owner (Untuk grafik yang dinamis)
    owner_data = df_lite[df_lite['resource_tags_user_tech_owner'] == selected_owner]

    # ==============================================================================
    # --- BARIS 1 (Atas) --- [2 Kolom Dibagi Rata: Rasio 1:1]
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        # 1. KIRI ATAS: Line Chart Actual vs Predicted
        chart1_data = owner_data.groupby('timestamp')[['line_item_unblended_cost', 'predicted_cost']].sum().reset_index()
        df_melted = chart1_data.melt(id_vars=['timestamp'], value_vars=['line_item_unblended_cost', 'predicted_cost'],
                                     var_name='Cost Type', value_name='Total Cost (USD)')
        df_melted['Cost Type'] = df_melted['Cost Type'].replace({
            'line_item_unblended_cost': 'Actual Cost (Riil)', 'predicted_cost': 'Predicted Cost (Baseline AI)'
        })

        fig1 = px.line(df_melted, x='timestamp', y='Total Cost (USD)', color='Cost Type',
                       color_discrete_map={"Actual Cost (Riil)": "#1f77b4", "Predicted Cost (Baseline AI)": "#ff7f0e"},
                       title=f"1. Tren Biaya Keseluruhan: {selected_owner}")

        fig1.update_layout(
            hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title="Trend Biaya pada bulan Februari 2025", yaxis_title="Total Biaya (USD)",
            margin=dict(l=0, r=0, t=40, b=0)
        )

        fig1.update_xaxes(
            rangeslider=dict(visible=True, thickness=0.04),
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1 Hari", step="day", stepmode="backward"),
                    dict(count=3, label="3 Hari", step="day", stepmode="backward"),
                    dict(step="all", label="Semua")
                ]), y=1.06
            )
        )
        st.plotly_chart(fig1, use_container_width=True)

    with row1_col2:
        # 2. KANAN ATAS: Bar Chart Top 6 Project
        top_projects = owner_data.groupby('resource_tags_user_project')['line_item_unblended_cost'].sum().nlargest(6).reset_index()

        fig2 = px.bar(top_projects, x='resource_tags_user_project', y='line_item_unblended_cost',
                      title=f"2. Top 6 Proyek Termahal ({selected_owner})",
                      text_auto='.2s', color='line_item_unblended_cost', color_continuous_scale='Blues')

        fig2.update_layout(xaxis_title="Nama Proyek", yaxis_title="Total Biaya (USD)", showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig2, use_container_width=True)


    # ==============================================================================
    # --- BARIS 2 (Bawah) --- [3 Kolom Dibagi Rata: Rasio 1:1:1]
    st.markdown("<br>", unsafe_allow_html=True)
    row2_col1, row2_col2, row2_col3 = st.columns(3)

    with row2_col1:
        # 3. KIRI BAWAH: Horizontal Bar Chart Top 5 Tech Owner GLOBAL (Statis)
        top_global = df_lite.groupby('resource_tags_user_tech_owner')['line_item_unblended_cost'].sum().nlargest(5).reset_index()

        fig3 = px.bar(top_global, x='line_item_unblended_cost', y='resource_tags_user_tech_owner', orientation='h',
                      title="3. 5 Divisi Termahal (Global PT Jalin)",
                      text_auto='.2s', color='line_item_unblended_cost', color_continuous_scale='Reds')

        fig3.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Biaya (USD)", yaxis_title="", showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig3, use_container_width=True)

    with row2_col2:
        # 4. TENGAH BAWAH: Line Chart Tren per Product Family
        product_trend = owner_data.groupby(['timestamp', 'product_product_family'])['line_item_unblended_cost'].sum().reset_index()

        fig4 = px.line(product_trend, x='timestamp', y='line_item_unblended_cost', color='product_product_family',
                       title=f"4. Tren Biaya Tipe Servis ({selected_owner})")

        fig4.update_xaxes(
            rangeslider=dict(visible=True, thickness=0.04),
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1 Hari", step="day", stepmode="backward"),
                    dict(count=3, label="3 Hari", step="day", stepmode="backward"),
                    dict(step="all", label="Semua")
                ]), y=1.06
            )
        )
        # Menaruh legend di bawah agar tidak memakan tempat horizontal
        fig4.update_layout(hovermode="x unified", xaxis_title="", yaxis_title="Biaya (USD)",
                           legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5), margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig4, use_container_width=True)

    with row2_col3:
        # 5. KANAN BAWAH (BARU): Donut Chart Porsi Tipe Servis AWS
        # Memperlihatkan servis apa yang paling banyak "dimakan" selama sebulan
        service_dist = owner_data.groupby('product_product_family')['line_item_unblended_cost'].sum().reset_index()

        fig5 = px.pie(service_dist, values='line_item_unblended_cost', names='product_product_family', hole=0.4,
                      title=f"5. Porsi Tipe Servis AWS ({selected_owner})")

        # Tampilkan persentase di dalam donat, legend ditaruh di bawah
        fig5.update_traces(textposition='inside', textinfo='percent+label', showlegend=False)
        fig5.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig5, use_container_width=True)

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