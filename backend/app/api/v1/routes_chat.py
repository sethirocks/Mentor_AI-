from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.mongo import db
from app.core.config import settings
from openai import OpenAI
import os

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize the new OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str
    model_used: str

    class Config:
        protected_namespaces = ()

@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    question = request.message.strip()

    # Step 1: Retrieve relevant scraped pages
    scraped_pages_collection = db.scraped_pages
    keywords = question.lower().split()
    regex_filters = [{"content": {"$regex": word, "$options": "i"}} for word in keywords]
    query = {"$or": regex_filters}
    matched_pages = list(scraped_pages_collection.find(query).limit(2))

    # Step 2: Build context text
    context_blocks = []
    for page in matched_pages:
        title = page.get("title", "")
        content = page.get("content", "")
        block = f"Title: {title}\nContent: {content[:1000]}"
        context_blocks.append(block)

    context = "\n\n".join(context_blocks)

    # Step 3: Construct prompt
    if context:
        prompt = f"Answer the following question using the provided university documents.\n\n{context}\n\nQuestion: {question}"
    else:
        prompt = question

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

        return ChatResponse(answer=answer, model_used=model_used)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))