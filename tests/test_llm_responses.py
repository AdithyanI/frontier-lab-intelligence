from fli import llm_responses


def test_gpt56_litellm_routes_use_verified_azure_cache_retention():
    assert llm_responses.litellm_prompt_cache_kwargs("gpt-5.6-luna") == {
        "prompt_cache_retention": "24h"
    }
    assert llm_responses.litellm_prompt_cache_kwargs("gpt-5.6-terra") == {
        "prompt_cache_retention": "24h"
    }
    assert llm_responses.litellm_prompt_cache_kwargs("gpt-5.4-mini") == {}
