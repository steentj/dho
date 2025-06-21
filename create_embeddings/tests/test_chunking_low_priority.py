"""
Tests for lower priority chunking functionality.
This includes additional edge cases and comprehensive testing of all chunking strategies.
"""
import pytest
from create_embeddings.chunking import (
    SentenceSplitterChunkingStrategy,
    WordSplitterChunkingStrategy,
    ChunkingStrategyFactory
)

@pytest.fixture
def sentence_strategy():
    return SentenceSplitterChunkingStrategy()

@pytest.fixture
def word_strategy():
    return WordSplitterChunkingStrategy()

class TestSentenceSplitterEdgeCases:
    """Additional edge cases for SentenceSplitterChunkingStrategy."""
    
    def test_multiple_consecutive_punctuation(self, sentence_strategy):
        """Test handling of text with multiple consecutive punctuation marks."""
        text = "First sentence!! Second sentence?? Third sentence..."
        chunks = list(sentence_strategy.chunk_text(text, max_tokens=5))
        assert len(chunks) == 3
        assert chunks[0] == "First sentence!!"
        assert chunks[1] == "Second sentence??"
        assert chunks[2] == "Third sentence..."
    
    def test_nested_punctuation(self, sentence_strategy):
        """Test handling of nested punctuation (e.g., quotes with periods)."""
        text = 'He said "Stop right there." Then he left. Another sentence.'
        chunks = list(sentence_strategy.chunk_text(text, max_tokens=10))
        assert len(chunks) == 3
        assert chunks[0] == 'He said "Stop right there."'
        assert chunks[1] == "Then he left."
        assert chunks[2] == "Another sentence."
    
    def test_special_characters(self, sentence_strategy):
        """Test handling of special characters and unicode punctuation."""
        text = "First sentence… Second sentence․ Third sentence؟"
        chunks = list(sentence_strategy.chunk_text(text, max_tokens=5))
        assert len(chunks) == 3
        assert "First sentence" in chunks[0]
        assert "Second sentence" in chunks[1]
        assert "Third sentence" in chunks[2]

    def test_title_with_special_characters(self, sentence_strategy):
        """Test title handling with special characters."""
        text = "This is a test sentence."
        title = "Book Title: A — Story!"
        chunks = list(sentence_strategy.chunk_text(text, max_tokens=10, title=title))
        assert len(chunks) == 1
        assert chunks[0] == f"##Book Title: A — Story!##{text}"

class TestWordSplitterStrategy:
    """Tests for WordSplitterChunkingStrategy."""
    
    def test_basic_word_splitting(self, word_strategy):
        """Test basic word splitting functionality."""
        text = "This is a simple test of word splitting"
        chunks = list(word_strategy.chunk_text(text, max_tokens=4))
        assert len(chunks) == 2
        assert chunks[0] == "This is a simple"
        assert chunks[1] == "test of word splitting"
    
    def test_word_splitting_with_title(self, word_strategy):
        """Test word splitting with title prefix."""
        text = "These are some test words"
        title = "Test Title"
        chunks = list(word_strategy.chunk_text(text, max_tokens=3, title=title))
        assert len(chunks) == 2
        assert chunks[0].startswith("##Test Title##")
        assert "These are some" in chunks[0]
        assert chunks[1] == "test words"
    
    def test_empty_and_whitespace(self, word_strategy):
        """Test handling of empty and whitespace-only input."""
        assert list(word_strategy.chunk_text("", max_tokens=5)) == []
        assert list(word_strategy.chunk_text("   ", max_tokens=5)) == []
        
    def test_single_long_word(self, word_strategy):
        """Test handling of single words longer than max_tokens."""
        text = "supercalifragilisticexpialidocious"
        chunks = list(word_strategy.chunk_text(text, max_tokens=10))
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_mixed_whitespace(self, word_strategy):
        """Test handling of various whitespace characters."""
        text = "Word1\tWord2\nWord3    Word4\r\nWord5"
        chunks = list(word_strategy.chunk_text(text, max_tokens=2))
        expected = ["Word1 Word2", "Word3 Word4", "Word5"]
        assert chunks == expected

class TestChunkingFactory:
    """Additional tests for ChunkingStrategyFactory."""
    
    def test_factory_creates_word_splitter(self):
        """Test factory creates WordSplitterChunkingStrategy."""
        strategy = ChunkingStrategyFactory.create_strategy("word_splitter")
        assert isinstance(strategy, WordSplitterChunkingStrategy)
    
    def test_factory_case_insensitive(self):
        """Test factory handles case-insensitive strategy names."""
        strategy1 = ChunkingStrategyFactory.create_strategy("WORD_SPLITTER")
        strategy2 = ChunkingStrategyFactory.create_strategy("word_splitter")
        assert isinstance(strategy1, WordSplitterChunkingStrategy)
        assert isinstance(strategy2, WordSplitterChunkingStrategy)
    
    def test_factory_empty_strategy_name(self):
        """Test factory handles empty strategy name."""
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            ChunkingStrategyFactory.create_strategy("")
    
    def test_factory_none_strategy_name(self):
        """Test factory handles None strategy name."""
        with pytest.raises(ValueError, match="Strategy name cannot be None"):
            ChunkingStrategyFactory.create_strategy(None)

class TestIntegrationScenarios:
    """Integration tests for chunking strategies."""
    
    @pytest.mark.parametrize("strategy_name,strategy_class", [
        ("sentence_splitter", SentenceSplitterChunkingStrategy),
        ("word_splitter", WordSplitterChunkingStrategy)
    ])
    def test_long_text_with_mixed_content(self, strategy_name, strategy_class):
        """Test handling of long text with mixed content using different strategies."""
        # Create a long text with various punctuation, spacing and content
        text = (
            "Short sentence. Very long sentence with multiple words and "
            "some, complex! punctuation... Third sentence.\n\n"
            "New paragraph. \"Quoted text.\" More text."
        )
        strategy = ChunkingStrategyFactory.create_strategy(strategy_name)
        assert isinstance(strategy, strategy_class)
        
        # Test with different token limits
        for max_tokens in [5, 10, 20]:
            chunks = list(strategy.chunk_text(text, max_tokens=max_tokens))
            # Basic validation
            assert chunks  # Should produce at least one chunk
            assert all(len(chunk.split()) <= max_tokens for chunk in chunks)  # Respect max_tokens
            assert "".join(chunks).replace("##", "").count(".") >= 7  # All sentences preserved
