# Drive-RAG
A full-stack Retrieval-Augmented Generation (RAG) application with a FastAPI backend and a Vite+React frontend.

## Project Structure
```bash
.
├── main.py              # Backend API routes
├── rag_chain.py         # RAG chain implementation
├── requirements.txt     # Python dependencies
├── drive-rag/           # Frontend application
│   ├── package.json
│   └── ...
└── .env                 # Environment variables (not committed)
```

## Backend Overview
1. ```main.py```
    1.1 Contains **all API routes** exposed by the FastAPI backend.
    1.2 Responsible for request handling, orchestration, and streaming responses.

2. ```rag_chain.py```
    2.1 Contains the **RAG chain** implementation.
    2.2 Handles retrieval, prompt construction, and LLM invocation logic.

## Setup Instructions
### Install Backend Dependencies
```bash
pip install -r requirements.txt
```

### Configure Environment Variables
Create a ```.env``` file in the project root:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```
Ensure this file is **not committed** to version control.

### Install Frontend Dependencies
Navigate to the frontend directory and install dependencies:
```bash
cd drive-rag
npm install
```

## Running the Application
### Backend Only

From the project root:
```bash
uvicorn main:app --reload
```
The backend will start in development mode with hot reload enabled.
 
### Frontend Only
From the ```drive-rag``` directory:
```bash
npm run dev
```

## Full Application
To run the complete application start the backend and the frontend simultaneously. 

## Notes
* Ensure the backend is running before initiating frontend requests.
* API URLs and ports should align between frontend and backend configurations.
* This setup is intended for local development.