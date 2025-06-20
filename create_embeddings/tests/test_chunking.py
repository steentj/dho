import pytest
from create_embeddings.chunking import SentenceSplitterChunkingStrategy, ChunkingStrategyFactory

@pytest.fixture
def strategy():
    return SentenceSplitterChunkingStrategy()

def test_chunk_text_simple(strategy):
    text = "This is the first sentence. This is the second sentence."
    chunks = list(strategy.chunk_text(text, max_tokens=5))
    assert len(chunks) == 2
    assert chunks[0] == "This is the first sentence."
    assert chunks[1] == "This is the second sentence."

def test_chunk_text_with_title(strategy):
    text = "This is a sentence."
    title = "My Book"
    chunks = list(strategy.chunk_text(text, max_tokens=10, title=title))
    assert len(chunks) == 1
    assert chunks[0] == "##My Book##This is a sentence."

def test_chunk_long_sentence_hard_split(strategy):
    text = "This single sentence is very long and will definitely exceed the maximum token limit."
    chunks = list(strategy.chunk_text(text, max_tokens=5))
    assert len(chunks) == 3
    assert chunks[0] == "This single sentence is very"
    assert chunks[1] == "long and will definitely exceed"
    assert chunks[2] == "the maximum token limit."

def test_empty_text(strategy):
    text = ""
    chunks = list(strategy.chunk_text(text, max_tokens=10))
    assert len(chunks) == 0

def test_whitespace_handling(strategy):
    text = "  This is sentence one.    This is sentence two, with more words.  "
    chunks = list(strategy.chunk_text(text, max_tokens=7))
    assert len(chunks) == 2
    assert chunks[0] == "This is sentence one."
    assert chunks[1] == "This is sentence two, with more words."

def test_factory_creates_sentence_splitter():
    strategy = ChunkingStrategyFactory.create_strategy("sentence_splitter")
    assert isinstance(strategy, SentenceSplitterChunkingStrategy)

def test_factory_raises_error_for_unknown_strategy():
    with pytest.raises(ValueError, match="Unknown chunking strategy: unknown_strategy"):
        ChunkingStrategyFactory.create_strategy("unknown_strategy")
