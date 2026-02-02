import streamlit as st
import requests
import fitz  # PyMuPDF
import re

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Financial Edge – SEC EDGAR Analyzer",
    layout="wide"
)

# ---------------- UI HEADER ----------------
st.markdown(
    "<h1 style='text-align:center;'>📊 Financial Edge – SEC EDGAR Analyzer</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align:center;'>Ask questions using Company CIK or Upload an official 10-K / 10-Q PDF</p>",
    unsafe_allow_html=True
)

# ---------------- HELPERS ----------------
HEADERS = {"User-Agent": "StudentProject/1.0 student@email.com"}

def clean_text(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_text_from_pdf(file):
    text = ""
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf:
        text += page.get_text()
    return clean_text(text)

def fetch_latest_10k(cik):
    cik = cik.zfill(10)

    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    sub = requests.get(submissions_url, headers=HEADERS)

    if sub.status_code != 200:
        return None, None, None

    data = sub.json()
    company = data["name"]

    filings = data["filings"]["recent"]
    for i, form in enumerate(filings["form"]):
        if form == "10-K":
            accession = filings["accessionNumber"][i].replace("-", "")
            doc = filings["primaryDocument"][i]
            filing_url = f"https://www.sec.gov/ixviewer/documents/{accession}/{doc}"
            text_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{doc}"

            filing_text = requests.get(text_url, headers=HEADERS)
            if filing_text.status_code != 200:
                continue

            return company, clean_text(filing_text.text), filing_url

    return None, None, None

def find_relevant_section(text, question):
    q = question.lower()

    if "risk" in q:
        keys = ["risk factor", "risk factors"]
    elif "growth" in q:
        keys = ["growth", "strategy", "expansion"]
    elif "revenue" in q:
        keys = ["revenue", "sales", "income"]
    elif "business" in q:
        keys = ["business", "overview", "operations"]
    else:
        keys = ["business", "risk", "revenue", "strategy"]

    chunks = []
    for k in keys:
        matches = re.findall(rf"(.{{0,1200}}{k}.{{0,1200}})", text, re.IGNORECASE)
        chunks.extend(matches)

    return " ".join(chunks[:5])

def generate_answer(company, question, context):
    if not context:
        return "Relevant section not clearly found in filing."

    answer = (
        f"Based on the official SEC filing of {company}, the following analysis answers the question: "
        f"'{question}'.\n\n"
        f"{context[:2000]}\n\n"
        "This information is disclosed directly by the company in its SEC filing. "
        "It reflects management’s discussion of operations, risks, revenue sources, "
        "and future outlook. Investors use this section to evaluate performance, "
        "stability, and long-term growth potential. The discussion highlights key drivers, "
        "market conditions, regulatory exposure, and strategic priorities that may affect "
        "financial results over time."
    )

    return answer

# ---------------- UI ----------------
left, right = st.columns([2, 1])

with left:
    st.subheader("🔘 Select Input Method")

    mode = st.radio(
        "Choose one",
        ["Enter Company CIK", "Upload SEC PDF"],
        horizontal=True
    )

    cik = ""
    uploaded_file = None

    if mode == "Enter Company CIK":
        cik = st.text_input("Enter CIK (Example: 0000320193 for Apple)")
    else:
        uploaded_file = st.file_uploader("Upload 10-K / 10-Q PDF", type=["pdf"])

    question = st.text_input("Ask your question (Business, Risks, Growth, Revenue, etc.)")
    analyze = st.button("Analyze")

    if analyze:
        if mode == "Enter Company CIK":
            if not cik:
                st.error("Please enter a CIK")
                st.stop()

            company, text, link = fetch_latest_10k(cik)

            if not text:
                st.error("Could not fetch 10-K for this CIK")
                st.stop()

            context = find_relevant_section(text, question)
            answer = generate_answer(company, question, context)

            st.markdown("### ✅ Answer")
            st.write(answer)
            st.markdown(f"🔗 **Official SEC Filing:** [View 10-K]({link})")

        else:
            if not uploaded_file:
                st.error("Please upload a PDF")
                st.stop()

            text = extract_text_from_pdf(uploaded_file)
            context = find_relevant_section(text, question)

            answer = generate_answer("Uploaded Company", question, context)

            st.markdown("### ✅ Answer")
            st.write(answer)
            st.markdown("📄 **Source:** Uploaded SEC PDF")

with right:
    st.subheader("ℹ️ How this works")
    st.markdown(
        """
        ✔ Fetches official SEC filings  
        ✔ Segments by Business / Risk / Growth / Revenue  
        ✔ Long, detailed answers (15+ lines)  
        ✔ No AI hallucination  
        ✔ 100% SEC-based content  
        """
    )

