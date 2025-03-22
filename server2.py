import sys
import os
import time
import requests
import psycopg2
from flask import Flask, request, jsonify
import openai

sys.stdout.reconfigure(encoding='utf-8')
app = Flask(__name__)

# 🔑 Настройки БД
DB_USER = "worker1"
DB_PASSWORD = "HxwV52HjFiJ6jIE9QsSzB5GSuxDATlwr"
DB_NAME = "mydatabase_o3vx"
DB_HOST = "dpg-cvdtb452ng1s73cajrp0-a.oregon-postgres.render.com"
DB_PORT = 5432

def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# 🔐 OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = "asst_4Jfbku9f3nTAJqcsyoCf9MGW"
openai.api_key = OPENAI_API_KEY

# 🧼 Чистим текст
def format_text(text):
    return text.replace("\\n", "\n").strip()

# 🧠 Отправка в OpenAI и получение ответа
def send_to_openai(user_message, thread_id=None):
    print(f"📤 Сообщение: {user_message}, thread_id: {thread_id}")

    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        print(f"🧵 Новый thread создан: {thread_id}")

    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    time.sleep(2)

    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )
    print(f"🚀 Run запущен: {run.id}")

    while True:
        status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if status.status == "completed":
            print("✅ Run завершен")
            break
        elif status.status in ["failed", "cancelled"]:
            print("❌ Ошибка в run")
            return thread_id, "Ошибка в обработке"
        time.sleep(1)

    time.sleep(1.5)

    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    print(f"📨 Получено сообщений: {len(messages.data)}")

    # 🧠 Берем последнее сообщение от ассистента (самое верхнее)
    for msg in messages.data:
        if msg.role == "assistant":
            parts = msg.content
            if isinstance(parts, list):
                result = "\n".join([
                    part.text.value for part in parts
                    if hasattr(part, "text") and hasattr(part.text, "value")
                ])
            else:
                result = str(parts)
            result = result.encode("utf-8").decode("utf-8")
            result = format_text(result)
            print(f"📩 Ответ ассистента:\n{result}")
            return thread_id, result

    return thread_id, "Ассистент не ответил"

# 📥 Обработка POST-запроса
@app.route("/message", methods=["POST"])
def receive_message():
    data = request.json
    print(f"📥 Запрос: {data}")

    telegram_id = data.get("telegram_id")
    user_message = data.get("message")

    if not telegram_id or not user_message:
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT thread_id FROM users_threads WHERE telegram_id = %s;", (telegram_id,))
    found = cursor.fetchone()

    if found:
        thread_id = found[0]
        print(f"📍 Thread найден: {thread_id}")
    else:
        thread_id, _ = send_to_openai(user_message)
        cursor.execute(
            "INSERT INTO users_threads (telegram_id, thread_id) VALUES (%s, %s);",
            (telegram_id, thread_id)
        )
        conn.commit()
        print(f"🆕 Thread сохранен: {thread_id}")

    _, reply = send_to_openai(user_message, thread_id)

    cursor.close()
    conn.close()

    return jsonify({"reply": reply})

# 🚀 Запуск
if __name__ == "__main__":
    print("🟢 Сервер запущен на http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
