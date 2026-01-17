from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import base64
from rag_chain import text_splitter, vector_store
from rag_chain import rag_chain

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

@app.post('/upload_file',tags=["VectorDB"])
def upload_file(request:FileRequest):
    file_str = ''
    try:
        decoded_bytes = base64.b64decode(request.file_data)
        file_str = decoded_bytes.decode("utf-8")
    except Exception as e:
        print(f"Base64 Decode Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Decode error: {str(e)}"
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

@app.post('/rag',tags=["RAG"])
def rag_chain_invoke(request:RAGRequest):
    query = request.query
    if not query:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Error in request: Empty or None String Value in Query..."
        )
    
    response = rag_chain.invoke(query)

    return{
        'status' : status.HTTP_200_OK,
        'response' : response
    }

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
            
            for token in rag_chain.stream(query):
                await websocket.send_text(token.content)
                resp += token.content
            
            await websocket.send_text('<<END>>')
    except WebSocketDisconnect:
        print("Websocket Disconnected")
    except Exception as e:
        print(f"Error during execution, {e}")