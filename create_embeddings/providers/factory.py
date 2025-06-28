"""
Factory for creating embedding providers.
"""

import os
from .embedding_providers import EmbeddingProvider, OpenAIEmbeddingProvider, DummyEmbeddingProvider, OllamaEmbeddingProvider


class EmbeddingProviderFactory:
    """Factory for creating embedding provider instances."""
    
    @staticmethod
    def create_provider(provider_name: str, api_key: str = None, model: str = None) -> EmbeddingProvider:
        """
        Create an embedding provider instance.
        
        Args:
            provider_name: Name of the provider ('openai', 'ollama', or 'dummy')
            api_key: API key for the provider (required for openai, ignored for ollama/dummy)
            model: Model to use (optional, uses default if not specified)
            
        Returns:
            EmbeddingProvider instance
            
        Raises:
            ValueError: If provider_name is unknown
        """
        if provider_name == "openai":
            return OpenAIEmbeddingProvider(api_key, model)
        elif provider_name == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
            model = model or os.getenv("OLLAMA_MODEL", "nomic-embed-text")
            return OllamaEmbeddingProvider(base_url, model)
        elif provider_name == "dummy":
            return DummyEmbeddingProvider()
        else:
            raise ValueError(f"Ukendt udbyder: {provider_name}")
