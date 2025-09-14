from __future__ import annotations
import os, httpx, json

TG = os.getenv("TG_BOT_TOKEN","")
CHAT = os.getenv("TELEGRAM_CHAT_ID","")

def send_text(text: str, chat_id: str|None=None):
    if not TG or not (chat_id or CHAT): 
        return
    url = f"https://api.telegram.org/bot{TG}/sendMessage"
    with httpx.Client(timeout=20) as c:
        c.post(url, data={"chat_id": chat_id or CHAT, "text": text})

def send_document(bytes_data: bytes, filename: str, caption: str = "", chat_id: str|None=None):
    if not TG or not (chat_id or CHAT): 
        return
    url = f"https://api.telegram.org/bot{TG}/sendDocument"
    files = {"document": (filename, bytes_data, "application/json")}
    data = {"chat_id": chat_id or CHAT, "caption": caption}
    with httpx.Client(timeout=60) as c:
        c.post(url, data=data, files=files)
