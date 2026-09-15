"""Rebuild the local ChromaDB recipe collection."""
from app.rag.service import rebuild

if __name__ == "__main__":
    count = rebuild()
    print(f"Indexed {count} recipes into ChromaDB")
