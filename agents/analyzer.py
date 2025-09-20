from agents.graph_builder import get_neo4j_driver
from collections import defaultdict
from typing import Dict, Optional

# Define bug subtypes based on keywords
BUG_KEYWORDS = {
    "UI": ["ui", "button", "layout", "screen", "css"],
    "Performance": ["slow", "lag", "performance", "memory"],
    "Security": ["vulnerable", "security", "auth", "permission"],
    "Crash": ["crash", "exception", "error", "fail"],
}

def analyze_issues(owner: str, repo: str) -> Dict[str, int]:
    """
    Categorize issues into detailed types/subtypes using labels + title/body.
    Returns a dict: category -> count
    """
    driver = get_neo4j_driver()
    issue_counts = defaultdict(int)

    with driver.session() as session:
        query = """
        MATCH (i:Issue)<-[:HAS_ISSUE]-(r:Repo {full_name:$full_name})
        RETURN i.title AS title, i.body AS body, i.labels AS labels
        """
        results = session.run(query, full_name=f"{owner}/{repo}")

        for record in results:
            title = record["title"] or ""
            body = record["body"] or ""
            labels = record["labels"] or []

            main_type = labels[0] if labels else "Other"
            sub_type = "General"

            if main_type.lower() == "bug":
                text = (title + " " + body).lower()
                for k, keywords in BUG_KEYWORDS.items():
                    if any(word in text for word in keywords):
                        sub_type = k
                        break

            category = f"{main_type} - {sub_type}"
            issue_counts[category] += 1

    return dict(issue_counts)

def get_last_ingested_repo() -> Optional[Dict[str, str]]:
    """
    Returns the last ingested repo from Neo4j to avoid asking repo repeatedly.
    """
    driver = get_neo4j_driver()
    with driver.session() as session:
        query = """
        MATCH (r:Repo) 
        RETURN r.owner AS owner, r.name AS repo 
        ORDER BY r.full_name DESC LIMIT 1
        """
        result = session.run(query)
        record = result.single()
        if record:
            return {"owner": record["owner"], "repo": record["repo"]}
    return None
