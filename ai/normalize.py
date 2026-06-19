import json
import requests
from utils.env import load_env, get_ai_provider, get_ai_api_key, get_ollama_host, get_ollama_model

NORMALIZE_PROMPT = """
You are a student scheduler assistant. Normalize this vague task into a time estimate in hours.

Task: "{task_description}"
Output format (JSON only):
{{
  "estimated_duration_hours": 2.5,
  "confidence": "high"
}}

Rules:
- Keep durations realistic for a student.
- Use 1-3 hours for a single chapter or problem set.
- If the task is vague, choose a conservative estimate.
- Return a single valid JSON object only.
- Do not include any explanation, reasoning, analysis, or extra text.
"""


def _extract_json_string(text):
    if not text or not isinstance(text, str):
        return None

    stripped = text.strip()
    if not stripped:
        return None

    try:
        json.loads(stripped)
        return stripped
    except ValueError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or start >= end:
        return None

    candidate = stripped[start:end + 1]
    try:
        json.loads(candidate)
        return candidate
    except ValueError:
        return None


def normalize_task(task_description: str) -> float:
    load_env()
    provider = get_ai_provider()
    api_key = get_ai_api_key()

    if provider != "ollama" and not api_key:
        return 1.0

    model = get_ollama_model() if provider == "ollama" else "llama-3.1-7b"
    endpoint = f"{get_ollama_host()}/v1/chat/completions" if provider == "ollama" else "https://api.groq.com/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if provider != "ollama":
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": NORMALIZE_PROMPT.format(task_description=task_description)}],
        "temperature": 0.7,
        "max_tokens": 150,
    }

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=(15, 180))
        data = response.json()
        choice = data.get("choices", [])[0] if isinstance(data.get("choices"), list) else None
        message = choice.get("message") if isinstance(choice, dict) else None
        content = None
        if isinstance(message, dict):
            raw_content = message.get("content")
            if isinstance(raw_content, str) and raw_content.strip():
                content = _extract_json_string(raw_content)
            else:
                reasoning = message.get("reasoning") or message.get("thoughts")
                content = _extract_json_string(reasoning)
        if not content:
            return 1.0
        parsed = json.loads(content)
        return float(parsed.get("estimated_duration_hours", 1.0))
    except Exception:
        return 1.0
