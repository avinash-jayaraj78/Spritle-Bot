import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

GMAIL_USER = os.getenv("GMAIL_USER", "ad2063277@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "frlf jqpa ypou kdrj")


def get_next_telecaller_id() -> str | None:
    """
    Allocates lead prioritizing ONLINE outreachers first.
    If none are online, falls back to offline telecallers.
    Selects the telecaller holding the FEWEST active leads.
    """
    try:
        # 1. Fetch all telecallers
        res = supabase.table("telecallers").select("id, is_online").execute()
        all_telecallers = res.data or []
        if not all_telecallers:
            return None

        # Filter active online telecallers
        online_telecallers = [t for t in all_telecallers if t.get("is_online") is True]
        candidates = online_telecallers if online_telecallers else all_telecallers

        # 2. Count current leads per candidate
        candidate_ids = [t["id"] for t in candidates]
        leads_res = supabase.table("leads").select("assigned_to").execute()
        
        counts = {cid: 0 for cid in candidate_ids}
        for lead in leads_res.data or []:
            aid = lead.get("assigned_to")
            if aid in counts:
                counts[aid] += 1

        # 3. Pick candidate with minimum assigned leads
        selected_id = min(counts, key=counts.get)
        return selected_id

    except Exception as e:
        print(f"⚠️ Allocation error: {e}")
        return None


def sync_new_lead(name: str, phone: str, email: str, requirements: str):
    """Unified handler: Allocates lead, logs audit event, and dispatches email."""
    
    # 1. Determine Allocation
    assigned_telecaller_id = get_next_telecaller_id()

    # 2. Insert into Supabase 'leads'
    payload = {
        "name": name,
        "phone": phone,
        "email": email,
        "requirements": requirements,
        "status": "New Inquiry",
        "assigned_to": assigned_telecaller_id
    }
    
    try:
        res = supabase.table("leads").insert(payload).execute()
        print(f"📊 Lead successfully registered and assigned to: {assigned_telecaller_id}")

        # 3. Log Audit Record
        supabase.table("audit_logs").insert({
            "event_type": "LEAD_AUTO_ASSIGNED",
            "actor": "System Automation",
            "details": {
                "assigned_to": assigned_telecaller_id or "Unassigned",
                "lead_email": email,
                "lead_name": name
            }
        }).execute()

    except Exception as e:
        print(f"⚠️ Supabase write failed: {e}")

    # 4. Dispatch Email Confirmation
    if GMAIL_APP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg['From'] = f"Spritle Software <{GMAIL_USER}>"
            msg['To'] = email
            msg['Subject'] = "Acknowledgement: Project Inquiry Received | Spritle Software"

            text_body = f"Hi {name},\n\nThank you for reaching out to Spritle Software! We have received your inquiry for: {requirements}.\n\nBest,\nSpritle Software Team"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
              <h2>Spritle Software</h2>
              <p>Hi <strong>{name}</strong>,</p>
              <p>Thank you for reaching out! We have registered your inquiry:</p>
              <blockquote style="background: #f4f6f8; padding: 10px; border-left: 4px solid #0052cc;">
                {requirements}
              </blockquote>
              <p>Our outreach team will be in touch with you shortly.</p>
            </body>
            </html>
            """

            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"📧 Confirmation email sent to {email}.")
        except Exception as e:
            print(f"⚠️ Email dispatch error: {e}")