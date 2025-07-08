"""
Factory for creating embedding providers.
"""

import os
from typing import Dict, Type
from .embedding_providers import EmbeddingProvider, OpenAIEmbeddingProvider, DummyEmbeddingProvider, OllamaEmbeddingProvider


class EmbeddingProviderRegistry:
    """Registry for embedding provider implementations."""
    
    _providers: Dict[str, Type[EmbeddingProvider]] = {
        "openai": OpenAIEmbeddingProvider,
        "ollama": OllamaEmbeddingProvider,
        "dummy": DummyEmbeddingProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[EmbeddingProvider]) -> None:
        """Register a new embedding provider."""
        cls._providers[name] = provider_class
    
    @classmethod
    def create_provider(cls, provider_name: str = None, api_key: str = None, model: str = None, **kwargs) -> EmbeddingProvider:
        """
        Create an embedding provider instance.
        
        Args:
            provider_name: Name of the provider ('openai', 'ollama', or 'dummy'). 
                          If None, uses PROVIDER environment variable or defaults to 'dummy'
            api_key: API key for the provider (required for openai, ignored for ollama/dummy)
            model: Model to use (optional, uses default if not specified)
            **kwargs: Additional arguments passed to provider constructor
            
        Returns:
            EmbeddingProvider instance
            
        Raises:
            ValueError: If provider_name is unknown
        """
        if provider_name is None:
            provider_name = os.getenv("PROVIDER", "dummy")
        
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown embedding provider: {provider_name}")
        
        provider_class = cls._providers[provider_name]
        
        # Handle provider-specific initialization
        if provider_name == "openai":
            return provider_class(api_key, model, **kwargs)
        elif provider_name == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
            model = model or os.getenv("OLLAMA_MODEL", "nomic-embed-text")
            return provider_class(base_url, model, **kwargs)
        elif provider_name == "dummy":
            return provider_class(**kwargs)
        else:
            # For any future providers, try to call with all available parameters
            # This provides flexibility for new provider implementations
            try:
                return provider_class(api_key=api_key, model=model, **kwargs)
            except TypeError:
                # Fallback to no-argument constructor
                return provider_class(**kwargs)
    
    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of available embedding providers."""
        return list(cls._providers.keys())


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
            
        Note:
            This method is maintained for backward compatibility.
            New code should use EmbeddingProviderRegistry.create_provider() instead.
        """
        return EmbeddingProviderRegistry.create_provider(provider_name, api_key, model)
