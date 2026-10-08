import imaplib
import email
import requests
from email.header import decode_header
from datetime import datetime

# === НАСТРОЙКИ GMAIL ===
EMAIL = "your_email@gmail.com"
APP_PASSWORD = "your_app_pasword"

# === КЛЮЧ GROQ ===
api_key = "gsk_your_api_key"

# === ПРОКСИ ===
proxies = {
    "http": "http://127.0.0.1:12334",
    "https": "http://127.0.0.1:12334"
}

# === ФУНКЦИЯ: расшифровка темы письма ===
def decode_subject(subject):
    if not subject:
        return "(без темы)"
    decoded = decode_header(subject)
    result = ""
    for part, encoding in decoded:
        if isinstance(part, bytes):
            try:
                result += part.decode(encoding or "utf-8", errors="ignore")
            except:
                result += part.decode("utf-8", errors="ignore")
        else:
            result += str(part)
    return result

# === 1. ПОДКЛЮЧЕНИЕ К ПОЧТЕ ===
print("Подключаюсь к Gmail...")
mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login(EMAIL, APP_PASSWORD)
mail.select("inbox")

status, messages = mail.search(None, "ALL")
email_ids = messages[0].split()

print("Всего писем:", len(email_ids))
print()

# === 2. БЕРЁМ ПОСЛЕДНИЕ 5 ПИСЕМ ===
last_emails = email_ids[-5:]
email_list = []

for e_id in last_emails:
    status, msg_data = mail.fetch(e_id, "(RFC822)")
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            subject = decode_subject(msg["subject"])
            sender = msg["from"]

            # Тело письма (только текст)
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                        except:
                            pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                except:
                    pass

            email_list.append({
                "from": sender,
                "subject": subject,
                "body": body[:500]
            })

mail.logout()

print("Собрано писем:", len(email_list))
print()

# === 3. ОТПРАВЛЯЕМ В AI ===
print("Отправляю в AI для сортировки...")

prompt = "Вот последние письма:\n\n"
for i, e in enumerate(email_list, 1):
    prompt += f"Письмо {i}:\n"
    prompt += f"От: {e['from']}\n"
    prompt += f"Тема: {e['subject']}\n"
    prompt += f"Текст: {e['body'][:200]}\n\n"

prompt += (
    "Для каждого письма:\n"
    "1. Определи категорию: ВАЖНОЕ / ОБЫЧНОЕ / СПАМ.\n"
    "2. Если ВАЖНОЕ — напиши краткий черновик ответа.\n\n"
    "Отвечай по-русски, кратко."
)

try:
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-oss-20b",
            "messages": [{"role": "user", "content": prompt}]
        },
        proxies=proxies,
        timeout=60
    )
    data = response.json()

    if "choices" in data:
        analysis = data["choices"][0]["message"]["content"]
        print()
        print("=== АНАЛИЗ ОТ AI ===")
        print(analysis)

        # === 4. СОХРАНЯЕМ В ФАЙЛ ===
        with open("email_report.txt", "w", encoding="utf-8") as f:
            f.write("ОТЧЁТ ПО ПОЧТЕ\n")
            f.write("Дата: " + datetime.now().strftime("%Y-%m-%d %H:%M") + "\n")
            f.write("=" * 50 + "\n\n")

            f.write("ПИСЬМА:\n")
            for i, e in enumerate(email_list, 1):
                f.write(f"{i}. От: {e['from']}\n")
                f.write(f"   Тема: {e['subject']}\n\n")

            f.write("=" * 50 + "\n\n")
            f.write("АНАЛИЗ ОТ AI:\n")
            f.write(analysis + "\n")

        print()
        print("Сохранено в email_report.txt")
    else:
        print("Ошибка AI:", data)

except Exception as e:
    print("Ошибка:", e)
