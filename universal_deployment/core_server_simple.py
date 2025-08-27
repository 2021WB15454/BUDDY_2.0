import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import chromadb

app = FastAPI(title="BUDDY Universal Core")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database (Postgres)
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, future=True)

# Vector DB (Chroma)
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = os.getenv("CHROMADB_PORT", "8000")
chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=int(CHROMADB_PORT))
collection = chroma_client.get_or_create_collection("buddy_memory")

@app.get("/")
async def root():
    return {"status": "BUDDY Core Running 🚀"}

@app.post("/chat")
async def chat_endpoint(message: dict):
    user_text = message.get("text", "")

    # Log message in Postgres
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO chat_logs (message) VALUES (:msg)"), {"msg": user_text})

    # Store embedding in Chroma
    collection.add(documents=[user_text], ids=[str(hash(user_text))])

    return {"response": f"BUDDY heard: {user_text}"}
