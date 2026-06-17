import os
from llama_parse import LlamaParse
from loguru import logger
from src.config import settings

def parse_file(file_path: str) -> str:
    """
    Parses a file (PDF, image, docx, etc.) using LlamaParse and returns the extracted markdown text.
    """
    logger.info(f"Parsing file using LlamaParse: {file_path}")
    if not settings.llama_cloud_api_key:
        raise ValueError("LLAMA_CLOUD_API_KEY is not configured in environment variables.")

    # Initialize LlamaParse
    parser = LlamaParse(
        api_key=settings.llama_cloud_api_key,
        result_type="markdown",
        verbose=True
    )
    
    # Load documents from file path
    documents = parser.load_data(file_path)
    
    # Join text from all extracted pages/documents
    full_text = "\n\n".join([doc.text for doc in documents])
    logger.info(f"Successfully parsed {len(documents)} pages/chunks from {file_path}")
    return full_text
