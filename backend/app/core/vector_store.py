# app/core/vector_store.py

import chromadb
import os

# Get absolute path to backend/vector_db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # app/core/
VECTOR_DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../vector_db"))

# Ensure directory exists
os.makedirs(VECTOR_DB_PATH, exist_ok=True)

print(f"🧠 ChromaDB path: {VECTOR_DB_PATH}")

# Initialize persistent client
chroma_client = chromadb.PersistentClient(path=VECTOR_DB_PATH)

