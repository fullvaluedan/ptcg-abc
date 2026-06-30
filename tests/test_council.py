"""U12 council orchestrator tests.

The council is a dev tool, so the whole suite runs fully offline: real network
providers are exercised only on their key-missing and transport-failure paths
(which never leave the machine), and the orchestrator is driven with mock
providers that return canned text. The tests pin the four contract points from
the plan: missing keys skip a provider without failing the run, proposals are
anonymized before cross-critique, the output is one synthesized spec plus
anonymized critiques, and no API key ever reaches a report or a log line.
"""
import json

from council import orchestrator
from council.providers import (
    ANTHROPIC,
    OPENAI,
    Provider,
    ProviderError,
    available_providers,
    default_providers,
)


class MockProvider:
    """Duck-typed stand-in for Provider: no network, scripted replies.

    Records every prompt it was asked, so a test can assert what the critique
    phase actually saw (it must not see author identity).
    """

    def __init__(self, name, reply, is_available=True, fail=False):
        self.name = name
        self._reply = reply
        self._available = is_available
        self._fail = fail
        self.prompts = []

    def available(self):
        return self._available

    def complete(self, prompt):
        self.prompts.append(prompt)
        if self._fail:
            raise ProviderError(f"{self.name}: simulated failure")
        return self._reply


# --- providers.py: env-keyed availability and no-leak error paths ---


def test_available_filters_by_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k-anthropic")
    for var in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "GLM_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    names = {p.name for p in available_providers(default_providers())}
    assert names == {"opus", "sonnet", "haiku"}  # OpenAI-wire ones have no key


def test_blank_key_is_not_available(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    p = Provider("opus", "ANTHROPIC_API_KEY", "claude-opus-4-8", ANTHROPIC)
    assert p.available() is False


def test_complete_raises_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    p = Provider("gpt", "OPENAI_API_KEY", "gpt-4o", OPENAI)
    try:
        p.complete("hello")
        assert False, "expected ProviderError"
    except ProviderError as exc:
        assert "OPENAI_API_KEY" in str(exc)


def test_transport_error_never_leaks_key(monkeypatch):
    # Point at a closed local port so urlopen fails fast, with the key set. The
    # error must carry the provider name and status class only, never the key.
    secret = "sk-this-must-never-appear"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    p = Provider(
        "gpt", "OPENAI_API_KEY", "gpt-4o", OPENAI,
        base_url="http://127.0.0.1:9", timeout=2,
    )
    try:
        p.complete("hello")
        assert False, "expected ProviderError"
    except ProviderError as exc:
        assert secret not in str(exc)
        assert "gpt" in str(exc)


# --- orchestrator: the four plan contract points ---


def test_council_offline_with_mock_providers():
    mocks = [
        MockProvider("alpha", "use determinization prior X"),
        MockProvider("beta", "cache repeated subtrees"),
    ]
    report = orchestrator.run_council("how to sharpen search?", providers=mocks)
    assert report["providers_used"] == ["alpha", "beta"]
    assert len(report["proposals"]) == 2
    assert report["spec"]  # one synthesized spec exists
    assert report["skipped"] == []


def test_missing_key_skips_provider_without_failing():
    mocks = [
        MockProvider("alpha", "live idea", is_available=True),
        MockProvider("ghost", "never runs", is_available=False),
    ]
    report = orchestrator.run_council("q", providers=mocks)
    assert report["providers_used"] == ["alpha"]
    assert len(report["proposals"]) == 1
    assert report["spec"]  # the run still completes


def test_proposals_anonymized_before_critique():
    a = MockProvider("alpha", "idea-one")
    b = MockProvider("beta", "idea-two")
    report = orchestrator.run_council("q", providers=[a, b])
    # Returned proposals carry opaque labels and drop the author name entirely.
    assert [p["label"] for p in report["proposals"]] == ["A", "B"]
    assert all("name" not in p for p in report["proposals"])
    # The critique prompt (each provider's second call) must not name the authors.
    critique_prompt = a.prompts[1]
    assert "Proposal A" in critique_prompt and "Proposal B" in critique_prompt
    assert "alpha" not in critique_prompt and "beta" not in critique_prompt


def test_output_is_one_spec_plus_anonymized_critiques():
    mocks = [MockProvider("alpha", "x"), MockProvider("beta", "y")]
    report = orchestrator.run_council("q", providers=mocks)
    assert isinstance(report["spec"], str) and report["spec"]
    assert len(report["critiques"]) == 2
    assert [c["label"] for c in report["critiques"]] == ["A", "B"]
    assert all(set(c) == {"label", "text"} for c in report["critiques"])


def test_provider_error_midrun_is_recorded_and_run_continues():
    mocks = [
        MockProvider("alpha", "good"),
        MockProvider("boom", "", fail=True),
    ]
    report = orchestrator.run_council("q", providers=mocks)
    # boom failed in both propose and critique phases; both are recorded.
    failed = [s for s in report["skipped"] if s["name"] == "boom"]
    assert len(failed) >= 1
    assert len(report["proposals"]) == 1  # alpha still proposed
    assert report["spec"]  # synthesizer (alpha) still produced a spec


def test_empty_pool_returns_note_not_crash():
    report = orchestrator.run_council("q", providers=[])
    assert report["providers_used"] == []
    assert report["spec"] is None
    assert "note" in report


def test_designated_synthesizer_is_used():
    a = MockProvider("alpha", "a-text")
    b = MockProvider("beta", "b-text")
    synth = MockProvider("judge", "MERGED SPEC")
    report = orchestrator.run_council("q", providers=[a, b], synthesizer=synth)
    assert report["spec"] == "MERGED SPEC"
    assert report["synthesizer"] == "judge"


def test_real_provider_error_keeps_key_out_of_report(monkeypatch):
    # End to end with a real provider whose key is set but whose endpoint is a
    # closed local port. The propose and critique phases both fail; their errors
    # flow through _gather into report["skipped"]. The serialized report must not
    # contain the key, proving the error->report path never carries a secret.
    secret = "sk-end-to-end-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    p = Provider(
        "gpt", "OPENAI_API_KEY", "gpt-4o", OPENAI,
        base_url="http://127.0.0.1:9", timeout=2,
    )
    report = orchestrator.run_council("q", providers=[p])
    assert report["spec"] is None  # no provider proposed
    assert report["skipped"]  # the failure was recorded
    assert secret not in json.dumps(report)


def test_saved_report_holds_no_api_key(tmp_path, monkeypatch):
    secret = "sk-secret-value-xyz"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    mocks = [MockProvider("alpha", "idea"), MockProvider("beta", "idea2")]
    report = orchestrator.run_council("q", providers=mocks)
    out = orchestrator.save_report(report, tmp_path / "report.json")
    text = out.read_text(encoding="utf-8")
    assert secret not in text
    # Round-trips as valid JSON with the expected shape.
    loaded = json.loads(text)
    assert loaded["spec"] and "proposals" in loaded
