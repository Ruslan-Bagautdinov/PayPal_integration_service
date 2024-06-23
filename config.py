from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())


PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com"  # Use https://api-m.paypal.com for live transactions
