"""
Unit test to verify supports_cross_page_chunking() interface compliance.
This test ensures both existing strategies correctly implement the new interface method.
"""

import pytest
from create_embeddings.chunking import (
    ChunkingStrategy,
    SentenceSplitterChunkingStrategy, 
    WordOverlapChunkingStrategy,
    ChunkingStrategyFactory
)


@pytest.mark.unit
class TestChunkingStrategyInterface:
    """Test the ChunkingStrategy interface compliance."""

    def test_sentence_splitter_interface_compliance(self):
        """Test that SentenceSplitterChunkingStrategy implements the interface correctly."""
        strategy = SentenceSplitterChunkingStrategy()
        
        # Test that it implements ChunkingStrategy
        assert isinstance(strategy, ChunkingStrategy)
        
        # Test that supports_cross_page_chunking method exists and returns False
        assert hasattr(strategy, 'supports_cross_page_chunking')
        assert callable(strategy.supports_cross_page_chunking)
        assert not strategy.supports_cross_page_chunking()
        
        # Test that chunk_text method still works
        chunks = list(strategy.chunk_text("Test sentence. Another sentence.", 10))
        assert len(chunks) > 0

    def test_word_overlap_interface_compliance(self):
        """Test that WordOverlapChunkingStrategy implements the interface correctly."""
        strategy = WordOverlapChunkingStrategy()
        
        # Test that it implements ChunkingStrategy
        assert isinstance(strategy, ChunkingStrategy)
        
        # Test that supports_cross_page_chunking method exists and returns True
        assert hasattr(strategy, 'supports_cross_page_chunking')
        assert callable(strategy.supports_cross_page_chunking)
        assert strategy.supports_cross_page_chunking()
        
        # Test that chunk_text method still works
        chunks = list(strategy.chunk_text("Test sentence. Another sentence.", 10))
        assert len(chunks) > 0

    def test_factory_created_strategies_interface_compliance(self):
        """Test that factory-created strategies implement the interface correctly."""
        
        # Test sentence splitter from factory
        sentence_strategy = ChunkingStrategyFactory.create_strategy("sentence_splitter")
        assert isinstance(sentence_strategy, ChunkingStrategy)
        assert hasattr(sentence_strategy, 'supports_cross_page_chunking')
        assert not sentence_strategy.supports_cross_page_chunking()
        
        # Test word overlap from factory
        word_overlap_strategy = ChunkingStrategyFactory.create_strategy("word_overlap")
        assert isinstance(word_overlap_strategy, ChunkingStrategy)
        assert hasattr(word_overlap_strategy, 'supports_cross_page_chunking')
        assert word_overlap_strategy.supports_cross_page_chunking()

    def test_polymorphic_behavior(self):
        """Test that strategies can be used polymorphically."""
        strategies = [
            ChunkingStrategyFactory.create_strategy("sentence_splitter"),
            ChunkingStrategyFactory.create_strategy("word_overlap")
        ]
        
        test_text = "First sentence. Second sentence. Third sentence."
        
        for strategy in strategies:
            # All strategies should implement the interface
            assert hasattr(strategy, 'supports_cross_page_chunking')
            assert hasattr(strategy, 'chunk_text')
            
            # Should be able to call methods polymorphically
            cross_page_support = strategy.supports_cross_page_chunking()
            assert isinstance(cross_page_support, bool)
            
            chunks = list(strategy.chunk_text(test_text, 10))
            assert len(chunks) > 0
            assert all(isinstance(chunk, str) for chunk in chunks)

    def test_interface_contract_consistency(self):
        """Test that the interface contract is consistent across strategies."""
        sentence_strategy = SentenceSplitterChunkingStrategy()
        word_overlap_strategy = WordOverlapChunkingStrategy()
        
        # Both should return boolean values
        sentence_result = sentence_strategy.supports_cross_page_chunking()
        word_overlap_result = word_overlap_strategy.supports_cross_page_chunking()
        
        assert isinstance(sentence_result, bool)
        assert isinstance(word_overlap_result, bool)
        
        # They should return different values (demonstrating the interface works)
        assert sentence_result != word_overlap_result
        assert sentence_result is False
        assert word_overlap_result is True
