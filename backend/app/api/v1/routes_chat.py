from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.mongo import db
from app.core.config import settings
from openai import OpenAI
import re
from typing import Optional, List

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize the OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


# Request & Response Models
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    model_used: str
    used_fallback: bool  # Indicates if fallback logic was triggered
    sources_used: Optional[List[str]] = None  # include URLs/titles of used sources

    class Config:
        protected_namespaces = ()


# Chat Route
@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Chat endpoint that uses GPT + scraped MongoDB context to answer user queries."""
    question = request.message.strip()

    # Step 1: Retrieve relevant scraped pages using filtered keyword regex
    scraped_pages_collection = db.scraped_pages

    # Clean the question: remove punctuation before splitting
    cleaned_question = re.sub(r'[^\w\s]', ' ', question.lower())

    # Remove common stop words and filter meaningful keywords
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'is', 'are', 'was', 'were',
                  'with', 'from', 'by', 'about', 'tell', 'me', 'what'}
    keywords = [word for word in cleaned_question.split() if word.strip() and word not in stop_words and len(word) > 2]

    # DEBUG: Print to see what's happening
    print(f"Question: {question}")
    print(f"Keywords extracted: {keywords}")

    # Only proceed with query if we have meaningful keywords
    if not keywords:
        matched_pages = []
    else:
        # Build a flat $or query that searches across ALL relevant fields
        regex_filters = []
        for word in keywords:
            # Search in multiple fields for better coverage
            regex_filters.append({"title": {"$regex": re.escape(word), "$options": "i"}})
            regex_filters.append({"content": {"$regex": re.escape(word), "$options": "i"}})
            regex_filters.append({"url": {"$regex": re.escape(word), "$options": "i"}})
            regex_filters.append({"headings": {"$regex": re.escape(word), "$options": "i"}})
            regex_filters.append({"tags": {"$regex": re.escape(word), "$options": "i"}})
            # For paragraphs array, use $elemMatch
            regex_filters.append({"paragraphs": {"$elemMatch": {"$regex": re.escape(word), "$options": "i"}}})

        # Single $or query - matches if ANY keyword appears in ANY field
        query = {"$or": regex_filters}
        print(f"MongoDB Query: {query}")

        matched_pages = list(scraped_pages_collection.find(query).limit(2))
        print(f"Matched pages count: {len(matched_pages)}")

        # DEBUG: Check what's in the database
        if len(matched_pages) == 0:
            # Try a broader search to see if ANY documents exist
            total_docs = scraped_pages_collection.count_documents({})
            print(f"Total documents in scraped_pages collection: {total_docs}")

            # Sample one document to see structure
            sample_doc = scraped_pages_collection.find_one()
            if sample_doc:
                print(f"Sample document fields: {list(sample_doc.keys())}")
                print(f"Sample title: {sample_doc.get('title', 'N/A')[:100]}")
                print(f"Sample content preview: {sample_doc.get('content', 'N/A')[:100]}")

    # FIXED: Fallback is True when no pages matched
    used_fallback = len(matched_pages) == 0

    # Step 2: Build context text (if any matched)
    context_blocks = []
    sources_used = []

    for page in matched_pages:
        title = page.get("title", "")
        content = page.get("content", "")
        paragraphs = page.get("paragraphs", "")
        url = page.get("url", "")

        # Combine content and paragraphs for better context
        full_content = f"{content}\n{paragraphs}" if paragraphs else content
        block = f"Title: {title}\nContent: {full_content[:1000]}"
        context_blocks.append(block)
        sources_used.append(url or title)

    context = "\n\n".join(context_blocks)

    # Step 3: Construct prompt
    if context:
        prompt = (
            "You are a helpful assistant that answers student questions using official university information.\n\n"
            "Use the following documents to answer the question. Be concise and accurate. If unsure, say so.\n\n"
            f"{context}\n\n"
            f"Question: {question}"
        )
    else:
        prompt = question  # fallback: GPT gets no context

    # Step 4: Send prompt to GPT model
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for university information."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        answer = response.choices[0].message.content.strip()
        model_used = response.model

        # Step 5: Return grounded response
        # FIXED: When fallback is True, sources_used should be None or empty list
        return ChatResponse(
            answer=answer,
            model_used=model_used,
            used_fallback=used_fallback,
            sources_used=sources_used if not used_fallback and sources_used else None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))