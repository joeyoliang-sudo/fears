"""
====================================================
🏥 臨床藥物不良反應 (ADR) 智能監測儀表板
FDA FAERS Pharmacovigilance Analytics Platform
====================================================
Version: 4.0 (Light Theme · Scrollable Case Browser · Hardened API)
====================================================
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==========================================
# Logging (取代沉默的 bare except)
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("adr_dashboard")

# ==========================================
# Page Configuration
# ==========================================
st.set_page_config(
    page_title="全球 ADR 智能監測儀表板",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================
# Light Theme Styling
# ==========================================
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root {
        --fda-blue: #0b3d91;
        --fda-light-blue: #2563eb;
        --fda-accent: #0891b2;
        --warning-orange: #ea580c;
        --danger-red: #b91c1c;
        --safe-green: #047857;
        --bg-primary: #f5f7fb;
        --bg-secondary: #ffffff;
        --bg-card: #ffffff;
        --bg-soft: #eef2f7;
        --text-primary: #0f172a;
        --text-secondary: #475569;
        --text-muted: #64748b;
        --border-color: #d8dfe8;
    }

    /* Global */
    .stApp {
        background: var(--bg-primary) !important;
        font-family: 'IBM Plex Sans', sans-serif;
        color: var(--text-primary);
    }
    h1, h2, h3, h4, h5, h6 { color: var(--text-primary) !important; }
    .stMarkdown p, .stMarkdown li { color: var(--text-primary); }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: var(--bg-secondary) !important;
        border-right: 1px solid var(--border-color) !important;
    }
    section[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

    /* Buttons */
    .stButton > button, .stDownloadButton > button {
        background: linear-gradient(90deg, var(--fda-blue) 0%, var(--fda-light-blue) 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.1rem !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        filter: brightness(1.05);
    }
    .stButton > button p, .stDownloadButton > button p { color: #ffffff !important; margin: 0 !important; }

    /* Header banner */
    .main-header {
        background: linear-gradient(90deg, var(--fda-blue) 0%, var(--fda-light-blue) 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border-left: 6px solid var(--fda-accent);
        box-shadow: 0 6px 20px rgba(11, 61, 145, 0.18);
        color: #ffffff;
    }
    .main-header h1, .main-header p { color: #ffffff !important; margin: 0; }
    .main-header p { opacity: 0.92; margin-top: 0.4rem; }

    /* KPI cards */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.1rem 1.25rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }
    .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2rem;
        font-weight: 700;
        color: var(--fda-light-blue);
        margin: 0;
    }
    .metric-label {
        color: var(--text-muted);
        font-size: 0.8rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-top: 0.4rem;
    }

    /* Risk cards */
    .risk-card {
        background: var(--bg-card);
        padding: 1.25rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border: 1px solid var(--border-color);
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }
    .risk-card h3 { margin: 0 0 0.6rem 0; }
    .risk-meta { display: flex; gap: 2rem; flex-wrap: wrap; color: var(--text-secondary); }
    .risk-meta strong { color: var(--text-primary); }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--bg-soft);
        border-radius: 10px;
        padding: 0.25rem;
        gap: 0.25rem;
    }
    .stTabs [data-baseweb="tab"] { color: var(--text-secondary); }
    .stTabs [aria-selected="true"] {
        background: var(--fda-light-blue) !important;
        color: #ffffff !important;
        border-radius: 8px;
    }

    /* Welcome panel */
    .welcome-panel {
        background: var(--bg-card);
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        border: 1px solid var(--border-color);
        box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
    }
    .welcome-panel h2 { color: var(--fda-blue); }
    .welcome-panel p { color: var(--text-secondary); font-size: 1.05rem; }

    /* Dataframe – let the native scrollbar work and stand out on light bg */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border-color);
        border-radius: 8px;
    }

    /* Alerts on light bg readability */
    .stAlert { border-radius: 8px; }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# Constants & Config
# ==========================================
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
OPENFDA_EVENT_URL = "https://api.fda.gov/drug/event.json"
PLOTLY_TEMPLATE = "plotly_white"
REQUEST_TIMEOUT = 15

COUNTRY_CODES = {
    "US": "美國", "JP": "日本", "DE": "德國", "FR": "法國", "GB": "英國",
    "CA": "加拿大", "AU": "澳洲", "IT": "義大利", "ES": "西班牙", "BR": "巴西",
    "KR": "南韓", "TW": "台灣", "CN": "中國", "IN": "印度", "MX": "墨西哥",
}

QUALIFICATION_MAP = {
    "1": "醫師",
    "2": "藥師",
    "3": "其他醫事人員",
    "4": "律師",
    "5": "消費者/病患",
}

CASE_COLUMNS = [
    "安全報告 ID", "用藥劑量 (Dose)", "給藥途徑", "適應症",
    "嚴重度", "年齡", "性別", "通報國家", "通報者身分",
]


def _sanitize(value: str) -> str:
    """Escape characters that would break the openFDA Lucene query string."""
    return value.replace("\\", "").replace('"', "").strip()


def get_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, connect=3, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# ==========================================
# Data Fetching
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def check_label_risk(drug_name: str, side_effect: str) -> tuple[bool, str, list[str]]:
    drug = _sanitize(drug_name)
    se = _sanitize(side_effect)
    if not drug or not se:
        return False, "輸入為空", []
    query = (
        f'(openfda.brand_name:"{drug}" OR openfda.generic_name:"{drug}") '
        f'AND (adverse_reactions:"{se}" OR warnings:"{se}" OR boxed_warning:"{se}")'
    )
    try:
        response = get_session().get(
            OPENFDA_LABEL_URL, params={"search": query, "limit": 1}, timeout=REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            return False, "仿單中未找到明確關聯", []
        results = response.json().get("results", [])
        if not results:
            return False, "仿單中未找到明確關聯", []
        data = results[0]
        generics = data.get("openfda", {}).get("generic_name", []) or []
        excerpt = ""
        if "boxed_warning" in data:
            excerpt = "⚠️ 黑框警告: " + data["boxed_warning"][0][:200] + "..."
        elif "warnings" in data:
            excerpt = "警告: " + data["warnings"][0][:200] + "..."
        elif "adverse_reactions" in data:
            excerpt = "不良反應: " + data["adverse_reactions"][0][:200] + "..."
        return True, excerpt, generics
    except requests.RequestException as exc:
        log.warning("check_label_risk failed for %s/%s: %s", drug, se, exc)
        return False, "連線錯誤", []


@st.cache_data(ttl=300, show_spinner=False)
def count_faers_events(
    input_name: str, side_effect: str, alias_list: list[str] | None = None
) -> tuple[int, list[str]]:
    aliases = alias_list or []
    terms = {_sanitize(t) for t in [input_name, *aliases] if _sanitize(t)}
    if not terms:
        return 0, []
    se = _sanitize(side_effect)
    terms_str = " ".join(f'"{t}"' for t in terms)
    query = (
        f"patient.drug.medicinalproduct:({terms_str}) "
        f'AND patient.reaction.reactionmeddrapt:"{se}"'
    )
    try:
        response = get_session().get(
            OPENFDA_EVENT_URL, params={"search": query, "limit": 1}, timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            total = (
                response.json().get("meta", {}).get("results", {}).get("total", 0)
            )
            return total, list(terms)
        if response.status_code == 404:
            return 0, list(terms)
        log.info("count_faers_events status=%s body=%s", response.status_code, response.text[:200])
        return 0, list(terms)
    except requests.RequestException as exc:
        log.warning("count_faers_events failed: %s", exc)
        return -1, []


@st.cache_data(ttl=300, show_spinner=False)
def get_distribution_data(
    drug_name: str, side_effect: str, field_name: str, limit: int = 20
) -> list[dict[str, Any]]:
    drug = _sanitize(drug_name)
    se = _sanitize(side_effect)
    if not drug or not se:
        return []
    query = (
        f'patient.drug.medicinalproduct:"{drug}" '
        f'AND patient.reaction.reactionmeddrapt:"{se}"'
    )
    try:
        response = get_session().get(
            OPENFDA_EVENT_URL,
            params={"search": query, "count": field_name, "limit": limit},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            return response.json().get("results", [])
        return []
    except requests.RequestException as exc:
        log.warning("get_distribution_data failed: %s", exc)
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_detailed_events(
    drug_name: str, side_effect: str, limit: int = 100
) -> list[dict[str, Any]]:
    drug = _sanitize(drug_name)
    se = _sanitize(side_effect)
    if not drug or not se:
        return []
    query = (
        f'patient.drug.medicinalproduct:"{drug}" '
        f'AND patient.reaction.reactionmeddrapt:"{se}"'
    )
    try:
        response = get_session().get(
            OPENFDA_EVENT_URL,
            params={"search": query, "limit": limit},
            timeout=REQUEST_TIMEOUT + 5,
        )
        if response.status_code == 200:
            return response.json().get("results", [])
        return []
    except requests.RequestException as exc:
        log.warning("get_detailed_events failed: %s", exc)
        return []


def parse_events_to_dataframe(events: list[dict[str, Any]], drug_name: str) -> pd.DataFrame:
    """Always returns a DataFrame containing every column in CASE_COLUMNS."""
    records: list[dict[str, Any]] = []
    drug_upper = drug_name.upper()

    for event in events:
        record: dict[str, Any] = {col: "N/A" for col in CASE_COLUMNS}
        try:
            record["安全報告 ID"] = event.get("safetyreportid", "N/A")
            record["通報國家"] = COUNTRY_CODES.get(
                event.get("occurcountry", "N/A"), event.get("occurcountry", "N/A")
            )
            qualification = (event.get("primarysource") or {}).get("qualification")
            record["通報者身分"] = QUALIFICATION_MAP.get(qualification, "未知")

            seriousness: list[str] = []
            if event.get("seriousnessdeath") == "1":
                seriousness.append("死亡")
            if event.get("seriousnesshospitalization") == "1":
                seriousness.append("住院")
            if event.get("seriousnessdisabling") == "1":
                seriousness.append("失能")
            if event.get("seriousnesslifethreatening") == "1":
                seriousness.append("危及生命")
            record["嚴重度"] = (
                "嚴重 (" + ", ".join(seriousness) + ")" if seriousness else "非嚴重"
            )

            patient = event.get("patient", {}) or {}
            record["年齡"] = patient.get("patientonsetage", "N/A")
            record["性別"] = {"1": "男", "2": "女"}.get(patient.get("patientsex"), "未知")

            for drug in patient.get("drug", []) or []:
                product = (drug.get("medicinalproduct") or "").upper()
                if drug_upper in product:
                    dose_text = drug.get("drugdosagetext") or ""
                    if not dose_text:
                        cum_dose = drug.get("drugcumulativedosagenumb", "")
                        unit = drug.get("drugcumulativedosageunit", "")
                        dose_text = f"{cum_dose} {unit}".strip() if cum_dose else "未提供"
                    record["用藥劑量 (Dose)"] = dose_text
                    record["給藥途徑"] = drug.get("drugadministrationroute", "N/A")
                    record["適應症"] = drug.get("drugindication", "N/A")
                    break

            records.append(record)
        except Exception as exc:  # noqa: BLE001 — last-resort guard, logged below
            log.warning("parse_events_to_dataframe skipped a record: %s", exc)
            continue

    return pd.DataFrame(records, columns=CASE_COLUMNS)


# ==========================================
# Helpers
# ==========================================
def _reset_case_state() -> None:
    for key in ("df_cases", "cases_loaded_drug"):
        st.session_state.pop(key, None)


def _summary_dataframe(results: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "藥品": r["drug"],
                "風險等級": r["risk_level"],
                "FAERS 案件數": r["event_count"],
                "FDA 仿單收載": "是" if r["in_label"] else "否",
                "評估依據": r["risk_reason"],
            }
            for r in results
        ]
    )


# ==========================================
# Main Application
# ==========================================
def main() -> None:
    st.markdown(
        """
        <div class="main-header">
            <h1>🏥 全球 ADR 智能監測儀表板 (V4.0)</h1>
            <p>基於 FDA FAERS 數據的臨床藥物警戒與劑量風險分析平台</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### 🔬 查詢參數設定")
        drug_input = st.text_area(
            "💊 藥品名稱 (可輸入多個，用逗號分隔)",
            value="Empagliflozin, Dapagliflozin",
            height=80,
        )
        side_effect = st.text_input("🎯 目標不良反應 (MedDRA PT)", value="Heart failure")
        st.markdown("---")
        st.markdown("### ⚙️ 風險閾值設定")
        high_threshold = st.number_input("🔴 高風險警示 (通報數 ≥)", value=500, step=100)
        medium_threshold = st.number_input("🟠 中風險警示 (通報數 ≥)", value=100, step=50)

        analyze_btn = st.button("🚀 執行深度分析", use_container_width=True)
        if st.session_state.get("is_analyzed"):
            if st.button("🧹 重設分析", use_container_width=True):
                for key in ("is_analyzed", "all_results", "current_side_effect", "analyzed_at"):
                    st.session_state.pop(key, None)
                _reset_case_state()
                st.rerun()

    if analyze_btn:
        if not drug_input.strip() or not side_effect.strip():
            st.warning("請至少輸入一個藥品名稱與一個不良反應後再執行分析。")
            return

        drug_list = [d.strip() for d in drug_input.split(",") if d.strip()]
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        all_results: list[dict[str, Any]] = []

        for i, drug in enumerate(drug_list):
            status_text.markdown(f"正在分析: `{drug}` 關聯之 `{side_effect}`...")
            in_label, label_excerpt, generics = check_label_risk(drug, side_effect)
            event_count, used_terms = count_faers_events(drug, side_effect, generics)

            if in_label:
                risk_level, risk_reason = "高風險", "✅ 已明確記載於 FDA 仿單"
            elif event_count >= high_threshold:
                risk_level, risk_reason = "高風險", f"⚠️ FAERS 訊號強烈 ({event_count:,} 筆通報)"
            elif event_count >= medium_threshold:
                risk_level, risk_reason = "中風險", f"🔍 中度通報訊號 ({event_count:,} 筆通報)"
            else:
                risk_level, risk_reason = "低風險", f"低度訊號 ({max(event_count, 0):,} 筆通報)"

            all_results.append(
                {
                    "drug": drug,
                    "in_label": in_label,
                    "label_excerpt": label_excerpt,
                    "event_count": event_count,
                    "risk_level": risk_level,
                    "risk_reason": risk_reason,
                    "used_terms": used_terms,
                }
            )
            progress_bar.progress((i + 1) / len(drug_list))

        progress_bar.empty()
        status_text.empty()
        _reset_case_state()
        st.session_state["is_analyzed"] = True
        st.session_state["all_results"] = all_results
        st.session_state["current_side_effect"] = side_effect
        st.session_state["analyzed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if st.session_state.get("is_analyzed"):
        all_results: list[dict[str, Any]] = st.session_state["all_results"]
        current_side_effect: str = st.session_state["current_side_effect"]
        analyzed_at: str = st.session_state.get("analyzed_at", "")

        st.caption(
            f"🕒 分析時間：{analyzed_at} ｜ 不良反應目標：**{current_side_effect}** ｜ "
            f"分析藥品：{', '.join(r['drug'] for r in all_results)}"
        )

        high_risk_count = sum(1 for r in all_results if r["risk_level"] == "高風險")
        total_events = sum(max(r["event_count"], 0) for r in all_results)
        in_label_count = sum(1 for r in all_results if r["in_label"])

        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(
            f'<div class="metric-card"><p class="metric-value">{len(all_results)}</p>'
            f'<p class="metric-label">分析藥品數</p></div>',
            unsafe_allow_html=True,
        )
        col2.markdown(
            f'<div class="metric-card"><p class="metric-value" style="color:#b91c1c;">{high_risk_count}</p>'
            f'<p class="metric-label">高風險藥物</p></div>',
            unsafe_allow_html=True,
        )
        col3.markdown(
            f'<div class="metric-card"><p class="metric-value" style="color:#0891b2;">{total_events:,}</p>'
            f'<p class="metric-label">總通報案件數</p></div>',
            unsafe_allow_html=True,
        )
        col4.markdown(
            f'<div class="metric-card"><p class="metric-value" style="color:#047857;">{in_label_count}/{len(all_results)}</p>'
            f'<p class="metric-label">已收載於 FDA 仿單</p></div>',
            unsafe_allow_html=True,
        )

        tab1, tab2, tab3, tab4 = st.tabs(
            ["📋 風險與仿單評估", "🌍 流行病學分佈", "💊 劑量與臨床案件檢閱", "📤 匯出資料"]
        )

        with tab1:
            for res in all_results:
                border_color = (
                    "#b91c1c"
                    if res["risk_level"] == "高風險"
                    else ("#ea580c" if res["risk_level"] == "中風險" else "#047857")
                )
                excerpt_html = (
                    f'<div style="margin-top:0.75rem; color:#475569; font-size:0.92rem; '
                    f'border-top:1px dashed #d8dfe8; padding-top:0.6rem;">{res["label_excerpt"]}</div>'
                    if res["label_excerpt"] and res["in_label"]
                    else ""
                )
                st.markdown(
                    f"""
                    <div class="risk-card" style="border-left: 5px solid {border_color};">
                        <h3>💊 {res['drug']}
                            <span style="font-size: 0.95rem; color: {border_color}; float: right;">
                                {res['risk_level']}
                            </span>
                        </h3>
                        <div class="risk-meta">
                            <div><strong>FAERS 案件數：</strong>
                                <span style="color:#0891b2; font-size:1.15rem;">{max(res['event_count'], 0):,}</span> 筆
                            </div>
                            <div><strong>評估依據：</strong> {res['risk_reason']}</div>
                        </div>
                        {excerpt_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with tab2:
            target_drug = st.selectbox(
                "選擇藥品進行流行病學分析：",
                [r["drug"] for r in all_results],
                key="geo_drug",
            )
            if target_drug:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### 👤 通報者專業身份")
                    reporters = get_distribution_data(
                        target_drug, current_side_effect, "primarysource.qualification"
                    )
                    if reporters:
                        df_r = pd.DataFrame(reporters)
                        df_r["term"] = df_r["term"].astype(str).map(QUALIFICATION_MAP).fillna("未知")
                        fig_r = px.pie(
                            df_r, values="count", names="term",
                            template=PLOTLY_TEMPLATE, hole=0.4,
                        )
                        fig_r.update_layout(
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#0f172a"),
                        )
                        st.plotly_chart(fig_r, use_container_width=True)
                    else:
                        st.info("無足夠資料繪製通報者分佈。")
                with c2:
                    st.markdown("#### 🎯 主要處方適應症")
                    inds = get_distribution_data(
                        target_drug, current_side_effect, "patient.drug.drugindication.exact", 10
                    )
                    if inds:
                        df_ind = pd.DataFrame(inds)
                        fig_ind = px.bar(df_ind, x="term", y="count", template=PLOTLY_TEMPLATE)
                        fig_ind.update_layout(
                            xaxis_title="適應症",
                            yaxis_title="案件數",
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#0f172a"),
                        )
                        st.plotly_chart(fig_ind, use_container_width=True)
                    else:
                        st.info("無足夠資料繪製適應症分佈。")

        with tab3:
            st.markdown("### 💊 臨床案件劑量檢閱器 (Case Browser)")
            target_drug = st.selectbox(
                "選擇藥品載入案件：",
                [r["drug"] for r in all_results],
                key="case_drug",
            )
            case_limit = st.slider("選擇載入的近期案件數量：", 20, 200, 110, step=10)

            if st.button("📥 載入案件與劑量明細"):
                with st.spinner("正在解析 JSON 並萃取劑量與嚴重度指標..."):
                    raw_cases = get_detailed_events(
                        target_drug, current_side_effect, limit=case_limit
                    )
                    if raw_cases:
                        df_cases = parse_events_to_dataframe(raw_cases, target_drug)
                        st.session_state["df_cases"] = df_cases
                        st.session_state["cases_loaded_drug"] = target_drug
                    else:
                        st.warning("openFDA 沒有回傳案件，請更換藥品或縮短不良反應名稱再試。")

            if (
                "df_cases" in st.session_state
                and st.session_state.get("cases_loaded_drug") == target_drug
            ):
                df_cases: pd.DataFrame = st.session_state["df_cases"]

                serious_count = int(df_cases["嚴重度"].astype(str).str.startswith("嚴重").sum())
                m1, m2, m3 = st.columns(3)
                m1.metric("載入案件總數", f"{len(df_cases):,}")
                m2.metric("嚴重案件數", f"{serious_count:,}")
                m3.metric("非嚴重案件數", f"{len(df_cases) - serious_count:,}")

                st.success(
                    f"✅ 成功載入 {len(df_cases)} 筆案件紀錄！(下方表格為固定高度，可直接上下捲動)"
                )

                with st.expander("🔎 篩選條件", expanded=False):
                    f1, f2 = st.columns(2)
                    severity_filter = f1.multiselect(
                        "嚴重度",
                        sorted(df_cases["嚴重度"].dropna().unique().tolist()),
                        default=[],
                    )
                    reporter_filter = f2.multiselect(
                        "通報者身分",
                        sorted(df_cases["通報者身分"].dropna().unique().tolist()),
                        default=[],
                    )

                view_df = df_cases
                if severity_filter:
                    view_df = view_df[view_df["嚴重度"].isin(severity_filter)]
                if reporter_filter:
                    view_df = view_df[view_df["通報者身分"].isin(reporter_filter)]

                st.markdown(f"#### 📋 完整案件清單（{len(view_df):,} / {len(df_cases):,} 筆）")
                st.dataframe(
                    view_df[CASE_COLUMNS],
                    use_container_width=True,
                    height=600,
                    hide_index=True,
                )
            else:
                st.info("👆 請先選擇藥品並點擊「載入案件與劑量明細」以檢視案件清單。")

        with tab4:
            st.markdown("### 📤 匯出完整結構化資料")

            summary_df = _summary_dataframe(all_results)
            st.markdown("#### 🧾 分析摘要")
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

            csv_summary = summary_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📄 下載分析摘要 CSV",
                data=csv_summary,
                file_name=f"FAERS_Summary_{current_side_effect}.csv",
                mime="text/csv",
            )

            st.markdown("---")
            st.markdown("#### 📁 案件級明細")
            if "df_cases" in st.session_state:
                df_cases: pd.DataFrame = st.session_state["df_cases"]
                csv_cases = df_cases.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "📄 下載案件 CSV (相容 Excel 繁體中文)",
                    data=csv_cases,
                    file_name=f"FAERS_Cases_{st.session_state.get('cases_loaded_drug', 'data')}.csv",
                    mime="text/csv",
                )

                xlsx_buf = io.BytesIO()
                with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
                    summary_df.to_excel(writer, sheet_name="Summary", index=False)
                    df_cases.to_excel(writer, sheet_name="Cases", index=False)
                st.download_button(
                    "📊 下載完整 Excel (摘要 + 案件)",
                    data=xlsx_buf.getvalue(),
                    file_name=f"FAERS_Report_{current_side_effect}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.info("尚未載入案件級資料。請先至「💊 劑量與臨床案件檢閱」分頁載入。")

    else:
        st.markdown(
            """
            <div class="welcome-panel">
                <h2>👋 歡迎使用全球 ADR 智能監測系統</h2>
                <p>
                    本系統直接串接 <b>FDA FAERS API</b>，提供即時的藥物不良反應流行病學與劑量關聯性分析。<br><br>
                    👈 請先在<b>左側選單</b>輸入您想研究的藥品與不良反應 (例如：SGLT2 inhibitors 與 Heart failure)，
                    然後點擊<b>「執行深度分析」</b>。
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
