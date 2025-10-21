"""MongoDB connection utilities."""

import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "mentor_ai")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]


def connect_to_mongo():
    """Return an active connection to the configured Mongo database."""

    return db


def close_mongo_connection():
    """Gracefully close the MongoDB client connection."""

    client.close()
