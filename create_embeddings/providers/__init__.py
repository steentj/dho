"""
Embedding providers package.
Provides interfaces and implementations for different embedding services.
"""

from .embedding_providers import EmbeddingProvider, OpenAIEmbeddingProvider, DummyEmbeddingProvider
from .factory import EmbeddingProviderFactory

__all__ = [
    'EmbeddingProvider',
    'OpenAIEmbeddingProvider', 
    'DummyEmbeddingProvider',
    'EmbeddingProviderFactory'
]
