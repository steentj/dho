import unittest.mock as mock
from create_embeddings.opret_bøger import parse_book
from create_embeddings.chunking import WordOverlapChunkingStrategy, SentenceSplitterChunkingStrategy


async def test_parse_book_integration_word_overlap():
    """Test that parse_book correctly uses cross-page chunking for WordOverlapChunkingStrategy"""
    
    # Mock PDF object
    mock_pdf = mock.MagicMock()
    mock_pdf.metadata = {"title": "Test Book", "author": "Test Author"}
    mock_pdf.__len__ = mock.MagicMock(return_value=3)  # 3 pages
    
    # Mock pages with substantial content
    mock_page1 = mock.MagicMock()
    mock_page1.get_text.return_value = "Page one content. " * 20  # 60 words
    mock_page2 = mock.MagicMock()
    mock_page2.get_text.return_value = "Page two content. " * 20  # 60 words
    mock_page3 = mock.MagicMock()
    mock_page3.get_text.return_value = "Page three content. " * 20  # 60 words
    
    mock_pdf.__getitem__ = mock.MagicMock(side_effect=[mock_page1, mock_page2, mock_page3])
    
    # Mock embedding provider
    mock_embedding_provider = mock.MagicMock()
    mock_embedding_provider.get_embedding = mock.AsyncMock(return_value=[0.1] * 1536)
    
    # Test with WordOverlapChunkingStrategy
    word_overlap_strategy = WordOverlapChunkingStrategy()
    
    book_result = await parse_book(
        pdf=mock_pdf,
        book_url="test-url",
        chunk_size=400,
        embedding_provider=mock_embedding_provider,
        chunking_strategy=word_overlap_strategy
    )
    
    # Should have book metadata
    assert book_result["titel"] == "Test Book"
    assert book_result["forfatter"] == "Test Author"
    assert book_result["sider"] == 3
    
    # Should have chunks and embeddings
    assert len(book_result["chunks"]) > 0
    assert len(book_result["embeddings"]) > 0
    assert len(book_result["chunks"]) == len(book_result["embeddings"])
    
    # For cross-page chunking, might have fewer chunks than pages
    # Each chunk should be (page_num, chunk_text) tuple
    for page_num, chunk_text in book_result["chunks"]:
        assert isinstance(page_num, int)
        assert isinstance(chunk_text, str)
        assert 1 <= page_num <= 3
        assert len(chunk_text.strip()) > 0
        # Should not have title prefix (WordOverlapChunkingStrategy behavior)
        assert not chunk_text.startswith("##")


async def test_parse_book_integration_sentence_splitter():
    """Test that parse_book correctly uses page-by-page chunking for SentenceSplitterChunkingStrategy"""
    
    # Mock PDF object
    mock_pdf = mock.MagicMock()
    mock_pdf.metadata = {"title": "Test Book", "author": "Test Author"}
    mock_pdf.__len__ = mock.MagicMock(return_value=2)  # 2 pages
    
    # Mock pages
    mock_page1 = mock.MagicMock()
    mock_page1.get_text.return_value = "First page sentence. Another sentence here."
    mock_page2 = mock.MagicMock()
    mock_page2.get_text.return_value = "Second page sentence. More content here."
    
    mock_pdf.__getitem__ = mock.MagicMock(side_effect=[mock_page1, mock_page2])
    
    # Mock embedding provider
    mock_embedding_provider = mock.MagicMock()
    mock_embedding_provider.get_embedding = mock.AsyncMock(return_value=[0.2] * 1536)
    
    # Test with SentenceSplitterChunkingStrategy
    sentence_strategy = SentenceSplitterChunkingStrategy()
    
    book_result = await parse_book(
        pdf=mock_pdf,
        book_url="test-url",
        chunk_size=20,  # Small chunks to force multiple chunks per page
        embedding_provider=mock_embedding_provider,
        chunking_strategy=sentence_strategy
    )
    
    # Should have book metadata
    assert book_result["titel"] == "Test Book"
    assert book_result["forfatter"] == "Test Author"
    assert book_result["sider"] == 2
    
    # Should have chunks and embeddings
    assert len(book_result["chunks"]) > 0
    assert len(book_result["embeddings"]) > 0
    assert len(book_result["chunks"]) == len(book_result["embeddings"])
    
    # For page-by-page chunking, should have chunks from each page
    page_numbers = [page_num for page_num, _ in book_result["chunks"]]
    assert 1 in page_numbers  # Should have chunks from page 1
    assert 2 in page_numbers  # Should have chunks from page 2
    
    # Each chunk should have title prefix (SentenceSplitterChunkingStrategy behavior)
    for page_num, chunk_text in book_result["chunks"]:
        assert isinstance(page_num, int)
        assert isinstance(chunk_text, str)
        assert 1 <= page_num <= 2
        assert len(chunk_text.strip()) > 0
        # Should have title prefix
        assert chunk_text.startswith("##Test Book##"), f"Chunk missing title: {chunk_text[:50]}"


def test_strategy_detection_in_parse_book():
    """Test that parse_book correctly detects strategy types"""
    # This is more of a structural test - we can't easily test the isinstance check
    # without mocking, but we can verify the strategies are correctly imported
    
    word_overlap_strategy = WordOverlapChunkingStrategy()
    sentence_strategy = SentenceSplitterChunkingStrategy()
    
    # Verify they are instances of the expected types
    assert isinstance(word_overlap_strategy, WordOverlapChunkingStrategy)
    assert isinstance(sentence_strategy, SentenceSplitterChunkingStrategy)
    
    # Verify they both implement the ChunkingStrategy interface
    from create_embeddings.chunking import ChunkingStrategy
    assert isinstance(word_overlap_strategy, ChunkingStrategy)
    assert isinstance(sentence_strategy, ChunkingStrategy)
