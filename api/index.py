from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Pehle environment variable check karo, nahi mila to hardcoded use karo
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8773103265:AAHbmBnEnzsr5UfKy8AuQistP24eAxzeDfI')


def send_message(chat_id, text):
    """Telegram par wapas message bhejne ka function"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)


@app.route('/', methods=['POST', 'GET'])
def webhook():
    """
    POST  -> Telegram se aata hai (naya message)
    GET   -> Browser se check karne ke liye
    """
    if request.method == 'POST':
        update = request.get_json()

        if "message" in update:
            chat_id = update["message"]["chat"]["id"]
            user_name = update["message"]["chat"].get("first_name", "Dost")
            text = update["message"].get("text", "")

            # /start command handle karna
            if text == "/start":
                reply_text = (
                    f"ðŸ¤– *Namaste {user_name}!*\n\n"
                    f"Main aapka *AI Video Agent* hoon â€” abhi Phase 1 mein zinda ho gaya hoon! âœ…\n\n"
                    f"ðŸ“Œ *Aage kya hoga:*\n"
                    f"â€¢ Phase 2: Gemini se script likhwana\n"
                    f"â€¢ Phase 3: Automatic video banana\n"
                    f"â€¢ Phase 4: Auto-upload YouTube par\n\n"
                    f"Abhi ke liye koi bhi message bhejein â€” main echo karunga! ðŸš€"
                )
            else:
                reply_text = (
                    f"âœ… *Agent Active!*\n\n"
                    f"Aapne kaha: `{text}`\n\n"
                    f"_Phase 1 complete. Main instructions lene ke liye ready hoon!_ ðŸŽ¬"
                )

            send_message(chat_id, reply_text)

        return jsonify({"status": "ok"}), 200

    # Browser se GET request aaye to status dikhao
    return "âœ… Telegram Bot is LIVE on Vercel! Phase 1 Complete.", 200
