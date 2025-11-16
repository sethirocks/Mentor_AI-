from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from app.core.vector_store import chroma_client
from openai import OpenAI
from typing import Optional, List
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize the OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Embedding model configuration
EMBEDDING_MODEL = getattr(settings, 'OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')

# Get ChromaDB collection
try:
    chroma_collection = chroma_client.get_or_create_collection(
        name="hda_documents",
        metadata={"description": "H_DA scraped pages and insights with embeddings"}
    )
    logger.info("ChromaDB collection initialized successfully")
except Exception as e:
    logger.error(f"Could not initialize ChromaDB collection: {e}")
    chroma_collection = None


# Request & Response Models
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    model_used: str
    used_fallback: bool
    sources_used: Optional[List[str]] = None

    class Config:
        protected_namespaces = ()


def get_embedding(text: str) -> list:
    """Generate embedding for query using OpenAI"""
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None


# Chat Route
@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Chat endpoint using vector similarity search + GPT for semantic RAG"""
    question = request.message.strip()

    logger.info(f"Received chat request: {question[:100]}...")

    # Check if ChromaDB is available
    if not chroma_collection:
        logger.error("Vector store not available")
        raise HTTPException(
            status_code=500,
            detail="Vector store not available. Please run indexing script first."
        )

    # Step 1: Generate embedding for the query
    logger.debug("Generating query embedding...")
    query_embedding = get_embedding(question)

    if not query_embedding:
        logger.error("Failed to generate query embedding")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate query embedding"
        )

    # Step 2: Search ChromaDB for semantically similar documents
    try:
        logger.info("Searching vector database...")
        results = chroma_collection.query(
            query_embeddings=[query_embedding],
            n_results=5,  # Get top 5 most relevant chunks
            include=["documents", "metadatas", "distances"]
        )

        logger.info("Vector Search Results:")
        logger.info(f"   Found {len(results['ids'][0])} results")

        # Debug: Show relevance scores
        for i, (doc_id, distance) in enumerate(zip(results['ids'][0], results['distances'][0])):
            metadata = results['metadatas'][0][i]
            doc_type = metadata.get('type', 'unknown')
            title_or_topic = metadata.get('title') or metadata.get('topic', 'N/A')
            logger.info(f"   {i+1}. Distance: {distance:.4f} | Type: {doc_type} | {title_or_topic}")

    except Exception as e:
        logger.error(f"Error querying ChromaDB: {e}")
        results = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    # Step 3: Build context from results with relevance filtering
    official_docs = []
    insights_context = []
    sources_used = []

    # Track unique URLs to avoid duplicates
    seen_urls = set()

    # Filter results by relevance threshold
    # Distance < 1.0 is very relevant, < 1.5 is relevant, > 1.5 is questionable
    RELEVANCE_THRESHOLD = 1.2

    relevant_count = 0
    for i, distance in enumerate(results['distances'][0]):
        if distance > RELEVANCE_THRESHOLD:
            logger.debug(f"Skipping result {i+1}: distance={distance:.4f} exceeds threshold")
            continue

        relevant_count += 1
        metadata = results['metadatas'][0][i]
        document = results['documents'][0][i]
        doc_type = metadata.get('type', 'unknown')

        if doc_type == 'page':
            title = metadata.get('title', 'Untitled')
            url = metadata.get('url', '')
            chunk_idx = metadata.get('chunk_index', 0)
            total_chunks = metadata.get('total_chunks', 1)

            block = f"Title: {title}\nChunk {chunk_idx+1}/{total_chunks}\nContent: {document}"
            official_docs.append(block)

            # Add source only once per URL
            if url and url not in seen_urls:
                sources_used.append(url)
                seen_urls.add(url)
            elif not url and title not in sources_used:
                sources_used.append(title)

        elif doc_type == 'insight':
            topic = metadata.get('topic', 'Unknown')
            source = metadata.get('source', 'insight')

            block = f"Topic: {topic}\n{document}"
            insights_context.append(block)

            source_label = f"Insight: {topic}" if not source or source == "insight" else source
            if source_label not in sources_used:
                sources_used.append(source_label)

    logger.debug(f"Relevance Summary: {relevant_count} relevant results, fallback={len(official_docs) == 0 and len(insights_context) == 0}")

    # Combine context with section headers
    context_parts = []
    if official_docs:
        context_parts.append("=== OFFICIAL UNIVERSITY DOCUMENTS ===\n\n" + "\n\n---\n\n".join(official_docs))
    if insights_context:
        context_parts.append("=== CRITICAL INSIDER INSIGHTS ===\n\n" + "\n\n---\n\n".join(insights_context))

    context = "\n\n\n".join(context_parts)
    used_fallback = len(official_docs) == 0 and len(insights_context) == 0

    logger.debug(f"Fallback mode: {used_fallback}")

    # Step 4: Construct prompt
    if context:
        prompt = (
            "You are a helpful assistant that answers questions about Hochschule Darmstadt (h_da).\n\n"
            "You have access to TWO types of information:\n"
            "1. Official university documents from h-da.de (marked as OFFICIAL UNIVERSITY DOCUMENTS)\n"
            "2. Critical insider insights from students, advisors, and staff (marked as CRITICAL INSIDER INSIGHTS)\n\n"
            "Use BOTH official university documents and critical insider insights to provide comprehensive, accurate answers. "
            "When insights provide additional context or practical advice beyond official information, include it. "
            "Be concise and accurate. If the answer is not in the provided information, say so.\n\n"
            f"{context}\n\n"
            f"Question: {question}"
        )
    else:
        # Fallback when no relevant context found
        prompt = (
            "You are a helpful assistant for Hochschule Darmstadt (h_da) university.\n\n"
            "The user asked a question, but no relevant information was found in the h-da.de database.\n\n"
            "Politely inform the user: 'I'm sorry, but I don't have information about [their topic] in the h_da database. "
            "I can only answer questions about Hochschule Darmstadt based on information from h-da.de, such as study programs, "
            "admissions, orientation semesters, campus life, and university services. Feel free to ask about the university!'\n\n"
            f"User's question: {question}\n\n"
            "Respond politely following the format above."
        )

    # Step 5: Send to GPT
    try:
        logger.info(f"Generating response with {settings.OPENAI_MODEL}...")
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for university information."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        answer = response.choices[0].message.content.strip()
        model_used = f"{settings.OPENAI_MODEL} + {EMBEDDING_MODEL}"

        logger.info(f"Response generated successfully (fallback={used_fallback})")

        return ChatResponse(
            answer=answer,
            model_used=model_used,
            used_fallback=used_fallback,
            sources_used=sources_used if not used_fallback and sources_used else None
        )

    except Exception as e:
        logger.error(f"Error calling OpenAI: {e}")
        raise HTTPException(status_code=500, detail=str(e))