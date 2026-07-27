import json
from types import SimpleNamespace

from fli import cli
from fli.diagnostics import prompt_cache


class _RawResponse:
    def __init__(self, response):
        self._response = response
        self.headers = {"x-litellm-response-cost": "0.001"}

    def parse(self):
        return self._response


class _RawAPI:
    def __init__(self, *, misses: set[str] | None = None):
        self.calls = []
        self._model_calls = {}
        self._misses = misses or set()

    def create(self, **kwargs):
        self.calls.append(kwargs)
        model = kwargs["model"]
        model_attempt = self._model_calls.get(model, 0) + 1
        self._model_calls[model] = model_attempt
        cached_tokens = (
            0 if model_attempt == 1 or model in self._misses else 1_792
        )
        response = SimpleNamespace(
            id=f"{model}-{model_attempt}",
            model=model,
            status="incomplete",
            usage=SimpleNamespace(
                input_tokens=1_977,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=cached_tokens,
                    cache_write_tokens=0,
                ),
                output_tokens=64,
            ),
        )
        response.model_dump = lambda **_: {
            "id": response.id,
            "model": response.model,
            "status": response.status,
        }
        return _RawResponse(response)


class _Client:
    def __init__(self, *, misses: set[str] | None = None):
        self.raw_api = _RawAPI(misses=misses)
        self.responses = SimpleNamespace(with_raw_response=self.raw_api)
        self.options = None

    def with_options(self, **options):
        self.options = options
        return self


def test_json_canary_observes_warm_cache_reads_for_luna_and_terra(capsys):
    client = _Client()

    exit_code = prompt_cache.main(
        ["--attempts", "3", "--no-input"],
        client_factory=lambda: client,
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert payload["schema_version"] == "1.0"
    assert payload["command"] == "prompt-cache-canary"
    assert payload["status"] == "ok"
    assert payload["error"] is None
    assert payload["meta"]["request_id"]
    assert payload["data"]["cache_observed_for_all_models"] is True
    assert [
        (item["model"], item["warm_hit_requests"], item["warm_requests"])
        for item in payload["data"]["models"]
    ] == [
        ("gpt-5.6-luna", 2, 2),
        ("gpt-5.6-terra", 2, 2),
    ]
    assert client.options == {"timeout": 180.0, "max_retries": 0}

    assert len(client.raw_api.calls) == 6
    by_model = {}
    for request in client.raw_api.calls:
        by_model.setdefault(request["model"], []).append(request)
        assert request["prompt_cache_retention"] == "24h"
        assert "prompt_cache_options" not in request
        assert request["max_output_tokens"] == 64
        assert request["store"] is False
    for calls in by_model.values():
        assert len({call["prompt_cache_key"] for call in calls}) == 1
        assert len({call["input"] for call in calls}) == 3


def test_canary_returns_retryable_error_when_a_model_has_no_warm_hit(capsys):
    client = _Client(misses={"gpt-5.6-luna"})

    exit_code = prompt_cache.main(
        ["--attempts", "2", "--no-input"],
        client_factory=lambda: client,
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "error"
    assert payload["error"] == {
        "code": "E_CACHE_NOT_OBSERVED",
        "message": "At least one model had no warm prompt-cache read.",
        "retryable": True,
        "hint": "Prompt caching is best-effort; retry before escalating.",
    }
    results = {item["model"]: item for item in payload["data"]["models"]}
    assert results["gpt-5.6-luna"]["cache_observed"] is False
    assert results["gpt-5.6-terra"]["cache_observed"] is True


def test_invalid_usage_is_structured_json(capsys):
    exit_code = prompt_cache.main(
        ["--attempts", "1", "--no-input"],
        client_factory=lambda: _Client(),
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["status"] == "error"
    assert payload["data"] is None
    assert payload["error"]["code"] == "E_USAGE"


def test_root_cli_forwards_canary_arguments(monkeypatch):
    seen = {}

    def fake_main(argv):
        seen["argv"] = argv
        return 7

    monkeypatch.setattr(prompt_cache, "main", fake_main)

    assert cli.main(["prompt-cache-canary", "--attempts", "2"]) == 7
    assert seen["argv"] == ["--attempts", "2"]
