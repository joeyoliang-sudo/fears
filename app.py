"""
====================================================
🏥 臨床藥物不良反應 (ADR) 智能監測儀表板
FDA FAERS Pharmacovigilance Analytics Platform
====================================================
Version: 3.2 (UI Rendering & Case Browser Fixes)
====================================================
"""

import streamlit as st
import requests
import pandas as pd
import time
import io
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# Page Configuration
# ==========================================
st.set_page_config(
    page_title="全球 ADR 智能監測儀表板",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# Custom Styling - 精準覆蓋，避免破壞原生組件
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
    
    :root {
        --fda-blue: #003366;
        --fda-light-blue: #0071bc;
        --fda-accent: #02bfe7;
        --warning-orange: #ff6b35;
        --danger-red: #d62828;
        --safe-green: #2a9d8f;
        --bg-primary: #0a1628;
        --bg-secondary: #0f2744;
        --bg-card: #132f4c;
        --text-primary: #ffffff;
        --text-secondary: #b0c4de;
        --border-color: #1e4976;
    }
    
    /* Global Styles */
    .stApp {
        background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
        font-family: 'IBM Plex Sans', sans-serif;
    }

    /* 針對標題與內文設定白色，不使用萬用字元以免破壞表格或按鈕 */
    h1, h2, h3, h4, h5, h6, .stMarkdown p {
        color: var(--text-primary) !important;
    }
    
    /* 側邊欄背景 */
    section[data-testid="stSidebar"] {
        background-color: var(--bg-secondary) !important;
        border-right: 1px solid var(--border-color) !important;
    }
    
    /* 修正按鈕樣式 (解決截圖中按鈕全白的問題) */
    .stButton > button {
        background: linear-gradient(90deg, var(--fda-light-blue) 0%, var(--fda-accent) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
    }
    .stButton > button p {
        color: white !important;
        margin: 0 !important;
    }
    
    /* Header Styling */
    .main-header {
        background: linear-gradient(90deg, var(--fda-blue) 0%, var(--fda-light-blue) 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border-left: 5px solid var(--fda-accent);
        box-shadow: 0 4px 20px rgba(0, 113, 188, 0.3);
    }
    
    /* Metric Cards */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
    }
    .metric-value { font-family: 'IBM Plex Mono', monospace; font-size: 2.2rem; font-weight: 700; color: var(--fda-accent); margin: 0; }
    .metric-label { color: var(--text-secondary); font-size: 0.85rem; text-transform: uppercase; margin-top: 0.5rem; }
    
    /* Tabs Fixes */
    .stTabs [data-baseweb="tab-list"] { background: var(--bg-secondary); border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { color: var(--text-secondary); }
    .stTabs [aria-selected="true"] { background: var(--fda-light-blue) !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# API Configuration & Helper Data
# ==========================================
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
OPENFDA_EVENT_URL = "https://api.fda.gov/drug/event.json"

COUNTRY_CODES = {
    "US": "美國", "JP": "日本", "DE": "德國", "FR": "法國", "GB": "英國",
    "CA": "加拿大", "AU": "澳洲", "IT": "義大利", "ES": "西班牙", "BR": "巴西",
    "KR": "南韓", "TW": "台灣", "CN": "中國", "IN": "印度", "MX": "墨西哥"
}

def get_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# ==========================================
# Data Fetching Functions
# ==========================================
@st.cache_data(ttl=300)
def check_label_risk(drug_name, side_effect):
    query = f'(openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}") AND (adverse_reactions:"{side_effect}" OR warnings:"{side_effect}" OR boxed_warning:"{side_effect}")'
    params = {"search": query, "limit": 1}
    try:
        session = get_session()
        response = session.get(OPENFDA_LABEL_URL, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json().get('results', [])[0]
            generics = data.get('openfda', {}).get('generic_name', [])
            excerpt = ""
            if 'boxed_warning' in data:
                excerpt = "⚠️ 黑框警告: " + data['boxed_warning'][0][:200] + "..."
            elif 'warnings' in data:
                excerpt = "警告: " + data['warnings'][0][:200] + "..."
            elif 'adverse_reactions' in data:
                excerpt = "不良反應: " + data['adverse_reactions'][0][:200] + "..."
            return True, excerpt, generics
        return False, "仿單中未找到明確關聯", []
    except Exception:
        return False, "連線錯誤", []

@st.cache_data(ttl=300)
def count_faers_events(input_name, side_effect, alias_list=None):
    if alias_list is None: alias_list = []
    search_terms = set([input_name] + alias_list)
    terms_str = " ".join([f'"{term}"' for term in search_terms if term])
    query = f'patient.drug.medicinalproduct:({terms_str}) AND patient.reaction.reactionmeddrapt:"{side_effect}"'
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params={"search": query, "limit": 1}, timeout=15)
        if response.status_code == 200:
            return response.json().get('meta', {}).get('results', {}).get('total', 0), list(search_terms)
        return 0, list(search_terms)
    except:
        return -1, []

@st.cache_data(ttl=300)
def get_distribution_data(drug_name, side_effect, field_name, limit=20):
    query = f'patient.drug.medicinalproduct:"{drug_name}" AND patient.reaction.reactionmeddrapt:"{side_effect}"'
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params={"search": query, "count": field_name, "limit": limit}, timeout=15)
        if response.status_code == 200:
            return response.json().get('results', [])
        return []
    except:
        return []

@st.cache_data(ttl=300)
def get_detailed_events(drug_name, side_effect, limit=100):
    query = f'patient.drug.medicinalproduct:"{drug_name}" AND patient.reaction.reactionmeddrapt:"{side_effect}"'
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params={"search": query, "limit": limit}, timeout=20)
        if response.status_code == 200:
            return response.json().get('results', [])
        return []
    except:
        return []

def parse_events_to_dataframe(events, drug_name):
    records = []
    qual_map = {"1": "醫師", "2": "藥師", "3": "其他醫事人員", "4": "律師", "5": "消費者/病患"}
    
    for event in events:
        try:
            record = {
                "安全報告 ID": event.get('safetyreportid', 'N/A'),
                "通報國家": COUNTRY_CODES.get(event.get('occurcountry', 'N/A'), event.get('occurcountry', 'N/A')),
                "通報者身分": qual_map.get(event.get('primarysource', {}).get('qualification'), '未知')
            }
            seriousness = []
            if event.get('seriousnessdeath') == '1': seriousness.append("死亡")
            if event.get('seriousnesshospitalization') == '1': seriousness.append("住院")
            if event.get('seriousnessdisabling') == '1': seriousness.append("失能")
            if event.get('seriousnesslifethreatening') == '1': seriousness.append("危及生命")
            record["嚴重度"] = "嚴重 (" + ", ".join(seriousness) + ")" if seriousness else "非嚴重"
            
            patient = event.get('patient', {})
            record["年齡"] = patient.get('patientonsetage', 'N/A')
            record["性別"] = {"1": "男", "2": "女"}.get(patient.get('patientsex'), '未知')
            
            for drug in patient.get('drug', []):
                if drug_name.upper() in drug.get('medicinalproduct', '').upper():
                    dose_text = drug.get('drugdosagetext', '')
                    if not dose_text:
                        cum_dose = drug.get('drugcumulativedosagenumb', '')
                        unit = drug.get('drugcumulativedosageunit', '')
                        dose_text = f"{cum_dose} {unit}".strip() if cum_dose else '未提供'
                    record["用藥劑量 (Dose)"] = dose_text
                    record["給藥途徑"] = drug.get('drugadministrationroute', 'N/A')
                    record["適應症"] = drug.get('drugindication', 'N/A')
                    break
            records.append(record)
        except Exception:
            continue
    return pd.DataFrame(records)

# ==========================================
# Main Application
# ==========================================
def main():
    st.markdown("""
    <div class="main-header">
        <h1>🏥 全球 ADR 智能監測儀表板 (V3.2)</h1>
        <p>基於 FDA FAERS 數據的臨床藥物警戒與劑量風險分析平台</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("### 🔬 查詢參數設定")
        drug_input = st.text_area("💊 藥品名稱 (可輸入多個，用逗號分隔)", value="Empagliflozin, Dapagliflozin", height=80)
        side_effect = st.text_input("🎯 目標不良反應 (MedDRA PT)", value="Heart failure")
        st.markdown("---")
        st.markdown("### ⚙️ 風險閾值設定")
        high_threshold = st.number_input("🔴 高風險警示 (通報數 ≥)", value=500, step=100)
        medium_threshold = st.number_input("🟠 中風險警示 (通報數 ≥)", value=100, step=50)
        
        analyze_btn = st.button("🚀 執行深度分析", use_container_width=True)

    if analyze_btn and drug_input and side_effect:
        drug_list = [d.strip() for d in drug_input.split(',') if d.strip()]
        progress_bar = st.progress(0)
        status_text = st.empty()
        all_results = []
        
        for i, drug in enumerate(drug_list):
            status_text.markdown(f"正在分析: `{drug}` 關聯之 `{side_effect}`...")
            progress_bar.progress((i + 1) / len(drug_list))
            
            in_label, label_excerpt, generics = check_label_risk(drug, side_effect)
            time.sleep(0.3)
            event_count, used_terms = count_faers_events(drug, side_effect, generics)
            
            if in_label:
                risk_level, risk_reason = "高風險", "✅ 已明確記載於 FDA 仿單"
            elif event_count >= high_threshold:
                risk_level, risk_reason = "高風險", f"⚠️ FAERS 訊號強烈 ({event_count:,} 筆通報)"
            elif event_count >= medium_threshold:
                risk_level, risk_reason = "中風險", f"🔍 中度通報訊號 ({event_count:,} 筆通報)"
            else:
                risk_level, risk_reason = "低風險", f"低度訊號 ({event_count:,} 筆通報)"
            
            all_results.append({
                "drug": drug, "in_label": in_label, "label_excerpt": label_excerpt,
                "event_count": event_count, "risk_level": risk_level, "risk_reason": risk_reason
            })
            
        progress_bar.empty()
        status_text.empty()
        st.session_state['is_analyzed'] = True
        st.session_state['all_results'] = all_results
        st.session_state['current_side_effect'] = side_effect
    
    if st.session_state.get('is_analyzed', False):
        all_results = st.session_state['all_results']
        current_side_effect = st.session_state['current_side_effect']
        
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(f'<div class="metric-card"><p class="metric-value">{len(all_results)}</p><p class="metric-label">分析藥品數</p></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="metric-card"><p class="metric-value" style="color: #d62828;">{sum(1 for r in all_results if r["risk_level"] == "高風險")}</p><p class="metric-label">高風險藥物</p></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="metric-card"><p class="metric-value" style="color: #02bfe7;">{sum(r["event_count"] for r in all_results):,}</p><p class="metric-label">總通報案件數</p></div>', unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["📋 風險與仿單評估", "🌍 流行病學分佈", "💊 劑量與臨床案件檢閱", "📤 匯出資料"])
        
        with tab1:
            for res in all_results:
                border_color = "#d62828" if res['risk_level'] == "高風險" else ("#ff6b35" if res['risk_level'] == "中風險" else "#2a9d8f")
                st.markdown(f"""
                <div style="background: var(--bg-card); border-left: 5px solid {border_color}; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem;">
                    <h3 style="margin-top:0;">💊 {res['drug']} <span style="font-size: 1rem; color: {border_color}; float: right;">{res['risk_level']}</span></h3>
                    <div style="display: flex; gap: 2rem; margin: 1rem 0;">
                        <div><strong>FAERS 案件數：</strong> <span style="color:#02bfe7; font-size:1.2rem;">{res['event_count']:,}</span> 筆</div>
                        <div><strong>評估依據：</strong> {res['risk_reason']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with tab2:
            target_drug = st.selectbox("選擇藥品進行流行病學分析：", [r['drug'] for r in all_results], key="geo_drug")
            if target_drug:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### 👤 通報者專業身份")
                    reporters = get_distribution_data(target_drug, current_side_effect, "primarysource.qualification")
                    if reporters:
                        qual_map = {"1": "醫師", "2": "藥師", "3": "其他醫事人員", "4": "律師", "5": "民眾"}
                        df_r = pd.DataFrame(reporters)
                        df_r['term'] = df_r['term'].astype(str).map(qual_map)
                        fig_r = px.pie(df_r, values='count', names='term', template='plotly_dark', hole=0.4)
                        fig_r.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_r, use_container_width=True)
                with c2:
                    st.markdown("#### 🎯 主要處方適應症")
                    inds = get_distribution_data(target_drug, current_side_effect, "patient.drug.drugindication.exact", 10)
                    if inds:
                        df_ind = pd.DataFrame(inds)
                        fig_ind = px.bar(df_ind, x='term', y='count', template='plotly_dark')
                        fig_ind.update_layout(xaxis_title="適應症", yaxis_title="案件數", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_ind, use_container_width=True)

        with tab3:
            st.markdown(f"### 💊 臨床案件劑量檢閱器 (Case Browser)")
            case_limit = st.slider("選擇載入的近期案件數量：", 20, 200, 110, step=10)
            
            if st.button("📥 載入案件與劑量明細"):
                with st.spinner("正在解析 JSON 並萃取劑量與嚴重度指標..."):
                    raw_cases = get_detailed_events(target_drug, current_side_effect, limit=case_limit)
                    if raw_cases:
                        df_cases = parse_events_to_dataframe(raw_cases, target_drug)
                        st.session_state['df_cases'] = df_cases
                        st.session_state['cases_loaded_drug'] = target_drug
            
            if 'df_cases' in st.session_state and st.session_state.get('cases_loaded_drug') == target_drug:
                df_cases = st.session_state['df_cases']
                
                # ✅ 這裡加上明確提示，並移除 height 限制，讓表格自由延展或顯示原生捲軸
                st.success(f"✅ 成功載入 {len(df_cases)} 筆案件紀錄！ (請在下方表格內上下滑動捲軸檢視完整資料)")
                
                st.markdown("#### 📋 完整案件清單")
                st.dataframe(
                    df_cases[['安全報告 ID', '用藥劑量 (Dose)', '給藥途徑', '適應症', '嚴重度', '年齡', '性別', '通報者身分']],
                    use_container_width=True
                    # 💡 移除了 height=400 的限制
                )

        with tab4:
            st.markdown("### 📤 匯出完整結構化資料")
            if 'df_cases' in st.session_state:
                csv = st.session_state['df_cases'].to_csv(index=False).encode('utf-8-sig')
                st.download_button("📄 下載 CSV (相容 Excel 繁體中文)", data=csv, file_name=f"FAERS_Cases_{target_drug}.csv", mime="text/csv")
            else:
                st.info("請先至「💊 劑量與臨床案件檢閱」分頁載入資料。")

    elif not st.session_state.get('is_analyzed', False):
        # ✅ 把歡迎畫面加回來，解決剛開啟時主畫面空白的問題
        st.markdown("""
        <div style="background: var(--bg-card); padding: 2rem; border-radius: 12px; text-align: center; border: 1px solid var(--border-color);">
            <h2 style="color: var(--fda-accent);">👋 歡迎使用全球 ADR 智能監測系統</h2>
            <p style="color: var(--text-secondary); font-size: 1.1rem; margin-top: 1rem;">
                本系統直接串接 <b>FDA FAERS API</b>，提供即時的藥物不良反應流行病學與劑量關聯性分析。<br><br>
                👈 請先在<b>左側選單</b>輸入您想研究的藥品與不良反應 (例如：SGLT2 inhibitors 與 Heart failure)，然後點擊<b>「執行深度分析」</b>。
            </p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
