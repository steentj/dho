#!/usr/bin/env python3
"""
Test to verify that the dependency injection violation has been fixed.
This test creates a new chunking strategy and verifies it works with parse_book
without requiring any modifications to parse_book().
"""

import unittest.mock as mock
from create_embeddings.chunking import ChunkingStrategy
from create_embeddings.opret_bøger import parse_book


class CustomTestChunkingStrategy(ChunkingStrategy):
    """Custom chunking strategy for testing DI compliance."""
    
    def chunk_text(self, text: str, max_tokens: int, title: str = None) -> list[str]:
        """Simple chunking for testing - just split on periods."""
        sentences = [s.strip() + "." for s in text.split(".") if s.strip()]
        return sentences
    
    def supports_cross_page_chunking(self) -> bool:
        """This test strategy supports cross-page chunking."""
        return True


class AnotherTestChunkingStrategy(ChunkingStrategy):
    """Another custom chunking strategy for testing DI compliance."""
    
    def chunk_text(self, text: str, max_tokens: int, title: str = None) -> list[str]:
        """Simple chunking for testing - just split into fixed-size word chunks."""
        words = text.split()
        chunk_size = 5  # Fixed for testing
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
        return chunks
    
    def supports_cross_page_chunking(self) -> bool:
        """This test strategy does NOT support cross-page chunking."""
        return False


async def test_custom_strategies_work_with_parse_book():
    """Test that new chunking strategies work with parse_book without modifying it."""
    
    # Mock PDF object
    mock_pdf = mock.MagicMock()
    mock_pdf.metadata = {"title": "Test Book", "author": "Test Author"}
    mock_pdf.__len__ = mock.MagicMock(return_value=2)  # 2 pages
    
    # Mock pages
    mock_page1 = mock.MagicMock()
    mock_page1.get_text.return_value = "First page text. More content here."
    mock_page2 = mock.MagicMock()
    mock_page2.get_text.return_value = "Second page text. Additional content here."
    
    mock_pdf.__getitem__ = mock.MagicMock(side_effect=[mock_page1, mock_page2])
    
    # Mock embedding provider
    mock_embedding_provider = mock.MagicMock()
    mock_embedding_provider.get_embedding = mock.AsyncMock(return_value=[0.1] * 1536)
    
    # Test with custom strategy that supports cross-page chunking
    custom_strategy = CustomTestChunkingStrategy()
    
    book_result = await parse_book(
        pdf=mock_pdf,
        book_url="test-url",
        chunk_size=10,
        embedding_provider=mock_embedding_provider,
        chunking_strategy=custom_strategy
    )
    
    print(f"✅ Custom strategy (supports cross-page): {len(book_result['chunks'])} chunks")
    assert len(book_result["chunks"]) > 0
    assert len(book_result["embeddings"]) > 0
    
    # Reset mock for second test
    mock_pdf.__getitem__ = mock.MagicMock(side_effect=[mock_page1, mock_page2])
    
    # Test with another custom strategy that does NOT support cross-page chunking
    another_strategy = AnotherTestChunkingStrategy()
    
    book_result2 = await parse_book(
        pdf=mock_pdf,
        book_url="test-url-2",
        chunk_size=10,
        embedding_provider=mock_embedding_provider,
        chunking_strategy=another_strategy
    )
    
    print(f"✅ Another strategy (no cross-page): {len(book_result2['chunks'])} chunks")
    assert len(book_result2["chunks"]) > 0
    assert len(book_result2["embeddings"]) > 0
    
    print("✅ DEPENDENCY INJECTION VIOLATION FIXED!")
    print("✅ New chunking strategies work with parse_book without modifying it!")
    print("✅ Polymorphism is working correctly!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_custom_strategies_work_with_parse_book())
