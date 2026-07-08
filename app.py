"""
====================================================
臨床藥物不良反應 (ADR) 智能監測儀表板
FDA FAERS Pharmacovigilance Analytics Platform
====================================================
Version: 5.0 (Signal Detection PRR/ROR · Trends · Geography · Demographics · Filters · API Key)
====================================================
"""

from __future__ import annotations

import io
import logging
import math
import re
from datetime import datetime, timedelta
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
    page_icon=":material/health_and_safety:",
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

    /* View switcher (segmented control) */
    [data-testid="stSegmentedControl"] button {
        font-weight: 600;
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

# FAERS reactionoutcome codes — see FDA E2B mapping
REACTION_OUTCOME_MAP = {
    "1": "已恢復/緩解",
    "2": "恢復中",
    "3": "未恢復",
    "4": "恢復伴後遺症",
    "5": "死亡",
    "6": "未知",
}

# E2B route of administration codes (openFDA drugadministrationroute)
ROUTE_MAP = {
    "030": "肌肉注射",
    "040": "靜脈推注",
    "041": "靜脈滴注",
    "042": "靜脈注射",
    "045": "鼻腔給藥",
    "047": "眼用",
    "048": "口服",
    "050": "其他",
    "054": "直腸給藥",
    "055": "吸入",
    "058": "皮下注射",
    "060": "舌下",
    "061": "局部外用",
    "062": "經皮",
    "065": "未知",
}

# E2B patientonsetageunit codes
AGE_UNIT_MAP = {
    "800": "十年",
    "801": "歲",
    "802": "個月",
    "803": "週",
    "804": "天",
    "805": "小時",
}

# E2B patientagegroup codes
AGE_GROUP_MAP = {
    "1": "新生兒",
    "2": "嬰兒",
    "3": "兒童",
    "4": "青少年",
    "5": "成人",
    "6": "老年",
}

SEX_MAP = {"0": "未知", "1": "男", "2": "女"}

# ISO 3166-1 alpha-2 → alpha-3，供 Plotly choropleth 使用（涵蓋 FAERS 主要通報國）
ISO2_TO_ISO3 = {
    "US": "USA", "JP": "JPN", "DE": "DEU", "FR": "FRA", "GB": "GBR",
    "CA": "CAN", "AU": "AUS", "IT": "ITA", "ES": "ESP", "BR": "BRA",
    "KR": "KOR", "TW": "TWN", "CN": "CHN", "IN": "IND", "MX": "MEX",
    "NL": "NLD", "CH": "CHE", "SE": "SWE", "BE": "BEL", "AT": "AUT",
    "DK": "DNK", "NO": "NOR", "FI": "FIN", "PL": "POL", "PT": "PRT",
    "GR": "GRC", "IE": "IRL", "CZ": "CZE", "HU": "HUN", "RO": "ROU",
    "RU": "RUS", "TR": "TUR", "IL": "ISR", "SA": "SAU", "AE": "ARE",
    "ZA": "ZAF", "EG": "EGY", "NG": "NGA", "AR": "ARG", "CL": "CHL",
    "CO": "COL", "PE": "PER", "VE": "VEN", "TH": "THA", "MY": "MYS",
    "SG": "SGP", "PH": "PHL", "ID": "IDN", "VN": "VNM", "HK": "HKG",
    "NZ": "NZL", "UA": "UKR", "SK": "SVK", "HR": "HRV", "RS": "SRB",
    "BG": "BGR", "LT": "LTU", "LV": "LVA", "EE": "EST", "SI": "SVN",
}

DATE_RANGE_OPTIONS = {
    "全部年份": None,
    "近 10 年": 10,
    "近 5 年": 5,
    "近 3 年": 3,
}

CASE_COLUMNS = [
    "安全報告 ID", "事件類型 (MedDRA PT)", "事件結果",
    "用藥劑量 (Dose)", "給藥途徑", "適應症",
    "嚴重度", "年齡", "性別", "通報國家", "通報者身分",
]


def _sanitize(value: str) -> str:
    """Escape characters that would break the openFDA Lucene query string."""
    return value.replace("\\", "").replace('"', "").strip()


@st.cache_resource(show_spinner=False)
def get_session() -> requests.Session:
    """Shared session — reuses TCP connections and honours openFDA 429 rate limits."""
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _drug_query_clause(terms: tuple[str, ...]) -> str:
    """Lucene clause matching any of the given product/generic names."""
    terms_str = " ".join(f'"{t}"' for t in terms)
    return f"patient.drug.medicinalproduct:({terms_str})"


def _reaction_clause(side_effect: str) -> str:
    return f'patient.reaction.reactionmeddrapt:"{_sanitize(side_effect)}"'


def _join_query(*clauses: str) -> str:
    """AND-join non-empty Lucene clauses."""
    return " AND ".join(c for c in clauses if c)


def _openfda_get(
    url: str, params: dict[str, Any], timeout: int = REQUEST_TIMEOUT
) -> requests.Response:
    """GET with the user's optional API key injected (raises the rate limit
    from 240/min/IP to 240/min/key + 120k/day)."""
    api_key = str(st.session_state.get("openfda_api_key", "") or "").strip()
    if api_key:
        params = {**params, "api_key": api_key}
    return get_session().get(url, params=params, timeout=timeout)


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-]+", "_", name).strip("_") or "data"


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
        response = _openfda_get(OPENFDA_LABEL_URL, {"search": query, "limit": 1})
        if response.status_code == 404:
            return False, "仿單中未找到明確關聯", []
        if response.status_code != 200:
            log.info("check_label_risk status=%s body=%s", response.status_code, response.text[:200])
            return False, "仿單查詢失敗", []
        results = response.json().get("results", [])
        if not results:
            return False, "仿單中未找到明確關聯", []
        data = results[0]
        generics = data.get("openfda", {}).get("generic_name", []) or []
        excerpt = ""
        if "boxed_warning" in data:
            excerpt = "黑框警告: " + data["boxed_warning"][0][:200] + "..."
        elif "warnings" in data:
            excerpt = "警告: " + data["warnings"][0][:200] + "..."
        elif "adverse_reactions" in data:
            excerpt = "不良反應: " + data["adverse_reactions"][0][:200] + "..."
        return True, excerpt, generics
    except requests.RequestException as exc:
        log.warning("check_label_risk failed for %s/%s: %s", drug, se, exc)
        return False, "連線錯誤", []


@st.cache_data(ttl=300, show_spinner=False)
def faers_total(search: str) -> int:
    """Total FAERS reports matching a Lucene query (empty = whole database).

    Returns -1 on connection/API failure so callers can distinguish
    「查無資料」from「查詢失敗」."""
    params: dict[str, Any] = {"limit": 1}
    if search:
        params["search"] = search
    try:
        response = _openfda_get(OPENFDA_EVENT_URL, params)
        if response.status_code == 200:
            return int(
                response.json().get("meta", {}).get("results", {}).get("total", 0)
            )
        if response.status_code == 404:
            return 0
        log.info("faers_total status=%s body=%s", response.status_code, response.text[:200])
        return -1
    except requests.RequestException as exc:
        log.warning("faers_total failed: %s", exc)
        return -1


def count_faers_events(
    input_name: str,
    side_effect: str,
    alias_list: list[str] | None = None,
    filters: str = "",
) -> tuple[int, list[str]]:
    aliases = alias_list or []
    terms = sorted({_sanitize(t) for t in [input_name, *aliases] if _sanitize(t)})
    if not terms:
        return 0, []
    query = _join_query(
        _drug_query_clause(tuple(terms)), _reaction_clause(side_effect), filters
    )
    return faers_total(query), terms


@st.cache_data(ttl=300, show_spinner=False)
def get_distribution_data(
    drug_terms: tuple[str, ...],
    side_effect: str,
    field_name: str,
    limit: int = 20,
    filters: str = "",
) -> list[dict[str, Any]]:
    terms = tuple(t for t in (_sanitize(t) for t in drug_terms) if t)
    se = _sanitize(side_effect)
    if not terms or not se:
        return []
    query = _join_query(_drug_query_clause(terms), _reaction_clause(se), filters)
    params: dict[str, Any] = {"search": query, "count": field_name}
    if limit:
        params["limit"] = limit
    try:
        response = _openfda_get(OPENFDA_EVENT_URL, params)
        if response.status_code == 200:
            return response.json().get("results", [])
        return []
    except requests.RequestException as exc:
        log.warning("get_distribution_data failed: %s", exc)
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_monthly_trend(
    drug_terms: tuple[str, ...], side_effect: str, filters: str = ""
) -> pd.DataFrame:
    """Monthly report counts via the receivedate histogram (count=receivedate
    returns the full daily time series; we aggregate to months)."""
    rows = get_distribution_data(drug_terms, side_effect, "receivedate", 0, filters)
    if not rows:
        return pd.DataFrame(columns=["月份", "案件數"])
    df = pd.DataFrame(rows)
    time_col = "time" if "time" in df.columns else "term"
    df["date"] = pd.to_datetime(df[time_col].astype(str), format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date"])
    monthly = (
        df.set_index("date")["count"].resample("MS").sum().reset_index()
    )
    monthly.columns = ["月份", "案件數"]
    return monthly


@st.cache_data(ttl=300, show_spinner=False)
def get_detailed_events(
    drug_terms: tuple[str, ...], side_effect: str, limit: int = 100, filters: str = ""
) -> list[dict[str, Any]]:
    """openFDA caps a single request at 100 records; page through with
    `skip` so the case browser can load up to 500 recent reports."""
    terms = tuple(t for t in (_sanitize(t) for t in drug_terms) if t)
    se = _sanitize(side_effect)
    if not terms or not se:
        return []
    query = _join_query(_drug_query_clause(terms), _reaction_clause(se), filters)
    events: list[dict[str, Any]] = []
    try:
        while len(events) < limit:
            batch = min(100, limit - len(events))
            response = _openfda_get(
                OPENFDA_EVENT_URL,
                # sort by receipt date so「近期案件」真的是最近通報的案件
                {
                    "search": query,
                    "limit": batch,
                    "skip": len(events),
                    "sort": "receiptdate:desc",
                },
                timeout=REQUEST_TIMEOUT + 5,
            )
            if response.status_code != 200:
                break
            results = response.json().get("results", [])
            events.extend(results)
            if len(results) < batch:  # exhausted
                break
    except requests.RequestException as exc:
        log.warning("get_detailed_events failed after %d records: %s", len(events), exc)
    return events


@st.cache_data(ttl=300, show_spinner=False)
def compute_signal_metrics(
    drug_terms: tuple[str, ...], side_effect: str, filters: str = ""
) -> dict[str, Any] | None:
    """Disproportionality analysis on the FAERS 2×2 contingency table.

                     目標反應    其他反應
        目標藥品        a           b
        其他藥品        c           d

    PRR  = (a/(a+b)) / (c/(c+d))
    ROR  = (a·d)/(b·c)，95% CI = exp(ln ROR ± 1.96·√(1/a+1/b+1/c+1/d))
    χ²   = Yates 校正卡方
    訊號判定採 EMA 標準：a ≥ 3 且 PRR ≥ 2 且 χ² ≥ 4。

    Returns None when any underlying count query fails.
    """
    terms = tuple(t for t in (_sanitize(t) for t in drug_terms) if t)
    se = _sanitize(side_effect)
    if not terms or not se:
        return None
    drug_q = _drug_query_clause(terms)
    react_q = _reaction_clause(se)

    a = faers_total(_join_query(drug_q, react_q, filters))
    n_drug = faers_total(_join_query(drug_q, filters))
    n_react = faers_total(_join_query(react_q, filters))
    n_all = faers_total(filters)
    if min(a, n_drug, n_react, n_all) < 0:
        return None

    b = max(n_drug - a, 0)
    c = max(n_react - a, 0)
    d = max(n_all - a - b - c, 0)
    result: dict[str, Any] = {
        "a": a, "b": b, "c": c, "d": d,
        "n_drug": n_drug, "n_react": n_react, "n_all": n_all,
        "prr": None, "ror": None, "ror_low": None, "ror_high": None,
        "chi2": None, "signal": False,
    }
    if a == 0 or (a + b) == 0 or (c + d) == 0:
        return result

    if c > 0:
        result["prr"] = (a / (a + b)) / (c / (c + d))

    # ROR：任一格為 0 時採 Haldane-Anscombe 0.5 校正
    aa, bb, cc, dd = (
        (a + 0.5, b + 0.5, c + 0.5, d + 0.5) if 0 in (a, b, c, d) else (a, b, c, d)
    )
    ror = (aa * dd) / (bb * cc)
    se_ln = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    result["ror"] = ror
    result["ror_low"] = math.exp(math.log(ror) - 1.96 * se_ln)
    result["ror_high"] = math.exp(math.log(ror) + 1.96 * se_ln)

    n = a + b + c + d
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    if denom > 0:
        result["chi2"] = n * (abs(a * d - b * c) - n / 2) ** 2 / denom

    result["signal"] = (
        a >= 3 and (result["prr"] or 0) >= 2 and (result["chi2"] or 0) >= 4
    )
    return result


def _format_age(patient: dict[str, Any]) -> str:
    age = patient.get("patientonsetage")
    if not age:
        return "N/A"
    unit = AGE_UNIT_MAP.get(str(patient.get("patientonsetageunit", "")), "")
    return f"{age} {unit}".strip()


def _match_drug_record(patient: dict[str, Any], term_uppers: list[str]) -> dict[str, Any] | None:
    """Find the drug record for the searched drug (by product or openFDA names),
    falling back to the first suspect drug (drugcharacterization == '1')."""
    drugs = patient.get("drug", []) or []
    for drug in drugs:
        names = [(drug.get("medicinalproduct") or "").upper()]
        openfda = drug.get("openfda", {}) or {}
        names += [n.upper() for n in (openfda.get("generic_name") or [])]
        names += [n.upper() for n in (openfda.get("brand_name") or [])]
        if any(term in name for term in term_uppers for name in names if name):
            return drug
    for drug in drugs:
        if drug.get("drugcharacterization") == "1":
            return drug
    return None


def parse_events_to_dataframe(
    events: list[dict[str, Any]],
    drug_terms: tuple[str, ...],
    target_reaction: str = "",
) -> pd.DataFrame:
    """Always returns a DataFrame containing every column in CASE_COLUMNS.

    Each FAERS report can carry multiple reactions; we expose the full set
    in ``事件類型 (MedDRA PT)`` (the searched-for term sorted to the front)
    and the per-reaction outcomes in ``事件結果``.
    """
    records: list[dict[str, Any]] = []
    term_uppers = [t.upper() for t in drug_terms if t]
    target_upper = target_reaction.strip().upper()

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
            record["年齡"] = _format_age(patient)
            record["性別"] = {"1": "男", "2": "女"}.get(str(patient.get("patientsex", "")), "未知")

            reactions = patient.get("reaction", []) or []
            pt_terms: list[str] = []
            outcomes: list[str] = []
            for r in reactions:
                pt = (r.get("reactionmeddrapt") or "").strip()
                if pt:
                    pt_terms.append(pt)
                outcome = REACTION_OUTCOME_MAP.get(r.get("reactionoutcome"), "")
                if outcome:
                    outcomes.append(outcome)
            if target_upper:
                # Move the searched-for reaction to the front so it's visible at a glance.
                pt_terms.sort(key=lambda t: 0 if t.upper() == target_upper else 1)
            if pt_terms:
                record["事件類型 (MedDRA PT)"] = "; ".join(dict.fromkeys(pt_terms))
            if outcomes:
                record["事件結果"] = "; ".join(dict.fromkeys(outcomes))

            drug = _match_drug_record(patient, term_uppers)
            if drug is not None:
                dose_text = drug.get("drugdosagetext") or ""
                if not dose_text:
                    cum_dose = drug.get("drugcumulativedosagenumb", "")
                    unit = drug.get("drugcumulativedosageunit", "")
                    dose_text = f"{cum_dose} {unit}".strip() if cum_dose else "未提供"
                record["用藥劑量 (Dose)"] = dose_text
                route = str(drug.get("drugadministrationroute") or "")
                record["給藥途徑"] = ROUTE_MAP.get(route, route or "N/A")
                record["適應症"] = drug.get("drugindication", "N/A")

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
                "FAERS 案件數": r["event_count"] if r["event_count"] >= 0 else None,
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
            <h1>全球 ADR 智能監測儀表板 (V5.0)</h1>
            <p>基於 FDA FAERS 數據的藥物警戒平台 ｜ PRR/ROR 訊號偵測 · 趨勢 · 地理 · 人口學分析</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### 查詢參數設定")
        drug_input = st.text_area(
            "藥品名稱 (可輸入多個，用逗號分隔)",
            value="Empagliflozin, Dapagliflozin",
            height=80,
        )
        side_effect = st.text_input("目標不良反應 (MedDRA PT)", value="Heart failure")
        st.markdown("---")
        st.markdown("### 資料範圍")
        date_range_label = st.selectbox("通報期間", list(DATE_RANGE_OPTIONS))
        serious_only = st.checkbox("僅統計嚴重案件", value=False,
                                   help="限定 serious=1（死亡、住院、失能、危及生命等）的通報")
        st.text_input(
            "openFDA API Key（選填）",
            type="password",
            key="openfda_api_key",
            help="至 open.fda.gov 免費申請，可將查詢額度自 240 次/分/IP 提高至 120,000 次/日",
        )
        st.markdown("---")
        st.markdown("### 風險閾值設定")
        high_threshold = st.number_input("高風險警示 (通報數 ≥)", min_value=1, value=500, step=100)
        medium_threshold = st.number_input("中風險警示 (通報數 ≥)", min_value=1, value=100, step=50)
        if medium_threshold > high_threshold:
            st.warning("中風險閾值高於高風險閾值，已自動以高風險閾值為上限。")
            medium_threshold = high_threshold

        analyze_btn = st.button("執行深度分析", icon=":material/query_stats:", width="stretch")
        if st.session_state.get("is_analyzed"):
            if st.button("重設分析", icon=":material/restart_alt:", width="stretch"):
                for key in (
                    "is_analyzed", "all_results", "current_side_effect",
                    "analyzed_at", "current_filters", "filters_desc", "df_signals",
                ):
                    st.session_state.pop(key, None)
                _reset_case_state()
                st.rerun()

    if analyze_btn:
        if not drug_input.strip() or not side_effect.strip():
            st.warning("請至少輸入一個藥品名稱與一個不良反應後再執行分析。")
            return

        drug_list = [d.strip() for d in drug_input.split(",") if d.strip()]

        # 全域查詢過濾條件（通報期間、嚴重度）——套用到所有 FAERS 查詢
        filter_parts: list[str] = []
        years = DATE_RANGE_OPTIONS[date_range_label]
        if years:
            start = datetime.now() - timedelta(days=365 * years)
            filter_parts.append(
                f"receivedate:[{start:%Y%m%d} TO {datetime.now():%Y%m%d}]"
            )
        if serious_only:
            filter_parts.append('serious:"1"')
        current_filters = _join_query(*filter_parts)
        filters_desc = date_range_label + ("｜僅嚴重案件" if serious_only else "")

        progress_bar = st.progress(0.0)
        status_text = st.empty()
        all_results: list[dict[str, Any]] = []

        for i, drug in enumerate(drug_list):
            status_text.markdown(f"正在分析: `{drug}` 關聯之 `{side_effect}`...")
            in_label, label_excerpt, generics = check_label_risk(drug, side_effect)
            event_count, used_terms = count_faers_events(
                drug, side_effect, generics, current_filters
            )

            if event_count < 0 and not in_label:
                risk_level, risk_reason = "查詢失敗", "FAERS 查詢失敗，無法評估（請稍後重試）"
            elif in_label:
                risk_level, risk_reason = "高風險", "已明確記載於 FDA 仿單"
            elif event_count >= high_threshold:
                risk_level, risk_reason = "高風險", f"FAERS 訊號強烈 ({event_count:,} 筆通報)"
            elif event_count >= medium_threshold:
                risk_level, risk_reason = "中風險", f"中度通報訊號 ({event_count:,} 筆通報)"
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
        st.session_state.pop("df_signals", None)
        st.session_state["is_analyzed"] = True
        st.session_state["all_results"] = all_results
        st.session_state["current_side_effect"] = side_effect
        st.session_state["current_filters"] = current_filters
        st.session_state["filters_desc"] = filters_desc
        st.session_state["analyzed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if st.session_state.get("is_analyzed"):
        all_results: list[dict[str, Any]] = st.session_state["all_results"]
        current_side_effect: str = st.session_state["current_side_effect"]
        current_filters: str = st.session_state.get("current_filters", "")
        analyzed_at: str = st.session_state.get("analyzed_at", "")
        # 各分頁查詢沿用摘要分析時的「商品名 + 學名」聯集，確保數字彼此一致
        drug_terms_map: dict[str, tuple[str, ...]] = {
            r["drug"]: tuple(r["used_terms"] or [r["drug"]]) for r in all_results
        }

        st.caption(
            f"分析時間：{analyzed_at} ｜ 不良反應目標：**{current_side_effect}** ｜ "
            f"分析藥品：{', '.join(r['drug'] for r in all_results)} ｜ "
            f"資料範圍：{st.session_state.get('filters_desc', '全部年份')}"
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

        # st.tabs 在每次 rerun（點按鈕、改篩選）後會跳回第一個分頁；
        # 改用綁定 session_state 的 segmented control 讓選取的面板跨 rerun 保留。
        views = [
            "風險與仿單評估", "訊號偵測 (PRR/ROR)", "流行病學分佈",
            "劑量與臨床案件檢閱", "匯出資料",
        ]
        view = st.segmented_control(
            "檢視面板",
            views,
            key="active_view",
            default=views[0],
            label_visibility="collapsed",
        ) or views[0]

        if view == "風險與仿單評估":
            for res in all_results:
                border_color = {
                    "高風險": "#b91c1c",
                    "中風險": "#ea580c",
                    "低風險": "#047857",
                }.get(res["risk_level"], "#64748b")
                count_display = (
                    f"{res['event_count']:,}" if res["event_count"] >= 0 else "—"
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
                        <h3>{res['drug']}
                            <span style="font-size: 0.95rem; color: {border_color}; float: right;">
                                {res['risk_level']}
                            </span>
                        </h3>
                        <div class="risk-meta">
                            <div><strong>FAERS 案件數：</strong>
                                <span style="color:#0891b2; font-size:1.15rem;">{count_display}</span> 筆
                            </div>
                            <div><strong>評估依據：</strong> {res['risk_reason']}</div>
                        </div>
                        {excerpt_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        elif view == "訊號偵測 (PRR/ROR)":
            st.markdown("### 不成比例分析 (Disproportionality Analysis)")
            with st.expander("方法說明", expanded=False, icon=":material/info:"):
                st.markdown(
                    """
以 FAERS 全資料庫為背景，對每個藥品建立 2×2 列聯表：

| | 目標反應 | 其他反應 |
|---|---|---|
| **目標藥品** | a | b |
| **其他藥品** | c | d |

- **PRR** (Proportional Reporting Ratio) = (a/(a+b)) / (c/(c+d))
- **ROR** (Reporting Odds Ratio) = (a·d)/(b·c)，附 95% 信賴區間
- **χ²**：Yates 校正卡方統計量
- **訊號判定**（EMA 標準）：a ≥ 3 且 PRR ≥ 2 且 χ² ≥ 4

分母使用目前分析所設定的資料範圍（期間／嚴重度）。FAERS 為自發通報系統，
不成比例訊號僅代表通報頻率異常，**不能推論因果關係**。
                    """
                )

            sig_rows: list[dict[str, Any]] = []
            plot_rows: list[dict[str, Any]] = []
            failed_drugs: list[str] = []
            with st.spinner("正在查詢列聯表並計算 PRR / ROR / χ² ..."):
                for res in all_results:
                    metrics = compute_signal_metrics(
                        drug_terms_map[res["drug"]], current_side_effect, current_filters
                    )
                    if metrics is None:
                        failed_drugs.append(res["drug"])
                        continue
                    sig_rows.append(
                        {
                            "藥品": res["drug"],
                            "目標反應案件 (a)": metrics["a"],
                            "藥品總通報": metrics["n_drug"],
                            "PRR": round(metrics["prr"], 2) if metrics["prr"] else None,
                            "ROR": round(metrics["ror"], 2) if metrics["ror"] else None,
                            "ROR 95% CI": (
                                f"{metrics['ror_low']:.2f} – {metrics['ror_high']:.2f}"
                                if metrics["ror"] else "—"
                            ),
                            "χ²": round(metrics["chi2"], 1) if metrics["chi2"] else None,
                            "訊號判定": "⬤ 偵測到訊號" if metrics["signal"] else "未達標準",
                        }
                    )
                    if metrics["ror"]:
                        plot_rows.append(
                            {
                                "藥品": res["drug"],
                                "ROR": metrics["ror"],
                                "err_plus": metrics["ror_high"] - metrics["ror"],
                                "err_minus": metrics["ror"] - metrics["ror_low"],
                                "訊號": "有訊號" if metrics["signal"] else "無訊號",
                            }
                        )

            if failed_drugs:
                st.warning(f"下列藥品的列聯表查詢失敗：{', '.join(failed_drugs)}（請稍後重試）")
            if sig_rows:
                df_signals = pd.DataFrame(sig_rows)
                st.session_state["df_signals"] = df_signals
                st.dataframe(df_signals, width="stretch", hide_index=True)

                if plot_rows:
                    st.markdown("#### ROR 森林圖（log 尺度，虛線 = 無關聯基準 ROR 1.0）")
                    df_plot = pd.DataFrame(plot_rows)
                    fig_forest = px.scatter(
                        df_plot,
                        x="ROR",
                        y="藥品",
                        color="訊號",
                        error_x="err_plus",
                        error_x_minus="err_minus",
                        log_x=True,
                        template=PLOTLY_TEMPLATE,
                        color_discrete_map={"有訊號": "#b91c1c", "無訊號": "#0891b2"},
                    )
                    fig_forest.add_vline(x=1, line_dash="dash", line_color="#64748b")
                    fig_forest.update_traces(marker=dict(size=12))
                    fig_forest.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#0f172a"),
                        height=max(240, 90 * len(df_plot) + 120),
                    )
                    st.plotly_chart(fig_forest, width="stretch")
            elif not failed_drugs:
                st.info("無足夠資料進行訊號偵測。")

        elif view == "流行病學分佈":
            st.markdown("#### 通報趨勢（每月案件數，各藥品疊加比較）")
            trend_frames: list[pd.DataFrame] = []
            with st.spinner("正在載入通報時間序列..."):
                for res in all_results:
                    trend = get_monthly_trend(
                        drug_terms_map[res["drug"]], current_side_effect, current_filters
                    )
                    if not trend.empty:
                        trend_frames.append(trend.assign(藥品=res["drug"]))
            if trend_frames:
                df_trend = pd.concat(trend_frames, ignore_index=True)
                fig_trend = px.line(
                    df_trend, x="月份", y="案件數", color="藥品",
                    template=PLOTLY_TEMPLATE,
                )
                fig_trend.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#0f172a"),
                )
                st.plotly_chart(fig_trend, width="stretch")
            else:
                st.info("無足夠資料繪製通報趨勢。")

            st.markdown("---")
            target_drug = st.selectbox(
                "選擇藥品進行流行病學分析：",
                [r["drug"] for r in all_results],
                key="geo_drug",
            )
            if target_drug:
                terms_sel = drug_terms_map[target_drug]

                st.markdown("#### 全球通報地理分佈")
                geo = get_distribution_data(
                    terms_sel, current_side_effect, "occurcountry.exact", 100, current_filters
                )
                if geo:
                    df_geo = pd.DataFrame(geo)
                    df_geo["term"] = df_geo["term"].astype(str).str.upper()
                    df_geo["iso3"] = df_geo["term"].map(ISO2_TO_ISO3)
                    df_geo["國家"] = df_geo["term"].map(COUNTRY_CODES).fillna(df_geo["term"])
                    g1, g2 = st.columns([3, 2])
                    with g1:
                        df_map = df_geo.dropna(subset=["iso3"])
                        if not df_map.empty:
                            fig_map = px.choropleth(
                                df_map,
                                locations="iso3",
                                color="count",
                                hover_name="國家",
                                color_continuous_scale="Blues",
                                template=PLOTLY_TEMPLATE,
                            )
                            fig_map.update_layout(
                                margin=dict(l=0, r=0, t=10, b=0),
                                paper_bgcolor="rgba(0,0,0,0)",
                                geo=dict(bgcolor="rgba(0,0,0,0)"),
                                coloraxis_colorbar_title_text="案件數",
                            )
                            st.plotly_chart(fig_map, width="stretch")
                    with g2:
                        df_top = df_geo.nlargest(15, "count")
                        fig_geo = px.bar(
                            df_top, x="count", y="國家", orientation="h",
                            template=PLOTLY_TEMPLATE,
                        )
                        fig_geo.update_layout(
                            xaxis_title="案件數", yaxis_title=None,
                            yaxis=dict(autorange="reversed"),
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#0f172a"),
                        )
                        st.plotly_chart(fig_geo, width="stretch")
                else:
                    st.info("無足夠資料繪製地理分佈。")

                d1, d2 = st.columns(2)
                with d1:
                    st.markdown("#### 患者性別分佈")
                    sexes = get_distribution_data(
                        terms_sel, current_side_effect, "patient.patientsex", 10, current_filters
                    )
                    if sexes:
                        df_sex = pd.DataFrame(sexes)
                        df_sex["term"] = df_sex["term"].astype(str).map(SEX_MAP).fillna("未知")
                        fig_sex = px.pie(
                            df_sex, values="count", names="term",
                            template=PLOTLY_TEMPLATE, hole=0.4,
                        )
                        fig_sex.update_layout(
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#0f172a"),
                        )
                        st.plotly_chart(fig_sex, width="stretch")
                    else:
                        st.info("無足夠資料繪製性別分佈。")
                with d2:
                    st.markdown("#### 患者年齡層分佈")
                    ages = get_distribution_data(
                        terms_sel, current_side_effect, "patient.patientagegroup", 10, current_filters
                    )
                    if ages:
                        df_age = pd.DataFrame(ages)
                        df_age["term"] = df_age["term"].astype(str)
                        df_age["年齡層"] = df_age["term"].map(AGE_GROUP_MAP).fillna("未知")
                        df_age = df_age.sort_values("term")
                        fig_age = px.bar(
                            df_age, x="年齡層", y="count", template=PLOTLY_TEMPLATE,
                        )
                        fig_age.update_layout(
                            xaxis_title=None, yaxis_title="案件數",
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#0f172a"),
                        )
                        st.plotly_chart(fig_age, width="stretch")
                    else:
                        st.info("無足夠資料繪製年齡層分佈。")

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### 通報者專業身份")
                    reporters = get_distribution_data(
                        drug_terms_map[target_drug], current_side_effect,
                        "primarysource.qualification", 20, current_filters,
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
                        st.plotly_chart(fig_r, width="stretch")
                    else:
                        st.info("無足夠資料繪製通報者分佈。")
                with c2:
                    st.markdown("#### 主要處方適應症")
                    inds = get_distribution_data(
                        drug_terms_map[target_drug], current_side_effect,
                        "patient.drug.drugindication.exact", 10, current_filters,
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
                        st.plotly_chart(fig_ind, width="stretch")
                    else:
                        st.info("無足夠資料繪製適應症分佈。")

                st.markdown("#### 共病反應 Top 10 (同案件並列出現的其他 MedDRA PT)")
                r1, r2 = st.columns(2)
                with r1:
                    st.markdown("#### 給藥途徑分佈")
                    routes = get_distribution_data(
                        terms_sel, current_side_effect,
                        "patient.drug.drugadministrationroute", 15, current_filters,
                    )
                    if routes:
                        df_route = pd.DataFrame(routes)
                        df_route["途徑"] = (
                            df_route["term"].astype(str).str.zfill(3)
                            .map(ROUTE_MAP)
                            .fillna(df_route["term"].astype(str))
                        )
                        fig_route = px.bar(
                            df_route.nlargest(10, "count"), x="途徑", y="count",
                            template=PLOTLY_TEMPLATE,
                        )
                        fig_route.update_layout(
                            xaxis_title=None, yaxis_title="案件數",
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#0f172a"),
                        )
                        st.plotly_chart(fig_route, width="stretch")
                    else:
                        st.info("無足夠資料繪製給藥途徑分佈。")
                with r2:
                    st.markdown("#### 反應結果分佈")
                    outcomes = get_distribution_data(
                        terms_sel, current_side_effect,
                        "patient.reaction.reactionoutcome", 10, current_filters,
                    )
                    if outcomes:
                        df_out = pd.DataFrame(outcomes)
                        df_out["結果"] = (
                            df_out["term"].astype(str).map(REACTION_OUTCOME_MAP).fillna("未知")
                        )
                        fig_out = px.pie(
                            df_out, values="count", names="結果",
                            template=PLOTLY_TEMPLATE, hole=0.4,
                        )
                        fig_out.update_layout(
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#0f172a"),
                        )
                        st.plotly_chart(fig_out, width="stretch")
                    else:
                        st.info("無足夠資料繪製反應結果分佈。")

                co_reactions = get_distribution_data(
                    drug_terms_map[target_drug], current_side_effect,
                    "patient.reaction.reactionmeddrapt.exact", 11, current_filters,
                )
                if co_reactions:
                    df_co = pd.DataFrame(co_reactions)
                    df_co = df_co[
                        df_co["term"].str.upper() != current_side_effect.strip().upper()
                    ].head(10)
                    if not df_co.empty:
                        fig_co = px.bar(
                            df_co, x="term", y="count", template=PLOTLY_TEMPLATE,
                        )
                        fig_co.update_layout(
                            xaxis_title="MedDRA PT",
                            yaxis_title="共現案件數",
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#0f172a"),
                        )
                        st.plotly_chart(fig_co, width="stretch")
                    else:
                        st.info("除目標反應外，其他共病訊號不足。")
                else:
                    st.info("無足夠資料繪製共病反應分佈。")

        elif view == "劑量與臨床案件檢閱":
            st.markdown("### 臨床案件劑量檢閱器 (Case Browser)")
            target_drug = st.selectbox(
                "選擇藥品載入案件：",
                [r["drug"] for r in all_results],
                key="case_drug",
            )
            case_limit = st.slider(
                "選擇載入的近期案件數量：", 20, 500, 100, step=20,
                help="超過 100 筆時會自動分頁抓取（openFDA 單次上限 100 筆）",
            )

            if st.button("載入案件與劑量明細", icon=":material/download:"):
                with st.spinner("正在解析 JSON 並萃取劑量與嚴重度指標..."):
                    raw_cases = get_detailed_events(
                        drug_terms_map[target_drug],
                        current_side_effect,
                        limit=case_limit,
                        filters=current_filters,
                    )
                    if raw_cases:
                        df_cases = parse_events_to_dataframe(
                            raw_cases,
                            drug_terms_map[target_drug],
                            target_reaction=current_side_effect,
                        )
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
                fatal_count = int(
                    df_cases["事件結果"].astype(str).str.contains("死亡", na=False).sum()
                )
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("載入案件總數", f"{len(df_cases):,}")
                m2.metric("嚴重案件數", f"{serious_count:,}")
                m3.metric("非嚴重案件數", f"{len(df_cases) - serious_count:,}")
                m4.metric("結果為死亡", f"{fatal_count:,}")

                st.success(
                    f"成功載入 {len(df_cases)} 筆案件紀錄。(下方表格為固定高度，可直接上下捲動)"
                )

                with st.expander("篩選條件", expanded=False, icon=":material/filter_alt:"):
                    f1, f2, f3 = st.columns(3)
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
                    reaction_keyword = f3.text_input(
                        "事件類型包含 (MedDRA PT)",
                        value="",
                        placeholder="例如 Ketoacidosis",
                    )

                view_df = df_cases
                if severity_filter:
                    view_df = view_df[view_df["嚴重度"].isin(severity_filter)]
                if reporter_filter:
                    view_df = view_df[view_df["通報者身分"].isin(reporter_filter)]
                if reaction_keyword.strip():
                    view_df = view_df[
                        view_df["事件類型 (MedDRA PT)"]
                        .astype(str)
                        .str.contains(reaction_keyword.strip(), case=False, na=False)
                    ]

                st.markdown(f"#### 完整案件清單（{len(view_df):,} / {len(df_cases):,} 筆）")
                st.dataframe(
                    view_df[CASE_COLUMNS],
                    width="stretch",
                    height=600,
                    hide_index=True,
                )
            else:
                st.info("請先選擇藥品並點擊「載入案件與劑量明細」以檢視案件清單。")

        elif view == "匯出資料":
            st.markdown("### 匯出完整結構化資料")

            summary_df = _summary_dataframe(all_results)
            st.markdown("#### 分析摘要")
            st.dataframe(summary_df, width="stretch", hide_index=True)

            csv_summary = summary_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "下載分析摘要 CSV",
                icon=":material/download:",
                data=csv_summary,
                file_name=f"FAERS_Summary_{_safe_filename(current_side_effect)}.csv",
                mime="text/csv",
            )

            if "df_signals" in st.session_state:
                st.markdown("#### 訊號偵測結果 (PRR/ROR)")
                df_signals: pd.DataFrame = st.session_state["df_signals"]
                st.dataframe(df_signals, width="stretch", hide_index=True)
                st.download_button(
                    "下載訊號偵測 CSV",
                    icon=":material/download:",
                    data=df_signals.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"FAERS_Signals_{_safe_filename(current_side_effect)}.csv",
                    mime="text/csv",
                )
            else:
                st.caption("提示：至「訊號偵測 (PRR/ROR)」面板計算後，可在此匯出訊號表。")

            st.markdown("---")
            st.markdown("#### 案件級明細")
            if "df_cases" in st.session_state:
                df_cases: pd.DataFrame = st.session_state["df_cases"]
                csv_cases = df_cases.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "下載案件 CSV (相容 Excel 繁體中文)",
                    icon=":material/download:",
                    data=csv_cases,
                    file_name=f"FAERS_Cases_{_safe_filename(st.session_state.get('cases_loaded_drug', 'data'))}.csv",
                    mime="text/csv",
                )

                xlsx_buf = io.BytesIO()
                with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
                    summary_df.to_excel(writer, sheet_name="Summary", index=False)
                    if "df_signals" in st.session_state:
                        st.session_state["df_signals"].to_excel(
                            writer, sheet_name="Signals", index=False
                        )
                    df_cases.to_excel(writer, sheet_name="Cases", index=False)
                st.download_button(
                    "下載完整 Excel (摘要 + 案件)",
                    icon=":material/table_view:",
                    data=xlsx_buf.getvalue(),
                    file_name=f"FAERS_Report_{_safe_filename(current_side_effect)}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.info("尚未載入案件級資料。請先至「劑量與臨床案件檢閱」面板載入。")

    else:
        st.markdown(
            """
            <div class="welcome-panel">
                <h2>歡迎使用全球 ADR 智能監測系統</h2>
                <p>
                    本系統直接串接 <b>FDA FAERS API</b>，提供即時的藥物不良反應流行病學與劑量關聯性分析。<br><br>
                    請先在<b>左側選單</b>輸入您想研究的藥品與不良反應 (例如：SGLT2 inhibitors 與 Heart failure)，
                    然後點擊<b>「執行深度分析」</b>。
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
