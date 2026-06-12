import os
from datetime import date
from utils.supabase_client import supabase

# Estimated free tier limits
FREE_TIER_LIMITS = {
    "groq": 500000,     # tokens per day (approximate)
    "gemini": 1000000,  # tokens per day (approximate)
    "twilio": 200       # messages per month on trial
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
            old_ratio = record["tokens_used"] / FREE_TIER_LIMITS[service]
            for threshold in ALERT_THRESHOLDS:
                if old_ratio < threshold <= usage_ratio:
                    print(f"⚠️ {service.upper()} at {int(usage_ratio * 100)}% of free tier limit")
                    # Alert would be sent here if SendGrid is configured
    else:
        supabase.table("api_usage").insert({
            "service": service,
            "tokens_used": tokens,
            "requests_used": requests,
            "date": today
        }).execute()