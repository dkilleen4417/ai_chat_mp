"""Tool definitions and registry for agentic use.

Each tool is a plain Python function that takes keyword arguments and returns a string.
The ToolRegistry converts these into the JSON-schema format expected by models that
support function / tool calling (e.g., Google Gemini).
"""

from __future__ import annotations

from typing import Callable, Dict, List, Any
import streamlit as st
import requests

###############################################################################
# Individual tool implementations
###############################################################################

def brave_search(query: str, num_results: int = 3) -> str:
    """Search the web using Brave Search API and return a formatted string."""
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": st.session_state.brave_api_key,
    }
    params = {"q": query, "count": num_results}

    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search", headers=headers, params=params, timeout=30
        )
        if resp.status_code != 200:
            return f"Brave API error {resp.status_code}: {resp.text}"
        data = resp.json()
        results = data.get("web", {}).get("results", [])[:num_results]
        if not results:
            return "No results found."
        lines: List[str] = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            desc = r.get("description", "")
            lines.append(f"[{i}] {title}\nURL: {url}\n{desc}\n")
        return "\n".join(lines)
    except Exception as exc:  # pylint: disable=broad-except
        return f"Brave search failed: {exc}"


def serper_search(query: str, num_results: int = 3) -> str:
    """Search Google via Serper.dev and return a formatted string."""
    headers = {"X-API-KEY": st.session_state.serper_api_key, "Content-Type": "application/json"}
    params = {"q": query, "num": num_results}
    try:
        resp = requests.get("https://google.serper.dev/search", headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            return f"Serper API error {resp.status_code}: {resp.text}"
        data = resp.json()
        lines: List[str] = []
        # Answer / knowledge boxes
        ab = data.get("answerBox")
        if ab:
            lines.append(f"[Featured] {ab.get('title','')}{ab.get('answer','')}{ab.get('snippet','')}\n")
        kg = data.get("knowledgeGraph")
        if kg:
            lines.append(f"[Knowledge] {kg.get('title','')}: {kg.get('description','')}\n")
        for i, r in enumerate(data.get("organic", [])[:num_results], 1):
            lines.append(f"[{i}] {r.get('title')}\nURL: {r.get('link')}\n{r.get('snippet')}\n")
        return "\n".join(lines) if lines else "No results found."
    except Exception as exc:  # pylint: disable=broad-except
        return f"Serper search failed: {exc}"

###############################################################################
# Tool registry
###############################################################################

class ToolRegistry:
    """Stores callable tools and produces JSON schemas for models."""

    def __init__(self) -> None:
        self._fns: Dict[str, Callable[..., str]] = {}
        self._descriptions: Dict[str, str] = {}

    def register_tool(self, fn: Callable[..., str], name: str, description: str) -> None:
        self._fns[name] = fn
        self._descriptions[name] = description

    # ---------------------------------------------------------------------
    # Access helpers
    # ---------------------------------------------------------------------
    def get_callable(self, name: str) -> Callable[..., str] | None:
        return self._fns.get(name)

    def list_tool_configs(self) -> List[Dict[str, Any]]:
        """Return JSON-schema tool definitions compatible with Gemini."""
        defs: List[Dict[str, Any]] = []
        for name, desc in self._descriptions.items():
            defs.append(
                {
                    "name": name,
                    "description": desc,
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to run",
                            }
                        },
                        "required": ["query"],
                    },
                }
            )
        # Gemini expects each tool wrapper with "function_declarations"
        return [{"function_declarations": [d]} for d in defs]


# -------------------------------------------------------------------------
# Global registry with default tools
# -------------------------------------------------------------------------

tool_registry = ToolRegistry()
tool_registry.register_tool(brave_search, "brave_search", "Search the web using Brave Search API.")
tool_registry.register_tool(serper_search, "serper_search", "Search Google via Serper.dev.")

__all__ = [
    "brave_search",
    "serper_search",
    "tool_registry",
    "ToolRegistry",
]
