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
    used_fallback: bool # Indicates if fallback logic was triggered
    sources_used: Optional[List[str]] = None  # include URLs/titles of used sources

    class Config:
        protected_namespaces = ()

# Chat Route
@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Chat endpoint that uses GPT + scraped MongoDB context to answer user queries."""
    question = request.message.strip()

    # Step 1: Retrieve relevant scraped pages
    scraped_pages_collection = db.scraped_pages
    keywords = question.lower().split()
    regex_filters = [
        {"content": {"$regex": re.escape(word), "$options": "i"}}
        for word in keywords if word.strip()
    ]
    query = {"$or": regex_filters} if regex_filters else {}
    matched_pages = list(scraped_pages_collection.find(query).limit(2))

    used_fallback = len(matched_pages) == 0  # True if no documents matched

    # Step 2: Build context text (if any matched)
    context_blocks = []
    sources_used = []

    for page in matched_pages:
        title = page.get("title", "")
        content = page.get("content", "")
        url = page.get("url", "")
        block = f"Title: {title}\nContent: {content[:1000]}"
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
        return ChatResponse(
            answer=answer,
            model_used=model_used,
            used_fallback=used_fallback,
            sources_used=sources_used if not used_fallback and sources_used else None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))