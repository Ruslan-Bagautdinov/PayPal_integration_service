from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

import secrets
from pydantic import BaseModel
import requests

from config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_BASE_URL



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PaymentRequest(BaseModel):
    currency: str
    amount: float


class WebhookRequest(BaseModel):
    url: str
    event_types: list


def get_access_token():
    url = f"{PAYPAL_BASE_URL}/v1/oauth2/token"
    data = {"grant_type": "client_credentials"}
    response = requests.post(url, data=data, auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET), headers={"Content-Type": "application/x-www-form-urlencoded"})
    response.raise_for_status()
    return response.json().get("access_token")


@app.middleware("http")
async def csrf_protection(request: Request, call_next):
    if request.method in ["POST", "PUT", "DELETE"]:
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token or csrf_token != request.session.get("csrf_token"):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
    response = await call_next(request)
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = secrets.token_hex(32)
    return response

@app.post("/create-payment-link/")
async def create_payment_link(payment_request: PaymentRequest):
    try:
        access_token = get_access_token()
        url = f"{PAYPAL_BASE_URL}/v2/checkout/orders"
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": payment_request.currency,
                        "value": str(payment_request.amount)
                    }
                }
            ]
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        order_id = response.json().get("id")
        approval_url = next((link["href"] for link in response.json().get("links") if link["rel"] == "approve"), None)
        if not approval_url:
            raise HTTPException(status_code=500, detail="Approval URL not found in PayPal response")
        return {"approval_url": approval_url, "order_id": order_id}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/check-payment-status/{order_id}")
async def check_payment_status(order_id: str):
    try:
        access_token = get_access_token()
        url = f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        order_status = response.json().get("status")
        return {"order_id": order_id, "status": order_status}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create-webhook/")
async def create_webhook(webhook_request: WebhookRequest):
    try:
        access_token = get_access_token()
        url = f"{PAYPAL_BASE_URL}/v1/notifications/webhooks"
        payload = {
            "url": webhook_request.url,
            "event_types": [{"name": event_type} for event_type in webhook_request.event_types]
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        webhook_id = response.json().get("id")
        return {"webhook_id": webhook_id, "message": "Webhook created successfully"}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook-listener/")
async def webhook_listener(request: Request):
    try:
        payload = await request.json()
        event_type = payload.get("event_type")
        if event_type == "CHECKOUT.ORDER.APPROVED":
            order_id = payload.get("resource", {}).get("id")
            # Handle the approved order as needed
            return {"status": "success", "message": f"Order {order_id} approved"}
        else:
            return {"status": "ignored", "message": f"Event type {event_type} ignored"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def forward_webhook_event(payload):
    webhook_id = payload.get("webhook_id")
    # Look up the application's webhook URL based on the webhook ID
    application_webhook_url = get_application_webhook_url(webhook_id)
    if application_webhook_url:
        response = requests.post(application_webhook_url, json=payload)
        response.raise_for_status()
    else:
        raise HTTPException(status_code=404, detail="Webhook ID not found")


def get_application_webhook_url(webhook_id):
    # Implement logic to look up the application's webhook URL based on the webhook ID
    # This could involve querying a database or a configuration file
    pass
