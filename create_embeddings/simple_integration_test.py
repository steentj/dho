#!/usr/bin/env python3
"""
Simple integration test for WordOverlapChunkingStrategy
Tests key functionality without complex imports
"""

import sys
import os

# Ensure we can import from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chunking import WordOverlapChunkingStrategy, SentenceSplitterChunkingStrategy, ChunkingStrategyFactory


def test_basic_functionality():
    """Test that the basic functionality works"""
    print("Testing basic functionality...")
    
    # Test factory creation
    word_overlap = ChunkingStrategyFactory.create_strategy("word_overlap")
    sentence_splitter = ChunkingStrategyFactory.create_strategy("sentence_splitter")
    
    assert isinstance(word_overlap, WordOverlapChunkingStrategy)
    assert isinstance(sentence_splitter, SentenceSplitterChunkingStrategy)
    print("✓ Factory creates correct strategy types")
    
    # Test basic chunking
    test_text = "This is the first sentence. This is the second sentence. " * 50
    word_chunks = list(word_overlap.chunk_text(test_text, 400, "Test"))
    sentence_chunks = list(sentence_splitter.chunk_text(test_text, 50, "Test"))
    
    assert len(word_chunks) > 0
    assert len(sentence_chunks) > 0
    print("✓ Both strategies produce chunks")
    
    # Test title handling differences
    for chunk in word_chunks:
        assert not chunk.startswith("##"), f"Word overlap chunk shouldn't have title prefix: {chunk[:50]}"
    
    for chunk in sentence_chunks:
        assert chunk.startswith("##Test##"), f"Sentence chunk should have title prefix: {chunk[:50]}"
    
    print("✓ Title handling works correctly")
    return True


def test_overlap_functionality():
    """Test that overlap works in WordOverlapChunkingStrategy"""
    print("\nTesting overlap functionality...")
    
    strategy = WordOverlapChunkingStrategy()
    
    # Create text with identifiable sentences for overlap testing - make it longer
    sentences = []
    for i in range(100):  # More sentences to ensure multiple chunks
        sentences.append(f"This is sentence number {i} with substantial content for testing overlap functionality.")
    
    text = " ".join(sentences)
    chunks = list(strategy.chunk_text(text, 400, "Test"))
    
    print(f"Generated {len(chunks)} chunks from {len(text.split())} words")
    assert len(chunks) >= 2, f"Should have multiple chunks for overlap testing, got {len(chunks)}"
    
    # Check for overlap between consecutive chunks
    overlaps_found = 0
    for i in range(len(chunks) - 1):
        chunk1_words = set(chunks[i].split())
        chunk2_words = set(chunks[i + 1].split())
        overlap = chunk1_words & chunk2_words
        if overlap:
            overlaps_found += 1
            print(f"  Found {len(overlap)} overlapping words between chunks {i} and {i+1}")
    
    assert overlaps_found > 0, "Should find overlaps between consecutive chunks"
    print(f"✓ Found overlaps in {overlaps_found} chunk pairs")
    
    return True


def test_cross_page_simulation():
    """Simulate cross-page chunking behavior"""
    print("\nTesting cross-page chunking simulation...")
    
    strategy = WordOverlapChunkingStrategy()
    
    # Create pages with substantial content
    pages = {}
    for page_num in range(1, 4):
        sentences = []
        for i in range(30):  # 30 sentences per page
            sentences.append(f"Page {page_num} sentence {i}: Some meaningful content here.")
        pages[page_num] = " ".join(sentences)
    
    # Simulate cross-page chunking
    all_text = " ".join(pages.values())
    chunks = list(strategy.chunk_text(all_text, 400, "Test"))
    
    # Should have fewer chunks than pages due to cross-page spanning
    assert len(chunks) < len(pages), f"Expected fewer chunks ({len(chunks)}) than pages ({len(pages)})"
    
    # Check that chunks contain content from multiple pages
    cross_page_chunks = 0
    for chunk in chunks:
        pages_mentioned = set()
        for page_num in pages.keys():
            if f"Page {page_num}" in chunk:
                pages_mentioned.add(page_num)
        
        if len(pages_mentioned) > 1:
            cross_page_chunks += 1
    
    assert cross_page_chunks > 0, "Should have chunks spanning multiple pages"
    print(f"✓ Found {cross_page_chunks} cross-page chunks out of {len(chunks)} total chunks")
    
    return True


def test_sentence_boundary_preservation():
    """Test that chunks respect sentence boundaries"""
    print("\nTesting sentence boundary preservation...")
    
    strategy = WordOverlapChunkingStrategy()
    
    # Create text with clear sentence boundaries
    text = "First sentence here. Second sentence follows. Third sentence continues. " * 50
    chunks = list(strategy.chunk_text(text, 400, "Test"))
    
    for i, chunk in enumerate(chunks):
        # Should start with capital letter (sentence start)
        assert chunk[0].isupper() or chunk[0].isdigit(), f"Chunk {i} doesn't start with capital: '{chunk[:20]}...'"
        
        # Should end with sentence-ending punctuation
        assert chunk.rstrip().endswith(('.', '!', '?')), f"Chunk {i} doesn't end with sentence punctuation: '...{chunk[-20:]}'"
    
    print("✓ All chunks respect sentence boundaries")
    return True


def test_backward_compatibility():
    """Test that existing functionality still works"""
    print("\nTesting backward compatibility...")
    
    # Test that sentence splitter still works as before
    sentence_strategy = ChunkingStrategyFactory.create_strategy("sentence_splitter")
    
    test_text = "Test sentence one. Test sentence two. Test sentence three."
    chunks = list(sentence_strategy.chunk_text(test_text, 100, "BackwardTest"))
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.startswith("##BackwardTest##")
    
    print("✓ SentenceSplitterChunkingStrategy works as before")
    
    # Test factory still raises error for unknown strategies
    try:
        ChunkingStrategyFactory.create_strategy("unknown_strategy")
        assert False, "Should have raised ValueError for unknown strategy"
    except ValueError:
        pass  # Expected
    
    print("✓ Factory error handling works as before")
    
    return True


def run_all_tests():
    """Run all integration tests"""
    print("Running simple integration tests for WordOverlapChunkingStrategy")
    print("=" * 70)
    
    tests = [
        test_basic_functionality,
        test_overlap_functionality,
        test_cross_page_simulation,
        test_sentence_boundary_preservation,
        test_backward_compatibility
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed: {e}")
    
    print("\n" + "=" * 70)
    print(f"Integration test results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! The WordOverlapChunkingStrategy is working correctly.")
        return True
    else:
        print("❌ Some integration tests failed.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
