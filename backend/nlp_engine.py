from openai import OpenAI
import os
import json
from datetime import datetime

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def parse_expense(text: str):
    prompt = f"""
    ### ROLE
    You are a strict data parsing assistant. Your goal is to extract structured financial data from the input text and output valid JSON.

    ### INPUT TEXT
    "{text}"

    ### STRICT RULES (Follow strictly)
    1.  **Language**: The output values must be in **ENGLISH ONLY**. If the input contains Vietnamese (e.g., "Gạo", "Quà"), translate it to English (e.g., "Rice", "Gift").
    2.  **Item Name (`item`)**: 
        -   Extract the specific product or service.
        -   **CRITICAL**: Never return "None", "Unknown", or null. If the text is "Uber 5$", the item is "Uber".
    3.  **Logic for `type`**:
        -   `set_limit`: If text implies setting a budget (keywords: "Limit", "Budget", "Hạn mức").
        -   `add_sub`: If text implies a recurring payment (keywords: "Sub", "Netflix", "mỗi tháng", "hàng tháng", "/mo", "monthly").
        -   `expense`: All other one-time purchases.
    4.  **Category**: Infer strictly from this list: [Food/Dining, Living/Utilities, Transport, Shopping, Entertainment, Health, Special Occasion, Subscription].
    5.  **Amount & Currency**:
        -   Extract numeric amount only. If the text is "5$", amount is 5.
        -   Detect symbols ($, €, VND, đ). Default to "USD" if strictly ambiguous. Note: "k" usually means thousand VND in Vietnamese context (e.g., 50k = 50000 VND, but you have to convert all currency into USD), if input is just "300$", keep it 300 USD.
    ### FEW-SHOT EXAMPLES
    Input: "Quà cho bạn gái 300$"
    Output: {{"type": "expense", "item": "Gift for girlfriend", "amount": 300, "currency": "USD", "category": "Shopping"}}

    Input: "Uber 5$"
    Output: {{"type": "expense", "item": "Uber", "amount": 5, "currency": "USD", "category": "Transport"}}

    Input: "Digital ocean 4$ tiền vps mỗi tháng"
    Output: {{"type": "add_sub", "item": "Digital Ocean VPS", "amount": 4, "currency": "USD", "category": "Subscription"}}

    Input: "gạo 5$"
    Output: {{"type": "expense", "item": "Rice", "amount": 5, "currency": "USD", "category": "Food/Dining"}}

    ### OUTPUT FORMAT
    Return ONLY the raw JSON object. No markdown formatting, no explanations.
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