from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

SECRET_KEY = os.getenv("SECRET_KEY")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_BASE_URL = os.getenv("PAYPAL_BASE_URL")

RETURN_BASE = os.getenv("RETURN_BASE")
RETURN_ENDPOINT = os.getenv("RETURN_ENDPOINT")

"""
Supported Currencies:

USD - United States Dollar
EUR - Euro
GBP - British Pound Sterling
CAD - Canadian Dollar
AUD - Australian Dollar
JPY - Japanese Yen
CNY - Chinese Yuan
INR - Indian Rupee
BRL - Brazilian Real
RUB - Russian Ruble
CHF - Swiss Franc
SEK - Swedish Krona
NZD - New Zealand Dollar
SGD - Singapore Dollar
HKD - Hong Kong Dollar
MXN - Mexican Peso
NOK - Norwegian Krone
DKK - Danish Krone
TRY - Turkish Lira
ZAR - South African Rand
"""
