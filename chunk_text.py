import pickle
from PyPDF2 import PdfReader

PDF_PATH = "criteo_10k_2024.pdf"
OUTPUT_FILE = "chunks.pkl"

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def chunk_text(text, chunk_size=500):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

if __name__ == "__main__":
    text = extract_text_from_pdf(PDF_PATH)
    chunks = chunk_text(text)

    with open(OUTPUT_FILE, "wb") as f:
        pickle.dump(chunks, f)

    print("✅ chunks.pkl created successfully with clean English text")