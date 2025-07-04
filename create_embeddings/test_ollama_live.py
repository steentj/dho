#!/usr/bin/env python3
"""
Quick test to verify Ollama embedding provider works with real service.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from create_embeddings.providers.embedding_providers import OllamaEmbeddingProvider


async def test_ollama_live():
    """Test the Ollama embedding provider against the actual running service."""
    
    print("Testing Ollama embedding provider...")
    
    # Create provider
    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="nomic-embed-text"
    )
    
    try:
        # Test with a simple text chunk
        test_text = "This is a test text for embedding generation."
        print(f"Getting embedding for: '{test_text}'")
        
        embedding = await provider.get_embedding(test_text)
        
        print(f"✅ Success! Got embedding with {len(embedding)} dimensions")
        print(f"First 5 values: {embedding[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        # Close the HTTP client if it exists
        if hasattr(provider, 'client') and hasattr(provider.client, 'aclose'):
            await provider.client.aclose()


if __name__ == "__main__":
    success = asyncio.run(test_ollama_live())
    if success:
        print("\n🎉 Ollama embedding provider is working correctly!")
        sys.exit(0)
    else:
        print("\n💥 Ollama embedding provider failed!")
        sys.exit(1)
