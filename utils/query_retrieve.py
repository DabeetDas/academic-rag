from langchain_openai import ChatOpenAI

def retrieve_query(query:str,llm:ChatOpenAI):
    
    # Rewritten Query Prompt
    query_rewrite_prompt = f"""You are a helpful assistant that takes a
    user's query and turns it into a short statement or paragraph so that
    it can be used in a semantic similarity search on a vector database to
    return the most similar chunks of content based on the rewritten query.
    Please make no comments, just return the rewritten query.
    \n\nquery: {query}\n\nai: """

    # Invoke LLM
    retrieval_query = llm.invoke(query_rewrite_prompt)

    # Return Generated Retrieval Query
    return retrieval_query