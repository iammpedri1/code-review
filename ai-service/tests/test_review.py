from email.message import Message
from io import BytesIO
import json
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from app.main import app, analyze_locally, parse_ai_review
import app.main as review_module

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_local_review_reports_line_and_severity() -> None:
    response = client.post(
        "/review",
        json={"code": "print(eval(user_input))", "language": "python"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "local"
    assert {finding["title"] for finding in payload["findings"]} == {
        "Evite eval",
        "Saída de depuração",
    }
    assert all(finding["line"] == 1 for finding in payload["findings"])
    assert all(finding["evidence"] == "print(eval(user_input))" for finding in payload["findings"])


def test_empty_code_is_rejected() -> None:
    response = client.post("/review", json={"code": "", "language": "python"})
    assert response.status_code == 422


def test_code_over_limit_is_rejected() -> None:
    response = client.post(
        "/review",
        json={"code": "x" * 20_001, "language": "python"},
    )
    assert response.status_code == 422


def test_clean_code_has_no_findings() -> None:
    assert analyze_locally("def add(a, b):\n    return a + b") == []


def test_ai_mode_without_key_returns_clear_error(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    response = client.post(
        "/review",
        json={"code": "print('hello')", "language": "python", "useAi": True},
    )
    assert response.status_code == 400
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_ai_parser_preserves_summary_and_rejects_nonexistent_line() -> None:
    review = parse_ai_review(
        '{"summary":"SQL injection confirmada","findings":[{'
        '"title":"SQL Injection","severity":"high","line":2,'
        '"evidence":"query = query + user_id","description":"A entrada controla a consulta.",'
        '"suggestion":"Use parâmetros.","category":"seguranca"}]}',
        "def query_user(user_id):\n    query = query + user_id",
    )
    assert review.summary == "SQL injection confirmada"
    assert review.findings[0].line == 2

    unanchored_review = parse_ai_review(
        '{"summary":"Problema","findings":[{'
        '"title":"Issue","severity":"high","line":9,"evidence":"missing_call()",'
        '"description":"desc","suggestion":"fix","category":"bug"}]}',
        "value = 1",
    )
    assert unanchored_review.findings == []


def test_openrouter_request_uses_model_latency_routing_and_verified_evidence(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.5")
    captured_request = None

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            model_response = {
                "summary": "SQL injection encontrada",
                "corrected_code": "query = 'SELECT * FROM users WHERE id = ?'\n"
                "cursor.execute(query, (user_id,))",
                "findings": [
                    {
                        "title": "SQL Injection",
                        "severity": "critical",
                        "line": 2,
                        "evidence": '"SELECT * FROM users WHERE id = " + str(user_id)',
                        "description": "A entrada e concatenada a query.",
                        "suggestion": "Use parametros.",
                        "category": "security",
                    }
                ],
            }
            return json.dumps(
                {"choices": [{"message": {"content": json.dumps(model_response)}}]}
            ).encode()

    def fake_urlopen(request, timeout):
        nonlocal captured_request
        captured_request = request
        assert timeout == review_module.PROVIDER_TIMEOUT_SECONDS
        return FakeResponse()

    code = 'def query_user(user_id):\n    query = "SELECT * FROM users WHERE id = " + str(user_id)'
    monkeypatch.setattr(review_module, "urlopen", fake_urlopen)
    response = client.post(
        "/review",
        json={
            "code": code,
            "language": "python",
            "useAi": True,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["summary"] == "SQL injection encontrada"
    assert response.json()["findings"][0]["line"] == 2
    assert response.json()["correctedCode"].startswith("query =")
    assert captured_request is not None
    assert captured_request.full_url.endswith("/chat/completions")
    assert captured_request.get_header("Authorization") == "Bearer test-key"
    openrouter_body = json.loads(captured_request.data)
    assert openrouter_body["model"] == "anthropic/claude-sonnet-4.5"
    assert openrouter_body["temperature"] == 0
    assert openrouter_body["provider"] == {
        "sort": "latency",
        "allow_fallbacks": True,
    }
    assert "Responda em português" in openrouter_body["messages"][0]["content"]
    assert "raciocínio interno" in openrouter_body["messages"][0]["content"]
    assert captured_request.get_header("X-title") == "Code Reviewer"


def test_ai_parser_drops_evidence_not_present_in_source() -> None:
    review = parse_ai_review(
        '{"summary":"Problema","findings":[{'
        '"title":"SQL Injection","severity":"high","line":1,'
        '"evidence":"DROP DATABASE","description":"desc",'
        '"suggestion":"fix","category":"security"}]}',
        "query = safe_query()",
    )
    assert review.findings == []


def test_ai_parser_recovers_missing_or_misaligned_evidence() -> None:
    code = "def get_user(user_id):\n    query = build_query(user_id)\n    return db.execute(query)"
    review = parse_ai_review(
        '{"summary":"Query insegura","findings":['
        '{"title":"Input validation","severity":"medium","line":99,'
        '"evidence":"build_query(user_id)","description":"A entrada não é validada.",'
        '"suggestion":"Valide user_id.","category":"security"},'
        '{"title":"Banco de dados","severity":"low","line":3,'
        '"description":"Verifique erros.","suggestion":"Trate erros.",'
        '"category":"reliability"}]}',
        code,
    )

    assert len(review.findings) == 1
    assert review.findings[0].line == 2
    assert review.findings[0].evidence == "build_query(user_id)"


def test_ai_parser_drops_unanchored_finding_instead_of_rejecting_review() -> None:
    review = parse_ai_review(
        '{"summary":"Review completa","findings":['
        '{"title":"Unanchored finding","severity":"high","line":99,'
        '"description":"Não é possível localizar.","suggestion":"Confira manualmente.",'
        '"category":"security"}]}',
        "x = 1",
    )

    assert review.summary == "Review completa"
    assert review.findings == []


def test_review_rejects_unknown_request_fields() -> None:
    response = client.post(
        "/review",
        json={
            "code": "value = 1",
            "language": "python",
            "provider": "unsupported",
        },
    )
    assert response.status_code == 422


def test_provider_retries_temporary_http_errors(monkeypatch) -> None:
    responses = iter(
        [
            HTTPError(
                "https://provider.test",
                503,
                "Unavailable",
                Message(),
                BytesIO(b""),
            ),
            BytesIO(b'{"ok":true}'),
        ]
    )
    calls = 0

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"ok":true}'

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        response = next(responses)
        if isinstance(response, HTTPError):
            raise response
        return FakeResponse()

    monkeypatch.setattr(review_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(review_module.time, "sleep", lambda _: None)

    result = review_module.post_provider_json(
        review_module.Request("https://provider.test"),
        "OpenRouter",
    )

    assert result == {"ok": True}
    assert calls == 2


def test_provider_reports_temporary_unavailability_after_retry_limit(monkeypatch) -> None:
    calls = 0

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        raise HTTPError(
            "https://provider.test",
            503,
            "Unavailable",
            Message(),
            BytesIO(b""),
        )

    monkeypatch.setattr(review_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(review_module.time, "sleep", lambda _: None)
    request = review_module.Request("https://provider.test")

    with pytest.raises(review_module.HTTPException) as error:
        review_module.post_provider_json(request, "OpenRouter")

    assert error.value.status_code == 503
    assert "temporariamente indisponível" in error.value.detail
    assert calls == review_module.PROVIDER_MAX_ATTEMPTS


def test_provider_does_not_retry_rate_limit_errors(monkeypatch) -> None:
    calls = 0

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        raise HTTPError(
            "https://provider.test",
            429,
            "Too Many Requests",
            Message(),
            BytesIO(b""),
        )

    monkeypatch.setattr(review_module, "urlopen", fake_urlopen)

    with pytest.raises(review_module.HTTPException) as error:
        review_module.post_provider_json(
            review_module.Request("https://provider.test"),
            "OpenRouter",
        )

    assert error.value.status_code == 429
    assert "limite de requisições ou de cota" in error.value.detail
    assert calls == 1


def test_ai_parser_rejects_malformed_top_level_response() -> None:
    with pytest.raises((ValueError, json.JSONDecodeError)):
        parse_ai_review("not json", "x = 1")
