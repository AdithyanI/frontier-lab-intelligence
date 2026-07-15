from fli import llm_responses


def test_gpt56_litellm_routes_use_verified_azure_cache_retention():
    assert llm_responses.litellm_prompt_cache_kwargs("gpt-5.6-luna") == {
        "prompt_cache_retention": "24h"
    }
    assert llm_responses.litellm_prompt_cache_kwargs("gpt-5.6-terra") == {
        "prompt_cache_retention": "24h"
    }
    assert llm_responses.litellm_prompt_cache_kwargs("gpt-5.4-mini") == {}


def test_long_prompt_cache_keys_are_stable_and_azure_compatible():
    kwargs = {
        "namespace": "audience-insights-v2-investment-extraction",
        "prompt_version": "investment-insight-v2.0",
        "scope_key": "candidate-123",
    }

    first = llm_responses.sharded_prompt_cache_key(**kwargs)
    second = llm_responses.sharded_prompt_cache_key(**kwargs)
    changed_version = llm_responses.sharded_prompt_cache_key(
        **{**kwargs, "prompt_version": "investment-insight-v2.1"}
    )

    assert first == second
    assert first != changed_version
    assert len(first) <= llm_responses.AZURE_PROMPT_CACHE_KEY_MAX_LENGTH


def test_short_prompt_cache_keys_remain_readable():
    key = llm_responses.sharded_prompt_cache_key(
        namespace="audience-routing",
        prompt_version="v3",
        scope_key="event-1",
    )

    assert key.startswith("fli:audience-routing:v3:shard-")
    assert len(key) <= llm_responses.AZURE_PROMPT_CACHE_KEY_MAX_LENGTH
