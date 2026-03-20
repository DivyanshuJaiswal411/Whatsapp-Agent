from flask import Flask, request
import os
import random
import time
import json
import threading
import schedule
from datetime import datetime
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from google import genai

# 🔐 LOAD ENV
load_dotenv()

# 🔑 API CLIENTS
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"   # Twilio sandbox
YOUR_GF_NUMBER = "whatsapp:+917482899942"         

app = Flask(__name__)

# 💾 MEMORY FILE
MEMORY_FILE = "memory.json"

if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r") as f:
        chat_memory = json.load(f)
else:
    chat_memory = {}

def save_memory():
    with open(MEMORY_FILE, "w") as f:
        json.dump(chat_memory, f)

# 💙 CONTEXT
USER_CONTEXT = """
She loves traveling.
Favourite foods: pav bhaji, tiramisu, cadbury, chizzi.

Friends:
Komal, Sakshi → dislike (light teasing allowed)
Junaid, Prarthna di, Aryan Bhaiya, Arun Bhaiya

If rude → she is bored or hungry → be funny
"""

# 💙 PERSONALITY
PERSONA = """
You are a loving boyfriend-like assistant.

Call her "bubu" naturally ❤️

Style:
- Hinglish
- Chill, witty, slightly teasing 😏
- Short messages + fillers

Behavior:
- Sad → comfort
- Bored → random topics
- Rude → funny distraction
- Happy → match energy

Never sound like AI.
"""

# 🧠 EMOTION DETECTION
def detect_emotion(msg):
    msg = msg.lower()

    if any(w in msg for w in ["sad", "cry", "upset"]):
        return "sad"
    elif any(w in msg for w in ["angry", "irritated"]):
        return "angry"
    elif len(msg) < 5 or msg in ["ok", "k", "hmm"]:
        return "bored"
    elif any(w in msg for w in ["happy", "excited"]):
        return "happy"
    else:
        return "neutral"

# ⏳ DELAY
def human_delay(text):
    delay = min(len(text) * 0.03, 2.5)
    delay += random.uniform(0.5, 1.2)
    time.sleep(delay)

# 🎲 RANDOM CONTENT
random_topics = [
    "aaj class me kya scene tha?",
    "khana khaya ya phir ignore kiya 😏",
    "weather kitna random ho gaya hai 😭",
    "kal travel karna ho toh kaha jaogi?",
    "koi gossip hai kya 👀"
]

teasing = [
    "Komal fir kuch bakwas kar rahi thi kya 😭",
    "Sakshi ka drama chalu hai kya 😏"
]

# 💬 REPLY FUNCTION
def get_reply(user_msg, user_id):
    try:
        emotion = detect_emotion(user_msg)

        if user_id not in chat_memory:
            chat_memory[user_id] = []

        chat_memory[user_id].append(f"User: {user_msg}")
        history = "\n".join(chat_memory[user_id][-10:])

        hour = datetime.now().hour
        if hour < 12:
            time_context = "morning"
        elif hour < 18:
            time_context = "afternoon"
        else:
            time_context = "night"

        extra = ""

        if emotion == "bored":
            extra += random.choice(random_topics) + "\n"

        if emotion == "angry":
            extra += "User rude → distract playfully\n"

        if random.random() < 0.3:
            extra += random.choice(teasing) + "\n"

        prompt = f"""
{PERSONA}

{USER_CONTEXT}

Time: {time_context}
Emotion: {emotion}

{extra}

Conversation:
{history}

Reply:
"""

        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        reply = response.text

        # nickname
        if random.random() < 0.3:
            reply += "\n\nwaise bubu ❤️"

        chat_memory[user_id].append(f"Bot: {reply}")
        save_memory()

        return reply

    except Exception as e:
        import traceback
        print("🔥 FULL ERROR BELOW 🔥")
        traceback.print_exc()
        return "arey bubu thoda glitch ho gaya 😭"

# 📤 SEND MESSAGE
def send_whatsapp_message(text):
    try:
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=text,
            to=YOUR_GF_NUMBER
        )
        print("Sent:", text)
    except Exception as e:
        print("Send error:", e)

# 🧠 PROACTIVE MESSAGE
def generate_proactive_message():
    try:
        history = "\n".join(chat_memory.get("proactive", [])[-10:])

        prompt = f"""
{PERSONA}

{USER_CONTEXT}

Conversation:
{history}

Send a short natural Hinglish message.
"""

        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        return response.text

    except:
        return "kya kar rhi ho bubu 😏"

# ⏰ SCHEDULED TASKS
def morning():
    send_whatsapp_message("Good morning bubu ☀️❤️")

def afternoon():
    send_whatsapp_message(generate_proactive_message())

def evening():
    send_whatsapp_message(generate_proactive_message())

def night():
    send_whatsapp_message("soyi nahi abhi tak bubu 😭")

# 📅 SCHEDULE
schedule.every().day.at("09:30").do(morning)
schedule.every().day.at("14:30").do(afternoon)
schedule.every().day.at("19:00").do(evening)
schedule.every().day.at("23:00").do(night)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(30)

threading.Thread(target=run_scheduler, daemon=True).start()

# 📱 WEBHOOK
@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    incoming_msg = request.form.get("Body")
    user_id = request.form.get("From")

    reply = get_reply(incoming_msg, user_id)

    human_delay(reply)

    resp = MessagingResponse()
    resp.message(reply)

    return str(resp)

# 🚀 RUN
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
