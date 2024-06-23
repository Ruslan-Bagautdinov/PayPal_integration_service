from fastapi import FastAPI, HTTPException, Request

app = FastAPI()


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
