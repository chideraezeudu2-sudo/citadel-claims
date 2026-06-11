import os
import stripe
import httpx
from fastapi import APIRouter, Request, HTTPException
from utils.supabase_client import supabase
from services.sms_sender import send_sms

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


async def assign_plivo_number() -> str:
    """Get an available Plivo phone number"""
    async with httpx.AsyncClient() as client:
        # List available numbers
        response = await client.get(
            f"https://api.plivo.com/v1/Account/{os.getenv('PLIVO_AUTH_ID')}/AvailableNumberGroup/",
            auth=(os.getenv("PLIVO_AUTH_ID"), os.getenv("PLIVO_AUTH_TOKEN"))
        )
        
        data = response.json()
        if not data.get("objects"):
            raise Exception("No available Plivo numbers")
        
        # Get a US number
        for group in data["objects"]:
            if group.get("country") == "US" and group.get("numbers"):
                number = group["numbers"][0]["number"]
                
                # Rent the number
                await client.post(
                    f"https://api.plivo.com/v1/Account/{os.getenv('PLIVO_AUTH_ID')}/PhoneNumber/{number}/",
                    auth=(os.getenv("PLIVO_AUTH_ID"), os.getenv("PLIVO_AUTH_TOKEN")),
                    json={"app_id": os.getenv("PLIVO_APP_ID")}
                )
                return number
        
        raise Exception("No US numbers available")


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
        
        # Assign Plivo number
        plivo_number = await assign_plivo_number()
        
        # Create client in database
        supabase.table("clients").insert({
            "phone": client_phone,
            "email": customer_email,
            "name": customer_name,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
            "telnyx_number": plivo_number,  # Using same field, storing Plivo number
            "status": "active"
        }).execute()
        
        # Send welcome SMS
        await send_sms(
            client_phone,
            plivo_number,
            f"Welcome to Citadel Claims, {customer_name.split()[0] if customer_name else 'there'}! 🏛️\n\nThis is your dedicated claims line. Save this number.\n\nYou're on the $1,750/month plan — 50 claims included.\n\nText me anytime to submit a claim or ask anything. Ready when you are."
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