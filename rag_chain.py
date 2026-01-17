from dotenv import load_dotenv
load_dotenv(".env")
import os
import logging

logging.getLogger("chromadb").setLevel(logging.CRITICAL)

from langchain_core.vectorstores.base import VectorStoreRetriever
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_chroma import Chroma
from utils.query_retrieve import retrieve_query
from utils.format_docs import format_docs
from langchain_text_splitters import CharacterTextSplitter
from utils.prompt import rag_prompt, judge_prompt, query_refining_prompt

# Initialize Gemini LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# Initialize Gemini Embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

#embeddings = FakeEmbeddings(size=768) # Gemini embedding size is 768

text_splitter = CharacterTextSplitter(
    chunk_size = 600,
    chunk_overlap = 150,
    length_function = len
)

# Initialize ChromaDB as Vector Store with persistence
from chromadb.config import Settings

# Parse telemetry setting (default to True if not set, strict check for "False")
telemetry_var = os.getenv("ANONYMIZED_TELEMETRY", "True")
telemetry_enabled = telemetry_var.lower() != "false"

vector_store = Chroma(
    collection_name="test_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_db",
    client_settings=Settings(anonymized_telemetry=telemetry_enabled)
)

# Set Chroma as the Retriever
retriever = vector_store.as_retriever()

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

    def invoke(self, query: str):
        current_query = query
        final_answer = ""
        
        # Initial Retrieval
        retrieved_query_obj = retrieve_query(current_query, self.llm)
        search_query = retrieved_query_obj.content
        
        for attempt in range(self.max_retries + 1):
            print(f"--- Attempt {attempt + 1} ---")
            print(f"Search Query: {search_query}")
            
            docs = self.retriever.invoke(search_query)
            context = format_docs(docs)
            final_prompt = self.prompt.format(context=context, query=query) # Use original user query for answer generation
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
    
    def stream(self, query: str):
        # For stream, we ideally want to stream the process or just the final answer.
        # Since the interface usually expects the final answer stream, we will buffer until final answer is found
        # then stream the final answer.
        # Note: This effectively defeats the purpose of 'streaming' as in 'immediate tokens', 
        # but is necessary for validation loops unless we stream status updates.
        
        final_response = self.invoke(query)
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