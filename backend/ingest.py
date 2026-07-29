import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# 1. Configuration
SUPABASE_URL = "https://ndiyellixdnirrxhzrbl.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

URLS = [
    "https://www.spritle.com/",
    "https://www.spritle.com/about-us/",
    "https://www.spritle.com/spritle-software-top-30-healthcare-software-development-companies/"
]

def scrape_page(url: str) -> str:
    print(f"📥 Scraping: {url}")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text(separator=" ")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase for line in lines for phrase in line.split("  "))
        clean_text = "\n".join(chunk for chunk in chunks if chunk)
        
        return clean_text
    except Exception as e:
        print(f"❌ Failed to scrape {url}: {e}")
        return ""

def main():
    if not SUPABASE_KEY or not GOOGLE_API_KEY:
        print("❌ Error: Please ensure SUPABASE_SERVICE_KEY and GOOGLE_API_KEY are set in your terminal!")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    '''embeddings_model = GoogleGenerativeAIEmbeddings(
        model="text-embedding-004", 
        google_api_key=GOOGLE_API_KEY,
        task_type="retrieval_document",       # Standard practice for chunk injection
        output_dimensionality=768
    )'''
    embeddings_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    all_text = ""
    for url in URLS:
        all_text += f"\n--- Source: {url} ---\n"
        all_text += scrape_page(url)

    if not all_text.strip():
        print("❌ No content scraped. Exiting.")
        return

    print("✂️ Chunking text...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_text(all_text)
    print(f"Generated {len(chunks)} chunks.")

    print("📤 Generating embeddings and uploading to Supabase...")
    for i, chunk in enumerate(chunks):
        vector = embeddings_model.embed_query(chunk)
        
        data = {
            "content": chunk,
            "embedding": vector,
            "metadata": {"source": "Spritle Web Scraping"}
        }
        
        try:
            supabase.table("documents").insert(data).execute()
            print(f"   Successfully uploaded chunk {i+1}/{len(chunks)}")
        except Exception as e:
            print(f"   ❌ Failed to upload chunk {i+1}: {e}")

    print("🎉 Ingestion complete!")

if __name__ == "__main__":
    main()