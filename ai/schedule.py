import os
import re
import requests
import json
from datetime import datetime, timedelta, time
from utils.env import load_env, get_ai_provider, get_ai_api_key, get_ollama_host, get_ollama_model

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "ai_schedule.log")

SCHEDULE_PROMPT = """Generate a 3-day schedule from these tasks. Max 6 hours/day. Return ONLY valid JSON with no explanation.
Tasks: {normalized_tasks}
Output: {{"schedule": [{{"day": 1, "blocks": []}}, {{"day": 2, "blocks": []}}, {{"day": 3, "blocks": []}}], "explanation": ""}}"""

TELEGRAM_MESSAGE_PROMPT = """You are a motivational student scheduler assistant. Create an engaging Telegram message for a student's study reminders.
Use these tasks to generate a friendly, encouraging message that will help the student stay focused.
Include:
- A warm greeting
- Task summary with deadlines
- Motivational tips
- Use emojis to make it visually appealing
- Keep it concise but friendly

Format it as a Telegram message (plain text, no markdown).
DO NOT include any JSON, code blocks, or technical formatting."""

def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def _write_ai_log(entry_type, prompt, payload, response_data=None, exception=None):
    _ensure_log_dir()
    timestamp = datetime.now().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {entry_type}\n")
        log_file.write("PROMPT:\n")
        log_file.write(prompt + "\n")
        log_file.write("PAYLOAD:\n")
        log_file.write(json.dumps(payload, indent=2) + "\n")
        if response_data is not None:
            try:
                log_file.write("RESPONSE:\n")
                log_file.write(json.dumps(response_data, indent=2) + "\n")
            except Exception:
                log_file.write(f"RESPONSE: {response_data}\n")
        if exception is not None:
            log_file.write("ERROR:\n")
            log_file.write(str(exception) + "\n")
        log_file.write("---\n")


def _strip_code_blocks(text):
    if not isinstance(text, str):
        return text
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        stripped = stripped[3:-3].strip()
    if stripped.startswith("`") and stripped.endswith("`"):
        stripped = stripped[1:-1].strip()
    return stripped


def _parse_ai_text_result(response_data):
    if not isinstance(response_data, dict):
        raise ValueError("AI response was not a JSON object")

    def _extract_text_from_message(message):
        if not isinstance(message, dict):
            return None
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return _strip_code_blocks(content)
        reasoning = message.get("reasoning") or message.get("thoughts")
        if isinstance(reasoning, str) and reasoning.strip():
            return _strip_code_blocks(reasoning)
        return None

    if "choices" in response_data:
        choices = response_data.get("choices")
        if choices and isinstance(choices, list):
            first_choice = choices[0]
            message = first_choice.get("message") or first_choice
            text = _extract_text_from_message(message)
            if text:
                return text

    if "outputs" in response_data and isinstance(response_data["outputs"], list):
        first_output = response_data["outputs"][0]
        if isinstance(first_output, dict):
            content = first_output.get("content")
            if isinstance(content, str) and content.strip():
                return _strip_code_blocks(content)
            if isinstance(content, list):
                return _strip_code_blocks("\n".join(str(item) for item in content))

    if "output" in response_data:
        output = response_data["output"]
        if isinstance(output, str) and output.strip():
            return _strip_code_blocks(output)
        if isinstance(output, list):
            return _strip_code_blocks("\n".join(str(item) for item in output))

    raise ValueError("AI response did not contain a recognized completion payload")


def _extract_json_string(text):
    if not text or not isinstance(text, str):
        return None

    text = text.strip()
    if not text:
        return None

    try:
        json.loads(text)
        return text
    except ValueError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        return None

    for i in range(start, end + 1):
        if text[i] != "{":
            continue
        depth = 0
        for j in range(i, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[i : j + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except ValueError:
                        continue
    return None


def _parse_time(value):
    if not value:
        return None
    normalized = value.strip().lower().replace(" ", "")
    if normalized.endswith("am") or normalized.endswith("pm"):
        try:
            suffix = normalized[-2:]
            base = normalized[:-2]
            if ":" in base:
                hour, minute = map(int, base.split(":"))
            else:
                hour = int(base)
                minute = 0
            if suffix == "pm" and hour < 12:
                hour += 12
            if suffix == "am" and hour == 12:
                hour = 0
            return time(hour, minute)
        except Exception:
            return None
    try:
        parts = [int(p) for p in value.split(":")]
        return time(parts[0], parts[1])
    except Exception:
        return None


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def _parse_week(value):
    if not value:
        return None
    normalized = str(value).strip()
    try:
        if normalized.upper().startswith("W"):
            normalized = normalized[1:]
        if "-W" in normalized.upper():
            year, week = normalized.upper().split("-W")
            year = int(year)
            week = int(week)
        elif "/W" in normalized.upper():
            year, week = normalized.upper().split("/W")
            year = int(year)
            week = int(week)
        elif len(normalized) <= 2:
            year = datetime.today().year
            week = int(normalized)
        else:
            return None
        return datetime.strptime(f"{year}-{week}-1", "%G-%V-%u").date()
    except Exception:
        return None


def _local_schedule_fallback(tasks, daily_limit=6.0):
    today = datetime.today().date()
    days = [
        {
            "date": today + timedelta(days=i),
            "blocks": [],
            "remaining": float(daily_limit),
            "current_datetime": datetime.combine(today + timedelta(days=i), time(8, 0)),
        }
        for i in range(3)
    ]

    task_items = []
    for task in tasks:
        deadline_date = _parse_date(task.get("deadline_date"))
        deadline_week_start = _parse_week(task.get("deadline_week"))
        task_items.append(
            {
                "task_id": task["id"],
                "task": task["title"],
                "duration": float(task.get("estimated_duration") or 1.0),
                "preferred_start": _parse_time(task.get("reminder_time")),
                "deadline_date": deadline_date,
                "deadline_week_start": deadline_week_start,
            }
        )

    task_items.sort(
        key=lambda item: (
            item["deadline_date"] or item["deadline_week_start"] or today + timedelta(days=999),
            item["preferred_start"] or time(0, 0),
            -item["duration"],
        )
    )

    explanation_lines = []
    for item in task_items:
        assigned = False
        deadline_cutoff = item["deadline_date"] or item["deadline_week_start"] or days[-1]["date"]
        for day in days:
            if day["date"] > deadline_cutoff:
                continue
            if day["remaining"] < item["duration"]:
                continue
            current = day["current_datetime"]
            if item["preferred_start"]:
                preferred_datetime = datetime.combine(day["date"], item["preferred_start"])
                if preferred_datetime > current:
                    current = preferred_datetime
            end_datetime = current + timedelta(hours=item["duration"])
            if end_datetime.time() > time(22, 0):
                continue
            day["blocks"].append(
                {
                    "task_id": item["task_id"],
                    "task": item["task"],
                    "start": current.strftime("%H:%M"),
                    "end": end_datetime.strftime("%H:%M"),
                }
            )
            explanation_lines.append(
                f"Day {days.index(day)+1}: {item['task']} from {current.strftime('%H:%M')} to {end_datetime.strftime('%H:%M')}"
            )
            day["current_datetime"] = end_datetime + timedelta(minutes=10)
            day["remaining"] -= item["duration"]
            assigned = True
            break

        if not assigned:
            for day in days:
                if day["remaining"] >= item["duration"]:
                    current = day["current_datetime"]
                    end_datetime = current + timedelta(hours=item["duration"])
                    day["blocks"].append(
                        {
                            "task_id": item["task_id"],
                            "task": item["task"],
                            "start": current.strftime("%H:%M"),
                            "end": end_datetime.strftime("%H:%M"),
                        }
                    )
                    explanation_lines.append(
                        f"Day {days.index(day)+1}: {item['task']} from {current.strftime('%H:%M')} to {end_datetime.strftime('%H:%M')}"
                    )
                    day["current_datetime"] = end_datetime + timedelta(minutes=10)
                    day["remaining"] -= item["duration"]
                    assigned = True
                    break

    schedule = [{"day": i + 1, "blocks": day["blocks"]} for i, day in enumerate(days)]
    explanation = "\n".join(explanation_lines) if explanation_lines else "No tasks were scheduled."
    return {"schedule": schedule, "explanation": explanation}


def _parse_ai_result(response_data):
    if not isinstance(response_data, dict):
        raise ValueError("AI response was not a JSON object")

    def _extract_from_message(message):
        if not isinstance(message, dict):
            return None
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return _extract_json_string(content)
        reasoning = message.get("reasoning") or message.get("thoughts")
        if isinstance(reasoning, str) and reasoning.strip():
            return _extract_json_string(reasoning)
        return None

    if "choices" in response_data:
        choices = response_data.get("choices")
        if choices and isinstance(choices, list):
            first_choice = choices[0]
            message = first_choice.get("message") or first_choice
            content = _extract_from_message(message)
            if content:
                return content

    if "outputs" in response_data and isinstance(response_data["outputs"], list):
        first_output = response_data["outputs"][0]
        if isinstance(first_output, dict):
            content = first_output.get("content")
            if isinstance(content, str) and content.strip():
                return content
            if isinstance(content, list):
                return "\n".join(str(item) for item in content)

    if "output" in response_data:
        output = response_data["output"]
        if isinstance(output, str) and output.strip():
            return output
        if isinstance(output, list):
            return "\n".join(str(item) for item in output)

    raise ValueError("AI response did not contain a recognized completion payload")


def generate_schedule(tasks, daily_limit=6.0):
    load_env()
    return _local_schedule_fallback(tasks, daily_limit=daily_limit)


def _build_text_schedule(tasks, daily_limit=6.0):
    """Build a plain text schedule (fallback when AI is not called)"""
    today = datetime.today().date()
    task_items = []
    for task in tasks:
        deadline_date = _parse_date(task.get("deadline_date"))
        deadline_week = _parse_week(task.get("deadline_week"))
        if deadline_date is None and deadline_week is not None:
            deadline_date = deadline_week
        if deadline_date is None:
            deadline_date = today + timedelta(days=7)

        reminder_time = _parse_time(task.get("reminder_time"))
        task_items.append(
            {
                "task_id": task.get("id"),
                "title": task.get("title", "Untitled task"),
                "description": task.get("description", ""),
                "duration": float(task.get("estimated_duration") or 1.0),
                "deadline_date": deadline_date,
                "reminder_time": reminder_time,
            }
        )

    task_items.sort(key=lambda item: (item["deadline_date"], item["reminder_time"] or time(0, 0), -item["duration"]))

    last_date = max(item["deadline_date"] for item in task_items) if task_items else today
    days = {}
    cur_date = today
    while cur_date <= last_date:
        days[cur_date] = {
            "blocks": [],
            "used": 0.0,
            "current_time": datetime.combine(cur_date, time(8, 0)),
        }
        cur_date += timedelta(days=1)

    unscheduled = []
    for item in task_items:
        assigned = False
        for date in sorted(days.keys()):
            if date > item["deadline_date"]:
                break
            day = days[date]
            if day["used"] + item["duration"] > float(daily_limit):
                continue
            start_dt = day["current_time"]
            if item["reminder_time"] is not None:
                candidate = datetime.combine(date, item["reminder_time"])
                if candidate >= day["current_time"]:
                    start_dt = candidate
            end_dt = start_dt + timedelta(hours=item["duration"])
            if end_dt.time() > time(22, 0):
                continue
            day["blocks"].append(
                {
                    "title": item["title"],
                    "start": start_dt.strftime("%H:%M"),
                    "end": end_dt.strftime("%H:%M"),
                    "duration": item["duration"],
                    "deadline": item["deadline_date"].isoformat(),
                    "description": item["description"],
                }
            )
            day["used"] += item["duration"]
            day["current_time"] = end_dt + timedelta(minutes=10)
            assigned = True
            break

        if not assigned:
            unscheduled.append(item)

    lines = ["Here is your study schedule based on deadlines and available time slots:"]
    for date in sorted(days.keys()):
        blocks = days[date]["blocks"]
        if not blocks:
            continue
        lines.append(f"\n{date.isoformat()}:")
        for block in blocks:
            desc = f" - {block['description']}" if block["description"] else ""
            lines.append(
                f"  {block['start']} - {block['end']}: {block['title']} ({block['duration']}h, due {block['deadline']}){desc}"
            )

    if unscheduled:
        lines.append("\nUnable to schedule the following tasks before their deadlines with the current daily limit:")
        for item in unscheduled:
            reminder = _format_time(item["reminder_time"]) if item["reminder_time"] else "no preferred time"
            lines.append(
                f"  - {item['title']} ({item['duration']}h, due {item['deadline_date'].isoformat()}, reminder {reminder})"
            )

    if not any(days[date]["blocks"] for date in days):
        lines.append("No schedule could be created. Please add more time or adjust deadlines.")

    return "\n".join(lines)


def _format_time(value):
    if not value:
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M")
    try:
        parsed = _parse_time(str(value))
        return parsed.strftime("%H:%M") if parsed else None
    except Exception:
        return None


def _format_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, str):
        parsed = _parse_date(value)
        return parsed.isoformat() if parsed else None
    return None


def generate_telegram_message(tasks):
    """Generate an AI-crafted Telegram message for study reminders"""
    load_env()
    provider = get_ai_provider()
    model = get_ollama_model() if provider == "ollama" else "llama-3.1-7b"
    api_key = get_ai_api_key()
    if provider != "ollama" and not api_key:
        raise RuntimeError("AI API key not found")

    # Build task context for AI
    task_lines = []
    for task in tasks:
        title = task.get("title", "Unnamed task")
        duration = float(task.get("estimated_duration") or 1.0)
        deadline = task.get("deadline_date") or task.get("deadline_week") or "no deadline"
        reminder = task.get("reminder_time") or "no reminder time"
        desc = task.get("description")
        if desc:
            task_lines.append(f"• {title}: {duration}h, deadline {deadline}, reminder {reminder}. {desc}")
        else:
            task_lines.append(f"• {title}: {duration}h, deadline {deadline}, reminder {reminder}")

    prompt = TELEGRAM_MESSAGE_PROMPT + "\n\nStudent's Tasks:\n" + "\n".join(task_lines)

    endpoint = f"{get_ollama_host()}/v1/chat/completions" if provider == "ollama" else "https://api.groq.com/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if provider != "ollama":
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 500,
    }

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=(15, 180))
        data = response.json()
        _write_ai_log("telegram_message", prompt, payload, response_data=data)
        message = _parse_ai_text_result(data)
        return message
    except Exception as exc:
        _write_ai_log("telegram_message_error", prompt, payload, exception=exc)
        # Fallback: return formatted schedule
        fallback = [
            "📚 Hey! Here's your study reminder:\n"
        ]
        for line in task_lines:
            fallback.append(line)
        fallback.append("\n✨ You've got this! Stay focused and consistent! 💪")
        return "\n".join(fallback)
