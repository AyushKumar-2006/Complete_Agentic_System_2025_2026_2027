# How to Use & Installation Guide

## 1. Prerequisites & Environment Setup
This project requires **Python `>=3.12,<3.14`** due to Apache Airflow compatibility.

Ensure you have Poetry installed, then set up the environment and install all dependencies:
```bash
# Install all project dependencies
poetry install
```

---

## 2. Installed Packages
The project dependencies managed by Poetry are:

### Core AI & LLM
*   `langchain` - LLM application framework
*   `langchain-community` - Community integrations for LangChain
*   `langgraph` - Building stateful, multi-actor applications
*   `openai` - OpenAI API client (embeddings via `text-embedding-3-small`, completions)
*   `tavily-python` - Tavily search API client
*   `google-search-results` - SerpApi client

### Document Parsing & Indexing
*   `llama-parse` - LlamaParse cloud document parser (PDFs, images, DOCX)
*   `llama-cloud-services` - Supporting services for LlamaParse
*   `llama-index-core` - SentenceSplitter chunking and LlamaIndex base utilities
*   `rank-bm25` - BM25 keyword ranking algorithm for local keyword search
*   `spacy` - NLP library for Named Entity Recognition (NER) and dependency parsing

### Databases & Storage
*   `pinecone` - Pinecone vector database client (renamed from `pinecone-client`)
*   `neo4j` - Neo4j graph database client for knowledge graph storage

### Connectivity & MCP Tools
*   `arcadepy` - Arcade AI client for connecting to MCP tools (Gmail, Google Docs, etc.)

### Web & Visualization
*   `streamlit` - Web application builder for the UI
*   `pyvis` - Interactive network visualization (knowledge graph rendering)

### Infrastructure & Utilities
*   `python-dotenv` - Environment variable management
*   `pydantic` - Data validation and settings
*   `loguru` - Advanced logging library
*   `requests` - HTTP requests library
*   `structlog (<25.5.0)` - Logging library pinned for Airflow compatibility
*   `apache-airflow (==3.1.0)` - Workflow orchestration for background pipelines

---

## 3. How Apache Airflow was Installed
Because Poetry doesn't support the `--constraint` parameter and Airflow has strict dependency limits, we performed the following:

1.  **Python Version Limit**: Updated `requires-python` in `pyproject.toml` to `">=3.12,<3.14"` (Airflow 3.1.0 does not support Python `>=3.14` yet).
2.  **Install Command**: Ran:
    ```bash
    poetry add "apache-airflow==3.1.0"
    ```
3.  **`structlog` Version Pin**: Airflow 3.1.0 has an import error (`ImportError: cannot import name 'Styles' from 'structlog.dev'`) with `structlog >= 25.5.0`. We resolved this by pinning and downgrading `structlog`:
    ```bash
    poetry add "structlog<25.5.0"
    ```

You can verify the installation is working by running:
```bash
poetry run airflow version
```

---

## 4. How Pinecone was Fixed
The `pinecone-client` package was renamed to `pinecone` by Pinecone. We migrated:
```bash
poetry remove pinecone-client
poetry add pinecone
```

## 5. How Arcade was Installed
Arcade AI provides an MCP tool integration layer (Gmail, Google Docs, Sheets, etc.). Installed via:
```bash
poetry add arcadepy
```
Used in `src/tools/mcp.py` to interact with external user data sources through an authorized tool-calling interface.

---

## 6. Production Best Practices & Setup

We have set up the project folder structure matching production standards, implementing 4 key best practices:

### I. Thin DAGs (Separation of Concerns)
*   **Concept**: Airflow DAGs should only schedule and orchestrate. They should never write core business or data logic inside the DAG files.
*   **File**: [dags/document_ingestion_dag.py](file:///r:/python/ai_flow/dags/document_ingestion_dag.py)
*   **Action**: The DAG file imports the core function `ingest_document_pipeline` from our python package [src/pipelines/ingestion.py](file:///r:/python/ai_flow/src/pipelines/ingestion.py) and executes it inside a `PythonOperator`.

### II. Centralized Configuration Management
*   **Concept**: Use environment variables (`.env`) validated at boot time via Pydantic schemas instead of scattering `os.getenv` calls across the codebase.
*   **File**: [src/config.py](file:///r:/python/ai_flow/src/config.py)
*   **Action**: Pydantic's `BaseSettings` automatically parses and validates environment keys. You can import variables using `from src.config import settings`.

### III. Isolated Database Initialization Scripts
*   **Concept**: DDL schemas, constraints, and indexes for databases (Pinecone, Neo4j) should be executed in setup/deployment scripts, not during active request processing.
*   **File**: [scripts/init_databases.py](file:///r:/python/ai_flow/scripts/init_databases.py)
*   **Action**: Running `poetry run python scripts/init_databases.py` connects to Pinecone & Neo4j, checks if the required indices/constraints are set up, and constructs them if missing.

### IV. Mocking External API calls in Tests
*   **Concept**: Production test pipelines should run quickly, reliably, and without spending money or requiring active API credentials or internet connections.
*   **File**: [tests/test_agents.py](file:///r:/python/ai_flow/tests/test_agents.py)
*   **Action**: Demonstrates how to write tests with `unittest.mock.patch` to intercept requests made by agents to OpenAI or search engines. Run via:
    ```bash
    poetry run pytest
    ```

---

## 7. RAG Pipeline Utility Modules (`src/utils/`)

These 6 new utility modules power the document ingestion and retrieval pipeline.

### `parser.py` — Document Parsing
Parses uploaded files (PDF, DOCX, images) using **LlamaParse** and returns the extracted text as markdown.
- **Libraries**: `llama_parse`, `loguru`, `src.config`

### `vector_store.py` — Chunking + Semantic Search
Splits text into chunks using **SentenceSplitter**, generates embeddings via **OpenAI `text-embedding-3-small`**, and stores/queries them in **Pinecone**.
- **Libraries**: `openai`, `pinecone`, `llama_index.core.node_parser.SentenceSplitter`, `loguru`

### `graph_store.py` — Knowledge Graph Storage & Lookup
Saves entities and relationships to **Neo4j**, retrieves direct entity neighbors for context enrichment, and computes **shortest path** between any two entities.
- **Libraries**: `neo4j`, `loguru`, `src.config`

### `keyword_search.py` — BM25 Keyword Search
Maintains a persistent, disk-backed **BM25 keyword index** over all ingested document chunks for fast lexical retrieval.
- **Libraries**: `rank_bm25`, `pickle`, `loguru`

### `hybrid_search.py` — Multi-Route Context Retrieval
Combines results from **Pinecone vector search**, **BM25 keyword search**, and **Neo4j entity graph neighbors** into a single deduplicated context bundle ready for the LLM.
- **Libraries**: `src.utils.vector_store`, `src.utils.keyword_search`, `src.utils.entity_extractor`, `src.utils.graph_store`

### `entity_extractor.py` — NLP Entity & Relation Extraction
Extracts named entities (people, orgs, locations) and Subject-Verb-Object triplets from raw text using **spaCy**, used to populate the knowledge graph.
- **Libraries**: `spacy (en_core_web_sm)`

---

## 8. Background Ingestion Pipeline (`src/pipelines/ingestion.py`)

The `ingest_document_pipeline(file_path, document_id)` function is the **slow-path** background worker triggered after every file upload:

```
Upload File
    │
    └──► ingest_document_pipeline()
              1. LlamaParse    → raw text
              2. SentenceSplitter → chunks
              3. OpenAI embed  → Pinecone index
              4. spaCy NER     → entities + relations
              5. Neo4j merge   → knowledge graph
              6. BM25 index    → keyword search
```

---

## 9. Production Directory Structure

```text
ai_flow/
├── .github/workflows/test.yml      # Automated CI testing on push/PR
├── data/
│   └── bm25_index.pkl              # Persistent BM25 keyword search index
├── dags/                           # Thin Airflow orchestrator DAGs
│   └── document_ingestion_dag.py   # Background ingestion DAG
├── src/                            # Main code package
│   ├── config.py                   # Settings loader (Pydantic BaseSettings)
│   ├── agents/                     # LLM/LangGraph agents
│   ├── tools/                      # MCP / DB / API agent tools
│   │   ├── mcp.py                  # Arcade MCP tool integrations
│   │   └── search.py               # Web search tools
│   ├── pipelines/
│   │   └── ingestion.py            # Full slow-path ingestion pipeline
│   └── utils/
│       ├── entity_extractor.py     # spaCy NER + SVO relation extraction
│       ├── parser.py               # LlamaParse document parser
│       ├── vector_store.py         # Pinecone + OpenAI embedding store
│       ├── graph_store.py          # Neo4j entity graph store
│       ├── keyword_search.py       # BM25 keyword search index
│       └── hybrid_search.py        # Combined retrieval orchestrator
├── ui/                             # Streamlit Frontend
│   ├── app.py                      # Main App entry point
│   ├── components/                 # Modular UI widgets
│   └── pages/                      # Subpages
├── scripts/
│   └── init_databases.py           # Pinecone & Neo4j setup script
└── tests/
    ├── test_agents.py              # Mock-based agent tests
    └── test_rag_utilities.py       # RAG utility unit tests
```
