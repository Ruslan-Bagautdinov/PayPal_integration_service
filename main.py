from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
import requests
from typing import Optional
import os
import json

from config import (PAYPAL_CLIENT_ID,
                    PAYPAL_CLIENT_SECRET,
                    PAYPAL_BASE_URL,
                    BASE_DIR
                    )


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
    return_url: Optional[str] = None


# class WebhookRequest(BaseModel):
#     url: str
#     event_types: list


def get_access_token():
    url = f"{PAYPAL_BASE_URL}/v1/oauth2/token"
    data = {"grant_type": "client_credentials"}
    response = requests.post(url,
                             data=data,
                             auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
    response.raise_for_status()
    return response.json().get("access_token")


@app.get("/")
async def root():
    return RedirectResponse(url='/docs')



@app.post("/create-payment-link/", description="""
Create a payment link for the specified amount and currency. 
This endpoint facilitates the generation of a PayPal payment link, allowing users to securely complete transactions.
The response includes the PayPal approval URL, the unique order ID associated with the transaction, 
and the redirect URL where the customer will be redirected after approving the payment.
""")
async def create_payment_link(payment_request: PaymentRequest):
    """
    Create a payment link for the specified amount and currency.

    Args:
        payment_request (PaymentRequest): {"currency": str, "amount": float, "return_url": Optional[str]}

    Supported Currencies:
        - USD: United States Dollar
        - EUR: Euro
        - GBP: British Pound Sterling
        - CAD: Canadian Dollar
        - AUD: Australian Dollar
        - JPY: Japanese Yen
        - CNY: Chinese Yuan
        - INR: Indian Rupee
        - BRL: Brazilian Real
        - RUB: Russian Ruble
        - CHF: Swiss Franc
        - SEK: Swedish Krona
        - NZD: New Zealand Dollar
        - SGD: Singapore Dollar
        - HKD: Hong Kong Dollar
        - MXN: Mexican Peso
        - NOK: Norwegian Krone
        - DKK: Danish Krone
        - TRY: Turkish Lira
        - ZAR: South African Rand

    Returns:
        dict: A dictionary containing the PayPal approval URL, the order ID, and the redirect URL (if provided).

    Raises:
        HTTPException: If there is an error during the PayPal API request
         or if the approval URL is not found in the response.
    """
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

        if payment_request.return_url:
            payload["payment_source"] = {
                "paypal": {
                    "experience_context": {
                        "return_url": payment_request.return_url
                    }
                }
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

        redirect_url = payment_request.return_url if payment_request.return_url else None

        return {"approval_url": approval_url, "order_id": order_id, "redirect_url": redirect_url}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


# handler for fake completing payments in the sandbox

# @app.post("/capture-payment/")
# async def capture_payment_handler(order_id: str):
#     try:
#         access_token = get_access_token()
#         url = f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture"
#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {access_token}"
#         }
#         response = requests.post(url, headers=headers)
#         response.raise_for_status()
#         return response.json()
#     except requests.RequestException as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.get("/check-payment-status/{order_id}", description="""
Check the status of a PayPal payment order using the provided order ID.
This endpoint queries the PayPal API to retrieve the current status of a payment order, 
providing real-time information on whether the payment has been completed, authorized, or is still pending.
""")
async def check_payment_status(order_id: str):
    """
    Check the status of a PayPal payment order.

    Args:
        order_id (str): The unique identifier of the PayPal order.

    Returns:
        dict: A dictionary containing the order ID and its current status.

    Possible Statuses:
        - CREATED: The order has been created but not yet approved by the buyer.
        - SAVED: The order has been saved and is awaiting action.
        - APPROVED: The buyer has approved the order.
        - VOIDED: The order has been voided.
        - COMPLETED: The order has been successfully completed.

    Raises:
        HTTPException: If there is an error during the PayPal API request.
    """
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


@app.post("/create-webhook/", description="""
Create a webhook for the specified URL to receive CHECKOUT.ORDER.APPROVED events.
This endpoint allows you to set up a webhook that will notify your specified URL 
whenever a checkout order is approved on PayPal.
""")
async def create_webhook(webhook_url: str = Query(..., description="The URL where the webhook events will be sent")):
    """
    Create a webhook for the specified URL to receive CHECKOUT.ORDER.APPROVED events.

    Args:
        webhook_url (str): The URL where the webhook events will be sent.

    Returns:
        dict: A dictionary containing a success message and the webhook ID.

    Raises:
        HTTPException: If there is an error during the PayPal API request.
    """
    try:
        access_token = get_access_token()
        url = f"{PAYPAL_BASE_URL}/v1/notifications/webhooks"
        payload = {
            "url": webhook_url,
            "event_types": [
                {"name": "CHECKOUT.ORDER.APPROVED"}
            ]
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        return {"message": "Webhook created successfully!", "webhook_id": response.json().get("id")}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error creating webhook: {str(e)}")


@app.get("/list-webhooks", description="""
List all webhooks configured for the PayPal account.
This endpoint retrieves a list of all webhooks that have been set up for the account, 
including their URLs and the types of events they are configured to receive.
""")
async def list_webhooks_handler():
    """
    List all webhooks configured for the PayPal account.

    Returns:
        dict: A dictionary containing the list of webhooks.

    Raises:
        HTTPException: If there is an error during the PayPal API request.
    """
    try:
        access_token = get_access_token()
        url = f"{PAYPAL_BASE_URL}/v1/notifications/webhooks"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete-webhook/", description="""
Delete a webhook using the provided webhook ID.
This endpoint allows you to remove a previously created webhook from your PayPal account. 
Once deleted, the webhook will no longer receive any events.
""")
async def delete_webhook(webhook_id: str = Query(..., description="The ID of the webhook to be deleted")):
    """
    Delete a webhook using the provided webhook ID.

    Args:
        webhook_id (str): The unique identifier of the webhook to be deleted.

    Returns:
        dict: A dictionary containing a success message.

    Raises:
        HTTPException: If there is an error during the PayPal API request.
    """
    try:
        access_token = get_access_token()
        url = f"{PAYPAL_BASE_URL}/v1/notifications/webhooks/{webhook_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.delete(url, headers=headers)
        response.raise_for_status()

        return {"message": "Webhook deleted successfully!"}
    except requests.RequestException as e:
        if e.response:
            try:
                error_detail = e.response.json().get("details", [])
                error_message = ", ".join([detail.get("description", "") for detail in error_detail])
                raise HTTPException(status_code=e.response.status_code,
                                    detail=f"Error deleting webhook: {error_message}")
            except ValueError:
                # If the response is not JSON, fallback to the original error message
                pass
        raise HTTPException(status_code=500, detail=f"Error deleting webhook: {str(e)}")


@app.post("/webhook-listener/", description="""
Listen for incoming webhook events from PayPal.
This endpoint is designed to receive notifications from PayPal whenever a specified event occurs, 
such as a checkout order being approved.
It processes the incoming webhook payload and extracts relevant information.
""")
async def webhook_listener(request: Request):
    """
    Listen for incoming webhook events from PayPal.

    Args:
        request (Request): The incoming HTTP request containing the webhook payload.

    Returns:
        dict: A dictionary containing the order ID and the event type.

    Raises:
        HTTPException: If there is an error processing the webhook payload.
    """
    try:
        payload = await request.json()
        order_id = payload.get("resource", {}).get("id")
        status = payload.get("event_type")

        # if order_id and status:
        #     file_name = f"{order_id}_{status}.txt"
        #     file_path = os.path.join(BASE_DIR, "webhook_logs", file_name)
        #     os.makedirs(os.path.dirname(file_path), exist_ok=True)
        #     with open(file_path, "w") as file:
        #         file.write(str(payload))

        return {"order_id": order_id, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
