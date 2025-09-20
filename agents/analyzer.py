# agents/analyzer.py
from collections import defaultdict
from typing import Optional, Dict, List, Any
from agents.graph_builder import get_neo4j_driver, set_issue_category

def categorize_issue(title: str, body: str, labels: Optional[List[str]]) -> str:
    text = f"{(title or '')} {(body or '')}".lower()
    labels = [l.lower() for l in (labels or [])]

    if any(l in labels for l in ("bug", "bugs")):
        if any(k in text for k in ("ui", "button", "screen", "layout", "css", "ux", "render")):
            return "UI Bug"
        if any(k in text for k in ("crash", "exception", "segfault", "traceback", "error")):
            return "Crash Bug"
        if any(k in text for k in ("slow", "performance", "latency", "lag", "timeout", "memory")):
            return "Performance Bug"
        if any(k in text for k in ("auth", "login", "token", "permission", "access")):
            return "Auth Bug"
        return "Other Bug"

    if any(l in labels for l in ("enhancement", "feature", "proposal")):
        if any(k in text for k in ("api", "backend", "server", "db", "database")):
            return "Backend Feature"
        if any(k in text for k in ("ui", "ux", "layout", "design")):
            return "UI Feature"
        return "General Feature"

    if any(l in labels for l in ("doc", "docs", "documentation", "readme")):
        return "Documentation"

    # fallback: detect from text
    if any(k in text for k in ("documentation", "readme", "docs")):
        return "Documentation"
    if any(k in text for k in ("feature request", "feature:", "enhancement")):
        return "Feature Request"
    if any(k in text for k in ("error", "exception", "fix", "bug", "crash")):
        return "Other Bug"

    return "Uncategorized"

def categorize_issues(owner: str, repo: str, include_samples: bool = True, persist: bool = False) -> Dict[str, Any]:
    driver = get_neo4j_driver()
    counts = defaultdict(int)
    samples = defaultdict(list)

    full_name = f"{owner}/{repo}"
    query = """
    MATCH (r:Repo {full_name:$full_name})-[:HAS_ISSUE]->(i:Issue)
    RETURN i.number AS number, i.title AS title, i.body AS body, i.labels AS labels
    """

    with driver.session() as session:
        results = session.run(query, full_name=full_name)
        for record in results:
            title = record.get("title") or ""
            body = record.get("body") or ""
            labels = record.get("labels") or []
            number = record.get("number")
            cat = categorize_issue(title, body, labels)
            counts[cat] += 1
            if include_samples and len(samples[cat]) < 3:
                samples[cat].append({"number": number, "title": title})
            if persist:
                try:
                    set_issue_category(owner, repo, number, cat)
                except Exception:
                    pass

    return {"counts": dict(counts), "samples": dict(samples)}

def get_issue_types(owner: Optional[str] = None, repo: Optional[str] = None) -> Dict[str, int]:
    driver = get_neo4j_driver()
    if owner and repo:
        full_name = f"{owner}/{repo}"
        label_query = """
        MATCH (r:Repo {full_name:$full_name})-[:HAS_ISSUE]->(i:Issue)
        UNWIND (CASE WHEN i.labels IS NULL THEN [] ELSE i.labels END) AS label
        RETURN label, count(*) AS cnt
        """
        unlabeled_query = """
        MATCH (r:Repo {full_name:$full_name})-[:HAS_ISSUE]->(i:Issue)
        WHERE i.labels IS NULL OR size(i.labels)=0
        RETURN count(i) AS cnt
        """
        params = {"full_name": full_name}
    else:
        label_query = """
        MATCH (i:Issue)
        UNWIND (CASE WHEN i.labels IS NULL THEN [] ELSE i.labels END) AS label
        RETURN label, count(*) AS cnt
        """
        unlabeled_query = """
        MATCH (i:Issue)
        WHERE i.labels IS NULL OR size(i.labels)=0
        RETURN count(i) AS cnt
        """
        params = {}

    counts: Dict[str, int] = {}
    with driver.session() as session:
        res = session.run(label_query, **params)
        for r in res:
            lbl = r["label"]
            cnt = r["cnt"]
            if lbl is None:
                continue
            counts[str(lbl)] = int(cnt)
        res2 = session.run(unlabeled_query, **params)
        unlabeled_cnt = 0
        row = res2.single()
        if row:
            unlabeled_cnt = int(row["cnt"] or 0)
        counts["__unlabeled__"] = unlabeled_cnt

    return counts
