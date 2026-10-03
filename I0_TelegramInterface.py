import json
import requests

BOT_TOKEN = "8949593265:AAGalkZDAGolW3PG_MNiieNJBkRMJFrC_6o"
CHANNEL_ID = "@International_MetaTech"

INPUT_FILE = "G1_NewsAfterAIContentGenerationRun.json"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(text):
    url = f"{TELEGRAM_API_URL}/sendMessage"

    payload = {
        "chat_id": CHANNEL_ID,
        "text": text
    }

    response = requests.post(url, data=payload, timeout=30)

    if response.status_code != 200:
        print("Telegram API error:")
        print(response.text)
        return False

    result = response.json()

    if not result.get("ok"):
        print("Telegram API returned an error:")
        print(result)
        return False

    return True


def main():
    print("Loading G1...")

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    generated_content = data.get("generated_content", {})

    print(f"Total groups: {len(generated_content)}")

    published = 0

    for group_id, content in generated_content.items():

        text = content.get("text", "").strip()

        if not text:
            print(f"{group_id}: Empty text. Skipping.")
            continue

        print(f"Publishing {group_id}...")

        if send_message(text):
            print(f"{group_id}: Published successfully.")
            published += 1
        else:
            print(f"{group_id}: Publishing failed.")

    print()
    print("I0 completed.")
    print(f"Published: {published}")
    print(f"Total groups: {len(generated_content)}")


if __name__ == "__main__":
    main()
