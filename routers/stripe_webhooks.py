import os
import stripe
from fastapi import APIRouter, Request, HTTPException
from utils.supabase_client import supabase
from services.sms_sender import send_sms

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def get_twilio_number() -> str:
    """Get the shared Twilio phone number"""
    return os.getenv("TWILIO_PHONE_NUMBER", "+12566374466")


@router.post("/webhook/stripe")
async def handle_stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_details", {}).get("email", "")
        customer_name = session.get("customer_details", {}).get("name", "")
        stripe_customer_id = session.get("customer", "")
        stripe_subscription_id = session.get("subscription", "")
        client_phone = session.get("metadata", {}).get("phone", "")
        
        twilio_number = get_twilio_number()
        
        # Create client in database
        supabase.table("clients").insert({
            "phone": client_phone,
            "email": customer_email,
            "name": customer_name,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
            "telnyx_number": twilio_number,  # Using Twilio number
            "status": "active"
        }).execute()
        
        # Send welcome SMS
        await send_sms(
            client_phone,
            twilio_number,
            f"Welcome to Citadel Claims, {customer_name.split()[0] if customer_name else 'there'}! 🏛️\n\nThis is your dedicated claims line. Save this number.\n\nYou're on the $1,750/month plan — 50 claims, 1,000 messages included.\n\nText me anytime to submit a claim or ask anything. Ready when you are."
        )
    
    elif event["type"] == "customer.subscription.deleted":
        subscription_id = event["data"]["object"]["id"]
        
        client_result = supabase.table("clients").select("*").eq("stripe_subscription_id", subscription_id).execute()
        if client_result.data:
            client = client_result.data[0]
            supabase.table("clients").update({"status": "cancelled"}).eq("id", client["id"]).execute()
            
            await send_sms(
                client["phone"],
                client["telnyx_number"],
                "Your Citadel Claims subscription has been cancelled. Your estimates remain accessible via your portal link. We hope to work with you again."
            )
    
    return {"status": "ok"}