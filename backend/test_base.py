# C:\spritle-bot\backend\test_db.py
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

print("--- SUPABASE CONNECTION DIAGNOSTIC ---")
print(f"URL Found: {'YES' if SUPABASE_URL else 'NO'}")
print(f"Key Found: {'YES' if SUPABASE_KEY else 'NO'}\n")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Missing SUPABASE_URL or SUPABASE_KEY in .env file!")
    exit(1)

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase client initialized successfully.\n")

    # Table Check Array
    tables_to_check = ["leads", "telecallers", "audit_logs"]

    for table in tables_to_check:
        try:
            res = supabase.table(table).select("*").limit(1).execute()
            print(f"✅ Table '{table}': Accessible (Found {len(res.data)} records in test query)")
        except Exception as te:
            print(f"❌ Table '{table}': FAILED to query. Details: {te}")

except Exception as e:
    print(f"❌ Connection Failed: {e}")