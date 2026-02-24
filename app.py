"""
====================================================
🏥 臨床藥物不良反應 (ADR) 智能監測儀表板
FDA FAERS Pharmacovigilance Analytics Platform
====================================================
Version: 3.1 (State Management & UI Fixes Update)
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
# Custom Styling - 側邊欄與深色模式全面覆蓋
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
        --text-primary: #ffffff !important;
        --text-secondary: #b0c4de !important;
        --border-color: #1e4976;
    }
    
    /* Global Styles */
    .stApp {
        background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
        font-family: 'IBM Plex Sans', sans-serif;
        color: var(--text-primary);
    }

    /* 強制修正所有文字顏色，避免黑字 */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: var(--text-primary);
    }
    
    .stMarkdown p { color: var(--text-secondary); }
    
    /* Sidebar Styling - 解決側邊欄白底或沒吃到的問題 */
    section[data-testid="stSidebar"] {
        background-color: var(--bg-secondary) !important;
        border-right: 1px solid var(--border-color) !important;
    }
    section[data-testid="stSidebar"] * {
        color: var(--text-primary) !important;
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
    
    .main-header h1 { color: white; font-size: 1.8rem; font-weight: 700; margin: 0; }
    .main-header p { color: rgba(255, 255, 255, 0.9); margin: 0.5rem 0 0 0; font-size: 0.95rem; }
    
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
    
    /* Input Fields Fixes */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        color: #ffffff !important;
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
    }
    
    div[data-baseweb="select"] > div, div[data-baseweb="popover"] {
        background-color: var(--bg-card) !important;
        color: white !important;
    }
    
    /* Tabs Fixes */
    .stTabs [data-baseweb="tab-list"] { background: var(--bg-secondary); border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { color: var(--text-secondary); }
    .stTabs [aria-selected="true"] { background: var(--fda-light-blue) !important; color: white !important; }
    
    /* Expander */
    .streamlit-expanderHeader { color: white !important; background: var(--bg-card); }
    
    /* DataTable overrides */
    [data-testid="stDataFrame"] { background-color: var(--bg-card); border-radius: 8px; }
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
                excerpt = "⚠️ 黑框警告 (Boxed Warning): " + data['boxed_warning'][0][:200] + "..."
            elif 'warnings' in data:
                excerpt = "警告 (Warnings): " + data['warnings'][0][:200] + "..."
            elif 'adverse_reactions' in data:
                excerpt = "不良反應 (Adverse Reactions): " + data['adverse_reactions'][0][:200] + "..."
            return True, excerpt, generics
        return False, "仿單中未找到明確關聯", []
    except Exception as e:
        return False, f"連線錯誤: {str(e)}", []

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
    params = {"search": query, "count": field_name, "limit": limit}
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params=params, timeout=15)
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
                "通報日期": event.get('receivedate', 'N/A'),
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
            record["體重(kg)"] = patient.get('patientweight', 'N/A')
            
            for drug in patient.get('drug', []):
                if drug_name.upper() in drug.get('medicinalproduct', '').upper():
                    record["懷疑藥品"] = drug.get('medicinalproduct', 'N/A')
                    dose_text = drug.get('drugdosagetext', '')
                    if not dose_text:
                        cum_dose = drug.get('drugcumulativedosagenumb', '')
                        unit = drug.get('drugcumulativedosageunit', '')
                        dose_text = f"{cum_dose} {unit}".strip() if cum_dose else '未提供'
                        
                    record["用藥劑量 (Dose)"] = dose_text
                    record["給藥途徑"] = drug.get('drugadministrationroute', 'N/A')
                    record["適應症"] = drug.get('drugindication', 'N/A')
                    record["製造商"] = event.get('companynumb', 'N/A')
                    break
            
            record["不良反應列表"] = "; ".join([r.get('reactionmeddrapt', '') for r in patient.get('reaction', [])])
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
        <h1>🏥 全球 ADR 智能監測儀表板 (V3.1)</h1>
        <p>基於 FDA FAERS 數據的臨床藥物警戒與劑量風險分析平台</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("### 🔬 查詢參數設定")
        
        # 預設值改為你常用的臨床問題
        drug_input = st.text_area(
            "💊 藥品名稱 (可輸入多個，用逗號分隔)",
            value="Empagliflozin, Dapagliflozin",
            height=80,
            help="請輸入學名或商品名 (英文)"
        )
        
        side_effect = st.text_input(
            "🎯 目標不良反應 (MedDRA PT)",
            value="Heart failure",
            help="使用標準 MedDRA 英文首選術語"
        )
        
        st.markdown("---")
        st.markdown("### ⚙️ 風險閾值設定")
        high_threshold = st.number_input("🔴 高風險警示 (通報數 ≥)", value=500, step=100)
        medium_threshold = st.number_input("🟠 中風險警示 (通報數 ≥)", value=100, step=50)
        
        analyze_btn = st.button("🚀 執行深度分析", type="primary", use_container_width=True)

    # 1. 將第一次搜尋結果存入 Session State，避免重新點擊其他按鈕時畫面消失
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
                risk_level, risk_reason = "高風險", "✅ 已明確記載於 FDA 仿單 (含黑框或警語)"
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
        
        # 保存狀態
        st.session_state['is_analyzed'] = True
        st.session_state['all_results'] = all_results
        st.session_state['current_side_effect'] = side_effect
    
    # 2. 如果狀態是已分析 (或曾經分析過)，就畫出主畫面
    if st.session_state.get('is_analyzed', False):
        all_results = st.session_state['all_results']
        current_side_effect = st.session_state['current_side_effect']
        
        st.markdown("### 📊 臨床分析摘要")
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(f'<div class="metric-card"><p class="metric-value">{len(all_results)}</p><p class="metric-label">分析藥品數</p></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="metric-card"><p class="metric-value" style="color: #d62828;">{sum(1 for r in all_results if r["risk_level"] == "高風險")}</p><p class="metric-label">高風險藥物</p></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="metric-card"><p class="metric-value" style="color: #02bfe7;">{sum(r["event_count"] for r in all_results):,}</p><p class="metric-label">總通報案件數</p></div>', unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 風險與仿單評估", 
            "🌍 地理與人口分佈", 
            "📈 適應症與趨勢",
            "💊 劑量與臨床案件檢閱",
            "📤 匯出資料"
        ])
        
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
                    {f'<div style="background: rgba(214, 40, 40, 0.1); padding: 1rem; border-radius: 6px;"><strong style="color: #ff6b35;">仿單摘錄：</strong><br>{res["label_excerpt"]}</div>' if res['in_label'] else ''}
                </div>
                """, unsafe_allow_html=True)

        with tab2:
            target_drug = st.selectbox("選擇藥品進行流行病學分析：", [r['drug'] for r in all_results], key="geo_drug")
            if target_drug:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### 🌍 前十大通報國家")
                    countries = get_distribution_data(target_drug, current_side_effect, "occurcountry", 10)
                    if countries:
                        df_c = pd.DataFrame(countries)
                        df_c['term'] = df_c['term'].map(lambda x: COUNTRY_CODES.get(x, x))
                        fig_c = px.bar(df_c, x='count', y='term', orientation='h', template='plotly_dark')
                        fig_c.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_c, use_container_width=True)
                
                with c2:
                    st.markdown("#### 👤 通報者專業身份")
                    reporters = get_distribution_data(target_drug, current_side_effect, "primarysource.qualification")
                    if reporters:
                        qual_map = {"1": "醫師", "2": "藥師", "3": "其他醫事人員", "4": "律師", "5": "民眾"}
                        df_r = pd.DataFrame(reporters)
                        df_r['term'] = df_r['term'].astype(str).map(qual_map)
                        fig_r = px.pie(df_r, values='count', names='term', template='plotly_dark', hole=0.4)
                        fig_r.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_r, use_container_width=True)

        with tab3:
            st.markdown("#### 🎯 主要處方適應症 (Indication) 分析")
            inds = get_distribution_data(target_drug, current_side_effect, "patient.drug.drugindication.exact", 10)
            if inds:
                df_ind = pd.DataFrame(inds)
                fig_ind = px.bar(df_ind, x='term', y='count', title=f"{target_drug} 引發 {current_side_effect} 案件的原始適應症", template='plotly_dark')
                fig_ind.update_layout(xaxis_title="適應症", yaxis_title="案件數", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_ind, use_container_width=True)
            else:
                st.info("無足夠的適應症資料。")

        with tab4:
            st.markdown(f"### 💊 臨床案件劑量檢閱器 (Case Browser)")
            st.markdown("此區塊直接從 FAERS 抽取近期詳細通報案件，方便您評估**「劑量依賴性 (Dose-dependency)」**與嚴重度。")
            
            case_limit = st.slider("選擇載入的近期案件數量：", 20, 200, 50, step=10)
            
            # 點擊此按鈕後，會觸發重新載入，但因為有 session_state['is_analyzed']，主畫面不會消失！
            if st.button("📥 載入案件與劑量明細", type="secondary"):
                with st.spinner("正在解析 JSON 並萃取劑量與嚴重度指標..."):
                    raw_cases = get_detailed_events(target_drug, current_side_effect, limit=case_limit)
                    if raw_cases:
                        df_cases = parse_events_to_dataframe(raw_cases, target_drug)
                        st.session_state['df_cases'] = df_cases
                        st.session_state['cases_loaded_drug'] = target_drug
            
            if 'df_cases' in st.session_state and st.session_state.get('cases_loaded_drug') == target_drug:
                df_cases = st.session_state['df_cases']
                
                st.markdown("#### 📌 劑量文字摘要 (Top 5 紀錄)")
                dose_counts = df_cases[df_cases['用藥劑量 (Dose)'] != '未提供']['用藥劑量 (Dose)'].value_counts().head(5)
                if not dose_counts.empty:
                    st.dataframe(dose_counts.reset_index().rename(columns={'index': '通報劑量', '用藥劑量 (Dose)': '案件數'}), use_container_width=True)
                
                st.markdown("#### 📋 完整案件清單")
                st.dataframe(
                    df_cases[['安全報告 ID', '用藥劑量 (Dose)', '給藥途徑', '適應症', '嚴重度', '年齡', '性別', '通報者身分']],
                    use_container_width=True,
                    height=400
                )

        with tab5:
            st.markdown("### 📤 匯出完整結構化資料")
            if 'df_cases' in st.session_state:
                st.success("資料已備妥可供匯出！包含所有欄位（如：體重、多重不良反應列表等）。")
                csv = st.session_state['df_cases'].to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📄 下載 CSV (相容 Excel 繁體中文)",
                    data=csv,
                    file_name=f"FAERS_Cases_{target_drug}_{current_side_effect}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("請先至「💊 劑量與臨床案件檢閱」分頁載入資料後再行匯出。")

    elif not st.session_state.get('is_analyzed', False):
        st.info("👈 請在側邊欄輸入藥品與不良反應後，點擊「執行深度分析」。")

if __name__ == "__main__":
    main()
