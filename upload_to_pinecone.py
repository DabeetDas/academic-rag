import os
import glob
from dotenv import load_dotenv
from pinecone import Pinecone
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load environment variables
load_dotenv(".env")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY not found in environment variables")

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

INDEX_NAME = "acadgpt"
MODEL_NAME = "llama-text-embed-v2"
NAMESPACE = "default"  # As per request

def extract_text_from_pdf(pdf_path):
    """Extracts text from a single PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def upload_pdfs(pdf_dir):
    """Uploads all PDFs in the specified directory to Pinecone."""
    
    # 1. Find all PDF files
    pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return

    print(f"Found {len(pdf_files)} PDF files to process.")

    # 2. Initialize Text Splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )

    index = pc.Index(INDEX_NAME)

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file}")
        
        try:
            # Extract text
            raw_text = extract_text_from_pdf(pdf_file)
            
            # Create chunks
            chunks = text_splitter.create_documents([raw_text])
            
            print(f"  - Split into {len(chunks)} chunks.")
            
            # Prepare data for embedding
            chunk_texts = [chunk.page_content for chunk in chunks]
            
            # Generate Embeddings using Pinecone Inference
            # The model is 'llama-text-embed-v2', dimension should be 1024
            # We process in batches to avoid hitting API limits if files are large
            batch_size = 96 # generic safe batch size
            
            vectors_to_upsert = []
            
            for i in range(0, len(chunk_texts), batch_size):
                batch_texts = chunk_texts[i : i + batch_size]
                
                # Input type 'passage' is usually recommended for storing in DB to be searched against 'query'
                embeddings = pc.inference.embed(
                    model=MODEL_NAME,
                    inputs=batch_texts,
                    parameters={"input_type": "passage", "truncate": "END"}
                )
                
                # Prepare vectors
                for j, embedding_obj in enumerate(embeddings):
                    # We need a unique ID. Using filename + chunk index
                    # Sanitizing filename for ID might be needed but simple string is usually fine in Pinecone
                    file_basename = os.path.basename(pdf_file)
                    chunk_idx = i + j
                    vector_id = f"{file_basename}_chunk_{chunk_idx}"
                    
                    metadata = {
                        "text": batch_texts[j],
                        "source": file_basename,
                        "chunk_index": chunk_idx
                    }
                    
                    vectors_to_upsert.append({
                        "id": vector_id,
                        "values": embedding_obj['values'],
                        "metadata": metadata
                    })
            
            # Upsert efficiently
            # Pinecone recommends upserting in batches of 100 or so
            upsert_batch_size = 100
            for i in range(0, len(vectors_to_upsert), upsert_batch_size):
                batch = vectors_to_upsert[i : i + upsert_batch_size]
                index.upsert(vectors=batch, namespace=NAMESPACE)
                
            print(f"  - Successfully uploaded {len(vectors_to_upsert)} chunks to Pinecone.")

        except Exception as e:
            print(f"  - Error processing {pdf_file}: {e}")

if __name__ == "__main__":
    # You can change this path to wherever your PDFs are located
    # For now, defaulting to a 'data' folder in the current directory
    TARGET_DIR = "data" 
    
    # Create data dir if it doesn't exist for convenience
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        print(f"Created directory '{TARGET_DIR}'. Please place PDF files there and run the script again.")
    else:
        upload_pdfs(TARGET_DIR)
