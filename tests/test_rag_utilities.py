import pytest
from unittest.mock import patch, MagicMock
from src.utils.vector_store import chunk_text
from src.utils.keyword_search import BM25IndexManager, tokenize

def test_tokenize():
    text = "Hello, World! This is a test."
    tokens = tokenize(text)
    assert tokens == ["hello", "world", "this", "is", "a", "test"]

def test_chunk_text():
    text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
    # Use small chunk size to trigger splits
    chunks = chunk_text(text, chunk_size=10, chunk_overlap=2)
    assert len(chunks) > 0
    assert any("Sentence" in chunk for chunk in chunks)

def test_bm25_index():
    # Setup index manager in-memory (bypass saving to disk)
    with patch("src.utils.keyword_search.BM25IndexManager.save"):
        manager = BM25IndexManager()
        # Clean state
        manager.chunks = []
        manager.tokenized_corpus = []
        manager.bm25 = None
        
        # Add 3 docs so BM25 IDF is non-trivial (avoids log(1)=0 with 2 docs)
        manager.add_chunks("doc1", [
            "The quick brown fox jumps over the lazy dog",
            "Artificial intelligence is changing the world",
            "Knowledge graphs store semantic relationships between entities"
        ])
        
        # Query "fox" - first chunk should rank highest
        results = manager.query("fox", top_k=3)
        assert len(results) > 0, "Should return at least one result"
        assert "fox" in results[0]["text"], "Top result should contain 'fox'"
        
        # Query "intelligence" - second chunk should rank highest
        results = manager.query("intelligence", top_k=3)
        assert len(results) > 0
        assert "intelligence" in results[0]["text"], "Top result should contain 'intelligence'"
        
        # Metadata should be correct
        assert results[0]["metadata"]["document_id"] == "doc1"

