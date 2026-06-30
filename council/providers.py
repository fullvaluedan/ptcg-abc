"""LLM providers for the council, keyed only from environment variables.

A Provider names a model, the env var that holds its key, and a wire format
(Anthropic messages or OpenAI chat completions). available() is true only when
the key is present in the environment, so a missing key skips that provider
without failing the run. The key is read at call time and never stored on the
instance, never returned, and never logged.

HTTP goes through urllib so the council adds no third party dependency. This
module is a dev tool and is never bundled into the offline submission.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

ANTHROPIC = "anthropic"
OPENAI = "openai"

_DEFAULT_BASES = {
    ANTHROPIC: "https://api.anthropic.com",
    OPENAI: "https://api.openai.com/v1",
}


class ProviderError(RuntimeError):
    """A provider call failed (network, auth, or a malformed response)."""


@dataclass(frozen=True)
class Provider:
    """One callable LLM endpoint.

    name      a short label used only in dev output (never a secret)
    env_var   the environment variable holding the API key
    model     the model id sent in the request
    wire      ANTHROPIC or OPENAI request/response shape
    base_url  endpoint root; defaults per wire, overridable per provider
    """

    name: str
    env_var: str
    model: str
    wire: str
    base_url: str | None = None
    max_tokens: int = 1024
    timeout: int = 120

    def available(self) -> bool:
        """True when this provider's API key is present in the environment."""
        return bool(os.environ.get(self.env_var, "").strip())

    def _base(self) -> str:
        if self.base_url:
            return self.base_url.rstrip("/")
        if self.wire == ANTHROPIC:
            return os.environ.get("ANTHROPIC_BASE_URL", _DEFAULT_BASES[ANTHROPIC]).rstrip("/")
        return _DEFAULT_BASES[self.wire].rstrip("/")

    def _request(self, prompt: str, key: str) -> urllib.request.Request:
        if self.wire == ANTHROPIC:
            url = f"{self._base()}/v1/messages"
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            body = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
        elif self.wire == OPENAI:
            url = f"{self._base()}/chat/completions"
            headers = {
                "authorization": f"Bearer {key}",
                "content-type": "application/json",
            }
            body = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
        else:
            raise ProviderError(f"unknown wire format {self.wire!r}")
        return urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
        )

    @staticmethod
    def _extract(wire: str, payload: dict) -> str:
        try:
            if wire == ANTHROPIC:
                parts = payload["content"]
                return "".join(p.get("text", "") for p in parts).strip()
            return payload["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"malformed {wire} response") from exc

    def complete(self, prompt: str) -> str:
        """Send one prompt and return the model's text.

        Reads the key from the environment at call time. Raises ProviderError on
        a missing key or any transport/parse failure. The error message never
        contains the key.
        """
        key = os.environ.get(self.env_var, "").strip()
        if not key:
            raise ProviderError(f"{self.name}: env var {self.env_var} is not set")
        req = self._request(prompt, key)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Status only; never echo the request (which carries the key).
            raise ProviderError(f"{self.name}: HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise ProviderError(f"{self.name}: {type(exc).__name__}") from None
        return self._extract(self.wire, payload)


# The default registry. Anthropic models share ANTHROPIC_API_KEY; the
# OpenAI-compatible providers (OpenAI, DeepSeek, GLM) each read their own key.
# Keys absent from the environment simply make a provider unavailable.
def default_providers() -> list[Provider]:
    return [
        Provider("opus", "ANTHROPIC_API_KEY", "claude-opus-4-8", ANTHROPIC),
        Provider("sonnet", "ANTHROPIC_API_KEY", "claude-sonnet-4-6", ANTHROPIC),
        Provider("haiku", "ANTHROPIC_API_KEY", "claude-haiku-4-5-20251001", ANTHROPIC),
        Provider("gpt", "OPENAI_API_KEY", "gpt-4o", OPENAI),
        Provider(
            "deepseek", "DEEPSEEK_API_KEY", "deepseek-chat", OPENAI,
            base_url="https://api.deepseek.com/v1",
        ),
        Provider(
            "glm", "GLM_API_KEY", "glm-4-plus", OPENAI,
            base_url="https://open.bigmodel.cn/api/paas/v4",
        ),
    ]


def available_providers(providers: list[Provider] | None = None) -> list[Provider]:
    """The subset of providers whose API key is present in the environment."""
    pool = providers if providers is not None else default_providers()
    return [p for p in pool if p.available()]
