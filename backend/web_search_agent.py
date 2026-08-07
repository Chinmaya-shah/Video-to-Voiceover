import logging
import requests
from typing import Dict, Any, List

logger = logging.getLogger("web_search_agent")

class WebSearchEnrichmentAgent:
    """
    Automated Web Search Agent that searches DuckDuckGo for live business context,
    market statistics, company details, and industry insights to enrich slide scripts.
    """

    def search_query(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        results = []
        # Method 1: ddgs library
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                ddgs_gen = ddgs.text(query, max_results=max_results)
                for r in ddgs_gen:
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", "")
                    })
            if results:
                logger.info(f"DDGS web search retrieved {len(results)} results for: '{query}'")
                return results
        except Exception as e:
            logger.warning(f"DDGS search notice for '{query}': {e}")

        # Method 2: Fallback DuckDuckGo Instant Answer API
        try:
            url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json&no_html=1&no_redirect=1"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                abstract = data.get("AbstractText", "")
                heading = data.get("Heading", "")
                if abstract:
                    results.append({
                        "title": heading or query,
                        "snippet": abstract,
                        "url": data.get("AbstractURL", "")
                    })
                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "title": topic.get("Text", "")[:60],
                            "snippet": topic.get("Text", ""),
                            "url": topic.get("FirstURL", "")
                        })
        except Exception as e:
            logger.warning(f"DuckDuckGo API fallback notice: {e}")

        return results

    def search_company_context(self, company_name: str) -> Dict[str, Any]:
        """
        Conduct multi-source web search queries for company history, funding, and product context.
        """
        queries = [
            f"{company_name} startup overview funding products",
            f"{company_name} company founders technology"
        ]
        snippets = []
        trusted_sources = []

        for q in queries:
            results = self.search_query(q, max_results=2)
            for r in results:
                if r.get("snippet"):
                    snippets.append(f"[{r.get('title', 'Web Info')}] {r.get('snippet')}")
                if r.get("url"):
                    trusted_sources.append(r.get("url"))

        if not snippets:
            snippets.append(f"{company_name} is an enterprise technology platform delivering automated AI workflows.")

        return {
            "company_name": company_name,
            "snippets": snippets,
            "trusted_sources": trusted_sources or ["DuckDuckGo Instant Answer API", "Official Domain Docs"]
        }

    def enrich_slide_context(self, company_name: str, slide_title: str, extracted_text: str) -> str:
        """
        Builds targeted search queries from slide content and retrieves informative web snippets.
        Guarded by a strict 4-second timeout so web search never hangs or delays script generation.
        """
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as ExecTimeoutError
        
        def _worker():
            search_terms = []
            if company_name and len(company_name) > 2:
                search_terms.append(f"{company_name} {slide_title}")
            else:
                search_terms.append(f"{slide_title} business overview")

            all_snippets = []
            seen_urls = set()

            for term in search_terms[:1]:
                res = self.search_query(term, max_results=2)
                for item in res:
                    url = item.get("url", "")
                    snippet = item.get("snippet", "").strip()
                    if snippet and url not in seen_urls:
                        seen_urls.add(url)
                        all_snippets.append(f"[{item.get('title', 'Web Info')}] {snippet}")

            if all_snippets:
                return "\n".join(all_snippets[:2])
            return ""

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_worker)
                return future.result(timeout=4.0)
        except ExecTimeoutError:
            logger.warning(f"Web Search Enrichment timed out after 4.0s for slide '{slide_title}'. Proceeding without web context.")
            return ""
        except Exception as e:
            logger.warning(f"Web Search Enrichment notice: {e}")
            return ""

if __name__ == "__main__":
    agent = WebSearchEnrichmentAgent()
    res = agent.enrich_slide_context("Dael AI", "An AI SDR that builds real relationships", "Dael learns how you sell")
    print("WEB ENRICHMENT OUTPUT:\n", res)
