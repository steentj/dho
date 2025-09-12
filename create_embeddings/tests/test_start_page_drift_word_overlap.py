from create_embeddings.chunking import WordOverlapChunkingStrategy


def _make_unique_sentence(page: int, sent_idx: int, words_per_sentence: int) -> str:
    """Create a sentence where each word is globally unique, ending with a period."""
    tokens = [f"P{page:02d}_S{sent_idx:02d}_W{i:02d}" for i in range(1, words_per_sentence)]
    # Attach period to the last token to form a sentence terminator recognized by the splitter
    return " ".join(tokens + [f"P{page:02d}_S{sent_idx:02d}_W{words_per_sentence:02d}."])


def _make_page(page: int, sentences: int, words_per_sentence: int) -> str:
    return " ".join(_make_unique_sentence(page, s, words_per_sentence) for s in range(1, sentences + 1))


def _build_full_tokens_and_markers(pages: dict[int, str]) -> tuple[list[str], list[tuple[int, int]]]:
    """Replicate process_document concatenation and build page markers for ALL pages (including empty)."""
    full_tokens: list[str] = []
    markers: list[tuple[int, int]] = []
    current_pos = 0
    for p in sorted(pages.keys()):
        # marker at the start of every page, even if empty
        markers.append((current_pos, p))
        txt = pages[p].strip()
        if txt:
            words = txt.split()
            full_tokens.extend(words)
            current_pos += len(words)
    return full_tokens, markers


def _find_sequence_index(haystack: list[str], needle: list[str], max_probe: int = 50) -> int:
    """Find start index of needle (first min(len(needle), max_probe) tokens) in haystack; -1 if not found."""
    if not needle:
        return -1
    probe_len = min(len(needle), max_probe)
    needle_probe = needle[:probe_len]
    # naive scan (acceptable for test sizes)
    for i in range(0, len(haystack) - probe_len + 1):
        if haystack[i : i + probe_len] == needle_probe:
            return i
    return -1


def _map_pos_to_page(pos: int, markers: list[tuple[int, int]]) -> int:
    page = markers[0][1]
    for mpos, p in markers:
        if mpos <= pos:
            page = p
        else:
            break
    return page


def test_word_overlap_start_pages_match_source_positions_with_empty_pages():
    """
    Ground-truth test: compute chunk start positions by locating chunk tokens inside the
    concatenated source tokens, and ensure the mapped page equals the strategy-reported page.

    Includes EMPTY pages to simulate real-world PDFs with blank pages. The expected mapping
    must account for page markers on empty pages as well.
    """
    total_pages = 30
    sentences_per_page = 8
    words_per_sentence = 10

    # Introduce some empty pages
    empty_pages = {1, 5, 16, 23}
    pages: dict[int, str] = {}
    for p in range(1, total_pages + 1):
        if p in empty_pages:
            pages[p] = ""  # empty page
        else:
            pages[p] = _make_page(p, sentences_per_page, words_per_sentence)

    # Build ground-truth token stream and page markers (including empties)
    full_tokens, markers = _build_full_tokens_and_markers(pages)

    # Execute chunking
    strategy = WordOverlapChunkingStrategy()
    chunk_size = 300
    chunks = list(strategy.process_document(pages, chunk_size, title="Ignored"))

    assert len(chunks) >= 2

    # Verify each chunk's start page against ground truth mapping
    for reported_page, chunk_text in chunks:
        chunk_tokens = chunk_text.split()
        start_idx = _find_sequence_index(full_tokens, chunk_tokens, max_probe=40)
        assert start_idx >= 0, "Chunk tokens not found in source token stream"
        expected_page = _map_pos_to_page(start_idx, markers)
        assert reported_page == expected_page, f"Mismatch: reported={reported_page}, expected={expected_page} at idx={start_idx}"
