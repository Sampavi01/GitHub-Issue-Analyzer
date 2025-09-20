from agents.graph_builder import get_neo4j_driver

def get_category_counts():
    driver = get_neo4j_driver()
    with driver.session() as session:
        r = session.run(
            "MATCH (i:Issue)-[:HAS_CATEGORY]->(c:Category) "
            "RETURN c.name as category, count(i) as cnt ORDER BY cnt DESC"
        )
        return {"counts":[{"category":rec["category"],"count":rec["cnt"]} for rec in r]}

def get_top_contributors(limit: int = 10):
    driver = get_neo4j_driver()
    with driver.session() as session:
        r = session.run(
            "MATCH (d:Developer)-[:AUTHORED]->(p:PR) "
            "RETURN d.login as login, count(p) as prs ORDER BY prs DESC LIMIT $limit",
            limit=limit
        )
        return {"top_contributors":[{"login":rec["login"],"prs":rec["prs"]} for rec in r]}
