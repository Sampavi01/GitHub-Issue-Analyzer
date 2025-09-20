# agents/ingestor.py
import os
import requests
import logging
import base64
from typing import List, Dict
from dotenv import load_dotenv
from agents.graph_builder import (
    upsert_repo_node, upsert_issue_node, upsert_pr_node, link_prs_to_issues_by_closing_text
)

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API = os.getenv("GITHUB_API", "https://api.github.com")

def github_headers() -> Dict[str, str]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

def fetch_readme(owner: str, repo: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
    resp = requests.get(url, headers=github_headers())
    if resp.status_code == 200:
        data = resp.json()
        content = base64.b64decode(data.get("content", "")).decode("utf-8")
        return content
    return ""

def fetch_repo_description(owner: str, repo: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    resp = requests.get(url, headers=github_headers())
    if resp.status_code == 200:
        return resp.json().get("description", "") or ""
    return ""

def fetch_issues(owner: str, repo: str, max_issues: int = 200) -> List[Dict]:
    issues, page, per_page, fetched = [], 1, 100, 0
    while fetched < max_issues:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
        resp = requests.get(url, headers=github_headers(), params={
            "state": "all", "per_page": per_page, "page": page
        })
        batch = resp.json()
        if isinstance(batch, dict) and "message" in batch:
            raise RuntimeError(f"GitHub API error: {batch['message']}")
        if not batch:
            break
        for it in batch:
            # skip PRs returned in issues endpoint
            if "pull_request" in it:
                continue
            issues.append(it)
            fetched += 1
            if fetched >= max_issues:
                break
        page += 1
    logger.info(f"Fetched {len(issues)} issues from {owner}/{repo}")
    return issues

def fetch_pull_requests(owner: str, repo: str, max_prs: int = 100) -> List[Dict]:
    prs, page, per_page, fetched = [], 1, 100, 0
    while fetched < max_prs:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
        resp = requests.get(url, headers=github_headers(), params={
            "state": "all", "per_page": per_page, "page": page
        })
        batch = resp.json()
        if isinstance(batch, dict) and "message" in batch:
            raise RuntimeError(f"GitHub API error: {batch['message']}")
        if not batch:
            break
        for it in batch:
            prs.append(it)
            fetched += 1
            if fetched >= max_prs:
                break
        page += 1
    logger.info(f"Fetched {len(prs)} PRs from {owner}/{repo}")
    return prs

def ingest_repo(owner: str, repo: str, max_issues: int = 200):
    readme_content = fetch_readme(owner, repo)
    repo_description = fetch_repo_description(owner, repo)

    upsert_repo_node(owner, repo, readme_content, repo_description)

    issues = fetch_issues(owner, repo, max_issues)
    prs = fetch_pull_requests(owner, repo, max_prs=int(max_issues/2))

    for it in issues:
        upsert_issue_node(owner, repo, it)
    for pr in prs:
        upsert_pr_node(owner, repo, pr)

    link_prs_to_issues_by_closing_text(owner, repo, prs)
    return {"status": "ok", "issues_ingested": len(issues), "prs_ingested": len(prs)}



