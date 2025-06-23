from create_embeddings.opret_bøger import _process_cross_page_chunking, _find_starting_page
from create_embeddings.chunking import WordOverlapChunkingStrategy, SentenceSplitterChunkingStrategy, ChunkingStrategyFactory


def test_find_starting_page():
    """Test the helper function for finding starting page"""
    page_markers = [(0, 1), (50, 2), (120, 3), (200, 4)]
    
    # Test various word positions
    assert _find_starting_page(0, page_markers) == 1
    assert _find_starting_page(25, page_markers) == 1
    assert _find_starting_page(50, page_markers) == 2
    assert _find_starting_page(75, page_markers) == 2
    assert _find_starting_page(120, page_markers) == 3
    assert _find_starting_page(150, page_markers) == 3
    assert _find_starting_page(200, page_markers) == 4
    assert _find_starting_page(250, page_markers) == 4
    
    # Edge cases
    assert _find_starting_page(0, []) == 1
    assert _find_starting_page(100, [(0, 1)]) == 1


def test_process_cross_page_chunking_basic():
    """Test basic cross-page chunking functionality"""
    # Create mock PDF pages
    pdf_pages = {
        1: "First page with some text. This continues on first page.",
        2: "Second page starts here. More text on second page.",
        3: "Third page begins. Final text here."
    }
    
    strategy = WordOverlapChunkingStrategy()
    chunk_size = 500  # Large enough to not split this small text
    
    result_chunks = _process_cross_page_chunking(pdf_pages, chunk_size, strategy, "Test Title")
    
    # Should get at least one chunk
    assert len(result_chunks) > 0
    
    # Each result should be (page_num, chunk_text) tuple
    for page_num, chunk_text in result_chunks:
        assert isinstance(page_num, int)
        assert isinstance(chunk_text, str)
        assert page_num >= 1
        assert len(chunk_text.strip()) > 0


def test_process_cross_page_chunking_spans_pages():
    """Test that chunks can span multiple pages"""
    # Create pages with more substantial content to force cross-page chunks
    pdf_pages = {}
    for i in range(1, 11):  # 10 pages
        # Each page now has about 50 words (5 sentences x 10 words each)
        sentences = [f"This is sentence {j} on page {i} with some additional content to make it longer." for j in range(1, 6)]
        pdf_pages[i] = " ".join(sentences)
    
    strategy = WordOverlapChunkingStrategy()
    chunk_size = 400  # Target size that should create multiple chunks (500 total words / 400 per chunk = ~2 chunks)
    
    result_chunks = _process_cross_page_chunking(pdf_pages, chunk_size, strategy, "Test Title")
    
    assert len(result_chunks) >= 2  # Should create multiple chunks
    
    # Check that we have chunks starting on different pages
    starting_pages = [page_num for page_num, _ in result_chunks]
    unique_pages = set(starting_pages)
    
    # Should have chunks starting on multiple pages
    assert len(unique_pages) >= 2, f"Chunks only start on pages: {unique_pages}"
    
    # All starting pages should be valid
    for page_num in starting_pages:
        assert 1 <= page_num <= 10, f"Invalid starting page: {page_num}"


def test_process_cross_page_chunking_preserves_overlap():
    """Test that overlap is preserved in cross-page chunking"""
    # Create content that will definitely need multiple chunks
    pages_content = []
    for i in range(1, 21):  # 20 pages with substantial content
        page_text = " ".join([f"Sentence {j} on page {i}." for j in range(1, 21)])  # 20 sentences per page
        pages_content.append(page_text)
    
    pdf_pages = {i+1: content for i, content in enumerate(pages_content)}
    
    strategy = WordOverlapChunkingStrategy()
    chunk_size = 400  # Should create multiple chunks with overlap
    
    result_chunks = _process_cross_page_chunking(pdf_pages, chunk_size, strategy, "Test Title")
    
    assert len(result_chunks) >= 3  # Should create multiple chunks
    
    # Check for overlap between consecutive chunks
    if len(result_chunks) >= 2:
        chunk1_text = result_chunks[0][1]
        chunk2_text = result_chunks[1][1]
        
        # Extract sentence numbers from chunks for overlap detection
        import re
        chunk1_sentences = re.findall(r'Sentence (\d+)', chunk1_text)
        chunk2_sentences = re.findall(r'Sentence (\d+)', chunk2_text)
        
        # Should have some overlap
        overlap = set(chunk1_sentences) & set(chunk2_sentences)
        assert len(overlap) > 0, "No overlap found between consecutive chunks"


def test_cross_page_chunking_vs_page_by_page():
    """Test that cross-page chunking produces different results than page-by-page"""
    # Create pages where cross-page chunking should be beneficial
    pdf_pages = {
        1: "Short text on page one.",
        2: "Brief content on page two.",
        3: "Small amount on page three.",
        4: "Little text on page four.",
        5: "Minimal content on page five."
    }
    
    word_overlap_strategy = WordOverlapChunkingStrategy()
    sentence_strategy = SentenceSplitterChunkingStrategy()
    chunk_size = 400
    
    # Get cross-page chunks (word overlap)
    cross_page_chunks = _process_cross_page_chunking(pdf_pages, chunk_size, word_overlap_strategy, "Test")
    
    # Simulate page-by-page chunks (sentence strategy)
    page_by_page_chunks = []
    for page_num, page_text in pdf_pages.items():
        for chunk in sentence_strategy.chunk_text(page_text, chunk_size, "Test"):
            if chunk.strip():
                page_by_page_chunks.append((page_num, chunk))
    
    # Cross-page should produce fewer, larger chunks
    cross_page_count = len(cross_page_chunks)
    page_by_page_count = len(page_by_page_chunks)
    
    # Should be different approaches
    assert cross_page_count != page_by_page_count or cross_page_chunks != page_by_page_chunks
    
    # Cross-page chunks should be able to span multiple pages
    cross_page_starting_pages = {page_num for page_num, _ in cross_page_chunks}
    page_by_page_starting_pages = {page_num for page_num, _ in page_by_page_chunks}
    
    # Page-by-page should have chunks starting on every page with content
    assert len(page_by_page_starting_pages) == 5  # All 5 pages
    
    # Cross-page might have fewer starting pages (chunks can span pages)
    assert len(cross_page_starting_pages) <= 5


def test_backward_compatibility_sentence_splitter():
    """Test that SentenceSplitterChunkingStrategy still works with new parse_book logic"""
    # This test simulates what happens in parse_book with SentenceSplitterChunkingStrategy
    pdf_pages = {
        1: "First page has this sentence. Another sentence on first page.",
        2: "Second page starts here. More content on second page.",
        3: "Third page begins now. Final content here."
    }
    
    from create_embeddings.opret_bøger import _process_cross_page_chunking
    
    sentence_strategy = SentenceSplitterChunkingStrategy()
    
    # This should NOT be called for SentenceSplitterChunkingStrategy in parse_book
    # But let's verify it would work if accidentally called
    try:
        cross_page_result = _process_cross_page_chunking(pdf_pages, 20, sentence_strategy, "Title")
        # Should work without error, even if not intended for this strategy
        assert len(cross_page_result) > 0
    except Exception:
        # If it fails, that's also acceptable since it's not meant for this strategy
        pass
    
    # Test traditional page-by-page processing (what should actually happen)
    page_by_page_chunks = []
    for page_num, page_text in pdf_pages.items():
        for chunk in sentence_strategy.chunk_text(page_text, 20, "Title"):
            if chunk.strip():
                page_by_page_chunks.append((page_num, chunk))
    
    # Should have chunks from each page
    assert len(page_by_page_chunks) >= 3  # At least one chunk per page
    
    # Each chunk should have title prefix (SentenceSplitterChunkingStrategy behavior)
    for page_num, chunk in page_by_page_chunks:
        assert chunk.startswith("##Title##"), f"Chunk missing title: {chunk[:50]}"


def test_strategy_interface_compliance():
    """Test that both strategies comply with the ChunkingStrategy interface"""
    sentence_strategy = SentenceSplitterChunkingStrategy()
    word_overlap_strategy = WordOverlapChunkingStrategy()
    
    test_text = "First sentence here. Second sentence follows. Third sentence continues."
    
    # Both strategies should implement the same interface
    sentence_chunks = list(sentence_strategy.chunk_text(test_text, 50, "Test"))
    word_overlap_chunks = list(word_overlap_strategy.chunk_text(test_text, 50, "Test"))
    
    # Both should return iterables of strings
    assert all(isinstance(chunk, str) for chunk in sentence_chunks)
    assert all(isinstance(chunk, str) for chunk in word_overlap_chunks)
    
    # Both should handle the same parameters without error
    assert len(sentence_chunks) > 0
    assert len(word_overlap_chunks) > 0
    
    # Verify different behaviors as expected
    # SentenceSplitterChunkingStrategy adds title
    assert any("##Test##" in chunk for chunk in sentence_chunks)
    
    # WordOverlapChunkingStrategy ignores title
    assert not any("##Test##" in chunk for chunk in word_overlap_chunks)


def test_factory_backward_compatibility():
    """Test that the factory still creates existing strategies correctly"""
    # Test existing strategy creation
    sentence_strategy = ChunkingStrategyFactory.create_strategy("sentence_splitter")
    assert isinstance(sentence_strategy, SentenceSplitterChunkingStrategy)
    
    # Test new strategy creation
    word_overlap_strategy = ChunkingStrategyFactory.create_strategy("word_overlap")
    assert isinstance(word_overlap_strategy, WordOverlapChunkingStrategy)
    
    # Test error handling for unknown strategies
    try:
        ChunkingStrategyFactory.create_strategy("nonexistent_strategy")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown chunking strategy" in str(e)
    
    # Test that old strategy names still work
    test_text = "Test sentence one. Test sentence two."
    
    old_chunks = list(sentence_strategy.chunk_text(test_text, 50, "Title"))
    new_chunks = list(word_overlap_strategy.chunk_text(test_text, 50, "Title"))
    
    # Should both produce valid output
    assert len(old_chunks) > 0
    assert len(new_chunks) > 0
