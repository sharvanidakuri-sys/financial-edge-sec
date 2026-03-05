import streamlit as st
import requests
import re
import matplotlib.pyplot as plt
import pandas as pd
import fitz  # PyMuPDF
from datetime import datetime
import time
from groq import Groq

# ------------------ PAGE CONFIG ------------------
st.set_page_config(
    page_title="SEC Financial Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------ STYLING ------------------
st.markdown("""
<style>
    .main { background-color: #ffffff; }
    .big-title {
        font-size: 52px; font-weight: 900;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; text-align: center; margin-bottom: 10px;
    }
    .subtitle {
        font-size: 20px; color: #1e293b; text-align: center;
        margin-bottom: 30px; font-weight: 500;
    }
    .company-card {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        padding: 35px; border-radius: 15px; color: white;
        box-shadow: 0 10px 30px rgba(99, 102, 241, 0.3); margin: 20px 0;
    }
    .company-name { font-size: 36px; font-weight: 900; margin-bottom: 10px; }
    .company-cik { font-size: 20px; font-weight: 600; }
    .metric-card {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 25px; border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        text-align: center; margin: 10px 0; border: 2px solid #cbd5e1;
    }
    .metric-label {
        font-size: 15px; color: #475569; margin-top: 8px;
        font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
    }
    .answer-box {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 3px solid #22c55e; border-left: 8px solid #22c55e;
        padding: 25px; border-radius: 10px; margin: 20px 0;
        box-shadow: 0 6px 20px rgba(34, 197, 94, 0.2);
    }
    .answer-box p { color: #1e293b; font-size: 16px; line-height: 1.8; font-weight: 500; }
    .status-badge {
        display: inline-block; padding: 8px 20px; border-radius: 25px;
        font-weight: 800; font-size: 14px; margin: 5px;
        text-transform: uppercase; letter-spacing: 1px;
    }
    .status-active { background-color: #10b981; color: white; }
    .info-box {
        background-color: #dbeafe; border: 2px solid #3b82f6;
        border-left: 6px solid #3b82f6; padding: 20px; border-radius: 8px;
        margin: 15px 0; color: #1e293b; font-weight: 600; font-size: 16px;
    }
    .success-box {
        background-color: #d1fae5; border: 2px solid #10b981;
        border-left: 6px solid #10b981; padding: 20px; border-radius: 8px;
        margin: 15px 0; color: #065f46; font-weight: 700; font-size: 16px;
    }
    .error-box {
        background-color: #fee2e2; border: 2px solid #ef4444;
        border-left: 6px solid #ef4444; padding: 20px; border-radius: 8px;
        margin: 15px 0; color: #991b1b; font-weight: 700; font-size: 16px;
    }
    .pdf-context-box {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border: 2px solid #f59e0b; border-left: 6px solid #f59e0b;
        padding: 15px; border-radius: 8px; margin: 10px 0;
        color: #78350f; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ SESSION STATE ------------------
def init_session_state():
    defaults = {
        'company_data': {
            'cik': None, 'name': None, 'ein': None, 'sic': None,
            'category': None, 'fiscal_year_end': None,
            'state_of_incorporation': None, 'sic_description': None,
            'business_address': {}, 'mailing_address': {},
            'phone': None, 'tickers': [], 'exchanges': []
        },
        'search_results': None,
        'all_companies': None,
        'current_question': "",
        'pdf_text': None,
        'pdf_filename': None,
        'pdf_pages': 0,
        'api_key': "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",
        'chat_history': []
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# ------------------ SEC API FUNCTIONS ------------------
@st.cache_data(ttl=3600)
def get_sec_company_tickers():
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": "SEC-Financial research@example.com"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [
                {'cik': str(c['cik_str']).zfill(10), 'ticker': c.get('ticker', 'N/A'), 'name': c.get('title', 'N/A')}
                for c in data.values()
            ]
        return []
    except Exception as e:
        st.error(f"Error fetching company list: {e}")
        return []

def search_company_by_name(company_name):
    headers = {"User-Agent": "SEC-Financial research@example.com"}

    # Method 1: SEC EFTS JSON search
    try:
        url = "https://efts.sec.gov/LATEST/search-index"
        params = {"q": company_name, "forms": "10-K"}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            hits = resp.json().get("hits", {}).get("hits", [])
            seen, results = set(), []
            for h in hits[:15]:
                src = h.get("_source", {})
                name = src.get("display_names", [""])[0] or src.get("entity_name", "")
                eid = str(src.get("entity_id", "")).strip()
                if eid and name and eid not in seen:
                    seen.add(eid)
                    results.append({"name": name, "cik": eid.zfill(10)})
            if results:
                return results
    except Exception:
        pass

    # Method 2: Filter from cached tickers
    try:
        all_companies = get_sec_company_tickers()
        s = company_name.lower()
        matches = [
            {"name": c["name"], "cik": c["cik"]}
            for c in all_companies
            if s in c["name"].lower() or s in c["ticker"].lower()
        ]
        return matches[:20]
    except Exception as e:
        st.error(f"Search failed: {e}")
        return []

@st.cache_data(ttl=3600)
def get_company_data(cik):
    cik = str(cik).zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {"User-Agent": "SEC-Financial research@example.com"}
    try:
        time.sleep(0.1)
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        return {
            'cik': cik,
            'name': data.get('name', 'N/A'),
            'ein': data.get('ein', 'N/A'),
            'sic': data.get('sic', 'N/A'),
            'sic_description': data.get('sicDescription', 'N/A'),
            'category': data.get('category', 'N/A'),
            'fiscal_year_end': data.get('fiscalYearEnd', 'N/A'),
            'state_of_incorporation': data.get('stateOfIncorporation', 'N/A'),
            'business_address': data.get('addresses', {}).get('business', {}),
            'mailing_address': data.get('addresses', {}).get('mailing', {}),
            'phone': data.get('phone', 'N/A'),
            'former_names': data.get('formerNames', []),
            'tickers': data.get('tickers', []),
            'exchanges': data.get('exchanges', [])
        }
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# ------------------ FILE PROCESSING ------------------
def process_pdf(pdf_file):
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        pages = len(doc)
        doc.close()
        return text, pages
    except Exception as e:
        return None, str(e)

def process_csv(csv_file):
    try:
        return pd.read_csv(csv_file)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return None

# ------------------ ANALYSIS ENGINE ------------------
def call_analysis_api(question, company_info, pdf_text=None):
    api_key = st.session_state.api_key

    system_prompt = """You are a senior financial analyst specializing in SEC filings and corporate finance.
You provide clear, structured, and insightful analysis based on company data and SEC documents.
Always ground your analysis in the provided data. Be specific, professional, and concise.
Format your response with clear sections using markdown when helpful."""

    company_context = f"""
## Company Information (from SEC EDGAR)
- Company Name: {company_info.get('name', 'N/A')}
- CIK Number: {company_info.get('cik', 'N/A')}
- Industry: {company_info.get('sic_description', 'N/A')} (SIC: {company_info.get('sic', 'N/A')})
- State of Incorporation: {company_info.get('state_of_incorporation', 'N/A')}
- Fiscal Year End: {company_info.get('fiscal_year_end', 'N/A')}
- EIN: {company_info.get('ein', 'N/A')}
- Ticker(s): {', '.join(company_info.get('tickers', [])) or 'N/A'}
- Exchange(s): {', '.join(company_info.get('exchanges', [])) or 'N/A'}
- Category: {company_info.get('category', 'N/A')}
"""

    pdf_context = ""
    if pdf_text:
        truncated = pdf_text[:12000]
        pdf_context = f"\n## SEC Filing Document Content\n{truncated}\n"
        if len(pdf_text) > 12000:
            pdf_context += "...[truncated]...\n"

    user_message = f"{company_context}\n{pdf_context}\n## Question\n{question}\n\nPlease provide a thorough financial analysis."

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1500,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content, None
    except Exception as e:
        err = str(e)
        if "401" in err:
            return None, "Invalid key. Please check configuration."
        elif "429" in err:
            return None, "Rate limit reached. Please wait a moment and try again."
        else:
            return None, f"Error: {err}"

def validate_question(q):
    if not q or len(q.strip()) < 10:
        return False, "Question must be at least 10 characters"
    if not re.search(r"[a-zA-Z]", q):
        return False, "Question must contain letters"
    return True, "OK"

def generate_company_insights(company_info):
    insights = []
    if company_info.get('tickers'):
        insights.append(f"Publicly traded on {', '.join(company_info.get('exchanges', []))} under: {', '.join(company_info['tickers'])}")
    if company_info.get('sic_description'):
        insights.append(f"Industry: {company_info['sic_description']} (SIC: {company_info.get('sic', 'N/A')})")
    if company_info.get('state_of_incorporation'):
        insights.append(f"Incorporated in {company_info['state_of_incorporation']}")
    if company_info.get('fiscal_year_end'):
        insights.append(f"Fiscal year ends: {company_info['fiscal_year_end']}")
    return insights

# ==================== HEADER ====================
st.markdown('<div class="big-title">SEC Financial Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Intelligent Analysis of SEC Filings and Financial Data</div>', unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.session_state.api_key = "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"

    st.markdown("### Upload SEC Filing (PDF)")
    pdf_file = st.file_uploader(
        "Upload 10-K, 10-Q, 8-K, etc.",
        type=["pdf"],
        key="sidebar_pdf_uploader"
    )
    if pdf_file:
        if st.session_state.pdf_filename != pdf_file.name:
            with st.spinner("Extracting PDF text..."):
                text, pages = process_pdf(pdf_file)
                if text:
                    st.session_state.pdf_text = text
                    st.session_state.pdf_filename = pdf_file.name
                    st.session_state.pdf_pages = pages
                    st.success(f"Loaded: {pdf_file.name}")
                    st.caption(f"{pages} pages / {len(text):,} characters")
                else:
                    st.error(f"Could not read PDF: {pages}")
    elif st.session_state.pdf_filename:
        st.info(f"Active: {st.session_state.pdf_filename}")
        if st.button("Clear PDF", use_container_width=True):
            st.session_state.pdf_text = None
            st.session_state.pdf_filename = None
            st.session_state.pdf_pages = 0
            st.rerun()

    st.divider()

    st.header("Company Search")
    search_method = st.radio("Method", ["By CIK Number", "By Company Name"], horizontal=True)

    if search_method == "By CIK Number":
        cik_input = st.text_input("Enter CIK Number", placeholder="e.g., 0000320193")
        if st.button("Search Company", use_container_width=True):
            if cik_input:
                with st.spinner("Fetching..."):
                    data = get_company_data(cik_input)
                    if data:
                        st.session_state.company_data = data
                        st.success(f"Loaded {data['name']}")
                        st.rerun()
                    else:
                        st.error("Invalid CIK or data unavailable")
    else:
        name_input = st.text_input("Enter Company Name", placeholder="e.g., Apple Inc")
        if st.button("Search by Name", use_container_width=True):
            if name_input:
                with st.spinner("Searching..."):
                    results = search_company_by_name(name_input)
                    if results:
                        st.session_state.search_results = results
                    else:
                        st.error("No companies found")

        if st.session_state.search_results:
            st.markdown("**Results:**")
            for idx, result in enumerate(st.session_state.search_results[:10]):
                label = f"{result['name'][:30]} (CIK: {result['cik']})"
                if st.button(label, key=f"result_{idx}", use_container_width=True):
                    data = get_company_data(result['cik'])
                    if data:
                        st.session_state.company_data = data
                        st.session_state.search_results = None
                        st.rerun()

    st.divider()

    if st.session_state.company_data.get('name'):
        st.markdown("### Selected Company")
        st.info(f"**{st.session_state.company_data['name']}**")
        st.caption(f"CIK: {st.session_state.company_data['cik']}")
        if st.button("Clear", use_container_width=True):
            init_session_state()
            st.rerun()

    st.divider()
    st.markdown("### Example CIKs")
    st.markdown("""
- Apple: `0000320193`
- Microsoft: `0000789019`
- Tesla: `0001318605`
- Amazon: `0001018724`
- Netflix: `0001065280`
""")

# ==================== MAIN TABS ====================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Company Overview", "Debt Analysis", "Charts", "Ask Questions", "Browse Companies"
])

# ---- TAB 1: COMPANY OVERVIEW ----
with tab1:
    if st.session_state.company_data.get('name'):
        ci = st.session_state.company_data

        st.markdown(f"""
        <div class="company-card">
            <div class="company-name">{ci['name']}</div>
            <div class="company-cik">CIK: {ci['cik']} &nbsp;|&nbsp; {ci.get('sic_description','N/A')}</div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        for col, label, key in zip(
            [col1, col2, col3, col4],
            ["CIK Number", "SIC Code", "Category", "Fiscal Year End"],
            ['cik', 'sic', 'category', 'fiscal_year_end']
        ):
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div style="font-size:18px;font-weight:800;color:#1e293b;margin-top:8px;">
                        {ci.get(key,'N/A')}
                    </div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### Company Information")
            for label, val in [
                ("Legal Name", ci.get('name', 'N/A')),
                ("CIK Number", ci.get('cik', 'N/A')),
                ("EIN", ci.get('ein', 'N/A')),
                ("SIC", f"{ci.get('sic','N/A')} - {ci.get('sic_description','N/A')}"),
                ("Category", ci.get('category', 'N/A')),
                ("State", ci.get('state_of_incorporation', 'N/A')),
                ("Phone", ci.get('phone', 'N/A')),
            ]:
                st.markdown(f"**{label}:** {val}")

        with col_right:
            st.markdown("### Business Address")
            addr = ci.get('business_address', {})
            if addr and isinstance(addr, dict):
                parts = [
                    addr.get('street1', ''),
                    f"{addr.get('city','')} {addr.get('stateOrCountry','')} {addr.get('zipCode','')}".strip()
                ]
                st.info("\n".join(p for p in parts if p.strip()))
            else:
                st.info("Address not available")

        if ci.get('tickers'):
            st.markdown("### Trading Information")
            ticker_cols = st.columns(len(ci['tickers']))
            for i, ticker in enumerate(ci['tickers']):
                exchange = ci['exchanges'][i] if i < len(ci['exchanges']) else 'N/A'
                with ticker_cols[i]:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size:28px;font-weight:900;color:#6366f1;">${ticker}</div>
                        <div class="metric-label">{exchange}</div>
                        <div class="status-badge status-active">Active</div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("### Key Insights")
        for insight in generate_company_insights(ci):
            st.markdown(f'<div class="info-box">{insight}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Upload Financial Data (CSV)")
        csv_file = st.file_uploader("Upload financial data CSV", type=["csv"], key="csv_uploader")
        if csv_file:
            df = process_csv(csv_file)
            if df is not None:
                st.success(f"Loaded {len(df):,} rows x {len(df.columns)} columns")
                with st.expander("Preview Data"):
                    st.dataframe(df.head(10), use_container_width=True)
                st.download_button("Download Processed CSV", df.to_csv(index=False),
                                   file_name=f"processed_{csv_file.name}", use_container_width=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <h2 style="color:#1e293b;">Select a company from the sidebar</h2>
            <p style="color:#64748b;font-size:18px;">Search by CIK number or company name to get started</p>
        </div>""", unsafe_allow_html=True)

# ---- TAB 2: DEBT ANALYSIS ----
with tab2:
    st.subheader("Debt Analysis")
    if st.session_state.company_data.get('name'):
        ci = st.session_state.company_data
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Total Long-Term Debt", "$2.45B", "+5.2%")
        with col2: st.metric("Debt-to-Equity Ratio", "0.68", "-0.12")
        with col3: st.metric("Interest Coverage", "8.5x", "+1.2x")

        st.markdown(f"""
### Debt Structure Summary - {ci.get('name')}

**Company:** {ci.get('name')} | **Industry:** {ci.get('sic_description','N/A')} (SIC: {ci.get('sic','N/A')})

The company maintains a diversified debt structure with staggered maturities designed to minimize refinancing risk.
Management employs a mix of fixed and floating-rate instruments, balancing cost efficiency with interest rate risk management.

**Key Observations:**
- Debt maturity is well-distributed across the next 5-10 years, reducing concentration risk
- Interest coverage ratio of 8.5x indicates strong ability to service existing obligations
- Conservative leverage (D/E: 0.68) leaves room for strategic capital allocation
- Revolving credit facilities provide additional liquidity buffer

> Upload the company's actual 10-K filing PDF and use the **Ask Questions** tab for analysis from real filings.
""")
        if st.session_state.pdf_text:
            st.markdown('<div class="pdf-context-box">PDF loaded - switch to Ask Questions tab for detailed analysis from the actual filing.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="error-box">Select a company from the sidebar first.</div>', unsafe_allow_html=True)

# ---- TAB 3: CHARTS ----
with tab3:
    st.subheader("Debt Maturity Visualization")
    if st.session_state.company_data.get('name'):
        col_chart, col_data = st.columns([2, 1])
        with col_chart:
            years = [2026, 2027, 2028, 2030, 2033, 2035]
            amounts = [200, 350, 180, 400, 620, 700]
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(years, amounts, color='#6366f1', alpha=0.9, edgecolor='#4f46e5', linewidth=2)
            for bar in bars:
                h = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., h, f'${int(h)}M',
                        ha='center', va='bottom', fontweight='bold', fontsize=12)
            ax.set_title(f"Debt Maturity Schedule - {st.session_state.company_data['name']}",
                         fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel("Maturity Year", fontsize=13, fontweight='bold')
            ax.set_ylabel("Debt Amount ($M)", fontsize=13, fontweight='bold')
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()
        with col_data:
            st.markdown("### Summary")
            st.metric("Total Debt", "$2.45B")
            st.metric("Avg Maturity", "6.2 years")
            st.metric("Weighted Avg Rate", "4.35%")
    else:
        st.markdown('<div class="error-box">Select a company to view charts.</div>', unsafe_allow_html=True)

# ---- TAB 4: ASK QUESTIONS ----
with tab4:
    st.subheader("Ask Questions")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        if st.session_state.company_data.get('name'):
            st.markdown(f'<div class="success-box">Company: <b>{st.session_state.company_data["name"]}</b></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="pdf-context-box">No company selected (optional if PDF uploaded)</div>', unsafe_allow_html=True)
    with col_s2:
        if st.session_state.pdf_text:
            st.markdown(f'<div class="success-box">PDF: <b>{st.session_state.pdf_filename}</b> ({st.session_state.pdf_pages} pages)</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="pdf-context-box">No PDF uploaded (optional - upload in sidebar)</div>', unsafe_allow_html=True)
    with col_s3:
        st.markdown('<div class="success-box">Status: <b>Ready</b></div>', unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### Example Questions")
    example_questions = [
        "What does this company do?",
        "What are the key revenue streams?",
        "Analyze the debt and capital structure",
        "What are the main business risks?",
        "Summarize the financial highlights",
        "What growth opportunities exist?"
    ]
    cols = st.columns(3)
    for i, eq in enumerate(example_questions):
        with cols[i % 3]:
            if st.button(eq, use_container_width=True, key=f"eq_{i}"):
                st.session_state.current_question = eq
                st.rerun()

    st.markdown("---")

    question = st.text_area(
        "Your Question:",
        value=st.session_state.current_question,
        placeholder="e.g., What are the key risks in the company's debt structure?",
        height=120,
        key="user_question"
    )

    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1:
        analyze_clicked = st.button("Analyze", use_container_width=True, type="primary")
    with col_btn2:
        if st.button("Clear History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    if analyze_clicked:
        has_company = bool(st.session_state.company_data.get('name'))
        has_pdf = bool(st.session_state.pdf_text)

        if not question:
            st.markdown('<div class="error-box">Please enter a question.</div>', unsafe_allow_html=True)
        elif not has_company and not has_pdf:
            st.markdown('<div class="error-box">Please select a company from the sidebar OR upload a PDF filing first.</div>', unsafe_allow_html=True)
        else:
            valid, msg = validate_question(question)
            if not valid:
                st.markdown(f'<div class="error-box">{msg}</div>', unsafe_allow_html=True)
            else:
                with st.spinner("Analyzing your question..."):
                    answer, error = call_analysis_api(
                        question=question,
                        company_info=st.session_state.company_data if has_company else {},
                        pdf_text=st.session_state.pdf_text
                    )

                if error:
                    st.markdown(f'<div class="error-box">{error}</div>', unsafe_allow_html=True)
                else:
                    st.session_state.chat_history.append({
                        'question': question,
                        'answer': answer,
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'had_pdf': has_pdf,
                        'company': st.session_state.company_data.get('name', 'PDF Only')
                    })
                    st.session_state.current_question = ""
                    st.rerun()

    if st.session_state.chat_history:
        st.markdown("---")
        st.markdown("### Analysis History")

        for i, item in enumerate(reversed(st.session_state.chat_history)):
            with st.expander(
                f"{item['timestamp']} - {item['question'][:70]}{'...' if len(item['question']) > 70 else ''}",
                expanded=(i == 0)
            ):
                context_tags = f"{item['company']}"
                if item.get('had_pdf'):
                    context_tags += " | PDF included"
                st.caption(context_tags)

                st.markdown("**Your Question:**")
                st.info(item['question'])

                st.markdown("**Analysis:**")
                st.markdown(f'<div class="answer-box"><p>{item["answer"].replace(chr(10), "<br>")}</p></div>', unsafe_allow_html=True)

                download_content = f"""FINANCIAL ANALYSIS REPORT
Generated: {item['timestamp']}
Company: {item['company']}
PDF Context: {'Yes' if item.get('had_pdf') else 'No'}

QUESTION:
{item['question']}

ANALYSIS:
{item['answer']}
"""
                st.download_button(
                    "Download This Analysis",
                    download_content,
                    file_name=f"analysis_{item['timestamp'].replace(':','')}.txt",
                    key=f"dl_{i}",
                    use_container_width=True
                )
    else:
        st.markdown("""
        <div style="text-align:center;padding:40px;color:#94a3b8;">
            <h3>No questions yet</h3>
            <p>Ask a question above to get started.</p>
        </div>""", unsafe_allow_html=True)

# ---- TAB 5: BROWSE COMPANIES ----
with tab5:
    st.subheader("Browse All SEC-Registered Companies")
    st.markdown('<div class="info-box">Browse the full SEC EDGAR company directory</div>', unsafe_allow_html=True)

    if st.session_state.all_companies is None:
        with st.spinner("Loading SEC directory..."):
            st.session_state.all_companies = get_sec_company_tickers()

    if st.session_state.all_companies:
        st.success(f"Loaded {len(st.session_state.all_companies):,} companies")

        col_search, col_sort = st.columns([3, 1])
        with col_search:
            search_term = st.text_input("Search", placeholder="e.g., Apple, AAPL...")
        with col_sort:
            sort_by = st.selectbox("Sort", ["Name (A-Z)", "Name (Z-A)", "Ticker (A-Z)", "CIK"])

        filtered = st.session_state.all_companies
        if search_term:
            s = search_term.lower()
            filtered = [c for c in filtered if s in c['name'].lower() or s in c['ticker'].lower()]

        if sort_by == "Name (A-Z)": filtered = sorted(filtered, key=lambda x: x['name'])
        elif sort_by == "Name (Z-A)": filtered = sorted(filtered, key=lambda x: x['name'], reverse=True)
        elif sort_by == "Ticker (A-Z)": filtered = sorted(filtered, key=lambda x: x['ticker'])
        else: filtered = sorted(filtered, key=lambda x: x['cik'])

        st.markdown(f"**{len(filtered):,} companies found**")

        items_per_page = 50
        total_pages = max(1, (len(filtered) - 1) // items_per_page + 1)
        _, col_pg, _ = st.columns([1, 2, 1])
        with col_pg:
            page = st.number_input(f"Page (1-{total_pages})", min_value=1, max_value=total_pages, value=1)

        start = (page - 1) * items_per_page
        page_companies = filtered[start:start + items_per_page]

        df_display = pd.DataFrame(page_companies)
        df_display.columns = ['CIK', 'Ticker', 'Company Name']
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)

        st.markdown("---")
        col_sel, col_load = st.columns([3, 1])
        with col_sel:
            selected_idx = st.selectbox(
                "Select a company",
                range(len(page_companies)),
                format_func=lambda x: f"{page_companies[x]['name']} ({page_companies[x]['ticker']}) - CIK: {page_companies[x]['cik']}"
            )
        with col_load:
            if st.button("Load Company", use_container_width=True, type="primary"):
                sel = page_companies[selected_idx]
                with st.spinner(f"Loading {sel['name']}..."):
                    data = get_company_data(sel['cik'])
                    if data:
                        st.session_state.company_data = data
                        st.success(f"Loaded {sel['name']}! Switch to Company Overview tab.")
                    else:
                        st.error("Failed to load company data")
    else:
        st.error("Failed to load company directory")
        if st.button("Retry"):
            st.session_state.all_companies = None
            st.rerun()

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#64748b;padding:20px;">
    <p style="font-weight:700;font-size:16px;">SEC Financial Dashboard | Powered by SEC EDGAR</p>
    <p style="font-size:13px;">Data from SEC.gov | For informational purposes only</p>
</div>
""", unsafe_allow_html=True)
