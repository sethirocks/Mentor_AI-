# FastAPI entrypoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.mongo import connect_to_mongo, close_mongo_connection
from app.api.v1.routes_health import router as health_router

app = FastAPI(title="Mentor_AI Backend", version="v1")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router, prefix="/api/v1")

# Connect to MongoDB once at startup (no async/await)
db = connect_to_mongo()

@app.on_event("shutdown")
def shutdown():
    close_mongo_connection()