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
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    await init_beanie(database=client.finance_bot, document_models=[User, Transaction, Subscription])
    
    today = datetime.now()
    print(f"[{today}] Worker Checking Subscriptions...")
    
    # Find all subscriptions due today
    subs = await Subscription.find(
        Subscription.status == "active",
        Subscription.next_billing_date <= today
    ).to_list()
    
    if not subs:
        print("No subscriptions due today.")
        return

    for sub in subs:
        try:
            print(f"Charging: {sub.service_name} - ${sub.amount}")
            
            # Make the charge
            await Transaction(
                psid=sub.psid,
                amount=sub.amount,
                category="Subscription",
                item_name=sub.service_name + " (Auto)",
                date=today
            ).insert()
            
            # Update next billing date
            new_date = sub.next_billing_date + timedelta(days=30)
            
            # In case of delays, ensure next billing date is in the future
            if new_date < today:
                new_date = today + timedelta(days=30)

            sub.next_billing_date = new_date
            await sub.save()
            
            # Notify user
            send_message(sub.psid, f"Auto-renewed: {sub.service_name} (${sub.amount})")
            
        except Exception as e:
            print(f"Error processing {sub.service_name}: {e}")
