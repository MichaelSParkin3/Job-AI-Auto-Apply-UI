from __future__ import annotations

from collections.abc import Iterable

import httpx
import pytest

from job_ai_auto_apply_ui.llm.openrouter_client import OpenRouterClient, OpenRouterError


class _SequenceResponder:
    def __init__(self, responses: Iterable[httpx.Response]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        try:
            return self._responses[self.calls - 1]
        except IndexError:  # pragma: no cover - defensive
            raise AssertionError("Unexpected extra request")


def _client(responder: _SequenceResponder) -> httpx.Client:
    transport = httpx.MockTransport(responder)
    return httpx.Client(transport=transport)


def test_complete_returns_message(monkeypatch: pytest.MonkeyPatch) -> None:
    responder = _SequenceResponder(
        [
            httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "Hello"}},
                    ]
                },
            )
        ]
    )
    client = OpenRouterClient(
        api_key="test",
        model="model",
        _client=_client(responder),
        max_retries=0,
    )

    result = client.complete([{"role": "user", "content": "Hi"}])

    assert result == "Hello"
    assert responder.calls == 1


def test_complete_retries_on_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    responder = _SequenceResponder(
        [
            httpx.Response(429, json={"error": "slow down"}),
            httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Recovered"}}]},
            ),
        ]
    )
    client = OpenRouterClient(
        api_key="test",
        model="model",
        _client=_client(responder),
        max_retries=2,
        backoff_seconds=0,
    )

    result = client.complete([{"role": "user", "content": "Ping"}])

    assert result == "Recovered"
    assert responder.calls == 2


def test_complete_raises_on_invalid_payload() -> None:
    responder = _SequenceResponder([httpx.Response(200, json={"choices": []})])
    client = OpenRouterClient(
        api_key="test",
        model="model",
        _client=_client(responder),
        max_retries=0,
    )

    with pytest.raises(OpenRouterError):
        client.complete([{"role": "user", "content": "Test"}])


def test_from_settings_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(OpenRouterError):
        OpenRouterClient.from_settings()
