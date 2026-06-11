from fastapi import APIRouter, HTTPException
from utils.supabase_client import supabase

router = APIRouter()


@router.get("/portal/{token}")
async def get_portal_data(token: str):
    # Look up client by portal token
    client_result = supabase.table("clients").select("*").eq("portal_token", token).execute()
    
    if not client_result.data:
        raise HTTPException(status_code=404, detail="Portal not found")
    
    client = client_result.data[0]
    
    if client["status"] == "cancelled":
        raise HTTPException(status_code=403, detail="Subscription cancelled")
    
    # Get all claims
    claims_result = supabase.table("claims").select("*").eq("client_id", client["id"]).order("created_at", desc=True).execute()
    
    claims = []
    for claim in claims_result.data:
        claims.append({
            "id": claim["id"][:8].upper(),
            "full_id": claim["id"],
            "claim_type": claim.get("claim_type", "General Claim"),
            "status": claim["status"],
            "created_at": claim["created_at"],
            "completed_at": claim.get("completed_at"),
            "pdf_url": claim.get("pdf_url"),
            "photo_count": len(claim.get("photo_urls") or [])
        })
    
    used = client.get("claims_used_this_month", 0)
    
    return {
        "client_name": client.get("name", ""),
        "phone": client["phone"],
        "telnyx_number": client.get("telnyx_number", ""),
        "status": client["status"],
        "claims_used": used,
        "claims_included": 50,
        "claims_remaining": max(0, 50 - used),
        "overage_claims": max(0, used - 50),
        "overage_cost": max(0, used - 50) * 75,
        "claims": claims
    }