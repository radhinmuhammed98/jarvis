import os
import uuid
import logging
from pathlib import Path

# Provide a fallback if chromadb isn't available
try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "chroma_db"

_client = None
_collection = None
_embed_model = None

def init_semantic_memory():
    """Initializes the ChromaDB client and collection."""
    global _client, _collection, _embed_model

    if not HAS_CHROMA:
        logger.warning("ChromaDB not installed. Semantic memory disabled.")
        return

    try:
        # Load a small, fast sentence transformer locally
        _embed_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Initialize ChromaDB client
        _client = chromadb.PersistentClient(path=str(DB_PATH))

        # Create or get the main long-term memory collection
        _collection = _client.get_or_create_collection(
            name="jarvis_long_term_memory",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Semantic memory (ChromaDB) initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize semantic memory: {e}")
        _client = None

def add_memory(text: str, category: str = "general", metadata: dict = None):
    """Embeds and saves a piece of text to long-term memory."""
    if not _collection or not _embed_model:
        return False

    try:
        embedding = _embed_model.encode(text).tolist()

        if metadata is None:
            metadata = {}
        metadata["category"] = category

        mem_id = str(uuid.uuid4())

        _collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[mem_id]
        )
        return True
    except Exception as e:
        logger.error(f"Failed to add to semantic memory: {e}")
        return False

def query_memory(query: str, n_results: int = 3, category_filter: str = None) -> list[str]:
    """Retrieves the most semantically relevant memories."""
    if not _collection or not _embed_model:
        return []

    try:
        query_embedding = _embed_model.encode(query).tolist()

        where_clause = None
        if category_filter:
            where_clause = {"category": category_filter}

        results = _collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause
        )

        if results and "documents" in results and results["documents"]:
            return results["documents"][0]
        return []

    except Exception as e:
        logger.error(f"Failed to query semantic memory: {e}")
        return []
