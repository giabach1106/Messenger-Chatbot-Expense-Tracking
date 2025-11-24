import os
import requests
import matplotlib.pyplot as plt
import io

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

def send_message(psid, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": psid},
        "message": {"text": text}
    }
    requests.post(url, json=payload)

def send_image(psid, image_buffer):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    
    data = {
        'recipient': f'{{"id":"{psid}"}}',
        'message': '{"attachment":{"type":"image", "payload":{}}}'
    }
    files = {
        'filedata': ('chart.png', image_buffer, 'image/png')
    }
    requests.post(url, data=data, files=files)

def generate_pie_chart(data_dict):
    """Data format: {'Food': 100, 'Rent': 500}"""
    labels = list(data_dict.keys())
    sizes = list(data_dict.values())

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf