import os
import asyncio
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import google.generativeai as genai

app = Flask(__name__)

# Tokens â€” env variable ya hardcoded fallback
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8773103265:AAHbmBnEnzsr5UfKy8AuQistP24eAxzeDfI')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'PLACEHOLDER_KEY')

# Gemini AI setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')


def send_message(chat_id, text):
    """Telegram par text message bhejne ka function"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"send_message error: {e}")


def send_photo(chat_id, photo_url, caption=""):
    """Telegram par image bhejne ka function"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"send_photo error: {e}")


def send_audio(chat_id, audio_path):
    """Telegram par audio file bhejne ka function"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    try:
        with open(audio_path, 'rb') as audio:
            files = {'audio': audio}
            data = {'chat_id': chat_id}
            requests.post(url, files=files, data=data, timeout=30)
    except Exception as e:
        print(f"send_audio error: {e}")


# Removed edge-tts async function


@app.route('/', methods=['POST', 'GET'])
def webhook():
    """
    POST â†’ Telegram se aata hai (naya message)
    GET  â†’ Browser se check karne ke liye
    """
    if request.method == 'POST':
        update = request.get_json()

        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_name = update["message"]["chat"].get("first_name", "Dost")
            user_text = update["message"]["text"]

            # â”€â”€ /start command â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if user_text == "/start":
                reply = (
                    f"ðŸ¤– *Namaste {user_name}!* Welcome to *AI Video Agent* âœ…\n\n"
                    f"ðŸ“Œ *Main ye kar sakta hoon:*\n\n"
                    f"âœï¸ *Script banana:*\n"
                    f"Kuch bhi type karo â€” main YouTube script likhta hoon\n\n"
                    f"ðŸŽ¨ *Image banana:*\n"
                    f"`Image: [aapka topic]`\n"
                    f"_Example: Image: handsome male influencer on wall street_\n\n"
                    f"ðŸŽ™ï¸ *Voiceover banana:*\n"
                    f"`Audio: [jo bolna hai]`\n"
                    f"_Example: Audio: Welcome to this finance case study_\n\n"
                    f"ðŸš€ *Try karo abhi!*"
                )
                send_message(chat_id, reply)

            # â”€â”€ IMAGE command: "Image: ..." â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            elif user_text.lower().startswith("image:"):
                prompt = user_text[6:].strip()
                send_message(chat_id, "ðŸŽ¨ *Image generate ho rahi hai... 10-15 seconds wait karein*")
                formatted_prompt = prompt.replace(" ", "%20")
                image_url = (
                    f"https://image.pollinations.ai/prompt/{formatted_prompt}"
                    f"?width=1080&height=1920&nologo=true"
                )
                send_photo(chat_id, image_url, f"ðŸŽ¨ Visual: _{prompt}_")

            # â”€â”€ AUDIO command: "Audio: ..." â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            elif user_text.lower().startswith("audio:"):
                text_to_speak = user_text[6:].strip()
                if not text_to_speak:
                    send_message(chat_id, "âŒ Audio ke baad text likhein!\n_Example: Audio: Hello world_")
                else:
                    send_message(chat_id, "ðŸŽ™ï¸ *Voiceover render ho raha hai... thoda wait karein*")
                    audio_path = "/tmp/voiceover.mp3"
                    try:
                        from gtts import gTTS
                        tts = gTTS(text=text_to_speak, lang='en', tld='us') # US English voice
                        tts.save(audio_path)
                        send_audio(chat_id, audio_path)
                    except Exception as e:
                        send_message(chat_id, f"âŒ Audio error: `{str(e)}`")
                    finally:
                        if os.path.exists(audio_path):
                            os.remove(audio_path)

            # â”€â”€ DEFAULT: Script Generation (Gemini AI) â”€â”€â”€â”€â”€â”€â”€
            else:
                send_message(chat_id, "âœï¸ *Script generate ho rahi hai... Thoda wait karein* â³")
                prompt = f"""
Tu ek expert YouTube scriptwriter aur AI video producer hai.
User ne ye input diya hai: '{user_text}'

Topic, language aur duration samajhkar ek detailed video script de jisme 2 clear sections hon:

1. [VISUALS]: Screen par kya dikhega (AI image prompts, stock footage ideas, B-roll).
2. [VOICEOVER]: Audio mein kya bolna hai (user ki dI gayi language mein).

Script ko engaging, high-retention aur viral banao.
"""
                try:
                    response = model.generate_content(prompt)
                    bot_reply = response.text
                except Exception as e:
                    bot_reply = (
                        f"âŒ *Gemini AI Error:* `{str(e)}`\n\n"
                        f"_GEMINI\\_API\\_KEY check karein Vercel Settings mein._"
                    )
                send_message(chat_id, bot_reply)

        return jsonify({"status": "ok"}), 200

    # GET request â€” browser se status check
    return "âœ… AI Video Agent - Phase 3 Active! Script + Image + Audio ready!", 200
