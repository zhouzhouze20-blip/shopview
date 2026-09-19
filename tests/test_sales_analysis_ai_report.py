from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))
from services.sales_analysis import ai_report


@pytest.mark.parametrize("style", ["chat_completions", "responses"])
@pytest.mark.parametrize("configured,minimum,expected", [(1200, None, 1200), (1200, 8192, 8192), (16000, 8192, 16000)])
def test_report_specific_output_budget_reaches_provider(monkeypatch, style, configured, minimum, expected):
    monkeypatch.setattr(ai_report, "_load_ai_config", lambda: {
        "provider": "test", "api_style": style, "api_key": "test-key",
        "base_url": "https://example.invalid/v1", "model": "test-model",
        "timeout": 90, "max_output_tokens": configured,
    })
    sent = []
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            if style == "responses":
                return {"status": "completed", "output_text": "完整方案"}
            return {"choices": [{"finish_reason": "stop", "message": {"content": "完整方案"}}]}
    def post(url, **kwargs):
        sent.append(kwargs["json"])
        return Response()
    monkeypatch.setattr(ai_report.requests, "post", post)
    result = ai_report.generate_ai_report({"summary": {}}, min_output_tokens=minimum)
    assert result["status"] == "success"
    assert result["report"] == "完整方案"
    field = "max_output_tokens" if style == "responses" else "max_tokens"
    assert sent[0][field] == expected


@pytest.mark.parametrize("style", ["chat_completions", "responses"])
def test_larger_budget_still_rejects_truncated_report(monkeypatch, style):
    monkeypatch.setattr(ai_report, "_load_ai_config", lambda: {
        "provider": "test", "api_style": style, "api_key": "test-key",
        "base_url": "https://example.invalid/v1", "model": "test-model",
        "timeout": 90, "max_output_tokens": 1200,
    })
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            if style == "responses":
                return {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}, "output_text": "不完整方案"}
            return {"choices": [{"finish_reason": "length", "message": {"content": "不完整方案"}}]}
    monkeypatch.setattr(ai_report.requests, "post", lambda *args, **kwargs: Response())
    result = ai_report.generate_ai_report({}, min_output_tokens=8192)
    assert result["status"] == "truncated"
    assert result["report"] is None
