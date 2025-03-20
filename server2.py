import sys
import os
import requests
import psycopg2
from flask import Flask, request, jsonify
import openai

sys.stdout.reconfigure(encoding='utf-8')  # Устанавливаем кодировку UTF-8

app = Flask(name)

# 🔑 Подключение к PostgreSQL
DB_USER = "worker1"
DB_PASSWORD = "HxwV52HjFiJ6jIE9QsSzB5GSuxDATlwr"
DB_NAME = "mydatabase_o3vx"
DB_HOST = "dpg-cvdtb452ng1s73cajrp0-a.oregon-postgres.render.com"
DB_PORT = 5432

# 🛠 Подключаемся к базе данных
def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# 🔥 OpenAI API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Загружаем ключ из переменной окружения
if not OPENAI_API_KEY:
    raise ValueError("❌ Ошибка: OPENAI_API_KEY не найден в переменных окружения!")
    
openai.api_key = OPENAI_API_KEY

# 📌 Функция для работы с OpenAI
def send_to_openai(user_message, thread_id=None):
    if thread_id:
        response = openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
    else:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        response = openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
    return thread_id, response

# 📌 API для получения сообщений
@app.route("/message", methods=["POST"])
def receive_message():
    try:
        data = request.json
        telegram_id = data.get("telegram_id")
        user_message = data.get("message")

        if not telegram_id or not user_message:
            return jsonify({"error": "Не переданы данные"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT thread_id FROM users_threads WHERE telegram_id = %s;", (telegram_id,))
        thread = cursor.fetchone()

        if thread:
            thread_id = thread[0]
        else:
            thread_id, _ = send_to_openai(user_message)
            cursor.execute("INSERT INTO users_threads (telegram_id, thread_id) VALUES (%s, %s);",
                           (telegram_id, thread_id))
            conn.commit()

        _, response = send_to_openai(user_message, thread_id)

        reply_text = response.content[0].text if response and response.content else "Ошибка получения ответа"

        cursor.close()
        conn.close()

        return jsonify({"reply": reply_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Запуск сервера
if name == "main":
    app.run(host="0.0.0.0", port=5000)
