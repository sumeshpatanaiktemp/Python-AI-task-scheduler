import asyncio
import importlib
import logging
from utils.env import load_env, get_telegram_token

logger = logging.getLogger(__name__)


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


async def _send_message_async(chat_id: str, message: str, token: str):
    """Async function to send Telegram message"""
    Bot = _get_telegram_bot_class()
    async with Bot(token=token) as bot:
        await bot.send_message(chat_id=chat_id, text=message, read_timeout=10, write_timeout=10)


def send_telegram_message(chat_id: str, message: str, timeout: int = 30):
    """
    Send a message to Telegram with proper timeout handling.
    
    Args:
        chat_id: Telegram chat ID
        message: Message text to send
        timeout: Timeout in seconds (default 30)
    """
    load_env()
    token = get_telegram_token()
    if not token:
        raise RuntimeError("Telegram bot token missing")

    try:
        # Run async function with timeout
        asyncio.run(asyncio.wait_for(_send_message_async(chat_id, message, token), timeout=timeout))
        logger.info(f"Message sent successfully to chat {chat_id}")
    except asyncio.TimeoutError:
        logger.error(f"Timeout sending message to chat {chat_id}")
        raise RuntimeError(f"Telegram send timeout for chat {chat_id}")
    except Exception as exc:
        logger.error(f"Failed to send message to chat {chat_id}: {str(exc)}")
        raise


def get_telegram_message_text(schedule_rows):
    lines = ["Your 3-day study plan:\n"]
    for row in schedule_rows:
        lines.append(f"Day {row['day_number']}: {row['title']} | {row['start_time']} - {row['end_time']}")
    return "\n".join(lines)


from ai.schedule import generate_telegram_message


def send_ai_generated_schedule_to_telegram(chat_id: str, tasks, timeout: int = 30):
    """
    Generate AI schedule message and send to Telegram.
    
    Args:
        chat_id: Telegram chat ID
        tasks: List of task dictionaries
        timeout: Timeout in seconds (default 30)
    
    Returns:
        The generated message text
    """
    load_env()
    token = get_telegram_token()
    if not token:
        raise RuntimeError("Telegram bot token missing")
    
    # Generate AI-crafted message from tasks
    message = generate_telegram_message(tasks)
    
    # Send to Telegram with timeout handling
    try:
        asyncio.run(asyncio.wait_for(_send_message_async(chat_id, message, token), timeout=timeout))
        logger.info(f"AI-generated schedule sent successfully to chat {chat_id}")
    except asyncio.TimeoutError:
        logger.error(f"Timeout sending AI schedule to chat {chat_id}")
        raise RuntimeError(f"Telegram send timeout for chat {chat_id}")
    except Exception as exc:
        logger.error(f"Failed to send AI schedule to chat {chat_id}: {str(exc)}")
        raise
    
    return message


def send_schedule_to_chat_ids(schedule_rows, timeout: int = 30):
    """
    Send schedule to multiple chat IDs with retry logic.
    
    Args:
        schedule_rows: List of schedule row dictionaries
        timeout: Timeout in seconds per message (default 30)
    
    Returns:
        Dictionary with successful and failed chat IDs
    """
    grouped = {}
    for row in schedule_rows:
        chat_id = row.get("chat_id")
        if not chat_id:
            continue
        grouped.setdefault(chat_id, []).append(row)

    results = {"successful": [], "failed": []}
    
    for chat_id, rows in grouped.items():
        message = get_telegram_message_text(rows)
        try:
            send_telegram_message(chat_id, message, timeout=timeout)
            results["successful"].append(chat_id)
        except Exception as exc:
            logger.warning(f"Failed to send to {chat_id}: {str(exc)}")
            results["failed"].append({"chat_id": chat_id, "error": str(exc)})

    return results
