from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os

router = APIRouter(prefix="/chat", tags=["chat"])

# Load OpenAI API key and model name from environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str
    model_used: str

    class Config:
        protected_namespaces = ()

@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Basic GPT-powered chat endpoint.
    Takes a user message and returns a GPT-generated answer.
    """
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for students at Hochschule Darmstadt."},
                {"role": "user", "content": request.message}
            ],
            temperature=0.7,
            max_tokens=300
        )

        answer = completion.choices[0].message.content
        return {"answer": answer, "model_used": MODEL}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat request failed: {str(e)}")