# backend.py
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Optional

from agents.ingestor import ingest_repo
from agents.graph_builder import ensure_neo4j_constraints
from agents.analyzer import categorize_issues, get_issue_types
from agents.reporter import generate_report

# Optionally init similarity if present
try:
    from agents.similarity import init_embedding_system
except Exception:
    def init_embedding_system():
        return None

app = FastAPI(title="SoftGraph Backend")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IngestRequest(BaseModel):
    owner: str
    repo: str
    max_issues: int = 200

class RepoRequest(BaseModel):
    owner: str
    repo: str

class WorkersInput(BaseModel):
    owner: str
    repo: str
    workers_per_task: Dict[str, int]  # user fills counts per category

@app.on_event("startup")
def startup_event():
    ensure_neo4j_constraints()
    init_embedding_system()

@app.post("/ingest_repo")
def api_ingest_repo(req: IngestRequest):
    return ingest_repo(req.owner, req.repo, req.max_issues)

@app.post("/get_issue_types")
def api_get_issue_types(req: RepoRequest):
    """
    Returns raw label counts + __unlabeled__ so UI can present labels to user.
    """
    types = get_issue_types(req.owner, req.repo)
    return {"issue_types": types}

@app.post("/get_issue_categories")
def api_get_issue_categories(req: RepoRequest):
    """
    Returns semantic categories and small samples plus a worker-template:
    {
      "categories": {"UI Bug": {"count": 5, "samples": [...], "workers": None}, ... }
    }
    """
    data = categorize_issues(req.owner, req.repo, include_samples=True, persist=False)
    counts = data.get("counts", {})
    samples = data.get("samples", {})
    # build template for front-end / Swagger
    template = {}
    for cat, cnt in counts.items():
        template[cat] = {"count": cnt, "samples": samples.get(cat, []), "workers": None}
    return {"categories": template}

@app.post("/submit_workers_and_report")
def api_submit_workers_and_report(req: WorkersInput):
    """
    Endpoint the user calls after filling workers_per_task (in Swagger or UI).
    Returns the final reporter output.
    """
    data = categorize_issues(req.owner, req.repo, include_samples=False, persist=False)
    counts = data.get("counts", {})
    report = generate_report(counts, req.workers_per_task)
    return {"report": report}

@app.post("/persist_categories")
def api_persist_categories(req: RepoRequest):
    """
    OPTIONAL: classify all issues and store i.category in Neo4j for later use.
    """
    categorize_issues(req.owner, req.repo, include_samples=False, persist=True)
    return {"status": "ok", "message": "categories persisted for repo"}

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
