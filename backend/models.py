from typing import Optional
from beanie import Document
from pydantic import BaseModel
from datetime import datetime

class User(Document):
    psid: str # Facebook User ID
    weekly_limit: float = 0.0
    currency: str = "USD"
    created_at: datetime = datetime.now()

    class Settings:
        name = "users"

class Transaction(Document):
    psid: str
    amount: float
    category: str
    item_name: str
    date: datetime = datetime.now()

    class Settings:
        name = "transactions"

class Subscription(Document):
    psid: str
    service_name: str
    amount: float
    next_billing_date: datetime
    status: str = "active"

    class Settings:
        name = "subscriptions"