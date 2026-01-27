from dotenv import load_dotenv
load_dotenv(".env")
import os
import logging

logging.getLogger("chromadb").setLevel(logging.CRITICAL)

from langchain_core.vectorstores.base import VectorStoreRetriever
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from typing import List
from pinecone import Pinecone
from utils.query_retrieve import retrieve_query
from utils.format_docs import format_docs
from utils.prompt import rag_prompt, judge_prompt, query_refining_prompt

# Initialize Gemini LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY not found in environment variables")

pc = Pinecone(api_key=PINECONE_API_KEY)
# These constants should match what was used in upload_to_pinecone.py
INDEX_NAME = "acadgpt" 
MODEL_NAME = "llama-text-embed-v2"
NAMESPACE = "default"

class PineconeRetriever(BaseRetriever):
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        # Embed the query using Pinecone Inference
        # input_type="query" is important for asymmetric retrieval models
        embeddings = pc.inference.embed(
            model=MODEL_NAME,
            inputs=[query],
            parameters={"input_type": "query"}
        )
        query_embedding = embeddings[0]['values']

        # Query the index
        index = pc.Index(INDEX_NAME)
        results = index.query(
            namespace=NAMESPACE,
            vector=query_embedding,
            top_k=5, 
            include_values=False,
            include_metadata=True
        )

        documents = []
        for match in results['matches']:
            metadata = match['metadata']
            # Reconstruct document content if stored in metadata
            content = metadata.get('text', '')
            # Clean up metadata to remove the text field if you don't want it duplicated
            doc_metadata = {k: v for k, v in metadata.items() if k != 'text'}
            doc_metadata['score'] = match['score']
            
            documents.append(Document(page_content=content, metadata=doc_metadata))
        
        return documents

# Set Pinecone as the Retriever
retriever = PineconeRetriever()

custom_rag_prompt = rag_prompt()
custom_judge_prompt = judge_prompt()
custom_refine_prompt = query_refining_prompt()


class RAGChain:
    def __init__(
            self,
            llm:ChatGoogleGenerativeAI,
            retriever:VectorStoreRetriever,
            prompt:PromptTemplate,
            judge_prompt:PromptTemplate,
            refine_prompt:PromptTemplate
    ):
        self.llm = llm
        self.retriever = retriever
        self.prompt = prompt
        self.judge_prompt = judge_prompt
        self.refine_prompt = refine_prompt
        self.max_retries = 3

    def _get_judge_feedback(self, query: str, answer: str) -> tuple[bool, str]:
        """
        Returns (is_satisfactory, feedback)
        """
        judge_input = self.judge_prompt.format(query=query, answer=answer)
        response = self.llm.invoke(judge_input).content
        
        is_satisfactory = "SATISFACTORY" in response
        feedback = ""
        if not is_satisfactory:
            # simple parsing assuming the format is strictly followed or at least contains Feedback:
            parts = response.split("Feedback:")
            if len(parts) > 1:
                feedback = parts[1].strip()
            else:
                feedback = response # fallback
        
        return is_satisfactory, feedback

    def invoke(self, query: str, chat_history: list = None):
        current_query = query
        final_answer = ""
        
        # Initial Retrieval
        retrieved_query_obj = retrieve_query(current_query, self.llm, chat_history)
        search_query = retrieved_query_obj.content
        
        for attempt in range(self.max_retries + 1):
            print(f"--- Attempt {attempt + 1} ---")
            print(f"Search Query: {search_query}")
            
            docs = self.retriever.invoke(search_query)
            context = format_docs(docs)
            
            formatted_history = ""
            if chat_history:
                for msg in chat_history:
                    formatted_history += f"{msg['role'].capitalize()}: {msg['content']}\n"

            final_prompt = self.prompt.format(context=context, query=query, chat_history=formatted_history) # Use original user query for answer generation
            answer_response = self.llm.invoke(final_prompt)
            current_answer = answer_response.content
            
            # Reflection Step
            is_satisfactory, feedback = self._get_judge_feedback(query, current_answer)
            
            if is_satisfactory:
                print("Judge: SATISFACTORY")
                final_answer = answer_response
                break
            else:
                print(f"Judge: UNSATISFACTORY. Feedback: {feedback}")
                if attempt < self.max_retries:
                    # Refine Query
                    refine_input = self.refine_prompt.format(query=query, feedback=feedback)
                    search_query = self.llm.invoke(refine_input).content.strip()
                else:
                    print("Max retries reached. Returning last answer.")
                    final_answer = answer_response

        return final_answer
    
    def stream(self, query: str, chat_history: list = None):
        # For stream, we ideally want to stream the process or just the final answer.
        # Since the interface usually expects the final answer stream, we will buffer until final answer is found
        # then stream the final answer.
        # Note: This effectively defeats the purpose of 'streaming' as in 'immediate tokens', 
        # but is necessary for validation loops unless we stream status updates.
        
        final_response = self.invoke(query, chat_history)
        # We can't easily "stream" a completed AIMessage response in the same way as a generator
        # So we will just yield the content if it's already done.
        # Or better, we can re-generate the final known good answer with stream=True if we want that UX,
        # but that wastes tokens. 
        # Let's just yield the final content as a single chunk or simulate streaming.
        
        yield final_response


rag_chain = RAGChain(llm, retriever, custom_rag_prompt, custom_judge_prompt, custom_refine_prompt)


'''
class RAGChain:
    def __init__(
        self,
        retriever: VectorStoreRetriever,
        prompt: PromptTemplate
    ):
        self.retriever = retriever
        self.prompt = prompt

    def invoke(self, query: str):
        docs = self.retriever.invoke(query)
        context = format_docs(docs)

        return {
            "query": query,
            "context": context
        }

rag_chain = RAGChain(
    retriever=retriever,
    prompt=custom_rag_prompt
)

'''