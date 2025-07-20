"""
Tests for the new ChunkingStrategyRegistry functionality.

This module tests the registry pattern implementation for chunking strategies,
including registration, discovery, environment-based defaults, and consistent error handling.
"""

import pytest
from unittest.mock import patch
from create_embeddings.chunking import (
    ChunkingStrategyRegistry,
    ChunkingStrategy,
    SentenceSplitterChunkingStrategy,
    WordOverlapChunkingStrategy,
    ChunkingStrategyFactory
)
from typing import Iterable


class MockChunkingStrategy(ChunkingStrategy):
    """Mock chunking strategy for testing registry functionality."""
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    
    def chunk_text(self, text: str, max_tokens: int, title: str = None) -> Iterable[str]:
        """Simple mock implementation that just returns the text."""
        yield text
    
    def supports_cross_page_chunking(self) -> bool:
        return True
    
    def process_document(self, pages_text: dict[int, str], chunk_size: int, title: str) -> Iterable[tuple[int, str]]:
        """Mock implementation of process_document."""
        for page_num, page_text in pages_text.items():
            for chunk_text in self.chunk_text(page_text, chunk_size, title):
                yield (page_num, chunk_text)


@pytest.mark.unit
class TestChunkingStrategyRegistry:
    """Test the ChunkingStrategyRegistry class."""
    
    def test_registry_has_all_strategies(self):
        """Test that registry contains all expected strategies."""
        available = ChunkingStrategyRegistry.get_available_strategies()
        expected = ["sentence_splitter", "word_overlap"]
        
        for strategy in expected:
            assert strategy in available
    
    def test_create_sentence_splitter_strategy(self):
        """Test creation of sentence splitter strategy through registry."""
        strategy = ChunkingStrategyRegistry.create_strategy("sentence_splitter")
        assert isinstance(strategy, SentenceSplitterChunkingStrategy)
    
    def test_create_word_overlap_strategy(self):
        """Test creation of word overlap strategy through registry."""
        strategy = ChunkingStrategyRegistry.create_strategy("word_overlap")
        assert isinstance(strategy, WordOverlapChunkingStrategy)
    
    def test_create_strategy_case_insensitive(self):
        """Test that strategy creation is case insensitive."""
        strategy1 = ChunkingStrategyRegistry.create_strategy("sentence_splitter")
        strategy2 = ChunkingStrategyRegistry.create_strategy("SENTENCE_SPLITTER")
        
        assert isinstance(strategy1, SentenceSplitterChunkingStrategy)
        assert isinstance(strategy2, SentenceSplitterChunkingStrategy)
    
    def test_create_strategy_with_kwargs(self):
        """Test that kwargs are passed to strategy constructors."""
        # Register a mock strategy temporarily
        original_strategies = ChunkingStrategyRegistry._strategies.copy()
        try:
            ChunkingStrategyRegistry.register_strategy("mock", MockChunkingStrategy)
            
            strategy = ChunkingStrategyRegistry.create_strategy("mock", test_param="test_value")
            assert isinstance(strategy, MockChunkingStrategy)
            assert strategy.kwargs == {"test_param": "test_value"}
        finally:
            # Restore original strategies
            ChunkingStrategyRegistry._strategies = original_strategies
    
    @patch.dict('os.environ', {'CHUNKING_STRATEGY': 'word_overlap'})
    def test_environment_default_strategy(self):
        """Test that environment variable sets default strategy."""
        strategy = ChunkingStrategyRegistry.create_strategy()
        assert isinstance(strategy, WordOverlapChunkingStrategy)
    
    @patch.dict('os.environ', {}, clear=True)
    def test_default_strategy_when_no_env(self):
        """Test default strategy when no environment variable is set."""
        strategy = ChunkingStrategyRegistry.create_strategy()
        assert isinstance(strategy, SentenceSplitterChunkingStrategy)  # Should default to sentence_splitter
    
    def test_unknown_strategy_error(self):
        """Test consistent error message for unknown strategy."""
        with pytest.raises(ValueError, match="Unknown chunking strategy: unknown_strategy"):
            ChunkingStrategyRegistry.create_strategy("unknown_strategy")
    
    def test_empty_strategy_error(self):
        """Test error handling for empty strategy name."""
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            ChunkingStrategyRegistry.create_strategy("")
        
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            ChunkingStrategyRegistry.create_strategy("   ")  # Whitespace only
    
    def test_register_strategy(self):
        """Test registering a new strategy."""
        # Store original state
        original_strategies = ChunkingStrategyRegistry._strategies.copy()
        original_count = len(ChunkingStrategyRegistry.get_available_strategies())
        
        try:
            # Register new strategy
            ChunkingStrategyRegistry.register_strategy("test", MockChunkingStrategy)
            
            # Verify registration
            available = ChunkingStrategyRegistry.get_available_strategies()
            assert len(available) == original_count + 1
            assert "test" in available
            
            # Test creation
            strategy = ChunkingStrategyRegistry.create_strategy("test")
            assert isinstance(strategy, MockChunkingStrategy)
            
        finally:
            # Restore original state
            ChunkingStrategyRegistry._strategies = original_strategies
    
    def test_get_available_strategies_returns_list(self):
        """Test that get_available_strategies returns a list."""
        available = ChunkingStrategyRegistry.get_available_strategies()
        assert isinstance(available, list)
        assert len(available) > 0


@pytest.mark.unit
class TestChunkingRegistryBackwardCompatibility:
    """Test backward compatibility with existing ChunkingStrategyFactory."""
    
    def test_factory_delegates_to_registry(self):
        """Test that old factory methods delegate to new registry."""
        # Both should create the same type
        factory_strategy = ChunkingStrategyFactory.create_strategy("sentence_splitter")
        registry_strategy = ChunkingStrategyRegistry.create_strategy("sentence_splitter")
        
        assert isinstance(factory_strategy, type(registry_strategy))
        assert isinstance(factory_strategy, SentenceSplitterChunkingStrategy)
    
    @patch.dict('os.environ', {}, clear=True)
    def test_factory_error_consistency(self):
        """Test that factory and registry produce consistent errors."""
        # Both should raise the same error for unknown strategies
        with pytest.raises(ValueError, match="Unknown chunking strategy: unknown"):
            ChunkingStrategyFactory.create_strategy("unknown")
        
        with pytest.raises(ValueError, match="Unknown chunking strategy: unknown"):
            ChunkingStrategyRegistry.create_strategy("unknown")
        
        # Both should handle None appropriately
        with pytest.raises(ValueError, match="Strategy name cannot be None"):
            ChunkingStrategyFactory.create_strategy(None)
        
        # Registry handles None differently (uses environment default)
        strategy = ChunkingStrategyRegistry.create_strategy(None)
        assert isinstance(strategy, SentenceSplitterChunkingStrategy)
    
    def test_factory_preserves_validation(self):
        """Test that old factory preserves original validation logic."""
        # Test None validation
        with pytest.raises(ValueError, match="Strategy name cannot be None"):
            ChunkingStrategyFactory.create_strategy(None)
        
        # Test empty string validation  
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            ChunkingStrategyFactory.create_strategy("")


@pytest.mark.unit
class TestChunkingRegistryIntegration:
    """Integration tests for chunking strategy registry functionality."""
    
    def test_registry_state_isolation(self):
        """Test that registry modifications don't affect other tests."""
        # Get original state
        original_count = len(ChunkingStrategyRegistry._strategies)
        
        # Register a temporary strategy
        ChunkingStrategyRegistry.register_strategy("temp", MockChunkingStrategy)
        assert len(ChunkingStrategyRegistry._strategies) == original_count + 1
        
        # Remove temporary strategy
        del ChunkingStrategyRegistry._strategies["temp"]
        assert len(ChunkingStrategyRegistry._strategies) == original_count
    
    @patch.dict('os.environ', {'CHUNKING_STRATEGY': 'word_overlap'})
    def test_full_environment_integration(self):
        """Test full integration with environment variables."""
        strategy = ChunkingStrategyRegistry.create_strategy()
        
        assert isinstance(strategy, WordOverlapChunkingStrategy)
        assert strategy.supports_cross_page_chunking()
    
    def test_strategy_interface_compliance(self):
        """Test that all registered strategies implement the correct interface."""
        for strategy_name in ChunkingStrategyRegistry.get_available_strategies():
            strategy = ChunkingStrategyRegistry.create_strategy(strategy_name)
            assert isinstance(strategy, ChunkingStrategy)
            
            # Test that all required methods exist
            assert hasattr(strategy, 'chunk_text')
            assert hasattr(strategy, 'supports_cross_page_chunking')
            
            # Test that methods return expected types
            assert isinstance(strategy.supports_cross_page_chunking(), bool)
            
            # Test chunking functionality
            chunks = list(strategy.chunk_text("Test text.", 10))
            assert isinstance(chunks, list)
            assert len(chunks) > 0
