from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TelnyxInbound(BaseModel):
    data: dict


class StripeEvent(BaseModel):
    type: str
    data: dict


class ClaimCreate(BaseModel):
    client_id: str
    claim_type: Optional[str] = None
    voice_note_url: Optional[str] = None
    photo_urls: Optional[List[str]] = None


class PortalResponse(BaseModel):
    client_name: Optional[str]
    phone: str
    claims_used: int
    claims_included: int
    claims: List[dict]