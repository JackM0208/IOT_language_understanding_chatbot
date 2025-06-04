import requests
import threading
import time
import tkinter as tk
import json
import random
import re
import winsound
import pygame
from tkinter import scrolledtext

# CLU 
endpoint = "https://iot-language-understanding.cognitiveservices.azure.com/"
api_key = "**********************************************************************"
project = "smart-timer"
deployment = "version3"
language = "en"

awaiting_remind_task = False
awaiting_remind_time = False
temp_remind_task = None
temp_remind_time = None
awaiting_timer_duration = False

def send_to_clu(text):
    url = f"{endpoint}language/:analyze-conversations?api-version=2023-04-01"
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Content-Type": "application/json"
    }

    body = {
        "kind": "Conversation",
        "analysisInput": {
            "conversationItem": {
                "id": "1",
                "participantId": "user",
                "modality": "text",
                "language": language,
                "text": text
            }
        },
        "parameters": {
            "projectName": project,
            "deploymentName": deployment,
            "verbose": True
        }
    }
    response = requests.post(url, headers=headers, json=body)
    return response.json()
    
    #print("Status code:", response.status_code)
    #print("Raw response:", response.text)
    #print(json.dumps(result, indent=2)) #in ra tỉ lệ tự tin của intent
def run_timer(minutes, seconds):
    total_seconds = minutes * 60 + seconds
    print(f"Timer started for {minutes} minutes and {seconds} seconds.")

    time.sleep(total_seconds)

    # Khi timer hết, thêm tin nhắn vào chat_area
    chat_area.insert(tk.END, f"\n⏰ Reminder: JUST DO IT!!!")

def extract_seconds(text):
    text = text.lower()
    match = re.search(r'(\d+)\s*second', text)
    if match:
        return int(match.group(1))
    match = re.search(r'(\d+)\s*minute', text)
    if match:
        return int(match.group(1)) * 60
    return 0  # mặc định 0 giây nếu không match

def play_sound(filename):
    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()

def get_bot_response(user_input):
    global awaiting_timer_duration
    global awaiting_remind_task, awaiting_remind_time
    global temp_remind_task, temp_remind_time
    try:
        if awaiting_remind_task:
            temp_remind_task = user_input
            awaiting_remind_task = False
            if not temp_remind_time:
                awaiting_remind_time = True
                return "When do you want me to remind you?"
            else:
                return get_bot_response("remind")

        if awaiting_remind_time:
            temp_remind_time = user_input
            awaiting_remind_time = False
            if not temp_remind_task:
                awaiting_remind_task = True
                return "Remind you to do what exactly?"
            else:
                return get_bot_response("remind")
        
        result = send_to_clu(user_input)
        intent = result['result']['prediction']['topIntent']
        intents = result['result']['prediction']['intents']
        entities = result['result']['prediction']['entities']
        score = None
        for item in intents:
            if item["category"] == intent:
                score = item["confidenceScore"]
                break

        print(f"Your intention is: {intent} ({score*100:.1f}%)")

        if awaiting_timer_duration:
            # regex nhận dạng: có phút, giây, hoặc 1 trong 2, hoặc cả 2
            pattern = r'(?:(\d+)\s*minutes?)?\s*(?:(\d+)\s*seconds?)?'
            match = re.search(pattern, user_input.lower()) # tìm biểu thức trong input, /d là decimal, + là nó có thể lặp lại 1 hoặc nhiều lần
            if match:
                # cú pháp của thư viện re, trả về nhóm được tìm thấy trong regular expression
                minutes = int(match.group(1)) if match.group(1) else 0
                seconds = int(match.group(2)) if match.group(2) else 0
                awaiting_timer_duration = False

                # Tạo và chạy thread timer
                threading.Thread(target=run_timer, args=(minutes, seconds), daemon=True).start() 
                # daemon là luồng nền, tức là khi tắt chtr thì thread sẽ dừng

                return f"Ok bro, I've set a timer for {minutes} minutes and {seconds} seconds!"
            else:
                return "Nice try bro, try harder"
        
        # Responses
        if intent == "greet_user":
            return random.choice([
                "Hey there! How can I assist you today?",
                "Hello! What can I do for you?",
                "Hi! Need any help?"
            ])
        
        
        elif intent == "set timer":
            awaiting_timer_duration = True
            return random.choice([
                "Got it! For how many minutes should I set the timer?",
                "Sure thing! Please tell me the duration.",
                "Okay, how long do you want the timer to run?"
            ])
            
        elif intent == "cancel timer":
            return random.choice([
                "Timer cancelled. Let me know if you want to set another one.",
                "Alright, I stopped the timer for you.",
                "Timer is off now."
            ])

        elif intent == "wish_birthday":
            name = None
            for entity in entities:
                if entity['category'] == 'name':
                    name = entity['text']
                    break
            
            if name:
                play_sound("festive-birthday-horn-250238.mp3")
                return f"Happy Birthday to {name}🎉! 🎂 I wish {name} a wonderful birthday!🥳"
                
            else:
                play_sound("festive-birthday-horn-250238.mp3")
                return "Happy Birthday🎉! 🎂 I wish you all the best🥳"
            
        if intent == "remind":
            # lấy task và time nếu có từ CLU

            if not temp_remind_task:
                awaiting_remind_task = True
                return "Remind you to do what exactly?"
            if not temp_remind_time:
                awaiting_remind_time = True
                return "When do you want me to remind you?"

            task = temp_remind_task
            seconds = extract_seconds(temp_remind_time)

            def reminder_action():
                time.sleep(seconds)
                chat_area.insert(tk.END, f"\n⏰ Reminder: JUST {task.upper()}!!!\n")
                play_sound("party-blower-4-207163.mp3")

            threading.Thread(target=reminder_action, daemon=True).start()

            # reset lại bộ nhớ tạm
            awaiting_remind_task = False
            awaiting_remind_time = False
            temp_remind_task = None
            temp_remind_time = None

            return f"Okay, I’ll remind you to {task} in {seconds} seconds!"

        else:
            return random.choice([ 
                "Sorry, I didn’t quite catch that. Could you say it differently?",
                "Hmm, I’m not sure what you mean. Can you just try harder?",
                "I’m still learning. Try better?"
            ])

    except Exception as e:
        return "Sorry, there was an error."
        #print("❗ Raw response:", response.text)


def send_message():
    user_input = entry.get() # trả về chuỗi kí tự người dùng nhập
    if user_input.strip() == "": # kiểm tra người dùng có đang mess around, bỏ qua space
        return 
    chat_area.insert(tk.END, f"You: {user_input}\n") # tk.END là vị trí cuối cùng ở ô nhập dữ liệu
    entry.delete(0, tk.END)
    response = get_bot_response(user_input)
    chat_area.insert(tk.END, f"Freind🤖: {response}\n")

# Tạo giao diện 
window = tk.Tk()
window.title("My friend Freind")

chat_area = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=60, height=20, font=("Segoe UI Emoji", 12))
chat_area.pack(padx=10, pady=10)
chat_area.config(state=tk.NORMAL)

entry = tk.Entry(window, width=50, font=("Segoe UI Emoji", 12))
entry.pack(padx=10, pady=5, side=tk.LEFT)

send_button = tk.Button(window, text="Send", command=send_message, font=("Arial", 12))
send_button.pack(padx=10, pady=5, side=tk.LEFT)

window.mainloop()
