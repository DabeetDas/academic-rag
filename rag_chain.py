from langchain_core.vectorstores.base import VectorStoreRetriever
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_chroma import Chroma
from dotenv import load_dotenv
from utils.query_retrieve import retrieve_query
from utils.format_docs import format_docs
from langchain_text_splitters import CharacterTextSplitter
from utils.prompt import rag_prompt

load_dotenv(".env")

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
vector_store = Chroma(
    collection_name="test_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_db"
)

# Set Chroma as the Retriever
retriever = vector_store.as_retriever()

custom_rag_prompt = rag_prompt()


class RAGChain:
    def __init__(
            self,
            llm:ChatGoogleGenerativeAI,
            retriever:VectorStoreRetriever,
            prompt:PromptTemplate
    ):
        self.llm = llm
        self.retriever = retriever
        self.prompt = prompt

    def invoke(self,query:str):
        retrieved_query = retrieve_query(query,self.llm)
        docs = self.retriever.invoke(retrieved_query.content)
        context = format_docs(docs)
        final_prompt = self.prompt.format(context=context,query=query)
        return self.llm.invoke(final_prompt)
    
    def stream(self,query:str):
        retrieved_query = retrieve_query(query,self.llm)
        docs = self.retriever.invoke(retrieved_query.content)
        context = format_docs(docs)
        final_prompt = self.prompt.format(context=context,query=query)
        for chunk in self.llm.stream(final_prompt):
            yield chunk


rag_chain = RAGChain(llm,retriever,custom_rag_prompt)


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