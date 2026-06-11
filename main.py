from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import sms, stripe_webhooks, portal
from dotenv import load_dotenv
import os
import stripe

load_dotenv()

app = FastAPI(title="Citadel Claims API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sms.router)
app.include_router(stripe_webhooks.router)
app.include_router(portal.router)


@app.get("/")
async def root():
    return {"status": "Citadel Claims API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    """Create a Stripe checkout session for subscription"""
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    body = await request.json()
    phone = body.get("phone", "")
    
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{"price": os.getenv("STRIPE_PRICE_ID"), "quantity": 1}],
        success_url=f"{os.getenv('PORTAL_BASE_URL')}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{os.getenv('PORTAL_BASE_URL')}",
        metadata={"phone": phone},
        phone_number_collection={"enabled": True}
    )
    
    return {"url": session.url}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))