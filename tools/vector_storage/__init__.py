"""
Initializes the ChromaDB client and collection, and provides shared utilities
for vector storage modules (requirements, acceptance criteria, test cases).
"""
import os
import re
import chromadb
from chromadb.utils import embedding_functions

# --- Configuration ---
# Use environment variables or defaults
PERSIST_DIRECTORY = os.getenv("VECTOR_DB_PATH", "./tools/chroma_db") # Default path inside tools folder
COLLECTION_NAME = os.getenv("VECTOR_DB_COLLECTION", "cerebra_requirements")
# Using default embedding function (requires sentence-transformers)
# For production, consider specifying a model explicitly or using a different provider.
# ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
# Or use OpenAI, Cohere, etc. if configured:
# ef = embedding_functions.OpenAIEmbeddingFunction(api_key="...", model_name="...")
# Using default for simplicity now:
ef = embedding_functions.DefaultEmbeddingFunction() # Requires sentence-transformers

# Ensure the persistence directory exists
os.makedirs(PERSIST_DIRECTORY, exist_ok=True)

# --- ChromaDB Client and Collection ---
# Initialize client (persistent)
client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)

# Get or create the collection
# Using allow_reset=True for development ease, might remove for production
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=ef,
    # metadata={"hnsw:space": "cosine"} # Optional: Specify distance metric if needed
)

# --- Helper Function for ID Generation ---
def _get_next_id(prefix: str) -> str:
    """
    Determines the next available ID for a given prefix (e.g., "REQ-").
    Retrieves all IDs, finds the highest number associated with the prefix,
    and returns the prefix + (highest_number + 1).
    """
    max_num = 0
    try:
        # Get all IDs from the collection
        all_ids = collection.get()['ids']

        # Filter IDs matching the prefix and extract numbers
        pattern = re.compile(f"^{re.escape(prefix)}(\\d+)$")
        for item_id in all_ids:
            match = pattern.match(item_id)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
    except Exception as e:
        # Log error or handle case where collection might be empty/unavailable
        print(f"Warning: Could not accurately determine max ID for prefix '{prefix}': {e}. Starting from 1.")
        max_num = 0 # Reset to 0 ensure next ID is prefix + 1

    next_num = max_num + 1
    return f"{prefix}{next_num}"

__all__ = ['client', 'collection', '_get_next_id']
