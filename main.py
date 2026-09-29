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
            **(headers or {}),
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
            "instructions": (
                "You are PouriaSun's Persian customer support assistant. "
                "Always answer in Persian unless the customer uses another language. "
                "Be concise, professional and helpful. "
                "PouriaSun works with solar energy systems, solar inverters, "
                "hybrid and off-grid systems, lithium batteries and energy storage. "
                "Never invent prices, stock availability, warranty terms, "
                "or exact technical specifications. "
                "If information is uncertain, tell the customer that it needs "
                "confirmation from PouriaSun support."
            ),
            "input": text,
            "max_output_tokens": 500,
        },
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
    )

    # Extract text safely from Responses API
    for item in result.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return content.get("text", "")

    return "متأسفانه فعلاً نتونستم پاسخ مناسبی آماده کنم."


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
    return jsonify({
        "status": "ok",
        "service": "PouriaSun Telegram Bot"
    })


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

        try:
            send_telegram(
                chat_id,
                "در حال حاضر ارتباط با هوش مصنوعی با مشکل مواجه شده. "
                "لطفاً کمی بعد دوباره امتحان کنید."
            )
        except Exception:
            pass

    return jsonify({"ok": True})


@app.get("/setup-webhook")
def setup_webhook():
    webhook_url = (
        "https://pouriasun-telegram-bot.vercel.app/api/telegram"
    )

    try:
        result = post_json(
            f"{TELEGRAM_API}/setWebhook",
            {
                "url": webhook_url,
                "drop_pending_updates": True,
            },
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
        }), 500
