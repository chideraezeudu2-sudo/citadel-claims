import os
import uuid
from utils.supabase_client import supabase


async def upload_media(file_bytes: bytes, filename: str, bucket: str = "claim-media") -> str:
    """Upload media file to Supabase Storage and return public URL"""
    path = f"{uuid.uuid4()}/{filename}"
    
    supabase.storage.from_(bucket).upload(
        path,
        file_bytes,
        {"content-type": "application/octet-stream"}
    )
    
    url = supabase.storage.from_(bucket).get_public_url(path)
    return url


async def upload_pdf(pdf_path: str, claim_id: str) -> str:
    """Upload generated PDF to Supabase Storage and return public URL"""
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    path = f"estimates/{claim_id}/estimate.pdf"
    
    supabase.storage.from_("estimates").upload(
        path,
        pdf_bytes,
        {"content-type": "application/pdf"}
    )
    
    url = supabase.storage.from_("estimates").get_public_url(path)
    return url