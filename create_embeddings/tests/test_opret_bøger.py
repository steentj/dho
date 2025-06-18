from create_embeddings.opret_bøger import add_title_to_chunk


class TestAddTitleToChunk:
    def test_add_title_to_chunk_with_title(self):
        """Test that title is correctly added to chunk when title is provided."""
        chunk = "This is a test chunk"
        title = "Test Book"
        result = add_title_to_chunk(chunk, title)
        expected = "##Test Book##This is a test chunk"
        assert result == expected

    def test_add_title_to_chunk_without_title(self):
        """Test that chunk is returned unchanged when title is None."""
        chunk = "This is a test chunk"
        title = None
        result = add_title_to_chunk(chunk, title)
        assert result == chunk

    def test_add_title_to_chunk_with_empty_title(self):
        """Test that chunk is returned unchanged when title is empty string."""
        chunk = "This is a test chunk"
        title = ""
        result = add_title_to_chunk(chunk, title)
        assert result == chunk

    def test_add_title_to_chunk_with_empty_chunk(self):
        """Test that title format is applied even with empty chunk."""
        chunk = ""
        title = "Test Book"
        result = add_title_to_chunk(chunk, title)
        expected = "##Test Book##"
        assert result == expected

    def test_add_title_to_chunk_with_special_characters(self):
        """Test that special characters in title and chunk are handled correctly."""
        chunk = "Chunk with special chars: æøå & symbols!"
        title = "Title with æøå"
        result = add_title_to_chunk(chunk, title)
        expected = "##Title with æøå##Chunk with special chars: æøå & symbols!"
        assert result == expected

    def test_add_title_to_chunk_with_whitespace_title(self):
        """Test that whitespace-only title is treated as falsy."""
        chunk = "This is a test chunk"
        title = "   "
        result = add_title_to_chunk(chunk, title)
        expected = "##   ##This is a test chunk"
        assert result == expected

    def test_add_title_to_chunk_with_list_input(self):
        """Test that function works when chunk is passed as list (as used in the code)."""
        chunk_list = ["This", "is", "a", "test", "chunk"]
        title = "Test Book"
        result = add_title_to_chunk(chunk_list, title)
        expected = "##Test Book##['This', 'is', 'a', 'test', 'chunk']"
        assert result == expected