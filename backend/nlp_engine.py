from openai import OpenAI
import os
import json
from datetime import datetime

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def parse_expense(text: str):
    prompt = f"""
    Analyze the following text: "{text}".
    Extract: item_name, amount, currency.
    Infer category from: [Food/Dining, Living/Utilities, Transport, Shopping, Entertainment, Health, Special Occasion, Subscription].
    If it's a limit setting (e.g., "Limit 500"), set type to "set_limit".
    If it's a subscription (e.g., "Add sub Netflix 15"), set type to "add_sub".
    Return JSON only.
    Example Output: {{"type": "expense", "item": "kfc", "amount": 30, "currency": "USD", "category": "Food/Dining"}}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial assistant API that outputs strict JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"NLP Error: {e}")
        return None