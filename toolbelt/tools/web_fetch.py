"""WebFetchTool - Web content fetching and parsing for Stack 3.0"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from .base import BaseTool, ToolResult
from .registry import tool_registry


def _extract_readable_content(html: str) -> str:
    """Extract readable text from HTML."""
    # Remove scripts and styles
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class WebFetchTool(BaseTool):
    """Fetch and extract readable content from URLs."""

    name = "web_fetch"
    description = "Fetch web page content and extract readable text"

    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch"
            },
            "max_chars": {
                "type": "number",
                "default": 10000,
                "description": "Maximum characters to return"
            },
            "extract_links": {
                "type": "boolean",
                "default": False,
                "description": "Extract links from the page"
            }
        },
        "required": ["url"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Fetch URL content."""
        url = input_data.get("url")
        max_chars = input_data.get("max_chars", 10000)
        extract_links = input_data.get("extract_links", False)

        if not HAS_HTTPX:
            return ToolResult(success=False, error="httpx library not installed")

        parsed = urlparse(url)
        if not parsed.scheme:
            return ToolResult(success=False, error="Invalid URL - missing scheme")

        try:
            response = httpx.get(url, timeout=15.0, follow_redirects=True)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return ToolResult(success=True, data={
                    "url": url,
                    "content": response.text[:max_chars],
                    "content_type": content_type,
                    "status_code": response.status_code
                })

            text = _extract_readable_content(response.text)
            text = text[:max_chars]

            result = {
                "url": url,
                "content": text,
                "content_type": content_type,
                "status_code": response.status_code,
                "fetched_at": datetime.now().isoformat()
            }

            if extract_links:
                links = re.findall(r'href=["\']([^"\']+)["\']', response.text)
                result["links"] = links[:50]

            return ToolResult(success=True, data=result)

        except httpx.TimeoutException:
            return ToolResult(success=False, error=f"Timeout fetching {url}")
        except httpx.HTTPError as e:
            return ToolResult(success=False, error=f"HTTP error: {e}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class WebFetchMetaTool(BaseTool):
    """Get metadata from a URL without full content."""

    name = "web_fetch_meta"
    description = "Get metadata (title, description, images) from a URL"

    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to analyze"
            }
        },
        "required": ["url"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Get URL metadata."""
        url = input_data.get("url")
        if not HAS_HTTPX:
            return ToolResult(success=False, error="httpx library not installed")

        try:
            response = httpx.get(url, timeout=10.0, follow_redirects=True)
            response.raise_for_status()

            title = re.search(r'<title[^>]*>([^<]+)</title>', response.text, re.IGNORECASE)
            description = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
            og_image = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', response.text, re.IGNORECASE)

            return ToolResult(success=True, data={
                "url": url,
                "title": title.group(1).strip() if title else None,
                "description": description.group(1).strip() if description else None,
                "og_image": og_image.group(1).strip() if og_image else None,
                "status_code": response.status_code
            })

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# Register tools
tool_registry.register(WebFetchTool())
tool_registry.register(WebFetchMetaTool())
