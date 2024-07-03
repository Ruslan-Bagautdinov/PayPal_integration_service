from fastapi import APIRouter, Query, Path, HTTPException
from fastapi.responses import RedirectResponse
import requests
import logging

from config import PAYPAL_BASE_URL, PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET


router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_access_token():
    url = f"{PAYPAL_BASE_URL}/v1/oauth2/token"
    data = {"grant_type": "client_credentials"}
    response = requests.post(url,
                             data=data,
                             auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
    response.raise_for_status()
    return response.json().get("access_token")


@router.get("/paypal_payment_capture/{user_id}", description="""
Handle the PayPal payment capture process after the user approves the payment.
This endpoint is triggered when PayPal redirects the user to the specified return URL with a token and PayerID.
It captures the payment using the provided token and PayerID, ensuring the payment is correctly attributed to the payer.
After successfully capturing the payment, it redirects the user to a specified link.
""")
async def handle_payment_and_redirect(token: str = Query(...),
                                      user_id: str = Path(...),
                                      PayerID: str = Query(...)):

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
        logger.info(f"Full PayPal API response from /paypal_payment_capture/{user_id}")
        logger.info(f"{response.json()}")

        # Добавь свою логику для получения redirect_link для юзера по его user_id
        # redirect_link = get_redirect_link(user_id)

        redirect_link = 'https://www.example.com'

        return RedirectResponse(url=redirect_link)

    except requests.RequestException as e:
        logger.error(f"Error capturing payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
