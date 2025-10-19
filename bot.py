import os
import requests
import time

TOKEN = os.getenv('BOT_TOKEN')
URL = f"https://api.telegram.org/bot{TOKEN}"

def get_updates(offset=None):
    try:
        url = f"{URL}/getUpdates"
        params = {"timeout": 100, "offset": offset}
        response = requests.get(url, params=params, timeout=120)
        return response.json()
    except:
        return {"ok": False}

def send_message(chat_id, text, reply_markup=None):
    try:
        url = f"{URL}/sendMessage"
        data = {"chat_id": chat_id, "text": text}
        if reply_markup:
            data["reply_markup"] = reply_markup
        requests.post(url, json=data, timeout=30)
    except:
        pass

def main():
    last_update = 0
    
    while True:
        updates = get_updates(offset=last_update + 1)
        
        if updates.get("ok"):
            for update in updates["result"]:
                last_update = update["update_id"]
                
                if "message" in update:
                    msg = update["message"]
                    if msg.get("text") == "/start":
                        keyboard = {
                            "inline_keyboard": [[
                                {"text": "get server", "callback_data": "get_server"}
                            ]]
                        }
                        send_message(
                            msg["chat"]["id"], 
                            "Добро пожаловать!\nв данном боте ты можешь генерировать ссылки на приватный сервер!",
                            reply_markup=keyboard
                        )
                
                elif "callback_query" in update:
                    callback = update["callback_query"]
                    if callback["data"] == "get_server":
                        requests.post(f"{URL}/answerCallbackQuery", 
                                    json={"callback_query_id": callback["id"]})
                        requests.post(f"{URL}/editMessageText",
                                    json={
                                        "chat_id": callback["message"]["chat"]["id"],
                                        "message_id": callback["message"]["message_id"],
                                        "text": "тест"
                                    })
        
        time.sleep(1)

if __name__ == "__main__":
    main()