import os
from datetime import date
from utils.supabase_client import supabase
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Estimated free tier limits
FREE_TIER_LIMITS = {
    "groq": 500000,    # tokens per day (approximate)
    "gemini": 1000000, # tokens per day (approximate)
    "telnyx": 200      # messages per month on trial
}

ALERT_THRESHOLDS = [0.80, 0.95]


async def log_usage(service: str, tokens: int = 0, requests: int = 1):
    """Log API usage to database"""
    today = date.today().isoformat()
    
    # Get today's record
    result = supabase.table("api_usage").select("*").eq("service", service).eq("date", today).execute()
    
    if result.data:
        record = result.data[0]
        new_tokens = record["tokens_used"] + tokens
        new_requests = record["requests_used"] + requests
        
        supabase.table("api_usage").update({
            "tokens_used": new_tokens,
            "requests_used": new_requests
        }).eq("id", record["id"]).execute()
        
        # Check thresholds
        if service in FREE_TIER_LIMITS:
            usage_ratio = new_tokens / FREE_TIER_LIMITS[service]
            for threshold in ALERT_THRESHOLDS:
                old_ratio = record["tokens_used"] / FREE_TIER_LIMITS[service]
                if old_ratio < threshold <= usage_ratio:
                    await send_alert(service, usage_ratio)
    else:
        supabase.table("api_usage").insert({
            "service": service,
            "tokens_used": tokens,
            "requests_used": requests,
            "date": today
        }).execute()


async def send_alert(service: str, usage_ratio: float):
    """Send email alert when approaching free tier limit"""
    sg = SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))
    
    percentage = int(usage_ratio * 100)
    
    message = Mail(
        from_email="alerts@citadelclaims.com",
        to_emails=os.getenv("ALERT_EMAIL"),
        subject=f"⚠️ Citadel Claims — {service.upper()} at {percentage}% of free tier",
        html_content=f"""
        <h2>Free Tier Usage Alert</h2>
        <p><strong>Service:</strong> {service.upper()}</p>
        <p><strong>Usage:</strong> {percentage}% of estimated free tier limit</p>
        <p><strong>Action needed:</strong> {'Consider upgrading or reducing usage.' if usage_ratio >= 0.95 else 'Monitor usage closely.'}</p>
        <p>Log into your dashboard to review current usage.</p>
        """
    )
    
    try:
        sg.send(message)
    except Exception as e:
        print(f"Alert email failed: {e}")