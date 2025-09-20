# agents/graph_builder.py
from neo4j import GraphDatabase
from typing import Dict, Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password")

neo4j_driver = None

def get_neo4j_driver():
    global neo4j_driver
    if neo4j_driver is None:
        neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    return neo4j_driver

def ensure_neo4j_constraints():
    driver = get_neo4j_driver()
    with driver.session() as session:
        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Repo) REQUIRE r.full_name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Issue) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:PR) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Developer) REQUIRE d.login IS UNIQUE",
        ]
        for q in queries:
            try:
                session.run(q)
            except Exception:
                pass

def upsert_repo_node(owner: str, repo: str, readme: str = "", description: str = ""):
    driver = get_neo4j_driver()
    with driver.session() as session:
        full_name = f"{owner}/{repo}"
        session.run(
            "MERGE (r:Repo {full_name:$full_name}) "
            "SET r.owner=$owner, r.name=$repo, r.readme=$readme, r.description=$description",
            full_name=full_name, owner=owner, repo=repo,
            readme=readme, description=description
        )

def upsert_developer_node(login: str, url: Optional[str] = None):
    driver = get_neo4j_driver()
    with driver.session() as session:
        session.run(
            "MERGE (d:Developer {login:$login}) SET d.url=$url",
            login=login, url=url
        )

def upsert_issue_node(owner: str, repo: str, issue: Dict):
    driver = get_neo4j_driver()
    with driver.session() as session:
        issue_key = f"{owner}/{repo}#{issue['number']}"
        labels_raw = issue.get('labels', []) or []
        # labels in GitHub can be list of dicts or strings; normalize to list[str]
        labels = []
        for lab in labels_raw:
            if isinstance(lab, dict) and 'name' in lab:
                labels.append(lab['name'])
            else:
                labels.append(str(lab))

        session.run(
            "MERGE (i:Issue {id:$id}) "
            "SET i.number=$number, i.title=$title, i.body=$body, i.url=$url, "
            "i.state=$state, i.created_at=$created_at, i.closed_at=$closed_at, i.labels=$labels",
            id=issue_key, number=issue['number'], title=issue.get('title'),
            body=issue.get('body') or "", url=issue.get('html_url'),
            state=issue.get('state'), created_at=issue.get('created_at'),
            closed_at=issue.get('closed_at'), labels=labels
        )

        session.run(
            "MATCH (r:Repo {full_name:$full_name}), (i:Issue {id:$id}) "
            "MERGE (r)-[:HAS_ISSUE]->(i)",
            full_name=f"{owner}/{repo}", id=issue_key
        )

        if issue.get('user') and issue['user'].get('login'):
            session.run(
                "MERGE (d:Developer {login:$login}) SET d.url=$url "
                "WITH d MATCH (i:Issue {id:$id}) MERGE (d)-[:CREATED]->(i)",
                login=issue['user']['login'], url=issue['user'].get('html_url'), id=issue_key
            )

def upsert_pr_node(owner: str, repo: str, pr: Dict):
    driver = get_neo4j_driver()
    with driver.session() as session:
        pr_key = f"{owner}/{repo}#PR{pr['number']}"
        session.run(
            "MERGE (p:PR {id:$id}) "
            "SET p.number=$number, p.title=$title, p.body=$body, p.url=$url, "
            "p.state=$state, p.created_at=$created_at, p.merged_at=$merged_at",
            id=pr_key, number=pr['number'], title=pr.get('title'),
            body=pr.get('body') or "", url=pr.get('html_url'),
            state=pr.get('state'), created_at=pr.get('created_at'), merged_at=pr.get('merged_at')
        )
        session.run(
            "MATCH (r:Repo {full_name:$full_name}), (p:PR {id:$id}) "
            "MERGE (r)-[:HAS_PR]->(p)",
            full_name=f"{owner}/{repo}", id=pr_key
        )
        if pr.get('user') and pr['user'].get('login'):
            session.run(
                "MERGE (d:Developer {login:$login}) SET d.url=$url "
                "WITH d MATCH (p:PR {id:$id}) MERGE (d)-[:AUTHORED]->(p)",
                login=pr['user']['login'], url=pr['user'].get('html_url'), id=pr_key
            )

def link_prs_to_issues_by_closing_text(owner: str, repo: str, prs: List[Dict]):
    import re
    pattern = re.compile(r"(?:close[sd]?|fixe[sd]?|resolve[sd]?)\s+#(\d+)", re.IGNORECASE)
    driver = get_neo4j_driver()
    with driver.session() as session:
        for pr in prs:
            text = (pr.get('title') or "") + "\n" + (pr.get('body') or "")
            matches = pattern.findall(text)
            pr_key = f"{owner}/{repo}#PR{pr['number']}"
            for m in matches:
                issue_key = f"{owner}/{repo}#{int(m)}"
                try:
                    session.run(
                        "MATCH (p:PR {id:$prid}), (i:Issue {id:$iid}) "
                        "MERGE (p)-[:RESOLVES]->(i)",
                        prid=pr_key, iid=issue_key
                    )
                except Exception:
                    pass

def set_issue_category(owner: str, repo: str, number: int, category: str):
    driver = get_neo4j_driver()
    with driver.session() as session:
        issue_key = f"{owner}/{repo}#{number}"
        session.run(
            "MATCH (i:Issue {id:$id}) SET i.category=$category",
            id=issue_key, category=category
        )
