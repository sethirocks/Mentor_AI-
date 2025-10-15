from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "mentor_ai")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

def connect_to_mongo():
    return db

def close_mongo_connection():
    client.close()