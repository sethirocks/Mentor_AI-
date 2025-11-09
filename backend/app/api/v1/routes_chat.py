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
    """Chat endpoint that uses GPT + scraped MongoDB context + insights to answer user queries."""
    question = request.message.strip()

    # Clean the question: remove punctuation before splitting
    cleaned_question = re.sub(r'[^\w\s]', ' ', question.lower())

    # Remove common stop words and filter meaningful keywords
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'is', 'are', 'was', 'were',
                  'with', 'from', 'by', 'about', 'tell', 'me', 'what'}
    keywords = [word for word in cleaned_question.split() if word.strip() and word not in stop_words and len(word) > 2]

    # DEBUG: Print to see what's happening
    print(f"Question: {question}")
    print(f"Keywords extracted: {keywords}")

    # Step 1: Retrieve relevant scraped pages and insights using filtered keyword regex
    scraped_pages_collection = db.scraped_pages
    insights_collection = db.insights

    matched_pages = []
    matched_insights = []

    # Only proceed with query if we have meaningful keywords
    if keywords and len(keywords) > 0:
        # Build a flat $or query that searches across ALL relevant fields for scraped pages
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
        print(f"MongoDB Query for scraped_pages: {query}")

        matched_pages = list(scraped_pages_collection.find(query).limit(2))
        print(f"Matched pages count: {len(matched_pages)}")

        # Step 2: Query insights collection with same keywords
        insights_regex_filters = []
        for word in keywords:
            insights_regex_filters.append({"topic": {"$regex": re.escape(word), "$options": "i"}})
            insights_regex_filters.append({"content": {"$regex": re.escape(word), "$options": "i"}})
            insights_regex_filters.append({"tags": {"$regex": re.escape(word), "$options": "i"}})

        insights_query = {"$or": insights_regex_filters}
        print(f"MongoDB Query for insights: {insights_query}")

        matched_insights = list(insights_collection.find(insights_query).limit(3))
        print(f"Matched insights count: {len(matched_insights)}")

        # DEBUG: Check what's in the database if no matches
        if len(matched_pages) == 0 and len(matched_insights) == 0:
            # Try a broader search to see if ANY documents exist
            total_docs = scraped_pages_collection.count_documents({})
            total_insights = insights_collection.count_documents({})
            print(f"Total documents in scraped_pages collection: {total_docs}")
            print(f"Total documents in insights collection: {total_insights}")

            # Sample one document to see structure
            sample_doc = scraped_pages_collection.find_one()
            if sample_doc:
                print(f"Sample document fields: {list(sample_doc.keys())}")
                print(f"Sample title: {sample_doc.get('title', 'N/A')[:100]}")
                print(f"Sample content preview: {sample_doc.get('content', 'N/A')[:100]}")
                print(f"Paragraphs type: {type(sample_doc.get('paragraphs'))}")
                if isinstance(sample_doc.get('paragraphs'), list):
                    print(
                        f"First paragraph: {sample_doc.get('paragraphs')[0] if sample_doc.get('paragraphs') else 'Empty list'}")
                print(f"Headings: {sample_doc.get('headings', 'N/A')}")

    # Determine if fallback is needed (no matches in either collection)
    used_fallback = len(matched_pages) == 0 and len(matched_insights) == 0

    # Step 3: Build context text from scraped pages
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

    # Step 4: Add insights to context
    for insight in matched_insights:
        topic = insight.get("topic", "")
        content = insight.get("content", "")
        source = insight.get("source", "insight")

        block = f"Insight on '{topic}':\n{content}"
        context_blocks.append(block)
        sources_used.append(f"Insight: {topic}" if not source else source)

    context = "\n\n---\n\n".join(context_blocks)

    # Step 5: Construct prompt
    if context:
        prompt = (
            "You are a helpful assistant that answers questions about Hochschule Darmstadt (h_da) using official university information and insights.\n\n"
            "Use the following documents and insights from h-da.de to answer the question. Be concise and accurate. "
            "If the answer is not in the documents or insights, say so.\n\n"
            f"{context}\n\n"
            f"Question: {question}"
        )
    else:
        # When no context available, instruct GPT to decline politely
        prompt = (
            "You are a helpful assistant for Hochschule Darmstadt (h_da) university.\n\n"
            "The user asked a question, but no relevant information was found in the h-da.de database.\n\n"
            "Politely inform the user: 'I'm sorry, but I don't have information about [their topic] in the h_da database. "
            "I can only answer questions about Hochschule Darmstadt based on information from h-da.de, such as study programs, "
            "admissions, orientation semesters, campus life, and university services. Feel free to ask about the university!'\n\n"
            f"User's question: {question}\n\n"
            "Respond politely following the format above."
        )

    # Step 6: Send prompt to GPT model
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

        # Step 7: Return grounded response
        # When fallback is True, sources_used should be None or empty list
        return ChatResponse(
            answer=answer,
            model_used=model_used,
            used_fallback=used_fallback,
            sources_used=sources_used if not used_fallback and sources_used else None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))