import os
import faiss
import re
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from django.conf import settings
print("🔥 USING NEW LIGHTWEIGHT RAG")


BASE_DIR = settings.BASE_DIR

SC_INDEX_PATH = os.path.join(BASE_DIR, "sc_judgments_faiss.index")
SC_DOCS_PATH = os.path.join(BASE_DIR, "sc_judgments_texts.pkl")

LAW_INDEX_PATH = os.path.join(BASE_DIR, "indian_law_faiss.index")
LAW_DOCS_PATH = os.path.join(BASE_DIR, "indian_law_texts.pkl")

# Global cache (lazy load)
embedder = None
sc_index = None
sc_documents = None
law_index = None
law_documents = None


def load_models():
    global embedder, sc_index, sc_documents, law_index, law_documents

    if embedder is None:
        print("Loading embedding model...")
        embedder = SentenceTransformer("all-MiniLM-L6-v2")

    if sc_index is None:
        print("Loading SC FAISS index...")
        sc_index = faiss.read_index(SC_INDEX_PATH)
        with open(SC_DOCS_PATH, "rb") as f:
            sc_documents = pickle.load(f)

    if law_index is None:
        print("Loading Law FAISS index...")
        law_index = faiss.read_index(LAW_INDEX_PATH)
        with open(LAW_DOCS_PATH, "rb") as f:
            law_documents = pickle.load(f)


def retrieve_context(query, k=5, threshold=0.3):
    load_models()

    query_vec = embedder.encode([query])

    D1, I1 = sc_index.search(np.array(query_vec), k)
    D2, I2 = law_index.search(np.array(query_vec), k)

    sc_results = []
    law_results = []

    # 🔹 Supreme Court filtering
    for score, idx in zip(D1[0], I1[0]):
        if score > threshold:
            sc_results.append(sc_documents[idx])

    # 🔹 Law filtering
    for score, idx in zip(D2[0], I2[0]):
        if score > threshold:
            law_results.append(law_documents[idx])

    # 🔥 KEYWORD BOOST (CRITICAL FOR STATUTES)
    q_lower = query.lower()

    if any(token.isdigit() for token in q_lower.split()):
        for doc in law_documents:
            if any(token in doc.lower() for token in q_lower.split() if token.isdigit()):
                law_results.insert(0, doc)
                break

    # 🔹 Empty check
    if not sc_results and not law_results:
        return ""

    # 🔹 Build context
    context = ""

    if sc_results:
        context += "\n\n--- Supreme Court Judgments ---\n"
        context += "\n\n".join(sc_results[:2])

    if law_results:
        context += "\n\n--- Statutory Provisions ---\n"
        context += "\n\n".join(law_results[:2])

    return context

def detect_section_query(query):
    """
    Detect:
    IPC 420
    IPC section 420
    Section 420 IPC
    CRPC 420
    """

    query = query.lower()

    act_pattern = r"(ipc|crpc|cpc|hma|iea|mva|nia)"
    section_pattern = r"section\s*(\d+)|\b(\d+)\b"

    act_match = re.search(act_pattern, query)
    section_match = re.search(section_pattern, query)

    act = act_match.group(1) if act_match else None

    section = None
    if section_match:
        nums = [g for g in section_match.groups() if g]
        if nums:
            section = nums[0]

    if act and section:
        return act.upper(), section

    # fallback: only section
    if section:
        return None, section

    return None, None

def direct_section_lookup(act, section_number):
    """
    Smart legal lookup with priority:
    1. Exact act match
    2. If no act → prefer IPC
    3. Then others
    """

    # ⭐ DEBUG (ADD HERE)
    print("🔥 LOOKUP ACT:", act)
    print("🔥 LOOKUP SECTION:", section_number)

    ipc_results = []
    other_results = []

    for text in law_documents:
        text_low = text.lower()

        # Skip if section not present
        if f"section {section_number}" not in text_low:
            continue

        # ⭐ If act specified → strict filter
        if act:
            if act.lower() in text_low:
                return [text]
            continue

        # ⭐ If no act → prefer IPC
        if "ipc" in text_low:
            ipc_results.append(text)
        else:
            other_results.append(text)

    # ⭐ Priority return
    if ipc_results:
        return ipc_results[:2]

    return other_results[:2]

def retrieve_context(query, k=5, threshold=0.3):
    load_models()

    # ⭐ STEP A — section routing
    act, section = detect_section_query(query)

    if section:
        print("🔥 SECTION QUERY DETECTED:", act, section)

        direct_results = direct_section_lookup(act, section)

        if direct_results:
            return "\n\n--- Statutory Provisions ---\n" + "\n\n".join(direct_results)
    # ⭐ STEP B — fallback semantic search