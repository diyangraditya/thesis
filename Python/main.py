import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px

# Import SDK
from google import genai
from dotenv import load_dotenv
from config import TECH_OWNER_KNOWLEDGE

# --- SETUP ENVIRONMENT & API CLIENT ---
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OR_API_KEY = os.getenv("OR_API_KEY")

# Model ID GPT OSS dari OR
OPENROUTER_GPT_OSS_MODEL = os.getenv(
    "OPENROUTER_GPT_OSS_MODEL",
    "openai/gpt-oss-120b:free"
)

# MODEL ID NVIDIA Nemotron dari OR
OPENROUTER_NEMOTRON_MODEL = os.getenv(
    "OPENROUTER_NEMOTRON_MODEL",
    "nvidia/nemotron-3-nano-30b-a3b:free"
)

# Client Gemini
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Cloud Cost - PT Jalin Mayantara", layout="wide")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    try:
        df_lite = pd.read_csv("../cleaned-datasets/dashboard_data_FULL-1.csv")
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

st.markdown("<p style='text-align: center; font-size: 18px; color: gray;'>⚠️ <b>Tambahan Informasi</b> : Data yang digunakan terbatas pada periode bulan Februari 2025 dari tanggal 1-16 dikarenakan keterbatasan kualitas data</p>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col_kosong1, col_filter, col_kosong2 = st.columns([1, 2, 1])

with col_filter:
    st.markdown("<h4 style='text-align: center;'>Pilih Divisi yang Ingin Dianalisis:</h4>", unsafe_allow_html=True)

    selected_owner = st.selectbox("Pilih Divisi (Tech Owner):",
                                  list(TECH_OWNER_KNOWLEDGE.keys()),
                                  label_visibility="collapsed")

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
        owner_data = df_lite[
            df_lite['resource_tags_user_tech_owner'] == selected_owner
        ].copy()

        total_actual_cost = owner_data['line_item_unblended_cost'].sum()
        total_predicted_cost = owner_data['predicted_cost'].sum()

        cost_difference = total_actual_cost - total_predicted_cost

        unique_days = owner_data['day_of_month'].nunique()
        avg_daily_cost = (
            total_actual_cost / unique_days
            if unique_days > 0 else 0
        )

        st.metric(
            label="Total Biaya Aktual",
            value=f"${total_actual_cost:,.2f}"
        )

        st.metric(
            label="Estimasi Biaya Random Forest",
            value=f"${total_predicted_cost:,.2f}"
        )

        st.metric(
            label="Selisih Aktual terhadap Estimasi",
            value=f"${cost_difference:,.2f}",
            help=(
                "Nilai positif menunjukkan biaya aktual lebih tinggi "
                "daripada estimasi model Random Forest."
            )
        )

        st.metric(
            label="Rata-rata Biaya per Hari",
            value=f"${avg_daily_cost:,.2f}"
        )

    else:
        st.metric("Total Biaya Aktual", "$0.00")
        st.metric("Estimasi Biaya Random Forest", "$0.00")
        st.metric("Selisih Aktual terhadap Estimasi", "$0.00")
        st.metric("Rata-rata Biaya per Hari", "$0.00")

# BAGIAN B: VISUALISASI DASHBOARD
st.markdown("---")
st.header("Bagian B: Visualisasi Pengeluaran & Distribusi Biaya")

if not df_lite.empty:
    owner_data = df_lite[df_lite['resource_tags_user_tech_owner'] == selected_owner]

    # --- BARIS 1 (Atas) ---
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        chart1_data = owner_data.groupby('timestamp')[['line_item_unblended_cost', 'predicted_cost']].sum().reset_index()
        df_melted = chart1_data.melt(id_vars=['timestamp'],
                                     value_vars=['line_item_unblended_cost', 'predicted_cost'],
                                     var_name='Cost Type',
                                     value_name='Total Cost (USD)')

        df_melted['Cost Type'] = df_melted['Cost Type'].replace({'line_item_unblended_cost': 'Biaya Aktual',
                                                                 'predicted_cost': 'Estimasi Biaya Random Forest'})

        fig1 = px.line(df_melted,
                       x='timestamp', y='Total Cost (USD)',
                       color='Cost Type', color_discrete_map={"Biaya Aktual": "#1f77b4", "Estimasi Biaya Random Forest": "#ff7f0e"}, title=f"1. Tren Total Pengeluaran Biaya: Divisi {selected_owner}")

        fig1.update_traces(hovertemplate="<b>Cost Type = %{data.name}</b><br>Timestamp = %{x|%b %d, %Y, %H:%M}<br>Total Pengeluaran = $%{y:,.4f}<extra></extra>")

        fig1.update_layout(hovermode="closest", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1),                                xaxis_title="Trend Biaya pada bulan Februari 2025",
                           yaxis_title="Total Biaya (USD)", margin=dict(l=0, r=0, t=40, b=50))

        fig1.update_xaxes(rangeslider=dict(visible=True, thickness=0.06, yaxis=dict(rangemode="fixed", range=[0, 0]),
                                           bgcolor="#260000", bordercolor="white", borderwidth=0),
                          rangeselector=dict(buttons=list([dict(count=1, label="1 Hari", step="day", stepmode="backward"),
                                                           dict(count=3, label="3 Hari", step="day", stepmode="backward"), dict(step="all", label="Semua")]), y=1))

        st.plotly_chart(fig1, use_container_width=True)

    with row1_col2:
        product_trend = owner_data.groupby(['timestamp', 'product_product_family'])['line_item_unblended_cost'].sum().reset_index()

        fig2 = px.line(product_trend, x='timestamp',
                       y='line_item_unblended_cost', color='product_product_family',
                       title=f"2. Tren Pengeluaran Biaya Tipe-tipe Servis AWS: Divisi {selected_owner}",
                       labels={'product_product_family': 'Servis AWS', 'line_item_unblended_cost': 'Total Pengeluaran', 'timestamp': 'Timestamp'})

        fig2.update_traces(hovertemplate="<b>Servis AWS = %{data.name}</b><br>Total Pengeluaran = $%{y:,.4f}<extra></extra>")

        fig2.update_xaxes(rangeslider=dict(visible=True, thickness=0.06, bgcolor='#260000', bordercolor="white", borderwidth=0), rangeselector=dict(buttons=list([dict(count=1, label="1 Hari", step="day", stepmode="backward"), dict(count=3, label="3 Hari", step="day", stepmode="backward"), dict(step="all", label="Semua")]), y=0.96))

        fig2.update_layout(hovermode="x unified", xaxis_title="", yaxis_title="Biaya (USD)",
                           legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
                           margin=dict(l=0, r=0, t=60, b=0))

        st.plotly_chart(fig2, use_container_width=True)

    # --- BARIS 2 ---
    st.markdown("<br>", unsafe_allow_html=True)
    row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)

    with row2_col1:
        top_global = df_lite.groupby('resource_tags_user_tech_owner')['line_item_unblended_cost'].sum().nlargest(5).reset_index()

        fig3 = px.bar(top_global, x='line_item_unblended_cost',
                      y='resource_tags_user_tech_owner', orientation='h',
                      title="3. Top 5 Divisi PT Jayantara dengan Pengeluaran Terbesar", text_auto='.2s',
                      color='line_item_unblended_cost', color_continuous_scale='Reds',
                      labels={'line_item_unblended_cost': 'Total Pengeluaran', 'resource_tags_user_tech_owner': 'Divisi'})

        fig3.update_traces(hovertemplate="<b>Divisi = %{y}</b><br>Total Pengeluaran = $%{x:,.2f}<extra></extra>")

        fig3.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Biaya (USD)",
                           yaxis_title="Divisi", showlegend=False, margin=dict(l=0, r=0, t=60, b=0))

        st.plotly_chart(fig3, use_container_width=True)

    with row2_col2:
        top_projects = owner_data.groupby('resource_tags_user_project')['line_item_unblended_cost'].sum().nlargest(6).reset_index()

        fig4 = px.bar(top_projects, x='resource_tags_user_project',
                      y='line_item_unblended_cost', title=f"4. Top 6 Proyek Paling Boros Biaya dari Divisi {selected_owner}", text_auto='.2s', color='line_item_unblended_cost',
                      color_continuous_scale='Blues',
                      labels={'line_item_unblended_cost': 'Total Pengeluaran', 'resource_tags_user_project': 'Nama Proyek'})

        fig4.update_traces(hovertemplate="<b>Project = %{x}</b><br>Total Pengeluaran = $%{y:,.2f}<extra></extra>")

        fig4.update_layout(xaxis_title="Nama Proyek", yaxis_title="Total Biaya (USD)", showlegend=False, margin=dict(l=0, r=0, t=60, b=0))

        st.plotly_chart(fig4, use_container_width=True)

    with row2_col3:
        top_services_global = df_lite.groupby('product_product_family')['line_item_unblended_cost'].sum().nlargest(5).reset_index()

        fig5 = px.bar(top_services_global, x='line_item_unblended_cost',
                      y='product_product_family', orientation='h',
                      title="5. Top 5 Pengeluaran Servis AWS Terboros PT Jalin Mayantara", text_auto='.2s',
                      color='line_item_unblended_cost', color_continuous_scale='Greens',
                      labels={'line_item_unblended_cost': 'Total Pengeluaran', 'product_product_family': 'Servis AWS'})

        fig5.update_traces(hovertemplate="<b>Servis AWS = %{y}</b><br>Total Pengeluaran = $%{x:,.2f}<extra></extra>")

        fig5.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Biaya (USD)",
                           yaxis_title="Servis AWS", showlegend=False, margin=dict(l=0, r=0, t=60, b=0))

        st.plotly_chart(fig5, use_container_width=True)

    with row2_col4:
        service_dist = owner_data.groupby('product_product_family')['line_item_unblended_cost'].sum().reset_index()

        total_owner_cost = service_dist['line_item_unblended_cost'].sum()

        fig6 = px.pie(service_dist, values='line_item_unblended_cost',
                      names='product_product_family', hole=0.5,
                      title=f"6. Porsi Biaya Servis AWS Divisi {selected_owner}")

        fig6.update_traces(textposition='inside', textinfo='percent', showlegend=True,
                           hovertemplate="<b>Servis AWS = %{label}</b><br>Total Pengeluaran = $%{value:,.2f}<extra></extra>")

        fig6.add_annotation(text=f"TOTAL<br><b>${total_owner_cost:,.0f}</b>",
                            x=0.5, y=0.5,
                            font=dict(size=16, color="white"), showarrow=False)

        fig6.update_layout(margin=dict(l=20, r=20, t=60, b=20),
                           legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5))

        st.plotly_chart(fig6, use_container_width=True)

# Helper functions: untuk menghindari pengulangan kode
def format_currency_list(series, max_items=3):
    """Mengubah Series biaya menjadi daftar teks untuk prompt LLM."""
    if series.empty:
        return "- Data tidak tersedia"

    lines = []
    for label, value in series.head(max_items).items():
        label_text = str(label) if pd.notna(label) else "Tidak teridentifikasi"
        lines.append(f"- {label_text}: ${value:,.2f}")

    return "\n".join(lines)


def build_deviation_summary(dataframe, group_column, top_n=3):
    """
    Menghitung perbandingan biaya aktual dan estimasi Random Forest
    pada suatu kelompok, misalnya proyek, layanan, atau operasi AWS.
    """
    summary = (
        dataframe
        .groupby(group_column)[
            ['line_item_unblended_cost', 'predicted_cost']
        ]
        .sum()
        .reset_index()
    )

    summary['selisih'] = (
        summary['line_item_unblended_cost']
        - summary['predicted_cost']
    )

    summary['selisih_abs'] = summary['selisih'].abs()

    return summary.sort_values(
        by='selisih_abs',
        ascending=False
    ).head(top_n)


def format_deviation_list(summary_df, label_column):
    """Membentuk daftar deviasi biaya untuk konteks LLM."""
    if summary_df.empty:
        return "- Data deviasi tidak tersedia"

    lines = []

    for _, row in summary_df.iterrows():
        label = str(row[label_column])
        actual = row['line_item_unblended_cost']
        predicted = row['predicted_cost']
        difference = row['selisih']

        status = (
            "lebih tinggi dari estimasi"
            if difference > 0
            else "lebih rendah dari estimasi"
        )

        lines.append(
            f"- {label}: aktual ${actual:,.2f}, "
            f"estimasi ${predicted:,.2f}, "
            f"selisih ${difference:,.2f} ({status})"
        )

    return "\n".join(lines)

def call_openrouter_model(
    model_name: str,
    system_instruction: str,
    analysis_prompt: str
) -> str:
    """
    Memanggil model generatif melalui OpenRouter dan mengembalikan respons naratif.
    """
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OR_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501",
            "X-OpenRouter-Title": (
                "Cloud Cost Optimization Prototype"
            )
        },
        json={
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ],
            "temperature": 0.2,
            "max_tokens": 1000
        },
        timeout=60
    )

    if response.status_code != 200:
        try:
            error_detail = response.json()
        except ValueError:
            error_detail = response.text

        raise requests.exceptions.RequestException(
            f"OpenRouter Error {response.status_code}: "
            f"{error_detail}"
        )

    response_json = response.json()

    final_insight = (
        response_json
        .get("choices", [{}])[0]
        .get("message", {})
        .get("content")
    )

    if not final_insight:
        raise ValueError(
            "Respons OpenRouter tidak mengandung konten insight."
        )

    return final_insight

# BAGIAN C: INTEGRASI AI
st.markdown("---")
st.header("🤖 AI Insight dan Evaluasi Efisiensi")

col_model, col_btn, col_info = st.columns([1, 1, 2])


with col_model:
    selected_model_ui = st.selectbox(
        "Pilih Model AI:",
        [
            "Gemini 2.5 Flash",
            "GPT-OSS 120B",
            "NVIDIA Nemotron 3 Nano"
        ],
        label_visibility="collapsed"
    )

    MODEL_CONFIG = {
        "Gemini 2.5 Flash": {
            "provider": "gemini",
            "model": "gemini-2.5-flash"
        },
        "GPT-OSS 120B": {
            "provider": "openrouter",
            "model": OPENROUTER_GPT_OSS_MODEL
        },
        "NVIDIA Nemotron 3 Nano": {
            "provider": "openrouter",
            "model": OPENROUTER_NEMOTRON_MODEL
        }
    }

    selected_model_config = MODEL_CONFIG[selected_model_ui]
    api_provider = selected_model_config["provider"]
    api_model_name = selected_model_config["model"]

with col_btn:
    generate_btn = st.button(
        "✨ Generate Insight",
        type="primary",
        use_container_width=True
    )

with col_info:
    st.caption(
        "Insight AI menggunakan ringkasan biaya aktual, estimasi "
        "Random Forest, deviasi biaya, serta konteks operasional divisi."
    )

st.markdown("<br>", unsafe_allow_html=True)

if generate_btn:
    # 1. Validasi ketersediaan API key
    if api_provider == "gemini" and not client:
        st.error(
            "API Key Gemini tidak ditemukan. "
            "Pastikan GEMINI_API_KEY telah diatur pada file .env."
        )
        st.stop()

    if api_provider == "openrouter" and not OR_API_KEY:
        st.error(
            "API Key OpenRouter tidak ditemukan. "
            "Pastikan OR_API_KEY telah diatur pada file .env."
        )
        st.stop()

    if df_lite.empty:
        st.warning(
            "Dataset dashboard tidak tersedia. "
            "Insight AI tidak dapat dibuat tanpa data biaya."
        )
        st.stop()

    if 'predicted_cost' not in df_lite.columns:
        st.error(
            "Kolom predicted_cost tidak ditemukan. "
            "Pastikan dataset dashboard telah memuat hasil prediksi "
            "model Random Forest."
        )
        st.stop()

    # 2. Menyiapkan data divisi terpilih
    owner_data = df_lite[
        df_lite['resource_tags_user_tech_owner'] == selected_owner
    ].copy()

    if owner_data.empty:
        st.warning(
            f"Tidak ditemukan data biaya untuk divisi {selected_owner}."
        )
        st.stop()

    total_actual_cost = owner_data['line_item_unblended_cost'].sum()
    total_predicted_cost = owner_data['predicted_cost'].sum()

    cost_difference = total_actual_cost - total_predicted_cost

    if total_predicted_cost != 0:
        deviation_percentage = (
            cost_difference / total_predicted_cost
        ) * 100
    else:
        deviation_percentage = 0.0

    # 3. Menyusun konteks biaya utama
    top_projects_actual = (
        owner_data
        .groupby('resource_tags_user_project')[
            'line_item_unblended_cost'
        ]
        .sum()
        .sort_values(ascending=False)
        .head(3)
    )

    top_services_actual = (
        owner_data
        .groupby('product_product_family')[
            'line_item_unblended_cost'
        ]
        .sum()
        .sort_values(ascending=False)
        .head(3)
    )

    top_operations_actual = (
        owner_data
        .groupby('line_item_operation')[
            'line_item_unblended_cost'
        ]
        .sum()
        .sort_values(ascending=False)
        .head(3)
    )

    project_deviation = build_deviation_summary(
        owner_data,
        'resource_tags_user_project'
    )

    service_deviation = build_deviation_summary(
        owner_data,
        'product_product_family'
    )

    top_projects_text = format_currency_list(top_projects_actual)
    top_services_text = format_currency_list(top_services_actual)
    top_operations_text = format_currency_list(top_operations_actual)

    project_deviation_text = format_deviation_list(
        project_deviation,
        'resource_tags_user_project'
    )

    service_deviation_text = format_deviation_list(
        service_deviation,
        'product_product_family'
    )

    # 4. Menyusun prompt yang terikat pada data
    system_instruction = """
Anda berperan sebagai analis Cloud FinOps yang membantu pengguna
memahami data biaya cloud AWS.

Gunakan hanya informasi yang tersedia pada konteks data.
Jangan mengarang angka, layanan, proyek, atau kondisi teknis
yang tidak disebutkan pada konteks.

Selisih antara biaya aktual dan estimasi Random Forest hanya
merupakan indikasi deviasi terhadap estimasi model, bukan bukti
pasti adanya pemborosan atau akar penyebab teknis.

Gunakan frasa seperti "indikasi", "perlu ditinjau", atau
"perlu divalidasi oleh tim teknis" ketika memberikan interpretasi.
Jangan menyatakan keputusan otomatis atau kepastian tanpa bukti.
"""

    analysis_prompt = f"""
Buat AI Insight dan Evaluasi Efisiensi Biaya Cloud AWS untuk divisi
{selected_owner} pada periode Februari 2025.

KONTEKS DIVISI
- Nama divisi: {info['full_name']}
- Deskripsi: {info['description']}
- Ruang lingkup kerja: {info['scope']}
- Produk AWS yang dikelola: {', '.join(info['products_handled'])}

RINGKASAN BIAYA
- Total biaya aktual: ${total_actual_cost:,.2f}
- Total estimasi model Random Forest: ${total_predicted_cost:,.2f}
- Selisih aktual terhadap estimasi: ${cost_difference:,.2f}
- Persentase deviasi terhadap estimasi: {deviation_percentage:,.2f}%

TIGA PROYEK DENGAN BIAYA AKTUAL TERBESAR
{top_projects_text}

TIGA LAYANAN AWS DENGAN BIAYA AKTUAL TERBESAR
{top_services_text}

TIGA OPERASI AWS DENGAN BIAYA AKTUAL TERBESAR
{top_operations_text}

TIGA PROYEK DENGAN DEVIASI TERBESAR
{project_deviation_text}

TIGA LAYANAN AWS DENGAN DEVIASI TERBESAR
{service_deviation_text}

Berikan respons dalam Bahasa Indonesia menggunakan format berikut:

## 1. Ringkasan Kondisi Biaya
Jelaskan secara singkat kondisi biaya aktual dibandingkan dengan
estimasi model Random Forest.

## 2. Indikasi Area yang Perlu Ditinjau
Jelaskan maksimal tiga area yang perlu diperhatikan berdasarkan
biaya dominan atau deviasi aktual terhadap estimasi.
Sebutkan proyek, layanan, atau operasi AWS yang relevan dari data.

## 3. Rekomendasi Awal Peluang Optimasi
Berikan tepat tiga rekomendasi dalam bullet point.
Setiap rekomendasi harus:
- terkait dengan data yang tersedia;
- menjelaskan tindakan teknis atau operasional awal;
- menyebutkan alasan berdasarkan layanan, proyek, atau operasi dominan;
- diakhiri dengan kebutuhan validasi oleh tim teknis.

Jangan menyatakan bahwa suatu komponen pasti boros atau pasti menjadi
akar masalah apabila bukti pada konteks tidak mencukupi.
"""

    full_prompt = f"{system_instruction}\n\n{analysis_prompt}"

    # 5. Pemanggilan API LLM
    with st.spinner(
            f"Menghasilkan insight menggunakan {selected_model_ui}..."
    ):
        try:
            if api_provider == "gemini":
                response = client.models.generate_content(
                    model=api_model_name,
                    contents=full_prompt
                )

                final_insight = response.text

            elif api_provider == "openrouter":
                final_insight = call_openrouter_model(
                    model_name=api_model_name,
                    system_instruction=system_instruction,
                    analysis_prompt=analysis_prompt
                )

            if not final_insight:
                st.warning(
                    "Model tidak menghasilkan narasi insight. "
                    "Silakan coba kembali."
                )
            else:
                st.subheader("Hasil AI Insight")
                st.info(final_insight)

                st.toast(
                    "Insight berhasil dihasilkan.",
                    icon="✅"
                )

        except requests.exceptions.Timeout:
            st.error(
                "Waktu pemanggilan model habis. "
                "Silakan coba kembali atau gunakan model lain."
            )

        except requests.exceptions.RequestException as error:
            st.error(
                "Terjadi kegagalan saat menghubungi OpenRouter: "
                f"{error}"
            )

        except Exception as error:
            st.error(
                "Terjadi kesalahan saat menghasilkan insight: "
                f"{error}"
            )