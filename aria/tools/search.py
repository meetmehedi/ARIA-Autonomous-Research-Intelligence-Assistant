import sys
from duckduckgo_search import DDGS
from aria.logging_setup import get_logger

logger = get_logger(__name__)

def search_web(query: str, max_results: int = 5) -> list:
    """Performs a web search using DuckDuckGo.

    Returns a list of dicts with keys: 'title', 'href', and 'body'.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", "")
                }
                for r in results
            ]
    except Exception as e:
        logger.warning("Error searching DDG for %r: %s", query, e)
        return []

if __name__ == "__main__":
    # Test DDG search
    print("Testing DuckDuckGo Search...")
    res = search_web("continual learning latest papers", max_results=2)
    for i, r in enumerate(res):
        print(f"\n[{i+1}] {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}")
