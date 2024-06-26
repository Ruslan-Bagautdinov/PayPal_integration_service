## To allow an application at www.example.com to create payments for customers and receive notifications when these payments are completed using the provided FastAPI app, follow these steps:

## Step 1: Set Up PayPal Developer Account and App

### Create a PayPal Developer Account:
1. Go to the [PayPal Developer website](https://developer.paypal.com/).
2. Log in with your PayPal account or create a new one.

### Create a PayPal App:
1. Navigate to the "My Apps & Credentials" section.
2. Click on "Create App" under the "REST API apps" section.
3. Fill in the required details and create the app. You will get a Client ID and Secret which are needed for API authentication.

## Step 2: Configure this FastAPI App

### Set Up Environment Variables:
1. Ensure that `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, and `PAYPAL_BASE_URL` are set in your environment or configuration file.

### Deploy this FastAPI App:
1. Deploy your FastAPI app to a server or cloud platform where it can be accessed by your application at www.example.com.

## Step 3: Integrate with Your Application

### Create a Payment:
1. Use the `/create-payment-link/` endpoint to create a payment.

**Example request:**
```http
POST /create-payment-link/
Content-Type: application/json

{
  "currency": "USD",
  "amount": 100.00
}
```
 **Example response:**
```
{
  "approval_url": "https://www.paypal.com/checkoutnow?token=ORDER-123456789",
  "order_id": "ORDER-123456789"
}
```
1. Redirect the customer to the approval_url received in the response to complete the payment.

### Check Payment Status:

1. Use the /check-payment-status/{order_id} endpoint to check the status of the payment.
**Example request:**
```http
GET /check-payment-status/ORDER-123456789
```
**Example response:**
```json
{
  "order_id": "ORDER-123456789",
  "status": "COMPLETED"
}
```

## Step 4: Set Up Webhook for Payment Notifications

### Create a Webhook:
1. Use the /create-webhook/ endpoint to create a webhook.

**Example request:**
```http
POST /create-webhook/?webhook_url=https://www.example.com/webhook-listener/
Content-Type: application/json
```
**Example response:**
```json
{
  "webhook_id": "WH-123456789",
  "message": "Webhook created successfully"
}
```
### Add endpoint into your app to handle webhook events:

**Example implementation on FastAPI:**
```python
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

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

        return {"order_id": order_id, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```
## Step 5: Test Your Integration
### Test in Sandbox Mode:
1. Use the PayPal sandbox to test your integration. Create sandbox accounts for buyers and sellers, and simulate payments.
### Go Live:
1.Once testing is complete and everything works as expected, switch your PayPal app to live mode and update your configuration.

By following these steps, you will enable your application at www.example.com to create payments for customers and receive notifications when these payments are completed using the provided FastAPI app.
