import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "YourName your@email.com"
}

def fetch_latest_10k_text(cik: str) -> str:
    cik = cik.zfill(10)

    # 1. Get submissions JSON
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    submissions = requests.get(submissions_url, headers=HEADERS).json()

    filings = submissions["filings"]["recent"]

    # 2. Find latest 10-K
    accession = None
    for form, acc in zip(filings["form"], filings["accessionNumber"]):
        if form == "10-K":
            accession = acc.replace("-", "")
            break

    if accession is None:
        raise ValueError("No 10-K found for this CIK")

    # 3. Get filing index
    index_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    filing_base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}"

    index_json = requests.get(f"{filing_base}/index.json", headers=HEADERS).json()

    # 4. Find main HTML document
    html_file = None
    for file in index_json["directory"]["item"]:
        if file["name"].endswith(".htm"):
            html_file = file["name"]
            break

    if html_file is None:
        raise ValueError("HTML filing not found")

    # 5. Download HTML
    html_url = f"{filing_base}/{html_file}"
    html = requests.get(html_url, headers=HEADERS).text

    # 6. Clean HTML
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "table"]):
        tag.decompose()

    text = soup.get_text(separator=" ")

    clean_text = " ".join(text.split())
    return clean_text