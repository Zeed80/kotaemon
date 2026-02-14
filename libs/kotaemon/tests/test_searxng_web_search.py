"""Tests for SearXNG web search retriever."""

from unittest.mock import patch

import pytest
import requests

from kotaemon.indices.retrievers.searxng_web_search import WebSearch


def test_searxng_web_search_returns_results():
    mock_response = type("Response", (), {})()
    mock_response.status_code = 200
    mock_response.json = lambda: {
        "results": [
            {
                "url": "https://example.com/page1",
                "title": "Example Page",
                "content": "Snippet from the page",
            },
            {
                "url": "https://example.com/page2",
                "title": "Another Page",
                "description": "Description as content fallback",
            },
        ]
    }
    mock_response.raise_for_status = lambda: None

    with patch("requests.get", return_value=mock_response):
        ws = WebSearch()
        docs = ws.run("test query")

    assert len(docs) == 1
    assert "Example Page" in docs[0].text
    assert "https://example.com/page1" in docs[0].text
    assert "Snippet from the page" in docs[0].text
    assert "Another Page" in docs[0].text
    assert "Description as content fallback" in docs[0].text
    assert docs[0].metadata["file_name"] == "Web search"


def test_searxng_web_search_empty_results():
    mock_response = type("Response", (), {})()
    mock_response.status_code = 200
    mock_response.json = lambda: {"results": []}
    mock_response.raise_for_status = lambda: None

    with patch("requests.get", return_value=mock_response):
        ws = WebSearch()
        docs = ws.run("test query")

    assert len(docs) == 1
    assert docs[0].text == ""
    assert docs[0].metadata["file_name"] == "Web search"


def test_searxng_web_search_connection_error():
    with patch(
        "requests.get",
        side_effect=requests.RequestException("Connection refused"),
    ):
        ws = WebSearch()
        with pytest.raises(ConnectionError, match="Cannot reach SearXNG"):
            ws.run("test query")
