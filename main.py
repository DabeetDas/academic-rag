from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import base64
from rag_chain import text_splitter, vector_store
from rag_chain import rag_chain
import io
from pypdf import PdfReader
import os
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

# Initialize MongoDB
MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["rag_db"]
interactions = db["interactions"]

app = FastAPI()

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dummy admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

@app.get('/', tags=["General"])
def root():
    return RedirectResponse('/docs')

# Auth Models and Endpoint
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post('/auth/login', tags=["Auth"])
def login(request: LoginRequest):
    if request.username == ADMIN_USERNAME and request.password == ADMIN_PASSWORD:
        return {
            'status': status.HTTP_200_OK,
            'message': 'Login successful',
            'isAdmin': True
        }
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

class FileRequest(BaseModel):
    file_data:str
    filename:str

@app.post('/upload_file',tags=["VectorDB"])
def upload_file(request:FileRequest):
    file_str = ''
    try:
        decoded_bytes = base64.b64decode(request.file_data)
        
        if request.filename.lower().endswith('.pdf'):
            pdf_file = io.BytesIO(decoded_bytes)
            reader = PdfReader(pdf_file)
            
            # Extract text from all pages
            text_content = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
            
            file_str = "\n".join(text_content)
        else:
            # Default to text file handling
            file_str = decoded_bytes.decode("utf-8")
            
    except Exception as e:
        print(f"File Processing Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File processing error: {str(e)}"
        )
    
    if not file_str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid file data: File is empty or null...")
    
    try:
        print(f"Adding {len(file_str)} characters to vector store...")
        texts = text_splitter.create_documents([file_str])
        ids = vector_store.add_documents(texts)
        print(f"Successfully added documents with ids: {ids}")
    except Exception as e:
        print(f"Error adding to vector store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector store error: {str(e)}"
        )

    return{
        'status' : status.HTTP_201_CREATED,
        'uploaded_ids' : ids
    }

class SearchRequest(BaseModel):
    search_str : str
    n: int = 2

@app.post('/vector_search',tags=["VectorDB"])
def similarity_search(request:SearchRequest):
    try:
        results = vector_store.similarity_search(
            request.search_str,
            k = request.n
        )

        return{
            'status' : status.HTTP_200_OK,
            'results' : results
        }
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = f"{e}"
        )
    
class RAGRequest(BaseModel):
    query: str
    history: list = []

@app.post('/rag',tags=["RAG"])
def rag_chain_invoke(request:RAGRequest):
    query = request.query
    if not query:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Error in request: Empty or None String Value in Query..."
        )
    
    response = rag_chain.invoke(query, request.history)
    
    # Store interaction
    interaction = {
        "query": query,
        "response": response.content,
        "history": request.history,
        "timestamp": datetime.utcnow(),
        "feedback": None
    }
    inserted_id = interactions.insert_one(interaction).inserted_id

    return{
        'status' : status.HTTP_200_OK,
        'response' : response,
        'interactionId': str(inserted_id)
    }

class FeedbackRequest(BaseModel):
    interactionId: str
    feedback: str  # "up", "down", or maybe text

@app.post('/feedback', tags=["Feedback"])
def submit_feedback(request: FeedbackRequest):
    try:
        interactions.update_one(
            {"_id": ObjectId(request.interactionId)},
            {"$set": {"feedback": request.feedback}}
        )
        return {"status": "success", "message": "Feedback received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/stream")
async def chat_stream(websocket:WebSocket):
    await websocket.accept()
    try:
        resp = ''
        while True:
            data = await websocket.receive_json()
            if 'query' not in data:
                await websocket.send_text('<<E:NO_QUERY>>')
                break
            query = data['query']
            history = data.get('history', [])
            
            for token in rag_chain.stream(query, history):
                await websocket.send_text(token.content)
                resp += token.content
            
            # Store interaction
            try:
                interaction = {
                    "query": query,
                    "response": resp,
                    "timestamp": datetime.utcnow(),
                    "feedback": None
                }
                inserted_id = interactions.insert_one(interaction).inserted_id
                
                # Send ID to client
                await websocket.send_text(f'<<ID:{str(inserted_id)}>>')
            except Exception as e:
                print(f"Error logging to Mongo: {e}")

            await websocket.send_text('<<END>>')
            resp = '' # Reset buffer
    except WebSocketDisconnect:
        print("Websocket Disconnected")
    except Exception as e:
        print(f"Error during execution, {e}")