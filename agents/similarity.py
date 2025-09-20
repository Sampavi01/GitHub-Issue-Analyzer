import os
import pickle
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
try:
    import faiss
except ImportError:
    faiss = None

DATA_DIR = os.getenv("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)
INDEX_PATH = os.path.join(DATA_DIR, "faiss.index")
MAPPING_PATH = os.path.join(DATA_DIR, "mapping.pkl")
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

logger = logging.getLogger(__name__)

embed_model = None
faiss_index = None
id_mapping = []
embed_dim = None

def init_embedding_system():
    global embed_model, faiss_index, id_mapping, embed_dim
    embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    embed_dim = embed_model.get_sentence_embedding_dimension()
    if faiss is None:
        logger.warning("FAISS not installed")
        return
    if os.path.exists(INDEX_PATH) and os.path.exists(MAPPING_PATH):
        faiss_index = faiss.read_index(INDEX_PATH)
        with open(MAPPING_PATH, "rb") as f:
            id_mapping = pickle.load(f)
        if faiss_index.d != embed_dim:
            faiss_index = faiss.IndexFlatIP(embed_dim)
            id_mapping = []
    else:
        faiss_index = faiss.IndexFlatIP(embed_dim)

def save_faiss():
    if faiss_index is None: return
    faiss.write_index(faiss_index, INDEX_PATH)
    with open(MAPPING_PATH, "wb") as f:
        pickle.dump(id_mapping, f)

def build_issue_embeddings_and_index(owner: str, repo: str, issues: list):
    global id_mapping
    if not issues: return 0
    texts, keys = [], []
    for it in issues:
        key = f"{owner}/{repo}#{it['number']}"
        text = (it.get('title') or "") + "\n" + (it.get('body') or "")
        texts.append(text)
        keys.append(key)
    vectors = embed_model.encode(texts, convert_to_numpy=True)
    vectors = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9)
    vectors = vectors.astype('float32')
    faiss_index.add(vectors)
    id_mapping.extend(keys)
    save_faiss()
    return len(keys)

def search_similar(text: str, top_k: int = 5):
    vec = embed_model.encode([text], convert_to_numpy=True)
    vec = vec / (np.linalg.norm(vec) + 1e-9)
    vec = vec.astype('float32')
    D, I = faiss_index.search(vec, top_k)
    results = [{"issue_key": id_mapping[idx], "score": float(score)} for idx, score in zip(I[0], D[0])]
    return results
