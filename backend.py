import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel

from agents.ingestor import ingest_repo
from agents.graph_builder import ensure_neo4j_constraints
from agents.similarity import init_embedding_system, search_similar
from agents.categorizer import keyword_categorize
from agents.analytics import get_category_counts, get_top_contributors

# -------------------------------
# Setup
# -------------------------------
app = FastAPI(title="SoftGraph Backend")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------
# Pydantic models
# -------------------------------
class IngestRequest(BaseModel):
    owner: str
    repo: str
    max_issues: int = 200

class QueryRequest(BaseModel):
    text: str
    top_k: int = 5

class CategorizeRequest(BaseModel):
    text: str

# -------------------------------
# Startup: initialize Neo4j + embeddings
# -------------------------------
@app.on_event("startup")
def startup_event():
    ensure_neo4j_constraints()
    init_embedding_system()

# -------------------------------
# API endpoints
# -------------------------------
@app.post("/ingest_repo")
def api_ingest_repo(req: IngestRequest):
    return ingest_repo(req.owner, req.repo, req.max_issues)

@app.post("/query_similar")
def api_query_similar(req: QueryRequest):
    return search_similar(req.text, req.top_k)

@app.post("/categorize_issue")
def api_categorize_issue(req: CategorizeRequest):
    cats = keyword_categorize(req.text)
    return {"categories": cats}

@app.get("/analytics/category_counts")
def api_category_counts():
    return get_category_counts()

@app.get("/analytics/top_contributors")
def api_top_contributors(limit: int = 10):
    return get_top_contributors(limit)

@app.get("/health")
def health_check():
    ok = True
    msgs = []
    try:
        ensure_neo4j_constraints()
    except Exception as e:
        ok = False
        msgs.append(f"Neo4j error: {e}")
    return {"ok": ok, "messages": msgs}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
