import asyncio
import importlib
from utils.env import load_env, get_telegram_token


def _get_telegram_bot_class():
    try:
        module = importlib.import_module("telegram")
    except ImportError as exc:
        raise ImportError("The telegram package is not installed. Install python-telegram-bot instead.") from exc

    bot_class = getattr(module, "Bot", None)
    if bot_class is None:
        bot_class = getattr(module, "bot", None)
        if bot_class is not None:
            bot_class = getattr(bot_class, "Bot", None)

    if bot_class is None:
        raise ImportError(
            "Unable to locate Bot in the telegram module. Ensure you have installed python-telegram-bot, not a conflicting telegram package."
        )

    return bot_class


def _run_async_if_needed(result):
    if asyncio.iscoroutine(result):
        return asyncio.run(result)
    return result


def get_telegram_message_text(schedule_rows):
    lines = ["Your 3-day study plan:\n"]
    for row in schedule_rows:
        lines.append(f"Day {row['day_number']}: {row['title']} | {row['start_time']} - {row['end_time']}")
    return "\n".join(lines)


def send_telegram_message(chat_id: str, message: str):
    load_env()
    token = get_telegram_token()
    if not token:
        raise RuntimeError("Telegram bot token missing")

    Bot = _get_telegram_bot_class()
    bot = Bot(token=token)
    result = bot.send_message(chat_id=chat_id, text=message)
    _run_async_if_needed(result)

from ai.schedule import generate_telegram_message

def send_ai_generated_schedule_to_telegram(chat_id: str, tasks):
    """Generate AI schedule message and send to Telegram"""
    load_env()
    token = get_telegram_token()
    if not token:
        raise RuntimeError("Telegram bot token missing")
    
    # Generate AI-crafted message from tasks
    message = generate_telegram_message(tasks)
    
    # Send to Telegram
    Bot = _get_telegram_bot_class()
    bot = Bot(token=token)
    result = bot.send_message(chat_id=chat_id, text=message)
    _run_async_if_needed(result)
    
    return message

def send_schedule_to_chat_ids(schedule_rows):
    grouped = {}
    for row in schedule_rows:
        chat_id = row.get("chat_id")
        if not chat_id:
            continue
        grouped.setdefault(chat_id, []).append(row)

    results = []
    for chat_id, rows in grouped.items():
        message = get_telegram_message_text(rows)
        send_telegram_message(chat_id, message)
        results.append(chat_id)

    return results
