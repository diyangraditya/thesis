import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import TECH_OWNER_KNOWLEDGE
# from dotenv import load_dotenv # Tidak wajib untuk UI mockup

# --- FUNGSI LOAD DATA (Jalan sekali di awal) ---
try:
    df_lite = pd.read_csv("../cleaned-datasets/dashboard_data_FULL.csv")
    df_lite['timestamp'] = pd.to_datetime({
        'year': 2025, 'month': 2,
        'day': df_lite['day_of_month'], 'hour': df_lite['hour_of_day']
    })
except FileNotFoundError:
    print("WARNING: Data tidak ditemukan. Menyiapkan DataFrame kosong.")
    df_lite = pd.DataFrame()

# --- FUNGSI UPDATE DINAMIS (Dijalankan setiap Dropdown berubah) ---
def update_dashboard(selected_owner):
    info = TECH_OWNER_KNOWLEDGE[selected_owner]

    # 1. Update Bagian A (Teks Profil & Metrik)
    projects_display = info['projects_handled'][:5]
    if len(info['projects_handled']) > 5:
        proj_text = f"{', '.join(projects_display)}, dan {len(info['projects_handled'])-5} lainnya."
    else:
        proj_text = f"{', '.join(projects_display)}"

    profil_text = f"""**Nama Divisi:** {info['full_name']}
**Deskripsi Pekerjaan:** {info['description']}
**Scope Pekerjaan:** {info['scope']}
**Produk AWS yang Dikelola:** {', '.join(info['products_handled'])}
**Proyek Utama:** {proj_text}"""

    if not df_lite.empty:
        owner_data = df_lite[df_lite['resource_tags_user_tech_owner'] == selected_owner]
        total_cost = owner_data['line_item_unblended_cost'].sum()
        unique_days = owner_data['day_of_month'].nunique()
        avg_daily_cost = total_cost / unique_days if unique_days > 0 else 0

        metric_text = f"""<div style="padding: 20px; background-color: #f3f4f6; border-radius: 10px; color: black;">
            <h3 style="margin-top:0;">Ringkasan Biaya</h3>
            <p style="font-size: 16px; margin-bottom: 5px;">Total Biaya (Actual): <b>${total_cost:,.2f}</b></p>
            <p style="font-size: 16px; margin-bottom: 0;">Rata-rata Biaya per Hari: <b>${avg_daily_cost:,.2f}</b></p>
        </div>"""
    else:
        owner_data = pd.DataFrame()
        metric_text = "Data tidak tersedia."

    # 2. Update Bagian B (Grafik)
    if not df_lite.empty:
        # FIG 1: Line Chart Actual vs Predicted
        chart1_data = owner_data.groupby('timestamp')[['line_item_unblended_cost', 'predicted_cost']].sum().reset_index()
        df_melted = chart1_data.melt(id_vars=['timestamp'], value_vars=['line_item_unblended_cost', 'predicted_cost'], var_name='Cost Type', value_name='Total Cost (USD)')
        df_melted['Cost Type'] = df_melted['Cost Type'].replace({'line_item_unblended_cost': 'Actual Cost (Riil)', 'predicted_cost': 'Predicted Cost (Baseline AI)'})
        fig1 = px.line(df_melted, x='timestamp', y='Total Cost (USD)', color='Cost Type', color_discrete_map={"Actual Cost (Riil)": "#1f77b4", "Predicted Cost (Baseline AI)": "#ff7f0e"}, title=f"1. Tren Total Pengeluaran Biaya: Divisi {selected_owner}")
        fig1.update_traces(hovertemplate="<b>Cost Type = %{data.name}</b><br>Timestamp = %{x|%b %d, %Y, %H:%M}<br>Total Pengeluaran = $%{y:,.4f}<extra></extra>")
        fig1.update_layout(hovermode="closest", legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1), xaxis_title="Trend Biaya pada bulan Februari 2025", yaxis_title="Total Biaya (USD)", margin=dict(l=0, r=0, t=40, b=50))
        fig1.update_xaxes(rangeslider=dict(visible=True, thickness=0.06, yaxis=dict(rangemode="fixed", range=[0, 0]), bgcolor="#260000", bordercolor="white", borderwidth=0), rangeselector=dict(buttons=list([dict(count=1, label="1 Hari", step="day", stepmode="backward"), dict(count=3, label="3 Hari", step="day", stepmode="backward"), dict(step="all", label="Semua")]), y=1))

        # FIG 2: Line Chart Tren per Product Family
        product_trend = owner_data.groupby(['timestamp', 'product_product_family'])['line_item_unblended_cost'].sum().reset_index()
        fig2 = px.line(product_trend, x='timestamp', y='line_item_unblended_cost', color='product_product_family', title=f"2. Tren Pengeluaran Biaya Tipe-tipe Servis AWS: Divisi {selected_owner}", labels={'product_product_family': 'Servis AWS', 'line_item_unblended_cost': 'Total Pengeluaran', 'timestamp': 'Timestamp'})
        fig2.update_traces(hovertemplate="<b>Servis AWS = %{data.name}</b><br>Total Pengeluaran = $%{y:,.4f}<extra></extra>")
        fig2.update_xaxes(rangeslider=dict(visible=True, thickness=0.06, bgcolor='#260000', bordercolor="white", borderwidth=0), rangeselector=dict(buttons=list([dict(count=1, label="1 Hari", step="day", stepmode="backward"), dict(count=3, label="3 Hari", step="day", stepmode="backward"), dict(step="all", label="Semua")]), y=0.96))
        fig2.update_layout(hovermode="x unified", xaxis_title="", yaxis_title="Biaya (USD)", legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5), margin=dict(l=0, r=0, t=60, b=0))

        # FIG 3: Bar Chart Global Owner
        top_global = df_lite.groupby('resource_tags_user_tech_owner')['line_item_unblended_cost'].sum().nlargest(5).reset_index()
        fig3 = px.bar(top_global, x='line_item_unblended_cost', y='resource_tags_user_tech_owner', orientation='h', title="3. Top 5 Divisi PT Jayantara dengan Pengeluaran Terbesar", text_auto='.2s', color='line_item_unblended_cost', color_continuous_scale='Reds', labels={'line_item_unblended_cost': 'Total Pengeluaran', 'resource_tags_user_tech_owner': 'Divisi'})
        fig3.update_traces(hovertemplate="<b>Divisi = %{y}</b><br>Total Pengeluaran = $%{x:,.2f}<extra></extra>")
        fig3.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Biaya (USD)", yaxis_title="Divisi", showlegend=False, margin=dict(l=0, r=0, t=60, b=0))

        # FIG 4: Bar Chart Top Projects
        top_projects = owner_data.groupby('resource_tags_user_project')['line_item_unblended_cost'].sum().nlargest(6).reset_index()
        fig4 = px.bar(top_projects, x='resource_tags_user_project', y='line_item_unblended_cost', title=f"4. Top 6 Proyek Paling Boros Biaya dari Divisi {selected_owner}", text_auto='.2s', color='line_item_unblended_cost', color_continuous_scale='Blues', labels={'line_item_unblended_cost': 'Total Pengeluaran', 'resource_tags_user_project': 'Nama Proyek'})
        fig4.update_traces(hovertemplate="<b>Project = %{x}</b><br>Total Pengeluaran = $%{y:,.2f}<extra></extra>")
        fig4.update_layout(xaxis_title="Nama Proyek", yaxis_title="Total Biaya (USD)", showlegend=False, margin=dict(l=0, r=0, t=60, b=0))

        # FIG 5: Bar Chart Global Services
        top_services_global = df_lite.groupby('product_product_family')['line_item_unblended_cost'].sum().nlargest(5).reset_index()
        fig5 = px.bar(top_services_global, x='line_item_unblended_cost', y='product_product_family', orientation='h', title="5. Top 5 Pengeluaran Servis AWS Terboros PT Jayantara", text_auto='.2s', color='line_item_unblended_cost', color_continuous_scale='Greens', labels={'line_item_unblended_cost': 'Total Pengeluaran', 'product_product_family': 'Servis AWS'})
        fig5.update_traces(hovertemplate="<b>Servis AWS = %{y}</b><br>Total Pengeluaran = $%{x:,.2f}<extra></extra>")
        fig5.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Biaya (USD)", yaxis_title="Servis AWS", showlegend=False, margin=dict(l=0, r=0, t=60, b=0))

        # FIG 6: Donut Chart
        service_dist = owner_data.groupby('product_product_family')['line_item_unblended_cost'].sum().reset_index()
        total_owner_cost = service_dist['line_item_unblended_cost'].sum()
        fig6 = px.pie(service_dist, values='line_item_unblended_cost', names='product_product_family', hole=0.5, title=f"6. Porsi Biaya Servis AWS Divisi {selected_owner}")
        fig6.update_traces(textposition='inside', textinfo='percent', showlegend=True, hovertemplate="<b>Servis AWS = %{label}</b><br>Total Pengeluaran = $%{value:,.2f}<extra></extra>")
        fig6.add_annotation(text=f"TOTAL<br><b>${total_owner_cost:,.0f}</b>", x=0.5, y=0.5, font=dict(size=16), showarrow=False)
        fig6.update_layout(margin=dict(l=20, r=20, t=60, b=20), legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5))
    else:
        empty_fig = go.Figure()
        fig1 = fig2 = fig3 = fig4 = fig5 = fig6 = empty_fig

    # 3. Update Bagian C (AI Narasi)
    ai_text = f"""**1. Analisis Efisiensi:**
Secara umum, divisi **{selected_owner}** menunjukkan pola pengeluaran yang [**Efisiensi Terjaga / Terdapat Anomali**]. Terdapat deviasi biaya sebesar X% dibandingkan dengan prediksi baseline pada tanggal [Tanggal Anomali].

**2. Identifikasi Pemborosan (Technical Root Cause):**
Lonjakan biaya tersebut dipicu oleh tingginya aktivitas operasi **[Nama Operasi]** pada layanan **[Nama Produk]**. Berdasarkan *scope* pekerjaan {selected_owner} yang fokus pada **{info['scope']}**, aktivitas ini kemungkinan berasal dari proyek **[Nama Proyek]** yang sedang melakukan sinkronisasi data secara masif.

**3. Rekomendasi Optimasi Actionable:**
* **Arsitektur:** Evaluasi arsitektur jaringan proyek terkait.
* **Rightsizing:** Pertimbangkan untuk menghentikan layanan jika tidak diperlukan.
* **Tagging:** Tingkatkan kedisiplinan pelabelan (*tagging*)."""

    return profil_text, metric_text, fig1, fig2, fig3, fig4, fig5, fig6, ai_text

# --- UI GRADIO BLOCKS ---
with gr.Blocks(theme=gr.themes.Soft(), title="Dashboard Cloud Cost - PT Jayantara") as demo:

    # Header Utama
    gr.HTML("""
        <h1 style='text-align: center; margin-bottom: 0;'>☁️ Identifikasi Peluang Optimasi Biaya Cloud AWS PT Jayantara pada Februari 2025 ☁️</h1>
        <p style='text-align: center; font-size: 18px; color: gray;'>Dashboard ini menampilkan profil biaya, visualisasi performa, dan insight otomatis berbasis AI untuk setiap divisi (Tech Owner).</p>
        <p style='text-align: center; font-size: 16px; color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 5px;'>
            ⚠️ <b>Tambahan Informasi</b> : Data yang digunakan terbatas pada periode bulan Februari 2025 dari tanggal 1-16 dikarenakan keterbatasan dan kualitas data
        </p>
    """)

    # Filter
    with gr.Row():
        with gr.Column(scale=1):
            pass
        with gr.Column(scale=2):
            dropdown_owner = gr.Dropdown(choices=list(TECH_OWNER_KNOWLEDGE.keys()), value=list(TECH_OWNER_KNOWLEDGE.keys())[0], label="🔍 Pilih Divisi yang Ingin Dianalisis")
        with gr.Column(scale=1):
            pass

    gr.Markdown("---")

    # Bagian A: Profil
    gr.Markdown("## Bagian A: Profil Divisi")
    with gr.Row():
        with gr.Column(scale=2):
            out_profil = gr.Markdown()
        with gr.Column(scale=1):
            out_metric = gr.HTML()

    gr.Markdown("---")

    # Bagian B: Visualisasi
    gr.Markdown("## Bagian B: Visualisasi Pengeluaran & Distribusi Biaya")

    with gr.Row():
        out_fig1 = gr.Plot()
        out_fig2 = gr.Plot()

    with gr.Row():
        out_fig3 = gr.Plot()
        out_fig4 = gr.Plot()
        out_fig5 = gr.Plot()
        out_fig6 = gr.Plot()

    gr.Markdown("---")

    # Bagian C: AI Insight
    gr.Markdown("## 🤖 AI Insight & Evaluasi Efisiensi")
    out_ai = gr.Markdown(elem_classes="ai-box")
    gr.Markdown("*Catatan: Narasi di atas akan digenerate secara otomatis (dinamis) oleh API LLM berdasarkan data aktual saat pengembangan dilanjutkan.*")

    # Hubungkan Interaksi (Event Listener)
    # Saat dropdown berubah, jalankan fungsi update_dashboard, dan salurkan hasilnya ke komponen output
    outputs = [out_profil, out_metric, out_fig1, out_fig2, out_fig3, out_fig4, out_fig5, out_fig6, out_ai]
    dropdown_owner.change(fn=update_dashboard, inputs=dropdown_owner, outputs=outputs)

    # Render pertama kali saat aplikasi dibuka
    demo.load(fn=update_dashboard, inputs=dropdown_owner, outputs=outputs)

# Jalankan Aplikasi
if __name__ == "__main__":
    demo.launch()