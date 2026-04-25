import os
import asyncio
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip
import urllib.request
import time

app = Flask(__name__)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8773103265:AAHbmBnEnzsr5UfKy8AuQistP24eAxzeDfI')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyCVfexY2dUB' + 'wgg_sGyS2R1389mlkcShfSo')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 🧠 MEMORY: Ye bot ko yaad rakhne me madad karega (Phase 5)
user_sessions = {}

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            payload["parse_mode"] = ""
            requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"send_message error: {e}")

def send_video(chat_id, video_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, 'rb') as video:
            files = {'video': video}
            data = {'chat_id': chat_id}
            requests.post(url, files=files, data=data, timeout=60)
    except Exception as e:
        print(f"send_video error: {e}")
        send_message(chat_id, "❌ Video upload fail ho gaya. File size bahut bada ho sakta hai.")

async def generate_audio(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def make_video(image_path, audio_path, output_path):
    # MoviePy logic for Image + Audio -> MP4 Video
    audio_clip = AudioFileClip(audio_path)
    image_clip = ImageClip(image_path).set_duration(audio_clip.duration)
    video_clip = image_clip.set_audio(audio_clip)
    # Render with 24 fps and small size
    video_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

def process_video_request(chat_id, topic, script, voice, image_prompt):
    try:
        # Generate unique filenames based on timestamp to avoid conflicts
        ts = str(int(time.time()))
        img_path = f"/tmp/img_{chat_id}_{ts}.jpg"
        aud_path = f"/tmp/aud_{chat_id}_{ts}.mp3"
        vid_path = f"/tmp/vid_{chat_id}_{ts}.mp4"
        
        # Ensure /tmp exists (for local testing, Render handles it differently but safe)
        os.makedirs("/tmp", exist_ok=True)
        
        # 1. Image Download
        image_url = f"https://image.pollinations.ai/prompt/{image_prompt.replace(' ', '%20')}?width=1080&height=1920&nologo=true"
        urllib.request.urlretrieve(image_url, img_path)
        
        # 2. Audio Generate
        asyncio.run(generate_audio(script, voice, aud_path))
        
        # 3. Video Merge (FFmpeg/MoviePy)
        send_message(chat_id, "⚙️ *Video render ho rahi hai (Audio aur Image merge ho rahe hain)...* ⏳")
        make_video(img_path, aud_path, vid_path)
        
        # 4. Upload to Telegram
        send_message(chat_id, "🚀 *Render successful! Video upload ho rahi hai...*")
        send_video(chat_id, vid_path)
        
        # Cleanup storage
        for path in [img_path, aud_path, vid_path]:
            if os.path.exists(path):
                os.remove(path)
                
    except Exception as e:
        send_message(chat_id, f"❌ Video Generation Error: {str(e)}")

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        update = request.get_json()
        
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            
            if user_text == "/start":
                send_message(chat_id, "🤖 *Welcome to The Boss Level (Phase 4 & 5)!*\n\nNaya Video Banane ke liye type karein:\n`MakeVideo: [Topic]`\n\nVideo me Changes Karne ke liye type karein:\n`Edit: [Changes]`")
                return jsonify({"status": "ok"}), 200

            # 🟢 COMMAND 1: Naya Video Banana
            if user_text.lower().startswith("makevideo:"):
                topic = user_text[10:].strip()
                send_message(chat_id, f"🎬 *'{topic}' par kaam shuru...* (Render Server Active)")
                
                script_prompt = f"Write exactly ONE engaging sentence for a YouTube short about: {topic}"
                try:
                    script = model.generate_content(script_prompt).text.strip()
                except Exception as e:
                    script = f"Here is an amazing video about {topic}."
                
                # Save default settings in memory for this user
                user_sessions[chat_id] = {
                    "topic": topic,
                    "script": script,
                    "image_prompt": topic,
                    "voice": "en-US-ChristopherNeural" # Default Male
                }
                
                process_video_request(chat_id, topic, script, user_sessions[chat_id]["voice"], topic)
                send_message(chat_id, "💡 *Tip:* Pasand nahi aaya? Aap changes karwa sakte hain! Likh kar bhejein: `Edit: Make the voice female` ya `Edit: Change image to a dark city`.")

            # 🟡 COMMAND 2: Video ko Edit Karna (Memory Based Iteration)
            elif user_text.lower().startswith("edit:"):
                if chat_id not in user_sessions:
                    send_message(chat_id, "❌ Pehle naya video banayein: `MakeVideo: [Topic]`")
                    return jsonify({"status": "ok"}), 200
                
                edit_instruction = user_text[5:].strip()
                session = user_sessions[chat_id]
                send_message(chat_id, "📝 *Aapke changes process ho rahe hain...*")
                
                # Update voice based on keywords
                if "female" in edit_instruction.lower() or "girl" in edit_instruction.lower() or "woman" in edit_instruction.lower():
                    session["voice"] = "en-US-AriaNeural"
                elif "male" in edit_instruction.lower() or "boy" in edit_instruction.lower() or "man" in edit_instruction.lower():
                    session["voice"] = "en-US-ChristopherNeural"
                
                # AI se script aur image prompt update karwana
                ai_prompt = f"""
                Current Script: {session['script']}
                Current Image Idea: {session['image_prompt']}
                User requested change: '{edit_instruction}'
                
                Provide updated values in exactly this format:
                SCRIPT: [new engaging 1-sentence script]
                IMAGE_PROMPT: [new descriptive image prompt]
                """
                try:
                    ai_response = model.generate_content(ai_prompt).text
                    lines = ai_response.split('\n')
                    for line in lines:
                        if line.startswith("SCRIPT:"):
                            session['script'] = line.replace("SCRIPT:", "").strip()
                        elif line.startswith("IMAGE_PROMPT:"):
                            session['image_prompt'] = line.replace("IMAGE_PROMPT:", "").strip()
                except Exception as e:
                    send_message(chat_id, "⚠️ AI instruction theek se nahi samajh paya, par main manual try kar raha hu.")

                # Update memory aur naya video banana
                user_sessions[chat_id] = session
                process_video_request(chat_id, session["topic"], session["script"], session["voice"], session["image_prompt"])

            else:
                send_message(chat_id, "🤖 Full MP4 Video banane ke liye type karein: `MakeVideo: [Aapka Topic]`")
            
        return jsonify({"status": "ok"}), 200
    
    return "Phase 5 Boss Level - Video Editor is Live!"
