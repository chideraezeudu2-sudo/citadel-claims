import os
import tempfile
from fastapi import APIRouter, Request
from utils.supabase_client import supabase
from services.nlp import classify_intent
from services.ai_pipeline import process_claim
from services.pdf_generator import generate_pdf
from services.storage import upload_pdf
from services.sms_sender import send_sms

router = APIRouter()

HELP_MESSAGE = """Welcome to Citadel Claims 🏛️

Just text me naturally. Here's what I can do:

📋 Submit a claim — send photos + voice note
📊 Check status — ask about your claims
📁 Get your files — ask for your portal link
💳 Billing info — ask about your usage
❌ Cancel — ask to cancel anytime

What do you need?"""


@router.post("/webhook/sms")
async def handle_inbound_sms(request: Request):
    """Handle inbound SMS from Twilio with message limit enforcement"""
    try:
        # Twilio sends form data, not JSON
        form_data = await request.form()
        payload = dict(form_data)
        
        from_number = payload.get("From", "")
        to_number = payload.get("To", "")
        body = payload.get("Body", "").strip()
        num_media = int(payload.get("NumMedia", 0))
        
        # Get media URLs if any
        media_urls = []
        for i in range(num_media):
            media_url = payload.get(f"MediaUrl{i}", "")
            if media_url:
                media_urls.append(media_url)
        
        # Look up client by their assigned number
        client_result = supabase.table("clients").select("*").eq("telnyx_number", to_number).execute()
        
        if not client_result.data:
            client_result = supabase.table("clients").select("*").eq("phone", from_number).execute()

        if not client_result.data:
            await send_sms(from_number, to_number, 
                "Hi! This number is for Citadel Claims clients. Visit our site to get started.")
            return {"status": "ok"}
        
        client = client_result.data[0]
        
        # Check message limit (default 1000 messages/month = ~$8.90/user with phone rental)
        msg_limit = client.get("message_limit", 1000)
        msg_used = client.get("messages_used_this_month", 0)
        
        # Update message count immediately
        new_msg_count = msg_used + 1
        supabase.table("clients").update({
            "messages_used_this_month": new_msg_count
        }).eq("id", client["id"]).execute()
        
        # Check if over limit (allow 1 grace message for limit notification)
        if new_msg_count > msg_limit and new_msg_count > msg_used + 1:
            await send_sms(from_number, to_number,
                f"⚠️ Message limit reached ({msg_used}/{msg_limit}).\n\nUpgrade or wait until next billing cycle.")
            return {"status": "ok"}
        
        # Log inbound message
        supabase.table("messages").insert({
            "client_id": client["id"],
            "direction": "inbound",
            "body": body,
            "media_urls": media_urls
        }).execute()
        
        # Classify intent
        intent_result = await classify_intent(body)
        intent = intent_result.get("intent", "UNKNOWN")
        
        # Route to correct handler
        if intent == "HELP" or intent == "UNKNOWN":
            await send_sms(from_number, to_number, HELP_MESSAGE)
        
        elif intent == "GET_PORTAL":
            portal_url = f"{os.getenv('BASE_URL')}/portal/{client['portal_token']}"
            await send_sms(from_number, to_number, 
                f"Here's your Citadel Claims portal 🏛️\n\n{portal_url}\n\nBookmark this link — all your estimates and claim history are here.")
        
        elif intent == "CHECK_STATUS":
            claims = supabase.table("claims").select("*").eq("client_id", client["id"]).order("created_at", desc=True).limit(5).execute()
            if not claims.data:
                await send_sms(from_number, to_number, "You haven't submitted any claims yet. Send photos + a voice note to get started!")
            else:
                status_lines = []
                for c in claims.data:
                    status_lines.append(f"• {c['claim_type'] or 'Claim'} — {c['status'].upper()}")
                await send_sms(from_number, to_number, "Your recent claims:\n\n" + "\n".join(status_lines))
        
        elif intent == "BILLING":
            msg_used = new_msg_count  # Use updated count
            msg_limit = client.get("message_limit", 1000)
            used = client.get("claims_used_this_month", 0)
            remaining = max(0, 50 - used)
            overage = max(0, used - 50)
            msg = f"📊 Your usage this month:\n\n{used}/50 claims\n{msg_used}/1000 messages\n\n{remaining} claims remaining"
            if overage > 0:
                msg += f"\n{overage} overage claims (${overage * 75} billed)"
            await send_sms(from_number, to_number, msg)
        
        elif intent == "CANCEL":
            await send_sms(from_number, to_number, 
                "To cancel your Citadel Claims subscription, reply CONFIRM CANCEL and we'll process it within 24 hours. You'll keep access until the end of your billing period.")
        
        elif intent == "SUBMIT_CLAIM":
            if not body:
                await send_sms(from_number, to_number,
                    "To submit a claim, text a description of the damage (e.g. 'roof damage from storm'). You can also send photos via your portal link.")
                return {"status": "ok"}
            
            # Create claim record
            claim = supabase.table("claims").insert({
                "client_id": client["id"],
                "claim_type": body,
                "status": "processing"
            }).execute().data[0]
            
            claim_id = claim["id"]
            
            # Send acknowledgment immediately
            await send_sms(from_number, to_number,
                f"✅ Got it! Claim {claim_id[:8].upper()} received.\n\nWe're processing your estimate now. You'll get your file within 24 hours (usually much faster).")
            
            # Run AI pipeline (without photos for now)
            estimate_text, transcript = await process_claim(
                claim_id, None, [], body
            )
            
            # Generate PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                pdf_path = tmp.name
            
            await generate_pdf(claim_id, estimate_text, pdf_path)
            pdf_url = await upload_pdf(pdf_path, claim_id)
            
            # Update claim as complete
            supabase.table("claims").update({
                "status": "complete",
                "transcript": transcript,
                "estimate_draft": estimate_text,
                "pdf_url": pdf_url
            }).eq("id", claim_id).execute()
            
            # Update client claim count
            supabase.table("clients").update({
                "claims_used_this_month": client["claims_used_this_month"] + 1
            }).eq("id", client["id"]).execute()
            
            # Send completion message with direct link
            portal_url = f"{os.getenv('BASE_URL')}/portal/{client['portal_token']}"
            await send_sms(from_number, to_number,
                f"🏛️ Your estimate is ready!\n\nClaim: {claim_id[:8].upper()}\n\n📄 Download PDF:\n{pdf_url}\n\n📁 Full portal:\n{portal_url}\n\nReview and submit. Text us if anything needs revision — it's free.")
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"SMS handler error: {e}")
        return {"status": "error", "detail": str(e)}