from fastapi import FastAPI, Request, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models import User, Transaction, Subscription
from nlp_engine import parse_expense
from utils import send_message, send_image, generate_pie_chart
import os
from datetime import datetime, timedelta

app = FastAPI()

# --- Startup ---
@app.on_event("startup")
async def start_db():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    await init_beanie(database=client.finance_bot, document_models=[User, Transaction, Subscription])

# --- Webhook Verification ---
@app.get("/webhook")
async def verify_webhook(request: Request):
    verify_token = os.getenv("VERIFY_TOKEN")
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == verify_token:
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
    return {"status": "ok"}

# --- Message Handling ---
@app.post("/webhook")
async def handle_message(request: Request):
    body = await request.json()
    
    if body.get("object") == "page":
        for entry in body.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event:
                    await process_user_message(event)
    return {"status": "received"}

async def process_user_message(event):
    psid = event["sender"]["id"]
    text = event["message"].get("text")
    
    if not text: return

    # Make sure user exits
    user = await User.find_one(User.psid == psid)
    if not user:
        user = User(psid=psid)
        await user.insert()
        send_message(psid, "Chao! I'm your Finance Assistance Bot. Try typing: 'KFC $30' or 'Limit 500'.")

    # Handle special commands "report"
    if "report" in text.lower():
        await send_weekly_report(psid)
        return

    # Send to NLP to analyze
    data = await parse_expense(text) # return JSON
    
    if not data:
        send_message(psid, "Sorry, I didn't catch that. Try: 'Item amount'.")
        return

    # Handle different types of inputs
    if data.get("type") == "set_limit":
        user.weekly_limit = float(data["amount"])
        await user.save()
        send_message(psid, f"Weekly limit set to ${user.weekly_limit}")

    elif data.get("type") == "add_sub":
        # Eg: "Add sub Netflix 15"
        sub = Subscription(
            psid=psid,
            service_name=data.get("item", "Unknown"),
            amount=data["amount"],
            next_billing_date=datetime.now() + timedelta(days=30)
        )
        await sub.insert()
        send_message(psid, f"Subscription added: {sub.service_name} (${sub.amount}/mo)")

    else: # Default to expense logging
        amount = float(data["amount"])
        
        # Save transaction
        await Transaction(
            psid=psid,
            amount=amount,
            category=data.get("category", "General"),
            item_name=data.get("item", "Unknown")
        ).insert()

        # Respond to user
        send_message(psid, f"Logged: {data.get('item')} (${amount}) - {data.get('category')}")

        # Check Budget Limit
        if user.weekly_limit > 0:
            await check_budget_alert(psid, user.weekly_limit)

async def check_budget_alert(psid, limit):
    # Find total transactions this week
    today = datetime.now()
    start_week = today - timedelta(days=today.weekday()) # Monday
    
    txs = await Transaction.find(
        Transaction.psid == psid,
        Transaction.date >= start_week
    ).to_list()
    
    total = sum(t.amount for t in txs)
    
    if total > limit:
        send_message(psid, f"ALERT: You've spent ${total}, exceeding your limit of ${limit}!")

async def send_weekly_report(psid):
    # Find transactions this month
    start_month = datetime.now().replace(day=1)
    txs = await Transaction.find(
        Transaction.psid == psid,
        Transaction.date >= start_month
    ).to_list()
    
    if not txs:
        send_message(psid, "No data found for this month.")
        return

    # Group by category
    cat_data = {}
    total = 0
    for t in txs:
        total += t.amount
        cat_data[t.category] = cat_data.get(t.category, 0) + t.amount

    # Send text report
    msg = f"Monthly Report:\nTotal: ${total}\n"
    for k, v in cat_data.items():
        msg += f"- {k}: ${v}\n"
    send_message(psid, msg)

    # Draw pie chart
    img_buf = generate_pie_chart(cat_data)
    send_image(psid, img_buf)