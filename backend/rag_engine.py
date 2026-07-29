import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI


prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant. Use the following pieces of retrieved context to answer the question. 
If the context is empty or doesn't contain the answer, use your general knowledge to answer anyway.

Context:
{context}

Question: {question}

Answer:""")

'''prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant. Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, say that you don't know.

Context:
{context}

Question: {question}

Answer:""")'''

def format_docs(docs):
    print("\n=== DEBUG: RETRIEVED CHUNKS FROM SUPABASE ===")
    if not docs:
        print(">>> No matching documents found in vector store! <<<")
    for i, doc in enumerate(docs):
        print(f"Chunk {i+1}: {doc.page_content[:200]}...")
    print("=============================================\n")
    
    return "\n\n".join(doc.page_content for doc in docs)

def get_rag_chain(retriever):
    # This only runs when called, avoiding the import-time crash!
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("CRITICAL: API Key is missing from the environment.")

    ai_brain = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash", 
        temperature=0.3,
        google_api_key=api_key
    )

    rag_chain = (
        {
            "context": retriever | format_docs, 
            "question": RunnablePassthrough()
        }
        | prompt
        | ai_brain
        | StrOutputParser()
    )
    return rag_chain