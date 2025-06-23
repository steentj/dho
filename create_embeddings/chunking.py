from abc import ABC, abstractmethod
import re
from typing import Iterable

class ChunkingStrategy(ABC):
    """Interface for different text chunking strategies."""

    @abstractmethod
    def chunk_text(self, text: str, max_tokens: int, title: str = None) -> Iterable[str]:
        """
        Splits the text into chunks of a specified maximum size.

        Args:
            text: The text to be chunked.
            max_tokens: The maximum number of tokens per chunk.
            title: An optional title to be added to each chunk.

        Returns:
            An iterable of text chunks.
        """
        pass

def _add_title_to_chunk(chunk_sentences: list[str], title: str | None) -> list[str]:
    """Prepend title to the first sentence of a chunk if a title is provided."""
    if title and chunk_sentences:
        # Add title only to the beginning of the first sentence
        chunk_sentences[0] = f"##{title}##{chunk_sentences[0]}"
    return chunk_sentences

class SentenceSplitterChunkingStrategy(ChunkingStrategy):
    """A chunking strategy that splits text by sentences."""

    def chunk_text(self, text: str, max_tokens: int, title: str = None) -> Iterable[str]:
        """
        Splits text into chunks by sentences, respecting a maximum token count.
        It attempts to keep sentences whole and adds a title to each chunk.
        """
        # Clean and normalize whitespace
        text = re.sub(r"\s+", " ", text.strip())
        if not text:
            return

        # Split text into sentences using a regular expression
        sentences = [s.strip() for s in re.findall(r'[^.!?]+[.!?]', text)]
        
        current_chunk_sentences = []
        current_chunk_tokens = 0

        for sentence in sentences:
            sentence_token_count = len(sentence.split())

            # If a single sentence is too long, split it hard
            if sentence_token_count > max_tokens:
                # First, yield any sentences already in the current chunk
                if current_chunk_sentences:
                    yield " ".join(_add_title_to_chunk(current_chunk_sentences, title))
                    current_chunk_sentences = []
                    current_chunk_tokens = 0

                # Split the oversized sentence into words
                words = sentence.split()
                for i in range(0, len(words), max_tokens):
                    # Create a chunk from a slice of words
                    word_chunk = words[i:i + max_tokens]
                    # Add title to the hard-split chunk
                    yield " ".join(_add_title_to_chunk([ " ".join(word_chunk)], title))
                continue

            # If adding the next sentence exceeds max_tokens, yield the current chunk
            if current_chunk_tokens + sentence_token_count > max_tokens and current_chunk_sentences:
                yield " ".join(_add_title_to_chunk(current_chunk_sentences, title))
                current_chunk_sentences = []
                current_chunk_tokens = 0
            
            # Add the sentence to the current chunk
            current_chunk_sentences.append(sentence)
            current_chunk_tokens += sentence_token_count

        # Yield any remaining sentences in the last chunk
        if current_chunk_sentences:
            yield " ".join(_add_title_to_chunk(current_chunk_sentences, title))


class WordOverlapChunkingStrategy(ChunkingStrategy):
    """A chunking strategy that splits text into approximately 400-word chunks with 50-word overlap."""

    def chunk_text(self, text: str, max_tokens: int, title: str = None) -> Iterable[str]:
        """
        Splits text into chunks of approximately 400 words with 50-word overlap, respecting sentence boundaries.
        Note: max_tokens parameter is ignored - this strategy uses fixed 400-word chunks.
        Title parameter is ignored - this strategy does not add title prefixes.
        """
        # Clean and normalize whitespace
        text = re.sub(r"\s+", " ", text.strip())
        if not text:
            return

        # Split text into sentences using a regular expression
        sentences = [s.strip() for s in re.findall(r'[^.!?]+[.!?]', text)]
        
        current_chunk_sentences = []
        current_chunk_words = 0
        target_words = 400
        overlap_words = 50
        last_was_hard_split = False

        for sentence in sentences:
            sentence_word_count = len(sentence.split())

            # If a single sentence is too long, split it hard
            if sentence_word_count > target_words * 1.1:  # Allow 10% tolerance
                # First, yield any sentences already in the current chunk
                if current_chunk_sentences:
                    yield " ".join(current_chunk_sentences)
                    current_chunk_sentences = []
                    current_chunk_words = 0

                # Split the oversized sentence into words
                words = sentence.split()
                for i in range(0, len(words), target_words):
                    # Create a chunk from a slice of words
                    word_chunk = words[i:i + target_words]
                    yield " ".join(word_chunk)
                last_was_hard_split = True
                continue

            # If adding the next sentence exceeds target with tolerance, yield the current chunk
            if (current_chunk_words + sentence_word_count > target_words * 1.1 and 
                current_chunk_sentences):
                yield " ".join(current_chunk_sentences)
                
                # Prepare overlap for next chunk only if last wasn't a hard split
                if not last_was_hard_split:
                    overlap_sentences, overlap_word_count = self._prepare_overlap(
                        current_chunk_sentences, overlap_words
                    )
                    # Start next chunk with overlap
                    current_chunk_sentences = overlap_sentences[:]
                    current_chunk_words = overlap_word_count
                else:
                    # Reset after hard split
                    current_chunk_sentences = []
                    current_chunk_words = 0
                
                last_was_hard_split = False
            
            # Add the sentence to the current chunk
            current_chunk_sentences.append(sentence)
            current_chunk_words += sentence_word_count
            last_was_hard_split = False  # Reset flag for normal sentences

        # Yield any remaining sentences in the last chunk
        if current_chunk_sentences:
            yield " ".join(current_chunk_sentences)

    def _prepare_overlap(self, chunk_sentences: list[str], overlap_words: int) -> tuple[list[str], int]:
        """
        Prepare overlap sentences from the end of the current chunk.
        Returns the last sentences that total approximately overlap_words.
        """
        if not chunk_sentences:
            return [], 0
        
        overlap_sentences = []
        overlap_word_count = 0
        
        # Work backwards from the end of the chunk
        for sentence in reversed(chunk_sentences):
            sentence_word_count = len(sentence.split())
            if overlap_word_count + sentence_word_count <= overlap_words * 1.2:  # Allow 20% tolerance
                overlap_sentences.insert(0, sentence)  # Insert at beginning to maintain order
                overlap_word_count += sentence_word_count
            else:
                break
        
        return overlap_sentences, overlap_word_count


class ChunkingStrategyFactory:
    """Factory for creating chunking strategy instances."""

    @staticmethod
    def create_strategy(strategy_name: str) -> ChunkingStrategy:
        """
        Creates a chunking strategy instance based on the provided name.

        Args:
            strategy_name: The name of the strategy to create.

        Returns:
            An instance of the specified chunking strategy.
        
        Raises:
            ValueError: If the strategy_name is unknown.
        """
        if strategy_name == "sentence_splitter":
            return SentenceSplitterChunkingStrategy()
        elif strategy_name == "word_overlap":
            return WordOverlapChunkingStrategy()
        # In the future, other strategies will be added here.
        # elif strategy_name == "recursive_character":
        #     return RecursiveCharacterChunkingStrategy()
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy_name}")
