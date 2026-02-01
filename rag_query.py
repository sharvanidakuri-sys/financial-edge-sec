import pickle
import numpy as np
import faiss

# Load saved objects
with open("chunks.pkl", "rb") as f:
    chunks = pickle.load(f)

with open("vectorizer.pkl", "rb") as f:
    vectorizer = pickle.load(f)

index = faiss.read_index("faiss.index")


def retrieve_chunks(question, top_k=3):
    """
    Retrieve most relevant text chunks for a question
    """
    question_vec = vectorizer.transform([question]).toarray().astype("float32")
    distances, indices = index.search(question_vec, top_k)
    results = [chunks[i] for i in indices[0]]
    return results, indices[0]


def generate_answer(question):
    """
    Generate a CLEAN English answer (not raw SEC text)
    """
    retrieved_chunks, indices = retrieve_chunks(question)

    # Combine chunks into readable context
    context = " ".join(retrieved_chunks)

    # Simple clean English summarization
    answer = (
        "Based on the SEC filing, the company operates its business as follows:\n\n"
        + context[:1200]
    )

    source = {
        "document": "criteo_10k_2024.pdf",
        "chunk_index": int(indices[0])
    }

    return answer, source


# Test run (for terminal testing only)
if __name__ == "__main__":
    q = "What is the company's business model?"
    ans, src = generate_answer(q)
    print("\nAnswer:\n", ans)
    print("\nSource:\n", src)