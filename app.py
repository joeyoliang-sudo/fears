"""
====================================================
🏥 Global ADR Intelligence Dashboard
FDA FAERS Style Pharmacovigilance Analytics Platform
====================================================
Version: 2.0
Author: Clinical Pharmacy Intelligence System
====================================================
"""

import streamlit as st
import requests
import pandas as pd
import time
import io
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# Page Configuration
# ==========================================
st.set_page_config(
    page_title="Global ADR Intelligence Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# Custom Styling - FDA/Clinical Dashboard Theme
# ==========================================
st.markdown("""
<style>
    /* Import Professional Fonts */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
    
    /* Root Variables - FDA Blue Theme */
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
        --text-primary: #e6f1ff;
        --text-secondary: #8ba3c7;
        --border-color: #1e4976;
    }
    
    /* Global Styles */
    .stApp {
        background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
        font-family: 'IBM Plex Sans', sans-serif;
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
    
    .main-header h1 {
        color: white;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .main-header p {
        color: rgba(255, 255, 255, 0.85);
        margin: 0.5rem 0 0 0;
        font-size: 0.95rem;
    }
    
    /* Metric Cards */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        border-color: var(--fda-accent);
        box-shadow: 0 8px 25px rgba(2, 191, 231, 0.15);
    }
    
    .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--fda-accent);
        margin: 0;
    }
    
    .metric-label {
        color: var(--text-secondary);
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.5rem;
    }
    
    /* Risk Level Badges */
    .risk-high {
        background: linear-gradient(135deg, #d62828 0%, #9d0208 100%);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    
    .risk-medium {
        background: linear-gradient(135deg, #ff6b35 0%, #f77f00 100%);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    
    .risk-low {
        background: linear-gradient(135deg, #2a9d8f 0%, #264653 100%);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    
    /* Data Cards */
    .data-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .data-card:hover {
        border-color: var(--fda-light-blue);
    }
    
    .data-card h3 {
        color: var(--text-primary);
        font-size: 1.1rem;
        margin: 0 0 1rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--border-color);
    }
    
    /* Result Row */
    .result-row {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .result-row:hover {
        border-color: var(--fda-accent);
        box-shadow: 0 4px 20px rgba(2, 191, 231, 0.1);
    }
    
    .result-row.high-risk {
        border-left: 4px solid var(--danger-red);
    }
    
    .result-row.medium-risk {
        border-left: 4px solid var(--warning-orange);
    }
    
    .result-row.low-risk {
        border-left: 4px solid var(--safe-green);
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border-color);
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: var(--text-primary);
    }
    
    /* Button Styling */
    .stButton > button {
        background: linear-gradient(90deg, var(--fda-light-blue) 0%, var(--fda-accent) 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(2, 191, 231, 0.4);
    }
    
    /* Input Fields */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        color: var(--text-primary);
        border-radius: 8px;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        color: var(--text-primary);
    }
    
    /* Table Styling */
    .dataframe {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: var(--bg-secondary);
        padding: 0.5rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: var(--text-secondary);
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--fda-light-blue);
        color: white;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, var(--fda-light-blue) 0%, var(--fda-accent) 100%);
    }
    
    /* Alerts */
    .stAlert {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 8px;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-primary);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--border-color);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--fda-light-blue);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# API Configuration
# ==========================================
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
OPENFDA_EVENT_URL = "https://api.fda.gov/drug/event.json"

# Country codes for reporter analysis
COUNTRY_CODES = {
    "US": "United States", "JP": "Japan", "DE": "Germany", "FR": "France",
    "GB": "United Kingdom", "CA": "Canada", "AU": "Australia", "IT": "Italy",
    "ES": "Spain", "BR": "Brazil", "KR": "South Korea", "TW": "Taiwan",
    "CN": "China", "IN": "India", "MX": "Mexico", "NL": "Netherlands",
    "BE": "Belgium", "SE": "Sweden", "CH": "Switzerland", "AT": "Austria"
}

# ==========================================
# Helper Functions
# ==========================================
def get_session():
    """Create a requests session with retry logic"""
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

@st.cache_data(ttl=300)
def check_label_risk(drug_name, side_effect):
    """
    Tier 1: Check FDA Drug Labels for documented ADRs
    Returns: (found: bool, excerpt: str, generics: list)
    """
    query = f'(openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}") AND (adverse_reactions:"{side_effect}" OR warnings:"{side_effect}" OR boxed_warning:"{side_effect}")'
    
    params = {"search": query, "limit": 1}
    found_generics = []
    
    try:
        session = get_session()
        response = session.get(OPENFDA_LABEL_URL, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])[0]
            
            if 'openfda' in results:
                found_generics = results['openfda'].get('generic_name', [])
            
            excerpt = ""
            if 'boxed_warning' in results:
                excerpt = "⚠️ BOXED WARNING: " + results['boxed_warning'][0][:200] + "..."
            elif 'warnings' in results:
                excerpt = "Warnings: " + results['warnings'][0][:200] + "..."
            elif 'adverse_reactions' in results:
                excerpt = "Adverse Reactions: " + results['adverse_reactions'][0][:200] + "..."
            
            return True, excerpt, found_generics
            
        elif response.status_code == 404:
            return False, "Not documented in label", []
        else:
            return False, f"API Error: {response.status_code}", []
            
    except Exception as e:
        return False, f"Connection Error: {str(e)}", []

@st.cache_data(ttl=300)
def count_faers_events(input_name, side_effect, alias_list=None):
    """
    Tier 2: Count FAERS adverse event reports
    """
    if alias_list is None:
        alias_list = []
    
    search_terms = set([input_name] + alias_list)
    terms_str = " ".join([f'"{term}"' for term in search_terms if term])
    
    query = f'patient.drug.medicinalproduct:({terms_str}) AND patient.reaction.reactionmeddrapt:"{side_effect}"'
    
    params = {"search": query, "limit": 1}
    
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            total_count = data.get('meta', {}).get('results', {}).get('total', 0)
            return total_count, list(search_terms)
        elif response.status_code == 404:
            return 0, list(search_terms)
        else:
            return -1, []
    except Exception as e:
        return -1, []

@st.cache_data(ttl=300)
def get_detailed_events(drug_name, side_effect, limit=100):
    """
    Fetch detailed FAERS event data including dose, route, reporter country
    """
    query = f'patient.drug.medicinalproduct:"{drug_name}" AND patient.reaction.reactionmeddrapt:"{side_effect}"'
    
    params = {"search": query, "limit": limit}
    
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params=params, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        else:
            return []
    except:
        return []

@st.cache_data(ttl=300)
def get_country_distribution(drug_name, side_effect):
    """Get ADR reports distribution by country"""
    query = f'patient.drug.medicinalproduct:"{drug_name}" AND patient.reaction.reactionmeddrapt:"{side_effect}"'
    
    params = {
        "search": query,
        "count": "occurcountry"
    }
    
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            return results
        return []
    except:
        return []

@st.cache_data(ttl=300)
def get_time_trend(drug_name, side_effect):
    """Get ADR reports trend over time"""
    query = f'patient.drug.medicinalproduct:"{drug_name}" AND patient.reaction.reactionmeddrapt:"{side_effect}"'
    
    params = {
        "search": query,
        "count": "receivedate"
    }
    
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        return []
    except:
        return []

@st.cache_data(ttl=300)
def get_dose_distribution(drug_name, side_effect):
    """Get dose information from reports"""
    query = f'patient.drug.medicinalproduct:"{drug_name}" AND patient.reaction.reactionmeddrapt:"{side_effect}"'
    
    params = {
        "search": query,
        "count": "patient.drug.drugdosagetext.exact",
        "limit": 20
    }
    
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        return []
    except:
        return []

@st.cache_data(ttl=300)
def get_reporter_qualification(drug_name, side_effect):
    """Get reporter qualification distribution (healthcare professionals vs consumers)"""
    query = f'patient.drug.medicinalproduct:"{drug_name}" AND patient.reaction.reactionmeddrapt:"{side_effect}"'
    
    params = {
        "search": query,
        "count": "primarysource.qualification"
    }
    
    # Qualification codes: 1=Physician, 2=Pharmacist, 3=Other HP, 4=Lawyer, 5=Consumer
    qualification_map = {
        "1": "Physician",
        "2": "Pharmacist", 
        "3": "Other Healthcare Professional",
        "4": "Lawyer",
        "5": "Consumer/Non-HP"
    }
    
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            mapped_results = []
            for r in results:
                term = qualification_map.get(str(r['term']), f"Unknown ({r['term']})")
                mapped_results.append({"term": term, "count": r['count']})
            return mapped_results
        return []
    except:
        return []

@st.cache_data(ttl=300)
def get_route_distribution(drug_name, side_effect):
    """Get administration route distribution"""
    query = f'patient.drug.medicinalproduct:"{drug_name}" AND patient.reaction.reactionmeddrapt:"{side_effect}"'
    
    params = {
        "search": query,
        "count": "patient.drug.drugadministrationroute",
        "limit": 15
    }
    
    # Route codes mapping
    route_map = {
        "001": "Auricular", "002": "Buccal", "003": "Cutaneous", "004": "Dental",
        "005": "Endocervical", "006": "Endosinusial", "007": "Endotracheal",
        "008": "Epidural", "009": "Extra-amniotic", "010": "Hemodialysis",
        "011": "Intra corpus cavernosum", "012": "Intra-amniotic", "013": "Intra-arterial",
        "014": "Intra-articular", "015": "Intra-uterine", "016": "Intracardiac",
        "017": "Intracavernous", "018": "Intracerebral", "019": "Intracervical",
        "020": "Intracisternal", "021": "Intracorneal", "022": "Intracoronary",
        "023": "Intradermal", "024": "Intradiscal", "025": "Intrahepatic",
        "026": "Intralesional", "027": "Intralymphatic", "028": "Intramedullar",
        "029": "Intrameningeal", "030": "Intramuscular", "031": "Intraocular",
        "032": "Intrapericardial", "033": "Intraperitoneal", "034": "Intrapleural",
        "035": "Intrasynovial", "036": "Intrathecal", "037": "Intrathoracic",
        "038": "Intratracheal", "039": "Intratumor", "040": "Intra-uterine",
        "041": "Intravenous bolus", "042": "Intravenous drip", "043": "Intravenous",
        "044": "Intravesical", "045": "Iontophoresis", "046": "Nasal",
        "047": "Occlusive dressing technique", "048": "Ophthalmic", "049": "Oral",
        "050": "Oropharyngeal", "051": "Other", "052": "Parenteral",
        "053": "Periarticular", "054": "Perineural", "055": "Rectal",
        "056": "Respiratory", "057": "Retrobulbar", "058": "Sunconjunctival",
        "059": "Subcutaneous", "060": "Subdermal", "061": "Sublingual",
        "062": "Topical", "063": "Transdermal", "064": "Transmammary",
        "065": "Transplacental", "066": "Unknown", "067": "Urethral",
        "068": "Vaginal"
    }
    
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            mapped_results = []
            for r in results:
                term = route_map.get(str(r['term']).zfill(3), f"Code {r['term']}")
                mapped_results.append({"term": term, "count": r['count']})
            return mapped_results
        return []
    except:
        return []

@st.cache_data(ttl=300)
def get_outcome_distribution(drug_name, side_effect):
    """Get patient outcome distribution"""
    query = f'patient.drug.medicinalproduct:"{drug_name}" AND patient.reaction.reactionmeddrapt:"{side_effect}"'
    
    params = {
        "search": query,
        "count": "serious"
    }
    
    try:
        session = get_session()
        response = session.get(OPENFDA_EVENT_URL, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            mapped = []
            for r in results:
                term = "Serious" if r['term'] == 1 else "Non-Serious"
                mapped.append({"term": term, "count": r['count']})
            return mapped
        return []
    except:
        return []

def parse_events_to_dataframe(events, drug_name):
    """Parse FAERS events into a structured DataFrame for export"""
    records = []
    
    for event in events:
        try:
            # Basic event info
            record = {
                "Safety Report ID": event.get('safetyreportid', 'N/A'),
                "Receive Date": event.get('receivedate', 'N/A'),
                "Report Type": event.get('reporttype', 'N/A'),
                "Serious": "Yes" if event.get('serious') == '1' else "No",
                "Reporter Country": event.get('occurcountry', 'N/A'),
            }
            
            # Patient info
            patient = event.get('patient', {})
            record["Patient Age"] = patient.get('patientonsetage', 'N/A')
            record["Patient Sex"] = {"1": "Male", "2": "Female"}.get(patient.get('patientsex'), 'N/A')
            
            # Drug info
            drugs = patient.get('drug', [])
            for drug in drugs:
                if drug_name.upper() in drug.get('medicinalproduct', '').upper():
                    record["Drug Name"] = drug.get('medicinalproduct', 'N/A')
                    record["Dose"] = drug.get('drugdosagetext', 'N/A')
                    record["Route"] = drug.get('drugadministrationroute', 'N/A')
                    record["Indication"] = drug.get('drugindication', 'N/A')
                    record["Drug Role"] = {
                        "1": "Suspect", "2": "Concomitant", "3": "Interacting"
                    }.get(drug.get('drugcharacterization'), 'N/A')
                    break
            
            # Reactions
            reactions = patient.get('reaction', [])
            record["Reactions"] = "; ".join([r.get('reactionmeddrapt', '') for r in reactions])
            
            # Reporter qualification
            primary_source = event.get('primarysource', {})
            qual_map = {"1": "Physician", "2": "Pharmacist", "3": "Other HP", "4": "Lawyer", "5": "Consumer"}
            record["Reporter Type"] = qual_map.get(primary_source.get('qualification'), 'N/A')
            
            records.append(record)
            
        except Exception as e:
            continue
    
    return pd.DataFrame(records)

# ==========================================
# Main Application
# ==========================================
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏥 Global ADR Intelligence Dashboard</h1>
        <p>FDA FAERS Pharmacovigilance Analytics Platform • Real-time Adverse Drug Reaction Monitoring</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🔬 Analysis Parameters")
        
        # Drug Input
        drug_input = st.text_area(
            "💊 Drug Names (comma-separated)",
            value="Zoloft, Lexapro, Prozac",
            height=80,
            help="Enter brand or generic names"
        )
        
        # ADR Input
        side_effect = st.text_input(
            "🎯 Adverse Reaction (MedDRA term)",
            value="Nausea",
            help="Use standard MedDRA preferred terms"
        )
        
        # Common ADRs quick select
        common_adrs = st.selectbox(
            "Quick Select Common ADRs",
            ["Custom...", "Nausea", "Headache", "Dizziness", "Fatigue", "Diarrhea",
             "Insomnia", "Weight gain", "Anxiety", "Depression", "Rash",
             "QT prolongation", "Hepatotoxicity", "Nephrotoxicity", "Bleeding"]
        )
        
        if common_adrs != "Custom...":
            side_effect = common_adrs
        
        st.markdown("---")
        
        # Threshold settings
        st.markdown("### ⚙️ Risk Thresholds")
        high_threshold = st.number_input("🔴 High Risk (reports ≥)", value=1000, step=100)
        medium_threshold = st.number_input("🟠 Medium Risk (reports ≥)", value=100, step=50)
        
        st.markdown("---")
        
        # Analysis button
        analyze_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)
        
        st.markdown("---")
        
        # Info
        st.markdown("""
        ### ℹ️ About
        This dashboard queries the **FDA FAERS** database to provide:
        - Label-based risk assessment
        - Global ADR signal detection
        - Reporter demographics
        - Dose-response patterns
        - Exportable case reports
        
        **Data Source**: openFDA API
        """)
    
    # Main content area
    if analyze_btn and drug_input and side_effect:
        drug_list = [d.strip() for d in drug_input.split(',') if d.strip()]
        
        # Progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_results = []
        
        # Analyze each drug
        for i, drug in enumerate(drug_list):
            status_text.markdown(f"**Analyzing:** `{drug}` for `{side_effect}`...")
            progress_bar.progress((i + 1) / len(drug_list))
            
            # Tier 1: Label check
            in_label, label_excerpt, generics = check_label_risk(drug, side_effect)
            
            time.sleep(0.3)  # Rate limiting
            
            # Tier 2: FAERS count
            event_count, used_terms = count_faers_events(drug, side_effect, generics)
            
            # Determine risk level
            if in_label:
                risk_level = "HIGH"
                risk_reason = "Documented in FDA Label"
            elif event_count >= high_threshold:
                risk_level = "HIGH"
                risk_reason = f"High signal in FAERS ({event_count:,} reports)"
            elif event_count >= medium_threshold:
                risk_level = "MEDIUM"
                risk_reason = f"Moderate signal ({event_count:,} reports)"
            else:
                risk_level = "LOW"
                risk_reason = "Low signal / Not documented"
            
            all_results.append({
                "drug": drug,
                "in_label": in_label,
                "label_excerpt": label_excerpt,
                "generics": generics,
                "event_count": event_count,
                "used_terms": used_terms,
                "risk_level": risk_level,
                "risk_reason": risk_reason
            })
        
        progress_bar.empty()
        status_text.empty()
        
        # Store results in session state
        st.session_state['analysis_results'] = all_results
        st.session_state['side_effect'] = side_effect
    
    # Display results if available
    if 'analysis_results' in st.session_state:
        results = st.session_state['analysis_results']
        side_effect = st.session_state['side_effect']
        
        # Summary Metrics Row
        st.markdown("### 📊 Analysis Summary")
        
        total_drugs = len(results)
        high_risk = sum(1 for r in results if r['risk_level'] == 'HIGH')
        medium_risk = sum(1 for r in results if r['risk_level'] == 'MEDIUM')
        total_reports = sum(r['event_count'] for r in results if r['event_count'] > 0)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <p class="metric-value">{total_drugs}</p>
                <p class="metric-label">Drugs Analyzed</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <p class="metric-value" style="color: #d62828;">{high_risk}</p>
                <p class="metric-label">High Risk Signals</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <p class="metric-value" style="color: #ff6b35;">{medium_risk}</p>
                <p class="metric-label">Medium Risk</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <p class="metric-value">{total_reports:,}</p>
                <p class="metric-label">Total FAERS Reports</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Risk Assessment", 
            "🌍 Geographic Analysis", 
            "📈 Trend & Demographics",
            "📤 Export Data"
        ])
        
        with tab1:
            st.markdown(f"### Risk Assessment for: `{side_effect}`")
            
            for res in results:
                risk_class = f"{res['risk_level'].lower()}-risk"
                risk_badge_class = f"risk-{res['risk_level'].lower()}"
                
                st.markdown(f"""
                <div class="result-row {risk_class}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <div>
                            <h3 style="margin: 0; color: #e6f1ff; font-size: 1.3rem;">💊 {res['drug']}</h3>
                            <span style="color: #8ba3c7; font-size: 0.85rem;">
                                Search terms: {', '.join(res['used_terms'][:3])}{'...' if len(res['used_terms']) > 3 else ''}
                            </span>
                        </div>
                        <span class="{risk_badge_class}">{res['risk_level']} RISK</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                        <div style="background: rgba(0,0,0,0.2); padding: 0.75rem; border-radius: 6px;">
                            <strong style="color: #8ba3c7;">📋 Label Status:</strong><br>
                            <span style="color: {'#2a9d8f' if res['in_label'] else '#ff6b35'};">
                                {'✅ Documented' if res['in_label'] else '❌ Not in Label'}
                            </span>
                        </div>
                        <div style="background: rgba(0,0,0,0.2); padding: 0.75rem; border-radius: 6px;">
                            <strong style="color: #8ba3c7;">📊 FAERS Reports:</strong><br>
                            <span style="color: #02bfe7; font-family: 'IBM Plex Mono', monospace; font-size: 1.1rem;">
                                {res['event_count']:,} cases
                            </span>
                        </div>
                    </div>
                    <div style="color: #8ba3c7; font-size: 0.9rem;">
                        <strong>Assessment:</strong> {res['risk_reason']}
                    </div>
                    {f'<div style="margin-top: 0.75rem; padding: 0.75rem; background: rgba(214, 40, 40, 0.1); border-radius: 6px; border-left: 3px solid #d62828; font-size: 0.85rem; color: #e6f1ff;">{res["label_excerpt"]}</div>' if res['in_label'] else ''}
                </div>
                """, unsafe_allow_html=True)
            
            # Summary table
            with st.expander("📊 View Summary Table"):
                summary_df = pd.DataFrame([{
                    "Drug": r['drug'],
                    "Risk Level": r['risk_level'],
                    "In Label": "Yes" if r['in_label'] else "No",
                    "FAERS Count": r['event_count'],
                    "Reason": r['risk_reason']
                } for r in results])
                st.dataframe(summary_df, use_container_width=True)
        
        with tab2:
            st.markdown("### 🌍 Geographic Distribution of Reports")
            
            # Drug selector for detailed analysis
            selected_drug = st.selectbox(
                "Select drug for detailed geographic analysis:",
                [r['drug'] for r in results]
            )
            
            if selected_drug:
                with st.spinner("Fetching geographic data..."):
                    country_data = get_country_distribution(selected_drug, side_effect)
                
                if country_data:
                    # Prepare data
                    country_df = pd.DataFrame(country_data)
                    country_df.columns = ['Country Code', 'Reports']
                    country_df['Country'] = country_df['Country Code'].map(
                        lambda x: COUNTRY_CODES.get(x, x)
                    )
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # World map
                        fig_map = px.choropleth(
                            country_df,
                            locations='Country Code',
                            locationmode='ISO-3',
                            color='Reports',
                            hover_name='Country',
                            color_continuous_scale='Blues',
                            title=f'Global ADR Reports: {selected_drug} → {side_effect}'
                        )
                        fig_map.update_layout(
                            geo=dict(
                                showframe=False,
                                showcoastlines=True,
                                projection_type='equirectangular',
                                bgcolor='rgba(0,0,0,0)'
                            ),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#e6f1ff'),
                            margin=dict(l=0, r=0, t=40, b=0)
                        )
                        st.plotly_chart(fig_map, use_container_width=True)
                    
                    with col2:
                        # Top countries bar chart
                        fig_bar = px.bar(
                            country_df.head(10),
                            x='Reports',
                            y='Country',
                            orientation='h',
                            title='Top 10 Reporting Countries',
                            color='Reports',
                            color_continuous_scale='Blues'
                        )
                        fig_bar.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#e6f1ff'),
                            yaxis=dict(categoryorder='total ascending'),
                            showlegend=False
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)
                    
                    # Data table
                    with st.expander("View All Country Data"):
                        st.dataframe(country_df[['Country', 'Country Code', 'Reports']], 
                                   use_container_width=True)
                else:
                    st.info("No geographic data available for this combination.")
        
        with tab3:
            st.markdown("### 📈 Trends & Demographics Analysis")
            
            selected_drug_trend = st.selectbox(
                "Select drug for trend analysis:",
                [r['drug'] for r in results],
                key="trend_drug"
            )
            
            if selected_drug_trend:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Reporter qualification
                    with st.spinner("Loading reporter data..."):
                        reporter_data = get_reporter_qualification(selected_drug_trend, side_effect)
                    
                    if reporter_data:
                        reporter_df = pd.DataFrame(reporter_data)
                        fig_pie = px.pie(
                            reporter_df,
                            values='count',
                            names='term',
                            title='Reporter Qualification',
                            color_discrete_sequence=px.colors.sequential.Blues_r
                        )
                        fig_pie.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#e6f1ff'),
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                        
                        # Healthcare professional percentage
                        hp_count = sum(r['count'] for r in reporter_data if 'Physician' in r['term'] or 'Pharmacist' in r['term'] or 'Healthcare' in r['term'])
                        total_count = sum(r['count'] for r in reporter_data)
                        hp_pct = (hp_count / total_count * 100) if total_count > 0 else 0
                        
                        st.metric("Healthcare Professional Reports", f"{hp_pct:.1f}%")
                
                with col2:
                    # Route distribution
                    with st.spinner("Loading route data..."):
                        route_data = get_route_distribution(selected_drug_trend, side_effect)
                    
                    if route_data:
                        route_df = pd.DataFrame(route_data)
                        fig_route = px.bar(
                            route_df.head(8),
                            x='count',
                            y='term',
                            orientation='h',
                            title='Administration Routes',
                            color='count',
                            color_continuous_scale='Viridis'
                        )
                        fig_route.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#e6f1ff'),
                            yaxis=dict(categoryorder='total ascending'),
                            showlegend=False
                        )
                        st.plotly_chart(fig_route, use_container_width=True)
                
                # Time trend
                st.markdown("#### 📅 Reporting Trend Over Time")
                with st.spinner("Loading time trend..."):
                    time_data = get_time_trend(selected_drug_trend, side_effect)
                
                if time_data:
                    time_df = pd.DataFrame(time_data)
                    time_df['time'] = pd.to_datetime(time_df['time'], format='%Y%m%d')
                    time_df = time_df.set_index('time').resample('M').sum().reset_index()
                    
                    fig_time = px.area(
                        time_df,
                        x='time',
                        y='count',
                        title=f'Monthly ADR Reports: {selected_drug_trend} → {side_effect}',
                    )
                    fig_time.update_traces(
                        fill='tozeroy',
                        line_color='#02bfe7',
                        fillcolor='rgba(2, 191, 231, 0.3)'
                    )
                    fig_time.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#e6f1ff'),
                        xaxis_title="Date",
                        yaxis_title="Number of Reports"
                    )
                    st.plotly_chart(fig_time, use_container_width=True)
                
                # Dose distribution
                st.markdown("#### 💊 Dose Distribution")
                with st.spinner("Loading dose data..."):
                    dose_data = get_dose_distribution(selected_drug_trend, side_effect)
                
                if dose_data:
                    dose_df = pd.DataFrame(dose_data)
                    dose_df.columns = ['Dosage', 'Count']
                    st.dataframe(dose_df.head(15), use_container_width=True)
                else:
                    st.info("Dose information not available in FAERS data.")
        
        with tab4:
            st.markdown("### 📤 Export Case-Level Data")
            
            export_drug = st.selectbox(
                "Select drug for case export:",
                [r['drug'] for r in results],
                key="export_drug"
            )
            
            export_limit = st.slider("Number of cases to export:", 10, 500, 100, step=10)
            
            if st.button("📥 Fetch & Prepare Export Data", type="secondary"):
                with st.spinner(f"Fetching {export_limit} case reports..."):
                    events = get_detailed_events(export_drug, side_effect, limit=export_limit)
                
                if events:
                    export_df = parse_events_to_dataframe(events, export_drug)
                    st.session_state['export_df'] = export_df
                    st.session_state['export_drug'] = export_drug
                    st.success(f"✅ Loaded {len(export_df)} case reports!")
            
            if 'export_df' in st.session_state:
                export_df = st.session_state['export_df']
                export_drug = st.session_state['export_drug']
                
                st.markdown(f"**Preview:** {len(export_df)} cases for `{export_drug}` → `{side_effect}`")
                st.dataframe(export_df.head(10), use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # CSV Export
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv,
                        file_name=f"FAERS_{export_drug}_{side_effect}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Excel Export
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        export_df.to_excel(writer, index=False, sheet_name='FAERS_Cases')
                    
                    st.download_button(
                        label="📊 Download Excel",
                        data=buffer.getvalue(),
                        file_name=f"FAERS_{export_drug}_{side_effect}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
                with col3:
                    # JSON Export
                    json_data = export_df.to_json(orient='records', indent=2)
                    st.download_button(
                        label="🔧 Download JSON",
                        data=json_data,
                        file_name=f"FAERS_{export_drug}_{side_effect}_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                # Statistics
                st.markdown("#### 📊 Export Data Statistics")
                
                stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                
                with stat_col1:
                    serious_count = (export_df['Serious'] == 'Yes').sum()
                    st.metric("Serious Cases", f"{serious_count} ({serious_count/len(export_df)*100:.1f}%)")
                
                with stat_col2:
                    hp_count = export_df['Reporter Type'].isin(['Physician', 'Pharmacist', 'Other Healthcare Professional']).sum()
                    st.metric("HP Reported", f"{hp_count} ({hp_count/len(export_df)*100:.1f}%)")
                
                with stat_col3:
                    top_country = export_df['Reporter Country'].mode().iloc[0] if not export_df['Reporter Country'].mode().empty else 'N/A'
                    st.metric("Top Reporter Country", COUNTRY_CODES.get(top_country, top_country))
                
                with stat_col4:
                    male_count = (export_df['Patient Sex'] == 'Male').sum()
                    female_count = (export_df['Patient Sex'] == 'Female').sum()
                    st.metric("M/F Ratio", f"{male_count}:{female_count}")
    
    else:
        # Welcome state
        st.markdown("""
        <div class="data-card">
            <h3>👋 Welcome to the Global ADR Intelligence Dashboard</h3>
            <p style="color: #8ba3c7; margin-bottom: 1rem;">
                This platform provides comprehensive pharmacovigilance analytics using the FDA FAERS database.
            </p>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
                <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px;">
                    <h4 style="color: #02bfe7; margin: 0 0 0.5rem 0;">📋 Risk Assessment</h4>
                    <p style="color: #8ba3c7; font-size: 0.9rem; margin: 0;">
                        Dual-layer analysis combining FDA labels and FAERS signals
                    </p>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px;">
                    <h4 style="color: #02bfe7; margin: 0 0 0.5rem 0;">🌍 Geographic Intel</h4>
                    <p style="color: #8ba3c7; font-size: 0.9rem; margin: 0;">
                        Global distribution of ADR reports by country
                    </p>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px;">
                    <h4 style="color: #02bfe7; margin: 0 0 0.5rem 0;">📤 Data Export</h4>
                    <p style="color: #8ba3c7; font-size: 0.9rem; margin: 0;">
                        Download case-level data in CSV, Excel, or JSON
                    </p>
                </div>
            </div>
            <p style="color: #8ba3c7; margin-top: 1.5rem; font-size: 0.9rem;">
                👈 Configure your analysis parameters in the sidebar and click <strong>Run Analysis</strong> to begin.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick demo stats
        st.markdown("### 📊 Quick Stats from FDA FAERS")
        
        demo_col1, demo_col2, demo_col3 = st.columns(3)
        
        with demo_col1:
            st.markdown("""
            <div class="metric-card">
                <p class="metric-value">28M+</p>
                <p class="metric-label">Total FAERS Reports</p>
            </div>
            """, unsafe_allow_html=True)
        
        with demo_col2:
            st.markdown("""
            <div class="metric-card">
                <p class="metric-value">190+</p>
                <p class="metric-label">Reporting Countries</p>
            </div>
            """, unsafe_allow_html=True)
        
        with demo_col3:
            st.markdown("""
            <div class="metric-card">
                <p class="metric-value">Real-time</p>
                <p class="metric-label">OpenFDA API Access</p>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
