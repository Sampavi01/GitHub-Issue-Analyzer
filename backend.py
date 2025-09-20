import logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict

from agents.ingestor import ingest_repo
from agents.graph_builder import ensure_neo4j_constraints
from agents.analyzer import analyze_issues, get_last_ingested_repo
from agents.reporter import generate_report

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

class TaskInputRequest(BaseModel):
    workers_per_task: Dict[str, int]  # user fills in number of employees per main issue type

# -------------------------------
# Startup: initialize Neo4j
# -------------------------------
@app.on_event("startup")
def startup_event():
    ensure_neo4j_constraints()

# -------------------------------
# API endpoints
# -------------------------------
@app.post("/ingest_repo")
def api_ingest_repo(req: IngestRequest):
    """
    Ingest repo metadata, README, issues, labels, and PRs.
    """
    return ingest_repo(req.owner, req.repo, req.max_issues)

@app.get("/analyze_issues")
def api_analyze_issues():
    """
    Display issue categories (subtypes) to user before worker allocation.
    """
    repo_info = get_last_ingested_repo()
    if not repo_info:
        return {"error": "No repo ingested yet. Please ingest a repo first."}

    owner, repo = repo_info["owner"], repo_info["repo"]
    issue_categories = analyze_issues(owner, repo)  # category -> count
    return {"repo": f"{owner}/{repo}", "issue_categories": issue_categories}

@app.post("/generate_report")
def api_generate_report(req: TaskInputRequest):
    """
    Generate report using previously analyzed issue categories and user input
    for workers per main issue type.
    """
    repo_info = get_last_ingested_repo()
    if not repo_info:
        return {"error": "No repo ingested yet. Please ingest a repo first."}

    owner, repo = repo_info["owner"], repo_info["repo"]
    issue_categories = analyze_issues(owner, repo)  # get subtypes

    # Generate recommendation report based on user input
    report = generate_report(issue_categories, req.workers_per_task)
    return {"report": report, "issue_categories": issue_categories}

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
