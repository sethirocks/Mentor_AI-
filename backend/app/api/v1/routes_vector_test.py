# app/api/v1/routes_vector_test.py

from fastapi import APIRouter
from app.core.vector_store import chroma_client

router = APIRouter(prefix="/vector-test", tags=["vector-test"])

@router.get("/heartbeat")
def vector_heartbeat():
    """Check if ChromaDB is alive."""
    return {"chroma_heartbeat": chroma_client.heartbeat()}


@router.get("/summary")
def vector_store_summary():
    """Show number of documents and preview a few sample vectors."""
    try:
        collection = chroma_client.get_collection("hda_documents")
        total_count = collection.count()
        sample = collection.peek(limit=5)

        docs = []
        for i, (doc_id, metadata, content) in enumerate(zip(
            sample["ids"], sample["metadatas"], sample["documents"]
        )):
            doc_info = {
                "id": doc_id,
                "type": metadata.get("type"),
                "preview": content[:100],
            }

            # Add extra details for clarity
            if metadata.get("type") == "page":
                doc_info.update({
                    "title": metadata.get("title"),
                    "url": metadata.get("url"),
                    "chunk_index": metadata.get("chunk_index"),
                })
            elif metadata.get("type") == "insight":
                doc_info.update({
                    "topic": metadata.get("topic"),
                    "source": metadata.get("source"),
                })

            docs.append(doc_info)

        return {
            "total_documents": total_count,
            "sample_documents": docs
        }

    except Exception as e:
        return {"error": str(e)}