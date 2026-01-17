from rag_chain import rag_chain

def test_rag_reflection():
    # A query that might be tricky or ambiguous to trigger reflection, 
    # or just a standard one to see if it passes judge.
    query = "What is the primary methodology described in the documents?"
    
    print(f"Querying: {query}")
    print("-" * 50)
    
    # Using invoke
    try:
        response = rag_chain.invoke(query)
        print("\nFinal Answer:")
        print(response.content)
    except Exception as e:
        print(f"Error during invocation: {e}")

if __name__ == "__main__":
    test_rag_reflection()
