import os
from loguru import logger
from src.config import settings
from src.utils.parser import parse_file
from src.utils.vector_store import chunk_text, index_chunks
from src.utils.entity_extractor import extract_knowledge_graph_elements
from src.utils.graph_store import upsert_entities_and_relations
from src.utils.keyword_search import add_to_bm25_index

def ingest_document_pipeline(file_path: str, document_id: str = None) -> dict:
    """
    Background (slow path) pipeline:
    1. Parse file using LlamaParse
    2. Split into chunks using SentenceSplitter
    3. Generate embeddings & upload to Pinecone
    4. Extract entities & relations using spaCy
    5. Load entities & relations into Neo4j
    6. Index chunks into BM25
    """
    if not document_id:
        document_id = os.path.basename(file_path)

    logger.info(f"Starting document ingestion pipeline for: {document_id}")
    
    # 1. Parsing
    logger.info("Step 1: Parsing document using LlamaParse...")
    text_content = parse_file(file_path)
    if not text_content:
        raise ValueError(f"No text extracted from file: {file_path}")
        
    # 2. Chunking
    logger.info("Step 2: Splitting text into chunks...")
    chunks = chunk_text(text_content)
    
    # 3. Vector Database Indexing (Pinecone)
    logger.info("Step 3: Indexing chunks in Pinecone...")
    metadata_base = {"filename": os.path.basename(file_path)}
    index_chunks(document_id, chunks, metadata_base)
    
    # 4. Entity Extraction
    logger.info("Step 4: Extracting entities & relationships...")
    kg_elements = extract_knowledge_graph_elements(text_content)
    entities = kg_elements.get("entities", [])
    relations = kg_elements.get("relations", [])
    
    # 5. Graph Database Ingestion (Neo4j)
    logger.info("Step 5: Loading entities and relations into Neo4j...")
    if entities or relations:
        upsert_entities_and_relations(entities, relations)
    else:
        logger.warning("No entities or relations found to load into Neo4j.")
        
    # 6. Keyword Index Ingestion (BM25)
    logger.info("Step 6: Adding chunks to BM25 index...")
    add_to_bm25_index(document_id, chunks, metadata_base)
    
    logger.info(f"Ingestion pipeline completed successfully for document: {document_id}")
    
    return {
        "document_id": document_id,
        "chunks_count": len(chunks),
        "entities_count": len(entities),
        "relations_count": len(relations)
    }
