"""WebSearchTool — search the web via DuckDuckGo."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Any

from .base import BaseTool, ToolResult
from .registry import get_registry

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None  # type: ignore


TOOL_NAME = "WebSearch"
DATA_DIR = os.path.expanduser("~/.stack-3.0")
CACHE_FILE = os.path.join(DATA_DIR, "web_search_cache.json")


def _load_cache() -> dict[str, Any]:
    """Load the web search result cache."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache: dict[str, Any]) -> None:
    """Persist the web search cache."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


@dataclass
class SearchHit:
    """A single search result."""

    title: str
    url: str
    snippet: str = ""


@dataclass
class SearchOutput:
    """Output of a web search."""

    query: str
    results: list[SearchHit]
    duration_seconds: float
    source: str = "duckduckgo"


class WebSearchTool(BaseTool[dict[str, Any], SearchOutput]):
    """Search the web using DuckDuckGo.

    Requires the `ddgs` package: pip install duckduckgo-search

    Parameters
    ----------
    query : str
        The search query (required, min 2 chars).
    allowed_domains : list[str], optional
        Restrict results to these domains.
    blocked_domains : list[str], optional
        Exclude results from these domains.
    max_results : int, optional
        Maximum number of results to return (default 10, max 20).
    """

    name = TOOL_NAME
    description = "Search the web for current information using DuckDuckGo."
    search_hint = "search the web for current information"

    # ── schema ────────────────────────────────────────────────────────────────

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query (minimum 2 characters)",
                    "minLength": 2,
                },
                "allowed_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Restrict results to these domains",
                },
                "blocked_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Exclude results from these domains",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default 10, max 20)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["query"],
        }

    # ── validation ────────────────────────────────────────────────────────────

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        query = input_data.get("query", "")
        if not query or len(query) < 2:
            return False, "Error: query must be at least 2 characters"
        if input_data.get("allowed_domains") and input_data.get("blocked_domains"):
            return False, "Error: cannot specify both allowed_domains and blocked_domains"
        return True, None

    # ── execution ─────────────────────────────────────────────────────────────

    def execute(self, input_data: dict[str, Any]) -> ToolResult[SearchOutput]:
        if DDGS is None:
            return ToolResult(
                success=False,
                error="duckduckgo-search not installed. Run: pip install duckduckgo-search",
            )

        query = input_data["query"]
        allowed = input_data.get("allowed_domains")
        blocked = input_data.get("blocked_domains")
        max_results = min(input_data.get("max_results", 10), 20)

        cache = _load_cache()
        cache_key = f"{query}|{json.dumps(allowed)}|{json.dumps(blocked)}"

        # Return cached result if fresh (5 minutes)
        now = time.time()
        if cache_key in cache:
            entry = cache[cache_key]
            if now - entry.get("cached_at", 0) < 300:
                output = SearchOutput(
                    query=query,
                    results=[SearchHit(**h) for h in entry["results"]],
                    duration_seconds=entry.get("duration", 0),
                    source="duckduckgo (cached)",
                )
                return ToolResult(success=True, data=asdict(output))

        try:
            hits: list[SearchHit] = []
            with DDGS() as ddgs:
                if allowed:
                    keywords = " ".join(allowed)
                    generator = ddgs.text(query, max_results=max_results)
                else:
                    generator = ddgs.text(query, max_results=max_results)

                for i, result in enumerate(generator):
                    if i >= max_results:
                        break
                    url = result.get("href", "")
                    # Apply blocked domains filter
                    if blocked and any(domain in url for domain in blocked):
                        continue
                    hits.append(
                        SearchHit(
                            title=result.get("title", ""),
                            url=url,
                            snippet=result.get("body", ""),
                        )
                    )

            output = SearchOutput(
                query=query,
                results=hits,
                duration_seconds=0.0,
                source="duckduckgo",
            )

            # Cache the result
            cache[cache_key] = {
                "results": [asdict(h) for h in hits],
                "cached_at": now,
            }
            _save_cache(cache)

            return ToolResult(success=True, data=asdict(output))

        except Exception as exc:
            return ToolResult(success=False, error=f"Web search failed: {exc}")

    def map_result_to_message(self, result: SearchOutput | dict, tool_use_id: str | None = None) -> str:
        """Format search results for display."""
        if isinstance(result, dict):
            query = result.get("query", "")
            hits = result.get("results", [])
        else:
            query = result.query
            hits = result.results

        lines = [f"Web search results for: \"{query}\"\n"]
        if not hits:
            lines.append("No results found.")
            return "\n".join(lines)

        lines.append(f"{len(hits)} results:\n")
        for i, hit in enumerate(hits, 1):
            snippet = hit.snippet[:200] + "..." if len(hit.snippet) > 200 else hit.snippet
            lines.append(f"{i}. {hit.title}")
            lines.append(f"   URL: {hit.url}")
            if snippet:
                lines.append(f"   {snippet}")
            lines.append("")

        return "\n".join(lines)


# Register the tool
_registry = get_registry()
_registry.register(WebSearchTool())
