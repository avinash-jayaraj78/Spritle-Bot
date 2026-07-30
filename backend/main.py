import os
import re
import hashlib
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ WARNING: SUPABASE_URL or SUPABASE_KEY is missing!")

# Initialize Supabase Client
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Import AI modules
#from test_agents import summarize_requirements_with_llm, extract_contact_info, llm, SYSTEM_CONTEXT
from .test_agents import summarize_requirements_with_llm, extract_contact_info, llm, SYSTEM_CONTEXT

app = FastAPI(title="Spritle CRM & AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://spritle-bot-git-main-aj-e4fe.vercel.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hardcoded Admin Credentials
ADMIN_UID = "admin@spritle.com"
ADMIN_PASS_HASH = hashlib.sha256("Admin@1234".encode()).hexdigest()

# Presence Expiry Threshold (In Seconds)
HEARTBEAT_THRESHOLD_SECONDS = 5

# --- HELPER FUNCTIONS ---
def is_telecaller_active(last_hb_str: str, is_online_flag: bool) -> bool:
    """Rigid presence check: Returns True ONLY if flag is True AND heartbeat was within last 5s."""
    if not is_online_flag or not last_hb_str:
        return False
    try:
        # Parse timestamp safely
        hb_time = datetime.fromisoformat(last_hb_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - hb_time).total_seconds() <= HEARTBEAT_THRESHOLD_SECONDS
    except Exception:
        return False

def get_truly_online_telecallers():
    """Fetches all telecallers and filters strictly by recent heartbeat."""
    res = supabase_client.table("telecallers").select("*").execute()
    telecallers = res.data or []
    
    online_list = []
    for t in telecallers:
        hb_str = t.get("last_heartbeat")
        flag = t.get("is_online", False)
        if is_telecaller_active(hb_str, flag):
            online_list.append(t)
        elif flag:
            # Lazy cleanup of stale status flags in database
            supabase_client.table("telecallers").update({"is_online": False}).eq("id", t["id"]).execute()
            
    return online_list

def log_audit_event(event_type: str, actor: str, lead_id: str = None, details: dict = None):
    try:
        payload = {
            "event_type": event_type,
            "actor": actor,
            "details": details or {}
        }
        if lead_id and str(lead_id).isdigit():
            payload["lead_id"] = int(lead_id)

        supabase_client.table("audit_logs").insert(payload).execute()
    except Exception as e:
        print(f"Failed to log audit event: {e}")

def sync_new_lead_rigid(name: str, phone: str, email: str, requirements: str):
    """Allocates leads ONLY to active outreachers with live heartbeats."""
    active_outreachers = get_truly_online_telecallers()
    assigned_id = None
    assigned_name = "Unassigned"

    if active_outreachers:
        # Round-robin or pick the first genuinely active telecaller
        target = active_outreachers[0]
        assigned_id = target["id"]
        assigned_name = target["full_name"]

    lead_data = {
        "name": name,
        "phone": phone,
        "email": email,
        "requirements": requirements,
        "status": "New Inquiry",
        "assigned_to": assigned_id
    }

    res = supabase_client.table("leads").insert(lead_data).execute()
    inserted_lead = res.data[0] if res.data else {}

    log_audit_event(
        event_type="LEAD_CAPTURED",
        actor="AI Assistant",
        lead_id=str(inserted_lead.get("id", "")),
        details={
            "assigned_to_name": assigned_name,
            "assigned_to_id": assigned_id,
            "lead_email": email
        }
    )
    return inserted_lead

# --- SCHEMAS ---
class LoginRequest(BaseModel):
    email: str
    password: str

class CreateTelecallerRequest(BaseModel):
    full_name: str
    email: str
    initial_password: str

class ResetPasswordRequest(BaseModel):
    telecaller_id: str
    new_password: str

class ChangeOwnPasswordRequest(BaseModel):
    telecaller_id: str
    old_password: str
    new_password: str

class UpdateStatusRequest(BaseModel):
    lead_id: int
    status: str
    telecaller_id: str
    telecaller_name: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: list[str] = []

# --- LLM GUARDRAIL CHECKER ---
ALLOWED_KEYWORDS = [
    "spritle", "software", "project", "app", "mobile", "web", "ai", "ml", "cloud",
    "devops", "development", "build", "hire", "pricing", "quote", "cost", "inquiry",
    "contact", "services", "team", "consulting", "solution", "digital", "iot"
]

BLOCKED_PATTERNS = [
    r"\brecipe\b", r"\bcook\b", r"\bingredients\b", r"\bhomework\b",
    r"\bwrite code for\b", r"\bpython script to\b", r"\bjoke\b", r"\bpoem\b",
    r"\bmovie\b", r"\bsong\b", r"\bcapital of\b", r"\bweather\b"
]

def check_guardrails(user_message: str) -> bool:
    msg_lower = user_message.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, msg_lower):
            return False
    for kw in ALLOWED_KEYWORDS:
        if kw in msg_lower:
            return True
    return len(msg_lower.split()) <= 4

# --- AUTHENTICATION & RIGID PRESENCE ENDPOINTS ---
@app.post("/api/login")
def login(req: LoginRequest):
    input_hash = hashlib.sha256(req.password.encode()).hexdigest()

    if req.email == ADMIN_UID and input_hash == ADMIN_PASS_HASH:
        return {"status": "success", "role": "admin", "token": "admin-session-token", "name": "Master Admin"}

    res = supabase_client.table("telecallers").select("*").eq("email", req.email).execute()
    if not res.data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = res.data[0]
    if user["password_hash"] != input_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    now_iso = datetime.now(timezone.utc).isoformat()
    supabase_client.table("telecallers").update({
        "is_online": True,
        "last_heartbeat": now_iso
    }).eq("id", user["id"]).execute()

    return {
        "status": "success",
        "role": "telecaller",
        "user_id": user["id"],
        "name": user["full_name"],
        "email": user["email"]
    }

@app.post("/api/telecaller/heartbeat")
def telecaller_heartbeat(telecaller_id: str):
    now_iso = datetime.now(timezone.utc).isoformat()
    supabase_client.table("telecallers").update({
        "is_online": True,
        "last_heartbeat": now_iso
    }).eq("id", telecaller_id).execute()
    return {"status": "success", "timestamp": now_iso}

@app.post("/api/telecaller/set-offline")
def set_telecaller_offline(telecaller_id: str):
    """Called immediately when tab is hidden, closed, or user logs out."""
    supabase_client.table("telecallers").update({
        "is_online": False
    }).eq("id", telecaller_id).execute()
    return {"status": "success"}

# --- ADMIN ENDPOINTS ---
@app.get("/api/admin/stats")
def get_dashboard_stats():
    leads = supabase_client.table("leads").select("id, status").execute().data or []
    truly_online = get_truly_online_telecallers()

    total_leads = len(leads)
    active_telecallers = len(truly_online)
    pending = len([l for l in leads if l.get("status") in ["New Inquiry", "Pending"]])
    in_progress = len([l for l in leads if l.get("status") in ["In Progress", "Outreach Done"]])
    delivered = len([l for l in leads if l.get("status") == "Project Delivered"])

    return {
        "status": "success",
        "total_leads": total_leads,
        "active_telecallers": active_telecallers,
        "pending": pending,
        "in_progress": in_progress,
        "delivered": delivered
    }

@app.get("/api/admin/telecallers")
def get_all_telecallers():
    res = supabase_client.table("telecallers").select("id, full_name, email, is_online, last_heartbeat").execute()
    raw_telecallers = res.data or []
    
    formatted = []
    for t in raw_telecallers:
        hb_str = t.get("last_heartbeat")
        flag = t.get("is_online", False)
        active_status = is_telecaller_active(hb_str, flag)
        formatted.append({
            "id": t["id"],
            "full_name": t["full_name"],
            "email": t["email"],
            "is_online": active_status,
            "last_heartbeat": hb_str
        })
        
    return {"status": "success", "telecallers": formatted}

@app.get("/api/admin/telecaller-details")
def get_telecaller_details(user_id: str):
    user_res = supabase_client.table("telecallers").select("id, full_name, email, is_online, last_heartbeat").eq("id", user_id).execute()
    if not user_res.data:
        raise HTTPException(status_code=404, detail="Telecaller not found")

    user_data = user_res.data[0]
    user_data["is_online"] = is_telecaller_active(user_data.get("last_heartbeat"), user_data.get("is_online", False))

    leads_res = supabase_client.table("leads").select("*").eq("assigned_to", user_id).execute()
    return {
        "status": "success",
        "profile": user_data,
        "leads": leads_res.data or []
    }

@app.get("/api/admin/logs")
def get_audit_logs(limit: int = 50):
    res = supabase_client.table("audit_logs").select("*").order("created_at", desc=True).limit(limit).execute()
    return {"status": "success", "logs": res.data or []}

@app.post("/api/admin/create-telecaller")
def create_telecaller(req: CreateTelecallerRequest):
    pass_hash = hashlib.sha256(req.initial_password.encode()).hexdigest()
    res = supabase_client.table("telecallers").insert({
        "full_name": req.full_name,
        "email": req.email,
        "password_hash": pass_hash,
        "is_online": False
    }).execute()

    log_audit_event("TELECALLER_CREATED", "Master Admin", details={"created_email": req.email, "name": req.full_name})
    return {"status": "success", "data": res.data}

@app.post("/api/admin/reset-password")
def admin_reset_password(req: ResetPasswordRequest):
    new_hash = hashlib.sha256(req.new_password.encode()).hexdigest()
    supabase_client.table("telecallers").update({"password_hash": new_hash}).eq("id", req.telecaller_id).execute()
    log_audit_event("PASSWORD_RESET_BY_ADMIN", "Master Admin", details={"telecaller_id": req.telecaller_id})
    return {"status": "success", "message": "Password updated successfully"}

# --- OUTREACHER ENDPOINTS ---
@app.get("/api/telecaller/leads")
def get_assigned_leads(user_id: str):
    res = supabase_client.table("leads").select("*").eq("assigned_to", user_id).execute()
    return {"status": "success", "leads": res.data or []}

@app.post("/api/telecaller/update-status")
def update_lead_status(req: UpdateStatusRequest):
    prev = supabase_client.table("leads").select("status").eq("id", req.lead_id).execute()
    old_status = prev.data[0]["status"] if prev.data else "Unknown"

    supabase_client.table("leads").update({"status": req.status}).eq("id", req.lead_id).execute()

    log_audit_event(
        event_type="STATUS_CHANGED",
        actor=f"Outreacher ({req.telecaller_name})",
        lead_id=str(req.lead_id),
        details={"old_status": old_status, "new_status": req.status, "telecaller_id": req.telecaller_id}
    )
    return {"status": "success", "message": "Lead status updated"}

@app.post("/api/telecaller/change-password")
def change_own_password(req: ChangeOwnPasswordRequest):
    old_hash = hashlib.sha256(req.old_password.encode()).hexdigest()
    new_hash = hashlib.sha256(req.new_password.encode()).hexdigest()

    user_res = supabase_client.table("telecallers").select("password_hash").eq("id", req.telecaller_id).execute()
    if not user_res.data or user_res.data[0]["password_hash"] != old_hash:
        raise HTTPException(status_code=400, detail="Incorrect current password")

    supabase_client.table("telecallers").update({"password_hash": new_hash}).eq("id", req.telecaller_id).execute()
    log_audit_event("PASSWORD_CHANGED_BY_USER", req.telecaller_id, details={"status": "self_service_update"})
    return {"status": "success", "message": "Password changed successfully"}

# --- CHATBOT ENDPOINT ---
@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    user_input = req.message
    history = req.conversation_history

    if not check_guardrails(user_input):
        return {
            "reply": "I am Spritle Software's automated assistant. I can only assist with software development services, project inquiries, technology stack selection, or custom solutions. How can I help with your engineering requirements today?",
            "lead_intercepted": False
        }

    phone_match = re.search(r'\b\d{10}\b', user_input)
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', user_input)

    if phone_match or email_match:
        name, email, phone = extract_contact_info(user_input)
        user_turns = [turn.replace("User: ", "") for turn in history if turn.startswith("User:")]
        user_turns.append(user_input)

        single_line_req = summarize_requirements_with_llm(user_turns)
        target_email = email if email else "ad2063277@gmail.com"

        sync_new_lead_rigid(
            name=name,
            phone=phone,
            email=target_email,
            requirements=single_line_req
        )

        reply = f"Thank you, {name}! I've registered your project requirements: \"{single_line_req}\". Our Outreach team has been assigned and will contact you at {target_email}!"
        return {"reply": reply, "lead_intercepted": True}

    messages = [("system", SYSTEM_CONTEXT)]
    for turn in history[-6:]:
        messages.append(("human" if turn.startswith("User:") else "assistant", turn))
    messages.append(("human", user_input))

    res = llm.invoke(messages)
    return {"reply": str(res.content).strip(), "lead_intercepted": False}
