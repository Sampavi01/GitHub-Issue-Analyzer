"""
Categorizer Agent
Classifies issues into categories based on keywords.
"""

CATEGORY_KEYWORDS = {
    "frontend": ["ui","frontend","css","html","react","vue","angular","button","layout"],
    "backend": ["backend","api","server","database","db","sql","query"],
    "auth": ["auth","login","authentication","oauth","token","jwt"],
    "performance": ["performance","slow","latency","optimi"],
    "security": ["security","vulnerab","xss","csrf","injection"],
    "documentation": ["doc","documentation","readme","guide"],
}

def keyword_categorize(text: str):
    text_l = text.lower()
    matches = []
    for cat, keys in CATEGORY_KEYWORDS.items():
        for k in keys:
            if k in text_l:
                matches.append(cat)
                break
    if not matches: matches=["uncategorized"]
    return matches
