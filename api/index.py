import os
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "1"
os.environ["GRPC_POLL_STRATEGY"] = "epoll1"

import traceback
from flask import Flask, request, jsonify

app = Flask(__name__)
error_message = None

try:
    import asyncio
    import requests
    import google.generativeai as genai
    import edge_tts
    import urllib.request
    import time
    import threading
    import subprocess
    import re
    import imageio_ffmpeg

    BOT_TOKEN = '8773103265:AAHbmBnEnzsr5UfKy8AuQistP24eAxzeDfI'
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyCVfexY2dUBwgg_sGyS2R1389mlkcShfSo')
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

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
                r = requests.post(url, files=files, data=data, timeout=60)
                if r.status_code != 200:
                    send_message(chat_id, f"❌ Video upload rejected by Telegram: {r.text}")
        except Exception as e:
            print(f"send_video error: {e}")
            send_message(chat_id, "❌ Video upload fail ho gaya.")

    def generate_audio(text, voice, output_path):
        communicate = edge_tts.Communicate(text, voice)
        asyncio.run(communicate.save(output_path))

    def make_video(image_paths, audio_path, output_path):
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        
        # Get duration using ffmpeg instead of moviepy to avoid grpc/epoll log parsing errors
        result = subprocess.run([ffmpeg_exe, '-i', audio_path], stderr=subprocess.PIPE, text=True)
        duration = 5.0 # default fallback
        match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", result.stderr)
        if match:
            h, m, s = match.groups()
            duration = int(h) * 3600 + int(m) * 60 + float(s)
            
        if duration <= 0:
            duration = 5.0

        n = len(image_paths)
        dur_per_img = duration / n
        frames = int(dur_per_img * 24)
        
        cmd = [ffmpeg_exe]
        for p in image_paths:
            cmd.extend(['-i', p])
        cmd.extend(['-i', audio_path])
        
        filters = []
        concat_inputs = ""
        for i in range(n):
            filters.append(f"[{i}:v]zoompan=z='zoom+0.0015':d={frames}:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=720x1280:fps=24[v{i}]")
            concat_inputs += f"[v{i}]"
            
        filters.append(f"{concat_inputs}concat=n={n}:v=1:a=0[outv]")
        filter_complex = ";".join(filters)
        
        cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '[outv]',
            '-map', f'{n}:a',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'stillimage',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            '-y',
            '-shortest',
            output_path
        ])
        
        subprocess.run(cmd, check=True)

    def process_video_request(chat_id, topic, script, voice, image_prompt):
        try:
            ts = str(int(time.time()))
            image_paths = []
            aud_path = f"/tmp/aud_{chat_id}_{ts}.mp3"
            vid_path = f"/tmp/vid_{chat_id}_{ts}.mp4"
            os.makedirs("/tmp", exist_ok=True)
            
            prompts = [
                f"{image_prompt} wide cinematic shot",
                f"{image_prompt} close up detailed",
                f"{image_prompt} epic lighting"
            ]
            
            for i, p in enumerate(prompts):
                img_path = f"/tmp/img_{chat_id}_{ts}_{i}.jpg"
                url = f"https://image.pollinations.ai/prompt/{p.replace(' ', '%20')}?width=720&height=1280&nologo=true&seed={int(time.time())+i}"
                img_response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                if img_response.status_code == 200:
                    with open(img_path, 'wb') as f:
                        f.write(img_response.content)
                    image_paths.append(img_path)
            
            if not image_paths:
                raise Exception("Images download fail ho gaya Pollinations se.")
            
            generate_audio(script, voice, aud_path)
            
            send_message(chat_id, f"⚙️ *Video render ho rahi hai ({len(image_paths)} images merge ho rahi hain)...* ⏳")
            make_video(image_paths, aud_path, vid_path)
            
            send_message(chat_id, "🚀 *Render successful! Video upload ho rahi hai...*")
            send_video(chat_id, vid_path)
            
            for path in image_paths + [aud_path, vid_path]:
                if os.path.exists(path):
                    os.remove(path)
        except Exception as e:
            send_message(chat_id, f"❌ Video Generation Error: {str(e)}")

except Exception as e:
    error_message = traceback.format_exc()
    print("CRITICAL IMPORT ERROR:\n" + error_message)

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if error_message:
        return f"<h1>Deployment Error</h1><pre>{error_message}</pre>"
        
    if request.method == 'POST':
        update = request.get_json()
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            print(f"Received message: '{user_text}' from chat_id: {chat_id}")
            
            if user_text == "/start":
                send_message(chat_id, "🤖 *Welcome to The Boss Level (Phase 4 & 5)!*\n\nNaya Video Banane ke liye type karein:\n`MakeVideo: [Topic]`\n\nVideo me Changes Karne ke liye type karein:\n`Edit: [Changes]`")
                return jsonify({"status": "ok"}), 200

            if user_text.lower().startswith("makevideo:"):
                topic = user_text[10:].strip()
                send_message(chat_id, f"🎬 *'{topic}' par kaam shuru...* (Render Server Active)")
                
                script_prompt = f"Write exactly ONE engaging sentence for a YouTube short about: {topic}"
                try:
                    script = model.generate_content(script_prompt).text.strip()
                except Exception as e:
                    script = f"Here is an amazing video about {topic}."
                
                user_sessions[chat_id] = {
                    "topic": topic, "script": script, "image_prompt": topic, "voice": "en-US-ChristopherNeural"
                }
                
                def bg_makevideo():
                    process_video_request(chat_id, topic, script, user_sessions[chat_id]["voice"], topic)
                    send_message(chat_id, "💡 *Tip:* Pasand nahi aaya? Aap changes karwa sakte hain! Likh kar bhejein: `Edit: Make the voice female` ya `Edit: Change image to a dark city`.")
                threading.Thread(target=bg_makevideo).start()

            elif user_text.lower().startswith("edit:"):
                if chat_id not in user_sessions:
                    send_message(chat_id, "❌ Pehle naya video banayein: `MakeVideo: [Topic]`")
                    return jsonify({"status": "ok"}), 200
                
                edit_instruction = user_text[5:].strip()
                session = user_sessions[chat_id]
                send_message(chat_id, "📝 *Aapke changes process ho rahe hain...*")
                
                if "female" in edit_instruction.lower() or "girl" in edit_instruction.lower() or "woman" in edit_instruction.lower():
                    session["voice"] = "en-US-AriaNeural"
                elif "male" in edit_instruction.lower() or "boy" in edit_instruction.lower() or "man" in edit_instruction.lower():
                    session["voice"] = "en-US-ChristopherNeural"
                
                ai_prompt = f"Current Script: {session['script']}\nCurrent Image Idea: {session['image_prompt']}\nUser requested change: '{edit_instruction}'\n\nProvide updated values in exactly this format:\nSCRIPT: [new engaging 1-sentence script]\nIMAGE_PROMPT: [new descriptive image prompt]"
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

                user_sessions[chat_id] = session
                
                def bg_editvideo():
                    process_video_request(chat_id, session["topic"], session["script"], session["voice"], session["image_prompt"])
                threading.Thread(target=bg_editvideo).start()

            else:
                send_message(chat_id, "🤖 Full MP4 Video banane ke liye type karein: `MakeVideo: [Aapka Topic]`")
            
        return jsonify({"status": "ok"}), 200
    
    return "Phase 5 Boss Level - Video Editor is Live!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
