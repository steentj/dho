#!/usr/bin/env python3
"""
Quick test to verify the new supports_cross_page_chunking() interface method works correctly.
"""

from create_embeddings.chunking import ChunkingStrategyFactory, SentenceSplitterChunkingStrategy, WordOverlapChunkingStrategy

def test_interface_method():
    """Test that both strategies correctly implement supports_cross_page_chunking()"""
    
    # Test direct instantiation
    sentence_strategy = SentenceSplitterChunkingStrategy()
    word_overlap_strategy = WordOverlapChunkingStrategy()
    
    print("Direct instantiation tests:")
    print(f"SentenceSplitterChunkingStrategy.supports_cross_page_chunking(): {sentence_strategy.supports_cross_page_chunking()}")
    print(f"WordOverlapChunkingStrategy.supports_cross_page_chunking(): {word_overlap_strategy.supports_cross_page_chunking()}")
    
    # Test factory instantiation
    sentence_factory = ChunkingStrategyFactory.create_strategy("sentence_splitter")
    word_overlap_factory = ChunkingStrategyFactory.create_strategy("word_overlap")
    
    print("\nFactory instantiation tests:")
    print(f"Factory sentence_splitter.supports_cross_page_chunking(): {sentence_factory.supports_cross_page_chunking()}")
    print(f"Factory word_overlap.supports_cross_page_chunking(): {word_overlap_factory.supports_cross_page_chunking()}")
    
    # Verify expected behavior
    assert not sentence_strategy.supports_cross_page_chunking()
    assert word_overlap_strategy.supports_cross_page_chunking()
    assert not sentence_factory.supports_cross_page_chunking()
    assert word_overlap_factory.supports_cross_page_chunking()
    
    print("\n✅ All interface method tests passed!")

if __name__ == "__main__":
    test_interface_method()
