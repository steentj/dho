import pytest
import re
from create_embeddings.chunking import SentenceSplitterChunkingStrategy, WordOverlapChunkingStrategy, ChunkingStrategyFactory

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


# Tests for WordOverlapChunkingStrategy
@pytest.fixture
def word_overlap_strategy():
    return WordOverlapChunkingStrategy()

def test_word_overlap_basic_chunking(word_overlap_strategy):
    # Create text with approximately 450 words (should create 2 chunks)
    text = " ".join(["This is sentence number {}.".format(i) for i in range(1, 91)])  # ~450 words
    chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=400))
    
    assert len(chunks) == 2
    # First chunk should be around max_tokens words
    first_chunk_words = len(chunks[0].split())
    assert 360 <= first_chunk_words <= 440  # Allow 10% tolerance around 400
    
    # Second chunk should contain the remaining words
    second_chunk_words = len(chunks[1].split())
    assert second_chunk_words > 0

def test_word_overlap_respects_max_tokens_small_text(word_overlap_strategy):
    # 20 simple words without punctuation triggers small-text path
    text = " ".join([f"word{i}" for i in range(1, 21)])
    chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=7))
    # Expect ceil(20/7) = 3 chunks, all <= 7 words
    assert len(chunks) == 3
    assert all(len(chunk.split()) <= 7 for chunk in chunks)

def test_word_overlap_tiny_text_guard(word_overlap_strategy):
    # For extremely small texts and max_tokens=1 we avoid over-chunking by design
    text = "This is a short sentence. This is another short sentence."
    chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=1))
    assert len(chunks) == 1

def test_word_overlap_ignores_title(word_overlap_strategy):
    text = "This is a sentence."
    title = "My Book"
    chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=10, title=title))
    assert len(chunks) == 1
    assert chunks[0] == "This is a sentence."  # No title prefix

def test_word_overlap_empty_text(word_overlap_strategy):
    text = ""
    chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=10))
    assert len(chunks) == 0

def test_word_overlap_whitespace_handling(word_overlap_strategy):
    text = "  This is sentence one.    This is sentence two.  "
    chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=10))
    assert len(chunks) == 1
    assert chunks[0] == "This is sentence one. This is sentence two."

def test_word_overlap_hard_split_long_sentence(word_overlap_strategy):
    # Create a single sentence with > 440 words (exceeds 10% tolerance)
    long_sentence = "This is a very " + "extremely " * 450 + "long sentence."
    chunks = list(word_overlap_strategy.chunk_text(long_sentence, max_tokens=10))
    
    assert len(chunks) > 1  # Should be split
    # Each chunk should be no more than max_tokens words
    for chunk in chunks:
        word_count = len(chunk.split())
        assert word_count <= 10

def test_factory_creates_word_overlap_strategy():
    strategy = ChunkingStrategyFactory.create_strategy("word_overlap")
    assert isinstance(strategy, WordOverlapChunkingStrategy)

def test_word_overlap_functionality(word_overlap_strategy):
    # Create text that will definitely create multiple chunks with overlap
    sentences = []
    for i in range(1, 101):  # 100 sentences, each ~5 words = 500 words total
        sentences.append(f"This is sentence number {i} in the text.")
    text = " ".join(sentences)
    
    chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=500))
    
    assert len(chunks) >= 2  # Should create multiple chunks
    
    if len(chunks) >= 2:
        # Check that there's overlap between first and second chunk
        first_chunk_text = chunks[0]
        second_chunk_text = chunks[1]
        
        # Look for sentences that appear in both chunks
        # Since we know the pattern: "This is sentence number X in the text."
        # We can find the sentence numbers in each chunk
        import re
        first_chunk_numbers = [int(match.group(1)) for match in re.finditer(r'sentence number (\d+)', first_chunk_text)]
        second_chunk_numbers = [int(match.group(1)) for match in re.finditer(r'sentence number (\d+)', second_chunk_text)]
        
        # Find overlapping sentence numbers
        overlap_numbers = set(first_chunk_numbers) & set(second_chunk_numbers)
        
        # There should be some overlap
        assert len(overlap_numbers) > 0, f"No overlap found. First chunk: {first_chunk_numbers[-5:]}, Second chunk: {second_chunk_numbers[:5]}"
        
        # The overlap should be around 50 words (about 7 sentences in our test)
        assert len(overlap_numbers) >= 5, f"Overlap too small: {len(overlap_numbers)} sentences"

def test_word_overlap_no_overlap_for_hard_split(word_overlap_strategy):
    # Create a single very long sentence that will be hard-split
    long_sentence = "This is an extremely " + "very " * 500 + "long sentence."
    # Use a smaller max_tokens so the single sentence exceeds the hard-split threshold
    chunks = list(word_overlap_strategy.chunk_text(long_sentence, max_tokens=100))
    
    assert len(chunks) >= 2  # Should be split
    
    # Hard-split chunks should not have sentence-level overlap
    # Since we have only one sentence that's being hard-split, 
    # we should NOT see complete sentences repeated between chunks
    if len(chunks) >= 2:
        # For hard splits, each chunk should contain only part of the original sentence
        # None of the chunks should contain the complete sentence
        complete_sentence = long_sentence
        for chunk in chunks:
            # No chunk should contain the complete original sentence
            assert complete_sentence not in chunk, "Hard-split chunk contains complete original sentence"
            
        # Also check that we don't have sentence-ending patterns in the middle chunks
        # (only the last chunk should end with a period)
        for i, chunk in enumerate(chunks[:-1]):  # All but the last
            assert not chunk.endswith('.'), f"Hard-split chunk {i} ends with period (should only be the last chunk)"

def test_word_overlap_prepare_overlap_helper(word_overlap_strategy):
    # Test the helper method directly
    chunk_sentences = [
        "First sentence with five words.",
        "Second sentence has six total words.", 
        "Third sentence contains exactly seven words here.",
        "Fourth sentence."
    ]
    
    overlap_sentences, overlap_count = word_overlap_strategy._prepare_overlap(chunk_sentences, 50)
    
    # Should return some sentences for overlap
    assert len(overlap_sentences) > 0
    assert overlap_count > 0
    assert overlap_count <= 50 * 1.2  # Within tolerance
    
    # Check that sentences are in correct order
    original_text = " ".join(chunk_sentences)
    overlap_text = " ".join(overlap_sentences)
    assert overlap_text in original_text

def test_word_overlap_sentence_boundaries(word_overlap_strategy):
    """Test that chunks always begin and end at sentence boundaries"""
    # Create text with clear sentence patterns
    text = "First sentence here. Second sentence follows. Third sentence continues. " \
           "Fourth sentence appears. Fifth sentence comes next. Sixth sentence is present. " \
           "Seventh sentence exists. Eighth sentence occurs. Ninth sentence happens. " \
           "Tenth sentence concludes."
    
    chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=500))
    
    for i, chunk in enumerate(chunks):
        # Each chunk should start with a capital letter (beginning of sentence)
        assert chunk[0].isupper() or chunk[0].isdigit(), f"Chunk {i} doesn't start with capital letter: '{chunk[:20]}...'"
        
        # Each chunk should end with sentence punctuation
        assert chunk.rstrip().endswith(('.', '!', '?')), f"Chunk {i} doesn't end with sentence punctuation: '...{chunk[-20:]}'"
        
        # Check that chunk contains complete sentences only
        # Split chunk into sentences and verify each is complete
        chunk_sentences = [s.strip() for s in re.findall(r'[^.!?]+[.!?]', chunk)]
        assert len(chunk_sentences) > 0, f"Chunk {i} contains no complete sentences"
        
        # Each sentence in chunk should be properly formed
        for sentence in chunk_sentences:
            assert sentence.endswith(('.', '!', '?')), f"Incomplete sentence in chunk {i}: '{sentence}'"

def test_word_overlap_mixed_punctuation_boundaries(word_overlap_strategy):
    """Test sentence boundaries with mixed punctuation"""
    text = "Statement one. Question two? Exclamation three! Another statement. " \
           "Is this working? Yes it is! Final statement here. " \
           "More text follows. Does it handle questions? Absolutely! " \
           "The end approaches. Will this work? I think so!"
    
    chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=500))
    
    for i, chunk in enumerate(chunks):
        # Should start with capital or digit
        assert chunk[0].isupper() or chunk[0].isdigit(), f"Chunk {i} starts incorrectly: '{chunk[:10]}'"
        
        # Should end with proper punctuation  
        assert chunk.rstrip().endswith(('.', '!', '?')), f"Chunk {i} ends incorrectly: '{chunk[-10:]}'"
        
        # Should not have incomplete sentences (no sentences ending mid-word)
        lines = chunk.split('.')
        if len(lines) > 1 and lines[-1].strip():  # If there's text after the last period
            # The text after last period should be complete sentence ending with ! or ?
            remaining = lines[-1].strip()
            if remaining:  # If there's remaining text
                assert remaining.endswith(('!', '?')), f"Incomplete sentence fragment: '{remaining}'"

def test_word_overlap_no_mid_sentence_breaks(word_overlap_strategy):
    """Test that sentences are never broken in the middle"""
    # Create a text where naive word-count splitting would break sentences
    long_sentences = []
    for i in range(20):
        # Each sentence is exactly 25 words - this should force some interesting boundary decisions
        sentence_words = [f"word{j}" for j in range(24)] + ["end."]
        long_sentences.append(" ".join(sentence_words))
    
    text = " ".join(long_sentences)
    chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=500))
    
    # Verify no sentence is broken across chunks
    original_sentences = [s.strip() for s in re.findall(r'[^.!?]+[.!?]', text)]
    
    for original_sentence in original_sentences:
        # Each original sentence should appear complete in exactly one chunk
        appearances = sum(1 for chunk in chunks if original_sentence in chunk)
        assert appearances >= 1, f"Sentence missing from chunks: '{original_sentence[:50]}...'"
        
        # Due to overlap, a sentence might appear in multiple chunks, which is okay
        # The important thing is that it's never broken apart

def test_word_overlap_no_title_prefix(word_overlap_strategy):
    """Test that WordOverlapChunkingStrategy ignores title parameter and adds no prefixes"""
    text = "First sentence here. Second sentence follows. Third sentence continues."
    title = "My Important Book"
    
    # Test with title parameter
    chunks_with_title = list(word_overlap_strategy.chunk_text(text, max_tokens=500, title=title))
    
    # Test without title parameter  
    chunks_without_title = list(word_overlap_strategy.chunk_text(text, max_tokens=500))
    
    # Should produce identical results regardless of title parameter
    assert len(chunks_with_title) == len(chunks_without_title)
    
    for i, (chunk_with, chunk_without) in enumerate(zip(chunks_with_title, chunks_without_title)):
        assert chunk_with == chunk_without, f"Chunk {i} differs with/without title"
        
        # Verify no title prefix is added
        assert not chunk_with.startswith("##"), f"Chunk {i} has title prefix: '{chunk_with[:30]}'"
        assert title not in chunk_with, f"Chunk {i} contains title text: '{chunk_with[:50]}'"
        
        # Should start with original text, not title
        assert chunk_with.startswith("First"), f"Chunk {i} doesn't start with original text: '{chunk_with[:30]}'"

def test_title_behavior_comparison():
    """Compare title behavior between SentenceSplitterChunkingStrategy and WordOverlapChunkingStrategy"""
    text = "First sentence here. Second sentence follows."
    title = "Test Book"
    
    sentence_strategy = SentenceSplitterChunkingStrategy()
    word_overlap_strategy = WordOverlapChunkingStrategy()
    
    # SentenceSplitterChunkingStrategy should add title prefixes
    sentence_chunks = list(sentence_strategy.chunk_text(text, max_tokens=20, title=title))
    
    # WordOverlapChunkingStrategy should NOT add title prefixes
    word_overlap_chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=500, title=title))
    
    # Verify SentenceSplitterChunkingStrategy adds titles
    for chunk in sentence_chunks:
        assert chunk.startswith(f"##{title}##"), f"SentenceSplitter chunk missing title: '{chunk[:50]}'"
    
    # Verify WordOverlapChunkingStrategy does NOT add titles
    for chunk in word_overlap_chunks:
        assert not chunk.startswith("##"), f"WordOverlap chunk has unexpected title: '{chunk[:50]}'"
        assert title not in chunk, f"WordOverlap chunk contains title: '{chunk[:50]}'"

def test_word_overlap_ignores_various_titles(word_overlap_strategy):
    """Test that various title formats are completely ignored"""
    text = "Sentence one. Sentence two. Sentence three."
    
    test_titles = [
        "Simple Title",
        "Title with Numbers 123",
        "Title with Special !@# Characters",
        "Very Long Title That Goes On And On With Many Words",
        "",  # Empty title
        None,  # None title
        "Title\nWith\nNewlines",
        "Title with 'quotes' and \"double quotes\""
    ]
    
    # Get baseline result with no title
    baseline_chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=500))
    
    # Test each title produces identical results
    for title in test_titles:
        chunks = list(word_overlap_strategy.chunk_text(text, max_tokens=500, title=title))
        
        assert len(chunks) == len(baseline_chunks), f"Different chunk count with title '{title}'"
        
        for i, (baseline_chunk, titled_chunk) in enumerate(zip(baseline_chunks, chunks)):
            assert baseline_chunk == titled_chunk, f"Chunk {i} differs with title '{title}'"
