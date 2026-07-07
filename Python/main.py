import os
import json
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai
from dotenv import load_dotenv
from config import TECH_OWNER_KNOWLEDGE

# ============================================================
# SETUP
# ============================================================
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OR_API_KEY = os.getenv("OR_API_KEY")

OPENROUTER_GPT_OSS_MODEL = os.getenv(
    "OPENROUTER_GPT_OSS_MODEL",
    "openai/gpt-oss-120b:free"
)
OPENROUTER_NEMOTRON_MODEL = os.getenv(
    "OPENROUTER_NEMOTRON_MODEL",
    "nvidia/nemotron-3-nano-30b-a3b:free"
)
SUS_EVALUATION_MODE = os.getenv("SUS_EVALUATION_MODE", "false").lower() == "true"

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

st.set_page_config(
    page_title="Dashboard Cloud Cost - PT Jalin Mayantara",
    layout="wide"
)

# ============================================================
# DATA LOADING
# ============================================================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("../cleaned-datasets/dashboard_data_FULL_FIXED1.csv")

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        else:
            df["timestamp"] = pd.to_datetime({
                "year": 2025,
                "month": 2,
                "day": df["day_of_month"],
                "hour": df["hour_of_day"]
            })

        if "is_test_period" not in df.columns:
            df["is_test_period"] = df["timestamp"] >= pd.Timestamp("2025-02-14 00:00:00")

        if "predicted_cost" not in df.columns:
            df["predicted_cost"] = pd.NA

        if "prediction_scope" not in df.columns:
            df["prediction_scope"] = df["is_test_period"].map(
                lambda x: "Out-of-time hold-out baseline" if x else "Tidak ditampilkan - periode pelatihan"
            )

        if "deviation_cost" not in df.columns:
            df["deviation_cost"] = pd.NA

        if "deviation_pct" not in df.columns:
            df["deviation_pct"] = pd.NA

        return df
    except FileNotFoundError:
        st.error("Dataset dashboard_data_FULL_FIXED1.csv tidak ditemukan.")
        return pd.DataFrame()


df_lite = load_data()

# ============================================================
# HELPERS
# ============================================================
def format_currency_list(series, max_items=3):
    if series.empty:
        return "- Data tidak tersedia"
    lines = []
    for label, value in series.head(max_items).items():
        label_text = str(label) if pd.notna(label) else "Tidak teridentifikasi"
        lines.append(f"- {label_text}: ${value:,.2f}")
    return "\n".join(lines)


def build_deviation_summary(dataframe, group_column, top_n=3):
    base = dataframe[dataframe["is_test_period"]].copy()
    if base.empty:
        return pd.DataFrame()

    summary = (
        base.groupby(group_column)[["line_item_unblended_cost", "predicted_cost"]]
        .sum()
        .reset_index()
    )
    summary["selisih"] = summary["line_item_unblended_cost"] - summary["predicted_cost"]
    summary["selisih_abs"] = summary["selisih"].abs()
    return summary.sort_values("selisih_abs", ascending=False).head(top_n)


def format_deviation_list(summary_df, label_column):
    if summary_df.empty:
        return "- Data deviasi tidak tersedia"

    lines = []
    for _, row in summary_df.iterrows():
        label = str(row[label_column]) if pd.notna(row[label_column]) else "Tidak teridentifikasi"
        actual = row["line_item_unblended_cost"]
        predicted = row["predicted_cost"]
        difference = row["selisih"]
        status = "lebih tinggi dari estimasi" if difference > 0 else "lebih rendah dari estimasi"
        lines.append(
            f"- {label}: aktual ${actual:,.2f}, estimasi ${predicted:,.2f}, "
            f"selisih ${difference:,.2f} ({status})"
        )
    return "\n".join(lines)


def build_priority_points(owner_data):
    priorities = []
    if owner_data.empty:
        return priorities

    top_project = (
        owner_data.groupby("resource_tags_user_project")["line_item_unblended_cost"]
        .sum()
        .sort_values(ascending=False)
        .head(1)
    )
    top_service = (
        owner_data.groupby("product_product_family")["line_item_unblended_cost"]
        .sum()
        .sort_values(ascending=False)
        .head(1)
    )
    top_operation = (
        owner_data.groupby("line_item_operation")["line_item_unblended_cost"]
        .sum()
        .sort_values(ascending=False)
        .head(1)
    )

    if not top_project.empty:
        priorities.append(
            f"Proyek prioritas: **{top_project.index[0]}** dengan total biaya sekitar **${top_project.iloc[0]:,.2f}**."
        )
    if not top_service.empty:
        priorities.append(
            f"Layanan AWS dominan: **{top_service.index[0]}** dengan kontribusi biaya sekitar **${top_service.iloc[0]:,.2f}**."
        )
    if not top_operation.empty:
        priorities.append(
            f"Operasi yang paling perlu ditinjau: **{top_operation.index[0]}** dengan total biaya sekitar **${top_operation.iloc[0]:,.2f}**."
        )

    return priorities


def build_simple_fallback(selected_owner, info, context):
    lines = [
        f"**Ringkasan Singkat untuk Divisi {selected_owner}**",
        "",
        f"1. Total biaya aktual divisi ini selama periode data adalah **${context['total_actual_cost']:,.2f}**.",
        f"2. Pada periode pengujian 14-16 Februari 2025, estimasi Random Forest adalah **${context['total_predicted_cost']:,.2f}** dengan selisih terhadap biaya aktual sebesar **${context['cost_difference']:,.2f}**.",
        f"3. Area biaya yang paling besar terlihat pada proyek **{context['top_project_name']}**, layanan **{context['top_service_name']}**, dan operasi **{context['top_operation_name']}**.",
        "4. Peluang optimasi awal dapat difokuskan pada komponen biaya terbesar terlebih dahulu, kemudian memvalidasi apakah biaya tersebut memang sesuai kebutuhan operasional divisi.",
        "5. Hasil ini berfungsi sebagai pendukung keputusan awal dan masih perlu ditinjau lebih lanjut oleh tim terkait."
    ]
    return "\n".join(lines)


def build_technical_fallback(selected_owner, info, context):
    lines = [
        f"**Analisis Teknis untuk Divisi {selected_owner}**",
        "",
        "**1. Ringkasan Kondisi Biaya**",
        f"Total biaya aktual pada periode data tercatat sebesar **${context['total_actual_cost']:,.2f}**. Pada periode hold-out 14-16 Februari 2025, model Random Forest menghasilkan estimasi total biaya sebesar **${context['total_predicted_cost']:,.2f}**, dengan selisih **${context['cost_difference']:,.2f}** terhadap biaya aktual.",
        "",
        "**2. Indikasi Area yang Perlu Ditinjau**",
        f"- Proyek dengan biaya terbesar adalah **{context['top_project_name']}** sebesar **${context['top_project_value']:,.2f}**.",
        f"- Layanan AWS dengan biaya terbesar adalah **{context['top_service_name']}** sebesar **${context['top_service_value']:,.2f}**.",
        f"- Operasi AWS yang paling dominan adalah **{context['top_operation_name']}** sebesar **${context['top_operation_value']:,.2f}**.",
        "- Deviasi antara biaya aktual dan estimasi sebaiknya diperlakukan sebagai indikasi awal, bukan bukti langsung adanya pemborosan.",
        "",
        "**3. Rekomendasi Awal**",
        f"- Tinjau konfigurasi dan pemakaian komponen yang terkait dengan layanan **{context['top_service_name']}** untuk memastikan ukuran resource, volume trafik, atau aktivitas operasionalnya sudah sesuai kebutuhan.",
        f"- Lakukan pemeriksaan pada proyek **{context['top_project_name']}** guna memastikan tidak ada resource aktif yang tidak lagi memberikan nilai operasional.",
        f"- Validasi lebih lanjut operasi **{context['top_operation_name']}** bersama tim teknis untuk memastikan pola penggunaan dan biaya yang muncul memang masih relevan.",
    ]
    return "\n".join(lines)


def call_openrouter(model_name, system_instruction, user_prompt):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OR_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501",
            "X-OpenRouter-Title": "Cloud Cost Optimization Prototype"
        },
        json={
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1200
        },
        timeout=60
    )
    response.raise_for_status()
    response_json = response.json()
    return (
        response_json
        .get("choices", [{}])[0]
        .get("message", {})
        .get("content")
    )


def call_llm(selected_model_label, provider, model_name, system_instruction, user_prompt):
    if provider == "gemini":
        if not client:
            raise RuntimeError("API Key Gemini tidak tersedia.")
        response = client.models.generate_content(
            model=model_name,
            contents=f"{system_instruction}\n\n{user_prompt}"
        )
        return response.text

    if provider == "openrouter":
        if not OR_API_KEY:
            raise RuntimeError("API Key OpenRouter tidak tersedia.")
        return call_openrouter(model_name, system_instruction, user_prompt)

    raise RuntimeError(f"Provider model tidak dikenali: {selected_model_label}")


# ============================================================
# UI HEADER
# ============================================================
st.markdown(
    "<h1 style='text-align: center;'>☁️ Identifikasi Peluang Optimasi Biaya Cloud AWS PT Jalin Mayantara pada Februari 2025 ☁️</h1>",
    unsafe_allow_html=True
)

st.markdown(
    "<p style='text-align: center; font-size: 18px; color: gray;'>Dashboard ini menampilkan profil biaya, visualisasi pengeluaran, dan insight AI untuk membantu identifikasi peluang optimasi biaya cloud AWS.</p>",
    unsafe_allow_html=True
)

st.markdown(
    "<p style='text-align: center; font-size: 17px; color: gray;'>⚠️ <b>Catatan</b>: Data yang digunakan terbatas pada periode 1-16 Februari 2025. Perbandingan biaya aktual dan estimasi Random Forest hanya ditampilkan pada periode pengujian 14-16 Februari 2025.</p>",
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)

col_empty1, col_filter, col_empty2 = st.columns([1, 2, 1])
with col_filter:
    st.markdown("<h4 style='text-align: center;'>Pilih Divisi yang Ingin Dianalisis</h4>", unsafe_allow_html=True)
    selected_owner = st.selectbox(
        "Pilih Divisi (Tech Owner):",
        list(TECH_OWNER_KNOWLEDGE.keys()),
        label_visibility="collapsed"
    )

if df_lite.empty:
    st.stop()

info = TECH_OWNER_KNOWLEDGE[selected_owner]
owner_data = df_lite[df_lite["resource_tags_user_tech_owner"] == selected_owner].copy()
test_owner_data = owner_data[owner_data["is_test_period"]].copy()

# ============================================================
# BAGIAN A
# ============================================================
st.markdown("---")
st.header(f"Bagian A: Profil {selected_owner}")

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
    total_actual_cost = owner_data["line_item_unblended_cost"].sum()
    total_predicted_cost = test_owner_data["predicted_cost"].sum(skipna=True)
    total_actual_test_cost = test_owner_data["line_item_unblended_cost"].sum()
    cost_difference = total_actual_test_cost - total_predicted_cost
    unique_days = owner_data["day_of_month"].nunique()
    avg_daily_cost = total_actual_cost / unique_days if unique_days > 0 else 0

    st.metric("Total Biaya Aktual (1-16 Feb)", f"${total_actual_cost:,.2f}")
    st.metric("Estimasi Random Forest (14-16 Feb)", f"${total_predicted_cost:,.2f}")
    st.metric(
        "Selisih Aktual vs Estimasi (14-16 Feb)",
        f"${cost_difference:,.2f}",
        help="Selisih dihitung hanya pada periode pengujian 14-16 Februari 2025."
    )
    st.metric("Rata-rata Biaya per Hari", f"${avg_daily_cost:,.2f}")

# ============================================================
# BAGIAN B VISUALISASI
# ============================================================
st.markdown("---")
st.header("Bagian B: Visualisasi Pengeluaran dan Distribusi Biaya")

# Tingkat 1
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    chart_actual = (
        owner_data.groupby("timestamp")["line_item_unblended_cost"]
        .sum()
        .reset_index()
    )

    fig1 = px.line(
        chart_actual,
        x="timestamp",
        y="line_item_unblended_cost",
        title=f"1. Tren Biaya Aktual Divisi {selected_owner}",
        labels={
            "timestamp": "Timestamp",
            "line_item_unblended_cost": "Total Biaya (USD)"
        }
    )
    fig1.update_traces(
        hovertemplate="<b>Biaya Aktual</b><br>Timestamp = %{x|%b %d, %Y, %H:%M}<br>Total Biaya = $%{y:,.4f}<extra></extra>"
    )
    fig1.update_layout(
        hovermode="closest",
        xaxis_title="Tren biaya pada Februari 2025",
        yaxis_title="Total Biaya (USD)",
        margin=dict(l=0, r=0, t=50, b=50)
    )
    fig1.update_xaxes(
        rangeslider=dict(visible=True, thickness=0.06, bgcolor="#260000", bordercolor="white", borderwidth=0),
        rangeselector=dict(buttons=[
            dict(count=1, label="1 Hari", step="day", stepmode="backward"),
            dict(count=3, label="3 Hari", step="day", stepmode="backward"),
            dict(step="all", label="Semua")
        ], y=1)
    )
    st.plotly_chart(fig1, use_container_width=True)

with row1_col2:
    comparison_data = test_owner_data.groupby("timestamp")[["line_item_unblended_cost", "predicted_cost"]].sum().reset_index()
    comparison_melted = comparison_data.melt(
        id_vars=["timestamp"],
        value_vars=["line_item_unblended_cost", "predicted_cost"],
        var_name="Cost Type",
        value_name="Total Cost (USD)"
    )
    comparison_melted["Cost Type"] = comparison_melted["Cost Type"].replace({
        "line_item_unblended_cost": "Biaya Aktual",
        "predicted_cost": "Estimasi Biaya Random Forest"
    })

    fig2 = px.line(
        comparison_melted,
        x="timestamp",
        y="Total Cost (USD)",
        color="Cost Type",
        color_discrete_map={
            "Biaya Aktual": "#1f77b4",
            "Estimasi Biaya Random Forest": "#ff7f0e"
        },
        title=f"2. Perbandingan Biaya Aktual dan Estimasi Random Forest Divisi {selected_owner} (14-16 Februari 2025)"
    )
    fig2.update_traces(
        hovertemplate="<b>%{data.name}</b><br>Timestamp = %{x|%b %d, %Y, %H:%M}<br>Total Biaya = $%{y:,.4f}<extra></extra>"
    )
    fig2.update_layout(
        hovermode="x unified",
        xaxis_title="Periode pengujian 14-16 Februari 2025",
        yaxis_title="Total Biaya (USD)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.1,
            xanchor="right",
            x=1
        ),
        margin=dict(l=0, r=0, t=50, b=50)
    )
    fig2.update_xaxes(
        rangeslider=dict(visible=True, thickness=0.06, bgcolor="#260000", bordercolor="white", borderwidth=0),
        rangeselector=dict(buttons=[
            dict(count=1, label="1 Hari", step="day", stepmode="backward"),
            dict(count=2, label="2 Hari", step="day", stepmode="backward"),
            dict(step="all", label="Semua")
        ], y=1)
    )
    st.plotly_chart(fig2, use_container_width=True)

# Tingkat 2
product_trend = (
    owner_data.groupby(["timestamp", "product_product_family"])["line_item_unblended_cost"]
    .sum()
    .reset_index()
)
fig3 = px.line(
    product_trend,
    x="timestamp",
    y="line_item_unblended_cost",
    color="product_product_family",
    title=f"3. Tren Pengeluaran Biaya Tipe-tipe Servis AWS: Divisi {selected_owner}",
    labels={
        "product_product_family": "Servis AWS",
        "line_item_unblended_cost": "Total Pengeluaran",
        "timestamp": "Timestamp"
    }
)
fig3.update_traces(
    hovertemplate="<b>Servis AWS = %{data.name}</b><br>Timestamp = %{x|%b %d, %Y, %H:%M}<br>Total Pengeluaran = $%{y:,.4f}<extra></extra>"
)
fig3.update_xaxes(
    rangeslider=dict(visible=True, thickness=0.06, bgcolor="#260000", bordercolor="white", borderwidth=0),
    rangeselector=dict(buttons=[
        dict(count=1, label="1 Hari", step="day", stepmode="backward"),
        dict(count=3, label="3 Hari", step="day", stepmode="backward"),
        dict(step="all", label="Semua")
    ], y=0.96)
)
fig3.update_layout(
    hovermode="x unified",
    xaxis_title="",
    yaxis_title="Biaya (USD)",
    legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5),
    margin=dict(l=0, r=0, t=60, b=0)
)
st.plotly_chart(fig3, use_container_width=True)

# Tingkat 3
st.markdown("<br>", unsafe_allow_html=True)
row3_col1, row3_col2, row3_col3, row3_col4 = st.columns(4)

with row3_col1:
    top_global = (
        df_lite.groupby("resource_tags_user_tech_owner")["line_item_unblended_cost"]
        .sum().nlargest(5).reset_index()
    )
    fig4 = px.bar(
        top_global,
        x="line_item_unblended_cost",
        y="resource_tags_user_tech_owner",
        orientation="h",
        title="4. Top 5 Divisi PT Jalin Mayantara dengan Pengeluaran Terbesar",
        text_auto='.2s',
        color="line_item_unblended_cost",
        color_continuous_scale='Reds',
        labels={
            "line_item_unblended_cost": "Total Pengeluaran",
            "resource_tags_user_tech_owner": "Divisi"
        }
    )
    fig4.update_traces(hovertemplate="<b>Divisi = %{y}</b><br>Total Pengeluaran = $%{x:,.2f}<extra></extra>")
    fig4.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title="Total Biaya (USD)",
        yaxis_title="Divisi",
        showlegend=False,
        margin=dict(l=0, r=0, t=60, b=0)
    )
    st.plotly_chart(fig4, use_container_width=True)

with row3_col2:
    top_projects = (
        owner_data.groupby("resource_tags_user_project")["line_item_unblended_cost"]
        .sum().nlargest(6).reset_index()
    )
    fig5 = px.bar(
        top_projects,
        x="resource_tags_user_project",
        y="line_item_unblended_cost",
        title=f"5. Top 6 Proyek Paling Besar Biayanya dari Divisi {selected_owner}",
        text_auto='.2s',
        color="line_item_unblended_cost",
        color_continuous_scale='Blues',
        labels={
            "line_item_unblended_cost": "Total Pengeluaran",
            "resource_tags_user_project": "Nama Proyek"
        }
    )
    fig5.update_traces(hovertemplate="<b>Project = %{x}</b><br>Total Pengeluaran = $%{y:,.2f}<extra></extra>")
    fig5.update_layout(
        xaxis_title="Nama Proyek",
        yaxis_title="Total Biaya (USD)",
        showlegend=False,
        margin=dict(l=0, r=0, t=60, b=0)
    )
    st.plotly_chart(fig5, use_container_width=True)

with row3_col3:
    top_services_global = (
        df_lite.groupby("product_product_family")["line_item_unblended_cost"]
        .sum().nlargest(5).reset_index()
    )
    fig6 = px.bar(
        top_services_global,
        x="line_item_unblended_cost",
        y="product_product_family",
        orientation="h",
        title="6. Top 5 Pengeluaran Servis AWS Terbesar PT Jalin Mayantara",
        text_auto='.2s',
        color="line_item_unblended_cost",
        color_continuous_scale='Greens',
        labels={
            "line_item_unblended_cost": "Total Pengeluaran",
            "product_product_family": "Servis AWS"
        }
    )
    fig6.update_traces(hovertemplate="<b>Servis AWS = %{y}</b><br>Total Pengeluaran = $%{x:,.2f}<extra></extra>")
    fig6.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title="Total Biaya (USD)",
        yaxis_title="Servis AWS",
        showlegend=False,
        margin=dict(l=0, r=0, t=60, b=0)
    )
    st.plotly_chart(fig6, use_container_width=True)

with row3_col4:
    service_dist = owner_data.groupby("product_product_family")["line_item_unblended_cost"].sum().reset_index()
    total_owner_cost = service_dist["line_item_unblended_cost"].sum()
    fig7 = px.pie(
        service_dist,
        values="line_item_unblended_cost",
        names="product_product_family",
        hole=0.5,
        title=f"7. Porsi Biaya Servis AWS Divisi {selected_owner}"
    )
    fig7.update_traces(
        textposition='inside',
        textinfo='percent',
        showlegend=True,
        hovertemplate="<b>Servis AWS = %{label}</b><br>Total Pengeluaran = $%{value:,.2f}<extra></extra>"
    )
    fig7.add_annotation(
        text=f"TOTAL<br><b>${total_owner_cost:,.0f}</b>",
        x=0.5,
        y=0.5,
        font=dict(size=16, color="white"),
        showarrow=False
    )
    fig7.update_layout(
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig7, use_container_width=True)

# ============================================================
# BAGIAN C AI INSIGHT
# ============================================================
st.markdown("---")
st.header("Bagian C: AI Insight dan Identifikasi Peluang Optimasi")

with st.expander("Cara membaca hasil", expanded=False):
    st.markdown(
        """
        1. **Lihat visualisasi terlebih dahulu** untuk mengenali proyek, layanan AWS, dan operasi yang paling dominan terhadap biaya.  
        2. **Gunakan mode Non-Teknis** jika ingin memperoleh rangkuman singkat yang sederhana dan mudah dipahami.  
        3. **Gunakan mode Teknis Mendalam** jika ingin mengetahui dugaan alasan teknis di balik biaya yang muncul serta rekomendasi awal yang lebih rinci.  
        4. **Selisih biaya aktual dan estimasi Random Forest** pada periode 14-16 Februari 2025 dapat digunakan sebagai indikasi awal area yang perlu ditinjau lebih lanjut.  
        5. Insight AI pada dashboard ini berfungsi sebagai **pendukung keputusan awal**, sehingga hasil akhirnya tetap perlu divalidasi oleh pihak terkait.
        """
    )

priority_points = build_priority_points(owner_data)
if priority_points:
    st.subheader("Prioritas Peninjauan Peluang Optimasi")
    for item in priority_points:
        st.markdown(f"- {item}")

col_model, col_mode, col_button = st.columns([1, 1, 1])

if SUS_EVALUATION_MODE:
    selected_model_ui = "Gemini 2.5 Flash"
    st.caption("Mode evaluasi SUS aktif: model dikunci ke Gemini 2.5 Flash agar pengalaman responden konsisten.")
else:
    with col_model:
        selected_model_ui = st.selectbox(
            "Pilih Model AI:",
            [
                "Gemini 2.5 Flash",
                "GPT-OSS 120B",
                "NVIDIA Nemotron 3 Nano"
            ]
        )

with col_mode:
    selected_output_mode = st.radio(
        "Pilih Jenis Insight:",
        ["Ringkas dan Mudah Dipahami", "Analisis Teknis Mendalam"],
        horizontal=False
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

with col_button:
    st.markdown("<br>", unsafe_allow_html=True)
    generate_btn = st.button("✨ Generate Insight", type="primary", use_container_width=True)

if generate_btn:
    if owner_data.empty:
        st.warning(f"Tidak ditemukan data biaya untuk divisi {selected_owner}.")
        st.stop()

    total_actual_cost = owner_data["line_item_unblended_cost"].sum()
    total_predicted_cost = test_owner_data["predicted_cost"].sum(skipna=True)
    total_actual_test_cost = test_owner_data["line_item_unblended_cost"].sum()
    cost_difference = total_actual_test_cost - total_predicted_cost
    deviation_percentage = (cost_difference / total_predicted_cost * 100) if total_predicted_cost not in [0, None] and pd.notna(total_predicted_cost) and total_predicted_cost != 0 else 0.0

    top_projects_actual = (
        owner_data.groupby("resource_tags_user_project")["line_item_unblended_cost"]
        .sum().sort_values(ascending=False).head(3)
    )
    top_services_actual = (
        owner_data.groupby("product_product_family")["line_item_unblended_cost"]
        .sum().sort_values(ascending=False).head(3)
    )
    top_operations_actual = (
        owner_data.groupby("line_item_operation")["line_item_unblended_cost"]
        .sum().sort_values(ascending=False).head(3)
    )

    project_deviation = build_deviation_summary(owner_data, "resource_tags_user_project")
    service_deviation = build_deviation_summary(owner_data, "product_product_family")

    top_projects_text = format_currency_list(top_projects_actual)
    top_services_text = format_currency_list(top_services_actual)
    top_operations_text = format_currency_list(top_operations_actual)
    project_deviation_text = format_deviation_list(project_deviation, "resource_tags_user_project")
    service_deviation_text = format_deviation_list(service_deviation, "product_product_family")

    context = {
        "total_actual_cost": total_actual_cost,
        "total_predicted_cost": total_predicted_cost,
        "cost_difference": cost_difference,
        "top_project_name": top_projects_actual.index[0] if not top_projects_actual.empty else "Tidak tersedia",
        "top_project_value": float(top_projects_actual.iloc[0]) if not top_projects_actual.empty else 0.0,
        "top_service_name": top_services_actual.index[0] if not top_services_actual.empty else "Tidak tersedia",
        "top_service_value": float(top_services_actual.iloc[0]) if not top_services_actual.empty else 0.0,
        "top_operation_name": top_operations_actual.index[0] if not top_operations_actual.empty else "Tidak tersedia",
        "top_operation_value": float(top_operations_actual.iloc[0]) if not top_operations_actual.empty else 0.0,
    }

    system_instruction = """
Anda berperan sebagai analis Cloud FinOps yang membantu pengguna memahami data biaya cloud AWS.
Gunakan hanya informasi yang tersedia pada konteks data.
Jangan mengarang angka, layanan, proyek, atau kondisi teknis yang tidak disebutkan pada konteks.
Selisih antara biaya aktual dan estimasi Random Forest hanya merupakan indikasi deviasi terhadap estimasi model, bukan bukti pasti adanya pemborosan atau akar penyebab teknis.
Gunakan frasa seperti "indikasi", "perlu ditinjau", atau "perlu divalidasi" bila bukti tidak cukup kuat.
""".strip()

    if selected_output_mode == "Ringkas dan Mudah Dipahami":
        user_prompt = f"""
Buat insight sederhana, ringkas, dan mudah dipahami untuk pengguna non-teknis.

KONTEKS DIVISI
- Nama divisi: {info['full_name']}
- Deskripsi: {info['description']}
- Ruang lingkup kerja: {info['scope']}
- Produk AWS yang dikelola: {', '.join(info['products_handled'])}

RINGKASAN BIAYA
- Total biaya aktual periode 1-16 Februari 2025: ${total_actual_cost:,.2f}
- Total biaya aktual periode pengujian 14-16 Februari 2025: ${total_actual_test_cost:,.2f}
- Total estimasi Random Forest periode pengujian 14-16 Februari 2025: ${total_predicted_cost:,.2f}
- Selisih aktual terhadap estimasi pada periode pengujian: ${cost_difference:,.2f}

TIGA PROYEK DENGAN BIAYA TERBESAR
{top_projects_text}

TIGA LAYANAN AWS DENGAN BIAYA TERBESAR
{top_services_text}

TIGA OPERASI AWS DENGAN BIAYA TERBESAR
{top_operations_text}

Berikan respons dalam Bahasa Indonesia dengan format berikut:

## 1. Ringkasan Kondisi Biaya
Jelaskan kondisi biaya secara singkat dan mudah dipahami.

## 2. Area yang Perlu Diperhatikan
Sebutkan maksimal tiga area yang paling layak ditinjau terlebih dahulu.

## 3. Saran Tindak Lanjut Awal
Berikan tepat tiga bullet points yang sederhana dan tidak terlalu teknis.

Gunakan bahasa yang singkat, jelas, dan ramah bagi pengguna non-teknis.
""".strip()
        fallback_text = build_simple_fallback(selected_owner, info, context)
    else:
        user_prompt = f"""
Buat analisis yang lebih teknis dan lebih rinci mengenai peluang optimasi biaya cloud AWS.

KONTEKS DIVISI
- Nama divisi: {info['full_name']}
- Deskripsi: {info['description']}
- Ruang lingkup kerja: {info['scope']}
- Produk AWS yang dikelola: {', '.join(info['products_handled'])}
- Operasi AWS yang umum digunakan: {', '.join(info['used_operation'][:12])}

RINGKASAN BIAYA
- Total biaya aktual periode 1-16 Februari 2025: ${total_actual_cost:,.2f}
- Total biaya aktual periode pengujian 14-16 Februari 2025: ${total_actual_test_cost:,.2f}
- Total estimasi Random Forest periode pengujian 14-16 Februari 2025: ${total_predicted_cost:,.2f}
- Selisih aktual terhadap estimasi pada periode pengujian: ${cost_difference:,.2f}
- Persentase deviasi terhadap estimasi: {deviation_percentage:,.2f}%

TIGA PROYEK DENGAN BIAYA TERBESAR
{top_projects_text}

TIGA LAYANAN AWS DENGAN BIAYA TERBESAR
{top_services_text}

TIGA OPERASI AWS DENGAN BIAYA TERBESAR
{top_operations_text}

TIGA PROYEK DENGAN DEVIASI TERBESAR
{project_deviation_text}

TIGA LAYANAN AWS DENGAN DEVIASI TERBESAR
{service_deviation_text}

Berikan respons dalam Bahasa Indonesia dengan format berikut:

## 1. Ringkasan Kondisi Biaya
Jelaskan secara singkat kondisi biaya aktual dibandingkan estimasi model Random Forest.

## 2. Indikasi Penyebab Teknis yang Perlu Ditinjau
Jelaskan maksimal tiga indikasi penyebab teknis secara hati-hati berdasarkan layanan, operasi, atau proyek yang dominan.

## 3. Rekomendasi Awal Peluang Optimasi
Berikan tepat tiga bullet points yang lebih rinci dan actionable.
Setiap rekomendasi harus menjelaskan alasan teknis singkat dan diakhiri dengan kebutuhan validasi oleh tim teknis.

Jangan menyatakan kepastian apabila konteks data belum cukup membuktikan penyebabnya.
""".strip()
        fallback_text = build_technical_fallback(selected_owner, info, context)

    final_insight = ""
    api_error_message = None

    try:
        with st.spinner(f"Menghasilkan insight menggunakan {selected_model_ui}..."):
            final_insight = call_llm(
                selected_model_ui,
                api_provider,
                api_model_name,
                system_instruction,
                user_prompt
            )
    except Exception as error:
        api_error_message = str(error)
        final_insight = fallback_text

    st.subheader("Hasil AI Insight")
    if api_error_message:
        st.warning(
            "Model AI eksternal sedang tidak tersedia atau gagal merespons. "
            "Sistem menampilkan fallback insight berbasis data agar analisis tetap dapat dilanjutkan."
        )
        st.caption(f"Detail error: {api_error_message}")

    st.info(final_insight)
