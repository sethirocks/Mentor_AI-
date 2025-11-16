# FastAPI entrypoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.mongo import connect_to_mongo, close_mongo_connection
from app.api.v1.routes_health import router as health_router
from app.api.v1.routes_chat import router as chat_router
from app.api.v1.routes_scrape import router as scrape_router
from app.api.v1.routes_insights import router as insights_router
from app.api.v1.routes_vector_test import router as vector_test_router  #  Add this line

import logging

# Configure global logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)
logger.info("Starting Mentor_AI Backend")

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
app.include_router(chat_router, prefix="/api/v1")
app.include_router(scrape_router, prefix="/api/v1")
app.include_router(insights_router, prefix="/api/v1")
app.include_router(vector_test_router, prefix="/api/v1")  #  Register vector test route

# Connect to MongoDB
db = connect_to_mongo()

@app.on_event("shutdown")
def shutdown():
    close_mongo_connection()
