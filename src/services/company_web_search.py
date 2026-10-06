"""Fetch company culture references from Tavily, keeping their original URLs."""

import os
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

from src.services.company_loader import load_company_profile
from src.services.company_registry import company_profile_path


TAVILY_SEARCH_URL = "https://api.tavily.com/search"
SEARCH_ALIASES = {
    "toss": "토스",
    "hyundai": "현대자동차",
    "baemin": "배달의민족",
}
SEARCH_TERMS = {
    "toss": ("토스", "toss"),
    "hyundai": ("현대자동차", "hyundai"),
    "baemin": ("배달의민족", "배민", "우아한형제들", "baemin"),
}


def search_company_web(company_id: str, max_results: int = 4) -> list[dict[str, str]]:
    """Search public company pages and return source-backed excerpts."""

    load_dotenv()
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("외부 검색에 TAVILY_API_KEY가 필요합니다.")

    profile = load_company_profile(company_profile_path(company_id))
    search_name = SEARCH_ALIASES.get(company_id, profile.name)
    matching_terms = SEARCH_TERMS.get(company_id, (search_name,))
    queries = [
        f"{search_name} 공식 채용 조직문화 일하는 방식 인재상",
        f"{search_name} 기업문화 협업 의사결정 채용 인터뷰",
    ]
    evidence: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    with httpx.Client(timeout=12) as client:
        for query in queries:
            response = client.post(
                TAVILY_SEARCH_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            response.raise_for_status()

            for item in response.json().get("results", []):
                url = str(item.get("url") or "")
                if (
                    urlparse(url).scheme not in {"http", "https"}
                    or url in seen_urls
                ):
                    continue
                title = str(item.get("title") or "").strip()
                snippet = str(item.get("content") or "").strip()
                if not title or not snippet:
                    continue
                searchable_text = f"{title} {snippet}".casefold()
                if not any(
                    term.casefold() in searchable_text
                    for term in matching_terms
                ):
                    continue
                seen_urls.add(url)
                evidence.append(
                    {
                        "source": title,
                        "text": snippet,
                        "url": url,
                        "source_type": "web",
                        "relevance": "외부 검색 결과 (원문에서 확인)",
                    }
                )
                if len(evidence) >= max_results:
                    return evidence

    return evidence
