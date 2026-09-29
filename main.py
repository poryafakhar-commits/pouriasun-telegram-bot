import os
import json
import urllib.request
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def post_json(url, data, headers=None):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            **(headers or {})
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def ask_openai(text):
    result = post_json(
        "https://api.openai.com/v1/responses",
        {
            "model": "gpt-5.6-luna",
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are PouriaSun's Persian customer support assistant. "
                        "Answer in Persian, clearly, briefly and professionally. "
                        "PouriaSun works in solar energy, solar inverters, "
                        "lithium batteries and energy storage systems. "
                        "If you are unsure about price, stock, warranty or exact "
                        "technical specifications, say that it should be confirmed "
                        "with PouriaSun support. Never invent product information."
                    ),
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            "max_output_tokens": 500,
        },
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
    )

    return result.get("output_text", "متأسفانه فعلاً نتونستم پاسخ مناسبی آماده کنم.")


def send_telegram(chat_id, text):
    return post_json(
        f"{TELEGRAM_API}/sendMessage",
        {
            "chat_id": chat_id,
            "text": text[:4000],
        },
    )


@app.get("/")
def home():
    return {
        "status": "ok",
        "service": "PouriaSun Telegram Bot"
    }


@app.post("/api/telegram")
def telegram_webhook():
    update = request.get_json(silent=True) or {}

    message = update.get("message", {})
    chat = message.get("chat", {})
    text = message.get("text")

    if not text or not chat.get("id"):
        return jsonify({"ok": True})

    chat_id = chat["id"]

    try:
        reply = ask_openai(text)
        send_telegram(chat_id, reply)
    except Exception as e:
        print("ERROR:", str(e))
        send_telegram(
            chat_id,
            "در حال حاضر ارتباط با هوش مصنوعی با مشکل مواجه شده. لطفاً کمی بعد دوباره امتحان کنید."
        )

    return jsonify({"ok": True})
