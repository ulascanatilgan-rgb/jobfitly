"""OpenAI-only discovery safety checks. No external API keys or network needed."""
import json

import job_search


class FakeResponse:
    status_code = 200

    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self.content


def _payload(url):
    entry = {
        "title": "Operations Manager",
        "company": "Example Employer",
        "city": "Brussels",
        "country": "Belgium",
        "description": "Coordinate teams and manage operations.",
        "url": url,
        "published": "2026-11-21",
        "source": "Employer Careers"
    }
    return {
        "status": "completed",
        "output": [
            {
                "type": "web_search_call",
                "action": {
                    "sources": [{"url": "https://careers.example.org/jobs/1234"}]
                }
            },
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": json.dumps({"jobs": [entry]})}
                ]
            }
        ]
    }


def test_cited_job_is_accepted(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setattr(job_search.requests, "post", lambda *args, **kwargs: FakeResponse(_payload("https://careers.example.org/jobs/1234")))
    jobs = job_search.search_jobs({"country": "Belgium", "city": "Brussels", "cv_text_preview": "Operations manager"})
    assert len(jobs) == 1
    assert jobs[0]["url"] == "https://careers.example.org/jobs/1234"
    assert jobs[0]["source"] == "OpenAI web search"


def test_hallucinated_job_url_is_rejected(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setattr(job_search.requests, "post", lambda *args, **kwargs: FakeResponse(_payload("https://careers.example.org/jobs/unknown")))
    assert job_search.search_jobs({"country": "Belgium", "city": "Brussels"}) == []


def test_search_does_not_send_personal_contacts(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    captured = {}
    def fake_post(*args, **kwargs):
        captured.update(kwargs)
        return FakeResponse(_payload("https://careers.example.org/jobs/1234"))
    monkeypatch.setattr(job_search.requests, "post", fake_post)
    job_search.search_jobs({"cv_text_preview": "Alex alex@example.com +32 470 123 456"})
    prompt = captured["json"]["input"][1]["content"]
    assert "alex@example.com" not in prompt
    assert "+32 470 123 456" not in prompt
    assert captured["json"]["tools"][0]["type"] == "web_search"


def test_only_https_direct_listing_urls():
    assert job_search._canonical("http://example.com/jobs/123") is None
    assert job_search._canonical("https://example.com/") is None
    assert job_search._canonical("https://example.com/jobs/123") == ("example.com", "/jobs/123")
