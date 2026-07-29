import sys
from supabase import create_client, Client

# Explicit credentials found in your Supabase Connect panel
SUPABASE_URL = "https://ndiyellixdnirrxhzrbl.supabase.co"
SUPABASE_KEY = "sb_publishable_2cYgVKQbu67TD7OdjhmvYQ_8StiyEYB"

print("--> Initializing Supabase Client...")

try:
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("--> Supabase Client initialized successfully!")
except Exception as e:
    print(f"--> ERROR Initializing Supabase: {str(e)}")
    sys.exit(1)