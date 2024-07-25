from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
import requests
from typing import Optional
from loguru import logger

from config import (PAYPAL_CLIENT_ID,
                    PAYPAL_CLIENT_SECRET,
                    PAYPAL_BASE_URL,
                    RETURN_BASE,
                    RETURN_ENDPOINT
                    )

app = FastAPI(
    title="PayPal Integration Service",
    description="""
    A FastAPI service to integrate PayPal payment processing into your application.
    This service provides endpoints to create payment links, handle payment captures,
    check payment statuses, manage webhooks, and listen for webhook events.
    """,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.add("app.log", rotation="500 MB")


class PaymentRequest(BaseModel):
    currency: str
    amount: float
    service_id: Optional[str] = None


def get_access_token():
    """
    Obtain an access token from PayPal using client credentials.

    Returns:
        str: The access token.

    Raises:
        HTTPException: If there is an error during the PayPal API request.
    """
    url = f"{PAYPAL_BASE_URL}/v1/oauth2/token"
    data = {"grant_type": "client_credentials"}
    response = requests.post(url,
                             data=data,
                             auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
    response.raise_for_status()
    return response.json().get("access_token")


@app.get("/", include_in_schema=False)
async def root():
    """
    Redirect to the API documentation.
    """
    return RedirectResponse(url='/docs')


@app.post("/create-payment-link/", description="""
Create a PayPal payment link for the specified currency and amount.
This endpoint generates a PayPal payment link that can be used to initiate a payment.
The payment link includes a return URL that redirects the user after payment approval.
""")
async def create_payment_link(payment_request: PaymentRequest):
    """
    Create a PayPal payment link.

    Args:
        payment_request (PaymentRequest): The payment details including currency, amount, and service ID.

    Returns:
        dict: A dictionary containing the approval URL, order ID, and return URL.

    Raises:
        HTTPException: If there is an error during the PayPal API request.
    """
    try:
        access_token = get_access_token()
        url = f"{PAYPAL_BASE_URL}/v2/checkout/orders"

        return_url = f"{RETURN_BASE}{RETURN_ENDPOINT}{payment_request.service_id}"

        logger.info(f"Creating payment link for service_id: {payment_request.service_id}, return_url: {return_url}")

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": payment_request.currency,
                        "value": str(payment_request.amount)
                    }
                }
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "return_url": return_url,
                    }
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

        logger.info(f"Order_id: {order_id} full PayPal API response from /create-payment-link/")
        logger.info(f"{response.json()}")

        approval_url = next((link["href"] for link in response.json().get("links") if link["rel"] == "approve"), None)
        if not approval_url:
            approval_url = next((link["href"] for link in response.json().get("links") if link["rel"] == "payer-action"), None)

        if not approval_url:
            raise HTTPException(status_code=500, detail="Approval URL not found in PayPal response")

        return {"approval_url": approval_url, "order_id": order_id, "return_url": return_url}
    except requests.RequestException as e:
        logger.error(f"Error creating payment link: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/paypal_payment_capture/{service_id}", description="""
Handle the PayPal payment capture process after the user approves the payment.
This endpoint is triggered when PayPal redirects the user to the specified return URL with a token and PayerID.
It captures the payment using the provided token and PayerID, ensuring the payment is correctly attributed to the payer.
After successfully capturing the payment, it redirects the user to a specified link.
""")
async def handle_payment_and_redirect(token: str = Query(...),
                                      service_id: str = Path(...),
                                      PayerID: str = Query(...)):
    """
    Capture the PayPal payment and redirect the user.

    Args:
        token (str): The payment token.
        service_id (str): The service ID associated with the payment.
        PayerID (str): The PayerID provided by PayPal.

    Returns:
        RedirectResponse: A redirect response to the specified link.

    Raises:
        HTTPException: If there is an error during the PayPal API request.
    """
    try:
        access_token = get_access_token()
        url = f"{PAYPAL_BASE_URL}/v2/checkout/orders/{token}/capture"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        payload = {
            "payer": {
                "payer_id": PayerID
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        logger.info(f"Payment captured for token: {token}, PayerID: {PayerID}")
        logger.info(f"Full PayPal API response from /paypal_payment_capture/{service_id}")
        logger.info(f"{response.json()}")

        redirect_link = 'https://www.example.com'

        return RedirectResponse(url=redirect_link)

    except requests.RequestException as e:
        logger.error(f"Error capturing payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/check-payment-status/{order_id}", description="""
Check the status of a PayPal payment order using the provided order ID.
This endpoint queries the PayPal API to retrieve the current status of a payment order, 
providing real-time information on whether the payment has been completed, authorized, or is still pending.
""")
async def check_payment_status(order_id: str):
    """
    Check the status of a PayPal payment order.

    Args:
        order_id (str): The order ID of the payment.

    Returns:
        dict: A dictionary containing the order ID and its status.

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

        logger.info(f"Order_id: {order_id} full PayPal API response from /check-payment-status/")
        logger.info(f"{response.json()}")

        return {"order_id": order_id, "status": order_status}
    except requests.RequestException as e:
        logger.error(f"Error checking payment status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create-webhook/", description="""
Create a webhook for the specified URL to receive CHECKOUT.ORDER.APPROVED events.
This endpoint allows you to set up a webhook that will notify your specified URL 
whenever a checkout order is approved on PayPal.
""")
async def create_webhook(webhook_url: str = Query(..., description="The URL where the webhook events will be sent")):
    """
    Create a PayPal webhook.

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
    List all PayPal webhooks.

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
    Delete a PayPal webhook.

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
    Listen for incoming PayPal webhook events.

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

        return {"order_id": order_id, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))