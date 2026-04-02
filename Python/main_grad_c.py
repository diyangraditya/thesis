import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# CONFIG — paste your actual TECH_OWNER_KNOWLEDGE dict here (or import it)
# ---------------------------------------------------------------------------
try:
    from config import TECH_OWNER_KNOWLEDGE
except ImportError:
    # Fallback dummy config so the UI still runs without config.py
    TECH_OWNER_KNOWLEDGE = {
        "INFRA": {
            "full_name": "Infrastructure Division",
            "description": "Manages cloud infrastructure and AWS resources.",
            "scope": "Cloud provisioning, networking, and cost management.",
            "products_handled": ["EC2", "S3", "RDS", "CloudFront"],
            "projects_handled": ["Project A", "Project B", "Project C"],
        }
    }

# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    try:
        df = pd.read_csv("../cleaned-datasets/dashboard_data_FULL.csv")
        df["timestamp"] = pd.to_datetime({
            "year": 2025, "month": 2,
            "day": df["day_of_month"], "hour": df["hour_of_day"],
        })
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df_lite = load_data()

# ---------------------------------------------------------------------------
# RANGESLIDER HELPER — applied to every time-series figure
# ---------------------------------------------------------------------------
def apply_rangeslider(fig, y_rangeselector: float = 1.0):
    fig.update_xaxes(
        rangeslider=dict(
            visible=True,
            thickness=0.08,
            yaxis=dict(rangemode="fixed", range=[0, 0]),
            bgcolor="#260000",
            bordercolor="#ff6b6b",
            borderwidth=2,
        ),
        rangeselector=dict(
            buttons=[
                dict(count=1,  label="1 Hari", step="day", stepmode="backward"),
                dict(count=3,  label="3 Hari", step="day", stepmode="backward"),
                dict(step="all", label="Semua"),
            ],
            y=y_rangeselector,
        ),
    )
    return fig

# ---------------------------------------------------------------------------
# DARK LAYOUT DEFAULTS
# ---------------------------------------------------------------------------
DARK_LAYOUT = dict(
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    font=dict(color="white"),
)

# ---------------------------------------------------------------------------
# MAIN DASHBOARD FUNCTION — called whenever the dropdown changes
# ---------------------------------------------------------------------------
def build_dashboard(selected_owner: str):
    info = TECH_OWNER_KNOWLEDGE[selected_owner]

    # ── Bagian A: Profil teks ───────────────────────────────────────────────
    projects = info["projects_handled"]
    projects_display = ", ".join(projects[:5])
    if len(projects) > 5:
        projects_display += f", dan {len(projects) - 5} lainnya."

    profile_md = f"""
### 🏢 Profil Divisi: {selected_owner}

| Field | Detail |
|---|---|
| **Nama Divisi** | {info['full_name']} |
| **Deskripsi** | {info['description']} |
| **Scope Pekerjaan** | {info['scope']} |
| **Produk AWS** | {', '.join(info['products_handled'])} |
| **Proyek Utama** | {projects_display} |
"""

    # ── Ringkasan Biaya ────────────────────────────────────────────────────
    if df_lite.empty:
        summary_md = "_Data tidak tersedia._"
        owner_data = pd.DataFrame()
    else:
        owner_data = df_lite[df_lite["resource_tags_user_tech_owner"] == selected_owner]
        total_cost = owner_data["line_item_unblended_cost"].sum()
        unique_days = owner_data["day_of_month"].nunique()
        avg_daily = total_cost / unique_days if unique_days > 0 else 0
        summary_md = f"""
### 💰 Ringkasan Biaya

| Metrik | Nilai |
|---|---|
| **Total Biaya (Actual)** | ${total_cost:,.2f} |
| **Rata-rata Biaya/Hari** | ${avg_daily:,.2f} |
| **Jumlah Hari Data** | {unique_days} hari |
"""

    # ── Figure 1: Actual vs Predicted ─────────────────────────────────────
    if owner_data.empty:
        fig1 = go.Figure()
    else:
        chart1 = (
            owner_data.groupby("timestamp")[["line_item_unblended_cost", "predicted_cost"]]
            .sum()
            .reset_index()
        )
        df_m = chart1.melt(
            id_vars=["timestamp"],
            value_vars=["line_item_unblended_cost", "predicted_cost"],
            var_name="Cost Type", value_name="Total Cost (USD)",
        )
        df_m["Cost Type"] = df_m["Cost Type"].replace({
            "line_item_unblended_cost": "Actual Cost (Riil)",
            "predicted_cost": "Predicted Cost (Baseline AI)",
        })
        fig1 = px.line(
            df_m, x="timestamp", y="Total Cost (USD)", color="Cost Type",
            color_discrete_map={
                "Actual Cost (Riil)": "#1f77b4",
                "Predicted Cost (Baseline AI)": "#ff7f0e",
            },
            title=f"1. Tren Total Pengeluaran Biaya: Divisi {selected_owner}",
        )
        fig1.update_traces(
            hovertemplate=(
                "<b>Cost Type = %{data.name}</b><br>"
                "Timestamp = %{x|%b %d, %Y, %H:%M}<br>"
                "Total Pengeluaran = $%{y:,.4f}<extra></extra>"
            )
        )
        fig1.update_layout(
            **DARK_LAYOUT,
            hovermode="closest",
            legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1),
            xaxis_title="Trend Biaya pada bulan Februari 2025",
            yaxis_title="Total Biaya (USD)",
            margin=dict(l=0, r=0, t=60, b=50),
        )
        fig1 = apply_rangeslider(fig1, y_rangeselector=1.0)

    # ── Figure 2: Per Product Family ──────────────────────────────────────
    if owner_data.empty:
        fig2 = go.Figure()
    else:
        product_trend = (
            owner_data.groupby(["timestamp", "product_product_family"])["line_item_unblended_cost"]
            .sum()
            .reset_index()
        )
        fig2 = px.line(
            product_trend, x="timestamp", y="line_item_unblended_cost",
            color="product_product_family",
            title=f"2. Tren Pengeluaran Biaya Tipe-tipe Servis AWS: Divisi {selected_owner}",
            labels={
                "product_product_family": "Servis AWS",
                "line_item_unblended_cost": "Total Pengeluaran",
                "timestamp": "Timestamp",
            },
        )
        fig2.update_traces(
            hovertemplate=(
                "<b>Servis AWS = %{data.name}</b><br>"
                "Total Pengeluaran = $%{y:,.4f}<extra></extra>"
            )
        )
        fig2.update_layout(
            **DARK_LAYOUT,
            hovermode="x unified",
            xaxis_title="",
            yaxis_title="Biaya (USD)",
            legend=dict(orientation="h", yanchor="top", y=-0.35, xanchor="center", x=0.5),
            margin=dict(l=0, r=0, t=60, b=0),
        )
        fig2 = apply_rangeslider(fig2, y_rangeselector=0.96)

    # ── Figure 3: Top 5 Divisi Global ─────────────────────────────────────
    if df_lite.empty:
        fig3 = go.Figure()
    else:
        top_global = (
            df_lite.groupby("resource_tags_user_tech_owner")["line_item_unblended_cost"]
            .sum().nlargest(5).reset_index()
        )
        fig3 = px.bar(
            top_global, x="line_item_unblended_cost", y="resource_tags_user_tech_owner",
            orientation="h",
            title="3. Top 5 Divisi PT Jayantara dengan Pengeluaran Terbesar",
            text_auto=".2s", color="line_item_unblended_cost",
            color_continuous_scale="Reds",
            labels={
                "line_item_unblended_cost": "Total Pengeluaran",
                "resource_tags_user_tech_owner": "Divisi",
            },
        )
        fig3.update_traces(
            hovertemplate="<b>Divisi = %{y}</b><br>Total Pengeluaran = $%{x:,.2f}<extra></extra>"
        )
        fig3.update_layout(
            **DARK_LAYOUT,
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="Total Biaya (USD)", yaxis_title="Divisi",
            showlegend=False, margin=dict(l=0, r=0, t=60, b=0),
        )

    # ── Figure 4: Top 6 Project per Divisi ───────────────────────────────
    if owner_data.empty:
        fig4 = go.Figure()
    else:
        top_projects = (
            owner_data.groupby("resource_tags_user_project")["line_item_unblended_cost"]
            .sum().nlargest(6).reset_index()
        )
        fig4 = px.bar(
            top_projects, x="resource_tags_user_project", y="line_item_unblended_cost",
            title=f"4. Top 6 Proyek Paling Boros: Divisi {selected_owner}",
            text_auto=".2s", color="line_item_unblended_cost",
            color_continuous_scale="Blues",
            labels={
                "line_item_unblended_cost": "Total Pengeluaran",
                "resource_tags_user_project": "Nama Proyek",
            },
        )
        fig4.update_traces(
            hovertemplate="<b>Project = %{x}</b><br>Total Pengeluaran = $%{y:,.2f}<extra></extra>"
        )
        fig4.update_layout(
            **DARK_LAYOUT,
            xaxis_title="Nama Proyek", yaxis_title="Total Biaya (USD)",
            showlegend=False, margin=dict(l=0, r=0, t=60, b=0),
        )

    # ── Figure 5: Top 5 Servis AWS Global ────────────────────────────────
    if df_lite.empty:
        fig5 = go.Figure()
    else:
        top_services = (
            df_lite.groupby("product_product_family")["line_item_unblended_cost"]
            .sum().nlargest(5).reset_index()
        )
        fig5 = px.bar(
            top_services, x="line_item_unblended_cost", y="product_product_family",
            orientation="h",
            title="5. Top 5 Pengeluaran Servis AWS Terboros PT Jayantara",
            text_auto=".2s", color="line_item_unblended_cost",
            color_continuous_scale="Greens",
            labels={
                "line_item_unblended_cost": "Total Pengeluaran",
                "product_product_family": "Servis AWS",
            },
        )
        fig5.update_traces(
            hovertemplate="<b>Servis AWS = %{y}</b><br>Total Pengeluaran = $%{x:,.2f}<extra></extra>"
        )
        fig5.update_layout(
            **DARK_LAYOUT,
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="Total Biaya (USD)", yaxis_title="Servis AWS",
            showlegend=False, margin=dict(l=0, r=0, t=60, b=0),
        )

    # ── Figure 6: Donut Chart Porsi Servis ───────────────────────────────
    if owner_data.empty:
        fig6 = go.Figure()
    else:
        service_dist = (
            owner_data.groupby("product_product_family")["line_item_unblended_cost"]
            .sum().reset_index()
        )
        total_owner_cost = service_dist["line_item_unblended_cost"].sum()
        fig6 = px.pie(
            service_dist, values="line_item_unblended_cost",
            names="product_product_family", hole=0.5,
            title=f"6. Porsi Biaya Servis AWS: Divisi {selected_owner}",
        )
        fig6.update_traces(
            textposition="inside", textinfo="percent", showlegend=True,
            hovertemplate="<b>Servis AWS = %{label}</b><br>Total Pengeluaran = $%{value:,.2f}<extra></extra>",
        )
        fig6.add_annotation(
            text=f"TOTAL<br><b>${total_owner_cost:,.0f}</b>",
            x=0.5, y=0.5,
            font=dict(size=16, color="white"),
            showarrow=False,
        )
        fig6.update_layout(
            **DARK_LAYOUT,
            margin=dict(l=20, r=20, t=60, b=20),
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
        )

    # ── AI Insight placeholder ────────────────────────────────────────────
    ai_md = f"""
> ⚠️ **Teks ini adalah mockup sementara** — akan digenerate secara dinamis oleh LLM API saat pengembangan dilanjutkan.

**1. Analisis Efisiensi:**
Divisi **{selected_owner}** menunjukkan pola pengeluaran yang **[Efisiensi Terjaga / Terdapat Anomali]**.
Terdapat deviasi biaya sebesar X% dibandingkan prediksi baseline pada tanggal **[Tanggal Anomali]**.

**2. Identifikasi Pemborosan (Technical Root Cause):**
Lonjakan biaya dipicu oleh tingginya aktivitas operasi **[Nama Operasi]** pada layanan **[Nama Produk]**.
Berdasarkan scope pekerjaan {selected_owner} yang fokus pada **{info['scope']}**,
aktivitas ini kemungkinan berasal dari proyek **[Nama Proyek]**.

**3. Rekomendasi Optimasi Actionable:**
- **Arsitektur:** Evaluasi arsitektur jaringan — pastikan resource yang sering berkomunikasi di AZ yang sama.
- **Rightsizing:** Pertimbangkan menghentikan layanan di luar jam kerja.
- **Tagging:** Tingkatkan kedisiplinan pelabelan untuk mempermudah alokasi biaya.
"""

    return (
        profile_md, summary_md,
        fig1, fig2,
        fig3, fig4, fig5, fig6,
        ai_md,
    )


# ---------------------------------------------------------------------------
# GRADIO UI
# ---------------------------------------------------------------------------
OWNER_LIST = list(TECH_OWNER_KNOWLEDGE.keys())

CSS = """
/* ── Global dark theme ── */
body, .gradio-container { background-color: #0e1117 !important; color: #ffffff !important; }
.gr-markdown h1, .gr-markdown h2, .gr-markdown h3 { color: #ff7f0e; }
.gr-markdown table { width: 100%; border-collapse: collapse; }
.gr-markdown table td, .gr-markdown table th {
    border: 1px solid #333; padding: 6px 12px;
}
.gr-markdown table tr:nth-child(even) { background-color: #161b22; }
.section-header {
    font-size: 1.3rem; font-weight: 700; color: #ff7f0e;
    border-bottom: 2px solid #ff7f0e; padding-bottom: 4px; margin: 12px 0 8px;
}
.ai-box {
    background: #161b22; border-left: 4px solid #ff7f0e;
    padding: 16px; border-radius: 8px;
}
"""

with gr.Blocks(css=CSS, theme=gr.themes.Base(), title="Dashboard Cloud Cost - PT Jayantara") as demo:

    # ── Header ──────────────────────────────────────────────────────────────
    gr.HTML("""
        <div style="text-align:center; padding: 20px 0 8px;">
            <h1 style="font-size:1.8rem; color:#ff7f0e;">
                ☁️ Identifikasi Peluang Optimasi Biaya Cloud AWS PT Jayantara — Februari 2025 ☁️
            </h1>
            <p style="color:#aaa; font-size:1rem;">
                Dashboard ini menampilkan profil biaya, visualisasi performa, dan insight otomatis berbasis AI
                untuk setiap divisi (Tech Owner).
            </p>
            <p style="color:#f0ad4e; font-size:0.9rem;">
                ⚠️ <b>Info:</b> Data terbatas pada periode 1–16 Februari 2025 karena keterbatasan kualitas data.
            </p>
        </div>
    """)

    # ── Filter dropdown ──────────────────────────────────────────────────────
    with gr.Row():
        with gr.Column(scale=1): gr.HTML("")          # spacer
        with gr.Column(scale=2):
            gr.HTML("<div style='text-align:center; color:#ccc; font-size:1rem; margin-bottom:4px;'>🔍 Pilih Divisi yang Ingin Dianalisis:</div>")
            owner_dd = gr.Dropdown(
                choices=OWNER_LIST, value=OWNER_LIST[0],
                label="", show_label=False, interactive=True,
            )
        with gr.Column(scale=1): gr.HTML("")          # spacer

    gr.HTML("<hr style='border-color:#333; margin: 16px 0;'>")

    # ── Bagian A ─────────────────────────────────────────────────────────────
    gr.HTML("<div class='section-header'>📋 Bagian A: Profil Divisi & Ringkasan Biaya</div>")
    with gr.Row():
        profile_out  = gr.Markdown()
        summary_out  = gr.Markdown()

    gr.HTML("<hr style='border-color:#333; margin: 16px 0;'>")

    # ── Bagian B — Baris 1 (Time-series) ────────────────────────────────────
    gr.HTML("<div class='section-header'>📈 Bagian B: Visualisasi Pengeluaran & Distribusi Biaya</div>")
    with gr.Row():
        fig1_out = gr.Plot(label="")
        fig2_out = gr.Plot(label="")

    # ── Bagian B — Baris 2 (Bar + Donut) ────────────────────────────────────
    with gr.Row():
        fig3_out = gr.Plot(label="")
        fig4_out = gr.Plot(label="")
        fig5_out = gr.Plot(label="")
        fig6_out = gr.Plot(label="")

    gr.HTML("<hr style='border-color:#333; margin: 16px 0;'>")

    # ── Bagian C — AI Insight ────────────────────────────────────────────────
    gr.HTML("<div class='section-header'>🤖 Bagian C: AI Insight & Evaluasi Efisiensi</div>")
    with gr.Row():
        with gr.Column():
            ai_out = gr.Markdown(elem_classes=["ai-box"])

    gr.HTML("<p style='text-align:center; color:#666; font-size:0.8rem; margin-top:8px;'>Narasi akan digenerate secara otomatis oleh API LLM berdasarkan data aktual.</p>")

    # ── Wire up ──────────────────────────────────────────────────────────────
    outputs = [profile_out, summary_out, fig1_out, fig2_out, fig3_out, fig4_out, fig5_out, fig6_out, ai_out]

    owner_dd.change(fn=build_dashboard, inputs=owner_dd, outputs=outputs)
    demo.load(fn=build_dashboard, inputs=owner_dd, outputs=outputs)


if __name__ == "__main__":
    demo.launch()