from langchain_core.prompts import PromptTemplate

def rag_prompt():
    prompt_template = """
    You are an academic assistant for a university repository.
     
    Rules:
    - First, try to answer using the provided context.
    - If the provided context does not contain the answer, you may use your general knowledge to answer the question.
    - Do not explicitly state that you are using general knowledge. 
    - State EXPLICITLY if you use the context to answer the question. 
    - If you use general knowledge, please be helpful and accurate.
    - Use a formal academic tone.
    - Be concise but precise.
    
    Context:
    {context}
    
    Question:
    {query}

    answer:
    """

    rag_prompt = PromptTemplate.from_template(prompt_template)
    return rag_prompt

def judge_prompt():
    prompt_template = """
    You are an impartial judge evaluating the quality of an answer provided by an AI assistant for a user's query.
    
    Query: {query}
    Answer: {answer}
    
    Your task is to determine if the answer is satisfactory, accurate, and relevant to the query.
    
    Return a response in the following format:
    Status: [SATISFACTORY | UNSATISFACTORY]
    Feedback: [If UNSATISFACTORY, provide concise feedback on what is missing or wrong. If SATISFACTORY, leave empty.]
    """
    return PromptTemplate.from_template(prompt_template)

def query_refining_prompt():
    prompt_template = """
    You are an expert search query improver. 
    The original query yielded an unsatisfactory answer. 
    
    Original Query: {query}
    Previous Answer Feedback: {feedback}
    
    Please generate a new, optimized search query that addresses the feedback and is more likely to retrieve relevant information.
    Do not add any preamble or explanation, just the new query text.
    
    New Query:
    """
    return PromptTemplate.from_template(prompt_template)