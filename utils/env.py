import os
from dotenv import load_dotenv


def load_env():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(root_dir, ".env")
    load_dotenv(env_path)


def get_ai_provider():
    return os.getenv("AI_PROVIDER", "ollama").strip().lower()


def get_ai_api_key():
    return os.getenv("AI_API_KEY")


def get_ollama_host():
    return os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def get_ollama_model():
    return os.getenv("OLLAMA_MODEL", "gemma4:e4b")


def get_telegram_token():
    return os.getenv("TELEGRAM_BOT_TOKEN")
