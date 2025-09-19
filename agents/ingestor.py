"""
Ingestor Agent
Fetches issues and PRs from GitHub and inserts them into Neo4j KG.
"""
import os
import requests
import logging
from typing import List, Dict
from agents.graph_builder import upsert_repo_node, upsert_issue_node, upsert_pr_node, link_prs_to_issues_by_closing_text
from agents.similarity import build_issue_embeddings_and_index

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
logger = logging.getLogger(__name__)

# -------------------------------
# GitHub API helpers
# -------------------------------
def github_headers():
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

def fetch_issues(owner: str, repo: str, max_issues: int = 200) -> List[Dict]:
    issues, page, per_page, fetched = [], 1, 100, 0
    while fetched < max_issues:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        resp = requests.get(url, headers=github_headers(), params={"state":"all", "per_page":per_page, "page":page})
        batch = resp.json()
        if not batch: break
        for it in batch:
            if "pull_request" in it: continue
            issues.append(it); fetched += 1
            if fetched >= max_issues: break
        page += 1
    logger.info(f"Fetched {len(issues)} issues from {owner}/{repo}")
    return issues

def fetch_pull_requests(owner: str, repo: str, max_prs: int = 100) -> List[Dict]:
    prs, page, per_page, fetched = [], 1, 100, 0
    while fetched < max_prs:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        resp = requests.get(url, headers=github_headers(), params={"state":"all", "per_page":per_page, "page":page})
        batch = resp.json()
        if not batch: break
        for it in batch:
            prs.append(it); fetched += 1
            if fetched >= max_prs: break
        page += 1
    logger.info(f"Fetched {len(prs)} PRs from {owner}/{repo}")
    return prs

# -------------------------------
# Main ingestion function
# -------------------------------
def ingest_repo(owner: str, repo: str, max_issues: int = 200):
    upsert_repo_node(owner, repo)
    issues = fetch_issues(owner, repo, max_issues)
    prs = fetch_pull_requests(owner, repo, max_prs=int(max_issues/2))

    for it in issues: upsert_issue_node(owner, repo, it)
    for pr in prs: upsert_pr_node(owner, repo, pr)
    link_prs_to_issues_by_closing_text(owner, repo, prs)
    indexed = build_issue_embeddings_and_index(owner, repo, issues)
    return {"status":"ok","issues_ingested":len(issues),"prs_ingested":len(prs),"indexed":indexed}
