from celery import Celery
from celery.schedules import crontab
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models import Subscription, Transaction, User
from utils import send_message
from datetime import datetime, timedelta

app = Celery('tasks', broker=os.getenv("REDIS_URL"))

# Database in Worker
async def init_db():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    await init_beanie(database=client.finance_bot, document_models=[User, Transaction, Subscription])

# Schedule: Every morning at 9AM
app.conf.beat_schedule = {
    'check-subscriptions-daily': {
        'task': 'worker.process_subscriptions',
        'schedule': crontab(hour=9, minute=0),
    },
}

@app.task
def process_subscriptions():
    """Wrapper for the async function to run in Celery."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_and_charge_subs())

async def check_and_charge_subs():
    await init_db()
    today = datetime.now()
    # Find sub due today
    # Logic: loop through active subs
    async for sub in Subscription.find(Subscription.status == "active"):
        if sub.next_billing_date.day == today.day:
            # Create transaction
            await Transaction(
                psid=sub.psid,
                amount=sub.amount,
                category="Subscription",
                item_name=sub.service_name,
                date=today
            ).insert()
            
            # Update next billing date (just plus 30 days)
            sub.next_billing_date = today + timedelta(days=30)
            await sub.save()
            
            # Alert to user
            send_message(sub.psid, f"Auto-logged subscription: {sub.service_name} (${sub.amount})")