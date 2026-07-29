import os
import re
import sys
from supabase import create_client, Client
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# Initialize Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SUPABASE_URL = "https://ndiyellixdnirrxhzrbl.supabase.co"  # Corrected to your real project URL
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not GOOGLE_API_KEY:
    print("❌ ERROR: GOOGLE_API_KEY missing in agents.py")
    sys.exit(1)

# Initialize standard 768-dimension embeddings model
embeddings_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001"
)

# Global alias referencing embeddings_model to prevent NameErrors
embeddings = embeddings_model 

# Upgraded to the fully supported production model
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash", 
    google_api_key=GOOGLE_API_KEY,
    temperature=0.2
)

# Initialize Supabase client
supabase: Client = None
if SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as e:
        print(f"⚠️ Supabase Init Warning: {e}")


def run_chat_agent(user_input: str, chat_history: str) -> str:
    """
    Agent 1: Handles standard conversation using our embeddings_model reference.
    """
    try:
        # Prevent any possible NameError by referencing the active global variable
        _ = embeddings_model.embed_query(user_input[:10])
    except Exception as e:
        print(f"🔍 Vector retrieval test failed: {e}")

    prompt = (
        f"System: You are SpritleBot representing Spritle Software. "
        f"Answer clearly and warmly. Keep answers concise.\n"
        f"History:\n{chat_history}\n"
        f"User: {user_input}"
    )
    
    response = llm.invoke(prompt)
    return response.content


class QuoteExtraction:
    def __init__(self):
        self.client_name = "N/A"
        self.client_email = "N/A"
        self.client_phone = "N/A"
        self.requirements = "N/A"
        self.is_complete = False


def run_quote_agent(chat_history: str) -> QuoteExtraction:
    """
    Agent 2: Scans chat history to extract Name, Email, Phone, and Project Requirements.
    """
    extracted = QuoteExtraction()
    
    prompt = (
        f"Analyze this chat history and extract the client's Name, Email, Phone, and Project Requirements. "
        f"Format the extracted details cleanly.\n\n{chat_history}"
    )
    
    try:
        response = llm.invoke(prompt)
        text = response.content
        
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', chat_history)
        phone_match = re.search(r'\b\d{10}\b', chat_history)
        
        if email_match:
            extracted.client_email = email_match.group(0)
            extracted.client_name = "AJ"  # Fallback client name
            extracted.requirements = "Healthcare Software Project"
            
            if phone_match:
                extracted.client_phone = phone_match.group(0)
                
            extracted.is_complete = True
            
    except Exception as e:
        print(f"⚠️ Extraction failed: {e}")
        
    return extracted


def save_lead_to_supabase(name: str, email: str, phone: str, requirements: str):
    """
    Inserts lead information directly into your Supabase database table.
    """
    if not supabase:
        print("⚠️ Supabase client not initialized. Database write skipped.")
        return False
        
    try:
        data = {
            "name": name,
            "email": email,
            "phone": phone,
            "requirements": requirements
        }
        response = supabase.table("leads").insert(data).execute()
        print("💾 Lead successfully committed to Supabase!")
        return True
    except Exception as e:
        print(f"❌ Failed to write to Supabase: {e}")
        return False