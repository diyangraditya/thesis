import os
import requests
import json
import streamlit as st
import pandas as pd
import plotly.express as px

# Import SDK Gemini terbaru
from google import genai
from dotenv import load_dotenv
from config import TECH_OWNER_KNOWLEDGE

# --- SETUP ENVIRONMENT & API CLIENT ---
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OR_API_KEY = os.getenv("OR_API_KEY")

# Inisialisasi Client Gemini (Otomatis mendeteksi GEMINI_API_KEY dari .env)
if GEMINI_API_KEY:
    client = genai.Client()
else:
    client = None

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Cloud Cost - PT Jayantara", layout="wide")

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_data():
    try:
        df_lite = pd.read_csv("../cleaned-datasets/dashboard_data_FULL.csv")
        df_lite['timestamp'] = pd.to_datetime({
            'year': 2025, 'month': 2,
            'day': df_lite['day_of_month'], 'hour': df_lite['hour_of_day']
        })
    except FileNotFoundError:
        st.warning("Data tidak ditemukan. Menampilkan UI tanpa data grafik.")
        df_lite = pd.DataFrame()
    return df_lite

df_lite = load_data()

# --- HEADER & FILTER (TENGAH ATAS) ---
st.markdown("<h1 style='text-align: center;'>☁️ Identifikasi Peluang Optimasi Biaya Cloud AWS PT Jayantara pada Februari 2025 ☁️ ️</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 18px; color: gray;'>Dashboard ini menampilkan profil biaya, visualisasi performa, dan insight otomatis berbasis AI untuk setiap divisi (Tech Owner).</p>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 18px; color: gray;'>⚠️ <b>Tambahan Informasi</b> : Data yang digunakan terbatas pada periode bulan Februari 2025 dari tanggal 1-16 dikarenakan keterbatasan dan kualitas data</p>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

col_kosong1, col_filter, col_kosong2 = st.columns([1, 2, 1])
with col_filter:
    st.markdown("<h4 style='text-align: center;'>🔍 Pilih Divisi yang Ingin Dianalisis:</h4>", unsafe_allow_html=True)
    selected_owner = st.selectbox("Pilih Divisi (Tech Owner):", list(TECH_OWNER_KNOWLEDGE.keys()), label_visibility="collapsed")
st.markdown("<br>", unsafe_allow_html=True)

# BAGIAN A: PROFIL DIVISI & SUMMARY BIAYA
st.markdown("---")
st.header(f"Bagian A: Profil {selected_owner}")
info = TECH_OWNER_KNOWLEDGE[selected_owner]

col_a1, col_a2 = st.columns([2, 1])
with col_a1:
    st.markdown(f"**Nama Divisi:** {info['full_name']}")
    st.markdown(f"**Deskripsi Pekerjaan:** {info['description']}")
    st.markdown(f"**Scope Pekerjaan:** {info['scope']}")
    st.markdown(f"**Produk AWS yang Dikelola:** {', '.join(info['products_handled'])}")

    projects_display = info['projects_handled'][:5]
    if len(info['projects_handled']) > 5:
        st.markdown(f"**Proyek Utama:** {', '.join(projects_display)}, dan {len(info['projects_handled'])-5} lainnya.")
    else:
        st.markdown(f"**Proyek Utama:** {', '.join(projects_display)}")

with col_a2:
    st.markdown("### Ringkasan Biaya")
    if not df_lite.empty:
        owner_data = df_lite[df_lite['resource_tags_user_tech_owner'] == selected_owner]
        total_cost = owner_data['line_item_unblended_cost'].sum()
        unique_days = owner_data['day_of_month'].nunique()
        avg_daily_cost = total_cost / unique_days if unique_days > 0 else 0

        st.metric(label="Total Biaya (Actual)", value=f"${total_cost:,.2f}")
        st.metric(label="Rata-rata Biaya per Hari", value=f"${avg_daily_cost:,.2f}")
    else:
        st.metric(label="Total Biaya (Actual)", value="$0.00")
        st.metric(label="Rata-rata Biaya per Hari", value="$0.00")

# BAGIAN B: VISUALISASI DASHBOARD
st.markdown("---")
st.header("Bagian B: Visualisasi Pengeluaran & Distribusi Biaya")

if not df_lite.empty:
    owner_data = df_lite[df_lite['resource_tags_user_tech_owner'] == selected_owner]

    # --- BARIS 1 (Atas) ---
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        chart1_data = owner_data.groupby('timestamp')[['line_item_unblended_cost', 'predicted_cost']].sum().reset_index()
        df_melted = chart1_data.melt(id_vars=['timestamp'], value_vars=['line_item_unblended_cost', 'predicted_cost'], var_name='Cost Type', value_name='Total Cost (USD)')
        df_melted['Cost Type'] = df_melted['Cost Type'].replace({'line_item_unblended_cost': 'Actual Cost (Riil)', 'predicted_cost': 'Predicted Cost (Baseline AI)'})
        fig1 = px.line(df_melted, x='timestamp', y='Total Cost (USD)', color='Cost Type', color_discrete_map={"Actual Cost (Riil)": "#1f77b4", "Predicted Cost (Baseline AI)": "#ff7f0e"}, title=f"1. Tren Total Pengeluaran Biaya: Divisi {selected_owner}")
        fig1.update_traces(hovertemplate="<b>Cost Type = %{data.name}</b><br>Timestamp = %{x|%b %d, %Y, %H:%M}<br>Total Pengeluaran = $%{y:,.4f}<extra></extra>")
        fig1.update_layout(hovermode="closest", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1), xaxis_title="Trend Biaya pada bulan Februari 2025", yaxis_title="Total Biaya (USD)", margin=dict(l=0, r=0, t=40, b=50))
        fig1.update_xaxes(rangeslider=dict(visible=True, thickness=0.06, yaxis=dict(rangemode="fixed", range=[0, 0]), bgcolor="#260000", bordercolor="white", borderwidth=0), rangeselector=dict(buttons=list([dict(count=1, label="1 Hari", step="day", stepmode="backward"), dict(count=3, label="3 Hari", step="day", stepmode="backward"), dict(step="all", label="Semua")]), y=1))
        st.plotly_chart(fig1, use_container_width=True)

    with row1_col2:
        product_trend = owner_data.groupby(['timestamp', 'product_product_family'])['line_item_unblended_cost'].sum().reset_index()
        fig2 = px.line(product_trend, x='timestamp', y='line_item_unblended_cost', color='product_product_family', title=f"2. Tren Pengeluaran Biaya Tipe-tipe Servis AWS: Divisi {selected_owner}", labels={'product_product_family': 'Servis AWS', 'line_item_unblended_cost': 'Total Pengeluaran', 'timestamp': 'Timestamp'})
        fig2.update_traces(hovertemplate="<b>Servis AWS = %{data.name}</b><br>Total Pengeluaran = $%{y:,.4f}<extra></extra>")
        fig2.update_xaxes(rangeslider=dict(visible=True, thickness=0.06, bgcolor='#260000', bordercolor="white", borderwidth=0), rangeselector=dict(buttons=list([dict(count=1, label="1 Hari", step="day", stepmode="backward"), dict(count=3, label="3 Hari", step="day", stepmode="backward"), dict(step="all", label="Semua")]), y=0.96))
        fig2.update_layout(hovermode="x unified", xaxis_title="", yaxis_title="Biaya (USD)", legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5), margin=dict(l=0, r=0, t=60, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    # --- BARIS 2 (Bawah) ---
    st.markdown("<br>", unsafe_allow_html=True)
    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)

    with row2_col1:
        top_global = df_lite.groupby('resource_tags_user_tech_owner')['line_item_unblended_cost'].sum().nlargest(5).reset_index()
        fig3 = px.bar(top_global, x='line_item_unblended_cost', y='resource_tags_user_tech_owner', orientation='h', title="3. Top 5 Divisi PT Jayantara dengan Pengeluaran Terbesar", text_auto='.2s', color='line_item_unblended_cost', color_continuous_scale='Reds', labels={'line_item_unblended_cost': 'Total Pengeluaran', 'resource_tags_user_tech_owner': 'Divisi'})
        fig3.update_traces(hovertemplate="<b>Divisi = %{y}</b><br>Total Pengeluaran = $%{x:,.2f}<extra></extra>")
        fig3.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Biaya (USD)", yaxis_title="Divisi", showlegend=False, margin=dict(l=0, r=0, t=60, b=0))
        st.plotly_chart(fig3, use_container_width=True)

    with row2_col2:
        top_projects = owner_data.groupby('resource_tags_user_project')['line_item_unblended_cost'].sum().nlargest(6).reset_index()
        fig4 = px.bar(top_projects, x='resource_tags_user_project', y='line_item_unblended_cost', title=f"4. Top 6 Proyek Paling Boros Biaya dari Divisi {selected_owner}", text_auto='.2s', color='line_item_unblended_cost', color_continuous_scale='Blues', labels={'line_item_unblended_cost': 'Total Pengeluaran', 'resource_tags_user_project': 'Nama Proyek'})
        fig4.update_traces(hovertemplate="<b>Project = %{x}</b><br>Total Pengeluaran = $%{y:,.2f}<extra></extra>")
        fig4.update_layout(xaxis_title="Nama Proyek", yaxis_title="Total Biaya (USD)", showlegend=False, margin=dict(l=0, r=0, t=60, b=0))
        st.plotly_chart(fig4, use_container_width=True)

    with row2_col3:
        top_services_global = df_lite.groupby('product_product_family')['line_item_unblended_cost'].sum().nlargest(5).reset_index()
        fig5 = px.bar(top_services_global, x='line_item_unblended_cost', y='product_product_family', orientation='h', title="5. Top 5 Pengeluaran Servis AWS Terboros PT Jayantara", text_auto='.2s', color='line_item_unblended_cost', color_continuous_scale='Greens', labels={'line_item_unblended_cost': 'Total Pengeluaran', 'product_product_family': 'Servis AWS'})
        fig5.update_traces(hovertemplate="<b>Servis AWS = %{y}</b><br>Total Pengeluaran = $%{x:,.2f}<extra></extra>")
        fig5.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Biaya (USD)", yaxis_title="Servis AWS", showlegend=False, margin=dict(l=0, r=0, t=60, b=0))
        st.plotly_chart(fig5, use_container_width=True)

    with row2_col4:
        service_dist = owner_data.groupby('product_product_family')['line_item_unblended_cost'].sum().reset_index()
        total_owner_cost = service_dist['line_item_unblended_cost'].sum()
        fig6 = px.pie(service_dist, values='line_item_unblended_cost', names='product_product_family', hole=0.5, title=f"6. Porsi Biaya Servis AWS Divisi {selected_owner}")
        fig6.update_traces(textposition='inside', textinfo='percent', showlegend=True, hovertemplate="<b>Servis AWS = %{label}</b><br>Total Pengeluaran = $%{value:,.2f}<extra></extra>")
        fig6.add_annotation(text=f"TOTAL<br><b>${total_owner_cost:,.0f}</b>", x=0.5, y=0.5, font=dict(size=16, color="white"), showarrow=False)
        fig6.update_layout(margin=dict(l=20, r=20, t=60, b=20), legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5))
        st.plotly_chart(fig6, use_container_width=True)

# ==============================================================================
# BAGIAN C: NARASI AI (INTEGRASI GEMINI & MINIMAX API)
st.markdown("---")
st.header("🤖 AI Insight & Evaluasi Efisiensi")

# UI: Dropdown Model dan Tombol Generate
col_model, col_btn, col_kosong = st.columns([1, 1, 2])
with col_model:
    selected_model_ui = st.selectbox(
        "Pilih Model AI:",
        [
            "Gemini 2.5 Flash (Cepat & Ringan)",
            "Gemini 2.5 Pro (Analisis Mendalam)",
            "Minimax 2.5 (OpenRouter Gratis)"
        ],
        label_visibility="collapsed"
    )

    # ---------------------------------------------------------
    # KUNCI JAWABAN: LOGIKA ROUTING MODEL
    # ---------------------------------------------------------
    if "Gemini" in selected_model_ui:
        api_provider = "gemini"
        # Map ke model string resmi (kamu bisa ganti jadi 2.0-flash jika 2.5 belum rilis resmi di akunmu)
        api_model_name = "gemini-2.5-flash" if "Flash" in selected_model_ui else "gemini-2.5-pro"
    else:
        api_provider = "openrouter"
        api_model_name = "minimax/minimax-m2.5:free"

with col_btn:
    generate_btn = st.button("✨ Generate Insight", type="primary", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- EKSEKUSI GENERATE AI ---
if generate_btn:
    # 1. Pengecekan Kunci API berdasarkan Provider yang dipilih
    if api_provider == "gemini" and not client:
        st.error("⚠️ API Key Gemini belum ditemukan. Pastikan GEMINI_API_KEY sudah di-set di file .env!")
        st.stop()
    elif api_provider == "openrouter" and not OR_API_KEY:
        st.error("⚠️ API Key OpenRouter belum ditemukan. Pastikan OR_API_KEY sudah di-set di file .env!")
        st.stop()

    if df_lite.empty:
        st.warning("⚠️ Data CSV kosong. AI butuh data untuk dianalisis.")
        st.stop()

    # 2. Siapkan Data Konteks untuk Prompt (Data Preparation)
    owner_data = df_lite[df_lite['resource_tags_user_tech_owner'] == selected_owner]
    total_cost = owner_data['line_item_unblended_cost'].sum()

    top_projects_ai = owner_data.groupby('resource_tags_user_project')['line_item_unblended_cost'].sum().nlargest(3)
    top_proj_text = "\n".join([f"- {proj}: ${cost:,.2f}" for proj, cost in top_projects_ai.items()])

    top_services_ai = owner_data.groupby('product_product_family')['line_item_unblended_cost'].sum().nlargest(3)
    top_serv_text = "\n".join([f"- {serv}: ${cost:,.2f}" for serv, cost in top_services_ai.items()])

    # 3. Merakit Prompt Engineering
    the_prompt = f"""
    Anda adalah seorang Cloud FinOps Expert Senior di PT Jayantara.
    Tugas Anda adalah memberikan 'AI Insight & Evaluasi Efisiensi' biaya AWS untuk divisi {selected_owner} pada bulan Februari 2025.
    
    Berikut adalah konteks data divisi tersebut:
    - Scope Pekerjaan Divisi: {info['scope']}
    - Total Pengeluaran Bulan Ini: ${total_cost:,.2f}
    
    3 Proyek dengan Pengeluaran Terbesar:
    {top_proj_text}
    
    3 Servis AWS dengan Pengeluaran Terbesar:
    {top_serv_text}
    
    Berikan analisis yang tajam, profesional, dan actionable dengan format Markdown berikut (tanpa preamble/pembukaan kata-kata lain, langsung ke format):
    
    **1. Analisis Efisiensi:**
    (Evaluasi apakah pengeluaran ini wajar sesuai scope pekerjaan divisinya. Adakah konsentrasi biaya yang tidak wajar pada servis/proyek tertentu?)
    
    **2. Identifikasi Pemborosan (Technical Root Cause):**
    (Berikan asumsi teknis yang logis berdasarkan jenis servis termahal dan proyeknya. Gunakan istilah teknis AWS seperti EC2, Data Transfer, Storage, dll yang relevan).
    
    **3. Rekomendasi Optimasi Actionable:**
    (Berikan 3 bullet points rekomendasi teknis yang SANGAT spesifik untuk mengoptimalkan proyek dan servis dominan di atas).
    
    Gunakan bahasa Indonesia yang profesional, tegas, dan langsung pada intinya (seperti laporan eksekutif).
    """

    # 4. Eksekusi Panggilan API dengan animasi loading
    with st.spinner(f"🤖 Mengontak {selected_model_ui} untuk menganalisis data {selected_owner}..."):
        try:
            final_insight = "" # Variabel penampung hasil

            # --- JIKA MEMILIH GEMINI ---
            if api_provider == "gemini":
                # Menggunakan syntax SDK Baru: client.models.generate_content
                response = client.models.generate_content(
                    model=api_model_name,
                    contents=the_prompt
                )
                final_insight = response.text

            # --- JIKA MEMILIH MINIMAX (OPENROUTER) ---
            elif api_provider == "openrouter":
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OR_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    data=json.dumps({
                        "model": api_model_name,
                        "messages": [{"role": "user", "content": the_prompt}],
                        "reasoning": {"enabled": True}
                    }),
                    verify=False # Tetap dipertahankan untuk mengatasi error SSL di DataSpell
                )

                if response.status_code == 200:
                    response_json = response.json()
                    final_insight = response_json['choices'][0]['message']['content']
                else:
                    st.error(f"❌ Gagal memanggil API Minimax. Status Code: {response.status_code}\nPesan: {response.text}")
                    st.stop() # Hentikan proses jika gagal

            # 5. Tampilkan Hasilnya
            if final_insight:
                st.info(final_insight)
                st.toast('Insight berhasil di-generate!', icon='✅')

        except Exception as e:
            st.error(f"❌ Terjadi kesalahan pada sistem pemanggilan AI: {e}")

        # Catatan Khusus Error SSL pada Gemini:
        # Jika Gemini juga terkena Error SSL (CERTIFICATE_VERIFY_FAILED),
        # kamu wajib melakukan update certifi di terminal: pip install --upgrade certifi