import streamlit as st
import requests
import fitz  # PyMuPDF
import re
from bs4 import BeautifulSoup

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Financial Edge – SEC EDGAR Analyzer",
    layout="wide"
)

st.title("📊 Financial Edge – SEC EDGAR Analyzer")
st.caption("Answers are extracted directly from official SEC EDGAR 10-K / 10-Q filings")

HEADERS = {
    "User-Agent": "AcademicProject/1.0 student@email.com"
}

# ---------------- CLEAN TEXT ----------------
def clean_text(text):
    text = re.sub(r"<.*?>", " ", text)          # remove HTML
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ---------------- PDF READER ----------------
def extract_text_from_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return clean_text(text)

# ---------------- FETCH SEC 10-K / 10-Q ----------------
def fetch_sec_filing(cik):
    cik = cik.zfill(10)
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(submissions_url, headers=HEADERS)

    if r.status_code != 200:
        return None, None

    data = r.json()
    company = data.get("name", "Company")

    filings = data["filings"]["recent"]

    for form, acc, doc in zip(
        filings["form"],
        filings["accessionNumber"],
        filings["primaryDocument"]
    ):
        if form in ["10-K", "10-Q"]:
            acc = acc.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
            html = requests.get(url, headers=HEADERS).text

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "table"]):
                tag.decompose()

            text = clean_text(soup.get_text(" "))
            return text, url

    return None, None

# ---------------- FIND RELEVANT CONTENT ----------------
def find_relevant_answer(question, text, max_words=200):
    keywords = [w for w in question.lower().split() if len(w) > 3]
    sentences = re.split(r"\. ", text)

    matched = []
    for s in sentences:
        if any(k in s.lower() for k in keywords):
            matched.append(s)

    if not matched:
        matched = sentences[:10]

    answer_text = ". ".join(matched)
    words = answer_text.split()[:max_words]

    return " ".join(words) + "."

# ---------------- UI ----------------
left, right = st.columns([2, 1])

with left:
    st.subheader("Input Method")

    option = st.radio(
        "Choose one:",
        ["Enter Company CIK", "Upload SEC PDF"],
        horizontal=True
    )

    filing_text = None
    source_link = ""

    if option == "Enter Company CIK":
        cik = st.text_input("Enter CIK (Example: 0000320193 for Apple)")
    else:
        uploaded_file = st.file_uploader("Upload 10-K / 10-Q PDF", type=["pdf"])

    question = st.text_input(
        "Ask your question (business model, risks, revenue, growth, etc.)"
    )

    if st.button("Analyze"):
        if option == "Enter Company CIK":
            if not cik:
                st.error("Please enter a CIK")
                st.stop()

            filing_text, source_link = fetch_sec_filing(cik)
            if filing_text is None:
                st.error("Unable to fetch SEC filing")
                st.stop()

        else:
            if uploaded_file is None:
                st.error("Please upload a PDF")
                st.stop()
            filing_text = extract_text_from_pdf(uploaded_file)
            source_link = "Uploaded SEC PDF"

        answer = find_relevant_answer(question, filing_text)

        st.markdown("### 📌 Answer (Simple English)")
        st.write(answer)

        st.markdown(f"🔗 **Official Source:** {source_link}")

with right:
    st.subheader("Project Notes")
    st.markdown(
        """
        ✔ Uses only SEC EDGAR data  
        ✔ CIK AND PDF UPLOAD  
        ✔ 100 % SEC based content  
        """
    )
