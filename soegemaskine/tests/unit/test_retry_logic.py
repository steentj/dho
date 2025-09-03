from unittest.mock import AsyncMock

import pytest

from create_embeddings.providers.embedding_providers import OpenAIEmbeddingProvider, OllamaEmbeddingProvider


@pytest.mark.asyncio
async def test_openai_retry_logic(monkeypatch):
    provider = OpenAIEmbeddingProvider(api_key="dummy", model="text-embedding-3-small")
    provider.max_retries = 2
    provider.retry_backoff = 0.01
    provider.timeout = 1

    # Mock internal call to fail twice then succeed
    calls = {"count": 0}

    async def failing_call(chunk: str):
        if calls["count"] < 2:
            calls["count"] += 1
            raise RuntimeError("transient")
        return [0.1, 0.2]

    monkeypatch.setattr(provider, "_call_openai", failing_call)

    embedding = await provider.get_embedding("hello")
    assert embedding == [0.1, 0.2]
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_ollama_retry_logic(monkeypatch):
    provider = OllamaEmbeddingProvider(base_url="http://ollama:11434", model="nomic-embed-text")
    provider.max_retries = 1
    provider.retry_backoff = 0.01
    provider.timeout = 1
    provider.client = AsyncMock()  # Avoid real HTTP call

    calls = {"count": 0}

    async def failing_http_post(url, json):  # mimic httpx.AsyncClient.post
        if calls["count"] == 0:
            calls["count"] += 1
            raise RuntimeError("boom")
        return type("Resp", (), {"raise_for_status": lambda self: None, "json": lambda self: {"embedding": [1.0, 2.0]}})()

    provider.client.post = failing_http_post  # type: ignore

    embedding = await provider.get_embedding("hello")
    assert embedding == [1.0, 2.0]
    assert calls["count"] == 1
