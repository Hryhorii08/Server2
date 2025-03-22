import sys
import os
import time
import requests
import psycopg2
from flask import Flask, request, jsonify
import openai

sys.stdout.reconfigure(encoding='utf-8')  # Устанавливаем кодировку UTF-8

app = Flask(__name__)

# 🔑 Подключение к PostgreSQL
DB_USER = "worker1"
DB_PASSWORD = "HxwV52HjFiJ6jIE9QsSzB5GSuxDATlwr"
DB_NAME = "mydatabase_o3vx"
DB_HOST = "dpg-cvdtb452ng1s73cajrp0-a.oregon-postgres.render.com"
DB_PORT = 5432  

def get_db_connection():
    print("🔌 Подключение к базе данных...")
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# 🔥 OpenAI API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = "asst_4Jfbku9f3nTAJqcsyoCf9MGW"
openai.api_key = OPENAI_API_KEY

# ✅ Функция форматирования текста
def format_text(text):
    return text.replace("\\n", "\n").strip()

# 📌 Работа с OpenAI
def send_to_openai(user_message, thread_id=None):
    print(f"📤 Отправка сообщения в OpenAI: {user_message}, thread_id: {thread_id}")

    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        print(f"🆕 Новый тред создан: {thread_id}")

    # 1. Отправляем сообщение
    message = openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )
    print(f"📩 Сообщение отправлено: {message.id}")

    time.sleep(2)

    # 2. Запускаем Run
    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )
    print(f"🚀 Run запущен: {run.id}")

    # 3. Ждём завершения Run
    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            print("✅ Run завершен")
            break
        elif run_status.status in ["failed", "cancelled"]:
            print("❌ Run завершился с ошибкой")
            return thread_id, "Ошибка обработки запроса"
        time.sleep(1)

    time.sleep(2)

    # 4. Получаем последнее сообщение от ассистента
    messages = openai.beta.threads.messages.list(thread_id=thread_id)

    assistant_reply = next(
        (msg for msg in reversed(messages.data) if msg.role == "assistant"),
        None
    )

    if assistant_reply and assistant_reply.content:
        last_message_data = assistant_reply.content
        if isinstance(last_message_data, list):
            # ✅ Читаем только part.text.value, без Text(...)
            last_message = "\n".join([
                part.text.value for part in last_message_data
                if hasattr(part, "text") and hasattr(part.text, "value")
            ])
        else:
            last_message = str(last_message_data)
    else:
        last_message = "Ошибка: ассистент не ответил"

    # ✅ Приводим текст к читаемому виду
    last_message = last_message.encode("utf-8").decode("utf-8")
    last_message = format_text(last_message)

    print(f"📩 Ответ ассистента:\n{last_message}")

    return thread_id, last_message

# 📥 POST endpoint
@app.route("/message", methods=["POST"])
def receive_message():
    data = request.json
    print(f"📥 Получен запрос: {data}")

    telegram_id = data.get("telegram_id")
    user_message = data.get("message")

    if not telegram_id or not user_message:
        print("⚠️ Ошибка: не переданы данные")
        return jsonify({"error": "Не переданы данные"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ищем thread_id
    cursor.execute("SELECT thread_id FROM users_threads WHERE telegram_id = %s;", (telegram_id,))
    thread = cursor.fetchone()

    if thread:
        thread_id = thread[0]
        print(f"✅ Найден thread_id: {thread_id}")
    else:
        thread_id, _ = send_to_openai(user_message)
        cursor.execute(
            "INSERT INTO users_threads (telegram_id, thread_id) VALUES (%s, %s);",
            (telegram_id, thread_id)
        )
        conn.commit()
        print(f"🆕 Сохранили новый thread_id: {thread_id}")

    _, reply = send_to_openai(user_message, thread_id)

    cursor.close()
    conn.close()

    return jsonify({"reply": reply})

# 🚀 Запуск сервера
if __name__ == "__main__":
    print("🚀 Сервер запущен на http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
