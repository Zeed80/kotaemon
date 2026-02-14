"""Web search via self-hosted SearXNG. No API key required."""

import requests

from flowsettings_config import config
from kotaemon.base import BaseComponent, RetrievedDocument

SEARXNG_URL = config("SEARXNG_URL", default="http://localhost:8080").rstrip("/")


class WebSearch(BaseComponent):
    """Web search via self-hosted SearXNG instance.

    Privacy-focused: no API keys, queries go only to your SearXNG.
    Requires SearXNG running (e.g. docker run -p 8080:8080 searxng/searxng).
    """

    def run(
        self,
        text: str,
        *args,
        **kwargs,
    ) -> list[RetrievedDocument]:
        url = f"{SEARXNG_URL}/search"
        params = {"q": text, "format": "json"}
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise ConnectionError(
                f"Cannot reach SearXNG at {SEARXNG_URL}. "
                "Start SearXNG (e.g. docker run -p 8080:8080 searxng/searxng) "
                "or set SEARXNG_URL."
            ) from e
        except ValueError as e:
            raise ValueError(
                f"SearXNG at {SEARXNG_URL} did not return JSON. "
                "Ensure format=json is enabled in SearXNG settings."
            ) from e

        results = data.get("results") or []
        if not results:
            return [
                RetrievedDocument(
                    text="",
                    metadata={
                        "file_name": "Web search",
                        "type": "table",
                        "llm_trulens_score": 1.0,
                    },
                )
            ]

        parts = []
        for r in results:
            url_val = r.get("url", "")
            title = r.get("title", "")
            content = r.get("content") or r.get("description", "")
            if url_val:
                parts.append(f"###URL: [{title or url_val}]({url_val})\n\n{content}")

        context = "\n\n".join(parts)
        return [
            RetrievedDocument(
                text=context,
                metadata={
                    "file_name": "Web search",
                    "type": "table",
                    "llm_trulens_score": 1.0,
                },
            )
        ]

    def generate_relevant_scores(self, text, documents: list[RetrievedDocument]):
        return documents
