import os
import sys
from dotenv import load_dotenv

# 1. Force load .env from the current directory
env_path = os.path.join(os.path.dirname(__file__), '.env')
loaded = load_dotenv(dotenv_path=env_path)

print("=" * 60)
print("🔍 SUPABASE INGESTION & DIAGNOSTIC TEST")
print("=" * 60)

print(f"\n1. Environment File Check:")
print(f"   - Target path: {env_path}")
print(f"   - File exists? {'✅ Yes' if os.path.exists(env_path) else '❌ No'}")
print(f"   - Loaded via python-dotenv? {'✅ Yes' if loaded else '❌ No'}")

# 2. Retrieve variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

print("\n2. Credential Validation:")
if SUPABASE_URL:
    print(f"   - SUPABASE_URL: ✅ Found ({SUPABASE_URL[:15]}...)")
else:
    print("   - SUPABASE_URL: ❌ MISSING or Empty")

if SUPABASE_KEY:
    print(f"   - SUPABASE_KEY: ✅ Found ({SUPABASE_KEY[:10]}...)")
else:
    print("   - SUPABASE_KEY: ❌ MISSING or Empty")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("\n❌ CRITICAL: Cannot proceed without SUPABASE_URL and SUPABASE_KEY in your .env file.")
    sys.exit(1)

# 3. Test Supabase Import & Connection
try:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("\n3. Client Initialization: ✅ Supabase client created successfully.")
except ImportError:
    print("\n❌ ERROR: 'supabase' package is not installed in this virtual environment.")
    print("   Run: ..\\venv\\Scripts\\python.exe -m pip install supabase")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ ERROR initializing Supabase client: {e}")
    sys.exit(1)

# 4. Interactive Terminal Ingestion Test
print("\n" + "-" * 60)
print("📝 TEST DATA INGESTION")
print("-" * 60)

test_name = input("Enter Test Name [Default: Avinash Test]: ").strip() or "Avinash Test"
test_email = input("Enter Test Email [Default: avinashjayaraj.g@gmail.com]: ").strip() or "avinashjayaraj.g@gmail.com"
test_phone = input("Enter Test Phone [Default: 9876543210]: ").strip() or "9876543210"
test_req = input("Enter Test Requirements [Default: Healthcare App Quote]: ").strip() or "Healthcare App Quote"

test_data = {
    "name": test_name,
    "email": test_email,
    "phone": test_phone,
    "requirements": test_req
}

print(f"\n⏳ Attempting to insert into 'leads' table...")
print(f"   Payload: {test_data}")

try:
    response = supabase.table("leads").insert(test_data).execute()
    print("\n✅ INGESTION SUCCESSFUL!")
    print(f"   Inserted Record Response: {response.data}")
except Exception as e:
    print("\n❌ INGESTION FAILED!")
    print(f"   Error details: {e}")
    print("\n💡 Common causes for this error:")
    print("   1. Table name is not 'leads' (check exact spelling in Supabase Dashboard).")
    print("   2. Column names in 'leads' table do not match keys: name, email, phone, requirements.")
    print("   3. RLS (Row Level Security) is enabled on 'leads' table without an INSERT policy for anonymous users.")

# 5. Fetch recent records for verification
print("\n" + "-" * 60)
print("📊 READING RECENT RECORDS FROM SUPABASE")
print("-" * 60)

try:
    read_res = supabase.table("leads").select("*").order("created_at", desc=True).limit(5).execute()
    print(f"Fetched {len(read_res.data)} record(s):")
    for idx, record in enumerate(read_res.data, 1):
        print(f"  [{idx}] Name: {record.get('name')} | Email: {record.get('email')} | Phone: {record.get('phone')} | Req: {record.get('requirements')}")
except Exception as e:
    print(f"⚠️ Could not read records from table: {e}")

print("\n" + "=" * 60)