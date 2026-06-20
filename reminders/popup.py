import tkinter as tk
from tkinter import ttk
from datetime import datetime
from utils.env import load_env


def parse_time(time_str):
    if not time_str:
        return None
    time_str = time_str.strip().lower()
    
    # Check AM/PM
    is_pm = False
    is_am = False
    if "pm" in time_str:
        is_pm = True
        time_str = time_str.replace("pm", "").strip()
    elif "am" in time_str:
        is_am = True
        time_str = time_str.replace("am", "").strip()
        
    parts = time_str.split(":")
    if len(parts) < 2:
        return None
        
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            return None
            
        if is_pm:
            if hours < 12:
                hours += 12
        elif is_am:
            if hours == 12:
                hours = 0
            
        return f"{hours:02d}:{minutes:02d}"
    except ValueError:
        return None


def show_popup(task_title: str, time_block: str):
    popup = tk.Toplevel()
    popup.title("Reminder")
    popup.geometry("420x200")
    popup.attributes("-topmost", True)

    ttk.Label(popup, text=f"📌 {task_title}", font=("Segoe UI", 14, "bold")).pack(pady=(20, 10), padx=16)
    ttk.Label(popup, text=time_block, font=("Segoe UI", 12)).pack(pady=(0, 16), padx=16)
    ttk.Button(popup, text="Dismiss", command=popup.destroy).pack(pady=(0, 20))

    popup.focus_force()
    popup.grab_set()


class ReminderManager:
    def __init__(self, db):
        self.db = db
        load_env()
        self.last_shown = set()
        self.root = None

    def set_root(self, root):
        """Set root window for scheduling recurring checks"""
        self.root = root

    def check_reminders(self):
        now = datetime.now().strftime("%H:%M")
        tasks = self.db.get_pending_reminders()
        for task in tasks:
            reminder_time = task.get("reminder_time")
            if reminder_time:
                normalized_time = parse_time(reminder_time)
                if normalized_time == now and (task["id"], normalized_time) not in self.last_shown:
                    title = task.get("title", "Task reminder")
                    block = f"Reminder time: {reminder_time}"
                    show_popup(title, block)
                    self.last_shown.add((task["id"], normalized_time))
        
        # Reschedule this check to run again in 1 second
        if self.root:
            self.root.after(1000, self.check_reminders)

