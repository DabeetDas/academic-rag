from langchain_core.language_models import BaseChatModel

def retrieve_query(query:str, llm:BaseChatModel, chat_history: list = None):
    
    formatted_history = ""
    if chat_history:
        for msg in chat_history:
            formatted_history += f"{msg['role'].capitalize()}: {msg['content']}\n"

    # Rewritten Query Prompt
    query_rewrite_prompt = f"""You are a helpful assistant that takes a
    user's query and turns it into a short statement or paragraph so that
    it can be used in a semantic similarity search on a vector database to
    return the most similar chunks of content based on the rewritten query.
    If the user's query is a follow-up question, use the chat history to provide context.
    Please make no comments, just return the rewritten query.
    
    Chat History:
    {formatted_history}

    query: {query}

    ai: """

    # Invoke LLM
    retrieval_query = llm.invoke(query_rewrite_prompt)

    # Return Generated Retrieval Query
    return retrieval_query
