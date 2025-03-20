import sys
sys.stdout.reconfigure(encoding='utf-8')  # ✅ Устанавливаем кодировку UTF-8

import os
import requests
import psycopg2
from flask import Flask, request, jsonify
import openai
 
app = Flask(__name__)

# 🔑 Подключение к PostgreSQL
DB_USER = "worker1"  # Твой username в БД
DB_PASSWORD = "HxwV52HjFiJ6jIE9QsSzB5GSuxDATlwr"  # Вставь свой пароль
DB_NAME = "mydatabase_o3vx"  # Имя базы данных
DB_HOST = "dpg-cvdtb452ng1s73cajrp0-a.oregon-postgres.render.com"  # Например: dpg-xxxxx-a.oregon-postgres.render.com
DB_PORT = 5432  # Порт PostgreSQL

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
OPENAI_API_KEY = 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"
ASSISTANT_ID = "asst_4Jfbku9f3nTAJqcsyoCf9MGW"
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
        # Создаем новый тред
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
    data = request.json
    telegram_id = data.get("telegram_id")
    user_message = data.get("message")

    if not telegram_id or not user_message:
        return jsonify({"error": "Не переданы данные"}), 400

    # Подключаемся к БД
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ищем тред в базе
    cursor.execute("SELECT thread_id FROM users_threads WHERE telegram_id = %s;", (telegram_id,))
    thread = cursor.fetchone()

    if thread:
        thread_id = thread[0]
    else:
        thread_id, _ = send_to_openai(user_message)
        cursor.execute("INSERT INTO users_threads (telegram_id, thread_id) VALUES (%s, %s);",
                       (telegram_id, thread_id))
        conn.commit()

    # Отправляем сообщение в OpenAI
    _, response = send_to_openai(user_message, thread_id)

    # Получаем текст ответа
    reply = response.content[0].text if response and response.content else "Ошибка получения ответа"

    # Закрываем соединение с БД
    cursor.close()
    conn.close()

    # Возвращаем ответ
    return jsonify({"reply": reply})

# 🚀 Запуск сервера
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
