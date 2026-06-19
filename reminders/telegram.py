import asyncio
import importlib
import logging
import os
from utils.env import load_env, get_telegram_token

# Setup logging
log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(os.path.join(log_dir, "telegram.log"))
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


def _get_telegram_bot_class():
    logger.debug("_get_telegram_bot_class() called")
    try:
        module = importlib.import_module("telegram")
        logger.debug("✓ telegram module imported successfully")
    except ImportError as exc:
        logger.error("✗ Failed to import telegram module")
        raise ImportError("The telegram package is not installed. Install python-telegram-bot instead.") from exc

    bot_class = getattr(module, "Bot", None)
    if bot_class is None:
        bot_class = getattr(module, "bot", None)
        if bot_class is not None:
            bot_class = getattr(bot_class, "Bot", None)

    if bot_class is None:
        logger.error("✗ Unable to locate Bot class in telegram module")
        raise ImportError(
            "Unable to locate Bot in the telegram module. Ensure you have installed python-telegram-bot, not a conflicting telegram package."
        )

    logger.debug("✓ Bot class found")
    return bot_class


async def _send_message_async(chat_id: str, message: str, token: str):
    """Async function to send Telegram message"""
    logger.debug(f"_send_message_async() called for chat_id: {chat_id}")
    Bot = _get_telegram_bot_class()
    try:
        async with Bot(token=token) as bot:
            logger.debug(f"Sending message to Telegram (chat_id: {chat_id}, message length: {len(message)})")
            await bot.send_message(
                chat_id=chat_id, 
                text=message, 
                read_timeout=15, 
                write_timeout=15,
                connect_timeout=15
            )
        logger.info(f"✓ Message sent successfully to Telegram chat {chat_id}")
    except Exception as e:
        logger.error(f"✗ Error sending to {chat_id}: {str(e)}", exc_info=True)
        raise


def send_telegram_message(chat_id: str, message: str, timeout: int = 45):
    """
    Send a message to Telegram with proper timeout handling.
    
    Args:
        chat_id: Telegram chat ID (must be a valid integer or string)
        message: Message text to send
        timeout: Timeout in seconds (default 45)
    
    Raises:
        ValueError: If chat_id is invalid
        RuntimeError: If token is missing or send fails
    """
    logger.info(f"send_telegram_message() called with chat_id: {chat_id}, timeout: {timeout}s")
    
    # Validate chat_id
    if not chat_id:
        logger.error("✗ chat_id cannot be empty")
        raise ValueError("chat_id cannot be empty")
    
    try:
        int(str(chat_id).strip())
        logger.debug(f"✓ chat_id format validated: {chat_id}")
    except ValueError:
        logger.error(f"✗ Invalid chat_id format: {chat_id}. Must be numeric.")
        raise ValueError(f"Invalid chat_id format: {chat_id}. Must be numeric.")
    
    load_env()
    token = get_telegram_token()
    if not token:
        logger.error("✗ Telegram bot token missing from .env file")
        raise RuntimeError("Telegram bot token missing from .env file")

    if not token.strip():
        logger.error("✗ Telegram bot token is empty in .env file")
        raise RuntimeError("Telegram bot token is empty in .env file")

    logger.debug(f"Starting send to chat_id: {chat_id}")
    
    try:
        # Run async function with timeout
        logger.debug(f"Running async message send with {timeout}s timeout...")
        asyncio.run(asyncio.wait_for(_send_message_async(str(chat_id), message, token), timeout=timeout))
        logger.info(f"✓ Message sent successfully to chat {chat_id}")
        return True
    except asyncio.TimeoutError:
        error_msg = f"Telegram API timeout after {timeout}s for chat {chat_id}"
        logger.error(f"✗ {error_msg}")
        raise RuntimeError(error_msg)
    except Exception as exc:
        error_msg = f"Failed to send message to chat {chat_id}: {str(exc)}"
        logger.error(f"✗ {error_msg}", exc_info=True)
        raise RuntimeError(error_msg)


def get_telegram_message_text(schedule_rows):
    """Format schedule rows as Telegram message"""
    logger.debug(f"get_telegram_message_text() called with {len(schedule_rows)} schedule rows")
    lines = ["Your 3-day study plan:\n"]
    for row in schedule_rows:
        lines.append(f"Day {row['day_number']}: {row['title']} | {row['start_time']} - {row['end_time']}")
    result = "\n".join(lines)
    logger.debug(f"✓ Formatted message ({len(result)} characters)")
    return result


from ai.schedule import generate_telegram_message


def send_ai_generated_schedule_to_telegram(chat_id: str, tasks, timeout: int = 45):
    """
    Generate AI schedule message and send to Telegram.
    
    Args:
        chat_id: Telegram chat ID (must be numeric)
        tasks: List of task dictionaries
        timeout: Timeout in seconds (default 45)
    
    Returns:
        The generated message text
    
    Raises:
        ValueError: If chat_id is invalid or no tasks provided
        RuntimeError: If token missing or send fails
    """
    logger.info(f"send_ai_generated_schedule_to_telegram() called with chat_id: {chat_id}, {len(tasks)} tasks")
    
    if not chat_id:
        logger.error("✗ chat_id cannot be empty")
        raise ValueError("chat_id cannot be empty")
    
    if not tasks:
        logger.error("✗ No tasks provided to generate message")
        raise ValueError("No tasks provided to generate message")
    
    try:
        int(str(chat_id).strip())
        logger.debug(f"✓ chat_id format validated: {chat_id}")
    except ValueError:
        logger.error(f"✗ Invalid chat_id format: {chat_id}. Must be numeric.")
        raise ValueError(f"Invalid chat_id format: {chat_id}. Must be numeric.")
    
    load_env()
    token = get_telegram_token()
    if not token:
        logger.error("✗ Telegram bot token missing from .env file")
        raise RuntimeError("Telegram bot token missing from .env file")

    logger.info(f"Generating AI message for chat_id: {chat_id}...")
    
    try:
        # Generate AI-crafted message from tasks
        message = generate_telegram_message(tasks)
        logger.debug(f"✓ AI message generated ({len(message)} characters)")
        
        # Send to Telegram with timeout handling
        logger.info(f"Sending AI-generated message to Telegram chat {chat_id}...")
        asyncio.run(asyncio.wait_for(_send_message_async(str(chat_id), message, token), timeout=timeout))
        logger.info(f"✓ AI-generated schedule sent successfully to chat {chat_id}")
        return message
    except asyncio.TimeoutError:
        error_msg = f"Telegram API timeout after {timeout}s for chat {chat_id}"
        logger.error(f"✗ {error_msg}")
        raise RuntimeError(error_msg)
    except Exception as exc:
        error_msg = f"Failed to send AI schedule to chat {chat_id}: {str(exc)}"
        logger.error(f"✗ {error_msg}", exc_info=True)
        raise RuntimeError(error_msg)


def send_schedule_to_chat_ids(schedule_rows, timeout: int = 45):
    """
    Send schedule to multiple chat IDs with retry logic.
    
    Args:
        schedule_rows: List of schedule row dictionaries
        timeout: Timeout in seconds per message (default 45)
    
    Returns:
        Dictionary with successful and failed chat IDs
    """
    logger.info(f"send_schedule_to_chat_ids() called with {len(schedule_rows)} schedule rows")
    
    grouped = {}
    for row in schedule_rows:
        chat_id = row.get("chat_id")
        if not chat_id:
            logger.warning("Schedule row has no chat_id")
            continue
        grouped.setdefault(chat_id, []).append(row)

    if not grouped:
        error_msg = "No chat IDs found in schedule rows"
        logger.error(f"✗ {error_msg}")
        raise ValueError(error_msg)

    results = {"successful": [], "failed": []}
    
    logger.info(f"Sending schedule to {len(grouped)} unique chat IDs...")
    for chat_id, rows in grouped.items():
        message = get_telegram_message_text(rows)
        try:
            logger.debug(f"Sending to chat_id: {chat_id}")
            send_telegram_message(str(chat_id), message, timeout=timeout)
            results["successful"].append(chat_id)
            logger.info(f"✓ Successfully sent to {chat_id}")
        except Exception as exc:
            error_details = str(exc)
            logger.warning(f"✗ Failed to send to {chat_id}: {error_details}")
            results["failed"].append({"chat_id": chat_id, "error": error_details})

    logger.info(f"✓ Send complete: {len(results['successful'])} successful, {len(results['failed'])} failed")
    return results
