"""OpenRouter API client with retry and diagnostics headers."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Sequence

import httpx

from ..config import Settings, load_settings

__all__ = ["OpenRouterClient", "OpenRouterError"]


class OpenRouterError(RuntimeError):
    """Represents failures when calling the OpenRouter API."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        """Store an error message and optional HTTP status code.

        Args:
            message: Human-readable error description.
            status_code: Optional HTTP status associated with the failure.
        """

        super().__init__(message)
        self.status_code = status_code


@dataclass(slots=True)
class OpenRouterClient:
    """Minimal client that performs chat completions against OpenRouter."""

    api_key: str
    model: str
    base_url: str = "https://openrouter.ai/api/v1"
    timeout: float = 30.0
    max_retries: int = 2
    backoff_seconds: float = 0.5
    referer: str | None = None
    user_agent: str | None = None
    _client: httpx.Client | None = None

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        model: str | None = None,
    ) -> "OpenRouterClient":
        """Build a client using repository settings.

        Args:
            settings: Optional pre-loaded :class:`Settings` instance.
            model: Optional override for the model identifier.

        Returns:
            OpenRouterClient: Configured client ready to perform chat completions.

        Raises:
            OpenRouterError: If the OpenRouter API key is missing.
        """

        resolved = settings or load_settings()
        if not resolved.openrouter_api_key:
            raise OpenRouterError("Missing OPENROUTER_API_KEY configuration.")
        chosen_model = model or resolved.llm_model or "openrouter/auto"
        return cls(
            api_key=resolved.openrouter_api_key,
            model=chosen_model,
            timeout=float(resolved.llm_timeout_seconds),
            referer=resolved.llm_referer,
            user_agent=resolved.llm_user_agent,
        )

    def complete(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float | None = None,
        extra_headers: Iterable[tuple[str, str]] | None = None,
    ) -> str:
        """Send chat messages to OpenRouter and return the assistant response.

        Args:
            messages: Ordered list of OpenAI-compatible chat messages.
            temperature: Optional sampling temperature override.
            extra_headers: Additional headers appended to the request.

        Returns:
            str: Assistant response content returned by the provider.

        Raises:
            OpenRouterError: When the request fails after retries or returns an
                invalid payload.
        """

        if not messages:
            raise OpenRouterError("At least one message is required for completion.")

        payload = {
            "model": self.model,
            "messages": list(messages),
            "temperature": temperature if temperature is not None else 0.0,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.referer:
            headers["HTTP-Referer"] = self.referer
        if self.user_agent:
            headers["X-Title"] = self.user_agent
        if extra_headers:
            headers.update(dict(extra_headers))

        last_error: OpenRouterError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._post(payload, headers=headers)
            except httpx.HTTPError as exc:
                last_error = OpenRouterError(f"Network error: {exc}")
            else:
                if response.status_code == 200:
                    return self._parse_response(response)
                if response.status_code in {429} or response.status_code >= 500:
                    last_error = OpenRouterError(
                        "OpenRouter unavailable. Retry later.",
                        status_code=response.status_code,
                    )
                else:
                    raise OpenRouterError(
                        f"OpenRouter request failed with {response.status_code}.",
                        status_code=response.status_code,
                    )
            if attempt < self.max_retries:
                time.sleep(self.backoff_seconds * (2**attempt))
        if last_error is not None:
            raise last_error
        raise OpenRouterError("OpenRouter request failed without response.")

    def _post(self, payload: dict[str, object], *, headers: dict[str, str]) -> httpx.Response:
        """Execute the HTTP request using the configured client."""

        if self._client is not None:
            return self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            return client.post("/chat/completions", json=payload, headers=headers)

    @staticmethod
    def _parse_response(response: httpx.Response) -> str:
        """Extract the assistant message from the API response."""

        try:
            data = response.json()
            choices = data["choices"]
            first = choices[0]
            message = first["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise OpenRouterError("Invalid OpenRouter response payload.") from exc
        return str(content)
